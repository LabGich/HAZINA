
from unittest.mock import MagicMock, patch

import pytest

from hazina_pipeline.deduplication.deduplicate_source_execution import (
    _deduplicate_source_execution,
)


RUN_ID = 100
SOURCE_EXECUTION_ID = 200
SOURCE_ID = 10
ORGANIZATION_ID = 512


def mock_database_connection():
    connection_context = MagicMock()
    connection = connection_context.__enter__.return_value

    cursor_context = connection.cursor.return_value
    cursor = cursor_context.__enter__.return_value

    return connection_context, connection, cursor


def mock_execution(
    cursor,
    status="RUNNING",
    organization_id=ORGANIZATION_ID,
):
    cursor.fetchone.return_value = (
        status,
        SOURCE_ID,
        organization_id,
    )


def valid_staging_row(
    transaction_id="TXN-001",
    source_transaction_id="PROVIDER-TX-001",
):
    return (
        501,                         # staging_id
        601,                         # raw_id
        transaction_id,
        "CUSTOMER-001",
        "2026-11-17",
        "PAYMENT",
        1500,
        "KES",
        "CREDIT",
        "BANK_TRANSFER",
        "COMPLETED",
        "Salary",
        "Employer",
        None,
        None,
        "TEST_SOURCE",
        "ACCOUNT-001",
        source_transaction_id,
        "test_mapping",
        "1.0",
        RUN_ID,
        SOURCE_EXECUTION_ID,
    )


def find_execute_call(cursor, sql_fragment):
    return next(
        call
        for call in cursor.execute.call_args_list
        if sql_fragment in call.args[0]
    )


def test_new_transaction_is_promoted_with_organization_id():
    cursor_context, connection, cursor = mock_database_connection()

    cursor.fetchone.side_effect = [
        ("RUNNING", SOURCE_ID, ORGANIZATION_ID),
        None,  # Existing provider identity
        None,  # Existing core transaction
    ]

    cursor.fetchall.return_value = [
        valid_staging_row()
    ]

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = _deduplicate_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
        )

    core_insert = find_execute_call(
        cursor,
        "INSERT INTO core.transactions",
    )
    identity_insert = find_execute_call(
        cursor,
        "INSERT INTO ops.source_transaction_identity",
    )
    audit_insert = find_execute_call(
        cursor,
        "INSERT INTO ops.transaction_audit",
    )

    assert core_insert.args[1][-1] == ORGANIZATION_ID
    assert identity_insert.args[1][-1] == ORGANIZATION_ID
    assert audit_insert.args[1][-1] == ORGANIZATION_ID

    assert result["records_examined"] == 1
    assert result["records_unique_eligible"] == 1
    assert result["records_promoted"] == 1
    assert result["records_already_in_core"] == 0

    # One new promotion produces exactly one audit INSERT.
    audit_calls = [
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO ops.transaction_audit" in call.args[0]
    ]
    assert len(audit_calls) == 1

    staging_select = find_execute_call(
        cursor,
        "FROM staging.transactions",
    )
    assert "organization_id IS NOT DISTINCT FROM %s" in staging_select.args[0]
    assert staging_select.args[1] == (
        RUN_ID,
        SOURCE_EXECUTION_ID,
        ORGANIZATION_ID,
    )


def test_parent_run_organization_is_used_for_execution_lookup():
    cursor_context, connection, cursor = mock_database_connection()

    cursor.fetchone.side_effect = [
        ("RUNNING", SOURCE_ID, ORGANIZATION_ID),
        None,
        None,
    ]
    cursor.fetchall.return_value = [
        valid_staging_row()
    ]

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        _deduplicate_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
        )

    execution_select = find_execute_call(
        cursor,
        "FROM ops.source_executions se",
    )

    assert "JOIN ops.pipeline_runs pr" in execution_select.args[0]
    assert "pr.organization_id" in execution_select.args[0]
    assert "FOR UPDATE OF se" in execution_select.args[0]
    assert execution_select.args[1] == (
        RUN_ID,
        SOURCE_EXECUTION_ID,
    )


