import {
  Activity,
  ArrowDownToLine,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navigation = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Data ingestion', path: '/ingestion', icon: ArrowDownToLine },
  { label: 'Pipeline runs', path: '/pipeline-runs', icon: Activity },
  { label: 'Mappings', path: '/mappings', icon: FileSpreadsheet },
]

const managementNavigation = [
  { label: 'User management', path: '/users', icon: Users },
  { label: 'Settings', path: '/settings', icon: Settings },
]

function Sidebar({ open, onClose }: SidebarProps) {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition ${
      isActive
        ? 'bg-teal-400/15 text-teal-300'
        : 'text-slate-400 hover:bg-white/5 hover:text-white'
    }`

  return (
    <>
      {open && (
        <button
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#101c35] text-white transition-transform duration-200 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center justify-between border-b border-white/10 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-400 text-[#101c35]">
              <Database size={23} strokeWidth={2.5} />
            </div>

            <div>
              <h1 className="text-xl font-bold tracking-wide">HAZINA</h1>
              <p className="text-[10px] font-medium tracking-[0.2em] text-slate-400">
                FINANCIAL INTELLIGENCE
              </p>
            </div>
          </div>

          <button
            aria-label="Close sidebar"
            onClick={onClose}
            className="text-slate-400 hover:text-white lg:hidden"
          >
            <X size={21} />
          </button>
        </div>

        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Workspace
          </p>

          <nav className="space-y-1">
            {navigation.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                onClick={onClose}
                className={linkClass}
              >
                <Icon size={19} />
                {label}

                {label === 'Pipeline runs' && (
                  <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-[10px]">
                    V2
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="px-4 pt-8">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Administration
          </p>

          <nav className="space-y-1">
            {managementNavigation.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                onClick={onClose}
                className={linkClass}
              >
                <Icon size={19} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-teal-300">
              <ShieldCheck size={18} />
              <span className="text-xs font-semibold">Secure workspace</span>
            </div>

            <p className="text-xs leading-5 text-slate-400">
              Organization-scoped financial processing and access control.
            </p>
          </div>

          <p className="mt-5 text-center text-[10px] text-slate-600">
            HAZINA FINANCIAL PIPELINE · V2
          </p>
        </div>
      </aside>
    </>
  )
}

export default Sidebar