# Unified file/source ingestion entry point
# Coordinates the components below to return standardized source records:
# 1. source reader -> reads file formats
# 2. adapters -> preprocesses source-specific layouts into clean records
# 3. mapping registry -> maps source records and YAML config to standardized fields

from pathlib import Path
from typing import Any

from src.mapping.mapping_registry import MappingRegistry
from src.ingestion.source_readers import FormatReaderRegistry
from src.ingestion.adapters.registry import AdapterRegistry


class SourceFileReaderError(ValueError):
    """Raised when source file ingestion cannot be completed."""


class SourceFileReader:
    """Unified entry point for registered file-based sources."""

    def __init__(
        self,
        mapping_registry: MappingRegistry | None = None,
    ) -> None:
        self.mapping_registry = mapping_registry or MappingRegistry()

    def read(
        self,
        source_name: str,
        file_path: str | Path,
    ) -> dict[str, Any]:
        """Read a registered source file using its configured reader."""

        source = self.mapping_registry.get_source(source_name)

        if source.get("source_type") != "FILE":
            raise SourceFileReaderError(
                f"Source is not file-based: {source_name}"
            )

        path = Path(file_path)

        if not path.is_file():
            raise SourceFileReaderError(
                f"Source file not found: {path}"
            )

        file_format = path.suffix.lower().lstrip(".").upper()
        supported_formats = source.get("supported_formats", [])

        if file_format not in supported_formats:
            raise SourceFileReaderError(
                f"{source_name} does not support {file_format} files. "
                f"Supported formats: {', '.join(supported_formats)}"
            )

        ingestion = source.get("ingestion", {})
        reader_options = ingestion.get("reader_options", {})
        adapter_name = ingestion.get("adapter")

        try:
            if adapter_name:
                result = AdapterRegistry.read(
                    adapter_name=adapter_name,
                    file_path=path,
                    reader_options=reader_options,
                )

                records = result["records"]

                metadata = {
                    key: value
                    for key, value in result.items()
                    if key != "records"
                }

            else:
                records = list(
                    FormatReaderRegistry.read(
                        file_path=path,
                        options=reader_options,
                    )
                )

                metadata = {}

            if not records:
                raise SourceFileReaderError(
                    f"No records found in source file: {path}"
                )

            return {
                "source_name": source_name.strip().upper(),
                "source_type": "FILE",
                "file_name": path.name,
                "file_format": file_format,
                "records_received": len(records),
                "records": records,
                "metadata": metadata,
            }

        except SourceFileReaderError:
            raise

        except (ValueError, KeyError) as exc:
            raise SourceFileReaderError(
                f"Unable to read {source_name} source file: {exc}"
            ) from exc
