import pytest

from src.monitoring.pipeline_status import (
    get_pipeline_run_summary,
)


def test_pipeline_run_summary_returns_correct_details(
    database_test_context,
):

    run_id = database_test_context["run_id"]

    summary = get_pipeline_run_summary(run_id)

    assert summary["run_id"] == run_id
    assert summary["source_file"] == (
        f"{database_test_context['prefix']}.csv"
    )
    assert summary["run_status"] == "RUNNING"
    assert summary["records_received"] == 0
    assert summary["records_staged"] == 0
    assert summary["records_rejected"] == 0
    assert summary["records_duplicated"] == 0

    assert summary["records_unique_eligible"] == 0
    assert summary["records_promoted"] == 0
    assert summary["records_already_in_core"] == 0

    assert summary["unique_records"] == 0
    assert summary["exact_duplicates"] == 0
    assert summary["conflicting_duplicates"] == 0
    assert summary["rejected_records"] == 0


def test_pipeline_run_summary_rejects_unknown_run():

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        get_pipeline_run_summary(-1)