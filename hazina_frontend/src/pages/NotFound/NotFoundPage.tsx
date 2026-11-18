import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <p className="text-sm font-semibold text-teal-700">404</p>

      <h1 className="mt-2 text-xl font-bold text-slate-900">
        Page not found
      </h1>

      <p className="mt-2 text-sm text-slate-500">
        The page you are looking for does not exist.
      </p>

      <Link
        to="/"
        className="mt-6 inline-flex rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-700"
      >
        Return to dashboard
      </Link>
    </section>
  )
}

export default NotFoundPage