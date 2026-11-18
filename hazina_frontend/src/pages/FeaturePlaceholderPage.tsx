//This file is shared by anyunfinished workspace routes
// so we don't need  duplicate placeholder components

import { Settings } from 'lucide-react'
import { Link } from 'react-router-dom'

interface FeaturePlaceholderPageProps {
  title: string
}

function FeaturePlaceholderPage({ title }: FeaturePlaceholderPageProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="mb-4 inline-flex rounded-xl bg-teal-50 p-3 text-teal-700">
        <Settings size={23} />
      </div>

      <h1 className="text-xl font-bold text-slate-900">{title}</h1>

      <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
        This workspace section is part of the Hazina frontend.
        Its interface and connection to the backend will be implemented
        in the next development phases.
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

export default FeaturePlaceholderPage