
from dataclasses import dataclass, field
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
    normalize_signed_amount,
    normalize_datetime_with_timezone,
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
    }

    DATETIME_TRANSFORMATIONS = {
        "normalize_datetime",
        "normalize_datetime_with_timezone",
    }

    SPECIAL_TRANSFORMATIONS = {
        "normalize_signed_amount",
    }

    REQUIRED_CANONICAL_TRANSFORMATIONS = {
        "transaction_date": {
            "normalize_datetime",
            "normalize_datetime_with_timezone",
        },
        "amount": {
            "normalize_amount",
            "normalize_signed_amount",
        },
        "currency": {"normalize_currency"},
        "transaction_type": {"normalize_transaction_type"},
        "status": {"normalize_status"},
    }

    VALID_AMOUNT_HANDLING = {
        "positive_with_separate_direction",
        "signed_amount",
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
        """Translate configured source values into canonical values."""

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

    def _validate_mapping_configuration(
        self,
        required_fields: Any,
        field_mappings: Any,
        value_mappings: Any,
        transformations: Any,
        amount_handling: Any,
        source_timezone: Any,
    ) -> str | None:
        """Validate the mapping configuration before processing records."""

        if not isinstance(required_fields, list):
            return "required_fields must be a list."

        if not isinstance(field_mappings, dict):
            return "field_mappings must be a mapping."

        if not isinstance(value_mappings, dict):
            return "value_mappings must be a mapping."

        if not isinstance(transformations, dict):
            return "transformations must be a mapping."

        if amount_handling not in self.VALID_AMOUNT_HANDLING:
            return f"Unsupported amount_handling strategy: {amount_handling}"

        if source_timezone is not None and (
            not isinstance(source_timezone, str)
            or not source_timezone.strip()
        ):
            return "source_timezone must be a non-empty string or null."

        for canonical_field, transformation_name in transformations.items():
            if not isinstance(transformation_name, str):
                return (
                    f"Transformation for {canonical_field} "
                    "must be a string."
                )

            approved = (
                self.TRANSFORMATIONS
                | {
                    name: None
                    for name in (
                        self.DATETIME_TRANSFORMATIONS
                        | self.SPECIAL_TRANSFORMATIONS
                    )
                }
            )

            if transformation_name not in approved:
                return (
                    f"Unsupported transformation: {transformation_name}"
                )

        for field_name, allowed_transformations in (
            self.REQUIRED_CANONICAL_TRANSFORMATIONS.items()
        ):
            configured = transformations.get(field_name)

            if configured not in allowed_transformations:
                return (
                    f"Required canonical field '{field_name}' "
                    "has a missing or invalid transformation."
                )

        expected_amount_transformation = (
            "normalize_signed_amount"
            if amount_handling == "signed_amount"
            else "normalize_amount"
        )

        if transformations.get("amount") != expected_amount_transformation:
            return (
                "The amount transformation does not match "
                "the configured amount_handling strategy."
            )

        if (
            "direction" in field_mappings
            and transformations.get("direction") != "normalize_direction"
        ):
            return (
                "A mapped direction field must use "
                "normalize_direction."
            )

        return None

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
        transformations = config.get("transformations", {})

        amount_handling = mapping.get("amount_handling")
        source_timezone = mapping.get("source_timezone")

        config_error = self._validate_mapping_configuration(
            required_fields=required_fields,
            field_mappings=field_mappings,
            value_mappings=value_mappings,
            transformations=transformations,
            amount_handling=amount_handling,
            source_timezone=source_timezone,
        )

        if config_error:
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                config_error,
            )

        for canonical_field, source_field in field_mappings.items():
            if not isinstance(canonical_field, str) or not isinstance(
                source_field, str
            ):
                return failure(
                    "INVALID_MAPPING_CONFIGURATION",
                    "Field mappings must contain string field names.",
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

        mapped: dict[str, Any] = {}
        current_field: str | None = None

        try:
            for canonical_field, source_field in field_mappings.items():
                current_field = canonical_field

                if source_field not in raw_record:
                    mapped[canonical_field] = None
                    continue

                value = normalize_optional(raw_record[source_field])

                if value is None:
                    mapped[canonical_field] = None
                    continue

                value = self._apply_value_mapping(
                    canonical_field,
                    value,
                    value_mappings,
                )

                transformation_name = transformations.get(canonical_field)

                if transformation_name in self.DATETIME_TRANSFORMATIONS:
                    value = normalize_datetime_with_timezone(
                        value,
                        source_timezone=source_timezone,
                    )

                elif transformation_name in self.SPECIAL_TRANSFORMATIONS:
                    # Signed amounts require both amount and direction.
                    # Process them together after all fields are mapped.
                    mapped[canonical_field] = value

                elif transformation_name is not None:
                    transformation = self.TRANSFORMATIONS.get(
                        transformation_name
                    )

                    if transformation is None:
                        raise TransformationError(
                            f"Unsupported transformation: {transformation_name}"
                        )

                    value = transformation(value)

                mapped[canonical_field] = value

            if amount_handling == "signed_amount":
                current_field = "amount"

                amount, inferred_direction = normalize_signed_amount(
                    mapped.get("amount"),
                    direction=mapped.get("direction"),
                )

                mapped["amount"] = amount
                mapped["direction"] = inferred_direction

            elif mapped.get("direction") is None:
                mapped["direction"] = "UNKNOWN"

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
                current_field,
            )

        except Exception as exc:
            return failure(
                "MAPPING_EXECUTION_ERROR",
                f"Unexpected mapping error: {exc}",
                current_field,
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
