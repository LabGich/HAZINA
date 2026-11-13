
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


class TransformationError(ValueError):
    """Raised when a source value cannot be safely normalized."""


VALID_DIRECTIONS = {"DEBIT", "CREDIT", "UNKNOWN"}

VALID_TRANSACTION_TYPES = {
    "PAYMENT",
    "DEPOSIT",
    "WITHDRAWAL",
    "TRANSFER",
    "REFUND",
    "FEE",
    "REVERSAL",
}

VALID_STATUSES = {
    "INITIATED",
    "PENDING",
    "COMPLETED",
    "FAILED",
    "REVERSED",
}

VALID_CURRENCIES = {
    "KES", "USD", "EUR", "GBP", "TZS", "UGX", "ZAR",
}


def normalize_optional(value: Any) -> Any | None:
    """Convert empty optional values to None."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

    return value


def normalize_amount(value: Any) -> Decimal:
    """Convert a financial amount into a positive Decimal."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Amount is required.")

    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise TransformationError(f"Invalid financial amount: {value}")

    if not amount.is_finite() or amount <= 0:
        raise TransformationError(
            f"Amount must be a finite positive number: {value}"
        )

    return amount.quantize(Decimal("0.01"))


def normalize_optional_amount(value: Any) -> Decimal | None:
    """Normalize an optional financial amount."""
    value = normalize_optional(value)

    if value is None:
        return None

    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise TransformationError(
            f"Invalid optional financial amount: {value}"
        )

    if not amount.is_finite():
        raise TransformationError(
            f"Optional financial amount must be finite: {value}"
        )

    return amount.quantize(Decimal("0.01"))


def normalize_currency(value: Any) -> str:
    """Normalize a supported ISO currency code."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Currency is required.")

    currency = str(value).strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        raise TransformationError(f"Invalid currency code: {value}")

    if currency not in VALID_CURRENCIES:
        raise TransformationError(
            f"Unsupported currency code: {currency}"
        )

    return currency


def normalize_direction(value: Any) -> str:
    """Normalize transaction direction."""
    value = normalize_optional(value)

    if value is None:
        return "UNKNOWN"

    direction = str(value).strip().upper()

    aliases = {
        "DR": "DEBIT",
        "DEBIT": "DEBIT",
        "CR": "CREDIT",
        "CREDIT": "CREDIT",
        "UNKNOWN": "UNKNOWN",
    }

    normalized = aliases.get(direction)

    if normalized not in VALID_DIRECTIONS:
        raise TransformationError(
            f"Unknown transaction direction: {value}"
        )

    return normalized


def normalize_transaction_type(value: Any) -> str:
    """Normalize supported transaction types."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Transaction type is required.")

    transaction_type = str(value).strip().upper()

    if transaction_type not in VALID_TRANSACTION_TYPES:
        raise TransformationError(
            f"Unknown transaction type: {value}"
        )

    return transaction_type


def normalize_status(value: Any) -> str:
    """Normalize supported transaction statuses."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Transaction status is required.")

    status = str(value).strip().upper()

    if status not in VALID_STATUSES:
        raise TransformationError(
            f"Unknown transaction status: {value}"
        )

    return status


def normalize_payment_method(value: Any) -> str:
    """Normalize supported payment methods."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Payment method is required.")

    payment_method = str(value).strip().upper()

    aliases = {
        "MPESA": "MPESA",
        "M-PESA": "MPESA",
        "BANK_TRANSFER": "BANK_TRANSFER",
        "BANK TRANSFER": "BANK_TRANSFER",
        "CARD": "CARD",
        "CASH": "CASH",
        "DIGITAL_WALLET": "DIGITAL_WALLET",
        "USSD": "USSD",
        "AGENT": "AGENT",
        "OTHER": "OTHER",
    }

    normalized = aliases.get(payment_method)

    if normalized is None:
        raise TransformationError(
            f"Unknown payment method: {value}"
        )

    return normalized


def normalize_datetime(value: Any) -> datetime:
    """Convert a supported date/time value into timezone-aware UTC."""
    value = normalize_optional(value)

    if value is None:
        raise TransformationError("Transaction date is required.")

    if isinstance(value, datetime):
        parsed = value

    elif isinstance(value, str):
        text = value.strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise TransformationError(
                f"Invalid date/time format: {value}"
            )

    else:
        raise TransformationError(
            f"Unsupported date/time value: {value}"
        )

    if parsed.tzinfo is None:
        raise TransformationError(
            "Transaction date must include timezone information."
        )

    return parsed.astimezone(timezone.utc)
