import api from './api'
import type {
  PipelineRunListResponse,
  PipelineRunDetailEnvelope,
} from '../types/pipeline'

export async function getPipelineRuns(
  limit = 5,
  offset = 0,
): Promise<PipelineRunListResponse> {
  const response = await api.get<PipelineRunListResponse>(
    '/pipeline-runs',
    {
      params: { limit, offset },
    },
  )

  return response.data
}

export async function getPipelineRunDetails(
  runId: number,
): Promise<PipelineRunDetailEnvelope> {
  const response = await api.get<PipelineRunDetailEnvelope>(
    `/pipeline-runs/${runId}`,
  )

  return response.data
}

export async function downloadPipelineRunReport(
  runId: number,
): Promise<Blob> {
  const response = await api.get(
    `/pipeline-runs/${runId}/report`,
    {
      responseType: 'blob',
    },
  )

  return response.data
}