
import { Activity, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'

function PipelineActivity() {
  return (
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
  )
}

export default PipelineActivity
