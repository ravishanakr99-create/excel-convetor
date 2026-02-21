import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import SnakeAnimation from '../components/SnakeAnimation'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) { toast.error('Email and password required'); return }
    if (isRegister && password.length < 6) { toast.error('Password must be at least 6 characters'); return }
    setLoading(true)
    try {
      if (isRegister) { await register(email, password); toast.success('Account created') }
      else             { await login(email, password);    toast.success('Signed in') }
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Authentication failed')
    } finally { setLoading(false) }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg)',
      padding: '1.5rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Snake Animation - background */}
      <SnakeAnimation isActive={true} />

      {/* Background blobs */}
      <div style={{
        position: 'absolute', width: 480, height: 480,
        background: 'radial-gradient(circle, rgba(79,124,255,0.07) 0%, transparent 70%)',
        top: '10%', left: '15%', pointerEvents: 'none', zIndex: 1,
      }} />
      <div style={{
        position: 'absolute', width: 300, height: 300,
        background: 'radial-gradient(circle, rgba(0,212,180,0.05) 0%, transparent 70%)',
        bottom: '15%', right: '20%', pointerEvents: 'none', zIndex: 1,
      }} />

      <div style={{ width: '100%', maxWidth: 420, position: 'relative', zIndex: 2 }}>
        {/* Logo mark */}
        <div className="animate-fadeUp" style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: 48, height: 48,
            background: 'var(--accent)',
            borderRadius: 12,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '1rem',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <h1 className="font-display" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem', letterSpacing: '-0.02em' }}>
            PDF<span style={{ color: 'var(--accent)' }}>Extract</span>
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-3)' }}>AI-powered document data extraction</p>
        </div>

        {/* Card */}
        <div className="animate-fadeUp-1 card" style={{ padding: '2rem' }}>
          {/* Tab toggle */}
          <div style={{
            display: 'flex',
            background: 'var(--bg-2)',
            borderRadius: 9,
            padding: '3px',
            marginBottom: '1.75rem',
          }}>
            {['Sign in', 'Register'].map((label, i) => {
              const active = (i === 0) ? !isRegister : isRegister
              return (
                <button
                  key={label}
                  onClick={() => setIsRegister(i === 1)}
                  style={{
                    flex: 1,
                    padding: '0.55rem',
                    borderRadius: 7,
                    border: 'none',
                    background: active ? 'var(--surface-2)' : 'transparent',
                    color: active ? 'var(--text)' : 'var(--text-3)',
                    fontWeight: active ? 500 : 400,
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >{label}</button>
              )
            })}
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-2)', marginBottom: '0.45rem', fontWeight: 500 }}>
                Email address
              </label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-2)', marginBottom: '0.45rem', fontWeight: 500 }}>
                Password
              </label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '0.75rem', fontSize: '0.9rem' }}
            >
              {loading && <span className="spinner" style={{ width: 16, height: 16 }} />}
              {loading ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="animate-fadeUp-2" style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.8rem', color: 'var(--text-3)' }}>
          {isRegister ? 'Already have an account? ' : "Don't have an account? "}
          <button
            onClick={() => setIsRegister(!isRegister)}
            style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500 }}
          >
            {isRegister ? 'Sign in' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  )
}
