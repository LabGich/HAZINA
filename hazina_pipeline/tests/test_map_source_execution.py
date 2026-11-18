
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hazina_pipeline.mapping.map_source_execution import (
    SourceMappingError,
    map_source_execution,
)


SOURCE_NAME = "TEST_SOURCE"
RUN_ID = 100
SOURCE_EXECUTION_ID = 200
ORGANIZATION_ID = 512
MAPPING_ID = "test_mapping"
MAPPING_VERSION = "1.0"


def mock_database_connection():
    connection_context = MagicMock()
    connection = connection_context.__enter__.return_value

    cursor_context = connection.cursor.return_value
    cursor = cursor_context.__enter__.return_value
    cursor.rowcount = 1

    return connection_context, connection, cursor


def mock_execution(
    cursor,
    source_name=SOURCE_NAME,
    status="RUNNING",
    mapping_id=MAPPING_ID,
    mapping_version=MAPPING_VERSION,
    organization_id=ORGANIZATION_ID,
):
    cursor.fetchone.return_value = (
        source_name,
        status,
        mapping_id,
        mapping_version,
        organization_id,
    )


def valid_transaction(transaction_id="PROVIDER-TX-001"):
    return {
        "transaction_id": transaction_id,
        "customer_id": "CUSTOMER-001",
        "transaction_date": "2026-11-17",
        "transaction_type": "PAYMENT",
        "amount": 1500,
        "currency": "KES",
        "payment_method": "BANK_TRANSFER",
        "status": "COMPLETED",
        "source_transaction_id": "PROVIDER-TX-001",
        "source_account_id": "ACCOUNT-001",
        "direction": "CREDIT",
        "description": "Salary",
        "counterparty": "Employer",
        "fee_amount": None,
        "account_balance": None,
        "source_metadata": {"reference": "REF-001"},
    }


def successful_mapping(transaction=None):
    return SimpleNamespace(
        success=True,
        canonical_transaction=transaction or valid_transaction(),
        errors=[],
        mapping_id=MAPPING_ID,
        mapping_version=MAPPING_VERSION,
    )


def mock_mapping_engine(result=None):
    engine = MagicMock()
    engine.map_transaction.return_value = (
        result or successful_mapping()
    )
    return engine


def test_mapping_stages_transaction_with_organization_id():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor)

    cursor.fetchall.return_value = [
        (
            501,
            {"transaction_id": "PROVIDER-TX-001"},
            {"reference": "RAW-REF-001"},
        )
    ]

    engine = mock_mapping_engine()

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = map_source_execution(
            run_id=RUN_ID,
            source_execution_id=SOURCE_EXECUTION_ID,
            source_name=SOURCE_NAME,
            mapping_id=MAPPING_ID,
            mapping_version=MAPPING_VERSION,
            mapping_engine=engine,
        )

    insert_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO staging.transactions" in call.args[0]
    ]

    assert len(insert_calls) == 1

    parameters = insert_calls[0].args[1]

    assert parameters[0] == "PROVIDER-TX-001"
    assert parameters[8] == RUN_ID
    assert parameters[9] == ORGANIZATION_ID
    assert parameters[10] == 501
    assert parameters[11] == SOURCE_NAME
    assert parameters[12] == "PROVIDER-TX-001"
    assert parameters[22] == SOURCE_EXECUTION_ID

    assert result["records_examined"] == 1
    assert result["records_mapped"] == 1
    assert result["records_rejected"] == 0

    engine.map_transaction.assert_called_once()


def test_mapping_supports_legacy_run_without_organization():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor, organization_id=None)

    cursor.fetchall.return_value = [
        (
            502,
            {"transaction_id": "LEGACY-TX-001"},
            {},
        )
    ]

    engine = mock_mapping_engine(
        successful_mapping(valid_transaction("LEGACY-TX-001"))
    )

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        map_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            MAPPING_ID,
            MAPPING_VERSION,
            engine,
        )

    insert_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO staging.transactions" in call.args[0]
    ]

    assert len(insert_calls) == 1
    assert insert_calls[0].args[1][9] is None


def test_mapping_generates_transaction_id_when_missing():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor)

    cursor.fetchall.return_value = [
        (503, {"amount": "1500"}, {})
    ]

    transaction = valid_transaction(transaction_id=None)
    engine = mock_mapping_engine(successful_mapping(transaction))

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        map_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            MAPPING_ID,
            MAPPING_VERSION,
            engine,
        )

    insert_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO staging.transactions" in call.args[0]
    ]

    assert len(insert_calls) == 1

    generated_id = insert_calls[0].args[1][0]

    assert isinstance(generated_id, str)
    assert len(generated_id) == 36


def test_mapping_records_mapping_failure():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor)

    cursor.fetchall.return_value = [
        (504, {"invalid": "record"}, {})
    ]

    engine = mock_mapping_engine(
        SimpleNamespace(
            success=False,
            canonical_transaction=None,
            errors=[],
            mapping_id=MAPPING_ID,
            mapping_version=MAPPING_VERSION,
        )
    )

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = map_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
            SOURCE_NAME,
            MAPPING_ID,
            MAPPING_VERSION,
            engine,
        )

    error_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO ops.mapping_errors" in call.args[0]
    ]

    assert len(error_calls) == 1
    assert error_calls[0].args[1][0:3] == (
        RUN_ID,
        SOURCE_EXECUTION_ID,
        504,
    )
    assert error_calls[0].args[1][5] == "MAPPING_EXECUTION_ERROR"

    assert result["records_mapped"] == 0
    assert result["records_rejected"] == 1


def test_mapping_rejects_unknown_source_execution():
    cursor_context, connection, cursor = mock_database_connection()
    cursor.fetchone.return_value = None

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        with pytest.raises(
            SourceMappingError,
            match="does not belong",
        ):
            map_source_execution(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                MAPPING_ID,
                MAPPING_VERSION,
                mock_mapping_engine(),
            )


def test_mapping_requires_running_execution():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor, status="PENDING")

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        with pytest.raises(
            SourceMappingError,
            match="must be RUNNING",
        ):
            map_source_execution(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                MAPPING_ID,
                MAPPING_VERSION,
                mock_mapping_engine(),
            )


def test_mapping_rejects_source_name_mismatch():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor, source_name="OTHER_SOURCE")

    with patch(
        "hazina_pipeline.mapping.map_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        with pytest.raises(
            SourceMappingError,
            match="does not match",
        ):
            map_source_execution(
                RUN_ID,
                SOURCE_EXECUTION_ID,
                SOURCE_NAME,
                MAPPING_ID,
                MAPPING_VERSION,
                mock_mapping_engine(),
            )
