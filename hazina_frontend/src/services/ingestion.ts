
import api from './api'

import type {
  SourceListResponse,
  MappingListResponse,
} from '../types/ingestion'

export interface PipelineUpload {
  file: File
  source_name: string
  mapping_id: string
  mapping_version: string
}

export interface SourceExecutionSubmission {
  source_execution_id: number
  source_name: string
  file_path: string
  execution_status: string
  stages: Record<string, unknown>
  error: Record<string, unknown> | null
}

export interface PipelineSubmissionResponse {
  run_id: number
  run_status: string
  pipeline: Record<string, unknown>
  source_executions: SourceExecutionSubmission[]
  report_path: string | null
  report_error: string | null
}

export async function getSources(): Promise<SourceListResponse> {
  const response = await api.get<SourceListResponse>('/sources')

  return response.data
}

export async function getMappings(
  sourceName: string,
): Promise<MappingListResponse> {
  const response = await api.get<MappingListResponse>('/mappings', {
    params: {
      source_name: sourceName,
    },
  })

  return response.data
}

export async function submitPipelineFiles(
  uploads: PipelineUpload[],
): Promise<PipelineSubmissionResponse> {
  const formData = new FormData()

  uploads.forEach((upload) => {
    formData.append('files', upload.file)
    formData.append('source_names', upload.source_name)
    formData.append('mapping_ids', upload.mapping_id)
    formData.append('mapping_versions', upload.mapping_version)
  })

  const response = await api.post<PipelineSubmissionResponse>(
    '/pipeline-runs',
    formData,
  )

  return response.data
}
