
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCES_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "sources" / "sources.yaml"
)

MAPPINGS_CONFIG_DIR = PROJECT_ROOT / "config" / "mappings"


class MappingRegistryError(Exception):
    """Raised when a source or mapping configuration cannot be resolved."""


class MappingRegistry:
    """Loads source definitions and resolves versioned mapping configurations."""

    def __init__(
        self,
        sources_path: Path = SOURCES_CONFIG_PATH,
        mappings_dir: Path = MAPPINGS_CONFIG_DIR,
    ) -> None:
        self.sources_path = Path(sources_path)
        self.mappings_dir = Path(mappings_dir)

        self.sources = self._load_sources()

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise MappingRegistryError(
                f"Configuration file not found: {path}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise MappingRegistryError(
                f"Invalid YAML in {path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise MappingRegistryError(
                f"Configuration must contain a YAML mapping: {path}"
            )

        return data

    def _load_sources(self) -> dict[str, Any]:
        config = self._load_yaml(self.sources_path)

        sources = config.get("sources")

        if not isinstance(sources, dict) or not sources:
            raise MappingRegistryError(
                "Source configuration must contain a non-empty 'sources' mapping."
            )

        for source_name, source_config in sources.items():
            if not isinstance(source_config, dict):
                raise MappingRegistryError(
                    f"Invalid configuration for source: {source_name}"
                )

        return sources

    def get_source(self, source_name: str) -> dict[str, Any]:
        source_name = source_name.strip().upper()

        source = self.sources.get(source_name)

        if source is None:
            raise MappingRegistryError(
                f"Source is not registered: {source_name}"
            )

        if source.get("enabled") is not True:
            raise MappingRegistryError(
                f"Source is disabled: {source_name}"
            )

        return source

    def resolve_mapping(
        self,
        source_name: str,
        mapping_id: str | None = None,
        mapping_version: str | None = None,
    ) -> dict[str, Any]:
        source = self.get_source(source_name)

        default_mapping = source.get("default_mapping")

        if mapping_id is None and mapping_version is None:
            if not isinstance(default_mapping, dict):
                raise MappingRegistryError(
                    f"No default mapping configured for {source_name}"
                )

            mapping_id = default_mapping.get("mapping_id")
            mapping_version = default_mapping.get("mapping_version")

        elif not mapping_id or not mapping_version:
            raise MappingRegistryError(
                "Explicit mapping selection requires both mapping_id "
                "and mapping_version."
            )

        if not mapping_id or not mapping_version:
            raise MappingRegistryError(
                f"Incomplete mapping selection for {source_name}"
            )

        mapping_path = self.mappings_dir / f"{mapping_id}.yaml"

        config = self._load_yaml(mapping_path)
        mapping = config.get("mapping")

        if not isinstance(mapping, dict):
            raise MappingRegistryError(
                f"Mapping metadata is missing in {mapping_path}"
            )

        if mapping.get("mapping_id") != mapping_id:
            raise MappingRegistryError(
                f"Mapping ID mismatch in {mapping_path}"
            )

        if mapping.get("mapping_version") != mapping_version:
            raise MappingRegistryError(
                f"Unsupported mapping version: {mapping_id} "
                f"version {mapping_version}"
            )

        if mapping.get("source_name") != source_name:
            raise MappingRegistryError(
                f"Mapping {mapping_id} does not belong to source {source_name}"
            )

        if mapping.get("source_type") != source.get("source_type"):
            raise MappingRegistryError(
                f"Source type mismatch for mapping {mapping_id}"
            )

        return config
