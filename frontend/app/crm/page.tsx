'use client'

import { useEffect, useRef, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import { StatusBadge } from '@/components/dashboard/status-badge'
import {
  useCRMKPIs,
  useCRMTimeline,
  useCRMTickets,
  useCRMSLA,
  useCRMChannels,
  useCRMPriority,
  useCRMSourceProjects,
  useCRMCriticalByModule,
} from '@/hooks/use-analytics'
import { ApiError, crmAPI } from '@/services/api'
import {
  Users,
  Headphones,
  Clock,
  AlertTriangle,
  CalendarPlus,
  Loader2,
  Radio,
  TrendingUp,
  ShieldAlert,
  ShieldCheck,
  AlertCircle,
  Search,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { CRMTicketRow, CRMExternalTicketResponse, CRMDistributionItem } from '@/types/analytics'

// Claves capitalizadas — coinciden con el casing real que devuelve el
// backend (Abierto/Progreso/Resuelto/Cerrado, Baja/Media/Alta/Crítica).
// El CRM externo envía minúsculas, pero se normalizan en la ingesta antes
// de guardarse, así que la API siempre responde en este casing.
const PRIORITY_STATUS: Record<string, 'warning' | 'info' | 'neutral' | 'error'> = {
  Alta:    'warning',
  Media:   'info',
  Baja:    'neutral',
  Crítica: 'error',
}

const STATE_LABEL: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  Abierto:  'error',
  Progreso: 'warning',
  Resuelto: 'success',
  Cerrado:  'neutral',
}

const PRIORITY_CHART_COLORS: Record<string, string> = {
  Baja:    'var(--chart-3)',
  Media:   'var(--chart-2)',
  Alta:    'var(--chart-4)',
  Crítica: 'var(--chart-5)',
}

const CHANNEL_CHART_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)']

// Cuántos de los tickets recientes se verifican en vivo contra el CRM
// externo al cargar la página (no en cada auto-refresh de 30s de SWR) —
// limitado por los cold-starts de Vercel del servicio externo (hasta ~8s
// por consulta, sin endpoint bulk).
const LIVE_REFRESH_COUNT = 3

const ESTADO_DISPLAY: Record<string, string> = {
  abierto: 'Abierto', progreso: 'Progreso', resuelto: 'Resuelto', cerrado: 'Cerrado',
}
const PRIORIDAD_DISPLAY: Record<string, string> = {
  baja: 'Baja', media: 'Media', alta: 'Alta', critica: 'Crítica', 'crítica': 'Crítica',
}

// El CRM externo devuelve estado/prioridad en minúscula sin tilde; nuestra
// API interna ya los normaliza — esto deja ambas fuentes con el mismo casing
// al mezclarlas en la UI.
function normalizeEstadoDisplay(value: string): string {
  return ESTADO_DISPLAY[value.toLowerCase()] ?? value
}
function normalizePrioridadDisplay(value: string): string {
  return PRIORIDAD_DISPLAY[value.toLowerCase()] ?? value
}

const chartTooltipProps = {
  contentStyle: {
    backgroundColor: 'var(--popover)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
  },
  labelStyle: { color: 'var(--foreground)' },
}

function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403)
      return 'Sin permiso para acceder a este módulo'
    if (error.status === 404)
      return 'Ticket no encontrado en el CRM externo'
    if (error.status === 504)
      return 'El CRM externo no respondió a tiempo'
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

