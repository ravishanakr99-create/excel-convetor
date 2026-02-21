import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, JobHistoryItem } from '../api/client'

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'completed' ? 'badge-success' :
    status === 'failed'    ? 'badge-danger'  :
    status === 'processing'? 'badge-info'    : 'badge-warn'
  return <span className={`badge ${cls}`}>{status}</span>
}

export default function History() {
  const [jobs, setJobs] = useState<JobHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const navigate = useNavigate()

  const fetchHistory = () => {
    setLoading(true)
    api.get<JobHistoryItem[]>('/jobs/history')
      .then(({ data }) => setJobs(data))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchHistory() }, [])

  const handleDelete = async (jobId: string) => {
    if (!confirm('Delete this job? This cannot be undone.')) return
    setDeleting(jobId)
    try {
      await api.delete(`/jobs/delete/${jobId}`)
      setJobs((j) => j.filter((x) => x.job_id !== jobId))
    } catch { alert('Failed to delete job') }
    finally { setDeleting(null) }
  }

  const handleDeleteAll = async () => {
    if (!confirm(`Delete all ${jobs.length} jobs? This cannot be undone.`)) return
    setDeleting('all')
    try {
      await api.delete('/jobs/delete-all')
      setJobs([])
    } catch { alert('Failed to delete all jobs') }
    finally { setDeleting(null) }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '5rem 0', gap: '0.75rem' }}>
        <span className="spinner" />
        <span style={{ color: 'var(--text-3)', fontSize: '0.875rem' }}>Loading history…</span>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace", letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            Past jobs
          </p>
          <h1 className="font-display" style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            History
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignSelf: 'flex-end' }}>
          {jobs.length > 0 && (
            <button 
              onClick={handleDeleteAll} 
              disabled={deleting === 'all'}
              className="btn btn-danger"
              style={{ fontSize: '0.85rem' }}
            >
              {deleting === 'all' ? 'Deleting…' : 'Delete All'}
            </button>
          )}
          <button onClick={fetchHistory} className="btn btn-ghost">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {jobs.length === 0 ? (
        <div className="animate-fadeUp-1 card" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
          <div style={{
            width: 52, height: 52, borderRadius: 12,
            background: 'var(--surface-2)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '1.25rem',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <p style={{ color: 'var(--text-2)', marginBottom: '0.5rem', fontWeight: 500 }}>No uploads yet</p>
          <p style={{ color: 'var(--text-3)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
            Process your first batch of PDFs to see results here.
          </p>
          <button onClick={() => navigate('/upload')} className="btn btn-primary">
            Upload PDFs
          </button>
        </div>
      ) : (
        <div className="animate-fadeUp-1 card" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Status</th>
                  <th>Files</th>
                  <th>Date</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id}>
                    <td>
                      <span style={{ fontFamily: "'DM Mono', monospace", fontSize: '0.78rem', color: 'var(--text-3)' }}>
                        {j.job_id.slice(0, 8)}
                      </span>
                    </td>
                    <td><StatusBadge status={j.status} /></td>
                    <td style={{ fontFamily: "'DM Mono', monospace", fontSize: '0.82rem' }}>{j.total_files}</td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--text-3)' }}>
                      {new Date(j.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => navigate(`/results/${j.job_id}`)}
                          className="btn btn-ghost"
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleDelete(j.job_id)}
                          disabled={deleting === j.job_id}
                          className="btn btn-danger"
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                        >
                          {deleting === j.job_id ? '…' : 'Delete'}
                        </button>
                      </div>
                    </td>
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
