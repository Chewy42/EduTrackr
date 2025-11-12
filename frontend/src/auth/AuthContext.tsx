import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type AuthMode = 'sign_in' | 'sign_up'

export type AuthState = {
  email: string
  password: string
  confirmPassword: string
}

export type SessionState = 'checking' | 'unauthenticated' | 'authenticated'

export type UserPreferences = {
  theme?: 'light' | 'dark'
  landingView?: 'dashboard' | 'schedule' | 'explore'
}

export type AuthContextValue = {
  sessionState: SessionState
  mode: AuthMode
  auth: AuthState
  loading: boolean
  error: string | null
  preferences: UserPreferences
  jwt: string | null
  setMode: (mode: AuthMode) => void
  setField: (field: keyof AuthState, value: string) => void
  handleSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
  refreshPreferences: () => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const LOCAL_SESSION_KEY = 'edutrackr.auth.jwt'
const LOCAL_PREF_KEY = 'edutrackr.preferences'

type Props = {
  children: React.ReactNode
}

export function AuthProvider({ children }: Props) {
  const [sessionState, setSessionState] = useState<SessionState>('checking')
  const [mode, setMode] = useState<AuthMode>('sign_in')
  const [auth, setAuth] = useState<AuthState>({ email: '', password: '', confirmPassword: '' })
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [preferences, setPreferences] = useState<UserPreferences>({})
  const [jwt, setJwt] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = typeof window !== 'undefined' ? window.localStorage.getItem(LOCAL_SESSION_KEY) : null
    const storedPrefs = typeof window !== 'undefined' ? window.localStorage.getItem(LOCAL_PREF_KEY) : null

    if (storedToken) {
      setJwt(storedToken)
      setSessionState('authenticated')
    } else {
      setSessionState('unauthenticated')
    }

    if (storedPrefs) {
      try {
        const parsed = JSON.parse(storedPrefs) as UserPreferences
        setPreferences(parsed)
      } catch {
      }
    }
  }, [])

  const setField = (field: keyof AuthState, value: string) => {
    setAuth((prev) => ({ ...prev, [field]: value }))
  }

  const persistJwt = (token: string) => {
    setJwt(token)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCAL_SESSION_KEY, token)
    }
  }

  const persistPreferences = (next: UserPreferences) => {
    setPreferences(next)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCAL_PREF_KEY, JSON.stringify(next))
    }
  }

  const refreshPreferences = async () => {
    if (!jwt) return

    const serverPreferences: UserPreferences = {
      theme: 'dark',
      landingView: 'dashboard',
    }

    persistPreferences(serverPreferences)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (!auth.email.endsWith('@chapman.edu')) {
        throw new Error('Use your @chapman.edu email to continue.')
      }

      if (mode === 'sign_up' && auth.password !== auth.confirmPassword) {
        throw new Error('Passwords must match.')
      }

      await new Promise((resolve) => setTimeout(resolve, 400))

      const fakeJwt = 'stub.jwt.token'
      persistJwt(fakeJwt)
      setSessionState('authenticated')

      await refreshPreferences()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to process request.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const signOut = () => {
    setSessionState('unauthenticated')
    setJwt(null)
    setAuth({ email: '', password: '', confirmPassword: '' })
    setPreferences({})
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(LOCAL_SESSION_KEY)
      window.localStorage.removeItem(LOCAL_PREF_KEY)
    }
  }

  const value: AuthContextValue = useMemo(
    () => ({
      sessionState,
      mode,
      auth,
      loading,
      error,
      preferences,
      jwt,
      setMode,
      setField,
      handleSubmit,
      refreshPreferences,
      signOut,
    }),
    [sessionState, mode, auth, loading, error, preferences, jwt]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
