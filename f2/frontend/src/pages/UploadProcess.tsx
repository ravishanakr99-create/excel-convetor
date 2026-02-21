import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { api } from '../api/client'

const MAX_FILES = 500

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function UploadProcess() {
  const [files, setFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const navigate = useNavigate()

  const onDrop = useCallback((accepted: File[]) => {
    const pdfs = accepted.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== accepted.length) toast.error('Only PDF files are accepted')
    setFiles((prev) => {
      const combined = [...prev, ...pdfs]
      if (combined.length > MAX_FILES) {
        toast.error(`Maximum ${MAX_FILES} files allowed`)
        return combined.slice(0, MAX_FILES)
      }
      return combined
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: MAX_FILES,
    disabled: uploading,
  })

  const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx))
  const clearAll = () => { setFiles([]); setUploadProgress(0) }

  const upload = async () => {
    if (files.length === 0) { toast.error('Select at least one PDF'); return }
    setUploading(true); setUploadProgress(0)
    try {
      const formData = new FormData()
      files.forEach((f) => formData.append('files', f))
      const { data } = await api.post<{ job_id: string; status: string; total_files: number }>(
        '/jobs/upload', formData,
        { onUploadProgress: (p) => { if (p.total) setUploadProgress(Math.round((p.loaded / p.total) * 100)) } }
      )
      toast.success(`${data.total_files} files uploaded — processing started`)
      navigate(`/results/${data.job_id}`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Upload failed')
    } finally { setUploading(false); setUploadProgress(0) }
  }

  const totalSize = files.reduce((acc, f) => acc + f.size, 0)

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ marginBottom: '2rem' }}>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace", letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
          New job
        </p>
        <h1 className="font-display" style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
          Upload PDFs
        </h1>
        <p style={{ color: 'var(--text-2)', marginTop: '0.35rem', fontSize: '0.9rem' }}>
          Up to {MAX_FILES} files per batch. AI will extract structured data and export to Excel.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`dropzone animate-fadeUp-1${isDragActive ? ' active' : ''}${uploading ? ' disabled' : ''}`}
        style={{ padding: '3.5rem 2rem', textAlign: 'center' }}
      >
        <input {...getInputProps()} />
        <div style={{
          width: 52, height: 52, borderRadius: 13,
          background: isDragActive ? 'rgba(79,124,255,0.2)' : 'var(--surface)',
          border: `1px solid ${isDragActive ? 'var(--accent)' : 'var(--border)'}`,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: '1rem', transition: 'all 0.2s',
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={isDragActive ? 'var(--accent)' : 'var(--text-3)'} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <p style={{ fontSize: '0.95rem', color: isDragActive ? 'var(--accent)' : 'var(--text-2)', fontWeight: 500, marginBottom: '0.3rem' }}>
          {isDragActive ? 'Release to add files' : 'Drop PDFs here or click to browse'}
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>
          PDF only · max {MAX_FILES} files
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="animate-fadeUp" style={{ marginTop: '1.5rem' }}>

          {/* Summary bar */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className="badge badge-info">{files.length} file{files.length !== 1 ? 's' : ''}</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace" }}>{formatBytes(totalSize)}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={clearAll} disabled={uploading} className="btn btn-ghost" style={{ padding: '0.35rem 0.8rem', fontSize: '0.8rem' }}>
                Clear all
              </button>
              <button onClick={upload} disabled={uploading} className="btn btn-primary">
                {uploading && <span className="spinner" style={{ width: 15, height: 15 }} />}
                {uploading ? `Uploading ${uploadProgress}%` : 'Upload & Process'}
              </button>
            </div>
          </div>

          {/* Progress */}
          {uploading && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          {/* File list */}
          <div className="card" style={{ overflow: 'hidden', maxHeight: 280, overflowY: 'auto' }}>
            {files.map((f, i) => (
              <div
                key={`${f.name}-${i}`}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.6rem 1rem',
                  borderBottom: i < files.length - 1 ? '1px solid var(--border)' : 'none',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', minWidth: 0 }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                  <span style={{ fontSize: '0.83rem', color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace" }}>{formatBytes(f.size)}</span>
                  <button
                    onClick={() => removeFile(i)}
                    disabled={uploading}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: '2px', lineHeight: 1, transition: 'color 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--danger)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-3)')}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
