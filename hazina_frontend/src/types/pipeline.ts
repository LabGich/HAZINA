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