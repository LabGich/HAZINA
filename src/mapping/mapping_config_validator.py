
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class MappingConfigurationError(ValueError):
    """Raised when a mapping configuration is structurally invalid."""


class MappingConfigValidator:
    """Validates mapping configuration structure and consistency."""

    CANONICAL_FIELDS = {
        "transaction_id",
        "source_name",
        "source_transaction_id",
        "source_account_id",
        "customer_id",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
        "direction",
        "payment_method",
        "status",
        "description",
        "counterparty",
        "fee_amount",
        "account_balance",
    }

    REQUIRED_CANONICAL_FIELDS = {
        "transaction_date",
        "amount",
        "currency",
        "transaction_type",
        "status",
    }

    REQUIRED_CANONICAL_FIELDS_WITH_SPLIT_AMOUNT = {
        "transaction_date",
        "currency",
        "transaction_type",
        "status",
    }

    APPROVED_TRANSFORMATIONS = {
        "normalize_amount",
        "normalize_optional_amount",
        "normalize_currency",
        "normalize_direction",
        "normalize_transaction_type",
        "normalize_status",
        "normalize_payment_method",
        "normalize_optional",
        "normalize_signed_amount",
    }

    AMOUNT_HANDLING_OPTIONS = {
        "positive_with_separate_direction",
        "signed_amount",
        "separate_debit_credit",
    }

    @classmethod
    def validate(
        cls,
        config: dict[str, Any],
        source_name: str,
        source_config: dict[str, Any],
    ) -> None:
        """Validate a complete mapping configuration."""

        if not isinstance(config, dict):
            raise MappingConfigurationError(
                "Mapping configuration must be a dictionary."
            )

        mapping = config.get("mapping")

        if not isinstance(mapping, dict):
            raise MappingConfigurationError(
                "Mapping metadata must be a dictionary."
            )

        mapping_id = mapping.get("mapping_id")
        mapping_version = mapping.get("mapping_version")
        configured_source = mapping.get("source_name")
        source_type = mapping.get("source_type")
        description = mapping.get("description")

        if not isinstance(mapping_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]*",
            mapping_id,
        ):
            raise MappingConfigurationError(
                "Invalid or missing mapping_id."
            )

        if (
            not isinstance(mapping_version, str)
            or not mapping_version.strip()
        ):
            raise MappingConfigurationError(
                "Invalid or missing mapping_version."
            )

        if configured_source != source_name:
            raise MappingConfigurationError(
                f"Mapping source mismatch: expected {source_name}."
            )

        if source_type not in {"FILE", "API"}:
            raise MappingConfigurationError(
                "Mapping source_type must be FILE or API."
            )

        if source_type != source_config.get("source_type"):
            raise MappingConfigurationError(
                "Mapping source_type does not match registered source."
            )

        if not isinstance(description, str) or not description.strip():
            raise MappingConfigurationError(
                "Mapping description is required."
            )

        cls._validate_timezone(mapping.get("source_timezone"))
        cls._validate_date_format(mapping.get("date_format"))

        required_fields = config.get("required_fields")
        field_mappings = config.get("field_mappings")
        value_mappings = config.get("value_mappings", {})
        transformations = config.get("transformations")
        default_values = config.get("default_values", {})
        derived_fields = config.get("derived_fields", {})

        amount_handling = mapping.get(
            "amount_handling",
            "positive_with_separate_direction",
        )

        amount_fields = config.get("amount_fields")

        split_mode = amount_handling == "separate_debit_credit"

        cls._validate_required_fields(required_fields)

        cls._validate_default_values(default_values)

        cls._validate_derived_fields(
            derived_fields,
            field_mappings,
            default_values,
        )

        cls._validate_field_mappings(
            field_mappings,
            split_mode,
            default_values,
            derived_fields,
        )

        cls._validate_required_field_mappings(
            required_fields,
            field_mappings,
            amount_fields,
            split_mode,
            derived_fields,
        )

        cls._validate_value_mappings(
            value_mappings,
            field_mappings,
        )

        cls._validate_transformations(
            transformations,
            field_mappings,
            split_mode,
            default_values,
            derived_fields,
        )

        cls._validate_amount_handling(
            amount_handling,
            transformations,
            field_mappings,
            amount_fields,
        )

    @staticmethod
    def _validate_timezone(source_timezone: Any) -> None:
        if source_timezone is None:
            return

        if (
            not isinstance(source_timezone, str)
            or not source_timezone.strip()
        ):
            raise MappingConfigurationError(
                "source_timezone must be a valid IANA timezone or null."
            )

        try:
            ZoneInfo(source_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise MappingConfigurationError(
                f"Unknown source timezone: {source_timezone}"
            )

    @staticmethod
    def _validate_date_format(date_format: Any) -> None:
        if date_format is None:
            return

        if (
            not isinstance(date_format, str)
            or not date_format.strip()
        ):
            raise MappingConfigurationError(
                "date_format must be a non-empty format string or null."
            )

        try:
            sample = datetime(2000, 3, 5, 14, 30, 0)
            formatted = sample.strftime(date_format)
            datetime.strptime(formatted, date_format)
        except (ValueError, TypeError):
            raise MappingConfigurationError(
                f"Invalid date_format: {date_format}"
            )

    @staticmethod
    def _validate_required_fields(required_fields: Any) -> None:
        if not isinstance(required_fields, list) or not required_fields:
            raise MappingConfigurationError(
                "required_fields must be a non-empty list."
            )

        if any(
            not isinstance(field, str) or not field.strip()
            for field in required_fields
        ):
            raise MappingConfigurationError(
                "Every required field must be a non-empty string."
            )

        if len(required_fields) != len(set(required_fields)):
            raise MappingConfigurationError(
                "required_fields cannot contain duplicates."
            )

    @classmethod
    def _validate_default_values(
        cls,
        default_values: Any,
    ) -> None:
        if not isinstance(default_values, dict):
            raise MappingConfigurationError(
                "default_values must be a mapping."
            )

        for canonical_field, value in default_values.items():
            if canonical_field not in cls.CANONICAL_FIELDS:
                raise MappingConfigurationError(
                    f"Unsupported default canonical field: "
                    f"{canonical_field}"
                )

            if value is None:
                raise MappingConfigurationError(
                    f"Default value for {canonical_field} cannot be null."
                )

            if isinstance(value, (dict, list)):
                raise MappingConfigurationError(
                    f"Default value for {canonical_field} must be scalar."
                )

    @classmethod
    def _validate_derived_fields(
        cls,
        derived_fields: Any,
        field_mappings: Any,
        default_values: Any,
    ) -> None:
        if not isinstance(derived_fields, dict):
            raise MappingConfigurationError(
                "derived_fields must be a mapping."
            )

        for canonical_field, configuration in derived_fields.items():
            if canonical_field not in cls.CANONICAL_FIELDS:
                raise MappingConfigurationError(
                    f"Unsupported derived canonical field: "
                    f"{canonical_field}"
                )

            if canonical_field in field_mappings:
                raise MappingConfigurationError(
                    f"Derived field {canonical_field} cannot also have "
                    "a direct field mapping."
                )

            if canonical_field in default_values:
                raise MappingConfigurationError(
                    f"Derived field {canonical_field} cannot also have "
                    "a default value."
                )

            if not isinstance(configuration, dict):
                raise MappingConfigurationError(
                    f"Derived field configuration for "
                    f"{canonical_field} must be a mapping."
                )

            source_field = configuration.get("source_field")

            if (
                not isinstance(source_field, str)
                or not source_field.strip()
            ):
                raise MappingConfigurationError(
                    f"Derived field {canonical_field} requires "
                    "a non-empty source_field."
                )

            rules = configuration.get("rules")

            if not isinstance(rules, list) or not rules:
                raise MappingConfigurationError(
                    f"Derived field {canonical_field} requires "
                    "a non-empty rules list."
                )

            for rule in rules:
                if not isinstance(rule, dict):
                    raise MappingConfigurationError(
                        f"Every rule for {canonical_field} "
                        "must be a mapping."
                    )

                match_value = rule.get("contains")
                result_value = rule.get("value")

                if (
                    not isinstance(match_value, str)
                    or not match_value.strip()
                ):
                    raise MappingConfigurationError(
                        f"Every rule for {canonical_field} requires "
                        "a non-empty contains value."
                    )

                if result_value is None:
                    raise MappingConfigurationError(
                        f"Every rule for {canonical_field} requires "
                        "a non-null value."
                    )

                if isinstance(result_value, (dict, list)):
                    raise MappingConfigurationError(
                        f"Rule values for {canonical_field} must be scalar."
                    )

    @classmethod
    def _validate_field_mappings(
        cls,
        field_mappings: Any,
        split_mode: bool = False,
        default_values: dict[str, Any] | None = None,
        derived_fields: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(field_mappings, dict) or not field_mappings:
            raise MappingConfigurationError(
                "field_mappings must be a non-empty mapping."
            )

        default_values = default_values or {}
        derived_fields = derived_fields or {}

        for canonical_field, source_field in field_mappings.items():
            if canonical_field not in cls.CANONICAL_FIELDS:
                raise MappingConfigurationError(
                    f"Unsupported canonical field: {canonical_field}"
                )

            if (
                not isinstance(source_field, str)
                or not source_field.strip()
            ):
                raise MappingConfigurationError(
                    f"Invalid source field for {canonical_field}."
                )

        required = (
            cls.REQUIRED_CANONICAL_FIELDS_WITH_SPLIT_AMOUNT
            if split_mode
            else cls.REQUIRED_CANONICAL_FIELDS
        )

        available_fields = (
            set(field_mappings)
            | set(default_values)
            | set(derived_fields)
        )

        missing = required - available_fields

        if missing:
            raise MappingConfigurationError(
                "Missing required canonical field mappings: "
                + ", ".join(sorted(missing))
            )

        if split_mode and "amount" in field_mappings:
            raise MappingConfigurationError(
                "separate_debit_credit must derive amount from amount_fields."
            )

    @staticmethod
    def _validate_required_field_mappings(
        required_fields: list[str],
        field_mappings: dict[str, str],
        amount_fields: dict[str, str] | None = None,
        split_mode: bool = False,
        derived_fields: dict[str, Any] | None = None,
    ) -> None:
        """Ensure required source fields are represented in the mapping."""

        mapped_source_fields = set(field_mappings.values())

        # Derived-field inputs are valid source fields too.
        for definition in (derived_fields or {}).values():
            if isinstance(definition, dict):
                source_field = definition.get("source_field")

                if isinstance(source_field, str):
                    mapped_source_fields.add(source_field)

        if split_mode:
            amount_source_fields = (
                set(amount_fields.values())
                if isinstance(amount_fields, dict)
                else set()
            )

            if set(required_fields) & amount_source_fields:
                raise MappingConfigurationError(
                    "Debit and credit amount fields must not be listed in "
                    "required_fields; exactly one must be populated per record."
                )

        missing = set(required_fields) - mapped_source_fields

        if missing:
            raise MappingConfigurationError(
                "Required source fields are not mapped: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _validate_value_mappings(
        value_mappings: Any,
        field_mappings: dict[str, str],
    ) -> None:
        if not isinstance(value_mappings, dict):
            raise MappingConfigurationError(
                "value_mappings must be a mapping."
            )

        for canonical_field, translations in value_mappings.items():
            if canonical_field not in field_mappings:
                raise MappingConfigurationError(
                    f"Value mapping references an unmapped field: "
                    f"{canonical_field}"
                )

            if not isinstance(translations, dict):
                raise MappingConfigurationError(
                    f"Value mappings for {canonical_field} must be a mapping."
                )

            for source_value, canonical_value in translations.items():
                if (
                    not isinstance(source_value, str)
                    or not source_value.strip()
                ):
                    raise MappingConfigurationError(
                        f"Invalid source value in {canonical_field} mapping."
                    )

                if canonical_value is None:
                    raise MappingConfigurationError(
                        f"Invalid canonical value in {canonical_field} mapping."
                    )

    @classmethod
    def _validate_transformations(
        cls,
        transformations: Any,
        field_mappings: dict[str, str],
        split_mode: bool = False,
        default_values: dict[str, Any] | None = None,
        derived_fields: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(transformations, dict):
            raise MappingConfigurationError(
                "transformations must be a mapping."
            )

        if split_mode and "amount" in transformations:
            raise MappingConfigurationError(
                "separate_debit_credit must not define an amount transformation."
            )

        available_fields = (
            set(field_mappings)
            | set(default_values or {})
            | set(derived_fields or {})
        )

        for canonical_field, transformation_name in transformations.items():
            if canonical_field not in available_fields:
                raise MappingConfigurationError(
                    f"Transformation references an unmapped field: "
                    f"{canonical_field}"
                )

            if not isinstance(transformation_name, str):
                raise MappingConfigurationError(
                    f"Invalid transformation for {canonical_field}."
                )

            if canonical_field == "transaction_date":
                if transformation_name != "normalize_datetime":
                    raise MappingConfigurationError(
                        "transaction_date must use normalize_datetime."
                    )

            elif transformation_name not in cls.APPROVED_TRANSFORMATIONS:
                raise MappingConfigurationError(
                    f"Unsupported transformation: {transformation_name}"
                )

        required = (
            cls.REQUIRED_CANONICAL_FIELDS_WITH_SPLIT_AMOUNT
            if split_mode
            else cls.REQUIRED_CANONICAL_FIELDS
        )

        missing = required - set(transformations)

        if missing:
            raise MappingConfigurationError(
                "Missing required transformations: "
                + ", ".join(sorted(missing))
            )

        for optional_field in ("fee_amount", "account_balance"):
            if (
                optional_field in field_mappings
                and optional_field not in transformations
            ):
                raise MappingConfigurationError(
                    f"Missing transformation for {optional_field}."
                )

        if (
            "direction" in field_mappings
            and "direction" not in transformations
        ):
            raise MappingConfigurationError(
                "A mapped direction field requires a transformation."
            )

    @classmethod
    def _validate_amount_handling(
        cls,
        amount_handling: Any,
        transformations: Any,
        field_mappings: Any,
        amount_fields: Any,
    ) -> None:
        if amount_handling not in cls.AMOUNT_HANDLING_OPTIONS:
            raise MappingConfigurationError(
                f"Unsupported amount_handling: {amount_handling}"
            )

        if amount_handling == "separate_debit_credit":
            if (
                not isinstance(amount_fields, dict)
                or set(amount_fields) != {"debit", "credit"}
            ):
                raise MappingConfigurationError(
                    "separate_debit_credit requires amount_fields containing "
                    "exactly debit and credit."
                )

            debit = amount_fields.get("debit")
            credit = amount_fields.get("credit")

            if (
                not isinstance(debit, str)
                or not debit.strip()
                or not isinstance(credit, str)
                or not credit.strip()
            ):
                raise MappingConfigurationError(
                    "Debit and credit source field names must be non-empty strings."
                )

            if debit == credit:
                raise MappingConfigurationError(
                    "Debit and credit source fields must be different."
                )

            if (
                isinstance(field_mappings, dict)
                and "amount" in field_mappings
            ):
                raise MappingConfigurationError(
                    "separate_debit_credit must not map canonical amount directly."
                )

            if (
                isinstance(transformations, dict)
                and "amount" in transformations
            ):
                raise MappingConfigurationError(
                    "separate_debit_credit must not define an amount transformation."
                )

            return

        if amount_fields is not None:
            raise MappingConfigurationError(
                "amount_fields is only valid with separate_debit_credit."
            )

        if (
            not isinstance(field_mappings, dict)
            or "amount" not in field_mappings
        ):
            raise MappingConfigurationError(
                f"{amount_handling} requires a canonical amount field mapping."
            )

        amount_transformation = (
            transformations.get("amount")
            if isinstance(transformations, dict)
            else None
        )

        if amount_handling == "signed_amount":
            if amount_transformation != "normalize_signed_amount":
                raise MappingConfigurationError(
                    "signed_amount requires normalize_signed_amount."
                )

        elif amount_transformation != "normalize_amount":
            raise MappingConfigurationError(
                "positive_with_separate_direction requires normalize_amount."
            )
