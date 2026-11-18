import { useCallback, useEffect, useState } from 'react'
import { ArrowUpRight, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getPipelineRuns } from '../../../services/pipeline'
import type { PipelineRunSummary } from '../../../types/pipeline'

const numberFormatter = new Intl.NumberFormat()

function formatDate(value: string | null): string {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return '—'

  return date.toLocaleString()
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'SUCCESS':
      return 'bg-emerald-50 text-emerald-700'
    case 'PARTIAL_SUCCESS':
      return 'bg-amber-50 text-amber-700'
    case 'FAILED':
      return 'bg-red-50 text-red-700'
    case 'RUNNING':
      return 'bg-blue-50 text-blue-700'
    case 'CANCELLED':
      return 'bg-slate-100 text-slate-600'
    default:
      return 'bg-slate-100 text-slate-600'
  }
}

function PipelineActivity() {
  const [runs, setRuns] = useState<PipelineRunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadRuns = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await getPipelineRuns(5)
      setRuns(response.items)
    } catch {
      setError('Unable to load recent pipeline activity.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadRuns()
  }, [loadRuns])

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-slate-900">Pipeline activity</h3>
          <p className="mt-1 text-xs text-slate-400">
            Your five most recent pipeline runs
          </p>
        </div>

        <Link
          to="/pipeline-runs"
          className="flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-900"
        >
          View runs <ArrowUpRight size={14} />
        </Link>
      </div>

      {loading ? (
        <div className="flex min-h-64 items-center justify-center text-sm text-slate-400">
          Loading recent activity...
        </div>
      ) : error ? (
        <div
          role="alert"
          className="flex min-h-64 flex-col items-center justify-center gap-3 text-center"
        >
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => void loadRuns()}
            className="text-sm font-semibold text-teal-700 hover:text-teal-900"
          >
            Try again
          </button>
        </div>
      ) : runs.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/70 px-6 text-center">
          <div className="mb-3 rounded-full bg-white p-4 shadow-sm">
            <Activity size={25} className="text-slate-400" />
          </div>

          <p className="text-sm font-semibold text-slate-700">
            No pipeline runs yet
          </p>

          <p className="mt-1 max-w-sm text-xs leading-5 text-slate-400">
            Your recent processing activity will appear here after you upload
            financial data.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 text-slate-400">
                <th className="pb-3 pr-4 font-medium">Source file</th>
                <th className="pb-3 pr-4 font-medium">Run ID</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 text-right font-medium">
                  Records processed
                </th>
                <th className="pb-3 text-right font-medium">Start time</th>
              </tr>
            </thead>

            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  className="border-b border-slate-50 last:border-0"
                >
                  <td className="max-w-40 truncate py-4 pr-4 font-medium text-slate-700">
                    {run.source_file || `Pipeline run #${run.run_id}`}
                  </td>

                  <td className="py-4 pr-4 text-slate-500">
                    #{run.run_id}
                  </td>

                  <td className="py-4 pr-4">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 font-semibold ${getStatusClass(run.run_status)}`}
                    >
                      {run.run_status.replace(/_/g, ' ')}
                    </span>
                  </td>

                  <td className="py-4 pr-4 text-right text-slate-600">
                    {numberFormatter.format(run.records_loaded)}
                  </td>

                  <td className="whitespace-nowrap py-4 text-right text-slate-500">
                    {formatDate(run.started_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default PipelineActivity