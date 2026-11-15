
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers import sources, mappings
from src.api.services.source_service import SourceService
from src.api.services.mapping_service import MappingService


client = TestClient(app)


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
