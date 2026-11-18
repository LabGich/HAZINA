export interface PipelineRunSummary {
  run_id: number
  source_file: string | null
  started_at: string | null
  completed_at: string | null
  run_status: string
  records_received: number
  records_loaded: number
  records_rejected: number
  records_promoted: number
  run_type: string | null
  triggered_by: string | null
}

export interface PipelineRunListResponse {
  items: PipelineRunSummary[]
  total: number
  limit: number
  offset: number
}

export interface PipelineErrorSummary {
  source_execution_id: number
  error_code: string
  error_message: string
  field_name: string | null
  affected_records: number
}

export interface PipelineDetails {
  run_id: number
  source_file: string | null
  started_at: string | null
  completed_at: string | null
  run_status: string
  records_received: number
  records_loaded: number
  records_rejected: number
  records_promoted: number
  run_type: string | null
  triggered_by: string | null
  metadata: Record<string, unknown> | null
}

export interface SourceExecutionDetails {
  source_execution_id: number
  source_id: number
  source_name: string
  mapping_id: string
  mapping_version: string
  execution_status: string
  started_at: string | null
  completed_at: string | null
  records_received: number
  records_loaded: number
  records_mapped: number
  records_rejected: number
  records_skipped: number
  records_updated: number
  records_duplicated: number
  records_unique_eligible: number
  records_promoted: number
  records_already_in_core: number
  error_code: string | null
  error_message: string | null
  metadata: Record<string, unknown> | null
}

export interface PipelineRunDetailResponse {
  pipeline: PipelineDetails
  source_executions: SourceExecutionDetails[]
  mapping_errors: PipelineErrorSummary[]
  validation_errors: PipelineErrorSummary[]
}

export interface PipelineRunDetailEnvelope {
  run_id: number
  report: PipelineRunDetailResponse
}