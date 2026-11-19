
import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from server.auth.dependencies import get_current_auth_context
from server.main import app
from server.services import pipeline_service
from server.services.pipeline_service import PipelineService


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


def test_pipeline_upload_requires_files():
    response = client.post("/pipeline-runs")

    assert response.status_code == 422


def test_pipeline_upload_requires_matching_metadata():
    response = client.post(
        "/pipeline-runs",
        files=[
            ("files", ("statement.csv", b"Date,Description\n", "text/csv")),
        ],
        data=[
            ("source_names", "EQUITY"),
            ("mapping_ids", "equity_csv_v1"),
        ],
    )

    assert response.status_code == 422


class FakeMappingRegistry:
    def get_source(self, source_name):
        assert source_name == "EQUITY"

        return {
            "source_type": "FILE",
            "supported_formats": ["CSV"],
        }

    def resolve_mapping(
        self,
        source_name,
        mapping_id,
        mapping_version,
    ):
        assert source_name == "EQUITY"
        assert mapping_id == "equity_csv_v1"
        assert mapping_version == "1.0"

        return {
            "mapping": {
                "mapping_id": mapping_id,
                "mapping_version": mapping_version,
            }
        }


def test_pipeline_service_saves_upload_and_calls_orchestrator(
    tmp_path,
    monkeypatch,
):
    upload_directory = tmp_path / "uploads"

    monkeypatch.setattr(
        pipeline_service,
        "UPLOAD_DIRECTORY",
        upload_directory,
    )

    captured = {}

    def fake_run_pipeline_v2(files, organization_id=None):
        captured["files"] = files
        captured["organization_id"] = organization_id

        return {
            "run_id": 123,
            "run_status": "SUCCESS",
            "pipeline": {"run_id": 123},
            "source_executions": [],
            "report_path": None,
            "report_error": None,
        }

    monkeypatch.setattr(
        pipeline_service,
        "run_pipeline_v2",
        fake_run_pipeline_v2,
    )

    upload = UploadFile(
        filename="statement.csv",
        file=BytesIO(
            b"Date,Description,Amount\n"
            b"2026-01-01,Salary,50000\n"
        ),
    )

    service = PipelineService(
        mapping_registry=FakeMappingRegistry()
    )

    result = asyncio.run(
        service.submit_files([
            {
                "file": upload,
                "source_name": "EQUITY",
                "mapping_id": "equity_csv_v1",
                "mapping_version": "1.0",
            }
        ])
    )

    assert result["run_id"] == 123
    assert result["run_status"] == "SUCCESS"

    assert captured["organization_id"] is None

    file_config = captured["files"][0]

    assert file_config["source_name"] == "EQUITY"
    assert file_config["mapping_id"] == "equity_csv_v1"
    assert file_config["mapping_version"] == "1.0"

    # The original filename must be preserved.
    assert file_config["file_name"] == "statement.csv"

    # The physical filename remains server-generated.
    saved_file = Path(file_config["file_path"])

    assert saved_file.exists()
    assert saved_file.parent == upload_directory
    assert saved_file.name != "statement.csv"

    assert saved_file.read_bytes() == (
        b"Date,Description,Amount\n"
        b"2026-01-01,Salary,50000\n"
    )


def test_pipeline_service_rejects_oversized_upload(
    tmp_path,
    monkeypatch,
):
    upload_directory = tmp_path / "uploads"

    monkeypatch.setattr(
        pipeline_service,
        "UPLOAD_DIRECTORY",
        upload_directory,
    )

    pipeline_called = False

    def fake_run_pipeline_v2(files):
        nonlocal pipeline_called
        pipeline_called = True
        raise AssertionError("Pipeline must not be called.")

    monkeypatch.setattr(
        pipeline_service,
        "run_pipeline_v2",
        fake_run_pipeline_v2,
    )

    upload = UploadFile(
        filename="large_statement.csv",
        file=BytesIO(b"A" * (10 * 1024 * 1024 + 1)),
    )

    service = PipelineService(
        mapping_registry=FakeMappingRegistry()
    )

    with pytest.raises(ValueError, match="10 MB upload limit"):
        asyncio.run(
            service.submit_files([
                {
                    "file": upload,
                    "source_name": "EQUITY",
                    "mapping_id": "equity_csv_v1",
                    "mapping_version": "1.0",
                }
            ])
        )

    assert not pipeline_called
    assert list(upload_directory.iterdir()) == []
