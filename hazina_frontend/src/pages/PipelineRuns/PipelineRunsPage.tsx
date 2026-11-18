
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from 'lucide-react'
import { getPipelineRuns } from '../../services/pipeline'
import type { PipelineRunSummary } from '../../types/pipeline'

const PAGE_SIZE = 10

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

function PipelineRunsPage() {
  const [runs, setRuns] = useState<PipelineRunSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadRuns = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await getPipelineRuns(PAGE_SIZE, offset)
      setRuns(response.items)
      setTotal(response.total)
    } catch {
      setError('Unable to load pipeline runs. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [offset])

  useEffect(() => {
    void loadRuns()
  }, [loadRuns])

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm text-slate-500">
            Monitor your financial data processing.
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Pipeline runs
          </h1>
        </div>

        <button
          type="button"
          onClick={() => void loadRuns()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Total pipeline runs</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading && total === 0 ? '...' : numberFormatter.format(total)}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Runs on this page</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : numberFormatter.format(runs.length)}
          </p>
        </div>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <h2 className="font-bold text-slate-900">All pipeline runs</h2>
          <p className="mt-1 text-xs text-slate-400">
            Processing history for your organization
          </p>
        </div>

        {error ? (
          <div
            role="alert"
            className="flex min-h-64 flex-col items-center justify-center gap-3 px-6 text-center"
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
        ) : loading ? (
          <div className="flex min-h-64 items-center justify-center text-sm text-slate-400">
            Loading pipeline runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
            <div className="mb-3 rounded-full bg-slate-50 p-4">
              <Activity size={26} className="text-slate-400" />
            </div>

            <h3 className="text-sm font-semibold text-slate-700">
              No pipeline runs yet
            </h3>

            <p className="mt-2 max-w-sm text-xs leading-5 text-slate-400">
              Once you upload financial data and submit it for processing,
              your pipeline runs will appear here.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1000px] text-left text-xs">
                <thead className="bg-slate-50">
                  <tr className="text-slate-500">
                    <th className="px-6 py-4 font-semibold">Run ID</th>
                    <th className="px-4 py-4 font-semibold">Source file</th>
                    <th className="px-4 py-4 font-semibold">Status</th>
                    <th className="px-4 py-4 text-right font-semibold">
                      Received
                    </th>
                    <th className="px-4 py-4 text-right font-semibold">
                      Loaded
                    </th>
                    <th className="px-4 py-4 text-right font-semibold">
                      Rejected
                    </th>
                    <th className="px-6 py-4 text-right font-semibold">
                      Started
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {runs.map((run) => (
                    <tr
                      key={run.run_id}
                      className="border-t border-slate-100 transition hover:bg-slate-50/70"
                    >
                      <td className="whitespace-nowrap px-6 py-4 font-semibold text-slate-700">
                        #{run.run_id}
                      </td>

                      <td className="max-w-56 truncate px-4 py-4 font-medium text-slate-700">
                        {run.source_file || '—'}
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 font-semibold ${getStatusClass(run.run_status)}`}
                        >
                          {run.run_status.replace(/_/g, ' ')}
                        </span>
                      </td>

                      <td className="px-4 py-4 text-right tabular-nums text-slate-600">
                        {numberFormatter.format(run.records_received)}
                      </td>

                      <td className="px-4 py-4 text-right tabular-nums text-slate-600">
                        {numberFormatter.format(run.records_loaded)}
                      </td>

                      <td className="px-4 py-4 text-right tabular-nums text-slate-600">
                        {numberFormatter.format(run.records_rejected)}
                      </td>

                      <td className="whitespace-nowrap px-6 py-4 text-right text-slate-500">
                        {formatDate(run.started_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-col justify-between gap-4 border-t border-slate-100 px-6 py-4 sm:flex-row sm:items-center">
              <p className="text-xs text-slate-500">
                Showing {offset + 1}–{offset + runs.length} of{' '}
                {numberFormatter.format(total)} runs
              </p>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  type="button"
                  onClick={() =>
                    setOffset((current) => Math.max(0, current - PAGE_SIZE))
                  }
                  disabled={offset === 0 || loading}
                  className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={16} />
                </button>

                <button
                  type="button"
                  onClick={() => setOffset((current) => current + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= total || loading}
                  className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Next page"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

export default PipelineRunsPage
