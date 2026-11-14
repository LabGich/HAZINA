
from datetime import datetime, timezone
from decimal import Decimal

import yaml

from src.mapping.mapping_registry import MappingRegistry
from src.mapping.mapping_engine import MappingEngine


SOURCE_NAME = "TEST_SOURCE"
MAPPING_ID = "test_source_csv_v1"


def valid_test_record():
    return {
        "transaction_id": "TEST_TXN001",
        "account_id": "TEST_ACC001",
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


def create_test_mapping():
    return {
        "mapping": {
            "mapping_id": MAPPING_ID,
            "mapping_version": "1.0",
            "source_name": SOURCE_NAME,
            "source_type": "FILE",
            "description": "Synthetic mapping for mapping engine tests",
            "source_timezone": "Africa/Nairobi",
            "amount_handling": "positive_with_separate_direction",
        },
        "required_fields": [
            "transaction_date",
            "amount",
            "currency",
            "transaction_type",
            "direction",
            "status",
        ],
        "field_mappings": {
            "source_transaction_id": "transaction_id",
            "source_account_id": "account_id",
            "customer_id": "customer_id",
            "transaction_date": "transaction_date",
            "amount": "amount",
            "currency": "currency",
            "transaction_type": "transaction_type",
            "direction": "direction",
            "payment_method": "payment_method",
            "status": "status",
            "description": "description",
            "counterparty": "counterparty",
            "fee_amount": "fee",
            "account_balance": "balance",
        },
        "value_mappings": {},
        "default_values": {},
        "derived_fields": {},
        "transformations": {
            "transaction_date": "normalize_datetime",
            "amount": "normalize_amount",
            "currency": "normalize_currency",
            "transaction_type": "normalize_transaction_type",
            "direction": "normalize_direction",
            "payment_method": "normalize_payment_method",
            "status": "normalize_status",
            "fee_amount": "normalize_optional_amount",
            "account_balance": "normalize_optional_amount",
        },
    }


def engine_with_custom_test_mapping(tmp_path, updates=None):
    """Create an isolated mapping engine for synthetic test records."""

    updates = updates or {}

    config = create_test_mapping()

    config["mapping"].update(updates.get("mapping", {}))
    config["transformations"].update(
        updates.get("transformations", {})
    )
    config["field_mappings"].update(
        updates.get("field_mappings", {})
    )

    if "required_fields" in updates:
        config["required_fields"] = updates["required_fields"]

    if "amount_fields" in updates:
        config["amount_fields"] = updates["amount_fields"]

    for key in updates.get("remove_field_mappings", []):
        config["field_mappings"].pop(key, None)

    for key in updates.get("remove_transformations", []):
        config["transformations"].pop(key, None)

    sources_config = {
        "sources": {
            SOURCE_NAME: {
                "source_type": "FILE",
                "source_identifier": "test_source",
                "description": "Synthetic source for mapping engine tests",
                "enabled": True,
                "supported_formats": ["CSV"],
                "default_mapping": {
                    "mapping_id": MAPPING_ID,
                    "mapping_version": "1.0",
                },
            }
        }
    }

    sources_path = tmp_path / "sources.yaml"
    mapping_path = tmp_path / f"{MAPPING_ID}.yaml"

    with sources_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(sources_config, file, sort_keys=False)

    with mapping_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    registry = MappingRegistry(
        sources_path=sources_path,
        mappings_dir=tmp_path,
    )

    return MappingEngine(registry=registry)


def test_mapping_engine_maps_valid_test_record(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=valid_test_record(),
        context={
            "transaction_id": "hazina-test-001",
            "raw_id": 1001,
            "run_id": 501,
            "source_metadata": {
                "source_file": "test_statement.csv",
            },
        },
    )

    assert result.success is True
    assert result.errors == []

    transaction = result.canonical_transaction

    assert transaction["transaction_id"] == "hazina-test-001"
    assert transaction["source_name"] == SOURCE_NAME
    assert transaction["source_transaction_id"] == "TEST_TXN001"
    assert transaction["source_account_id"] == "TEST_ACC001"
    assert transaction["customer_id"] == "CUST001"

    assert transaction["amount"] == Decimal("1500.00")
    assert transaction["currency"] == "KES"
    assert transaction["transaction_type"] == "PAYMENT"
    assert transaction["direction"] == "DEBIT"
    assert transaction["payment_method"] == "MPESA"
    assert transaction["status"] == "COMPLETED"

    assert transaction["fee_amount"] == Decimal("15.00")
    assert transaction["account_balance"] == Decimal("5000.00")

    assert transaction["mapping_id"] == MAPPING_ID
    assert transaction["mapping_version"] == "1.0"

    assert transaction["raw_id"] == 1001
    assert transaction["run_id"] == 501


def test_mapping_engine_normalizes_transaction_date_to_utc(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=valid_test_record(),
    )

    assert result.success is True

    assert result.canonical_transaction["transaction_date"] == (
        datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)
    )


