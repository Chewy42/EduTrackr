import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type AuthMode = 'sign_in' | 'sign_up'

export type AuthState = {
  email: string
  password: string
  confirmPassword: string
}

export type SessionState = 'checking' | 'unauthenticated' | 'authenticated' | 'pending_confirmation' | 'backend_unavailable'

export type UserPreferences = {
  theme?: 'light' | 'dark'
  landingView?: 'dashboard' | 'schedule' | 'explore'
  hasProgramEvaluation?: boolean
  onboardingComplete?: boolean
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
  retryBackendConnection: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const LOCAL_SESSION_KEY = 'edutrackr.auth.jwt'
const LOCAL_PREF_KEY = 'edutrackr.preferences'

type Props = {
  children: React.ReactNode
}

function isValidJwtFormat(token: string): boolean {
  if (!token || typeof token !== 'string') {
    return false
  }
  const parts = token.split('.')
  if (parts.length !== 3) {
    return false
  }
  try {
    for (const part of parts) {
      if (!part || !/^[A-Za-z0-9_-]+$/.test(part)) {
        return false
      }
    }
    return true
  } catch {
    return false
  }
}

function safeGetLocalStorage(key: string): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    return window.localStorage.getItem(key)
  } catch (err) {
    console.error(`Failed to read from localStorage (${key}):`, err)
    return null
  }
}

function safeParseJson<T>(json: string | null, fallback: T): T {
  if (!json) {
    return fallback
  }
  try {
    return JSON.parse(json) as T
  } catch (err) {
    console.error('Failed to parse JSON from localStorage:', err)
    return fallback
  }
}

async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)
    
    const res = await fetch('/api/health', {
      method: 'GET',
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    return res.ok
  } catch (err) {
    console.error('Backend health check failed:', err)
    return false
  }
}

