from unittest.mock import patch
from pathlib import Path

import pytest

from server.services.pipeline_service import PipelineService


def test_get_run_details_returns_report():
    expected_report = {
        "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
        "source_executions": [],
        "mapping_errors": [],
        "validation_errors": [],
    }

    with patch(
        "server.services.pipeline_service.get_pipeline_v2_report_data",
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
        "server.services.pipeline_service.get_pipeline_v2_report_data",
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

def test_get_run_report_path_returns_existing_pdf(tmp_path):
    expected_path = tmp_path / "pipeline_run_10_report.pdf"
    expected_path.write_bytes(b"%PDF-test")

    report_data = {
        "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
        "source_executions": [],
        "mapping_errors": [],
        "validation_errors": [],
    }

    with (
        patch(
            "server.services.pipeline_service.get_pipeline_v2_report_data",
            return_value=report_data,
        ) as mock_report,
        patch(
            "server.services.pipeline_service.REPORT_DIRECTORY",
            tmp_path,
        ),
    ):
        result = PipelineService.get_run_report_path(10)

    assert result == expected_path
    mock_report.assert_called_once_with(10)


def test_get_run_report_path_rejects_missing_run(tmp_path):
    with (
        patch(
            "server.services.pipeline_service.get_pipeline_v2_report_data",
            return_value={
                "pipeline": None,
                "source_executions": [],
                "mapping_errors": [],
                "validation_errors": [],
            },
        ),
        patch(
            "server.services.pipeline_service.REPORT_DIRECTORY",
            tmp_path,
        ),
    ):
        with pytest.raises(ValueError, match="was not found"):
            PipelineService.get_run_report_path(999999)


def test_get_run_report_path_rejects_missing_pdf(tmp_path):
    with (
        patch(
            "server.services.pipeline_service.get_pipeline_v2_report_data",
            return_value={
                "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
                "source_executions": [],
                "mapping_errors": [],
                "validation_errors": [],
            },
        ),
        patch(
            "server.services.pipeline_service.REPORT_DIRECTORY",
            tmp_path,
        ),
    ):
        with pytest.raises(ValueError, match="PDF report.*not found"):
            PipelineService.get_run_report_path(10)


@pytest.mark.parametrize("run_id", [0, -1, True, "10", None])
def test_get_run_report_path_rejects_invalid_id(run_id):
    with pytest.raises(ValueError, match="positive integer"):
        PipelineService.get_run_report_path(run_id)

def test_get_run_details_passes_organization_id():
    expected_report = {
        "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
        "source_executions": [],
        "mapping_errors": [],
        "validation_errors": [],
    }

    with patch(
        "server.services.pipeline_service.get_pipeline_v2_report_data",
        return_value=expected_report,
    ) as mock_report:
        result = PipelineService.get_run_details(
            10,
            organization_id=512,
        )

    assert result["run_id"] == 10
    mock_report.assert_called_once_with(
        10,
        organization_id=512,
    )


def test_get_run_report_path_passes_organization_id(tmp_path):
    expected_path = tmp_path / "pipeline_run_10_report.pdf"
    expected_path.write_bytes(b"%PDF-test")

    report_data = {
        "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
        "source_executions": [],
        "mapping_errors": [],
        "validation_errors": [],
    }

    with (
        patch(
            "server.services.pipeline_service.get_pipeline_v2_report_data",
            return_value=report_data,
        ) as mock_report,
        patch(
            "server.services.pipeline_service.REPORT_DIRECTORY",
            tmp_path,
        ),
    ):
        result = PipelineService.get_run_report_path(
            10,
            organization_id=512,
        )

    assert result == expected_path
    mock_report.assert_called_once_with(
        10,
        organization_id=512,
    )