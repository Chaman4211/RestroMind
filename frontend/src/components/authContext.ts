import { createContext, useContext } from 'react'
import type { StaffUser } from '../services/api'

export type AuthContextValue = {
  user: StaffUser
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthGate')
  }
  return context
}
