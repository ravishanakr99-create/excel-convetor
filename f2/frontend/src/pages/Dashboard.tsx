import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const features = [
  { icon: '⬆', label: 'Batch upload', desc: 'Up to 500 PDFs at once' },
  { icon: '🧠', label: 'AI extraction', desc: 'Section detection & field parsing' },
  { icon: '🔍', label: 'OCR support',  desc: 'Works on scanned documents' },
  { icon: '📊', label: 'Excel export', desc: 'All results in one spreadsheet' },
]

export default function Dashboard() {
  const { user } = useAuth()

  // Derive a short greeting name from email
  const name = user?.email?.split('@')[0] ?? 'there'

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>

      {/* Hero greeting */}
      <div className="animate-fadeUp" style={{ marginBottom: '2.5rem' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace", letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
          Good to see you
        </p>
        <h1 className="font-display" style={{ fontSize: 'clamp(1.8rem, 4vw, 2.4rem)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.025em', lineHeight: 1.15 }}>
          Hello, <span style={{ color: 'var(--accent)' }}>{name}</span>
        </h1>
        <p style={{ color: 'var(--text-2)', marginTop: '0.4rem', fontSize: '0.925rem' }}>
          What would you like to do today?
        </p>
      </div>

      {/* Action cards */}
      <div className="animate-fadeUp-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginBottom: '2.5rem' }}>
        
        <NavLink to="/upload" style={{ textDecoration: 'none' }}>
          <div className="card card-glow" style={{ padding: '1.75rem', cursor: 'pointer', transition: 'all 0.2s' }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10,
              background: 'rgba(79,124,255,0.12)',
              border: '1px solid rgba(79,124,255,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '1.1rem',
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <h2 className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text)', marginBottom: '0.4rem', letterSpacing: '-0.01em' }}>
              Upload & Process
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-3)', lineHeight: 1.5 }}>
              Drop PDFs, extract structured data with AI, and export to Excel.
            </p>
            <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--accent)', fontWeight: 500 }}>
              Get started
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
              </svg>
            </div>
          </div>
        </NavLink>

        <NavLink to="/history" style={{ textDecoration: 'none' }}>
          <div className="card card-glow" style={{ padding: '1.75rem', cursor: 'pointer', transition: 'all 0.2s' }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10,
              background: 'rgba(0,212,180,0.08)',
              border: '1px solid rgba(0,212,180,0.18)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '1.1rem',
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <h2 className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text)', marginBottom: '0.4rem', letterSpacing: '-0.01em' }}>
              History
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-3)', lineHeight: 1.5 }}>
              Browse past uploads, check processing status, and download results.
            </p>
            <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--accent-2)', fontWeight: 500 }}>
              View history
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
              </svg>
            </div>
          </div>
        </NavLink>
      </div>

      {/* Features */}
      <div className="animate-fadeUp-2">
        <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: "'DM Mono', monospace", letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: '1rem' }}>
          What's included
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
          {features.map((f) => (
            <div key={f.label} style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              padding: '0.9rem 1rem',
              display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
            }}>
              <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>{f.icon}</span>
              <div>
                <p style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text)', marginBottom: '0.15rem' }}>{f.label}</p>
                <p style={{ fontSize: '0.775rem', color: 'var(--text-3)' }}>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
