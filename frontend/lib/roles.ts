/**
 * Helpers para chequear roles del usuario autenticado contra los roles
 * permitidos por una vista o accion.
 *
 * Mantener en sync con las constantes del backend en
 * `backend/app/api/routes/kpis.py` (SUBS_ROLES, ORDERS_ROLES, etc.).
 */

/**
 * Roles permitidos por dominio. `admin` y `analista` tienen acceso global.
 */
export const ROLE_MATRIX = {
  overview: ['admin', 'analista'],
  orders: ['admin', 'analista', 'orders'],
  subscriptions: ['admin', 'analista', 'subscriptions'],
  salud: ['admin', 'analista', 'salud'],
  incidents: ['admin', 'analista', 'incidents'],
  notifications: ['admin', 'analista', 'notifications'],
  iot: ['admin', 'analista', 'iot'],
  payments: ['admin', 'analista', 'payments'],
  logistics: ['admin'],
  inventory: ['admin', 'analista', 'inventory'],
  crm: ['admin', 'analista', 'crm'],
  security: ['admin'],
} as const

export type Domain = keyof typeof ROLE_MATRIX

/** True si el usuario tiene al menos uno de los roles permitidos. */
export function hasAnyRole(userRoles: string[], allowed: readonly string[]): boolean {
  if (!userRoles || userRoles.length === 0) return false
  return allowed.some((r) => userRoles.includes(r))
}

/** True si el usuario puede acceder al dominio pedido. */
export function canAccess(userRoles: string[], domain: Domain): boolean {
  return hasAnyRole(userRoles, ROLE_MATRIX[domain])
}

/**
 * Devuelve la primera ruta a la que el usuario puede acceder, en orden de
 * preferencia (overview primero, despues los 4 dominios). Sirve para hacer
 * un landing redirect cuando un usuario sin rol overview entra a "/".
 *
 * Retorna null si el usuario no tiene rol para ningun dashboard implementado.
 */
const LANDING_PRIORITY: Array<{ domain: Domain; path: string }> = [
  { domain: 'overview', path: '/' },
  { domain: 'orders', path: '/orders' },
  { domain: 'salud', path: '/health' },
  { domain: 'incidents', path: '/incidents' },
  // subscriptions: pagina aun no implementada, no la usamos como destino.
]

export function pickLandingPath(userRoles: string[]): string | null {
  for (const { domain, path } of LANDING_PRIORITY) {
    if (canAccess(userRoles, domain)) return path
  }
  return null
}
