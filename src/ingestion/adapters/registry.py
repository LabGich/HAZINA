# automated internal adapter selection
# registry that resolves source-specific adapters from config names
from src.ingestion.adapters.utilly import UtillyStatementAdapter


class AdapterRegistryError(ValueError):
    """Raised when a source adapter cannot be resolved."""


class AdapterRegistry:
    """Resolves source-specific adapters by configuration name."""

    _adapters = {
        "utilly_statement": UtillyStatementAdapter,
    }

    @classmethod
    def get_adapter(cls, adapter_name: str):
        """Return the registered adapter for a given name."""

        if not isinstance(adapter_name, str) or not adapter_name.strip():
            raise AdapterRegistryError(
                "Adapter name must be a non-empty string."
            )

        adapter = cls._adapters.get(adapter_name)

        if adapter is None:
            raise AdapterRegistryError(
                f"Unsupported source adapter: {adapter_name}"
            )

        return adapter

    @classmethod
    def read(
        cls,
        adapter_name: str,
        file_path,
        reader_options=None,
    ):
        """Resolve and execute a source-specific adapter."""

        adapter = cls.get_adapter(adapter_name)

        return adapter.read(
            file_path,
            reader_options=reader_options,
        )