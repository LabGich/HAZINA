
import pytest
from datetime import datetime
from decimal import Decimal

from src.validation.validate_transactions import validate_record


@pytest.fixture
def valid_transaction():
    return {
        "transaction_id": "TXN000001",
        "customer_id": "CUST001",
        "transaction_date": "2026-11-11T14:30:00+03:00",
        "transaction_type": "PAYMENT",
        "amount": "1500.00",
        "currency": "KES",
        "payment_method": "MPESA",
        "status": "COMPLETED",
    }


def test_valid_transaction_is_accepted(valid_transaction):
    standardized, errors = validate_record(valid_transaction)

    assert errors == []
    assert standardized is not None
    assert standardized["transaction_id"] == "TXN000001"
    assert standardized["amount"] == Decimal("1500.00")
    assert isinstance(standardized["transaction_date"], datetime)


def test_missing_transaction_id_is_rejected(valid_transaction):
    valid_transaction["transaction_id"] = ""

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert "transaction_id is required" in errors


def test_invalid_timestamp_is_rejected(valid_transaction):
    valid_transaction["transaction_date"] = "not-a-date"

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert (
        "transaction_date is not a valid ISO 8601 timestamp"
        in errors
    )


def test_timestamp_without_timezone_is_rejected(valid_transaction):
    valid_transaction["transaction_date"] = "2026-11-11T14:30:00"

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert "transaction_date must include a timezone" in errors


@pytest.mark.parametrize(
    "amount",
    ["abc", "0", "-100", "NaN", "Infinity", "100.123", "1" + "0" * 18],
)
def test_invalid_amounts_are_rejected(valid_transaction, amount):
    valid_transaction["amount"] = amount

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert errors


@pytest.mark.parametrize(
    "field,value,expected_error",
    [
        (
            "transaction_type",
            "INVALID_TYPE",
            "Invalid transaction_type: INVALID_TYPE",
        ),
        (
            "currency",
            "EUR",
            "Invalid currency: EUR",
        ),
        (
            "payment_method",
            "INVALID_METHOD",
            "Invalid payment_method: INVALID_METHOD",
        ),
        (
            "status",
            "INVALID_STATUS",
            "Invalid status: INVALID_STATUS",
        ),
    ],
)
def test_invalid_enum_values_are_rejected(
    valid_transaction,
    field,
    value,
    expected_error,
):
    valid_transaction[field] = value

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert expected_error in errors


def test_lowercase_values_are_standardized(valid_transaction):
    valid_transaction["transaction_type"] = "payment"
    valid_transaction["currency"] = "kes"
    valid_transaction["payment_method"] = "mpesa"
    valid_transaction["status"] = "completed"

    standardized, errors = validate_record(valid_transaction)

    assert errors == []
    assert standardized["transaction_type"] == "PAYMENT"
    assert standardized["currency"] == "KES"
    assert standardized["payment_method"] == "MPESA"
    assert standardized["status"] == "COMPLETED"


def test_identifier_exceeding_maximum_length_is_rejected(valid_transaction):
    valid_transaction["transaction_id"] = "T" * 51

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert "transaction_id exceeds 50 characters" in errors


def test_zero_amount_is_rejected(valid_transaction):
    valid_transaction["amount"] = "0.00"

    standardized, errors = validate_record(valid_transaction)

    assert standardized is None
    assert "amount must be greater than zero" in errors
