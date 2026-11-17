from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from hazina_pipeline.monitoring.pipeline_status import get_pipeline_v2_runs


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