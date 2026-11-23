import { useEffect, useState, type ReactNode } from 'react'
import { createDemoSession } from '../services/auth'
import './AuthGate.css'

type AuthGateProps = {
  children: ReactNode
}

export default function AuthGate({ children }: AuthGateProps) {
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    createDemoSession()
      .then(() => {
        if (active) setReady(true)
      })
      .catch((sessionError) => {
        if (active) {
          setError(
            sessionError instanceof Error
              ? sessionError.message
              : 'Could not open the demo workspace.',
          )
        }
      })

    return () => {
      active = false
    }
  }, [])

  if (error) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="auth-brand-mark">RM</div>
          <p className="auth-eyebrow">RESTAURANT INTELLIGENCE</p>
          <h1>Demo unavailable</h1>
          <p className="auth-description">{error}</p>
          <button type="button" onClick={() => window.location.reload()}>
            Try again
          </button>
        </section>
      </main>
    )
  }

  if (!ready) {
    return <div className="auth-loading">Loading RestroMind...</div>
  }

  return <>{children}</>
}