def test_mapping_engine_rejects_missing_required_field(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    record = valid_test_record()
    del record["amount"]

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MISSING_REQUIRED_FIELD"
    assert result.errors[0].field_name == "amount"


def test_mapping_engine_rejects_unknown_transaction_type(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    record = valid_test_record()
    record["transaction_type"] = "UNKNOWN_TYPE"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def test_mapping_engine_rejects_unknown_source(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    result = engine.map_transaction(
        source_name="UNKNOWN_SOURCE",
        raw_record=valid_test_record(),
    )

    assert result.success is False
    assert result.canonical_transaction is None
    assert result.errors[0].error_code == "MAPPING_CONFIGURATION_ERROR"


def test_mapping_engine_preserves_optional_missing_fields(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    record = valid_test_record()
    record.pop("customer_id")
    record.pop("description")
    record.pop("counterparty")
    record.pop("fee")
    record.pop("balance")

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is True

    transaction = result.canonical_transaction

    assert transaction["customer_id"] is None
    assert transaction["description"] is None
    assert transaction["counterparty"] is None
    assert transaction["fee_amount"] is None
    assert transaction["account_balance"] is None


def test_mapping_engine_rejects_non_dictionary_record(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record="not-a-dictionary",
    )

    assert result.success is False
    assert result.errors[0].error_code == "INVALID_SOURCE_RECORD"


def test_mapping_engine_records_mapping_version_on_success(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=valid_test_record(),
    )

    assert result.success is True
    assert result.mapping_id == MAPPING_ID
    assert result.mapping_version == "1.0"


def test_mapping_engine_records_mapping_version_on_record_error(tmp_path):
    engine = engine_with_custom_test_mapping(tmp_path)

    record = valid_test_record()
    record["status"] = "UNKNOWN_STATUS"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is False
    assert result.mapping_id == MAPPING_ID
    assert result.mapping_version == "1.0"


def test_mapping_engine_maps_signed_negative_amount_as_debit(tmp_path):
    engine = engine_with_custom_test_mapping(
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

    record = valid_test_record()
    record["amount"] = "-1500.50"
    record["direction"] = "DR"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("1500.50")
    assert result.canonical_transaction["direction"] == "DEBIT"


def test_mapping_engine_maps_signed_positive_amount_as_credit(tmp_path):
    engine = engine_with_custom_test_mapping(
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

    record = valid_test_record()
    record["amount"] = "2500.00"
    record["direction"] = "CR"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("2500.00")
    assert result.canonical_transaction["direction"] == "CREDIT"


def test_mapping_engine_rejects_signed_amount_direction_conflict(tmp_path):
    engine = engine_with_custom_test_mapping(
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

    record = valid_test_record()
    record["amount"] = "-500"
    record["direction"] = "CR"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def test_mapping_engine_uses_configured_source_timezone(tmp_path):
    engine = engine_with_custom_test_mapping(
        tmp_path,
        {
            "mapping": {
                "source_timezone": "Africa/Nairobi",
            },
        },
    )

    record = valid_test_record()
    record["transaction_date"] = "2026-11-12T14:30:00"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is True
    assert result.canonical_transaction["transaction_date"] == (
        datetime(2026, 11, 12, 11, 30, tzinfo=timezone.utc)
    )


def test_mapping_engine_rejects_naive_timestamp_without_timezone(tmp_path):
    engine = engine_with_custom_test_mapping(
        tmp_path,
        {
            "mapping": {
                "source_timezone": None,
            },
        },
    )

    record = valid_test_record()
    record["transaction_date"] = "2026-11-12T14:30:00"

    result = engine.map_transaction(
        source_name=SOURCE_NAME,
        raw_record=record,
    )

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def _split_amount_engine(tmp_path):
    return engine_with_custom_test_mapping(
        tmp_path,
        {
            "mapping": {
                "amount_handling": "separate_debit_credit",
            },
            "remove_field_mappings": ["amount"],
            "remove_transformations": ["amount"],
            "required_fields": [
                "transaction_date",
                "currency",
                "transaction_type",
                "status",
            ],
            "amount_fields": {
                "debit": "Debit",
                "credit": "Credit",
            },
        },
    )


def test_mapping_engine_maps_separate_debit_column(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = "1250.00"
    record["Credit"] = ""

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("1250.00")
    assert result.canonical_transaction["direction"] == "DEBIT"


def test_mapping_engine_maps_separate_credit_column(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = ""
    record["Credit"] = "2750.00"

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is True
    assert result.canonical_transaction["amount"] == Decimal("2750.00")
    assert result.canonical_transaction["direction"] == "CREDIT"


def test_mapping_engine_rejects_both_separate_amount_columns_empty(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = ""
    record["Credit"] = None

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"
    assert "both are empty" in result.errors[0].error_message


def test_mapping_engine_rejects_both_separate_amount_columns_populated(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = "100.00"
    record["Credit"] = "200.00"

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"
    assert "both are populated" in result.errors[0].error_message


def test_mapping_engine_rejects_missing_separate_amount_column(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = "100.00"
    record.pop("Credit", None)

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is False
    assert result.errors[0].error_code == "MISSING_REQUIRED_FIELD"
    assert result.errors[0].field_name == "Credit"


def test_mapping_engine_rejects_invalid_separate_amount(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = "not-a-number"
    record["Credit"] = ""

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"


def test_mapping_engine_rejects_zero_separate_amount(tmp_path):
    engine = _split_amount_engine(tmp_path)
    record = valid_test_record()
    record.pop("amount")
    record["Debit"] = "0"
    record["Credit"] = ""

    result = engine.map_transaction(SOURCE_NAME, record)

    assert result.success is False
    assert result.errors[0].error_code == "MAPPING_EXECUTION_ERROR"
