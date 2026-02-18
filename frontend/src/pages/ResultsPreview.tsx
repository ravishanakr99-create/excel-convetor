import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, JobStatus, ExtractionResult } from '../api/client'

export default function ResultsPreview() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [results, setResults] = useState<ExtractionResult[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    let intervalId: ReturnType<typeof setInterval>
    const fetchStatus = async () => {
      try {
        const { data } = await api.get<JobStatus>(`/jobs/status/${jobId}`)
        if (!cancelled) {
          setStatus(data)
          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(intervalId)
          }
        }
      } catch {
        if (!cancelled) setStatus(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchStatus()
    intervalId = setInterval(fetchStatus, 2000)
    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId || status?.status !== 'completed') return
    api
      .get<{ extraction_results: ExtractionResult[] }>(`/jobs/results/${jobId}`)
      .then(({ data }) => setResults(data.extraction_results || []))
      .catch(() => setResults([]))
  }, [jobId, status?.status])

  const download = async () => {
    if (!jobId) return
    try {
      const { data } = await api.get(`/jobs/download/${jobId}`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `extraction_${jobId}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Download started')
    } catch {
      toast.error('Download failed')
    }
  }

  if (loading && !status) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <div className="animate-spin h-8 w-8 border-2 border-primary-500 border-t-transparent rounded-full" />
        <p className="text-slate-400">Loading job status...</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 mb-4">Job not found</p>
        <button
          onClick={() => navigate('/')}
          className="text-primary-400 hover:text-primary-300"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  const isComplete = status.status === 'completed'
  const isFailed = status.status === 'failed'
  const isProcessing = status.status === 'processing' || status.status === 'uploaded'

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Results</h1>
        <div className="flex gap-2">
          <Link
            to="/upload"
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors"
          >
            Upload New
          </Link>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            Dashboard
          </button>
        </div>
      </div>

      {/* Status panel */}
      <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 mb-6">
        <h2 className="font-medium text-slate-200 mb-3">Processing Status</h2>
        <div className="flex flex-wrap gap-4 items-center">
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              isComplete
                ? 'bg-green-500/20 text-green-400'
                : isFailed
                ? 'bg-red-500/20 text-red-400'
                : 'bg-primary-500/20 text-primary-400'
            }`}
          >
            {status.status}
          </span>
          <span className="text-slate-400 text-sm">
            {status.processed_files} / {status.total_files} files
          </span>
          {isProcessing && (
            <div className="flex-1 max-w-xs">
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all duration-500"
                  style={{ width: `${status.progress_percent}%` }}
                />
              </div>
            </div>
          )}
        </div>
        {status.error_message && (
          <p className="mt-3 text-sm text-red-400">{status.error_message}</p>
        )}
        {isComplete && (
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={download}
              className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors"
            >
              Download Excel
            </button>
            <Link
              to="/history"
              className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium transition-colors"
            >
              View History
            </Link>
          </div>
        )}
      </div>

      {/* Results preview table */}
      {isComplete && results.length === 0 && !status.error_message && (
        <p className="text-slate-400 py-8 text-center">No extraction data to preview.</p>
      )}
      {results.length > 0 && (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/80 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-slate-300 font-medium">File</th>
                  {Object.keys(results[0]?.fields || {}).slice(0, 8).map((col) => (
                    <th key={col} className="px-4 py-3 text-left text-slate-300 font-medium">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-t border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-2 text-slate-400">{r.file_name}</td>
                    {Object.values(r.fields || {}).slice(0, 8).map((v, j) => (
                      <td key={j} className="px-4 py-2 text-slate-300 max-w-[200px] truncate">
                        {v != null ? String(v) : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
