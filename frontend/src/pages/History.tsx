import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, JobHistoryItem } from '../api/client'

export default function History() {
  const [jobs, setJobs] = useState<JobHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get<JobHistoryItem[]>('/jobs/history')
      .then(({ data }) => setJobs(data))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-pulse text-slate-400">Loading history...</div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Upload History</h1>
      <p className="text-slate-400 mb-8">Previous uploads and processing jobs</p>

      {jobs.length === 0 ? (
        <div className="p-12 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400">
          No uploads yet. <button onClick={() => navigate('/upload')} className="text-primary-400 hover:text-primary-300">Upload PDFs</button> to get started.
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/80">
              <tr>
                <th className="px-4 py-3 text-left text-slate-300 font-medium">Job ID</th>
                <th className="px-4 py-3 text-left text-slate-300 font-medium">Status</th>
                <th className="px-4 py-3 text-left text-slate-300 font-medium">Files</th>
                <th className="px-4 py-3 text-left text-slate-300 font-medium">Date</th>
                <th className="px-4 py-3 text-right text-slate-300 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.job_id} className="border-t border-slate-800 hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{j.job_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        j.status === 'completed'
                          ? 'bg-green-500/20 text-green-400'
                          : j.status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {j.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{j.total_files}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {new Date(j.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => navigate(`/results/${j.job_id}`)}
                      className="text-primary-400 hover:text-primary-300 text-sm"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
