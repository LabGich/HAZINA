
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.mapping.transformations import (
    TransformationError,
    normalize_amount,
    normalize_currency,
    normalize_datetime,
    normalize_direction,
    normalize_optional,
    normalize_optional_amount,
    normalize_payment_method,
    normalize_status,
    normalize_transaction_type,
)


def test_normalize_amount_returns_decimal():
    assert normalize_amount("1,250.50") == Decimal("1250.50")


def test_normalize_amount_rejects_zero():
    with pytest.raises(TransformationError):
        normalize_amount("0")


def test_normalize_amount_rejects_negative():
    with pytest.raises(TransformationError):
        normalize_amount("-100")


def test_normalize_amount_rejects_invalid_value():
    with pytest.raises(TransformationError):
        normalize_amount("invalid")


def test_normalize_optional_amount_allows_negative_balance():
    assert normalize_optional_amount("-250.50") == Decimal("-250.50")


def test_normalize_optional_amount_returns_none_for_empty_value():
    assert normalize_optional_amount("") is None


def test_normalize_currency_uppercases_code():
    assert normalize_currency("kes") == "KES"


def test_normalize_currency_rejects_unsupported_code():
    with pytest.raises(TransformationError):
        normalize_currency("XYZ")


def test_normalize_direction_supports_bank_aliases():
    assert normalize_direction("DR") == "DEBIT"
    assert normalize_direction("CR") == "CREDIT"


def test_normalize_missing_direction_returns_unknown():
    assert normalize_direction(None) == "UNKNOWN"


def test_normalize_direction_rejects_unknown_value():
    with pytest.raises(TransformationError):
        normalize_direction("SIDEWAYS")


def test_normalize_transaction_type():
    assert normalize_transaction_type("payment") == "PAYMENT"


def test_normalize_transaction_type_rejects_unknown_value():
    with pytest.raises(TransformationError):
        normalize_transaction_type("PURCHASE")


def test_normalize_status():
    assert normalize_status("completed") == "COMPLETED"


def test_normalize_status_rejects_unknown_value():
    with pytest.raises(TransformationError):
        normalize_status("SETTLED")


def test_normalize_payment_method_supports_mpesa_alias():
    assert normalize_payment_method("M-Pesa") == "MPESA"


def test_normalize_payment_method_rejects_unknown_value():
    with pytest.raises(TransformationError):
        normalize_payment_method("CRYPTO")


def test_normalize_optional_converts_empty_string_to_none():
    assert normalize_optional("   ") is None


def test_normalize_datetime_converts_to_utc():
    value = "2026-11-13T15:00:00+03:00"

    result = normalize_datetime(value)

    assert result == datetime(
        2026, 11, 13, 12, 0, tzinfo=timezone.utc
    )


def test_normalize_datetime_rejects_naive_timestamp():
    with pytest.raises(TransformationError):
        normalize_datetime("2026-11-13T15:00:00")


def test_normalize_datetime_rejects_invalid_value():
    with pytest.raises(TransformationError):
        normalize_datetime("not-a-date")
