/**
 * Cliente del backend FastAPI para el dominio salud (KPIs desde el warehouse).
 * Base URL: NEXT_PUBLIC_API_BASE_URL (ej. http://127.0.0.1:8000)
 */
import { getAccessToken } from '@/lib/keycloak'

const DEFAULT_API_BASE = 'http://127.0.0.1:8000'

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (!raw) return DEFAULT_API_BASE
  return raw.replace(/\/$/, '')
}

export type SaludDashboard = {
  active_patients: number
  today_visits: number
  healthcare_staff: number
  avg_visit_time_minutes: number | null
  coverage_zones: number
  satisfaction_score: number | null
}

export type SaludVisitTrendPoint = {
  date: string
  visits: number
  completed: number
}

export type SaludVisitTrends = {
  days: number
  points: SaludVisitTrendPoint[]
}

export type SaludTodayVisit = {
  visita_id: string
  time_display: string
  patient: string
  visit_type: string
  professional: string
  status: string
}

export type SaludTodaySchedule = {
  date: string
  visits: SaludTodayVisit[]
}

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = await getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(url, { headers })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function fetchSaludDashboard() {
  return fetchJson<SaludDashboard>('/kpis/salud/dashboard')
}

export function fetchSaludVisitTrends(days = 14) {
  return fetchJson<SaludVisitTrends>(`/kpis/salud/visit-trends?days=${days}`)
}

export function fetchSaludTodaySchedule() {
  return fetchJson<SaludTodaySchedule>('/kpis/salud/today-schedule')
}
