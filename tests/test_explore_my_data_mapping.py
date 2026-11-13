
import csv
from decimal import Decimal
from datetime import timezone
from pathlib import Path

from src.mapping.mapping_engine import MappingEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "sample"
    /"source_samples"
    / "explore_my_data_1000.csv"
)

CATEGORY_TO_TYPE = {
    "Income": "DEPOSIT",
    "Transfer": "TRANSFER",
    "Coffee": "PAYMENT",
    "Dining": "PAYMENT",
    "Fuel": "PAYMENT",
    "Groceries": "PAYMENT",
    "Health": "PAYMENT",
    "Housing": "PAYMENT",
    "Shopping": "PAYMENT",
    "Software": "PAYMENT",
    "Subscriptions": "PAYMENT",
    "Transport": "PAYMENT",
    "Travel": "PAYMENT",
    "Utilities": "PAYMENT",
}


def load_dataset():
    with DATASET_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def test_explore_my_data_dataset_contains_1000_records():
    records = load_dataset()

    assert len(records) == 1000


def test_explore_my_data_all_records_map_successfully():
    engine = MappingEngine()
    records = load_dataset()

    for index, record in enumerate(records):
        result = engine.map_transaction(
            source_name="EXPLORE_MY_DATA",
            raw_record=record,
        )

        assert result.success is True, (
            f"Record {index + 1} failed: {result.errors}"
        )


def test_explore_my_data_signed_amounts_map_correctly():
    engine = MappingEngine()

    for record in load_dataset():
        result = engine.map_transaction(
            source_name="EXPLORE_MY_DATA",
            raw_record=record,
        )

        assert result.success is True

        transaction = result.canonical_transaction
        source_amount = Decimal(record["amount"])

        assert transaction["amount"] == abs(source_amount)

        expected_direction = (
            "DEBIT" if source_amount < 0 else "CREDIT"
        )

        assert transaction["direction"] == expected_direction


def test_explore_my_data_categories_map_correctly():
    engine = MappingEngine()

    for record in load_dataset():
        result = engine.map_transaction(
            source_name="EXPLORE_MY_DATA",
            raw_record=record,
        )

        assert result.success is True

        expected_type = CATEGORY_TO_TYPE[record["category"]]

        assert (
            result.canonical_transaction["transaction_type"]
            == expected_type
        )


def test_explore_my_data_dates_are_utc():
    engine = MappingEngine()

    for record in load_dataset():
        result = engine.map_transaction(
            source_name="EXPLORE_MY_DATA",
            raw_record=record,
        )

        assert result.success is True

        transaction_date = (
            result.canonical_transaction["transaction_date"]
        )

        assert transaction_date.tzinfo is not None
        assert transaction_date.utcoffset().total_seconds() == 0
        assert transaction_date.tzinfo == timezone.utc


def test_explore_my_data_preserves_source_identity():
    engine = MappingEngine()

    for record in load_dataset():
        result = engine.map_transaction(
            source_name="EXPLORE_MY_DATA",
            raw_record=record,
        )

        assert result.success is True

        transaction = result.canonical_transaction

        assert (
            transaction["source_transaction_id"]
            == record["transaction_id"]
        )

        assert (
            transaction["source_account_id"]
            == record["account_id"]
        )

        assert transaction["currency"] == "USD"
        assert transaction["status"] == "COMPLETED"
