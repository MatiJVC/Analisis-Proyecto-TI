'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
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

export default function IncidentsPage() {
  const { data: kpis, isLoading: kpisLoading } = useIncidentKPIs()
  const { data: timeline, isLoading: timelineLoading } = useIncidentTimeline()
  const { data: incidents, isLoading: incidentsLoading } = useIncidents()

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Incident Management</h1>
            <p className="text-muted-foreground">
              Track and resolve operational incidents
            </p>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            Create Incident
          </Button>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {kpisLoading ? (
            Array.from({ length: 5 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Active Incidents"
                value={kpis?.activeIncidents ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Resolved Today"
                value={kpis?.resolvedToday ?? 0}
                icon={<CheckCircle className="h-5 w-5" />}
              />
              <KPICard
                title="Avg Resolution (hrs)"
                value={kpis?.avgResolutionTime ?? 0}
                icon={<Clock className="h-5 w-5" />}
              />
              <KPICard
                title="SLA Compliance"
                value={kpis?.slaCompliance ?? 0}
                format="percentage"
                icon={<Target className="h-5 w-5" />}
              />
              <KPICard
                title="Critical Count"
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
            title="Incident Timeline"
            description="Daily incident volume over the last 14 days"
          >
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timeline ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
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
                  <Bar dataKey="opened" fill="var(--chart-5)" name="Opened" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="resolved" fill="var(--chart-1)" name="Resolved" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="critical" fill="var(--destructive)" name="Critical" radius={[4, 4, 0, 0]} />
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
                  Active Incidents
                </CardTitle>
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  View all <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {incidents?.filter((i: Incident) => i.status !== 'resolved').map((incident: Incident) => (
                    <div
                      key={incident.id}
                      className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                    >
                      <div className="flex items-center gap-4">
                        <SeverityBadge severity={incident.severity} />
                        <div>
                          <div className="font-medium text-foreground">{incident.title}</div>
                          <div className="text-sm text-muted-foreground">
                            {incident.id} • Assigned to {incident.assignee}
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
                Severity Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { severity: 'Critical', count: 2, color: 'var(--destructive)', percentage: 16.7 },
                { severity: 'High', count: 4, color: 'var(--warning)', percentage: 33.3 },
                { severity: 'Medium', count: 4, color: 'var(--chart-2)', percentage: 33.3 },
                { severity: 'Low', count: 2, color: 'var(--muted-foreground)', percentage: 16.7 },
              ].map((item) => (
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
        <ChartCard title="Response Metrics" description="Incident response performance">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">12min</div>
              <div className="text-sm text-muted-foreground mt-1">Mean Time to Acknowledge</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">2.4h</div>
              <div className="text-sm text-muted-foreground mt-1">Mean Time to Resolve</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-success">94.5%</div>
              <div className="text-sm text-muted-foreground mt-1">SLA Met</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">8.2</div>
              <div className="text-sm text-muted-foreground mt-1">Avg Incidents/Day</div>
            </div>
          </div>
        </ChartCard>
      </div>
    </DashboardLayout>
  )
}
