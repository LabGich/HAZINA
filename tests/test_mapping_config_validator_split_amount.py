
from copy import deepcopy
from pathlib import Path

import yaml
import pytest

from src.mapping.mapping_config_validator import (
    MappingConfigValidator,
    MappingConfigurationError,
)


def _equity_config():
    root = Path(__file__).resolve().parents[1]
    path = root / "config" / "mappings" / "equity_csv_v1.yaml"

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _validate(config):
    MappingConfigValidator.validate(
        config,
        source_name="EQUITY",
        source_config={"source_type": "FILE"},
    )


def test_validator_accepts_separate_debit_credit_configuration():
    _validate(_equity_config())


def test_validator_rejects_missing_amount_fields():
    config = _equity_config()
    config.pop("amount_fields")

    with pytest.raises(MappingConfigurationError, match="amount_fields"):
        _validate(config)


def test_validator_rejects_same_debit_and_credit_source_field():
    config = _equity_config()
    config["amount_fields"] = {
        "debit": "Amount",
        "credit": "Amount",
    }

    with pytest.raises(MappingConfigurationError, match="different"):
        _validate(config)


def test_validator_rejects_direct_amount_mapping_in_split_mode():
    config = _equity_config()
    config["field_mappings"]["amount"] = "Amount"

    with pytest.raises(MappingConfigurationError, match="derive amount"):
        _validate(config)


def test_validator_rejects_amount_transformation_in_split_mode():
    config = _equity_config()
    config["transformations"]["amount"] = "normalize_amount"

    with pytest.raises(
        MappingConfigurationError,
        match="amount transformation",
    ):
        _validate(config)


def test_validator_rejects_debit_or_credit_in_required_fields():
    config = _equity_config()
    config["required_fields"].append("Debit")

    with pytest.raises(MappingConfigurationError, match="must not be listed"):
        _validate(config)


def test_validator_rejects_amount_fields_for_non_split_mode():
    config = _equity_config()
    config["mapping"]["amount_handling"] = (
        "positive_with_separate_direction"
    )
    config["field_mappings"]["amount"] = "amount"
    config["transformations"]["amount"] = "normalize_amount"
    config["required_fields"].append("amount")

    with pytest.raises(MappingConfigurationError, match="only valid"):
        _validate(config)
