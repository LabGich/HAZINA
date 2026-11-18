
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import {
  getCurrentUser,
  login as loginUser,
  logout as logoutUser,
  refreshTokens,
} from '../services/auth'

import {
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from '../services/tokenStorage'

import type {
  AuthUser,
  LoginRequest,
} from '../types/auth'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

// Shared across React StrictMode's development effect re-runs.
// This prevents two simultaneous refresh requests from rotating
// the same refresh token.
let sessionRestorePromise: Promise<AuthUser | null> | null = null

async function restoreSession(): Promise<AuthUser | null> {
  const refreshToken = getRefreshToken()

  if (!refreshToken) {
    return null
  }

  const tokens = await refreshTokens({
    refresh_token: refreshToken,
  })

  setAccessToken(tokens.access_token)
  setRefreshToken(tokens.refresh_token)

  return getCurrentUser()
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!sessionRestorePromise) {
      sessionRestorePromise = restoreSession().catch(() => {
        clearTokens()
        return null
      })
    }

    let isMounted = true

    sessionRestorePromise.then((restoredUser) => {
      if (isMounted) {
        setUser(restoredUser)
        setIsLoading(false)
      }
    })

    return () => {
      isMounted = false
    }
  }, [])

  const login = useCallback(
    async (credentials: LoginRequest): Promise<void> => {
      const response = await loginUser(credentials)

      setAccessToken(response.access_token)
      setRefreshToken(response.refresh_token)
      setUser(response.user)
    },
    [],
  )

  const logout = useCallback(async (): Promise<void> => {
    const refreshToken = getRefreshToken()

    try {
      if (refreshToken) {
        await logoutUser({
          refresh_token: refreshToken,
        })
      }
    } finally {
      clearTokens()
      setUser(null)
    }
  }, [])

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    login,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}
