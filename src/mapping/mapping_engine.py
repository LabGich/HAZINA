
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
    normalize_datetime_with_timezone,
    normalize_signed_amount,
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
    """Maps source-specific records into Hazina's canonical model."""

    TRANSFORMATIONS = {
        "normalize_amount": normalize_amount,
        "normalize_optional_amount": normalize_optional_amount,
        "normalize_currency": normalize_currency,
        "normalize_direction": normalize_direction,
        "normalize_transaction_type": normalize_transaction_type,
        "normalize_status": normalize_status,
        "normalize_payment_method": normalize_payment_method,
        "normalize_optional": normalize_optional,
        "normalize_signed_amount": normalize_signed_amount,
    }

    REQUIRED_TRANSFORMATIONS = {
        "transaction_date",
        "amount",
        "currency",
        "transaction_type",
        "status",
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

        if not field_mapping:
            return value

        normalized_value = str(value).strip().upper()

        if normalized_value not in field_mapping:
            raise TransformationError(
                f"Unmapped value for {field_name}: {value}"
            )

        return field_mapping[normalized_value]

    def _validate_configuration(
        self,
        required_fields: Any,
        field_mappings: Any,
        value_mappings: Any,
        configured_transformations: Any,
        amount_handling: Any,
    ) -> str | None:
        """Validate the structure and supported options of a mapping."""

        if not isinstance(required_fields, list):
            return "required_fields must be a list."

        if not isinstance(field_mappings, dict):
            return "field_mappings must be a mapping."

        if not isinstance(value_mappings, dict):
            return "value_mappings must be a mapping."

        if not isinstance(configured_transformations, dict):
            return "transformations must be a mapping."

        for canonical_field, source_field in field_mappings.items():
            if not isinstance(canonical_field, str) or not isinstance(
                source_field, str
            ):
                return (
                    "Every field_mappings entry must map a canonical "
                    "field name to a source field name."
                )

        for field_name, transformation_name in (
            configured_transformations.items()
        ):
            if not isinstance(field_name, str):
                return "Transformation field names must be strings."

            if not isinstance(transformation_name, str):
                return (
                    f"Transformation for {field_name} must be a string."
                )

            if (
                transformation_name not in self.TRANSFORMATIONS
                and not (
                    field_name == "transaction_date"
                    and transformation_name == "normalize_datetime"
                )
            ):
                return (
                    f"Unsupported transformation: "
                    f"{transformation_name}"
                )

        missing_transformations = (
            self.REQUIRED_TRANSFORMATIONS
            - set(configured_transformations)
        )

        if missing_transformations:
            return (
                "Missing required transformations: "
                + ", ".join(sorted(missing_transformations))
            )

        if amount_handling not in {
            "positive_with_separate_direction",
            "signed_amount",
        }:
            return f"Unsupported amount_handling: {amount_handling}"

        if amount_handling == "signed_amount":
            if (
                configured_transformations.get("amount")
                != "normalize_signed_amount"
            ):
                return (
                    "signed_amount handling requires "
                    "normalize_signed_amount for the amount field."
                )

        return None

    def _apply_transformation(
        self,
        field_name: str,
        value: Any,
        transformation_name: str,
        source_timezone: str | None,
    ) -> Any:
        """Execute an approved transformation."""

        if field_name == "transaction_date":
            if transformation_name != "normalize_datetime":
                raise TransformationError(
                    "transaction_date must use normalize_datetime."
                )

            return normalize_datetime_with_timezone(
                value,
                source_timezone=source_timezone,
            )

        transformation = self.TRANSFORMATIONS.get(
            transformation_name
        )

        if transformation is None:
            raise TransformationError(
                f"Unsupported transformation: {transformation_name}"
            )

        return transformation(value)

    def map_transaction(
        self,
        source_name: str,
        raw_record: dict[str, Any],
        mapping_id: str | None = None,
        mapping_version: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> MappingResult:
        """Map one source record into Hazina's canonical model."""

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
            "transformations", {}
        )

        amount_handling = mapping.get(
            "amount_handling",
            "positive_with_separate_direction",
        )

        configuration_error = self._validate_configuration(
            required_fields,
            field_mappings,
            value_mappings,
            configured_transformations,
            amount_handling,
        )

        if configuration_error:
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                configuration_error,
            )

        source_timezone = mapping.get("source_timezone")

        if source_timezone is not None and not isinstance(
            source_timezone, str
        ):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "source_timezone must be a timezone string or null.",
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
                f"Missing required source fields: "
                f"{', '.join(missing_fields)}",
                missing_fields[0],
            )

        mapped: dict[str, Any] = {}

        try:
            for canonical_field, source_field in field_mappings.items():
                value = raw_record.get(source_field)

                value = normalize_optional(value)

                if value is None:
                    mapped[canonical_field] = None
                    continue

                value = self._apply_value_mapping(
                    canonical_field,
                    value,
                    value_mappings,
                )

                if (
                    amount_handling == "signed_amount"
                    and canonical_field == "amount"
                ):
                    mapped[canonical_field] = value
                    continue

                transformation_name = (
                    configured_transformations.get(canonical_field)
                )

                if transformation_name is not None:
                    value = self._apply_transformation(
                        canonical_field,
                        value,
                        transformation_name,
                        source_timezone,
                    )

                mapped[canonical_field] = value

            if amount_handling == "signed_amount":
                raw_amount = mapped.get("amount")

                if raw_amount is None:
                    raise TransformationError(
                        "Required canonical field is missing: amount"
                    )

                amount, inferred_direction = normalize_signed_amount(
                    raw_amount,
                    direction=mapped.get("direction"),
                )

                mapped["amount"] = amount
                mapped["direction"] = inferred_direction

            else:
                if mapped.get("amount") is None:
                    raise TransformationError(
                        "Required canonical field is missing: amount"
                    )

                if mapped.get("direction") is None:
                    mapped["direction"] = "UNKNOWN"

            for field_name in (
                "transaction_date",
                "currency",
                "transaction_type",
                "status",
            ):
                if mapped.get(field_name) is None:
                    raise TransformationError(
                        f"Required canonical field is missing: "
                        f"{field_name}"
                    )

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

            mapped["description"] = normalize_optional(
                mapped.get("description")
            )

            mapped["counterparty"] = normalize_optional(
                mapped.get("counterparty")
            )

            for field_name in ("fee_amount", "account_balance"):
                value = mapped.get(field_name)

                if value is not None:
                    transformation_name = (
                        configured_transformations.get(field_name)
                    )

                    if transformation_name is None:
                        raise TransformationError(
                            f"Missing transformation for {field_name}."
                        )

                    mapped[field_name] = self._apply_transformation(
                        field_name,
                        value,
                        transformation_name,
                        source_timezone,
                    )

            mapped["transaction_id"] = context.get("transaction_id")
            mapped["mapping_id"] = resolved_mapping_id
            mapped["mapping_version"] = resolved_mapping_version
            mapped["raw_id"] = context.get("raw_id")
            mapped["run_id"] = context.get("run_id")
            mapped["source_metadata"] = context.get(
                "source_metadata", {}
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
