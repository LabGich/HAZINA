
from pathlib import Path

import pytest
import yaml

from src.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)


@pytest.fixture
def registry():
    return MappingRegistry()


def test_registry_loads_all_registered_sources(registry):
    assert set(registry.sources) == {
        "BANK",
        "MPESA",
        "STRIPE",
        "PLAID",
        "DARAJA",
    }


def test_get_source_is_case_insensitive(registry):
    source = registry.get_source("bank")

    assert source["source_type"] == "FILE"
    assert source["enabled"] is True


def test_unknown_source_raises_error(registry):
    with pytest.raises(
        MappingRegistryError,
        match="Source is not registered",
    ):
        registry.get_source("UNKNOWN")


def test_disabled_source_raises_error(tmp_path):
    sources_path = tmp_path / "sources.yaml"

    sources_path.write_text(
        yaml.safe_dump({
            "sources": {
                "BANK": {
                    "enabled": False,
                    "source_type": "FILE",
                }
            }
        }),
        encoding="utf-8",
    )

    registry = MappingRegistry(
        sources_path=sources_path,
        mappings_dir=tmp_path / "mappings",
    )

    with pytest.raises(
        MappingRegistryError,
        match="Source is disabled",
    ):
        registry.get_source("BANK")


def test_default_bank_mapping_resolves(registry):
    mapping = registry.resolve_mapping("BANK")

    assert mapping["mapping"]["mapping_id"] == "bank_csv_v1"
    assert mapping["mapping"]["mapping_version"] == "1.0"


def test_explicit_mapping_resolves(registry):
    mapping = registry.resolve_mapping(
        source_name="BANK",
        mapping_id="bank_csv_v1",
        mapping_version="1.0",
    )

    assert mapping["mapping"]["mapping_id"] == "bank_csv_v1"


def test_explicit_mapping_requires_id_and_version(registry):
    with pytest.raises(
        MappingRegistryError,
        match="requires both mapping_id and mapping_version",
    ):
        registry.resolve_mapping(
            source_name="BANK",
            mapping_id="bank_csv_v1",
        )


def test_unsupported_mapping_version_raises_error(registry):
    with pytest.raises(
        MappingRegistryError,
        match="Unsupported mapping version",
    ):
        registry.resolve_mapping(
            source_name="BANK",
            mapping_id="bank_csv_v1",
            mapping_version="99.0",
        )


def test_mapping_from_wrong_source_raises_error(registry):
    with pytest.raises(
        MappingRegistryError,
        match="does not belong to source",
    ):
        registry.resolve_mapping(
            source_name="MPESA",
            mapping_id="bank_csv_v1",
            mapping_version="1.0",
        )


def test_missing_mapping_file_raises_error(registry):
    with pytest.raises(
        MappingRegistryError,
        match="Configuration file not found",
    ):
        registry.resolve_mapping(
            source_name="BANK",
            mapping_id="missing_mapping_v1",
            mapping_version="1.0",
        )
