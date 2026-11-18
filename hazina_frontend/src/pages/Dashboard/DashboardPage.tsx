import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Clock3,
  Database,
  FileSpreadsheet,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import './DashboardPage.css'

const statistics = [
  {
    label: 'Pipeline runs',
    value: '—',
    description: 'Total processing runs',
    icon: Activity,
    color: 'bg-blue-50 text-blue-600',
  },
  {
    label: 'Records processed',
    value: '—',
    description: 'Across all executions',
    icon: Database,
    color: 'bg-teal-50 text-teal-700',
  },
  {
    label: 'Successful runs',
    value: '—',
    description: 'Completed successfully',
    icon: ShieldCheck,
    color: 'bg-emerald-50 text-emerald-700',
  },
  {
    label: 'Pending executions',
    value: '—',
    description: 'Awaiting completion',
    icon: Clock3,
    color: 'bg-orange-50 text-orange-700',
  },
]

const quickActions = [
  {
    label: 'Upload a financial file',
    description: 'Start a new pipeline run',
    icon: ArrowDownToLine,
    path: '/ingestion',
  },
  {
    label: 'Review pipeline runs',
    description: 'Monitor processing status',
    icon: Activity,
    path: '/pipeline-runs',
  },
  {
    label: 'Manage mappings',
    description: 'View available data mappings',
    icon: FileSpreadsheet,
    path: '/mappings',
  },
  {
    label: 'Manage workspace users',
    description: 'Control user access',
    icon: Users,
    path: '/users',
  },
]

function DashboardPage() {
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

      <div className="mb-7 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
        <Clock3 size={16} />
        Preview mode — live organization data will appear after API integration.
      </div>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {statistics.map(({ label, value, description, icon: Icon, color }) => (
          <div
            key={label}
            className="dashboard-stat-card rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <p className="text-sm font-medium text-slate-500">{label}</p>
              <div className={`rounded-lg p-2.5 ${color}`}>
                <Icon size={19} />
              </div>
            </div>

            <p className="mt-5 text-3xl font-bold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-400">{description}</p>
          </div>
        ))}
      </div>

      <div className="mt-7 grid gap-6 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900">Pipeline activity</h3>
              <p className="mt-1 text-xs text-slate-400">
                Processing activity over time
              </p>
            </div>

            <Link
              to="/pipeline-runs"
              className="flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-900"
            >
              View runs <ArrowUpRight size={14} />
            </Link>
          </div>

          <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/70 px-6 text-center">
            <div className="mb-3 rounded-full bg-white p-4 shadow-sm">
              <Activity size={25} className="text-slate-400" />
            </div>

            <p className="text-sm font-semibold text-slate-700">
              No activity to display yet
            </p>

            <p className="mt-1 max-w-sm text-xs leading-5 text-slate-400">
              Once the dashboard is connected to your pipeline API,
              processing activity and trends will appear here.
            </p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6">
            <h3 className="font-bold text-slate-900">Quick actions</h3>
            <p className="mt-1 text-xs text-slate-400">
              Common workspace tasks
            </p>
          </div>

          <div className="space-y-3">
            {quickActions.map(
              ({ label, description, icon: Icon, path }) => (
                <Link
                  key={path}
                  to={path}
                  className="flex w-full items-center gap-3 rounded-lg border border-slate-100 p-3 text-left transition hover:border-teal-200 hover:bg-teal-50/50"
                >
                  <div className="rounded-lg bg-slate-100 p-2 text-slate-600">
                    <Icon size={18} />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-slate-800">
                      {label}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {description}
                    </p>
                  </div>

                  <ArrowUpRight size={15} className="text-slate-400" />
                </Link>
              ),
            )}
          </div>
        </section>
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