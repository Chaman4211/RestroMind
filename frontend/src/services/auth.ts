import type { StaffUser } from './api'

const API_BASE_URL = '/api/v1'
const TOKEN_KEY = 'restromind_access_token'

export type AuthResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: StaffUser
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function saveAccessToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

export async function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  const body = await response.json()

  if (!response.ok) {
    throw new Error(body.detail || 'Login failed')
  }

  const result = body as AuthResponse
  saveAccessToken(result.access_token)

  return result
}

export async function getCurrentUser(): Promise<StaffUser> {
  const token = getAccessToken()

  if (!token) {
    throw new Error('No active login session')
  }

  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    clearAccessToken()
    throw new Error('Your session has expired. Please log in again.')
  }

  return response.json() as Promise<StaffUser>
}

export function logout(): void {
  clearAccessToken()
}
