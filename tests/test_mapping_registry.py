
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
        "EXPLORE_MY_DATA",
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


def create_registry_with_modified_bank_mapping(
    tmp_path,
    modify_config,
):
    project_root = Path(__file__).resolve().parents[1]

    original_mapping_path = (
        project_root
        / "config"
        / "mappings"
        / "bank_csv_v1.yaml"
    )

    with original_mapping_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    modify_config(config)

    mappings_dir = tmp_path / "mappings"
    mappings_dir.mkdir()

    custom_mapping_path = mappings_dir / "bank_csv_v1.yaml"

    with custom_mapping_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    sources_path = (
        project_root / "config" / "sources" / "sources.yaml"
    )

    return MappingRegistry(
        sources_path=sources_path,
        mappings_dir=mappings_dir,
    )


def test_registry_rejects_unsupported_canonical_field(tmp_path):
    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        lambda config: config["field_mappings"].update({
            "unknown_field": "some_source_field"
        }),
    )

    with pytest.raises(
        MappingRegistryError,
        match="Unsupported canonical field",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_unmapped_required_source_field(tmp_path):
    def modify(config):
        config["field_mappings"].pop("amount")

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Missing required canonical field mappings",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_unknown_transformation(tmp_path):
    def modify(config):
        config["transformations"]["amount"] = "invented_transformation"

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Unsupported transformation",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_invalid_source_timezone(tmp_path):
    def modify(config):
        config["mapping"]["source_timezone"] = "Invalid/Timezone"

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Unknown source timezone",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_required_source_field_not_mapped(tmp_path):
    def modify(config):
        config["required_fields"].append("missing_source_column")

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Required source fields are not mapped",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_inconsistent_signed_amount_configuration(
    tmp_path,
):
    def modify(config):
        config["mapping"]["amount_handling"] = "signed_amount"

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="signed_amount requires normalize_signed_amount",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_transformation_for_unmapped_field(tmp_path):
    def modify(config):
        config["transformations"]["transaction_id"] = (
            "normalize_optional"
        )

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Transformation references an unmapped field",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_value_mapping_for_unmapped_field(tmp_path):
    def modify(config):
        config["value_mappings"]["unmapped_field"] = {
            "A": "B"
        }

    registry = create_registry_with_modified_bank_mapping(
        tmp_path,
        modify,
    )

    with pytest.raises(
        MappingRegistryError,
        match="Value mapping references an unmapped field",
    ):
        registry.resolve_mapping("BANK")


def test_registry_rejects_mapping_path_traversal(registry):
    with pytest.raises(
        MappingRegistryError,
        match="Invalid mapping ID",
    ):
        registry.resolve_mapping(
            source_name="BANK",
            mapping_id="../bank_csv_v1",
            mapping_version="1.0",
        )
