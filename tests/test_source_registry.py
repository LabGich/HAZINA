
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.mapping.mapping_registry import MappingRegistryError
from src.mapping.source_registry import (
    DatabaseSourceRegistry,
    SourceRegistryError,
)


SOURCE_NAME = "TEST_SOURCE"


class FakeMappingRegistry:
    def __init__(self, sources):
        self.sources = sources

    def get_source(self, source_name):
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


def valid_source_config():
    return {
        "source_type": "FILE",
        "source_identifier": "test_source_statement",
        "description": "Test source statement files",
        "enabled": True,
        "supported_formats": ["CSV", "XLSX"],
        "default_mapping": {
            "mapping_id": "test_source_csv_v1",
            "mapping_version": "1.0",
        },
    }


def mock_database_connection():
    connection_context = MagicMock()
    connection = connection_context.__enter__.return_value

    cursor_context = connection.cursor.return_value
    cursor = cursor_context.__enter__.return_value

    return connection_context, connection, cursor


def test_synchronize_registers_sources():
    sources = {
        SOURCE_NAME: valid_source_config(),
        "MPESA": {
            **valid_source_config(),
            "source_identifier": "mpesa_statement",
            "default_mapping": {
                "mapping_id": "mpesa_csv_v1",
                "mapping_version": "1.0",
            },
        },
    }

    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(sources)
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )

    cursor.fetchone.side_effect = [(1,), (2,)]

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        result = registry.synchronize()

    assert result == {SOURCE_NAME: 1, "MPESA": 2}
    assert cursor.execute.call_count == 2
    connection.commit.assert_not_called()


def test_synchronize_serializes_supported_formats():
    sources = {SOURCE_NAME: valid_source_config()}

    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(sources)
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    cursor.fetchone.return_value = (1,)

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        registry.synchronize()

    parameters = cursor.execute.call_args.args[1]

    assert json.loads(parameters[5]) == ["CSV", "XLSX"]


def test_synchronize_rejects_invalid_source_type():
    config = valid_source_config()
    config["source_type"] = "UNKNOWN"

    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: config}
        )
    )

    with pytest.raises(SourceRegistryError, match="Invalid source type"):
        registry.synchronize()


def test_synchronize_rejects_invalid_supported_formats():
    config = valid_source_config()
    config["supported_formats"] = "CSV"

    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: config}
        )
    )

    with pytest.raises(
        SourceRegistryError,
        match="Invalid supported_formats",
    ):
        registry.synchronize()


def test_get_source_id_returns_registered_id():
    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: valid_source_config()}
        )
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    cursor.fetchone.return_value = (1,)

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        result = registry.get_source_id(SOURCE_NAME)

    assert result == 1


def test_get_source_returns_database_record():
    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: valid_source_config()}
        )
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )

    columns = [
        "source_id",
        "source_name",
        "source_type",
        "source_identifier",
        "description",
        "enabled",
        "supported_formats",
        "default_mapping_id",
        "default_mapping_version",
    ]

    cursor.description = [
        SimpleNamespace(name=column) for column in columns
    ]

    cursor.fetchone.return_value = (
        1,
        SOURCE_NAME,
        "FILE",
        "test_source_statement",
        "Test source statement files",
        True,
        ["CSV", "XLSX"],
        "test_source_csv_v1",
        "1.0",
    )

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        result = registry.get_source(SOURCE_NAME)

    assert result["source_id"] == 1
    assert result["source_name"] == SOURCE_NAME
    assert result["default_mapping_id"] == "test_source_csv_v1"


def test_get_source_id_rejects_unregistered_source():
    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: valid_source_config()}
        )
    )

    with pytest.raises(
        SourceRegistryError,
        match="Source is not registered",
    ):
        registry.get_source_id("UNKNOWN")


def test_get_source_rejects_disabled_source():
    config = valid_source_config()
    config["enabled"] = False

    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: config}
        )
    )

    with pytest.raises(
        SourceRegistryError,
        match="Source is disabled",
    ):
        registry.get_source(SOURCE_NAME)


def test_get_source_id_rejects_missing_database_registration():
    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: valid_source_config()}
        )
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    cursor.fetchone.return_value = None

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        with pytest.raises(
            SourceRegistryError,
            match="not synchronized in the database",
        ):
            registry.get_source_id(SOURCE_NAME)


def test_source_names_are_case_insensitive():
    registry = DatabaseSourceRegistry(
        mapping_registry=FakeMappingRegistry(
            {SOURCE_NAME: valid_source_config()}
        )
    )

    connection_context, connection, cursor = (
        mock_database_connection()
    )
    cursor.fetchone.return_value = (1,)

    with patch(
        "src.mapping.source_registry.get_database_connection",
        return_value=connection_context,
    ):
        result = registry.get_source_id("test_source")

    assert result == 1
