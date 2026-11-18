
import pytest
from fastapi.testclient import TestClient

from server.auth.dependencies import get_current_auth_context
from server.main import app
from server.services.pipeline_service import PipelineService


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def test_dashboard_summary_requires_authentication():
    response = client.get("/dashboard/summary")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "role",
    ["ADMIN", "OPERATOR", "VIEWER"],
)
def test_dashboard_summary_returns_organization_metrics(
    role,
    monkeypatch,
):
    auth_context = {
        "user_id": 10,
        "organization_id": 512,
        "role_code": role,
    }

    app.dependency_overrides[get_current_auth_context] = (
        lambda: auth_context
    )

    expected = {
        "total_runs": 12,
        "records_processed": 850,
        "successful_runs": 9,
        "pending_executions": 2,
    }

    captured = {}

    def fake_get_dashboard_summary(organization_id):
        captured["organization_id"] = organization_id
        return expected

    monkeypatch.setattr(
        PipelineService,
        "get_dashboard_summary",
        staticmethod(fake_get_dashboard_summary),
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == expected
    assert captured["organization_id"] == 512


def test_dashboard_summary_uses_authenticated_organization(
    monkeypatch,
):
    auth_context = {
        "user_id": 20,
        "organization_id": 700,
        "role_code": "ADMIN",
    }

    app.dependency_overrides[get_current_auth_context] = (
        lambda: auth_context
    )

    captured = {}

    def fake_get_dashboard_summary(organization_id):
        captured["organization_id"] = organization_id

        return {
            "total_runs": 0,
            "records_processed": 0,
            "successful_runs": 0,
            "pending_executions": 0,
        }

    monkeypatch.setattr(
        PipelineService,
        "get_dashboard_summary",
        staticmethod(fake_get_dashboard_summary),
    )

    response = client.get(
        "/dashboard/summary",
        params={"organization_id": 512},
    )

    assert response.status_code == 200
    assert captured["organization_id"] == 700
