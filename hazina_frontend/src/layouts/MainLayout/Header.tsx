import {
  Bell,
  ChevronDown,
  CircleHelp,
  Menu,
  Search,
} from 'lucide-react'

interface HeaderProps {
  pageTitle: string
  onMenuClick: () => void
}

function Header({ pageTitle, onMenuClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-8">
      <div className="flex items-center gap-3">
        <button
          aria-label="Open navigation"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
        >
          <Menu size={22} />
        </button>

        <div>
          <p className="text-xs text-slate-400">Workspace / Overview</p>
          <h2 className="text-lg font-bold text-slate-900">{pageTitle}</h2>
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
  )
}

export default Header