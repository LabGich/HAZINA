
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  ArrowDownToLine,
  CheckCircle2,
  Clock3,
  Database,
  FileCheck2,
  FileInput,
  FileX,
  ShieldCheck,
  XCircle,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import StatCard from './components/StatCard'
import PipelineActivity from './components/PipelineActivity'
import QuickActions from './components/QuickActions'

import { getDashboardSummary } from '../../services/dashboard'
import type { DashboardSummary } from '../../types/dashboard'

import './DashboardPage.css'

const numberFormatter = new Intl.NumberFormat()

function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getDashboardSummary()
      setSummary(data)
    } catch {
      setError('Unable to load dashboard metrics. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  const formatValue = (value: number | undefined) => {
    if (loading) return '...'
    if (value === undefined || value === null) return '—'

    return numberFormatter.format(value)
  }

  const pipelineStatistics = [
    {
      label: 'Pipeline runs',
      value: formatValue(summary?.total_runs),
      description: 'Total processing runs',
      icon: Activity,
      color: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Successful',
      value: formatValue(summary?.successful_runs),
      description: 'Completed successfully',
      icon: CheckCircle2,
      color: 'bg-emerald-50 text-emerald-700',
    },
    {
      label: 'Partially successful',
      value: formatValue(summary?.partially_successful_runs),
      description: 'Completed with issues',
      icon: ShieldCheck,
      color: 'bg-amber-50 text-amber-700',
    },
    {
      label: 'Failed',
      value: formatValue(summary?.failed_runs),
      description: 'Unsuccessful runs',
      icon: XCircle,
      color: 'bg-red-50 text-red-700',
    },
    {
      label: 'Cancelled',
      value: formatValue(summary?.cancelled_runs),
      description: 'Cancelled runs',
      icon: FileX,
      color: 'bg-slate-100 text-slate-600',
    },
    {
      label: 'Running',
      value: formatValue(summary?.pending_executions),
      description: 'Currently processing',
      icon: Clock3,
      color: 'bg-orange-50 text-orange-700',
    },
  ]

  const transactionStatistics = [
    {
      label: 'Records received',
      value: formatValue(summary?.records_received),
      description: 'Incoming source records',
      icon: FileInput,
      color: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Records processed',
      value: formatValue(summary?.records_processed),
      description: 'Successfully loaded',
      icon: Database,
      color: 'bg-teal-50 text-teal-700',
    },
    {
      label: 'Records rejected',
      value: formatValue(summary?.records_rejected),
      description: 'Rejected during processing',
      icon: FileX,
      color: 'bg-red-50 text-red-700',
    },
    {
      label: 'Records promoted',
      value: formatValue(summary?.records_promoted),
      description: 'Promoted into core',
      icon: FileCheck2,
      color: 'bg-emerald-50 text-emerald-700',
    },
  ]

  const successRate =
    summary && summary.total_runs > 0
      ? (summary.successful_runs / summary.total_runs) * 100
      : 0

  return (
    <>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm text-slate-500">
            Welcome to your financial data workspace.
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Dashboard overview
          </h1>
        </div>

        <Link
          to="/ingestion"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
        >
          <ArrowDownToLine size={17} />
          Upload financial data
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-7 flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="font-semibold hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      <section>
        <div className="mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
            Pipeline overview
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Processing activity and execution outcomes
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {pipelineStatistics.map((statistic) => (
            <StatCard key={statistic.label} {...statistic} />
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
            Transaction overview
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Financial records moving through the pipeline
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {transactionStatistics.map((statistic) => (
            <StatCard key={statistic.label} {...statistic} />
          ))}
        </div>
      </section>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-bold text-slate-900">
              Pipeline success rate
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Successful runs as a proportion of all pipeline runs
            </p>
          </div>

          <p className="text-2xl font-bold text-slate-900">
            {loading ? '...' : `${successRate.toFixed(1)}%`}
          </p>
        </div>

        <div
          className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"
          role="progressbar"
          aria-label="Pipeline success rate"
          aria-valuenow={loading ? 0 : successRate}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{
              width: `${loading ? 0 : successRate}%`,
            }}
          />
        </div>
      </section>

      <div className="mt-7 grid gap-6 xl:grid-cols-3">
        <PipelineActivity />
        <QuickActions />
      </div>

      <div className="mt-6 rounded-xl bg-[#101c35] p-6 text-white sm:flex sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-teal-400/15 p-3 text-teal-300">
            <Zap size={22} />
          </div>

          <div>
            <h3 className="font-semibold">
              Your financial data, organized.
            </h3>
            <p className="mt-1 max-w-xl text-xs leading-5 text-slate-400">
              Hazina provides structured ingestion, validation,
              deduplication and monitoring for your financial data.
            </p>
          </div>
        </div>

        <span className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-teal-300 sm:mt-0">
          <ShieldCheck size={16} />
          Organization-aware processing
        </span>
      </div>
    </>
  )
}

export default DashboardPage
