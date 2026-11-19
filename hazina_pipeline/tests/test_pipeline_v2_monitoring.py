from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from hazina_pipeline.monitoring.pipeline_status import get_pipeline_v2_runs
from hazina_pipeline.monitoring.pipeline_status import (
    get_pipeline_v2_dashboard_summary,
)


def test_get_pipeline_v2_runs_returns_paginated_results():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (3,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]

    cursor.fetchall.return_value = [
        (3, "file3.csv", None, None, "SUCCESS", 10, 10, 0, 10, "FILE", "API"),
        (2, "file2.csv", None, None, "FAILED", 5, 0, 5, 0, "FILE", "API"),
    ]

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(limit=2, offset=1)

    assert result["total"] == 3
    assert result["limit"] == 2
    assert result["offset"] == 1
    assert len(result["items"]) == 2
    assert result["items"][0]["run_id"] == 3
    assert result["items"][1]["run_id"] == 2


@pytest.mark.parametrize(
    ("limit", "offset"),
    [
        (0, 0),
        (101, 0),
        (-1, 0),
        (True, 0),
        (20, -1),
        (20, True),
    ],
)
def test_get_pipeline_v2_runs_rejects_invalid_pagination(
    limit,
    offset,
):
    with pytest.raises(ValueError):
        get_pipeline_v2_runs(limit=limit, offset=offset)

def test_get_pipeline_v2_runs_filters_by_organization():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (2,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]
    cursor.fetchall.return_value = [
        (3, "file3.csv", None, None, "SUCCESS", 10, 10, 0, 10, "FILE", "API"),
    ]

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(
            limit=10,
            offset=0,
            organization_id=512,
        )

    assert result["total"] == 2
    assert len(result["items"]) == 1

    execute_calls = cursor.execute.call_args_list

    assert len(execute_calls) == 2

    count_sql = " ".join(execute_calls[0].args[0].split())
    list_sql = " ".join(execute_calls[1].args[0].split())

    assert "WHERE organization_id = %s" in count_sql
    assert execute_calls[0].args[1] == (512,)

    assert "WHERE organization_id = %s" in list_sql
    assert execute_calls[1].args[1] == (512, 10, 0)


def test_get_pipeline_v2_dashboard_summary_returns_metrics():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (12, 850, 9, 2)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "total_runs",
            "records_processed",
            "successful_runs",
            "pending_executions",
        )
    ]

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_dashboard_summary(
            organization_id=512,
        )

    assert result == {
        "total_runs": 12,
        "records_processed": 850,
        "successful_runs": 9,
        "pending_executions": 2,
    }

    cursor.execute.assert_called_once()

    sql = " ".join(cursor.execute.call_args.args[0].split())

    assert "FROM ops.pipeline_runs" in sql
    assert "WHERE organization_id = %s" in sql
    assert cursor.execute.call_args.args[1] == (512,)


def test_get_pipeline_v2_dashboard_summary_returns_zero_metrics():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (0, 0, 0, 0)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "total_runs",
            "records_processed",
            "successful_runs",
            "pending_executions",
        )
    ]

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_dashboard_summary(
            organization_id=512,
        )

    assert result == {
        "total_runs": 0,
        "records_processed": 0,
        "successful_runs": 0,
        "pending_executions": 0,
    }


@pytest.mark.parametrize(
    "organization_id",
    [0, -1, True, "512", None],
)
def test_get_pipeline_v2_dashboard_summary_rejects_invalid_organization_id(
    organization_id,
):
    with pytest.raises(ValueError, match="positive integer"):
        get_pipeline_v2_dashboard_summary(organization_id)


@pytest.mark.parametrize(
    "status",
    [
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "FAILED",
        "RUNNING",
        "CANCELLED",
    ],
)
def test_get_pipeline_v2_runs_filters_by_status(status):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (2,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]
    cursor.fetchall.return_value = []

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(status=status)

    assert result["total"] == 2

    execute_calls = cursor.execute.call_args_list
    assert len(execute_calls) == 2

    for call in execute_calls:
        sql = " ".join(call.args[0].split())
        assert "WHERE run_status = %s" in sql
        assert call.args[1][0] == status

    assert execute_calls[0].args[1] == (status,)
    assert execute_calls[1].args[1] == (status, 20, 0)


def test_get_pipeline_v2_runs_filters_by_organization_and_status():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (1,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]
    cursor.fetchall.return_value = []

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(
            limit=10,
            offset=5,
            organization_id=512,
            status="SUCCESS",
        )

    assert result["total"] == 1

    execute_calls = cursor.execute.call_args_list

    assert execute_calls[0].args[1] == (512, "SUCCESS")
    assert execute_calls[1].args[1] == (512, "SUCCESS", 10, 5)

    for call in execute_calls:
        sql = " ".join(call.args[0].split())
        assert "organization_id = %s" in sql
        assert "run_status = %s" in sql


@pytest.mark.parametrize(
    "status",
    [
        "",
        "UNKNOWN",
        "PENDING",
        123,
        True,
    ],
)
def test_get_pipeline_v2_runs_rejects_invalid_status(status):
    with pytest.raises(ValueError, match="status|Invalid status"):
        get_pipeline_v2_runs(status=status)


def test_get_pipeline_v2_runs_filters_by_source_name():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (2,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]
    cursor.fetchall.return_value = []

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(
            limit=10,
            offset=5,
            source_name="equity",
        )

    assert result["total"] == 2

    execute_calls = cursor.execute.call_args_list
    assert len(execute_calls) == 2

    for call in execute_calls:
        sql = " ".join(call.args[0].split())

        assert "EXISTS (" in sql
        assert "ops.source_executions" in sql
        assert "ops.source_registry" in sql
        assert "s.source_name = %s" in sql

    assert execute_calls[0].args[1] == ("EQUITY",)
    assert execute_calls[1].args[1] == ("EQUITY", 10, 5)


def test_get_pipeline_v2_runs_filters_by_organization_status_and_source():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (1,)
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "run_id",
            "source_file",
            "started_at",
            "completed_at",
            "run_status",
            "records_received",
            "records_loaded",
            "records_rejected",
            "records_promoted",
            "run_type",
            "triggered_by",
        )
    ]
    cursor.fetchall.return_value = []

    with patch(
        "hazina_pipeline.monitoring.pipeline_status.get_database_connection"
    ) as mock_connection:
        mock_connection.return_value.__enter__.return_value = connection

        result = get_pipeline_v2_runs(
            limit=10,
            offset=5,
            organization_id=512,
            status="SUCCESS",
            source_name=" equity ",
        )

    assert result["total"] == 1

    execute_calls = cursor.execute.call_args_list

    assert execute_calls[0].args[1] == (
        512,
        "SUCCESS",
        "EQUITY",
    )
    assert execute_calls[1].args[1] == (
        512,
        "SUCCESS",
        "EQUITY",
        10,
        5,
    )

    for call in execute_calls:
        sql = " ".join(call.args[0].split())

        assert "organization_id = %s" in sql
        assert "run_status = %s" in sql
        assert "EXISTS (" in sql


@pytest.mark.parametrize(
    "source_name",
    [
        "",
        "   ",
        123,
        True,
    ],
)
def test_get_pipeline_v2_runs_rejects_invalid_source_name(source_name):
    with pytest.raises(ValueError, match="source_name"):
        get_pipeline_v2_runs(source_name=source_name)
