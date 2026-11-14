# Database-backed source registry

from typing import Any

from src.database.connection import get_database_connection
from src.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)


class SourceRegistryError(Exception):
    """Raised when source registry synchronization or lookup fails."""


class DatabaseSourceRegistry:
    """Synchronizes YAML sources with the database source registry."""

    def __init__(self, mapping_registry: MappingRegistry | None = None):
        self.mapping_registry = mapping_registry or MappingRegistry()

    def synchronize(self) -> dict[str, int]:
        """
        Synchronize configured sources with ops.source_registry.

        Existing source IDs are preserved. Configuration changes update
        the existing database record rather than creating duplicates.
        """
        synchronized = {}

        with get_database_connection() as connection:
            with connection.cursor() as cursor:

                for source_name, config in self.mapping_registry.sources.items():
                    source_name = source_name.strip().upper()

                    source_type = config.get("source_type")
                    source_identifier = config.get("source_identifier")
                    description = config.get("description")
                    enabled = config.get("enabled", True)
                    supported_formats = config.get("supported_formats", [])

                    if source_type not in {"FILE", "API"}:
                        raise SourceRegistryError(
                            f"Invalid source type for {source_name}"
                        )

                    if not isinstance(enabled, bool):
                        raise SourceRegistryError(
                            f"Invalid enabled value for {source_name}"
                        )

                    if not isinstance(supported_formats, list):
                        raise SourceRegistryError(
                            f"Invalid supported_formats for {source_name}"
                        )

                    default_mapping = config.get("default_mapping") or {}

                    mapping_id = default_mapping.get("mapping_id")
                    mapping_version = default_mapping.get("mapping_version")

                    if bool(mapping_id) != bool(mapping_version):
                        raise SourceRegistryError(
                            f"Incomplete default mapping for {source_name}"
                        )

                    cursor.execute(
                        """
                        INSERT INTO ops.source_registry (
                            source_name,
                            source_type,
                            source_identifier,
                            description,
                            enabled,
                            supported_formats,
                            default_mapping_id,
                            default_mapping_version
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s::jsonb, %s, %s
                        )
                        ON CONFLICT (source_name)
                        DO UPDATE SET
                            source_type = EXCLUDED.source_type,
                            source_identifier = EXCLUDED.source_identifier,
                            description = EXCLUDED.description,
                            enabled = EXCLUDED.enabled,
                            supported_formats = EXCLUDED.supported_formats,
                            default_mapping_id = EXCLUDED.default_mapping_id,
                            default_mapping_version = EXCLUDED.default_mapping_version,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING source_id
                        """,
                        (
                            source_name,
                            source_type,
                            source_identifier,
                            description,
                            enabled,
                            __import__("json").dumps(supported_formats),
                            mapping_id,
                            mapping_version,
                        ),
                    )

                    synchronized[source_name] = cursor.fetchone()[0]

        return synchronized

    def get_source_id(self, source_name: str) -> int:
        """Return the database ID of an enabled registered source."""
        if not isinstance(source_name, str) or not source_name.strip():
            raise SourceRegistryError(
                "Source name must be a non-empty string."
            )

        source_name = source_name.strip().upper()

        try:
            self.mapping_registry.get_source(source_name)
        except MappingRegistryError as exc:
            raise SourceRegistryError(str(exc)) from exc

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT source_id
                    FROM ops.source_registry
                    WHERE source_name = %s
                      AND enabled = TRUE
                    """,
                    (source_name,),
                )

                result = cursor.fetchone()

        if result is None:
            raise SourceRegistryError(
                f"Source is not synchronized in the database: {source_name}"
            )

        return result[0]

    def get_source(self, source_name: str) -> dict[str, Any]:
        """Return the database registry record for an enabled source."""
        if not isinstance(source_name, str) or not source_name.strip():
            raise SourceRegistryError(
                "Source name must be a non-empty string."
            )

        source_name = source_name.strip().upper()

        try:
            self.mapping_registry.get_source(source_name)
        except MappingRegistryError as exc:
            raise SourceRegistryError(str(exc)) from exc

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        source_id,
                        source_name,
                        source_type,
                        source_identifier,
                        description,
                        enabled,
                        supported_formats,
                        default_mapping_id,
                        default_mapping_version
                    FROM ops.source_registry
                    WHERE source_name = %s
                      AND enabled = TRUE
                    """,
                    (source_name,),
                )

                row = cursor.fetchone()

                if row is None:
                    raise SourceRegistryError(
                        f"Source is not synchronized in the database: {source_name}"
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

        return dict(zip(columns, row))