def test_existing_provider_identity_is_scoped_to_organization():
    cursor_context, connection, cursor = mock_database_connection()

    existing_identity = (
        "TXN-001",
        "CUSTOMER-001",
        "2026-11-17",
        "PAYMENT",
        1500,
        "KES",
        "CREDIT",
        "BANK_TRANSFER",
        "COMPLETED",
    )

    cursor.fetchone.side_effect = [
        ("RUNNING", SOURCE_ID, ORGANIZATION_ID),
        existing_identity,
    ]
    cursor.fetchall.return_value = [
        valid_staging_row()
    ]

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = _deduplicate_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
        )

    identity_lookup = find_execute_call(
        cursor,
        "FROM ops.source_transaction_identity identity",
    )

    assert (
        "identity.organization_id IS NOT DISTINCT FROM %s"
        in identity_lookup.args[0]
    )
    assert (
        "core.organization_id"
        in identity_lookup.args[0]
    )
    assert identity_lookup.args[1] == (
        SOURCE_ID,
        "ACCOUNT-001",
        "PROVIDER-TX-001",
        ORGANIZATION_ID,
    )

    assert result["records_promoted"] == 0
    assert result["records_already_in_core"] == 1

    assert not any(
        "INSERT INTO core.transactions" in call.args[0]
        for call in cursor.execute.call_args_list
    )

    assert not any(
        "INSERT INTO ops.transaction_audit" in call.args[0]
        for call in cursor.execute.call_args_list
    )



def test_existing_core_transaction_is_scoped_to_organization():
    cursor_context, connection, cursor = mock_database_connection()

    existing_core = (
        "CUSTOMER-001",
        "2026-11-17",
        "PAYMENT",
        1500,
        "KES",
        "CREDIT",
        "BANK_TRANSFER",
        "COMPLETED",
    )

    cursor.fetchone.side_effect = [
        ("RUNNING", SOURCE_ID, ORGANIZATION_ID),
        existing_core,
    ]

    cursor.fetchall.return_value = [
        valid_staging_row(
            source_transaction_id=None,
        )
    ]

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = _deduplicate_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
        )

    core_lookup = find_execute_call(
        cursor,
        "FROM core.transactions",
    )

    assert "organization_id IS NOT DISTINCT FROM %s" in core_lookup.args[0]
    assert core_lookup.args[1] == (
        "TXN-001",
        ORGANIZATION_ID,
    )

    assert result["records_promoted"] == 0
    assert result["records_already_in_core"] == 1

    assert not any(
        "INSERT INTO core.transactions" in call.args[0]
        for call in cursor.execute.call_args_list
    )

    assert not any(
        "INSERT INTO ops.transaction_audit" in call.args[0]
        for call in cursor.execute.call_args_list
    )


def test_legacy_run_without_organization_is_supported():
    cursor_context, connection, cursor = mock_database_connection()

    cursor.fetchone.side_effect = [
        ("RUNNING", SOURCE_ID, None),
        None,  # Existing core transaction
    ]

    cursor.fetchall.return_value = [
        valid_staging_row(
            transaction_id="LEGACY-TXN-001",
            source_transaction_id=None,
        )
    ]

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        result = _deduplicate_source_execution(
            RUN_ID,
            SOURCE_EXECUTION_ID,
        )

    core_insert = find_execute_call(
        cursor,
        "INSERT INTO core.transactions",
    )
    audit_insert = find_execute_call(
        cursor,
        "INSERT INTO ops.transaction_audit",
    )

    assert core_insert.args[1][-1] is None
    assert audit_insert.args[1][-1] is None

    staging_select = find_execute_call(
        cursor,
        "FROM staging.transactions",
    )
    assert staging_select.args[1] == (
        RUN_ID,
        SOURCE_EXECUTION_ID,
        None,
    )

    assert result["records_promoted"] == 1
    assert result["records_already_in_core"] == 0

    # No provider ID means no source identity record.
    assert not any(
        "INSERT INTO ops.source_transaction_identity" in call.args[0]
        for call in cursor.execute.call_args_list
    )


def test_deduplication_rejects_unknown_source_execution():
    cursor_context, connection, cursor = mock_database_connection()
    cursor.fetchone.return_value = None

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        with pytest.raises(
            ValueError,
            match="does not belong",
        ):
            _deduplicate_source_execution(
                RUN_ID,
                SOURCE_EXECUTION_ID,
            )


def test_deduplication_requires_running_execution():
    cursor_context, connection, cursor = mock_database_connection()
    mock_execution(cursor, status="PENDING")

    with patch(
        "hazina_pipeline.deduplication.deduplicate_source_execution.get_database_connection",
        return_value=cursor_context,
    ):
        with pytest.raises(
            ValueError,
            match="must be RUNNING",
        ):
            _deduplicate_source_execution(
                RUN_ID,
                SOURCE_EXECUTION_ID,
            )


@pytest.mark.parametrize(
    ("run_id", "source_execution_id", "message"),
    [
        (0, SOURCE_EXECUTION_ID, "run_id"),
        (RUN_ID, 0, "source_execution_id"),
    ],
)
def test_deduplication_rejects_invalid_ids(
    run_id,
    source_execution_id,
    message,
):
    with pytest.raises(ValueError, match=message):
        _deduplicate_source_execution(
            run_id,
            source_execution_id,
        )
