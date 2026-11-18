
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Clock,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Activity,
} from 'lucide-react'

import {
  downloadPipelineRunReport,
  getPipelineRunDetails,
} from '../../services/pipeline'

import type {
  PipelineRunDetailResponse,
  PipelineErrorSummary,
} from '../../types/pipeline'

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

function MetricCard({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
        {numberFormatter.format(value)}
      </p>
    </div>
  )
}

function ErrorTable({
  title,
  errors,
}: {
  title: string
  errors: PipelineErrorSummary[]
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-6 py-5">
        <div className="flex items-center gap-2">
          <AlertCircle size={18} className="text-amber-600" />
          <h2 className="font-bold text-slate-900">{title}</h2>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {errors.length} error group{errors.length === 1 ? '' : 's'}
        </p>
      </div>

      {errors.length === 0 ? (
        <div className="px-6 py-8 text-center text-sm text-slate-400">
          No errors recorded.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[650px] text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-6 py-3 font-semibold">Error code</th>
                <th className="px-4 py-3 font-semibold">Field</th>
                <th className="px-4 py-3 font-semibold">Message</th>
                <th className="px-6 py-3 text-right font-semibold">
                  Affected records
                </th>
              </tr>
            </thead>

            <tbody>
              {errors.map((error, index) => (
                <tr
                  key={`${error.source_execution_id}-${error.error_code}-${index}`}
                  className="border-t border-slate-100"
                >
                  <td className="whitespace-nowrap px-6 py-4 font-semibold text-slate-700">
                    {error.error_code}
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {error.field_name || '—'}
                  </td>
                  <td className="max-w-md px-4 py-4 text-slate-600">
                    {error.error_message}
                  </td>
                  <td className="px-6 py-4 text-right tabular-nums text-slate-600">
                    {numberFormatter.format(error.affected_records)}
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

function PipelineRunDetailsPage() {
  const { runId } = useParams<{ runId: string }>()

  const [details, setDetails] = useState<PipelineRunDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const loadDetails = useCallback(async () => {
    if (!runId || !/^\d+$/.test(runId) || Number(runId) <= 0) {
      setError('Invalid pipeline run ID.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await getPipelineRunDetails(Number(runId))
      setDetails(response.report)
    } catch {
      setError('Unable to load this pipeline run. It may not exist or you may not have access.')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    void loadDetails()
  }, [loadDetails])

  const handleDownload = async () => {
    if (!runId) return

    setDownloading(true)
    setDownloadError(null)

    try {
      const blob = await downloadPipelineRunReport(Number(runId))
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = url
      link.download = `pipeline_run_${runId}_report.pdf`

      document.body.appendChild(link)
      link.click()
      link.remove()

      URL.revokeObjectURL(url)
    } catch {
      setDownloadError(
        'Unable to download the PDF report. It may not have been generated yet.',
      )
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center text-sm text-slate-400">
        Loading pipeline run details...
      </div>
    )
  }

  if (error || !details) {
    return (
      <div>
        <Link
          to="/pipeline-runs"
          className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-teal-700 hover:text-teal-900"
        >
          <ArrowLeft size={16} />
          Back to pipeline runs
        </Link>

        <div
          role="alert"
          className="rounded-xl border border-red-100 bg-white p-6 text-sm text-red-600 shadow-sm"
        >
          {error || 'Pipeline run details are unavailable.'}

          <button
            type="button"
            onClick={() => void loadDetails()}
            className="ml-3 font-semibold text-teal-700 hover:text-teal-900"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const pipeline = details.pipeline

  return (
    <div>
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <Link
          to="/pipeline-runs"
          className="inline-flex items-center gap-2 text-sm font-medium text-teal-700 hover:text-teal-900"
        >
          <ArrowLeft size={16} />
          Back to pipeline runs
        </Link>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void loadDetails()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>

          <button
            type="button"
            onClick={() => void handleDownload()}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={16} />
            {downloading ? 'Downloading...' : 'Download PDF report'}
          </button>
        </div>
      </div>

      {downloadError && (
        <div
          role="alert"
          className="mb-5 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {downloadError}
        </div>
      )}

      <div className="mb-8">
        <p className="text-sm text-slate-500">
          Detailed processing information
        </p>

        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Pipeline run #{pipeline.run_id}
          </h1>

          <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${getStatusClass(pipeline.run_status)}`}
          >
            {pipeline.run_status.replace(/_/g, ' ')}
          </span>
        </div>

        <p className="mt-2 text-sm text-slate-500">
          {pipeline.source_file || 'Source file unavailable'}
        </p>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Records received" value={pipeline.records_received} />
        <MetricCard label="Records loaded" value={pipeline.records_loaded} />
        <MetricCard label="Records rejected" value={pipeline.records_rejected} />
        <MetricCard label="Records promoted" value={pipeline.records_promoted} />
      </div>

      <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center gap-2">
          <Activity size={18} className="text-teal-700" />
          <h2 className="font-bold text-slate-900">Run information</h2>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <div>
            <p className="text-xs text-slate-400">Run ID</p>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              #{pipeline.run_id}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-400">Run type</p>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              {pipeline.run_type || '—'}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-400">Triggered by</p>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              {pipeline.triggered_by || '—'}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-400">Started</p>
            <p className="mt-1 flex items-center gap-2 text-sm text-slate-700">
              <Clock size={14} />
              {formatDate(pipeline.started_at)}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-400">Completed</p>
            <p className="mt-1 flex items-center gap-2 text-sm text-slate-700">
              <Clock size={14} />
              {formatDate(pipeline.completed_at)}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-400">Source file</p>
            <p className="mt-1 flex items-center gap-2 break-all text-sm text-slate-700">
              <FileText size={14} />
              {pipeline.source_file || '—'}
            </p>
          </div>
        </div>
      </section>

      <section className="mb-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <h2 className="font-bold text-slate-900">Source executions</h2>
          <p className="mt-1 text-xs text-slate-400">
            {details.source_executions.length} source execution(s)
          </p>
        </div>

        {details.source_executions.length === 0 ? (
          <div className="px-6 py-8 text-center text-sm text-slate-400">
            No source executions recorded.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {details.source_executions.map((execution) => (
              <div
                key={execution.source_execution_id}
                className="p-6"
              >
                <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      {execution.source_name}
                    </h3>
                    <p className="mt-1 text-xs text-slate-400">
                      Execution #{execution.source_execution_id} · Source ID {execution.source_id}
                    </p>
                  </div>

                  <span
                    className={`inline-flex w-fit rounded-full px-3 py-1 text-xs font-semibold ${getStatusClass(execution.execution_status)}`}
                  >
                    {execution.execution_status.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <div>
                    <p className="text-xs text-slate-400">Mapping</p>
                    <p className="mt-1 text-sm font-medium text-slate-700">
                      {execution.mapping_id}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400">Mapping version</p>
                    <p className="mt-1 text-sm font-medium text-slate-700">
                      {execution.mapping_version}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400">Started</p>
                    <p className="mt-1 text-sm text-slate-700">
                      {formatDate(execution.started_at)}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400">Completed</p>
                    <p className="mt-1 text-sm text-slate-700">
                      {formatDate(execution.completed_at)}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400">Error code</p>
                    <p className="mt-1 text-sm text-slate-700">
                      {execution.error_code || '—'}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400">Error message</p>
                    <p className="mt-1 break-words text-sm text-slate-700">
                      {execution.error_message || '—'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
                  {[
                    ['Received', execution.records_received],
                    ['Loaded', execution.records_loaded],
                    ['Mapped', execution.records_mapped],
                    ['Rejected', execution.records_rejected],
                    ['Skipped', execution.records_skipped],
                    ['Updated', execution.records_updated],
                    ['Duplicated', execution.records_duplicated],
                    ['Unique eligible', execution.records_unique_eligible],
                    ['Promoted', execution.records_promoted],
                    ['Already in core', execution.records_already_in_core],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-lg bg-slate-50 p-3"
                    >
                      <p className="text-xs text-slate-400">{label}</p>
                      <p className="mt-1 font-semibold tabular-nums text-slate-800">
                        {numberFormatter.format(Number(value))}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="mb-6 grid gap-6 xl:grid-cols-2">
        <ErrorTable
          title="Mapping errors"
          errors={details.mapping_errors}
        />

        <ErrorTable
          title="Validation errors"
          errors={details.validation_errors}
        />
      </div>

      <div className="mb-8 flex items-center gap-2 text-sm text-slate-500">
        {pipeline.run_status === 'SUCCESS' ? (
          <CheckCircle2 size={17} className="text-emerald-600" />
        ) : pipeline.run_status === 'FAILED' ? (
          <XCircle size={17} className="text-red-600" />
        ) : (
          <Activity size={17} className="text-slate-400" />
        )}
        <span>
          Run status: {pipeline.run_status.replace(/_/g, ' ')}
        </span>
      </div>
    </div>
  )
}

export default PipelineRunDetailsPage
