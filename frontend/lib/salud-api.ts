const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? '').replace(/\/+$/, '')

async function get<T>(path: string, fallback: T): Promise<T> {
  if (!API_BASE) return fallback
  try {
    const res = await fetch(`${API_BASE}${path}`)
    if (!res.ok) throw new Error(`${res.status}`)
    return res.json()
  } catch {
    return fallback
  }
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface SaludDashboard {
  active_patients: number
  today_visits: number
  healthcare_staff: number
  avg_visit_time_minutes: number | null
  coverage_zones: number
  satisfaction_score: number | null
}

export interface SaludVisitTrendPoint {
  date: string
  visits: number
  completed: number
}

export interface SaludVisitTrends {
  days: number
  points: SaludVisitTrendPoint[]
}

export interface SaludTodayVisit {
  visita_id: string
  time_display: string
  patient: string
  visit_type: string
  professional: string
  status: string
}

export interface SaludTodaySchedule {
  date: string
  visits: SaludTodayVisit[]
}

// ── Fetch functions ───────────────────────────────────────────────────────────

const EMPTY_DASHBOARD: SaludDashboard = {
  active_patients: 0,
  today_visits: 0,
  healthcare_staff: 0,
  avg_visit_time_minutes: null,
  coverage_zones: 0,
  satisfaction_score: null,
}

export function fetchSaludDashboard(): Promise<SaludDashboard> {
  return get('/kpis/salud/summary', EMPTY_DASHBOARD)
}

export function fetchSaludVisitTrends(days = 14): Promise<SaludVisitTrends> {
  return get(`/kpis/salud/visit-trends?days=${days}`, { days, points: [] })
}

export function fetchSaludTodaySchedule(): Promise<SaludTodaySchedule> {
  const today = new Date().toISOString().split('T')[0]
  return get('/kpis/salud/today-schedule', { date: today, visits: [] })
}
