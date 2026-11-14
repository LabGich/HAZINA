# Mapping registry responsible for YAML configuration

from pathlib import Path
from typing import Any
import re

import yaml
import codecs

from config import sources
from src.mapping.mapping_config_validator import (
    MappingConfigValidator,
    MappingConfigurationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCES_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "sources" / "sources.yaml"
)

MAPPINGS_CONFIG_DIR = PROJECT_ROOT / "config" / "mappings"


class MappingRegistryError(Exception):
    """Raised when a source or mapping configuration cannot be resolved."""


class MappingRegistry:
    """Loads sources and resolves validated versioned mappings."""

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

    @staticmethod
    def _validate_source_config(
        source_name: str,
        source_config: dict[str, Any],
    ) -> None:
        """Validate source registration and optional ingestion settings."""

        source_type = source_config.get("source_type")

        if source_type not in {"FILE", "API"}:
            raise MappingRegistryError(
                f"Invalid source_type for {source_name}."
            )

        for field in ("source_identifier", "description"):
            value = source_config.get(field)

            if not isinstance(value, str) or not value.strip():
                raise MappingRegistryError(
                    f"{field} is required for source {source_name}."
                )

        if not isinstance(source_config.get("enabled"), bool):
            raise MappingRegistryError(
                f"enabled must be a boolean for source {source_name}."
            )

        supported_formats = source_config.get("supported_formats")

        valid_formats = {
            "CSV", "XLSX", "JSON", "JSONL", "PARQUET"
        }

        if (
            not isinstance(supported_formats, list)
            or not supported_formats
            or any(
                not isinstance(fmt, str)
                or fmt not in valid_formats
                for fmt in supported_formats
            )
            or len(supported_formats) != len(set(supported_formats))
        ):
            raise MappingRegistryError(
                f"Invalid supported_formats for source {source_name}."
            )

        default_mapping = source_config.get("default_mapping")

        if not isinstance(default_mapping, dict):
            raise MappingRegistryError(
                f"default_mapping must be a mapping for {source_name}."
            )

        mapping_id = default_mapping.get("mapping_id")
        mapping_version = default_mapping.get("mapping_version")

        if (
            not isinstance(mapping_id, str)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]*",
                mapping_id,
            )
            or not isinstance(mapping_version, str)
            or not mapping_version.strip()
        ):
            raise MappingRegistryError(
                f"Invalid default mapping configuration for {source_name}."
            )

        ingestion = source_config.get("ingestion")

        if ingestion is None:
            return

        if source_type != "FILE":
            raise MappingRegistryError(
                f"Ingestion reader settings are only valid for FILE "
                f"sources: {source_name}."
            )

        if not isinstance(ingestion, dict):
            raise MappingRegistryError(
                f"ingestion must be a mapping for {source_name}."
            )

        #make adapter optional for shared readers
        #reserves validation whenever an adapter is specified
        # while allowing shared readers to work with reader options alone
        adapter = ingestion.get("adapter")

        if adapter is not None:
            if (
                not isinstance(adapter, str)
                or not re.fullmatch(
                    r"[a-z][a-z0-9_]*",
                    adapter,
                )
            ):
                raise MappingRegistryError(
                    f"Invalid ingestion adapter for {source_name}."
                )

        reader_options = ingestion.get("reader_options", {})

        if not isinstance(reader_options, dict):
            raise MappingRegistryError(
                f"reader_options must be a mapping for {source_name}."
            )

        # Reader options must be supported by every format registered
        # for this source. This prevents configuration that works for
        # one format but fails when another format is submitted.
        format_options = {
            "CSV": {"header_row", "encoding", "delimiter"},
            "XLSX": {"header_row", "sheet_name"},
            "JSON": {"record_path", "encoding"},
            "JSONL": {"encoding"},
            "PARQUET": {"columns"},
        }

        allowed_reader_options = set.intersection(
            *[
                format_options[fmt]
                for fmt in supported_formats
            ]
        )

        unknown_options = (
            set(reader_options) - allowed_reader_options
        )

        if unknown_options:
            raise MappingRegistryError(
                f"Unsupported reader options for {source_name}: "
                + ", ".join(sorted(unknown_options))
                + ". Options must be supported by every registered "
                "file format."
            )

        if "header_row" in reader_options:
            header_row = reader_options["header_row"]

            if (
                not isinstance(header_row, int)
                or isinstance(header_row, bool)
                or header_row < 1
            ):
                raise MappingRegistryError(
                    f"header_row must be a positive integer "
                    f"for {source_name}."
                )

        if "encoding" in reader_options:
            encoding = reader_options["encoding"]

            if not isinstance(encoding, str) or not encoding.strip():
                raise MappingRegistryError(
                    f"encoding must be a non-empty string "
                    f"for {source_name}."
                )

            try:
                codecs.lookup(encoding)
            except LookupError as exc:
                raise MappingRegistryError(
                    f"Unknown text encoding '{encoding}' "
                    f"for {source_name}."
                ) from exc

        if "delimiter" in reader_options:
            delimiter = reader_options["delimiter"]

            if not isinstance(delimiter, str) or len(delimiter) != 1:
                raise MappingRegistryError(
                    f"delimiter must be exactly one character "
                    f"for {source_name}."
                )

        if "sheet_name" in reader_options:
            sheet_name = reader_options["sheet_name"]

            if not isinstance(sheet_name, str) or not sheet_name.strip():
                raise MappingRegistryError(
                    f"sheet_name must be a non-empty string "
                    f"for {source_name}."
                )

        if "record_path" in reader_options:
            record_path = reader_options["record_path"]

            if not isinstance(record_path, str) or not record_path.strip():
                raise MappingRegistryError(
                    f"record_path must be a non-empty string "
                    f"for {source_name}."
                )

        if "columns" in reader_options:
            columns = reader_options["columns"]

            if (
                not isinstance(columns, list)
                or not columns
                or any(
                    not isinstance(column, str) or not column.strip()
                    for column in columns
                )
                or len(columns) != len(set(columns))
            ):
                raise MappingRegistryError(
                    f"columns must be a non-empty list of unique "
                    f"column names for {source_name}."
                )


    def _load_sources(self) -> dict[str, Any]:
        config = self._load_yaml(self.sources_path)

        sources = config.get("sources")

        if not isinstance(sources, dict) or not sources:
            raise MappingRegistryError(
                "Source configuration must contain a non-empty 'sources' mapping."
            )

        for source_name, source_config in sources.items():
            if (
                not isinstance(source_name, str)
                or not source_name.strip()
                or not isinstance(source_config, dict)
            ):
                raise MappingRegistryError(
                    f"Invalid configuration for source: {source_name}"
                )

            self._validate_source_config(
                source_name,
                source_config,
            )

        return sources

    def get_source(self, source_name: str) -> dict[str, Any]:
        if not isinstance(source_name, str) or not source_name.strip():
            raise MappingRegistryError(
                "Source name must be a non-empty string."
            )

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

        if source.get("source_type") not in {"FILE", "API"}:
            raise MappingRegistryError(
                f"Invalid source_type for {source_name}"
            )

        return source

    def resolve_mapping(
        self,
        source_name: str,
        mapping_id: str | None = None,
        mapping_version: str | None = None,
    ) -> dict[str, Any]:
        source_name = source_name.strip().upper()
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

        if (
            not isinstance(mapping_id, str)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]*",
                mapping_id,
            )
        ):
            raise MappingRegistryError(
                f"Invalid mapping ID: {mapping_id}"
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

        try:
            MappingConfigValidator.validate(
                config=config,
                source_name=source_name,
                source_config=source,
            )
        except MappingConfigurationError as exc:
            raise MappingRegistryError(
                f"Invalid mapping configuration {mapping_id}: {exc}"
            ) from exc

        return config
