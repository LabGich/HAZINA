// AuthContext.logout() clears local tokens in its finally block
// even if the backend logout request fails.

import {
  Bell,
  ChevronDown,
  CircleHelp,
  LogOut,
  Menu,
  Search,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext'

interface HeaderProps {
  pageTitle: string
  onMenuClick: () => void
}

function Header({ pageTitle, onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [profileOpen, setProfileOpen] = useState(false)
  const [logoutError, setLogoutError] = useState('')

  const handleLogout = async () => {
    setLogoutError('')

    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      setLogoutError('Logout could not be completed. Please try again.')
    }
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0].toUpperCase())
        .join('')
    : 'H'

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
          <p className="text-xs text-slate-400">
            {user?.organization_name ?? 'Workspace'} / Overview
          </p>
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

        <div className="relative border-l border-slate-200 pl-3 sm:pl-5">
          <button
            type="button"
            onClick={() => setProfileOpen((open) => !open)}
            aria-expanded={profileOpen}
            aria-label="Open account menu"
            className="flex items-center gap-2"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#e0f2ef] text-sm font-bold text-teal-800">
              {initials}
            </div>

            <div className="hidden text-left sm:block">
              <p className="text-xs font-semibold text-slate-800">
                {user?.full_name ?? 'User'}
              </p>
              <p className="text-[10px] text-slate-400">
                {user?.role_code ?? 'Account'}
              </p>
            </div>

            <ChevronDown
              size={15}
              className="hidden text-slate-400 sm:block"
            />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-12 z-50 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <div className="border-b border-slate-100 px-3 py-3">
                <p className="truncate text-sm font-semibold text-slate-800">
                  {user?.full_name}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {user?.email}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {user?.organization_name}
                </p>
              </div>

              {logoutError && (
                <p role="alert" className="px-3 py-2 text-xs text-red-600">
                  {logoutError}
                </p>
              )}

              <button
                type="button"
                onClick={handleLogout}
                className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
              >
                <LogOut size={16} />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
