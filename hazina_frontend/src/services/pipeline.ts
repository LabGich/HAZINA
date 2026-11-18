import api from './api'
import type { PipelineRunListResponse } from '../types/pipeline'

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