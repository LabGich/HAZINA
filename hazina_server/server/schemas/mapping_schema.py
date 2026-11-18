
from pydantic import BaseModel


class MappingSchema(BaseModel):
    mapping_id: str
    mapping_version: str
    description: str | None = None
    supported_formats: list[str]
    is_default: bool


class MappingListResponse(BaseModel):
    source_name: str
    count: int
    mappings: list[MappingSchema]
