
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  description: string
  icon: LucideIcon
  color: string
}

function StatCard({
  label,
  value,
  description,
  icon: Icon,
  color,
}: StatCardProps) {
  return (
    <div className="dashboard-stat-card rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`rounded-lg p-2.5 ${color}`}>
          <Icon size={19} />
        </div>
      </div>

      <p className="mt-5 text-3xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  )
}

export default StatCard
