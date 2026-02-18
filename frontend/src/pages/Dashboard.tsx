import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Dashboard</h1>
      <p className="text-slate-400 mb-8">Welcome, {user?.email}</p>

      <div className="grid gap-6 md:grid-cols-2">
        <NavLink
          to="/upload"
          className="block p-6 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-primary-500/50 hover:bg-slate-800/50 transition-all group"
        >
          <div className="text-primary-400 group-hover:text-primary-300 mb-3">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-100 mb-1">Upload & Process</h2>
          <p className="text-sm text-slate-400">
            Upload up to 500 PDFs, extract data with AI, and export to Excel
          </p>
        </NavLink>

        <NavLink
          to="/history"
          className="block p-6 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-primary-500/50 hover:bg-slate-800/50 transition-all group"
        >
          <div className="text-primary-400 group-hover:text-primary-300 mb-3">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-100 mb-1">History</h2>
          <p className="text-sm text-slate-400">
            View previous uploads and download results
          </p>
        </NavLink>
      </div>

      <div className="mt-12 p-6 rounded-xl bg-slate-900/50 border border-slate-800">
        <h3 className="font-medium text-slate-200 mb-2">Features</h3>
        <ul className="text-sm text-slate-400 space-y-1">
          <li>• Upload multiple PDFs (up to 500 files)</li>
          <li>• AI-powered section detection and field extraction</li>
          <li>• OCR support for scanned documents</li>
          <li>• Batch processing with progress tracking</li>
          <li>• Export all results to a single Excel file</li>
        </ul>
      </div>
    </div>
  )
}
