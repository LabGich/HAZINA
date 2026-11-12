
from src.deduplication.deduplicate_transactions import (
    get_transaction_signature,
)


def sample_transaction():
    return {
        "transaction_id": "TXN000001",
        "customer_id": "CUST001",
        "transaction_date": "2026-11-11T14:30:00+03:00",
        "transaction_type": "PAYMENT",
        "amount": 1500.00,
        "currency": "KES",
        "payment_method": "MPESA",
        "status": "COMPLETED",
    }


def test_identical_transactions_have_same_signature():
    transaction_one = sample_transaction()
    transaction_two = sample_transaction()

    assert (
        get_transaction_signature(transaction_one)
        == get_transaction_signature(transaction_two)
    )


def test_different_amounts_have_different_signatures():
    transaction_one = sample_transaction()
    transaction_two = sample_transaction()

    transaction_two["amount"] = 2000.00

    assert (
        get_transaction_signature(transaction_one)
        != get_transaction_signature(transaction_two)
    )


def test_different_customers_have_different_signatures():
    transaction_one = sample_transaction()
    transaction_two = sample_transaction()

    transaction_two["customer_id"] = "CUST002"

    assert (
        get_transaction_signature(transaction_one)
        != get_transaction_signature(transaction_two)
    )


def test_different_statuses_have_different_signatures():
    transaction_one = sample_transaction()
    transaction_two = sample_transaction()

    transaction_two["status"] = "FAILED"

    assert (
        get_transaction_signature(transaction_one)
        != get_transaction_signature(transaction_two)
    )
