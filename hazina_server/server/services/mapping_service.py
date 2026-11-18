
from hazina_pipeline.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)


class MappingService:
    """Application service for mapping discovery."""

    def __init__(self, registry: MappingRegistry | None = None):
        self.registry = registry or MappingRegistry()

    def list_mappings(self, source_name: str) -> dict:
        """Return all valid mappings for a file source."""

        source_name = source_name.strip().upper()
        source = self.registry.get_source(source_name)

        if source.get("source_type") != "FILE":
            return {
                "source_name": source_name,
                "count": 0,
                "mappings": [],
            }

        default_mapping = source.get("default_mapping") or {}

        default_mapping_id = default_mapping.get("mapping_id")
        default_mapping_version = default_mapping.get(
            "mapping_version"
        )

        validated_mappings = self.registry.list_mappings(
            source_name
        )

        mappings = []

        for config in validated_mappings:
            metadata = config["mapping"]

            mapping_id = metadata["mapping_id"]
            mapping_version = metadata["mapping_version"]

            mappings.append({
                "mapping_id": mapping_id,
                "mapping_version": mapping_version,
                "description": metadata.get("description"),
                "supported_formats": metadata.get(
                    "supported_formats", []
                ),
                "is_default": (
                    mapping_id == default_mapping_id
                    and mapping_version == default_mapping_version
                ),
            })

        return {
            "source_name": source_name,
            "count": len(mappings),
            "mappings": mappings,
        }
