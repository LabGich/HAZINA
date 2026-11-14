#unified file ingestion test

from pathlib import Path

import pytest

from src.ingestion.source_file_reader import (
    SourceFileReader,
    SourceFileReaderError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample" / "source_samples"


@pytest.fixture
def reader():
    return SourceFileReader()


@pytest.mark.parametrize(
    "file_name",
    [
        "equity_statement_sample.csv",
        "equity_statement_sample.json",
        "kcb_statement_sample.csv",
        "kcb_statement_sample.json",
        "coop_statement_sample.csv",
        "coop_statement_sample.json",
        "ncba_statement_sample.csv",
        "ncba_statement_sample.json",
    ],
)
def test_bank_provider_samples(reader, file_name):
    result = reader.read("BANK", SAMPLE_DIR / file_name)

    assert result["source_name"] == "BANK"
    assert result["source_type"] == "FILE"
    assert result["file_name"] == file_name
    assert result["records_received"] == 5
    assert result["records_returned"] == 5
    assert len(result["records"]) == 5
    assert all(isinstance(record, dict) for record in result["records"])
    assert result["metadata"] == {}


@pytest.mark.parametrize(
    "file_name",
    [
        "explore_my_data_1000.csv",
        "explore_my_data_1000.json",
        "explore_my_data_1000.jsonl",
        "explore_my_data_1000.xlsx",
        "explore_my_data_1000.parquet",
    ],
)
def test_explore_my_data_supported_formats(reader, file_name):
    result = reader.read(
        "EXPLORE_MY_DATA",
        SAMPLE_DIR / file_name,
    )

    assert result["source_name"] == "EXPLORE_MY_DATA"
    assert result["records_received"] == 1000
    assert result["records_returned"] == 1000
    assert len(result["records"]) == 1000
    assert all(isinstance(record, dict) for record in result["records"])


def test_utilly_adapter_preserves_statement_metadata(reader):
    result = reader.read(
        "UTILLY",
        SAMPLE_DIR / "utilly_bank_statement.csv",
    )

    assert result["source_name"] == "UTILLY"
    assert result["records_received"] == 33
    assert result["records_returned"] == 31
    assert len(result["records"]) == 31

    assert result["metadata"]["source_name"] == "UTILLY"
    assert result["metadata"]["source_account_id"] == "XXXXXX0427"
    assert result["metadata"]["statement_period_start"] == "2026-09-01"
    assert result["metadata"]["statement_period_end"] == "2026-09-30"


def test_utilly_records_include_account_identifier(reader):
    result = reader.read(
        "UTILLY",
        SAMPLE_DIR / "utilly_bank_statement.csv",
    )

    assert all(
        record["account_id"] == "XXXXXX0427"
        for record in result["records"]
    )


def test_api_source_is_rejected(reader):
    with pytest.raises(
        SourceFileReaderError,
        match="not file-based",
    ):
        reader.read("STRIPE", "unused.json")


def test_missing_file_is_rejected(reader, tmp_path):
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(
        SourceFileReaderError,
        match="Source file not found",
    ):
        reader.read("BANK", missing_file)


def test_unsupported_file_format_is_rejected(reader, tmp_path):
    unsupported_file = tmp_path / "statement.txt"
    unsupported_file.write_text(
        "sample data",
        encoding="utf-8",
    )

    with pytest.raises(
        SourceFileReaderError,
        match="does not support TXT files",
    ):
        reader.read("BANK", unsupported_file)


def test_empty_source_file_is_rejected(reader, tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text(
        "Date,Description\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SourceFileReaderError,
        match="No records found",
    ):
        reader.read("BANK", empty_file)


def test_source_name_is_normalized(reader):
    result = reader.read(
        "bank",
        SAMPLE_DIR / "equity_statement_sample.csv",
    )

    assert result["source_name"] == "BANK"
