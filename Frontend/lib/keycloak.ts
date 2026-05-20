import type Keycloak from 'keycloak-js'

/**
 * Singleton de Keycloak compartido por toda la app.
 * - Solo se instancia en el navegador (keycloak-js no funciona en SSR).
 * - `services/api.ts` lo importa para leer el token en cada fetch sin
 *   tener que pasarlo por props/context a cada llamada SWR.
 */
let keycloakInstance: Keycloak | null = null

export async function getKeycloak(): Promise<Keycloak> {
  if (typeof window === 'undefined') {
    throw new Error('Keycloak solo puede usarse en el navegador')
  }

  if (keycloakInstance) return keycloakInstance

  const KeycloakCtor = (await import('keycloak-js')).default

  keycloakInstance = new KeycloakCtor({
    url: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? 'http://localhost:8080',
    realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? 'sistema-centralizado',
    clientId:
      process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? 'proyecto-analisis-ti',
  })

  return keycloakInstance
}

/**
 * Devuelve el access_token vigente o null si todavía no hay sesión.
 * Si el token está por vencer (<30s) intenta refrescarlo en silencio.
 */
export async function getAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  if (!keycloakInstance) return null

  try {
    await keycloakInstance.updateToken(30)
  } catch {
    // Si falla el refresh dejamos que la app reaccione al 401.
  }

  return keycloakInstance.token ?? null
}
