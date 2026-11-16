from unittest.mock import patch

import pytest

from src.api.services.pipeline_service import PipelineService


def test_get_run_details_returns_report():
    expected_report = {
        "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
        "source_executions": [],
        "mapping_errors": [],
        "validation_errors": [],
    }

    with patch(
        "src.api.services.pipeline_service.get_pipeline_v2_report_data",
        return_value=expected_report,
    ) as mock_report:
        result = PipelineService.get_run_details(10)

    assert result == {
        "run_id": 10,
        "report": expected_report,
    }
    mock_report.assert_called_once_with(10)


def test_get_run_details_rejects_missing_run():
    with patch(
        "src.api.services.pipeline_service.get_pipeline_v2_report_data",
        return_value={
            "pipeline": None,
            "source_executions": [],
            "mapping_errors": [],
            "validation_errors": [],
        },
    ):
        with pytest.raises(ValueError, match="was not found"):
            PipelineService.get_run_details(999999)


@pytest.mark.parametrize("run_id", [0, -1, True, "10", None])
def test_get_run_details_rejects_invalid_id(run_id):
    with pytest.raises(ValueError, match="positive integer"):
        PipelineService.get_run_details(run_id)