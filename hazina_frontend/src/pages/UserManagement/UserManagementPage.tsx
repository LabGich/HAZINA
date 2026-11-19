
import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Shield,
  User,
  Users,
  XCircle,
} from 'lucide-react'

import { useAuth } from '../../contexts/AuthContext'
import { getOrganizationUsers } from '../../services/admin'

import type { AdminUser } from '../../types/admin'

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function UserManagementPage() {
  const { user: currentUser, isLoading: authLoading } = useAuth()

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await getOrganizationUsers()
      setUsers(result)
    } catch {
      setError('Unable to load organization users. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!authLoading && currentUser?.role_code === 'ADMIN') {
      void loadUsers()
    } else if (!authLoading) {
      setLoading(false)
    }
  }, [authLoading, currentUser, loadUsers])

  if (authLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
        <RefreshCw size={18} className="animate-spin" />
        Checking access...
      </div>
    )
  }

  if (currentUser?.role_code !== 'ADMIN') {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-red-200 bg-white px-6 text-center shadow-sm">
        <Shield size={32} className="mb-3 text-red-400" />

        <h2 className="text-lg font-semibold text-slate-800">
          Access denied
        </h2>

        <p className="mt-2 max-w-md text-sm text-slate-500">
          You must have the ADMIN role to manage organization users.
        </p>
      </div>
    )
  }

  const activeUsers = users.filter(
    (item) => item.user_is_active && item.membership_is_active,
  ).length

  const inactiveUsers = users.length - activeUsers

  const administrators = users.filter(
    (item) => item.role_code === 'ADMIN',
  ).length

  return (
    <div>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm text-slate-500">
            Manage users and access within your organization.
          </p>

          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            User management
          </h1>
        </div>

        <button
          type="button"
          onClick={() => void loadUsers()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-6 flex flex-col justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center"
        >
          <div className="flex items-start gap-2">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>

          <button
            type="button"
            onClick={() => void loadUsers()}
            className="font-semibold hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Organization users</p>
            <Users size={19} className="text-slate-400" />
          </div>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : users.length}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Active memberships</p>
            <CheckCircle2 size={19} className="text-emerald-500" />
          </div>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : activeUsers}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Administrators</p>
            <Shield size={19} className="text-teal-600" />
          </div>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : administrators}
          </p>
        </div>
      </div>

      {!loading && !error && (
        <div className="mb-4 flex items-center gap-2 text-xs text-slate-500">
          <XCircle size={14} />
          {inactiveUsers} inactive {inactiveUsers === 1 ? 'membership' : 'memberships'}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <h2 className="font-bold text-slate-900">
            Organization members
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Users belonging to your current organization.
          </p>
        </div>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
            <RefreshCw size={18} className="animate-spin" />
            Loading organization users...
          </div>
        ) : error ? (
          <div className="flex min-h-48 items-center justify-center text-sm text-slate-400">
            User information is unavailable.
          </div>
        ) : users.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
            <Users size={30} className="mb-3 text-slate-300" />

            <h3 className="text-sm font-semibold text-slate-700">
              No organization users found
            </h3>

            <p className="mt-2 text-xs text-slate-400">
              Organization members will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-semibold">User</th>
                  <th className="px-6 py-3 font-semibold">Role</th>
                  <th className="px-6 py-3 font-semibold">Account</th>
                  <th className="px-6 py-3 font-semibold">Membership</th>
                  <th className="px-6 py-3 font-semibold">Email</th>
                  <th className="px-6 py-3 font-semibold">Joined</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {users.map((item) => {
                  const isCurrentUser =
                    item.user_id === currentUser.user_id

                  const accountActive = item.user_is_active
                  const membershipActive = item.membership_is_active

                  return (
                    <tr
                      key={item.membership_id}
                      className="hover:bg-slate-50/70"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                            <User size={17} />
                          </div>

                          <div>
                            <p className="font-semibold text-slate-800">
                              {item.full_name}
                            </p>

                            <p className="mt-0.5 text-xs text-slate-500">
                              {item.email}
                            </p>

                            {isCurrentUser && (
                              <span className="mt-1 inline-block rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-semibold text-teal-700">
                                You
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                          {item.role_code}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            accountActive
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {accountActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            membershipActive
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {membershipActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 text-xs ${
                            item.email_verified
                              ? 'text-emerald-700'
                              : 'text-amber-700'
                          }`}
                        >
                          {item.email_verified ? (
                            <CheckCircle2 size={14} />
                          ) : (
                            <AlertCircle size={14} />
                          )}

                          {item.email_verified ? 'Verified' : 'Unverified'}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs text-slate-500">
                        {formatDate(item.membership_created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default UserManagementPage
