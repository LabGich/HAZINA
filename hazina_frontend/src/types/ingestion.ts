
export interface DefaultMapping {
  mapping_id: string | null
  mapping_version: string | null
}

export interface Source {
  source_name: string
  source_type: string
  description: string
  supported_formats: string[]
  default_mapping: DefaultMapping
}

export interface SourceListResponse {
  count: number
  sources: Source[]
}

export interface Mapping {
  mapping_id: string
  mapping_version: string
  description: string | null
  is_default: boolean
}

export interface MappingListResponse {
  source_name: string
  count: number
  mappings: Mapping[]
}
