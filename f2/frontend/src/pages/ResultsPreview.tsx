import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, JobStatus, ExtractionResult } from '../api/client'

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'completed' ? 'badge-success' :
    status === 'failed'    ? 'badge-danger'  :
    status === 'processing'? 'badge-info'    : 'badge-warn'
  return <span className={`badge ${cls}`}>{status}</span>
}

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
          if (data.status === 'completed' || data.status === 'failed') clearInterval(intervalId)
        }
      } catch { if (!cancelled) setStatus(null) }
      finally   { if (!cancelled) setLoading(false) }
    }
    fetchStatus()
    intervalId = setInterval(fetchStatus, 2000)
    return () => { cancelled = true; clearInterval(intervalId) }
  }, [jobId])

  useEffect(() => {
    if (!jobId || status?.status !== 'completed') return
    api.get<{ extraction_results: ExtractionResult[] }>(`/jobs/results/${jobId}`)
      .then(({ data }) => setResults(data.extraction_results || []))
      .catch(() => setResults([]))
  }, [jobId, status?.status])

  const download = async () => {
    if (!jobId) return
    try {
      const { data } = await api.get(`/jobs/download/${jobId}`, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([data]))
      const a = document.createElement('a'); a.href = url; a.download = `extraction_${jobId}.xlsx`; a.click()
      URL.revokeObjectURL(url); toast.success('Download started')
    } catch { toast.error('Download failed') }
  }

  if (loading && !status) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '6rem 0', gap: '0.75rem' }}>
        <span className="spinner" style={{ width: 28, height: 28 }} />
        <p style={{ color: 'var(--text-3)', fontSize: '0.875rem' }}>Loading job status…</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div style={{ textAlign: 'center', padding: '6rem 0' }}>
        <p style={{ color: 'var(--text-2)', marginBottom: '1rem' }}>Job not found.</p>
        <button onClick={() => navigate('/')} className="btn btn-ghost">Back to Dashboard</button>
      </div>
    )
  }

  const isComplete  = status.status === 'completed'
  const isFailed    = status.status === 'failed'
  const isProcessing = status.status === 'processing' || status.status === 'uploaded'
  const pct = status.progress_percent ?? 0

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace", letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            Job · <span style={{ color: 'var(--text-2)' }}>{jobId?.slice(0, 8)}</span>
          </p>
          <h1 className="font-display" style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            Results
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Link to="/upload" className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>New upload</Link>
          <button onClick={() => navigate('/')} className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>Dashboard</button>
        </div>
      </div>

      {/* Status card */}
      <div className="animate-fadeUp-1 card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <StatusBadge status={status.status} />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace" }}>
              {status.processed_files} / {status.total_files} files
            </span>
            {isProcessing && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div style={{ width: 160 }}>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                </div>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace" }}>{pct}%</span>
              </div>
            )}
          </div>
          {isComplete && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={download} className="btn btn-primary">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download Excel
              </button>
              <Link to="/history" className="btn btn-ghost">History</Link>
            </div>
          )}
        </div>

        {/* Processing spinner */}
        {isProcessing && (
          <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="spinner" style={{ width: 16, height: 16 }} />
            <span style={{ fontSize: '0.83rem', color: 'var(--text-3)' }}>Processing files… this may take a moment</span>
          </div>
        )}

        {status.error_message && (
          <p style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--danger)', background: 'rgba(244,63,94,0.08)', padding: '0.65rem 0.9rem', borderRadius: 8, border: '1px solid rgba(244,63,94,0.2)' }}>
            {status.error_message}
          </p>
        )}
      </div>

      {/* Results table */}
      {isComplete && results.length === 0 && !status.error_message && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-3)', fontSize: '0.875rem' }}>No extraction data to preview.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="animate-fadeUp-2 card" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto', maxHeight: 480, overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>File</th>
                  {Object.keys(results[0]?.fields || {}).slice(0, 8).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: "'DM Mono', monospace", fontSize: '0.78rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.file_name}
                    </td>
                    {Object.values(r.fields || {}).slice(0, 8).map((v, j) => (
                      <td key={j} style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {v != null ? String(v) : <span style={{ color: 'var(--text-3)' }}>—</span>}
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
