
import pytest

from src.api.services.source_service import SourceService
from src.api.services.mapping_service import MappingService
from src.mapping.mapping_registry import MappingRegistryError


class FakeMappingRegistry:
    def __init__(self):
        self.sources = {
            "EQUITY": {
                "enabled": True,
                "source_type": "FILE",
                "description": "Equity Bank statements",
                "supported_formats": ["CSV", "JSON"],
                "default_mapping": {
                    "mapping_id": "equity_csv_v1",
                    "mapping_version": "1.0",
                },
            },
            "STRIPE": {
                "enabled": True,
                "source_type": "API",
                "description": "Stripe transactions",
                "supported_formats": ["JSON"],
                "default_mapping": {
                    "mapping_id": "stripe_api_v1",
                    "mapping_version": "1.0",
                },
            },
            "DISABLED_SOURCE": {
                "enabled": False,
                "source_type": "FILE",
                "description": "Disabled source",
                "supported_formats": ["CSV"],
                "default_mapping": {},
            },
        }

    def get_source(self, source_name):
        source = self.sources.get(source_name)

        if source is None or source.get("enabled") is not True:
            raise MappingRegistryError(
                f"Source is not registered or enabled: {source_name}"
            )

        return source

    def resolve_mapping(
        self,
        source_name,
        mapping_id,
        mapping_version,
    ):
        if mapping_id != "equity_csv_v1":
            raise MappingRegistryError("Mapping not found")

        return {
            "mapping": {
                "mapping_id": mapping_id,
                "mapping_version": mapping_version,
                "description": "Equity CSV mapping",
            }
        }


def test_source_service_lists_enabled_sources():
    registry = FakeMappingRegistry()
    service = SourceService(registry=registry)

    result = service.list_sources()

    assert result["count"] == 2

    source_names = [
        source["source_name"]
        for source in result["sources"]
    ]

    assert "EQUITY" in source_names
    assert "STRIPE" in source_names
    assert "DISABLED_SOURCE" not in source_names


def test_source_service_includes_default_mapping():
    registry = FakeMappingRegistry()
    service = SourceService(registry=registry)

    result = service.list_sources()

    equity = next(
        source
        for source in result["sources"]
        if source["source_name"] == "EQUITY"
    )

    assert equity["default_mapping"] == {
        "mapping_id": "equity_csv_v1",
        "mapping_version": "1.0",
    }


def test_mapping_service_lists_file_source_default_mapping():
    registry = FakeMappingRegistry()
    service = MappingService(registry=registry)

    result = service.list_mappings("EQUITY")

    assert result["source_name"] == "EQUITY"
    assert result["count"] == 1
    assert result["mappings"][0] == {
        "mapping_id": "equity_csv_v1",
        "mapping_version": "1.0",
        "description": "Equity CSV mapping",
        "is_default": True,
    }


def test_mapping_service_returns_empty_list_for_api_source():
    registry = FakeMappingRegistry()
    service = MappingService(registry=registry)

    result = service.list_mappings("STRIPE")

    assert result == {
        "source_name": "STRIPE",
        "count": 0,
        "mappings": [],
    }


def test_mapping_service_rejects_unknown_source():
    registry = FakeMappingRegistry()
    service = MappingService(registry=registry)

    with pytest.raises(MappingRegistryError):
        service.list_mappings("UNKNOWN")
