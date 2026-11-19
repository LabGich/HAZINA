
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Building2,
  CheckCircle2,
  LogOut,
  Mail,
  ShieldCheck,
  User,
} from 'lucide-react'

import { useAuth } from '../../contexts/AuthContext'

function SettingsPage() {
  const { user, isLoading, logout } = useAuth()
  const navigate = useNavigate()

  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')

  const handleLogout = async () => {
    setIsLoggingOut(true)
    setLogoutError('')

    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      setLogoutError(
        'There was a problem ending your session. Your local session has been cleared.',
      )
      navigate('/login', { replace: true })
    } finally {
      setIsLoggingOut(false)
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-500">
          Loading account information...
        </p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8">
        <h1 className="text-xl font-bold text-slate-900">
          Account unavailable
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Please sign in to view your account settings.
        </p>
      </div>
    )
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          View your account, organization, and access information.
        </p>
      </div>

      {logoutError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {logoutError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-lg bg-teal-50 p-2.5 text-teal-700">
              <User size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">
                Personal details
              </h2>
              <p className="text-sm text-slate-500">
                Your account information
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Full name
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {user.full_name}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Email address
              </p>
              <div className="mt-1 flex items-center gap-2">
                <Mail size={15} className="text-slate-400" />
                <p className="text-sm font-medium text-slate-800">
                  {user.email}
                </p>
              </div>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                User ID
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {user.user_id}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2.5 text-blue-700">
              <Building2 size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">
                Organization
              </h2>
              <p className="text-sm text-slate-500">
                Your organization's details
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Organization name
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {user.organization_name}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Organization slug
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {user.organization_slug}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Organization ID
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {user.organization_id}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-lg bg-purple-50 p-2.5 text-purple-700">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">
                Access and security
              </h2>
              <p className="text-sm text-slate-500">
                Your assigned access level
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Assigned role
              </p>
              <span className="mt-2 inline-flex rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
                {user.role_code}
              </span>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Session status
              </p>
              <div className="mt-2 flex items-center gap-2 text-sm font-medium text-green-700">
                <CheckCircle2 size={16} />
                Authenticated
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-lg bg-red-50 p-2.5 text-red-600">
              <LogOut size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">
                Session
              </h2>
              <p className="text-sm text-slate-500">
                Manage your current session
              </p>
            </div>
          </div>

          <p className="mb-5 text-sm leading-6 text-slate-600">
            Sign out of Hazina on this browser. You will need to sign
            in again to access your organization workspace.
          </p>

          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <LogOut size={16} />
            {isLoggingOut ? 'Signing out...' : 'Sign out'}
          </button>
        </div>
      </div>
    </section>
  )
}

export default SettingsPage
