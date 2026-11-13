
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

    @staticmethod
    def _validate_defaults(default_values: Any) -> str | None:
        """Validate configured canonical default values."""

        if not isinstance(default_values, dict):
            return "default_values must be a mapping."

        for field_name, value in default_values.items():
            if not isinstance(field_name, str) or not field_name.strip():
                return "Default field names must be non-empty strings."

            if value is None or isinstance(value, (dict, list, tuple, set)):
                return (
                    f"Default value for {field_name} must be a "
                    "non-null scalar."
                )

        return None

    @staticmethod
    def _validate_derived_fields(derived_fields: Any) -> str | None:
        """Validate configured derived-field rules."""

        if not isinstance(derived_fields, dict):
            return "derived_fields must be a mapping."

        for canonical_field, definition in derived_fields.items():
            if not isinstance(canonical_field, str) or not canonical_field.strip():
                return "Derived field names must be non-empty strings."

            if not isinstance(definition, dict):
                return (
                    f"Derived field configuration for {canonical_field} "
                    "must be a mapping."
                )

            source_field = definition.get("source_field")
            rules = definition.get("rules")

            if not isinstance(source_field, str) or not source_field.strip():
                return (
                    f"Derived field {canonical_field} requires a "
                    "non-empty source_field."
                )

            if not isinstance(rules, list) or not rules:
                return (
                    f"Derived field {canonical_field} requires a "
                    "non-empty rules list."
                )

            for index, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    return (
                        f"Rule {index + 1} for {canonical_field} "
                        "must be a mapping."
                    )

                if set(rule) != {"contains", "value"}:
                    return (
                        f"Rule {index + 1} for {canonical_field} "
                        "must contain exactly 'contains' and 'value'."
                    )

                contains = rule.get("contains")
                value = rule.get("value")

                if not isinstance(contains, str) or not contains.strip():
                    return (
                        f"Rule {index + 1} for {canonical_field} "
                        "requires a non-empty contains value."
                    )

                if value is None or isinstance(value, (dict, list, tuple, set)):
                    return (
                        f"Rule {index + 1} for {canonical_field} "
                        "requires a non-null scalar value."
                    )

        return None

    def _validate_configuration(
        self,
        required_fields: Any,
        field_mappings: Any,
        value_mappings: Any,
        configured_transformations: Any,
        amount_handling: Any,
        amount_fields: Any = None,
        default_values: Any = None,
        derived_fields: Any = None,
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

        if default_values is None:
            default_values = {}

        if derived_fields is None:
            derived_fields = {}

        defaults_error = self._validate_defaults(default_values)
        if defaults_error:
            return defaults_error

        derived_error = self._validate_derived_fields(derived_fields)
        if derived_error:
            return derived_error

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

        if amount_handling not in {
            "positive_with_separate_direction",
            "signed_amount",
            "separate_debit_credit",
        }:
            return f"Unsupported amount_handling: {amount_handling}"

        required_transformations = set(self.REQUIRED_TRANSFORMATIONS)

        if amount_handling == "separate_debit_credit":
            required_transformations.discard("amount")

        available_canonical_fields = (
            set(field_mappings)
            | set(default_values)
            | set(derived_fields)
        )

        missing_canonical_fields = (
            required_transformations - available_canonical_fields
        )

        if missing_canonical_fields:
            return (
                "Missing required canonical fields: "
                + ", ".join(sorted(missing_canonical_fields))
            )

        missing_transformations = (
            required_transformations
            - set(configured_transformations)
        )

        if missing_transformations:
            return (
                "Missing required transformations: "
                + ", ".join(sorted(missing_transformations))
            )

        if amount_handling == "signed_amount":
            if "amount" not in field_mappings:
                return "signed_amount handling requires an amount field mapping."

            if configured_transformations.get("amount") != "normalize_signed_amount":
                return (
                    "signed_amount handling requires "
                    "normalize_signed_amount for the amount field."
                )

            if amount_fields is not None:
                return "amount_fields is only valid with separate_debit_credit."

        elif amount_handling == "positive_with_separate_direction":
            if "amount" not in field_mappings:
                return (
                    "positive_with_separate_direction requires an amount "
                    "field mapping."
                )

            if configured_transformations.get("amount") != "normalize_amount":
                return (
                    "positive_with_separate_direction requires "
                    "normalize_amount for the amount field."
                )

            if amount_fields is not None:
                return "amount_fields is only valid with separate_debit_credit."

        else:
            if "amount" in field_mappings:
                return (
                    "separate_debit_credit must derive amount from "
                    "amount_fields, not field_mappings.amount."
                )

            if not isinstance(amount_fields, dict):
                return (
                    "separate_debit_credit requires amount_fields with "
                    "debit and credit source columns."
                )

            if set(amount_fields) != {"debit", "credit"}:
                return "amount_fields must contain exactly debit and credit."

            debit_field = amount_fields.get("debit")
            credit_field = amount_fields.get("credit")

            if (
                not isinstance(debit_field, str)
                or not debit_field.strip()
                or not isinstance(credit_field, str)
                or not credit_field.strip()
            ):
                return "Debit and credit source field names must be non-empty strings."

            if debit_field == credit_field:
                return "Debit and credit source fields must be different."

            if "amount" in configured_transformations:
                return (
                    "separate_debit_credit must not define an amount "
                    "transformation."
                )

        for canonical_field, source_field in field_mappings.items():
            if not canonical_field.strip() or not source_field.strip():
                return "Field mapping names must be non-empty strings."

        mapped_source_fields = set(field_mappings.values())

        if not set(required_fields).issubset(mapped_source_fields):
            return (
                "Every required source field must be represented in "
                "field_mappings."
            )

        for canonical_field, definition in derived_fields.items():
            if definition["source_field"] not in mapped_source_fields:
                return (
                    f"Source field for derived field {canonical_field} "
                    "must also be represented in field_mappings."
                )

        return None

    def _apply_transformation(
        self,
        field_name: str,
        value: Any,
        transformation_name: str,
        source_timezone: str | None,
        date_format: str | None = None,
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
                date_format=date_format,
            )

        transformation = self.TRANSFORMATIONS.get(
            transformation_name
        )

        if transformation is None:
            raise TransformationError(
                f"Unsupported transformation: {transformation_name}"
            )

        return transformation(value)

    def _apply_derived_fields(
        self,
        mapped: dict[str, Any],
        raw_record: dict[str, Any],
        derived_fields: dict[str, Any],
        configured_transformations: dict[str, str],
        source_timezone: str | None,
        date_format: str | None,
        value_mappings: dict[str, Any],
    ) -> None:
        """Derive canonical values using ordered, first-match rules."""

        for canonical_field, definition in derived_fields.items():
            # A directly mapped, non-empty value takes precedence.
            if normalize_optional(mapped.get(canonical_field)) is not None:
                continue

            source_field = definition["source_field"]
            source_value = normalize_optional(raw_record.get(source_field))

            if source_value is None:
                raise TransformationError(
                    f"Cannot derive {canonical_field}: "
                    f"source field {source_field} is empty."
                )

            normalized_source = str(source_value).strip().upper()
            derived_value = None

            for rule in definition["rules"]:
                search_text = rule["contains"].strip().upper()

                if search_text in normalized_source:
                    derived_value = rule["value"]
                    break

            if derived_value is None:
                raise TransformationError(
                    f"No derivation rule matched {canonical_field} "
                    f"using source field {source_field}: {source_value}"
                )

            derived_value = self._apply_value_mapping(
                canonical_field,
                derived_value,
                value_mappings,
            )

            transformation_name = configured_transformations.get(
                canonical_field
            )

            if transformation_name is not None:
                derived_value = self._apply_transformation(
                    canonical_field,
                    derived_value,
                    transformation_name,
                    source_timezone,
                    date_format,
                )

            mapped[canonical_field] = derived_value

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
            self.registry.get_source(source_name)

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
        default_values = config.get("default_values", {})
        derived_fields = config.get("derived_fields", {})

        amount_handling = mapping.get(
            "amount_handling",
            "positive_with_separate_direction",
        )
        amount_fields = config.get("amount_fields")

        configuration_error = self._validate_configuration(
            required_fields,
            field_mappings,
            value_mappings,
            configured_transformations,
            amount_handling,
            amount_fields,
            default_values,
            derived_fields,
        )

        if configuration_error:
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                configuration_error,
            )

        source_timezone = mapping.get("source_timezone")
        date_format = mapping.get("date_format")

        if source_timezone is not None and not isinstance(
            source_timezone, str
        ):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "source_timezone must be a timezone string or null.",
            )

        if date_format is not None and (
            not isinstance(date_format, str) or not date_format.strip()
        ):
            return failure(
                "INVALID_MAPPING_CONFIGURATION",
                "date_format must be a non-empty string or null.",
            )

        missing_fields = [
            field_name
            for field_name in required_fields
            if field_name not in raw_record
            or normalize_optional(raw_record[field_name]) is None
        ]

        if amount_handling == "separate_debit_credit":
            for source_field in (
                amount_fields["debit"],
                amount_fields["credit"],
            ):
                if source_field not in raw_record:
                    missing_fields.append(source_field)

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
                value = normalize_optional(raw_record.get(source_field))

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
                        date_format,
                    )

                mapped[canonical_field] = value

            # Apply configured defaults only when a field is absent or blank.
            for canonical_field, default_value in default_values.items():
                if normalize_optional(mapped.get(canonical_field)) is None:
                    value = self._apply_value_mapping(
                        canonical_field,
                        default_value,
                        value_mappings,
                    )

                    transformation_name = (
                        configured_transformations.get(canonical_field)
                    )

                    if transformation_name is not None:
                        value = self._apply_transformation(
                            canonical_field,
                            value,
                            transformation_name,
                            source_timezone,
                            date_format,
                        )

                    mapped[canonical_field] = value

            # Derive configured fields using the first matching rule.
            self._apply_derived_fields(
                mapped=mapped,
                raw_record=raw_record,
                derived_fields=derived_fields,
                configured_transformations=configured_transformations,
                source_timezone=source_timezone,
                date_format=date_format,
                value_mappings=value_mappings,
            )

            if amount_handling == "separate_debit_credit":
                debit_field = amount_fields["debit"]
                credit_field = amount_fields["credit"]

                debit_value = normalize_optional(
                    raw_record.get(debit_field)
                )
                credit_value = normalize_optional(
                    raw_record.get(credit_field)
                )

                if debit_value is None and credit_value is None:
                    raise TransformationError(
                        "Exactly one of the debit or credit fields must "
                        "contain an amount; both are empty."
                    )

                if debit_value is not None and credit_value is not None:
                    raise TransformationError(
                        "Exactly one of the debit or credit fields must "
                        "contain an amount; both are populated."
                    )

                if debit_value is not None:
                    mapped["amount"] = normalize_amount(debit_value)
                    mapped["direction"] = "DEBIT"
                else:
                    mapped["amount"] = normalize_amount(credit_value)
                    mapped["direction"] = "CREDIT"

            elif amount_handling == "signed_amount":
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
                        date_format,
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
