'use client'

import { useMemo } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { RoleGate } from '@/components/auth/role-gate'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import { StatusBadge, SeverityBadge } from '@/components/dashboard/status-badge'
import {
  useIncidentKPIs,
  useIncidentTimeline,
  useIncidents,
} from '@/hooks/use-analytics'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  AlertCircle,
  ArrowRight,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { Incident } from '@/types/analytics'

const SEVERITY_DISTRIBUTION = [
  { key: 'critical' as const, label: 'Crítica', color: 'var(--destructive)' },
  { key: 'high' as const, label: 'Alta', color: 'var(--warning)' },
  { key: 'medium' as const, label: 'Media', color: 'var(--chart-2)' },
  { key: 'low' as const, label: 'Baja', color: 'var(--muted-foreground)' },
]

function formatResolutionTime(hours: number): string {
  if (hours <= 0) return '0h'
  if (hours < 1) return `${Math.round(hours * 60)}min`
  return `${hours}h`
}

function buildSeverityDistribution(incidents: Incident[] | undefined) {
  const active = incidents?.filter((i) => i.status !== 'resolved') ?? []
  const total = active.length

  return SEVERITY_DISTRIBUTION.map(({ key, label, color }) => {
    const count = active.filter((i) => i.severity === key).length
    const percentage = total > 0 ? Math.round((count / total) * 1000) / 10 : 0
    return { severity: label, count, color, percentage }
  })
}

function IncidentsContent() {
  const { data: kpis, isLoading: kpisLoading } = useIncidentKPIs()
  const { data: timeline, isLoading: timelineLoading } = useIncidentTimeline()
  const { data: incidents, isLoading: incidentsLoading } = useIncidents()

  const activeIncidents = useMemo(
    () => incidents?.filter((i: Incident) => i.status !== 'resolved') ?? [],
    [incidents],
  )

  const severityDistribution = useMemo(
    () => buildSeverityDistribution(incidents),
    [incidents],
  )

  const avgIncidentsPerDay = useMemo(() => {
    if (!timeline?.length) return 0
    const totalOpened = timeline.reduce((sum, point) => sum + point.opened, 0)
    return Math.round((totalOpened / timeline.length) * 10) / 10
  }, [timeline])

  return (
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Gestión de incidentes</h1>
            <p className="text-muted-foreground">
              Monitorea y resuelve incidentes operativos
            </p>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            Crear incidente
          </Button>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {kpisLoading ? (
            Array.from({ length: 5 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Incidentes activos"
                value={kpis?.activeIncidents ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Resueltos hoy"
                value={kpis?.resolvedToday ?? 0}
                icon={<CheckCircle className="h-5 w-5" />}
              />
              <KPICard
                title="Resolución promedio (hrs)"
                value={kpis?.avgResolutionTime ?? 0}
                icon={<Clock className="h-5 w-5" />}
              />
              <KPICard
                title="Cumplimiento SLA"
                value={kpis?.slaCompliance ?? 0}
                format="percentage"
                icon={<Target className="h-5 w-5" />}
              />
              <KPICard
                title="Críticos"
                value={kpis?.criticalCount ?? 0}
                icon={<AlertCircle className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Timeline Chart */}
        {timelineLoading ? (
          <ChartCardSkeleton />
        ) : (
          <ChartCard
            title="Cronología de incidentes"
            description="Volumen diario de incidentes en los últimos 14 días"
          >
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timeline ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val) => new Date(val).toLocaleDateString('es-CL', { month: 'short', day: 'numeric' })}
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
                    labelStyle={{ color: 'var(--foreground)' }}
                  />
                  <Bar dataKey="opened" fill="var(--chart-5)" name="Abiertos" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="resolved" fill="var(--chart-1)" name="Resueltos" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="critical" fill="var(--destructive)" name="Críticos" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {/* Incident List and Metrics */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Active Incidents */}
          {incidentsLoading ? (
            <ChartCardSkeleton className="lg:col-span-2" />
          ) : (
            <Card className="bg-card border-border lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base font-semibold text-foreground">
                  Incidentes activos
                </CardTitle>
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  Ver todos <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activeIncidents.map((incident: Incident) => (
                    <div
                      key={incident.id}
                      className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                    >
                      <div className="flex items-center gap-4">
                        <SeverityBadge severity={incident.severity} />
                        <div>
                          <div className="font-medium text-foreground">{incident.title}</div>
                          <div className="text-sm text-muted-foreground">
                            {incident.id} • Asignado a {incident.assignee}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={incident.status} />
                        <span className="text-sm text-muted-foreground">{incident.updatedAt}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Severity Distribution */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Distribución por severidad
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {severityDistribution.map((item) => (
                <div key={item.severity} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">{item.severity}</span>
                    <span className="text-sm text-muted-foreground">
                      {item.count} ({item.percentage}%)
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${item.percentage}%`,
                        backgroundColor: item.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Response Metrics */}
        <ChartCard title="Métricas de respuesta" description="Rendimiento en respuesta a incidentes">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">N/D</div>
              <div className="text-sm text-muted-foreground mt-1">Tiempo medio de reconocimiento</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">
                {formatResolutionTime(kpis?.avgResolutionTime ?? 0)}
              </div>
              <div className="text-sm text-muted-foreground mt-1">Tiempo medio de resolución</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-success">{kpis?.slaCompliance ?? 0}%</div>
              <div className="text-sm text-muted-foreground mt-1">SLA cumplido</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">{avgIncidentsPerDay}</div>
              <div className="text-sm text-muted-foreground mt-1">Incidentes promedio/día</div>
            </div>
          </div>
        </ChartCard>
      </div>
  )
}

export default function IncidentsPage() {
  return (
    <DashboardLayout>
      <RoleGate domain="incidents">
        <IncidentsContent />
      </RoleGate>
    </DashboardLayout>
  )
}
