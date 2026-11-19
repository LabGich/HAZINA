
import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Plus,
  RefreshCw,
  Shield,
  User,
  Users,
  X,
} from 'lucide-react'

import { useAuth } from '../../contexts/AuthContext'
import {
  createOrganizationUser,
  getOrganizationUsers,
  updateOrganizationUser,
} from '../../services/admin'

import type { AdminUser } from '../../types/admin'
import type { UserRole } from '../../types/auth'

const roles: UserRole[] = ['ADMIN', 'OPERATOR', 'VIEWER']

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function getApiError(error: unknown): string {
  const response = (
    error as {
      response?: {
        data?: {
          detail?: unknown
        }
      }
    }
  )?.response?.data

  const detail = response?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item

        if (item && typeof item === 'object') {
          const entry = item as {
            loc?: unknown[]
            msg?: string
          }

          const location = entry.loc?.join(' → ')

          return location
            ? `${location}: ${entry.msg ?? 'Invalid value'}`
            : entry.msg ?? 'Invalid value'
        }

        return String(item)
      })
      .join('; ')
  }

  return 'The request could not be completed. Please try again.'
}

function UserManagementPage() {
  const { user: currentUser, isLoading: authLoading } = useAuth()

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null)
  const [roleDrafts, setRoleDrafts] = useState<Record<number, UserRole>>({})
  const [updateError, setUpdateError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [roleCode, setRoleCode] = useState<UserRole>('VIEWER')

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

  function resetCreateForm() {
    setFullName('')
    setEmail('')
    setPassword('')
    setRoleCode('VIEWER')
    setCreateError(null)
  }

  async function handleCreateUser(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setCreateError(null)
    setSuccessMessage(null)
    setUpdateError(null)

    if (fullName.trim().length === 0) {
      setCreateError('Full name is required.')
      return
    }

    if (password.length < 12) {
      setCreateError('Password must contain at least 12 characters.')
      return
    }

    setCreating(true)

    try {
      await createOrganizationUser({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role_code: roleCode,
      })

      resetCreateForm()
      setShowCreateForm(false)
      setSuccessMessage('User created successfully.')

      await loadUsers()
    } catch (requestError) {
      setCreateError(getApiError(requestError))
    } finally {
      setCreating(false)
    }
  }

  async function handleUpdateUser(
    userId: number,
    payload: { role_code?: UserRole; is_active?: boolean },
  ) {
    setUpdatingUserId(userId)
    setUpdateError(null)
    setSuccessMessage(null)
    setCreateError(null)

    try {
      await updateOrganizationUser(userId, payload)

      setSuccessMessage(
        payload.role_code
          ? 'User role updated successfully.'
          : payload.is_active
            ? 'User membership activated successfully.'
            : 'User membership deactivated successfully.',
      )

      setRoleDrafts((previous) => {
        const updated = { ...previous }
        delete updated[userId]
        return updated
      })

      await loadUsers()
    } catch (requestError) {
      setUpdateError(getApiError(requestError))
    } finally {
      setUpdatingUserId(null)
    }
  }

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

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadUsers()}
            disabled={loading || updatingUserId !== null || creating}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={loading ? 'animate-spin' : ''}
            />
            Refresh
          </button>

          <button
            type="button"
            onClick={() => {
              setSuccessMessage(null)
              setCreateError(null)
              setUpdateError(null)
              setShowCreateForm(true)
            }}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
          >
            <Plus size={17} />
            Add user
          </button>
        </div>
      </div>

      {successMessage && (
        <div
          role="status"
          className="mb-6 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          <CheckCircle2 size={18} />
          {successMessage}
        </div>
      )}

      {updateError && (
        <div
          role="alert"
          className="mb-6 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <AlertCircle size={18} />
          {updateError}
        </div>
      )}

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

      {showCreateForm && (
        <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-slate-900">
                Create organization user
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Add a new user to your organization.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false)
                resetCreateForm()
              }}
              disabled={creating}
              aria-label="Close form"
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
            >
              <X size={19} />
            </button>
          </div>

          {createError && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              <AlertCircle size={17} className="mt-0.5 shrink-0" />
              <span>{createError}</span>
            </div>
          )}

          <form onSubmit={handleCreateUser}>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="user-full-name"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Full name
                </label>

                <input
                  id="user-full-name"
                  type="text"
                  required
                  maxLength={150}
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Enter full name"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                />
              </div>

              <div>
                <label
                  htmlFor="user-email"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Email address
                </label>

                <input
                  id="user-email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="user@example.com"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                />
              </div>

              <div>
                <label
                  htmlFor="user-password"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Initial password
                </label>

                <input
                  id="user-password"
                  type="password"
                  required
                  minLength={12}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="At least 12 characters"
                  autoComplete="new-password"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                />

                <p className="mt-1.5 text-xs text-slate-400">
                  Minimum 12 characters.
                </p>
              </div>

              <div>
                <label
                  htmlFor="user-role"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Organization role
                </label>

                <select
                  id="user-role"
                  value={roleCode}
                  onChange={(event) =>
                    setRoleCode(event.target.value as UserRole)
                  }
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                >
                  {roles.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false)
                  resetCreateForm()
                }}
                disabled={creating}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={creating}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {creating && (
                  <RefreshCw size={16} className="animate-spin" />
                )}
                {creating ? 'Creating user...' : 'Create user'}
              </button>
            </div>
          </form>
        </section>
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
        <div className="mb-4 text-xs text-slate-500">
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
            <table className="w-full min-w-[1050px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-semibold">User</th>
                  <th className="px-6 py-3 font-semibold">Role</th>
                  <th className="px-6 py-3 font-semibold">Account</th>
                  <th className="px-6 py-3 font-semibold">Membership</th>
                  <th className="px-6 py-3 font-semibold">Email</th>
                  <th className="px-6 py-3 font-semibold">Joined</th>
                  <th className="px-6 py-3 font-semibold">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {users.map((item) => {
                  const isCurrentUser =
                    item.user_id === currentUser.user_id

                  const isUpdating = updatingUserId === item.user_id
                  const selectedRole =
                    roleDrafts[item.user_id] ?? item.role_code
                  const roleChanged = selectedRole !== item.role_code

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
                            item.user_is_active
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {item.user_is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            item.membership_is_active
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {item.membership_is_active ? 'Active' : 'Inactive'}
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

                      <td className="px-6 py-4">
                        <div className="flex min-w-48 flex-col gap-2">
                          <div className="flex items-center gap-2">
                            <select
                              aria-label={`Role for ${item.full_name}`}
                              value={selectedRole}
                              disabled={
                                isCurrentUser ||
                                isUpdating ||
                                updatingUserId !== null
                              }
                              onChange={(event) =>
                                setRoleDrafts((previous) => ({
                                  ...previous,
                                  [item.user_id]: event.target.value as UserRole,
                                }))
                              }
                              className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-teal-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                            >
                              {roles.map((role) => (
                                <option key={role} value={role}>
                                  {role}
                                </option>
                              ))}
                            </select>

                            <button
                              type="button"
                              disabled={
                                !roleChanged ||
                                isUpdating ||
                                updatingUserId !== null ||
                                isCurrentUser
                              }
                              onClick={() =>
                                void handleUpdateUser(item.user_id, {
                                  role_code: selectedRole,
                                })
                              }
                              className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
                            >
                              {isUpdating ? 'Saving...' : 'Save'}
                            </button>
                          </div>

                          <button
                            type="button"
                            disabled={
                              isCurrentUser ||
                              isUpdating ||
                              updatingUserId !== null
                            }
                            onClick={() =>
                              void handleUpdateUser(item.user_id, {
                                is_active: !item.membership_is_active,
                              })
                            }
                            className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
                              item.membership_is_active
                                ? 'border-red-200 text-red-700 hover:bg-red-50'
                                : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                            }`}
                          >
                            {isUpdating
                              ? 'Updating...'
                              : item.membership_is_active
                                ? 'Deactivate membership'
                                : 'Activate membership'}
                          </button>

                          {isCurrentUser && (
                            <span className="text-[10px] text-slate-400">
                              Your own access cannot be changed here.
                            </span>
                          )}
                        </div>
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
