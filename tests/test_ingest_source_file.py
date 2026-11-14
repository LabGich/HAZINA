
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.ingest_source_file import (
    SourceIngestionError,
    ingest_source_file,
)


SOURCE_NAME = "TEST_SOURCE"
RUN_ID = 100
SOURCE_EXECUTION_ID = 200


def mock_database_connection():
    connection_context = MagicMock()
    connection = connection_context.__enter__.return_value

    cursor_context = connection.cursor.return_value
    cursor = cursor_context.__enter__.return_value
    cursor.rowcount = 1

    return connection_context, connection, cursor


def mock_reader(records=None):
    reader = MagicMock()

    reader.read.return_value = {
        "source_name": SOURCE_NAME,
        "source_type": "FILE",
        "file_name": "test_statement.csv",
        "file_format": "CSV",
        "records_received": len(records or []),
        "records_returned": len(records or []),
        "records": records or [],
        "metadata": {},
    }

    return reader


def mock_execution(cursor, source_name=SOURCE_NAME, status="RUNNING"):
    cursor.fetchone.return_value = (source_name, status)


def test_ingest_source_file_persists_raw_records():
    records = [
        {
            "transaction_id": "TX001",
            "amount": "1500.00",
            "currency": "KES",
            "description": "Salary",
        },
        {
            "transaction_id": "TX002",
            "amount": "500.00",
            "currency": "KES",
            "description": "Shopping",
        },
    ]

    reader = mock_reader(records)
    connection_context, connection, cursor = (
        mock_database_connection()
    )
    mock_execution(cursor)

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        result = ingest_source_file(
            run_id=RUN_ID,
            source_execution_id=SOURCE_EXECUTION_ID,
            source_name=SOURCE_NAME,
            file_path=Path("test_statement.csv"),
            source_file_reader=reader,
        )

    assert result["run_id"] == RUN_ID
    assert result["source_execution_id"] == SOURCE_EXECUTION_ID
    assert result["source_name"] == SOURCE_NAME
    assert result["records_received"] == 2
    assert result["records_loaded"] == 2

    reader.read.assert_called_once()

    insert_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO raw.transactions" in call.args[0]
    ]

    assert len(insert_calls) == 2

    first_parameters = insert_calls[0].args[1]

    assert first_parameters[0] == "TX001"
    assert first_parameters[9] == RUN_ID
    assert first_parameters[10].obj == records[0]
    assert first_parameters[11] == SOURCE_NAME
    assert first_parameters[12] == "FILE"
    assert first_parameters[17] == SOURCE_EXECUTION_ID

    connection_context.__exit__.assert_called_once_with(
        None,
        None,
        None,
    )


def test_ingest_source_file_updates_execution_counters():
    records = [
        {"transaction_id": "TX001"},
        {"transaction_id": "TX002"},
        {"transaction_id": "TX003"},
    ]

    reader = mock_reader(records)
    reader.read.return_value["records_received"] = 5

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    mock_execution(cursor)

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        result = ingest_source_file(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            "test_statement.csv",
            reader,
        )

    counter_calls = [
        call
        for call in cursor.execute.call_args_list
        if "UPDATE ops.source_executions" in call.args[0]
    ]

    assert len(counter_calls) == 1
    assert counter_calls[0].args[1] == (
        5,
        3,
        SOURCE_EXECUTION_ID,
    )

    assert result["records_received"] == 5
    assert result["records_loaded"] == 3


def test_ingest_rejects_unknown_source_execution():
    reader = mock_reader([{"transaction_id": "TX001"}])

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    cursor.fetchone.return_value = None

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        with pytest.raises(
            SourceIngestionError,
            match="does not belong",
        ):
            ingest_source_file(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                "test_statement.csv",
                reader,
            )

    connection_context.__exit__.assert_called_once()
    assert connection_context.__exit__.call_args.args[0] is not None


def test_ingest_rejects_source_name_mismatch():
    reader = mock_reader([{"transaction_id": "TX001"}])

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    mock_execution(cursor, source_name="OTHER_SOURCE")

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        with pytest.raises(
            SourceIngestionError,
            match="does not match",
        ):
            ingest_source_file(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                "test_statement.csv",
                reader,
            )


def test_ingest_requires_running_execution():
    reader = mock_reader([{"transaction_id": "TX001"}])

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    mock_execution(cursor, status="PENDING")

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        with pytest.raises(
            SourceIngestionError,
            match="must be RUNNING",
        ):
            ingest_source_file(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                "test_statement.csv",
                reader,
            )


def test_ingest_rejects_non_dictionary_records():
    reader = mock_reader(["invalid record"])

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    mock_execution(cursor)

    with patch(
        "src.ingestion.ingest_source_file.get_database_connection",
        return_value=connection_context,
    ):
        with pytest.raises(
            SourceIngestionError,
            match="must be a dictionary",
        ):
            ingest_source_file(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                "test_statement.csv",
                reader,
            )


def test_ingest_wraps_file_reader_errors():
    reader = MagicMock()
    reader.read.side_effect = ValueError("Unsupported file format")

    with pytest.raises(
        SourceIngestionError,
        match="Unable to read",
    ):
        ingest_source_file(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            "test_statement.csv",
            reader,
        )


def test_ingest_rejects_empty_source_file():
    reader = mock_reader([])

    with pytest.raises(
        SourceIngestionError,
        match="No records available",
    ):
        ingest_source_file(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            "test_statement.csv",
            reader,
        )
