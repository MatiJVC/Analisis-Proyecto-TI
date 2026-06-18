'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import { StatusBadge } from '@/components/dashboard/status-badge'
import { useCRMKPIs, useCRMTimeline, useCRMTickets, useCRMSLA } from '@/hooks/use-analytics'
import { ApiError } from '@/services/api'
import {
  Users,
  Headphones,
  Clock,
  ThumbsUp,
  MessageSquare,
  TrendingUp,
  ShieldAlert,
  ShieldCheck,
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
import type { CRMTicketRow } from '@/types/analytics'

const PRIORITY_STATUS: Record<string, 'warning' | 'info' | 'neutral' | 'error'> = {
  alta:   'warning',
  media:  'info',
  baja:   'neutral',
  critica:'error',
}

const STATE_LABEL: Record<string, string> = {
  abierto:     'open',
  en_progreso: 'investigating',
  cerrado:     'resolved',
  escalado:    'warning',
}

function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403)
      return 'Sin permiso para acceder a este módulo'
    if (error.status >= 500)
      return 'Error del servidor — intente nuevamente'
  }
  return 'Error al cargar los datos'
}

function SectionError({ error }: { error: unknown }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-destructive">
      <AlertCircle className="h-5 w-5 shrink-0" />
      <span className="text-sm font-medium">{apiErrorMessage(error)}</span>
    </div>
  )
}

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h}h ${m}min` : `${h}h`
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (diff < 1)   return 'ahora'
  if (diff < 60)  return `${diff} min`
  if (diff < 1440)return `${Math.floor(diff / 60)}h`
  return `${Math.floor(diff / 1440)}d`
}

export default function CRMPage() {
  const { data: kpis,     isLoading: kpisLoading,     error: kpisError }     = useCRMKPIs()
  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useCRMTimeline(14)
  const { data: tickets,  isLoading: ticketsLoading,  error: ticketsError }  = useCRMTickets()
  const { data: sla,      isLoading: slaLoading,      error: slaError }      = useCRMSLA()

  const chartPoints = timeline?.points ?? []

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">CRM & Soporte</h1>
          <p className="text-muted-foreground">
            Gestión de relaciones con clientes y análisis de tickets de soporte
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : kpisError ? (
            <div className="col-span-full"><SectionError error={kpisError} /></div>
          ) : (
            <>
              <KPICard
                title="Total Clientes"
                value={kpis?.totalCustomers ?? 0}
                icon={<Users className="h-5 w-5" />}
              />
              <KPICard
                title="Tickets Abiertos"
                value={kpis?.openTickets ?? 0}
                icon={<Headphones className="h-5 w-5" />}
              />
              <KPICard
                title="Tiempo Respuesta"
                value={formatMinutes(kpis?.avgResponseTimeMinutes ?? 0)}
                icon={<Clock className="h-5 w-5" />}
              />
              <KPICard
                title="CSAT Score"
                value={kpis?.csatScore?.toFixed(1) ?? '0.0'}
                icon={<ThumbsUp className="h-5 w-5" />}
              />
              <KPICard
                title="Mensajes Hoy"
                value={kpis?.messagesToday ?? 0}
                icon={<MessageSquare className="h-5 w-5" />}
              />
              <KPICard
                title="Tasa Resolución"
                value={kpis?.resolutionRate ?? 0}
                format="percentage"
                icon={<TrendingUp className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Timeline Chart */}
        {timelineLoading ? (
          <ChartCardSkeleton />
        ) : timelineError ? (
          <SectionError error={timelineError} />
        ) : (
          <ChartCard title="Volumen de Tickets" description="Tickets abiertos vs resueltos — últimos 14 días">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartPoints}>
                  <defs>
                    <linearGradient id="openedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="resolvedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val) =>
                      new Date(val).toLocaleDateString('es-CL', { month: 'short', day: 'numeric' })
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
                    labelStyle={{ color: 'var(--foreground)' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="opened"
                    stroke="var(--chart-2)"
                    fill="url(#openedGradient)"
                    strokeWidth={2}
                    name="Abiertos"
                  />
                  <Area
                    type="monotone"
                    dataKey="resolved"
                    stroke="var(--chart-1)"
                    fill="url(#resolvedGradient)"
                    strokeWidth={2}
                    name="Resueltos"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {/* Tickets + SLA */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Tickets */}
          {ticketsLoading ? (
            <ChartCardSkeleton className="lg:col-span-2" />
          ) : ticketsError ? (
            <div className="lg:col-span-2"><SectionError error={ticketsError} /></div>
          ) : (
            <Card className="bg-card border-border lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base font-semibold text-foreground">
                  Tickets Recientes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(tickets?.tickets ?? []).map((ticket: CRMTicketRow) => (
                    <div
                      key={ticket.ticketId}
                      className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-foreground truncate">
                            {ticket.asunto}
                          </span>
                          <StatusBadge
                            status={PRIORITY_STATUS[ticket.prioridad] ?? 'neutral'}
                            label={ticket.prioridad}
                          />
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {ticket.ticketId} · {ticket.canal} · {ticket.sourceProject} · {timeAgo(ticket.openedAt)}
                        </div>
                      </div>
                      <div className="ml-4 shrink-0">
                        <StatusBadge status={STATE_LABEL[ticket.estado] ?? ticket.estado} />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* SLA Summary */}
          {slaLoading ? (
            <ChartCardSkeleton />
          ) : slaError ? (
            <SectionError error={slaError} />
          ) : (
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-base font-semibold text-foreground">
                  Cumplimiento SLA
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center">
                  <div className="text-4xl font-bold text-foreground">
                    {sla?.slaComplianceRate?.toFixed(1) ?? 0}%
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">Tasa de cumplimiento</div>
                </div>

                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-chart-1 transition-all"
                    style={{ width: `${sla?.slaComplianceRate ?? 0}%` }}
                  />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-3">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="h-4 w-4 text-destructive" />
                      <span className="text-sm text-foreground">Violaciones críticas</span>
                    </div>
                    <span className="font-semibold text-destructive">
                      {sla?.criticalViolations ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-foreground">Total violaciones</span>
                    </div>
                    <span className="font-semibold text-foreground">
                      {sla?.totalViolations ?? 0}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
