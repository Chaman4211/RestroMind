import { createContext, useContext, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getCurrentUser, login, logout as clearSession } from '../services/auth'
import type { StaffUser } from '../services/api'
import './AuthGate.css'

type AuthContextValue = {
  user: StaffUser
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthGate')
  }
  return context
}

type AuthGateProps = {
  children: ReactNode
}

export default function AuthGate({ children }: AuthGateProps) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<StaffUser | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let active = true

    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser)
      })
      .catch(() => {
        if (active) setUser(null)
      })
      .finally(() => {
        if (active) setCheckingSession(false)
      })

    return () => {
      active = false
    }
  }, [])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const result = await login(email.trim(), password)
      setUser(result.user)
      setPassword('')
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Login failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function handleLogout() {
    clearSession()
    queryClient.clear()
    setUser(null)
    setPassword('')
  }

  if (checkingSession) {
    return <div className="auth-loading">Loading RestroMind...</div>
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="auth-brand-mark">RM</div>
          <p className="auth-eyebrow">RESTAURANT INTELLIGENCE</p>
          <h1>Welcome back</h1>
          <p className="auth-description">Sign in to access your RestroMind workspace.</p>

          <form className="auth-form" onSubmit={handleLogin}>
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              placeholder="you@restaurant.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />

            {error && <p className="auth-error" role="alert">{error}</p>}

            <button type="submit" disabled={submitting}>
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="auth-footer">Secure access for your restaurant team</p>
        </section>
      </main>
    )
  }

  return (
    <AuthContext.Provider value={{ user, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  )
}
