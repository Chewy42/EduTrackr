import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type AuthMode = 'sign_in' | 'sign_up'

export type AuthState = {
  email: string
  password: string
  confirmPassword: string
}

export type SessionState = 'checking' | 'unauthenticated' | 'authenticated' | 'pending_confirmation'

export type UserPreferences = {
  theme?: 'light' | 'dark'
  landingView?: 'dashboard' | 'schedule' | 'explore'
  hasProgramEvaluation?: boolean
}

export type AuthContextValue = {
  sessionState: SessionState
  mode: AuthMode
  auth: AuthState
  loading: boolean
  error: string | null
  preferences: UserPreferences
  jwt: string | null
  pendingEmail: string | null
  setMode: (mode: AuthMode) => void
  setField: (field: keyof AuthState, value: string) => void
  handleSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>
  refreshPreferences: () => Promise<void>
  resendConfirmation: () => Promise<void>
  signOut: () => void
  mergePreferences: (patch: Partial<UserPreferences>) => void
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
  const [pendingEmail, setPendingEmail] = useState<string | null>(null)

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

  const persistJwt = (token: string | null) => {
    setJwt(token)
    if (typeof window === 'undefined') {
      return
    }
    if (token) {
      window.localStorage.setItem(LOCAL_SESSION_KEY, token)
    } else {
      window.localStorage.removeItem(LOCAL_SESSION_KEY)
    }
  }

  const persistPreferences = (next: UserPreferences) => {
    setPreferences(next)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCAL_PREF_KEY, JSON.stringify(next))
    }
  }

  const mergePreferences = useCallback((patch: Partial<UserPreferences>) => {
    setPreferences((prev) => {
      const next = { ...prev, ...patch }
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(LOCAL_PREF_KEY, JSON.stringify(next))
      }
      return next
    })
  }, [])

  const refreshPreferences = async () => {
    if (!jwt) return

    try {
      const res = await fetch('/api/auth/preferences', {
        headers: {
          'Authorization': `Bearer ${jwt}`,
          'Accept': 'application/json'
        }
      })

      if (res.ok) {
        const prefs = await res.json() as UserPreferences
        persistPreferences(prefs)
      }
    } catch {
    }
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

      const endpoint = mode === 'sign_in' ? '/api/auth/sign-in' : '/api/auth/sign-up'
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          email: auth.email,
          password: auth.password
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || 'Unable to process request.')
      }

      if (data.status === 'pending_confirmation') {
        setSessionState('pending_confirmation')
        setPendingEmail(data.user?.email ?? auth.email)
        persistJwt(null)
        return
      }

      persistJwt(data.token)
      setSessionState('authenticated')

      if (data.preferences) {
        persistPreferences(data.preferences)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to process request.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const resendConfirmation = async () => {
    if (!pendingEmail) {
      throw new Error('No pending email to confirm.')
    }

    const res = await fetch('/api/auth/resend-confirmation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ email: pendingEmail })
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || 'Unable to resend confirmation email.')
    }
  }

  const signOut = () => {
    setSessionState('unauthenticated')
    persistJwt(null)
    setAuth({ email: '', password: '', confirmPassword: '' })
    setPreferences({})
    setPendingEmail(null)
    if (typeof window !== 'undefined') {
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
      pendingEmail,
      setMode,
      setField,
      handleSubmit,
      refreshPreferences,
      resendConfirmation,
      signOut,
      mergePreferences,
    }),
    [sessionState, mode, auth, loading, error, preferences, jwt, pendingEmail, mergePreferences]
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
