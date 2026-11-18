
import { Outlet } from 'react-router-dom'

function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Hazina
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Financial Transactions Pipeline
          </p>
        </div>

        <Outlet />

        <p className="mt-8 text-center text-xs text-slate-400">
          Secure financial data management
        </p>
      </div>
    </div>
  )
}

export default AuthLayout
