
import { Activity, ArrowDownToLine, ArrowUpRight, FileSpreadsheet, Users } from 'lucide-react'
import { Link } from 'react-router-dom'

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

function QuickActions() {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <h3 className="font-bold text-slate-900">Quick actions</h3>
        <p className="mt-1 text-xs text-slate-400">
          Common workspace tasks
        </p>
      </div>

      <div className="space-y-3">
        {quickActions.map(({ label, description, icon: Icon, path }) => (
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
        ))}
      </div>
    </section>
  )
}

export default QuickActions