function TicketLiveSearch() {
  const [ticketId, setTicketId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<CRMExternalTicketResponse | null>(null)

  async function handleSearch() {
    const id = ticketId.trim()
    if (!id) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await crmAPI.getTicketLive(id)
      setResult(data as CRMExternalTicketResponse)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-foreground">
          Consultar ticket en vivo (CRM externo)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="ID del ticket (ej: TKT-4521)"
            value={ticketId}
            onChange={(e) => setTicketId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button onClick={handleSearch} disabled={loading || !ticketId.trim()}>
            <Search className="h-4 w-4 mr-2" />
            {loading ? 'Buscando…' : 'Buscar'}
          </Button>
        </div>

        {error ? (
          <SectionError error={error} />
        ) : result ? (
          <div className="rounded-lg border border-border/50 bg-muted/30 p-4 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-foreground">{result.ticket_id}</span>
              {(() => {
                // El CRM externo devuelve estado/prioridad en minúscula sin
                // tilde; se normaliza al canónico para que el badge tenga el
                // color y texto correctos (igual que en Tickets Recientes).
                const estado = normalizeEstadoDisplay(result.estado)
                return <StatusBadge status={STATE_LABEL[estado] ?? 'neutral'} label={estado} />
              })()}
              {result.prioridad && (() => {
                const prioridad = normalizePrioridadDisplay(result.prioridad)
                return <StatusBadge status={PRIORITY_STATUS[prioridad] ?? 'neutral'} label={prioridad} />
              })()}
            </div>
            {result.asunto && <div className="text-sm text-foreground">{result.asunto}</div>}
            <div className="text-sm text-muted-foreground space-y-1">
              {result.cliente_nombre && <div>Cliente: {result.cliente_nombre}</div>}
              {result.canal && <div>Canal: {result.canal}</div>}
              {result.pago_id_ref && <div>Pago ref: {result.pago_id_ref}</div>}
              {result.salud_ref && <div>Salud ref: {result.salud_ref}</div>}
              {result.suscripcion_id_ref && <div>Suscripción ref: {result.suscripcion_id_ref}</div>}
              {result.resolucion && <div>Resolución: {result.resolucion}</div>}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

export default function CRMPage() {
  const { data: kpis,     isLoading: kpisLoading,     error: kpisError }     = useCRMKPIs()
  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useCRMTimeline(14)
  const { data: tickets,  isLoading: ticketsLoading,  error: ticketsError }  = useCRMTickets()
  const { data: sla,      isLoading: slaLoading,      error: slaError }      = useCRMSLA()
  const { data: channels,       isLoading: channelsLoading,       error: channelsError }       = useCRMChannels()
  const { data: priority,       isLoading: priorityLoading,       error: priorityError }       = useCRMPriority()
  const { data: sourceProjects, isLoading: sourceProjectsLoading, error: sourceProjectsError }  = useCRMSourceProjects()
  const { data: criticalByModule, isLoading: criticalByModuleLoading, error: criticalByModuleError } = useCRMCriticalByModule()

  const chartPoints = timeline?.points ?? []

  // Refresco en vivo de los N tickets más recientes contra el CRM externo —
  // solo al entrar a los IDs top-N por primera vez, no en cada revalidación
  // de SWR (ver LIVE_REFRESH_COUNT).
  const [liveTickets, setLiveTickets] = useState<Record<string, CRMExternalTicketResponse>>({})
  const [liveLoadingId, setLiveLoadingId] = useState<string | null>(null)
  const attemptedLiveIds = useRef<Set<string>>(new Set())
  const topTicketIdsKey = (tickets?.tickets ?? [])
    .slice(0, LIVE_REFRESH_COUNT)
    .map((t) => t.ticketId)
    .join(',')

  useEffect(() => {
    const idsToFetch = topTicketIdsKey ? topTicketIdsKey.split(',').filter((id) => !attemptedLiveIds.current.has(id)) : []
    if (idsToFetch.length === 0) return

    let cancelled = false
    async function fetchSequentially() {
      for (const id of idsToFetch) {
        if (cancelled) return
        attemptedLiveIds.current.add(id)
        setLiveLoadingId(id)
        try {
          const data = await crmAPI.getTicketLive(id)
          if (!cancelled) {
            setLiveTickets((prev) => ({ ...prev, [id]: data as CRMExternalTicketResponse }))
          }
        } catch {
          // Silencioso: si falla la consulta en vivo (timeout, 404, etc.),
          // se deja el dato interno de la lista tal cual estaba.
        }
      }
      if (!cancelled) setLiveLoadingId(null)
    }
    fetchSequentially()
    return () => {
      cancelled = true
    }
  }, [topTicketIdsKey])

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">CRM & Soporte</h1>
          <p className="text-muted-foreground">
            Gestión de relaciones con clientes y análisis de tickets de soporte
          </p>
        </div>

        <TicketLiveSearch />

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
                title="Tiempo Resolución Prom."
                value={formatMinutes(kpis?.avgResponseTimeMinutes ?? 0)}
                icon={<Clock className="h-5 w-5" />}
              />
              <KPICard
                title="Tickets Críticos"
                value={kpis?.criticalTickets ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Tickets Creados Hoy"
                value={kpis?.ticketsCreatedToday ?? 0}
                icon={<CalendarPlus className="h-5 w-5" />}
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

        {/* Distribución de Tickets */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Por Canal */}
          {channelsLoading ? (
            <ChartCardSkeleton />
          ) : channelsError ? (
            <SectionError error={channelsError} />
          ) : (
            <ChartCard title="Tickets por Canal" description="Distribución según canal de contacto">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={channels?.items ?? []}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="name"
                    >
                      {(channels?.items ?? []).map((entry: CRMDistributionItem, index: number) => (
                        <Cell key={`cell-${index}`} fill={CHANNEL_CHART_COLORS[index % CHANNEL_CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip {...chartTooltipProps} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Por Prioridad */}
          {priorityLoading ? (
            <ChartCardSkeleton />
          ) : priorityError ? (
            <SectionError error={priorityError} />
          ) : (
            <ChartCard title="Tickets por Prioridad" description="Distribución según nivel de prioridad">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={priority?.items ?? []}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="name"
                    >
                      {(priority?.items ?? []).map((entry: CRMDistributionItem, index: number) => (
                        <Cell key={`cell-${index}`} fill={PRIORITY_CHART_COLORS[entry.name] ?? 'var(--chart-1)'} />
                      ))}
                    </Pie>
                    <Tooltip {...chartTooltipProps} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Por Dominio de Origen */}
          {sourceProjectsLoading ? (
            <ChartCardSkeleton />
          ) : sourceProjectsError ? (
            <SectionError error={sourceProjectsError} />
          ) : (
            <ChartCard title="Tickets por Dominio de Origen" description="Qué módulo genera más carga de soporte">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sourceProjects?.items ?? []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} />
                    <YAxis dataKey="name" type="category" stroke="var(--muted-foreground)" fontSize={12} width={90} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar dataKey="count" fill="var(--chart-1)" radius={[0, 4, 4, 0]} name="Tickets" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Críticos por Módulo */}
          {criticalByModuleLoading ? (
            <ChartCardSkeleton />
          ) : criticalByModuleError ? (
            <SectionError error={criticalByModuleError} />
          ) : (
            <ChartCard title="Tickets Críticos por Módulo" description="Alta/Crítica abiertos — qué grupo origina más carga urgente">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={criticalByModule?.items ?? []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} allowDecimals={false} />
                    <YAxis dataKey="name" type="category" stroke="var(--muted-foreground)" fontSize={12} width={90} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar dataKey="count" fill="var(--chart-5)" radius={[0, 4, 4, 0]} name="Tickets críticos" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}
        </div>

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
                  {(tickets?.tickets ?? []).map((ticket: CRMTicketRow) => {
                    const live = liveTickets[ticket.ticketId]
                    const estado = normalizeEstadoDisplay(live?.estado ?? ticket.estado)
                    const prioridad = normalizePrioridadDisplay(live?.prioridad ?? ticket.prioridad)
                    const isLiveLoading = liveLoadingId === ticket.ticketId
                    return (
                      <div
                        key={ticket.ticketId}
                        className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-foreground truncate">
                              {ticket.asunto}
                            </span>
                            <StatusBadge status={PRIORITY_STATUS[prioridad] ?? 'neutral'} label={prioridad} />
                            {isLiveLoading && (
                              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
                            )}
                            {live && !isLiveLoading && (
                              <Radio
                                className="h-3.5 w-3.5 shrink-0 text-chart-1"
                                aria-label="Verificado en vivo con el CRM externo"
                              />
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {ticket.ticketId} · {ticket.canal} · {ticket.sourceProject} · {timeAgo(ticket.openedAt)}
                          </div>
                        </div>
                        <div className="ml-4 shrink-0">
                          <StatusBadge status={STATE_LABEL[estado] ?? 'neutral'} label={estado} />
                        </div>
                      </div>
                    )
                  })}
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
                {(sla?.ticketsEvaluated ?? 0) === 0 ? (
                  <div className="text-center">
                    <div className="text-3xl font-bold text-muted-foreground">Sin datos</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Aún no hay tickets resueltos con dato de SLA para evaluar
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="text-center">
                      <div className="text-4xl font-bold text-foreground">
                        {sla?.slaComplianceRate?.toFixed(1) ?? 0}%
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        Tasa de cumplimiento · {sla?.ticketsEvaluated} tickets evaluados
                      </div>
                    </div>

                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-chart-1 transition-all"
                        style={{ width: `${sla?.slaComplianceRate ?? 0}%` }}
                      />
                    </div>
                  </>
                )}

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
