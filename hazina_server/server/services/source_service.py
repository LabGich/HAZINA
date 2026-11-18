
from hazina_pipeline.mapping.mapping_registry import MappingRegistry


class SourceService:
    """Application service for discovering usable file sources."""

    def __init__(self, registry: MappingRegistry | None = None):
        self.registry = registry or MappingRegistry()

    def list_sources(self) -> dict:
        """Return enabled FILE sources with at least one valid mapping."""

        sources = []

        for source_name, config in self.registry.sources.items():
            if config.get("enabled") is not True:
                continue

            if config.get("source_type") != "FILE":
                continue

            mappings = self.registry.list_mappings(source_name)

            if not mappings:
                continue

            default_mapping = config.get("default_mapping") or {}
            default_mapping_id = default_mapping.get("mapping_id")
            default_mapping_version = default_mapping.get(
                "mapping_version"
            )

            available_formats = []
            valid_default = None

            for mapping_config in mappings:
                metadata = mapping_config["mapping"]

                for file_format in metadata.get("supported_formats", []):
                    if file_format not in available_formats:
                        available_formats.append(file_format)

                if (
                    metadata.get("mapping_id") == default_mapping_id
                    and metadata.get("mapping_version")
                    == default_mapping_version
                ):
                    valid_default = {
                        "mapping_id": default_mapping_id,
                        "mapping_version": default_mapping_version,
                    }

            if not available_formats:
                continue

            sources.append({
                "source_name": source_name,
                "source_type": "FILE",
                "description": config.get("description") or "",
                "supported_formats": available_formats,
                "default_mapping": valid_default or {
                    "mapping_id": None,
                    "mapping_version": None,
                },
            })

        return {
            "count": len(sources),
            "sources": sources,
        }
