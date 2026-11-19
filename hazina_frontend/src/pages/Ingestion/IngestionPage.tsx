
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react'

import {
  getSources,
  getMappings,
  submitPipelineFiles,
} from '../../services/ingestion'

import type { Source, Mapping } from '../../types/ingestion'
import type {
  PipelineSubmissionResponse,
  PipelineUpload,
} from '../../services/ingestion'

const MAX_FILE_SIZE = 10 * 1024 * 1024

interface UploadRow {
  id: string
  file: File
  source_name: string
  mapping_id: string
  mapping_version: string
  mapping_supported_formats: string[]
  mapping_loading: boolean
  mapping_error: string | null
}

function normalizeFormat(format: string): string {
  return format.replace('.', '').trim().toUpperCase()
}

function getFileExtension(fileName: string): string {
  return fileName.split('.').pop()?.toUpperCase() ?? ''
}

function isFormatSupported(
  formats: string[],
  extension: string,
): boolean {
  return formats.some(
    (format) => normalizeFormat(format) === extension,
  )
}

function getCompatibleMappings(
  mappings: Mapping[],
  extension: string,
): Mapping[] {
  return mappings.filter((mapping) =>
    isFormatSupported(mapping.supported_formats, extension),
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function getSubmissionError(error: unknown): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error
  ) {
    const response = error.response as {
      data?: { detail?: unknown }
    }

    const detail = response.data?.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === 'string') {
            return item
          }

          if (typeof item === 'object' && item !== null) {
            const validationError = item as {
              loc?: unknown[]
              msg?: unknown
            }

            const location = Array.isArray(validationError.loc)
              ? validationError.loc.join(' → ')
              : ''

            const message =
              typeof validationError.msg === 'string'
                ? validationError.msg
                : 'Invalid input'

            return location
              ? `${location}: ${message}`
              : message
          }

          return String(item)
        })
        .join('; ')
    }

    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail)
    }
  }

  return 'Unable to submit the files. Please try again.'
}

function IngestionPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [sources, setSources] = useState<Source[]>([])
  const [mappingCatalog, setMappingCatalog] = useState<
    Record<string, Mapping[]>
  >({})
  const [sourcesLoading, setSourcesLoading] = useState(true)
  const [sourcesError, setSourcesError] = useState<string | null>(null)

  const [uploads, setUploads] = useState<UploadRow[]>([])
  const [pageError, setPageError] = useState<string | null>(null)

  const [submitting, setSubmitting] = useState(false)
  const [submission, setSubmission] =
    useState<PipelineSubmissionResponse | null>(null)

  const loadSources = useCallback(async () => {
    setSourcesLoading(true)
    setSourcesError(null)

    try {
      const response = await getSources()

      const fileSources = response.sources.filter(
        (source) => source.source_type === 'FILE',
      )

      const mappingsBySource: Record<string, Mapping[]> = {}

      await Promise.all(
        fileSources.map(async (source) => {
          const mappingResponse = await getMappings(source.source_name)
          mappingsBySource[source.source_name] =
            mappingResponse.mappings
        }),
      )

      const configuredSources = fileSources.filter((source) =>
        (mappingsBySource[source.source_name] ?? []).some(
          (mapping) => mapping.supported_formats.length > 0,
        ),
      )

      setMappingCatalog(mappingsBySource)
      setSources(configuredSources)
    } catch {
      setSources([])
      setMappingCatalog({})
      setSourcesError(
        'Unable to load available sources and mappings. Please try again.',
      )
    } finally {
      setSourcesLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadSources()
  }, [loadSources])

  const handleAddFiles = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFiles = Array.from(event.target.files ?? [])

    setPageError(null)
    setSubmission(null)

    const newRows: UploadRow[] = []

    for (const file of selectedFiles) {
      if (file.size > MAX_FILE_SIZE) {
        setPageError(
          `${file.name} exceeds the 10 MB file size limit.`,
        )
        continue
      }

      newRows.push({
        id: crypto.randomUUID(),
        file,
        source_name: '',
        mapping_id: '',
        mapping_version: '',
        mapping_supported_formats: [],
        mapping_loading: false,
        mapping_error: null,
      })
    }

    setUploads((current) => [...current, ...newRows])

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSourceChange = (
    rowId: string,
    sourceName: string,
  ) => {
    setPageError(null)
    setSubmission(null)

    const row = uploads.find((upload) => upload.id === rowId)

    if (!row) return

    const extension = getFileExtension(row.file.name)

    const compatibleMappings = getCompatibleMappings(
      mappingCatalog[sourceName] ?? [],
      extension,
    )

    const mapping =
      compatibleMappings.find((item) => item.is_default) ??
      compatibleMappings[0]

    if (sourceName && !mapping) {
      setPageError(
        `${sourceName} does not have a configured mapping for ${extension} files.`,
      )
      return
    }

    setUploads((current) =>
      current.map((upload) =>
        upload.id === rowId
          ? {
              ...upload,
              source_name: sourceName,
              mapping_id: mapping?.mapping_id ?? '',
              mapping_version: mapping?.mapping_version ?? '',
              mapping_supported_formats:
                mapping?.supported_formats ?? [],
              mapping_loading: false,
              mapping_error: mapping
                ? null
                : sourceName
                  ? `No mapping is available for ${extension} files from ${sourceName}.`
                  : null,
            }
          : upload,
      ),
    )
  }

  const handleRemoveFile = (rowId: string) => {
    setUploads((current) =>
      current.filter((upload) => upload.id !== rowId),
    )

    setPageError(null)
    setSubmission(null)
  }

  const validateUploads = (): string | null => {
    if (uploads.length === 0) {
      return 'Add at least one file before submitting.'
    }

    for (const upload of uploads) {
      const extension = getFileExtension(upload.file.name)

      const compatibleSources = sources.filter((source) =>
        getCompatibleMappings(
          mappingCatalog[source.source_name] ?? [],
          extension,
        ).length > 0,
      )

      if (compatibleSources.length === 0) {
        return `No configured source has a valid mapping for ${extension} files (${upload.file.name}).`
      }

      if (!upload.source_name) {
        return `Select a source for ${upload.file.name}.`
      }

      if (upload.mapping_loading) {
        return `Wait for the mapping to load for ${upload.file.name}.`
      }

      if (upload.mapping_error) {
        return upload.mapping_error
      }

      if (!upload.mapping_id || !upload.mapping_version) {
        return `A valid mapping is required for ${upload.file.name}.`
      }

      const source = sources.find(
        (item) => item.source_name === upload.source_name,
      )

      if (
        !source ||
        getCompatibleMappings(
          mappingCatalog[upload.source_name] ?? [],
          extension,
        ).length === 0
      ) {
        return `${upload.file.name} is not supported by a configured mapping for ${upload.source_name}.`
      }

      if (
        !isFormatSupported(
          upload.mapping_supported_formats,
          extension,
        )
      ) {
        return `The selected mapping ${upload.mapping_id} does not support ${extension} files.`
      }
    }

    return null
  }

  const handleSubmit = async () => {
    const validationError = validateUploads()

    if (validationError) {
      setPageError(validationError)
      return
    }

    const payload: PipelineUpload[] = uploads.map((upload) => ({
      file: upload.file,
      source_name: upload.source_name,
      mapping_id: upload.mapping_id,
      mapping_version: upload.mapping_version,
    }))

    setSubmitting(true)
    setPageError(null)
    setSubmission(null)

    try {
      const response = await submitPipelineFiles(payload)
      setSubmission(response)
    } catch (error) {
      setPageError(getSubmissionError(error))
    } finally {
      setSubmitting(false)
    }
  }

  const supportedFormats = Array.from(
    new Set(
      sources.flatMap((source) =>
        (mappingCatalog[source.source_name] ?? []).flatMap(
          (mapping) => mapping.supported_formats,
        ),
      ),
    ),
  ).join(', ')

  return (
    <div>
      <div className="mb-8">
        <p className="text-sm text-slate-500">
          Upload and process financial data from your supported sources.
        </p>

        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
          Data ingestion
        </h1>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Selected files</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {uploads.length}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Available file sources</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {sourcesLoading ? '...' : sources.length}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Maximum file size</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            10 MB
          </p>
        </div>
      </div>

      {sourcesError && (
        <div
          role="alert"
          className="mb-6 flex flex-col justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center"
        >
          <span>{sourcesError}</span>

          <button
            type="button"
            onClick={() => void loadSources()}
            className="font-semibold hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      {pageError && (
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{pageError}</span>
        </div>
      )}

      {submission && (
        <div
          role="status"
          className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5"
        >
          <div className="flex items-start gap-3">
            <CheckCircle2
              size={22}
              className="mt-0.5 shrink-0 text-emerald-600"
            />

            <div className="min-w-0 flex-1">
              <h2 className="font-bold text-emerald-900">
                Pipeline submitted successfully
              </h2>

              <p className="mt-1 text-sm text-emerald-800">
                Run #{submission.run_id} — {submission.run_status}
              </p>

              <p className="mt-1 text-xs text-emerald-700">
                {submission.source_executions.length} source executions
                submitted.
              </p>

              {submission.report_error && (
                <p className="mt-2 text-xs text-amber-800">
                  The pipeline report could not be generated:{' '}
                  {submission.report_error}
                </p>
              )}

              <Link
                to={`/pipeline-runs/${submission.run_id}`}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800"
              >
                View pipeline run
              </Link>
            </div>
          </div>
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-bold text-slate-900">
              Upload financial files
            </h2>

            <p className="mt-1 text-xs text-slate-400">
              Add one or more files and configure each source independently.
            </p>
          </div>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={sourcesLoading || Boolean(sourcesError) || submitting}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus size={17} />
            Add files
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".csv,.json,.jsonl,.xlsx,.parquet"
          onChange={handleAddFiles}
          className="hidden"
        />

        {sourcesLoading ? (
          <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
            <RefreshCw size={17} className="animate-spin" />
            Loading available sources and mappings...
          </div>
        ) : sourcesError ? (
          <div className="flex min-h-64 items-center justify-center text-sm text-slate-400">
            Source and mapping information is unavailable.
          </div>
        ) : uploads.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
            <div className="mb-4 rounded-full bg-teal-50 p-4">
              <Upload size={28} className="text-teal-600" />
            </div>

            <h3 className="text-sm font-semibold text-slate-700">
              No files selected
            </h3>

            <p className="mt-2 max-w-md text-xs leading-5 text-slate-400">
              Add your financial statement files to begin. Each file can
              have its own source and mapping configuration.
            </p>

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mt-5 inline-flex items-center gap-2 rounded-lg border border-teal-200 bg-white px-4 py-2.5 text-sm font-semibold text-teal-700 transition hover:bg-teal-50"
            >
              <Plus size={16} />
              Choose files
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {uploads.map((upload, index) => {
              const selectedSource = sources.find(
                (source) =>
                  source.source_name === upload.source_name,
              )

              const extension = getFileExtension(upload.file.name)

              const compatibleSources = sources.filter((source) =>
                getCompatibleMappings(
                  mappingCatalog[source.source_name] ?? [],
                  extension,
                ).length > 0,
              )

              return (
                <div
                  key={upload.id}
                  className="p-5 sm:p-6"
                >
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="rounded-lg bg-slate-100 p-2.5 text-slate-600">
                        <FileText size={20} />
                      </div>

                      <div className="min-w-0">
                        <p className="break-all text-sm font-semibold text-slate-800">
                          {upload.file.name}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          {formatFileSize(upload.file.size)}
                          {' · '}
                          {extension}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRemoveFile(upload.id)}
                      disabled={submitting}
                      aria-label={`Remove ${upload.file.name}`}
                      className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label
                        htmlFor={`source-${upload.id}`}
                        className="mb-2 block text-xs font-semibold text-slate-600"
                      >
                        Source
                      </label>

                      <select
                        id={`source-${upload.id}`}
                        value={upload.source_name}
                        disabled={submitting}
                        onChange={(event) =>
                          handleSourceChange(
                            upload.id,
                            event.target.value,
                          )
                        }
                        className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:bg-slate-50"
                      >
                        <option value="">Select source</option>

                        {compatibleSources.map((source) => (
                          <option
                            key={source.source_name}
                            value={source.source_name}
                          >
                            {source.source_name}
                          </option>
                        ))}
                      </select>

                      {compatibleSources.length === 0 ? (
                        <p className="mt-2 text-xs text-red-600">
                          No configured mapping supports {extension} files.
                        </p>
                      ) : selectedSource ? (
                        <p className="mt-2 text-xs text-slate-400">
                          {selectedSource.description}
                        </p>
                      ) : (
                        <p className="mt-2 text-xs text-slate-400">
                          Choose a source with a configured mapping for {extension} files.
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="mb-2 block text-xs font-semibold text-slate-600">
                        Mapping
                      </label>

                      <div className="flex min-h-10 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600">
                        {upload.mapping_loading ? (
                          <span className="flex items-center gap-2 text-slate-400">
                            <RefreshCw
                              size={14}
                              className="animate-spin"
                            />
                            Loading mapping...
                          </span>
                        ) : upload.mapping_error ? (
                          <span className="text-red-600">
                            {upload.mapping_error}
                          </span>
                        ) : upload.mapping_id ? (
                          <span>
                            {upload.mapping_id}
                            <span className="ml-2 text-xs text-slate-400">
                              v{upload.mapping_version}
                            </span>
                          </span>
                        ) : (
                          <span className="text-slate-400">
                            Select a source to load its compatible mapping
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {selectedSource && (
                    <p className="mt-3 text-xs text-slate-400">
                      Mapping-supported formats:{' '}
                      {(
                        mappingCatalog[selectedSource.source_name] ?? []
                      )
                        .flatMap((mapping) => mapping.supported_formats)
                        .filter(
                          (format, formatIndex, formats) =>
                            formats.indexOf(format) === formatIndex,
                        )
                        .join(', ')}
                    </p>
                  )}

                  <p className="mt-3 text-xs font-medium text-slate-400">
                    File {index + 1} of {uploads.length}
                  </p>
                </div>
              )
            })}
          </div>
        )}

        <div className="flex flex-col justify-between gap-4 border-t border-slate-100 bg-slate-50/70 px-6 py-5 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-medium text-slate-600">
              Supported formats
            </p>

            <p className="mt-1 text-xs text-slate-400">
              {supportedFormats || 'Loading formats...'}
              {' · '}
              Maximum 10 MB per file
            </p>
          </div>

          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={
              submitting ||
              sourcesLoading ||
              Boolean(sourcesError) ||
              uploads.length === 0 ||
              uploads.some(
                (upload) =>
                  upload.mapping_loading ||
                  Boolean(upload.mapping_error),
              )
            }
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Upload size={16} />
                Submit for processing
              </>
            )}
          </button>
        </div>
      </section>
    </div>
  )
}

export default IngestionPage
