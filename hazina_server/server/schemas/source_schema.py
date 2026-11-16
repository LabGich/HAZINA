from pydantic import BaseModel


class DefaultMappingSchema(BaseModel):
    mapping_id: str | None = None
    mapping_version: str | None = None


class SourceSchema(BaseModel):
    source_name: str
    source_type: str
    description: str
    supported_formats: list[str]
    default_mapping: DefaultMappingSchema


class SourceListResponse(BaseModel):
    count: int
    sources: list[SourceSchema]