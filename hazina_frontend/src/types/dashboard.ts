
export interface DashboardSummary {
  total_runs: number
  successful_runs: number
  partially_successful_runs: number
  failed_runs: number
  cancelled_runs: number
  pending_executions: number
  records_received: number
  records_processed: number
  records_rejected: number
  records_promoted: number
}
