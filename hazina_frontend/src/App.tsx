
import { useState } from 'react'
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Bell,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
  Zap,
} from 'lucide-react'

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Data ingestion', icon: ArrowDownToLine },
  { label: 'Pipeline runs', icon: Activity },
  { label: 'Mappings', icon: FileSpreadsheet },
]

const managementNavigation = [
  { label: 'User management', icon: Users },
  { label: 'Settings', icon: Settings },
]

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const selectPage = (page: string) => {
    setActivePage(page)
    setSidebarOpen(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {sidebarOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#101c35] text-white transition-transform duration-200 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
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
            onClick={() => setSidebarOpen(false)}
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
            {navigation.map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => selectPage(label)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition ${
                  activePage === label
                    ? 'bg-teal-400/15 text-teal-300'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                <Icon size={19} />
                {label}
                {label === 'Pipeline runs' && (
                  <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-[10px]">
                    V2
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="px-4 pt-8">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Administration
          </p>
          <nav className="space-y-1">
            {managementNavigation.map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => selectPage(label)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition ${
                  activePage === label
                    ? 'bg-teal-400/15 text-teal-300'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                <Icon size={19} />
                {label}
              </button>
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

      <div className="min-h-screen lg:pl-64">
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-8">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open navigation"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            >
              <Menu size={22} />
            </button>
            <div>
              <p className="text-xs text-slate-400">Workspace / Overview</p>
              <h2 className="text-lg font-bold text-slate-900">
                {activePage}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-5">
            <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 md:flex">
              <Search size={16} className="text-slate-400" />
              <input
                aria-label="Search"
                placeholder="Search..."
                className="w-36 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
              <kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-400">
                /
              </kbd>
            </div>

            <button
              aria-label="Help"
              className="hidden text-slate-400 hover:text-slate-700 sm:block"
            >
              <CircleHelp size={20} />
            </button>
            <button
              aria-label="Notifications"
              className="relative text-slate-400 hover:text-slate-700"
            >
              <Bell size={20} />
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border-2 border-white bg-teal-500" />
            </button>

            <div className="flex items-center gap-2 border-l border-slate-200 pl-3 sm:pl-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#e0f2ef] text-sm font-bold text-teal-800">
                H
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-semibold text-slate-800">Workspace</p>
                <p className="text-[10px] text-slate-400">Account profile</p>
              </div>
              <ChevronDown size={15} className="hidden text-slate-400 sm:block" />
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] p-5 sm:p-8">
          {activePage === 'Dashboard' ? (
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
                <button
                  onClick={() => selectPage('Data ingestion')}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
                >
                  <ArrowDownToLine size={17} />
                  Upload financial data
                </button>
              </div>

              <div className="mb-7 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
                <Clock3 size={16} />
                Preview mode — live organization data will appear after API integration.
              </div>

              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                {[
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
                ].map(({ label, value, description, icon: Icon, color }) => (
                  <div
                    key={label}
                    className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-medium text-slate-500">{label}</p>
                      <div className={`rounded-lg p-2.5 ${color}`}>
                        <Icon size={19} />
                      </div>
                    </div>
                    <p className="mt-5 text-3xl font-bold text-slate-900">
                      {value}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">{description}</p>
                  </div>
                ))}
              </div>

              <div className="mt-7 grid gap-6 xl:grid-cols-3">
                <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
                  <div className="mb-6 flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-slate-900">
                        Pipeline activity
                      </h3>
                      <p className="mt-1 text-xs text-slate-400">
                        Processing activity over time
                      </p>
                    </div>
                    <button
                      onClick={() => selectPage('Pipeline runs')}
                      className="flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-900"
                    >
                      View runs <ArrowUpRight size={14} />
                    </button>
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
                    {[
                      {
                        label: 'Upload a financial file',
                        description: 'Start a new pipeline run',
                        icon: ArrowDownToLine,
                        page: 'Data ingestion',
                      },
                      {
                        label: 'Review pipeline runs',
                        description: 'Monitor processing status',
                        icon: Activity,
                        page: 'Pipeline runs',
                      },
                      {
                        label: 'Manage mappings',
                        description: 'View available data mappings',
                        icon: FileSpreadsheet,
                        page: 'Mappings',
                      },
                      {
                        label: 'Manage workspace users',
                        description: 'Control user access',
                        icon: Users,
                        page: 'User management',
                      },
                    ].map(({ label, description, icon: Icon, page }) => (
                      <button
                        key={label}
                        onClick={() => selectPage(page)}
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
                      </button>
                    ))}
                  </div>
                </section>
              </div>

              <div className="mt-6 rounded-xl bg-[#101c35] p-6 text-white sm:flex sm:items-center sm:justify-between">
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-teal-400/15 p-3 text-teal-300">
                    <Zap size={22} />
                  </div>
                  <div>
                    <h3 className="font-semibold">Your financial data, organized.</h3>
                    <p className="mt-1 max-w-xl text-xs leading-5 text-slate-400">
                      Hazina provides structured ingestion, validation,
                      deduplication and monitoring for your financial data.
                    </p>
                  </div>
                </div>
                <span className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-teal-300 sm:mt-0">
                  <ShieldCheck size={16} /> Organization-aware processing
                </span>
              </div>
            </>
          ) : (
            <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
              <div className="mb-4 inline-flex rounded-xl bg-teal-50 p-3 text-teal-700">
                <Settings size={23} />
              </div>
              <h1 className="text-xl font-bold text-slate-900">{activePage}</h1>
              <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
                This workspace section is part of the Hazina frontend.
                Its interface and connection to the backend will be implemented
                in the next development phases.
              </p>
              <button
                onClick={() => selectPage('Dashboard')}
                className="mt-6 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-700"
              >
                Return to dashboard
              </button>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
