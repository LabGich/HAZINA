import pytest

from fastapi.testclient import TestClient

from server.main import app
from server.routers import sources, mappings, pipeline
from server.services.source_service import SourceService
from server.services.mapping_service import MappingService


from server.auth.dependencies import get_current_auth_context


client = TestClient(app)

@pytest.fixture(autouse=True)
def authenticated_test_client():
    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_current_auth_context] = lambda: {
        "user_id": 1,
        "organization_id": 1,
        "role_code": "ADMIN",
    }

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "hazina-api",
    }


def test_list_sources_endpoint(monkeypatch):
    expected = {
        "count": 1,
        "sources": [
            {
                "source_name": "EQUITY",
                "source_type": "FILE",
                "description": "Equity Bank statements",
                "supported_formats": ["CSV", "JSON"],
                "default_mapping": {
                    "mapping_id": "equity_csv_v1",
                    "mapping_version": "1.0",
                },
            }
        ],
    }

    monkeypatch.setattr(
        sources,
        "SourceService",
        lambda: type(
            "FakeService",
            (),
            {"list_sources": lambda self: expected},
        )(),
    )

    response = client.get("/sources")

    assert response.status_code == 200
    assert response.json() == expected


def test_list_mappings_endpoint(monkeypatch):
    expected = {
        "source_name": "EQUITY",
        "count": 1,
        "mappings": [
            {
                "mapping_id": "equity_csv_v1",
                "mapping_version": "1.0",
                "description": "Equity CSV mapping",
                "is_default": True,
            }
        ],
    }

    monkeypatch.setattr(
        mappings,
        "MappingService",
        lambda: type(
            "FakeService",
            (),
            {"list_mappings": lambda self, source_name: expected},
        )(),
    )

    response = client.get(
        "/mappings",
        params={"source_name": "EQUITY"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_list_mappings_requires_source_name():
    response = client.get("/mappings")

    assert response.status_code == 422

def test_list_pipeline_runs():
    from unittest.mock import patch

    mock_result = {
        "items": [
            {
                "run_id": 10,
                "source_file": "equity.csv",
                "started_at": None,
                "completed_at": None,
                "run_status": "SUCCESS",
                "records_received": 20,
                "records_loaded": 20,
                "records_rejected": 0,
                "records_promoted": 20,
                "run_type": "FILE",
                "triggered_by": "API",
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }

    with patch(
        "server.routers.pipeline.PipelineService.list_runs",
        return_value=mock_result,
    ) as mock_list:
        response = client.get("/pipeline-runs")

    assert response.status_code == 200
    assert response.json() == mock_result
    mock_list.assert_called_once_with(
        limit=20,
        offset=0,
        organization_id=1,
    )


def test_list_pipeline_runs_validates_pagination():
    response = client.get("/pipeline-runs?limit=101&offset=0")
    assert response.status_code == 422

    response = client.get("/pipeline-runs?limit=20&offset=-1")
    assert response.status_code == 422

def test_get_pipeline_run_details(monkeypatch):
    expected = {
        "run_id": 10,
        "report": {
            "pipeline": {"run_id": 10, "run_status": "SUCCESS"},
            "source_executions": [],
            "mapping_errors": [],
            "validation_errors": [],
        },
    }

    calls = []

    def fake_get_run_details(run_id, organization_id=None):
        calls.append((run_id, organization_id))
        return expected

    monkeypatch.setattr(
        pipeline.PipelineService,
        "get_run_details",
        staticmethod(fake_get_run_details),
    )

    response = client.get("/pipeline-runs/10")

    assert response.status_code == 200
    assert response.json() == expected
    assert calls == [(10, 1)]


def test_get_pipeline_run_details_not_found(monkeypatch):
    def raise_not_found(run_id, organization_id=None):
        raise ValueError(f"Pipeline run {run_id} was not found.")

    monkeypatch.setattr(
        pipeline.PipelineService,
        "get_run_details",
        staticmethod(raise_not_found),
    )

    response = client.get("/pipeline-runs/999999")

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_get_pipeline_run_details_rejects_invalid_id():
    response = client.get("/pipeline-runs/0")

    assert response.status_code == 400

def test_download_pipeline_run_report(monkeypatch, tmp_path):
    report_path = tmp_path / "pipeline_run_10_report.pdf"
    report_path.write_bytes(b"%PDF-test-content")

    calls = []

    def fake_get_report_path(run_id, organization_id=None):
        calls.append((run_id, organization_id))
        return report_path

    monkeypatch.setattr(
        pipeline.PipelineService,
        "get_run_report_path",
        staticmethod(fake_get_report_path),
    )

    response = client.get("/pipeline-runs/10/report")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="pipeline_run_10_report.pdf"' in response.headers[
        "content-disposition"
    ]
    assert response.content == b"%PDF-test-content"
    assert calls == [(10, 1)]


def test_download_pipeline_run_report_not_found(monkeypatch):
    def raise_not_found(run_id, organization_id=None):
        raise ValueError(f"Pipeline run {run_id} was not found.")

    monkeypatch.setattr(
        pipeline.PipelineService,
        "get_run_report_path",
        staticmethod(raise_not_found),
    )

    response = client.get("/pipeline-runs/999999/report")

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_download_pipeline_run_report_pdf_missing(monkeypatch):
    def raise_missing_report(run_id, organization_id=None):
        raise ValueError(
            f"PDF report for pipeline run {run_id} was not found."
        )

    monkeypatch.setattr(
        pipeline.PipelineService,
        "get_run_report_path",
        staticmethod(raise_missing_report),
    )

    response = client.get("/pipeline-runs/10/report")

    assert response.status_code == 404
    assert "PDF report" in response.json()["detail"]


def test_download_pipeline_run_report_rejects_invalid_id():
    response = client.get("/pipeline-runs/0/report")

    assert response.status_code == 400