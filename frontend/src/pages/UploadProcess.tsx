import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { api } from '../api/client'

const MAX_FILES = 500

export default function UploadProcess() {
  const [files, setFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const navigate = useNavigate()

  const onDrop = useCallback((accepted: File[]) => {
    const pdfs = accepted.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== accepted.length) {
      toast.error('Only PDF files are accepted')
    }
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

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const clearAll = () => {
    setFiles([])
    setJobId(null)
    setUploadProgress(0)
  }

  const upload = async () => {
    if (files.length === 0) {
      toast.error('Select at least one PDF')
      return
    }
    setUploading(true)
    setUploadProgress(0)
    try {
      const formData = new FormData()
      files.forEach((f) => formData.append('files', f))
      const { data } = await api.post<{ job_id: string; status: string; total_files: number }>(
        '/jobs/upload',
        formData,
        {
          onUploadProgress: (p) => {
            if (p.total) setUploadProgress(Math.round((p.loaded / p.total) * 100))
          },
        }
      )
      setJobId(data.job_id)
      toast.success(`${data.total_files} files uploaded. Processing started.`)
      navigate(`/results/${data.job_id}`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Upload & Process</h1>
      <p className="text-slate-400 mb-8">
        Drag and drop PDFs or click to select. Up to {MAX_FILES} files.
      </p>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="text-slate-400">
          <svg
            className="mx-auto h-12 w-12 text-slate-500 mb-4"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-lg">
            {isDragActive ? 'Drop files here' : 'Drop PDF files here or click to browse'}
          </p>
          <p className="text-sm mt-1">Maximum {MAX_FILES} PDF files</p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-6">
          <div className="flex justify-between items-center mb-3">
            <span className="text-slate-300">{files.length} file(s) selected</span>
            <div className="flex gap-2">
              <button
                onClick={clearAll}
                disabled={uploading}
                className="text-sm text-slate-400 hover:text-slate-200 px-3 py-1 rounded"
              >
                Clear
              </button>
              <button
                onClick={upload}
                disabled={uploading}
                className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Upload & Process'}
              </button>
            </div>
          </div>
          {uploading && (
            <div className="mb-4">
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-sm text-slate-400 mt-1">Upload progress: {uploadProgress}%</p>
            </div>
          )}
          <div className="max-h-60 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/50">
            {files.map((f, i) => (
              <div
                key={`${f.name}-${i}`}
                className="flex items-center justify-between px-4 py-2 border-b border-slate-800 last:border-0"
              >
                <span className="text-sm text-slate-300 truncate">{f.name}</span>
                <button
                  onClick={() => removeFile(i)}
                  disabled={uploading}
                  className="text-slate-500 hover:text-red-400 text-sm disabled:opacity-50"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
