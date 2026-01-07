import Keycloak, { KeycloakInitOptions } from 'keycloak-js'
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react'

interface User {
  email?: string
  name?: string
  preferredUsername?: string
}

interface AuthContextType {
  keycloak: Keycloak | null
  authenticated: boolean
  token: string | null
  user: User | null
  login: () => void
  logout: () => void
  isLoading: boolean
  refreshToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Keycloak configuration from environment variables
const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'myrealm',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'ai-foundry-chat-app',
}

// Token storage keys
const TOKEN_STORAGE_KEY = 'kc_token'
const REFRESH_TOKEN_STORAGE_KEY = 'kc_refresh_token'
const ID_TOKEN_STORAGE_KEY = 'kc_id_token'

// Initialize Keycloak instance outside component to prevent re-creation
let keycloakInstance: Keycloak | null = null
let keycloakInitialized = false

function getKeycloakInstance(): Keycloak {
  if (!keycloakInstance) {
    keycloakInstance = new Keycloak(keycloakConfig)
  }
  return keycloakInstance
}

function isKeycloakInitialized(): boolean {
  return keycloakInitialized
}

function setKeycloakInitialized(value: boolean): void {
  keycloakInitialized = value
}

// Token persistence helpers
function saveTokens(kc: Keycloak): void {
  if (kc.token) localStorage.setItem(TOKEN_STORAGE_KEY, kc.token)
  if (kc.refreshToken) localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, kc.refreshToken)
  if (kc.idToken) localStorage.setItem(ID_TOKEN_STORAGE_KEY, kc.idToken)
}

function getStoredTokens(): { token?: string; refreshToken?: string; idToken?: string } {
  return {
    token: localStorage.getItem(TOKEN_STORAGE_KEY) || undefined,
    refreshToken: localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || undefined,
    idToken: localStorage.getItem(ID_TOKEN_STORAGE_KEY) || undefined,
  }
}

function clearStoredTokens(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
  localStorage.removeItem(ID_TOKEN_STORAGE_KEY)
}

// Export for use in API client
export function getKeycloak(): Keycloak | null {
  return keycloakInstance
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const updateAuthState = useCallback((kc: Keycloak) => {
    setAuthenticated(kc.authenticated ?? false)
    setToken(kc.token ?? null)

    if (kc.authenticated && kc.tokenParsed) {
      setUser({
        email: kc.tokenParsed.email as string | undefined,
        name: kc.tokenParsed.name as string | undefined,
        preferredUsername: kc.tokenParsed.preferred_username as string | undefined,
      })
    } else {
      setUser(null)
    }
  }, [])

  const refreshToken = useCallback(async (): Promise<boolean> => {
    if (!keycloak) return false

    try {
      // Refresh if token expires in less than 60 seconds
      const refreshed = await keycloak.updateToken(60)
      if (refreshed) {
        console.log('Token refreshed successfully')
        saveTokens(keycloak)
        updateAuthState(keycloak)
      }
      return true
    } catch (error) {
      console.error('Failed to refresh token:', error)
      clearStoredTokens()
      // Token refresh failed, need to re-login
      keycloak.login()
      return false
    }
  }, [keycloak, updateAuthState])

  useEffect(() => {
    const initKeycloak = async () => {
      // Prevent double initialization in React Strict Mode
      if (isKeycloakInitialized()) {
        const kc = getKeycloakInstance()
        setKeycloak(kc)
        updateAuthState(kc)
        setIsLoading(false)
        return
      }

      const kc = getKeycloakInstance()
      const storedTokens = getStoredTokens()

      try {
        setKeycloakInitialized(true)

        // If we have stored tokens, try to use them
        const initOptions: KeycloakInitOptions = {
          onLoad: 'login-required',
          checkLoginIframe: false,
          pkceMethod: 'S256',
          scope: 'openid email profile offline_access',
        }

        // Pass stored tokens if available
        if (storedTokens.token && storedTokens.refreshToken) {
          initOptions.token = storedTokens.token
          initOptions.refreshToken = storedTokens.refreshToken
          initOptions.idToken = storedTokens.idToken
        }

        const authenticated = await kc.init(initOptions)

        if (authenticated) {
          console.log('User authenticated')
          // Save tokens after successful auth
          saveTokens(kc)
        } else {
          // Clear any stale tokens
          clearStoredTokens()
        }

        setKeycloak(kc)
        updateAuthState(kc)
      } catch (error) {
        console.error('Keycloak initialization failed:', error)
        clearStoredTokens()
        setKeycloakInitialized(false)
        setAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    initKeycloak()
  }, [updateAuthState])

  // Set up automatic token refresh
  useEffect(() => {
    if (!keycloak?.authenticated) return

    // Refresh token every 30 seconds if it will expire in 60 seconds
    const refreshInterval = setInterval(async () => {
      try {
        const refreshed = await keycloak.updateToken(60)
        if (refreshed) {
          console.log('Token auto-refreshed')
          saveTokens(keycloak)
          updateAuthState(keycloak)
        }
      } catch (error) {
        console.error('Auto token refresh failed:', error)
        // Don't force login here, let the next API call handle it
      }
    }, 30000)

    return () => clearInterval(refreshInterval)
  }, [keycloak?.authenticated, keycloak, updateAuthState])

  // Listen for token expiry events
  useEffect(() => {
    if (!keycloak) return

    const handleTokenExpired = () => {
      console.warn('Token expired, attempting refresh...')
      keycloak.updateToken(0).catch(() => {
        console.error('Token refresh after expiry failed')
        keycloak.login()
      })
    }

    keycloak.onTokenExpired = handleTokenExpired

    return () => {
      keycloak.onTokenExpired = undefined
    }
  }, [keycloak])

  const login = useCallback(() => {
    keycloak?.login()
  }, [keycloak])

  const logout = useCallback(() => {
    clearStoredTokens()
    keycloak?.logout()
  }, [keycloak])

  const value: AuthContextType = {
    keycloak,
    authenticated,
    token,
    user,
    login,
    logout,
    isLoading,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
