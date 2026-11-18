
import pytest

from server.services.source_service import SourceService
from server.services.mapping_service import MappingService
from hazina_pipeline.mapping.mapping_registry import MappingRegistryError


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
            "MPESA": {
                "enabled": True,
                "source_type": "FILE",
                "description": "M-PESA statements",
                "supported_formats": ["CSV", "XLSX", "JSON"],
                "default_mapping": {
                    "mapping_id": "mpesa_csv_v1",
                    "mapping_version": "1.0",
                },
            },
        }

    def get_source(self, source_name):
        source = self.sources.get(source_name)

        if source is None or source.get("enabled") is not True:
            raise MappingRegistryError(
                f"Source is not registered or enabled: {source_name}"
            )

        return source

    def list_mappings(self, source_name):
        if source_name != "EQUITY":
            return []

        return [
            {
                "mapping": {
                    "mapping_id": "equity_csv_v1",
                    "mapping_version": "1.0",
                    "description": "Equity CSV mapping",
                    "supported_formats": ["CSV"],
                }
            },
            {
                "mapping": {
                    "mapping_id": "equity_json_v1",
                    "mapping_version": "1.0",
                    "description": "Equity JSON mapping",
                    "supported_formats": ["JSON"],
                }
            },
        ]
    
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


def test_source_service_lists_only_usable_file_sources():
    registry = FakeMappingRegistry()
    service = SourceService(registry=registry)

    result = service.list_sources()

    assert result["count"] == 1

    source_names = [
        source["source_name"]
        for source in result["sources"]
    ]

    assert "EQUITY" in source_names
    assert "STRIPE" not in source_names
    assert "MPESA" not in source_names
    assert "DISABLED_SOURCE" not in source_names


def test_source_service_includes_default_mapping_and_valid_formats():
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

    assert equity["supported_formats"] == ["CSV", "JSON"]


def test_mapping_service_lists_all_file_source_mappings():
    registry = FakeMappingRegistry()
    service = MappingService(registry=registry)

    result = service.list_mappings("EQUITY")

    assert result["source_name"] == "EQUITY"
    assert result["count"] == 2

    assert result["mappings"] == [
        {
            "mapping_id": "equity_csv_v1",
            "mapping_version": "1.0",
            "description": "Equity CSV mapping",
            "supported_formats": ["CSV"],
            "is_default": True,
        },
        {
            "mapping_id": "equity_json_v1",
            "mapping_version": "1.0",
            "description": "Equity JSON mapping",
            "supported_formats": ["JSON"],
            "is_default": False,
        },
    ]


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