function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError && (
    (err.message.toLowerCase().includes('network') ||
     err.message.toLowerCase().includes('fetch') ||
     err.message.toLowerCase().includes('failed'))
  )
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
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

  const persistJwt = useCallback((token: string | null) => {
    setJwt(token)
    if (typeof window === 'undefined') {
      return
    }
    try {
      if (token) {
        window.localStorage.setItem(LOCAL_SESSION_KEY, token)
      } else {
        window.localStorage.removeItem(LOCAL_SESSION_KEY)
      }
    } catch (err) {
      console.error('Failed to persist JWT to localStorage:', err)
    }
  }, [])

  const persistPreferences = useCallback((next: UserPreferences) => {
    setPreferences(next)
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(LOCAL_PREF_KEY, JSON.stringify(next))
      } catch (err) {
        console.error('Failed to persist preferences to localStorage:', err)
      }
    }
  }, [])

  const signOut = useCallback(() => {
    setSessionState('unauthenticated')
    persistJwt(null)
    setAuth({ email: '', password: '', confirmPassword: '' })
    setPreferences({})
    setPendingEmail(null)
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.removeItem(LOCAL_PREF_KEY)
      } catch (err) {
        console.error('Failed to remove preferences from localStorage:', err)
      }
    }
  }, [persistJwt])

  const retryBackendConnection = useCallback(async () => {
    setSessionState('checking')
    const isHealthy = await checkBackendHealth()
    if (isHealthy) {
      const storedToken = safeGetLocalStorage(LOCAL_SESSION_KEY)
      if (storedToken && isValidJwtFormat(storedToken)) {
        setJwt(storedToken)
        setSessionState('authenticated')
      } else {
        setSessionState('unauthenticated')
      }
    } else {
      setSessionState('backend_unavailable')
    }
  }, [])

  useEffect(() => {
    const initializeAuth = async () => {
      const storedPrefs = safeGetLocalStorage(LOCAL_PREF_KEY)
      const parsedPrefs = safeParseJson<UserPreferences>(storedPrefs, {})
      setPreferences(parsedPrefs)

      if (typeof window !== 'undefined' && window.location.hash) {
        const hashParams = new URLSearchParams(window.location.hash.substring(1))
        const accessToken = hashParams.get('access_token')
        if (accessToken && isValidJwtFormat(accessToken)) {
          setJwt(accessToken)
          setSessionState('authenticated')
          persistJwt(accessToken)
          window.history.replaceState(null, '', window.location.pathname + window.location.search)
          return
        }
      }

      const storedToken = safeGetLocalStorage(LOCAL_SESSION_KEY)
      
      if (storedToken) {
        if (!isValidJwtFormat(storedToken)) {
          console.warn('Stored JWT appears corrupted, clearing and requiring login')
          persistJwt(null)
          setSessionState('unauthenticated')
          return
        }

        const isHealthy = await checkBackendHealth()
        if (!isHealthy) {
          console.warn('Backend is unavailable')
          setJwt(storedToken)
          setSessionState('backend_unavailable')
          return
        }

        setJwt(storedToken)
        setSessionState('authenticated')
      } else {
        const isHealthy = await checkBackendHealth()
        if (!isHealthy) {
          setSessionState('backend_unavailable')
          return
        }
        setSessionState('unauthenticated')
      }
    }

    initializeAuth()
  }, [persistJwt])

  const setField = (field: keyof AuthState, value: string) => {
    setAuth((prev) => ({ ...prev, [field]: value }))
  }

  const mergePreferences = useCallback((patch: Partial<UserPreferences>) => {
    setPreferences((prev) => {
      const next = { ...prev, ...patch }
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(LOCAL_PREF_KEY, JSON.stringify(next))
        } catch (err) {
          console.error('Failed to merge preferences to localStorage:', err)
        }
      }
      return next
    })
  }, [])

  const refreshPreferences = useCallback(async () => {
    if (!jwt) return

    const attemptFetch = async (): Promise<Response> => {
      return await fetch('/api/auth/preferences', {
        headers: {
          'Authorization': `Bearer ${jwt}`,
          'Accept': 'application/json'
        }
      })
    }

    try {
      let res: Response
      try {
        res = await attemptFetch()
      } catch (err) {
        if (isNetworkError(err)) {
          console.error('Network error while refreshing preferences, using cached:', err)
          return
        }
        throw err
      }

      if (res.ok) {
        const prefs = await res.json() as UserPreferences
        persistPreferences(prefs)
        return
      }

      if (res.status === 401 || res.status === 403) {
        console.warn(`Auth error (${res.status}) refreshing preferences, signing out`)
        signOut()
        return
      }

      if (res.status >= 500 && res.status < 600) {
        console.warn(`Server error (${res.status}) refreshing preferences, retrying in 2s...`)
        await delay(2000)
        
        try {
          const retryRes = await attemptFetch()
          if (retryRes.ok) {
            const prefs = await retryRes.json() as UserPreferences
            persistPreferences(prefs)
            return
          }
          console.error(`Retry also failed with status ${retryRes.status}, using cached preferences`)
        } catch (retryErr) {
          console.error('Retry failed with error, using cached preferences:', retryErr)
        }
        return
      }

      console.error(`Unexpected error (${res.status}) refreshing preferences, using cached`)
    } catch (err) {
      console.error('Failed to refresh preferences, using cached:', err)
    }
  }, [jwt, persistPreferences, signOut])

  useEffect(() => {
    if (jwt && sessionState === 'authenticated') {
      refreshPreferences()
    }
  }, [jwt, sessionState, refreshPreferences])

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
      
      let res: Response
      try {
        res = await fetch(endpoint, {
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
      } catch (err) {
        if (isNetworkError(err)) {
          throw new Error('Unable to connect to server. Please check your internet connection and try again.')
        }
        throw err
      }

      if (res.status === 502 || res.status === 503) {
        throw new Error('Service is temporarily unavailable. Please try again in a few moments.')
      }

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

    try {
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
    } catch (err) {
      if (isNetworkError(err)) {
        throw new Error('Unable to connect to server. Please check your internet connection and try again.')
      }
      throw err
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
      retryBackendConnection,
    }),
    [sessionState, mode, auth, loading, error, preferences, jwt, pendingEmail, mergePreferences, signOut, refreshPreferences, retryBackendConnection]
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
