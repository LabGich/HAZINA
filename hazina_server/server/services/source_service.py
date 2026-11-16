from hazina_pipeline.mapping.mapping_registry import MappingRegistry


class SourceService:
    """Application service for source discovery."""

    def __init__(self, registry: MappingRegistry | None = None):
        self.registry = registry or MappingRegistry()

    def list_sources(self) -> dict:
        """Return enabled source configurations."""

        sources = []

        for source_name, config in self.registry.sources.items():
            if config.get("enabled") is not True:
                continue

            default_mapping = config.get("default_mapping") or {}

            sources.append({
                "source_name": source_name,
                "source_type": config.get("source_type"),
                "description": config.get("description"),
                "supported_formats": config.get(
                    "supported_formats", []
                ),
                "default_mapping": {
                    "mapping_id": default_mapping.get("mapping_id"),
                    "mapping_version": default_mapping.get(
                        "mapping_version"
                    ),
                },
            })

        return {
            "count": len(sources),
            "sources": sources,
        }