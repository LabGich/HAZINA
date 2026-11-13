from datetime import datetime, timezone
from decimal import Decimal

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
