import { useCallback, useEffect, useState } from "react"

const TOKEN_KEY = "house_helper_token"
const USER_KEY = "house_helper_user"

interface User {
  id: number
  email: string
  name: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  authMode: "local" | "multi"
}

/**
 * Auth hook — manages login, signup, logout, token storage.
 * In local mode, always authenticated (no login needed).
 */
export function useAuth() {
  const [state, setState] = useState<AuthState>({
    token: localStorage.getItem(TOKEN_KEY),
    user: (() => { try { return JSON.parse(localStorage.getItem(USER_KEY) || "null") } catch { return null } })(),
    isAuthenticated: false,
    isLoading: true,
    authMode: "local",
  })

  useEffect(() => {
    // Check auth mode from backend
    fetch("/api/auth/config")
      .then((r) => r.ok ? r.json() : { auth_mode: "local" })
      .then((config) => {
        const mode = config.auth_mode || "local"
        if (mode === "local") {
          setState((prev) => ({ ...prev, authMode: "local", isAuthenticated: true, isLoading: false }))
        } else {
          const token = localStorage.getItem(TOKEN_KEY)
          const isAuthenticated = !!token
          setState((prev) => ({ ...prev, authMode: "multi", isAuthenticated, isLoading: false }))
        }
      })
      .catch(() => {
        setState((prev) => ({ ...prev, authMode: "local", isAuthenticated: true, isLoading: false }))
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || "Login failed")
    }
    const data = await response.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setState((prev) => ({ ...prev, token: data.token, user: data.user, isAuthenticated: true }))
    return data
  }, [])

  const signup = useCallback(async (email: string, password: string, name: string) => {
    const response = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || "Signup failed")
    }
    const data = await response.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setState((prev) => ({ ...prev, token: data.token, user: data.user, isAuthenticated: true }))
    return data
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setState((prev) => ({ ...prev, token: null, user: null, isAuthenticated: false }))
  }, [])

  return { ...state, login, signup, logout }
}

/** Get the stored JWT token for API calls. */
export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
