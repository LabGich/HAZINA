from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import yaml
from src.mapping.mapping_registry import MappingRegistry

from src.mapping.mapping_engine import MappingEngine


def valid_bank_record():
    return {
        "transaction_id": "BANK_TXN001",
        "account_id": "BANK_ACC001",
        "customer_id": "CUST001",
        "transaction_date": "2026-11-12T14:30:00+03:00",
        "amount": "1500.00",
        "currency": "KES",
        "transaction_type": "PAYMENT",
        "direction": "DR",
        "payment_method": "MPESA",
        "status": "COMPLETED",
        "description": "Test payment",
        "counterparty": "Test Merchant",
        "fee": "15.00",
        "balance": "5000.00",
    }

def engine_with_custom_bank_mapping(tmp_path, updates):
    """Create a mapping engine using a temporary BANK configuration."""

    project_root = Path(__file__).resolve().parents[1]

    sources_path = (
        project_root / "config" / "sources" / "sources.yaml"
    )

    mapping_path = (
        project_root
        / "config"
        / "mappings"
        / "bank_csv_v1.yaml"
    )

    with mapping_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    config["mapping"].update(updates.get("mapping", {}))
    config["transformations"].update(
        updates.get("transformations", {})
    )

    custom_mapping_path = tmp_path / "bank_csv_v1.yaml"

    with custom_mapping_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    registry = MappingRegistry(
        sources_path=sources_path,
        mappings_dir=tmp_path,
    )

    return MappingEngine(registry=registry)

def test_mapping_engine_maps_valid_bank_record():

    engine = MappingEngine()

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=valid_bank_record(),
        context={
            "transaction_id": "hazina-test-001",
            "raw_id": 1001,
            "run_id": 501,
            "source_metadata": {
                "source_file": "bank_statement.csv",
            },
        },
    )

    assert result.success is True
    assert result.errors == []

    transaction = result.canonical_transaction

    assert transaction["transaction_id"] == "hazina-test-001"
    assert transaction["source_name"] == "BANK"
    assert transaction["source_transaction_id"] == "BANK_TXN001"
    assert transaction["source_account_id"] == "BANK_ACC001"
    assert transaction["customer_id"] == "CUST001"

    assert transaction["amount"] == Decimal("1500.00")
    assert transaction["currency"] == "KES"
    assert transaction["transaction_type"] == "PAYMENT"
    assert transaction["direction"] == "DEBIT"
    assert transaction["payment_method"] == "MPESA"
    assert transaction["status"] == "COMPLETED"

    assert transaction["fee_amount"] == Decimal("15.00")
    assert transaction["account_balance"] == Decimal("5000.00")

    assert transaction["mapping_id"] == "bank_csv_v1"
    assert transaction["mapping_version"] == "1.0"

    assert transaction["raw_id"] == 1001
    assert transaction["run_id"] == 501


def test_mapping_engine_normalizes_transaction_date_to_utc():

    engine = MappingEngine()

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=valid_bank_record(),
    )

    assert result.success is True

    assert result.canonical_transaction["transaction_date"] == (
        datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)
    )


def test_mapping_engine_rejects_missing_required_field():

    engine = MappingEngine()

    record = valid_bank_record()
    del record["amount"]

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MISSING_REQUIRED_FIELD"
    assert result.errors[0].field_name == "amount"


def test_mapping_engine_rejects_unknown_transaction_type():

    engine = MappingEngine()

    record = valid_bank_record()
    record["transaction_type"] = "UNKNOWN_TYPE"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def test_mapping_engine_rejects_unknown_source():

    engine = MappingEngine()

    result = engine.map_transaction(
        source_name="UNKNOWN_SOURCE",
        raw_record=valid_bank_record(),
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MAPPING_CONFIGURATION_ERROR"


def test_mapping_engine_preserves_optional_missing_fields():

    engine = MappingEngine()

    record = valid_bank_record()
    record.pop("customer_id")
    record.pop("description")
    record.pop("counterparty")
    record.pop("fee")
    record.pop("balance")

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is True

    transaction = result.canonical_transaction

    assert transaction["customer_id"] is None
    assert transaction["description"] is None
    assert transaction["counterparty"] is None
    assert transaction["fee_amount"] is None
    assert transaction["account_balance"] is None


def test_mapping_engine_rejects_non_dictionary_record():

    engine = MappingEngine()

    result = engine.map_transaction(
        source_name="BANK",
        raw_record="not-a-dictionary",
    )

    assert result.success is False
    assert result.errors[0].error_code == "INVALID_SOURCE_RECORD"


def test_mapping_engine_records_mapping_version_on_success():

    engine = MappingEngine()

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=valid_bank_record(),
    )

    assert result.success is True
    assert result.mapping_id == "bank_csv_v1"
    assert result.mapping_version == "1.0"


def test_mapping_engine_records_mapping_version_on_record_error():

    engine = MappingEngine()

    record = valid_bank_record()
    record["status"] = "UNKNOWN_STATUS"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is False
    assert result.mapping_id == "bank_csv_v1"
    assert result.mapping_version == "1.0"

def test_mapping_engine_maps_signed_negative_amount_as_debit(tmp_path):
    engine = engine_with_custom_bank_mapping(
        tmp_path,
        {
            "mapping": {
                "amount_handling": "signed_amount",
            },
            "transformations": {
                "amount": "normalize_signed_amount",
            },
        },
    )

    record = valid_bank_record()
    record["amount"] = "-1500.50"
    record["direction"] = "DR"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("1500.50")
    assert result.canonical_transaction["direction"] == "DEBIT"


def test_mapping_engine_maps_signed_positive_amount_as_credit(tmp_path):
    engine = engine_with_custom_bank_mapping(
        tmp_path,
        {
            "mapping": {
                "amount_handling": "signed_amount",
            },
            "transformations": {
                "amount": "normalize_signed_amount",
            },
        },
    )

    record = valid_bank_record()
    record["amount"] = "2500.00"
    record["direction"] = "CR"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("2500.00")
    assert result.canonical_transaction["direction"] == "CREDIT"


def test_mapping_engine_rejects_signed_amount_direction_conflict(tmp_path):
    engine = engine_with_custom_bank_mapping(
        tmp_path,
        {
            "mapping": {
                "amount_handling": "signed_amount",
            },
            "transformations": {
                "amount": "normalize_signed_amount",
            },
        },
    )

    record = valid_bank_record()
    record["amount"] = "-500"
    record["direction"] = "CR"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def test_mapping_engine_uses_configured_source_timezone(tmp_path):
    engine = engine_with_custom_bank_mapping(
        tmp_path,
        {
            "mapping": {
                "source_timezone": "Africa/Nairobi",
            },
        },
    )

    record = valid_bank_record()
    record["transaction_date"] = "2026-11-12T14:30:00"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["transaction_date"] == (
        datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)
    )


def test_mapping_engine_rejects_naive_timestamp_without_timezone(tmp_path):
    engine = engine_with_custom_bank_mapping(
        tmp_path,
        {
            "mapping": {
                "source_timezone": None,
            },
        },
    )

    record = valid_bank_record()
    record["transaction_date"] = "2026-11-12T14:30:00"

    result = engine.map_transaction(
        source_name="BANK",
        raw_record=record,
    )

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"