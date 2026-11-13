
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)
from src.mapping.transformations import (
    TransformationError,
    normalize_amount,
    normalize_optional,
    normalize_optional_amount,
    normalize_currency,
    normalize_direction,
    normalize_transaction_type,
    normalize_status,
    normalize_payment_method,
    normalize_datetime,
)


@dataclass
class MappingErrorDetail:
    """Represents a structured mapping error."""

    error_code: str
    error_message: str
    field_name: str | None = None


@dataclass
class MappingResult:
    """Contains either a canonical transaction or mapping errors."""

    success: bool
    canonical_transaction: dict[str, Any] | None = None
    errors: list[MappingErrorDetail] = field(default_factory=list)
    mapping_id: str | None = None
    mapping_version: str | None = None


class MappingEngine:
    """Maps source-specific transaction records to Hazina's canonical model."""

    TRANSFORMATIONS = {
        "normalize_amount": normalize_amount,
        "normalize_optional_amount": normalize_optional_amount,
        "normalize_currency": normalize_currency,
        "normalize_direction": normalize_direction,
        "normalize_transaction_type": normalize_transaction_type,
        "normalize_status": normalize_status,
        "normalize_payment_method": normalize_payment_method,
        "normalize_datetime": normalize_datetime,
        "normalize_optional": normalize_optional,
    }

    def __init__(
        self,
        registry: MappingRegistry | None = None,
    ) -> None:
        self.registry = registry or MappingRegistry()

    @staticmethod
    def _error(
        error_code: str,
        message: str,
        field_name: str | None = None,
    ) -> MappingResult:
        return MappingResult(
            success=False,
            errors=[
                MappingErrorDetail(
                    error_code=error_code,
                    error_message=message,
                    field_name=field_name,
                )
            ],
        )

    @staticmethod
    def _apply_value_mapping(
        field_name: str,
        value: Any,
        value_mappings: dict[str, Any],
    ) -> Any:
        """Apply configured source-value translations."""

        if value is None:
            return None

        field_mapping = value_mappings.get(field_name, {})

        if not isinstance(field_mapping, dict):
            raise TransformationError(
                f"Invalid value mapping configuration for {field_name}"
            )

        normalized_value = str(value).strip().upper()

        if not field_mapping:
            return value

        if normalized_value not in field_mapping:
            raise TransformationError(
                f"Unmapped value for {field_name}: {value}"
            )

        return field_mapping[normalized_value]

    @staticmethod
    def _apply_transformation(
        field_name: str,
        value: Any,
        transformation_name: str | None,
        transformations: dict[str, Any],
    ) -> Any:
        """Execute an approved transformation."""

        if transformation_name is None:
            return value

        transformation = transformations.get(transformation_name)

        if transformation is None:
            raise TransformationError(
                f"Unsupported transformation: {transformation_name}"
            )

        try:
            return transformation(value)
        except TransformationError:
            raise
        except Exception as exc:
            raise TransformationError(
                f"Transformation failed for {field_name}: {exc}"
            ) from exc

    def map_transaction(
        self,
        source_name: str,
        raw_record: dict[str, Any],
        mapping_id: str | None = None,
        mapping_version: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> MappingResult:
        """Map one source record into Hazina's canonical transaction model."""

        context = context or {}

        if not isinstance(raw_record, dict):
            return self._error(
                "INVALID_SOURCE_RECORD",
                "Raw transaction must be a dictionary.",
            )

        try:
            source = self.registry.get_source(source_name)

            config = self.registry.resolve_mapping(
                source_name=source_name,
                mapping_id=mapping_id,
                mapping_version=mapping_version,
            )

        except MappingRegistryError as exc:
            return self._error(
                "MAPPING_CONFIGURATION_ERROR",
                str(exc),
            )

        mapping = config["mapping"]
        resolved_mapping_id = mapping["mapping_id"]
        resolved_mapping_version = mapping["mapping_version"]

        def failure(
            code: str,
            message: str,
            field_name: str | None = None,
        ) -> MappingResult:
            result = self._error(code, message, field_name)
            result.mapping_id = resolved_mapping_id
            result.mapping_version = resolved_mapping_version
            return result

        required_fields = config.get("required_fields", [])
        field_mappings = config.get("field_mappings", {})
        value_mappings = config.get("value_mappings", {})
        configured_transformations = config.get(
            "transformations",
            {},
        )

        if not isinstance(required_fields, list):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "required_fields must be a list.",
            )

        if not isinstance(field_mappings, dict):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "field_mappings must be a mapping.",
            )

        if not isinstance(value_mappings, dict):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "value_mappings must be a mapping.",
            )

        if not isinstance(configured_transformations, dict):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "transformations must be a mapping.",
            )

        missing_fields = [
            field_name
            for field_name in required_fields
            if field_name not in raw_record
            or normalize_optional(raw_record[field_name]) is None
        ]

        if missing_fields:
            return failure(
                "MISSING_REQUIRED_FIELD",
                f"Missing required source fields: {', '.join(missing_fields)}",
                missing_fields[0],
            )

        mapped = {}

        try:
            for canonical_field, source_field in field_mappings.items():

                if source_field not in raw_record:
                    mapped[canonical_field] = None
                    continue

                value = raw_record[source_field]

                value = normalize_optional(value)

                if value is None:
                    mapped[canonical_field] = None
                    continue

                value = self._apply_value_mapping(
                    canonical_field,
                    value,
                    value_mappings,
                )

                transformation_name = configured_transformations.get(
                    canonical_field
                )

                value = self._apply_transformation(
                    canonical_field,
                    value,
                    transformation_name,
                    self.TRANSFORMATIONS,
                )

                mapped[canonical_field] = value

            # Apply canonical transformations even when they are
            # not explicitly configured in YAML.
            canonical_transformations = {
                "transaction_date": normalize_datetime,
                "amount": normalize_amount,
                "currency": normalize_currency,
                "transaction_type": normalize_transaction_type,
                "direction": normalize_direction,
                "payment_method": normalize_payment_method,
                "status": normalize_status,
                "fee_amount": normalize_optional_amount,
                "account_balance": normalize_optional_amount,
            }

            for field_name, transformation in (
                canonical_transformations.items()
            ):
                value = mapped.get(field_name)

                if value is None and field_name not in {
                    "direction",
                    "fee_amount",
                    "account_balance",
                }:
                    raise TransformationError(
                        f"Required canonical field is missing: {field_name}"
                    )

                if value is not None:
                    mapped[field_name] = transformation(value)

            mapped["source_name"] = source_name.strip().upper()
            mapped["source_transaction_id"] = normalize_optional(
                mapped.get("source_transaction_id")
            )
            mapped["source_account_id"] = normalize_optional(
                mapped.get("source_account_id")
            )
            mapped["customer_id"] = normalize_optional(
                mapped.get("customer_id")
            )

            mapped["transaction_id"] = context.get("transaction_id")

            mapped["mapping_id"] = resolved_mapping_id
            mapped["mapping_version"] = resolved_mapping_version

            mapped["raw_id"] = context.get("raw_id")
            mapped["run_id"] = context.get("run_id")

            mapped["source_metadata"] = context.get(
                "source_metadata",
                {},
            )

            return MappingResult(
                success=True,
                canonical_transaction=mapped,
                mapping_id=resolved_mapping_id,
                mapping_version=resolved_mapping_version,
            )

        except TransformationError as exc:
            return failure(
                "MAPPING_EXECUTION_ERROR",
                str(exc),
            )

        except Exception as exc:
            return failure(
                "MAPPING_EXECUTION_ERROR",
                f"Unexpected mapping error: {exc}",
            )


def map_transaction(
    source_name: str,
    raw_record: dict[str, Any],
    mapping_id: str | None = None,
    mapping_version: str | None = None,
    context: dict[str, Any] | None = None,
) -> MappingResult:
    """Convenience function for mapping one transaction."""

    engine = MappingEngine()

    return engine.map_transaction(
        source_name=source_name,
        raw_record=raw_record,
        mapping_id=mapping_id,
        mapping_version=mapping_version,
        context=context,
    )
