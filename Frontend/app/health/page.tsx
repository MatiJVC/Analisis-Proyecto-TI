'use client'

import useSWR from 'swr'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { RoleGate } from '@/components/auth/role-gate'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard } from '@/components/dashboard/chart-card'
import { StatusBadge } from '@/components/dashboard/status-badge'
import {
  fetchSaludDashboard,
  fetchSaludTodaySchedule,
  fetchSaludVisitTrends,
  type SaludTodayVisit,
} from '@/lib/salud-api'
import {
  Heart,
  Users,
  Calendar,
  MapPin,
  Clock,
  Activity,
  AlertCircle,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const fetcher = <T,>(fn: () => Promise<T>) => fn()

function scheduleBadgeStatus(status: string): 'success' | 'warning' | 'info' | 'error' | 'neutral' {
  const s = status.toLowerCase().replace(/-/g, ' ')
  if (/complet|done|cerrad|finaliz/i.test(s)) return 'success'
  if (/progress|curso|atendi|en curso/i.test(s)) return 'warning'
  if (/cancel|fail|error|crit/i.test(s)) return 'error'
  if (/program|schedul|pend|abiert/i.test(s)) return 'info'
  return 'neutral'
}

function formatAvgVisit(minutes: number | null | undefined): string {
  if (minutes == null || Number.isNaN(minutes)) return '—'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

function HealthContent() {
  const { data: dashboard, error: errDash, isLoading: loadDash } = useSWR(
    'salud-dashboard',
    () => fetcher(fetchSaludDashboard),
    { refreshInterval: 60_000 }
  )

  const { data: trends, error: errTrends, isLoading: loadTrends } = useSWR(
    'salud-visit-trends-14',
    () => fetcher(() => fetchSaludVisitTrends(14)),
    { refreshInterval: 60_000 }
  )

  const { data: schedule, error: errSchedule, isLoading: loadSchedule } = useSWR(
    'salud-today-schedule',
    () => fetcher(fetchSaludTodaySchedule),
    { refreshInterval: 30_000 }
  )

  const apiError = errDash ?? errTrends ?? errSchedule
  const visitData =
    trends?.points?.length && trends.points.length > 0
      ? trends.points
      : Array.from({ length: 14 }, (_, i) => {
          const d = new Date()
          d.setDate(d.getDate() - (13 - i))
          return { date: d.toISOString().split('T')[0], visits: 0, completed: 0 }
        })

  const upcomingVisits: SaludTodayVisit[] = schedule?.visits ?? []

  return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Servicios de salud domiciliaria</h1>
          <p className="text-muted-foreground">
            Operaciones de atención domiciliaria y gestión de pacientes (datos desde la API de analítica)
          </p>
        </div>

        {apiError && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">No se pudo conectar con el backend</p>
              <p className="text-destructive/90">
                Comprueba que FastAPI esté en marcha y que{' '}
                <code className="rounded bg-background/80 px-1">NEXT_PUBLIC_API_BASE_URL</code> apunte al
                servidor (por defecto se usa http://127.0.0.1:8000).
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {loadDash && !dashboard ? (
            <>
              {Array.from({ length: 6 }).map((_, i) => (
                <KPICardSkeleton key={i} />
              ))}
            </>
          ) : (
            <>
              <KPICard
                title="Pacientes activos"
                value={dashboard?.active_patients ?? 0}
                icon={<Heart className="h-5 w-5" />}
              />
              <KPICard
                title="Visitas de hoy"
                value={dashboard?.today_visits ?? 0}
                icon={<Calendar className="h-5 w-5" />}
              />
              <KPICard
                title="Personal de salud"
                value={dashboard?.healthcare_staff ?? 0}
                icon={<Users className="h-5 w-5" />}
              />
              <KPICard
                title="Duración promedio"
                value={formatAvgVisit(dashboard?.avg_visit_time_minutes)}
                icon={<Clock className="h-5 w-5" />}
              />
              <KPICard
                title="Zonas de cobertura"
                value={dashboard?.coverage_zones ?? 0}
                icon={<MapPin className="h-5 w-5" />}
              />
              <KPICard
                title="Satisfacción"
                value={
                  dashboard?.satisfaction_score != null
                    ? dashboard.satisfaction_score
                    : 'N/D'
                }
                icon={<Activity className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        <ChartCard
          title="Tendencia de visitas"
          description={
            loadTrends && !trends
              ? 'Cargando tendencia desde el warehouse…'
              : 'Visitas domiciliarias diarias (programadas vs completadas), últimos 14 días'
          }
        >
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visitData}>
                <defs>
                  <linearGradient id="visitsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="completedGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(val) =>
                    new Date(val + 'T12:00:00').toLocaleDateString('es-CL', {
                      month: 'short',
                      day: 'numeric',
                    })
                  }
                  stroke="var(--muted-foreground)"
                  fontSize={12}
                />
                <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="visits"
                  stroke="var(--chart-2)"
                  fill="url(#visitsGradient)"
                  strokeWidth={2}
                  name="Programadas"
                />
                <Area
                  type="monotone"
                  dataKey="completed"
                  stroke="var(--chart-1)"
                  fill="url(#completedGradient)"
                  strokeWidth={2}
                  name="Completadas"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">
              {schedule?.date ? `Agenda de hoy (${schedule.date})` : 'Agenda de hoy'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadSchedule && !schedule ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-16 animate-pulse rounded-lg border border-border/50 bg-muted/30"
                  />
                ))}
              </div>
            ) : upcomingVisits.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No hay visitas con fecha programada para hoy en el warehouse. Envía eventos{' '}
                <code className="rounded bg-muted px-1 text-xs">visita_upsert</code> con{' '}
                <code className="rounded bg-muted px-1 text-xs">fecha_programada</code> igual a hoy.
              </p>
            ) : (
              <div className="space-y-3">
                {upcomingVisits.map((visit) => (
                  <div
                    key={visit.visita_id}
                    className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-lg font-semibold text-primary">{visit.time_display}</div>
                      <div>
                        <div className="font-medium text-foreground">{visit.patient}</div>
                        <div className="text-sm text-muted-foreground">
                          {visit.visit_type} • {visit.professional}
                        </div>
                      </div>
                    </div>
                    <StatusBadge
                      status={scheduleBadgeStatus(visit.status)}
                      label={visit.status.replace(/-/g, ' ')}
                    />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
  )
}

export default function HealthPage() {
  return (
    <DashboardLayout>
      <RoleGate domain="salud">
        <HealthContent />
      </RoleGate>
    </DashboardLayout>
  )
}
