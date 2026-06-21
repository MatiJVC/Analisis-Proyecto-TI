'use client'

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type Keycloak from 'keycloak-js'
import { getKeycloak } from '@/lib/keycloak'

interface AuthContextValue {
  keycloak: Keycloak | null
  authenticated: boolean
  username: string | null
  email: string | null
  roles: string[]
  logout: () => void
}

const AuthContext = createContext<AuthContextValue>({
  keycloak: null,
  authenticated: false,
  username: null,
  email: null,
  roles: [],
  logout: () => {},
})

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [ready, setReady] = useState(false)
  // En modo dev de React, useEffect se ejecuta dos veces; sin este flag
  // keycloak.init() se llama dos veces y revienta con "already initialized".
  const initStarted = useRef(false)

  useEffect(() => {
    if (initStarted.current) return
    initStarted.current = true

    let cancelled = false

    getKeycloak()
      .then((kc) =>
        kc
          .init({
            onLoad: 'login-required',
            pkceMethod: 'S256',
            checkLoginIframe: false,
          })
          .then((auth) => {
            if (cancelled) return
            setKeycloak(kc)
            setAuthenticated(auth)
            setReady(true)

            // Refresca el token automáticamente cada 60s.
            const interval = window.setInterval(() => {
              kc.updateToken(70).catch(() => {
                console.warn('No se pudo refrescar el token, cerrando sesión')
                kc.logout()
              })
            }, 60_000)

            kc.onTokenExpired = () => {
              kc.updateToken(30).catch(() => kc.logout())
            }

            return () => window.clearInterval(interval)
          }),
      )
      .catch((err) => {
        console.error('Error inicializando Keycloak:', err)
        setReady(true)
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm">Conectando con el sistema de identidad…</p>
        </div>
      </div>
    )
  }

  if (!authenticated || !keycloak) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Redirigiendo al login…</p>
      </div>
    )
  }

  const tokenParsed = keycloak.tokenParsed as
    | {
        preferred_username?: string
        email?: string
        realm_access?: { roles?: string[] }
        resource_access?: Record<string, { roles?: string[] }>
      }
    | undefined

 
  const realmRoles = tokenParsed?.realm_access?.roles ?? []
  const clientRoles = Object.values(tokenParsed?.resource_access ?? {}).flatMap(
    (client) => client?.roles ?? [],
  )
  const allRoles = Array.from(new Set([...realmRoles, ...clientRoles]))

  const value: AuthContextValue = {
    keycloak,
    authenticated,
    username: tokenParsed?.preferred_username ?? null,
    email: tokenParsed?.email ?? null,
    roles: allRoles,
    logout: () =>
      keycloak.logout({ redirectUri: window.location.origin }),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
