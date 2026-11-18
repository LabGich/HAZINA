
import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Database,
  RefreshCw,
} from 'lucide-react'

import { getSources, getMappings } from '../../services/ingestion'

import type {
  Mapping,
  Source,
} from '../../types/ingestion'

interface SourceMappings {
  source: Source
  mappings: Mapping[]
}

function MappingsPage() {
  const [data, setData] = useState<SourceMappings[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadMappings = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const sourceResponse = await getSources()

      const fileSources = sourceResponse.sources.filter(
        (source) => source.source_type === 'FILE',
      )

      const results = await Promise.all(
        fileSources.map(async (source) => {
          const response = await getMappings(source.source_name)

          return {
            source,
            mappings: response.mappings,
          }
        }),
      )

      setData(results)
    } catch {
      setError(
        'Unable to load mapping information. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadMappings()
  }, [loadMappings])

  const totalMappings = data.reduce(
    (total, item) => total + item.mappings.length,
    0,
  )

  const totalSources = data.filter(
    (item) => item.mappings.length > 0,
  ).length

  const defaultMappings = data.reduce(
    (total, item) =>
      total +
      item.mappings.filter((mapping) => mapping.is_default).length,
    0,
  )

  return (
    <div>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm text-slate-500">
            Browse the available transaction mapping configurations.
          </p>

          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Mappings
          </h1>
        </div>

        <button
          type="button"
          onClick={() => void loadMappings()}
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
            onClick={() => void loadMappings()}
            className="font-semibold hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Available sources</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : totalSources}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Registered mappings</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : totalMappings}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Default mappings</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading ? '...' : defaultMappings}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
          <RefreshCw size={18} className="animate-spin" />
          Loading mappings...
        </div>
      ) : error ? (
        <div className="flex min-h-48 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400">
          Mapping information is unavailable.
        </div>
      ) : data.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-slate-200 bg-white px-6 text-center">
          <Database size={30} className="mb-3 text-slate-300" />
          <h2 className="text-sm font-semibold text-slate-700">
            No mappings available
          </h2>
          <p className="mt-2 text-xs text-slate-400">
            No enabled file sources with valid mappings were found.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {data.map(({ source, mappings }) => (
            <section
              key={source.source_name}
              className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
            >
              <div className="flex flex-col justify-between gap-3 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-center">
                <div>
                  <h2 className="font-bold text-slate-900">
                    {source.source_name}
                  </h2>

                  <p className="mt-1 text-xs text-slate-500">
                    {source.description || 'No description available.'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                    FILE source
                  </span>

                  <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
                    {mappings.length} {mappings.length === 1 ? 'mapping' : 'mappings'}
                  </span>
                </div>
              </div>

              <div className="px-6 py-4">
                <p className="mb-2 text-xs font-semibold text-slate-500">
                  Supported source formats
                </p>

                <div className="flex flex-wrap gap-2">
                  {source.supported_formats.map((format) => (
                    <span
                      key={format}
                      className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600"
                    >
                      {format}
                    </span>
                  ))}
                </div>
              </div>

              {mappings.length === 0 ? (
                <div className="border-t border-slate-100 px-6 py-5 text-sm text-slate-400">
                  No valid mappings are currently available for this source.
                </div>
              ) : (
                <div className="overflow-x-auto border-t border-slate-100">
                  <table className="w-full min-w-[650px] text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-6 py-3 font-semibold">
                          Mapping ID
                        </th>
                        <th className="px-6 py-3 font-semibold">
                          Version
                        </th>
                        <th className="px-6 py-3 font-semibold">
                          Supported formats
                        </th>
                        <th className="px-6 py-3 font-semibold">
                          Description
                        </th>
                        <th className="px-6 py-3 font-semibold">
                          Status
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100">
                      {mappings.map((mapping) => (
                        <tr
                          key={`${mapping.mapping_id}-${mapping.mapping_version}`}
                          className="hover:bg-slate-50/70"
                        >
                          <td className="px-6 py-4 font-medium text-slate-800">
                            {mapping.mapping_id}
                          </td>

                          <td className="px-6 py-4 text-slate-600">
                            {mapping.mapping_version}
                          </td>

                          <td className="px-6 py-4">
                            <div className="flex flex-wrap gap-1.5">
                              {mapping.supported_formats.map((format) => (
                                <span
                                  key={format}
                                  className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600"
                                >
                                  {format}
                                </span>
                              ))}
                            </div>
                          </td>

                          <td className="px-6 py-4 text-slate-500">
                            {mapping.description || '—'}
                          </td>

                          <td className="px-6 py-4">
                            {mapping.is_default ? (
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                                <CheckCircle2 size={13} />
                                Default
                              </span>
                            ) : (
                              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500">
                                Available
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  )
}

export default MappingsPage
