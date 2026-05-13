'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import { DataTable, DataTableSkeleton } from '@/components/dashboard/data-table'
import { StatusBadge, SeverityBadge } from '@/components/dashboard/status-badge'
import {
  useGlobalKPIs,
  useServiceStatuses,
  useRecentActivities,
  useCriticalAlerts,
  useOrderTimeline,
} from '@/hooks/use-analytics'
import {
  ShoppingCart,
  Truck,
  DollarSign,
  Bell,
  RefreshCw,
  Cpu,
  AlertTriangle,
  CreditCard,
  TrendingUp,
  ArrowRight,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import type { ServiceStatus, Activity, Alert } from '@/types/analytics'

export default function OverviewPage() {
  const { data: kpis, isLoading: kpisLoading } = useGlobalKPIs()
  const { data: services, isLoading: servicesLoading } = useServiceStatuses()
  const { data: activities, isLoading: activitiesLoading } = useRecentActivities()
  const { data: alerts, isLoading: alertsLoading } = useCriticalAlerts()
  const { data: timeline, isLoading: timelineLoading } = useOrderTimeline()

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Overview</h1>
            <p className="text-muted-foreground">
              Real-time operational metrics across all services
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
              Live data
            </div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {kpisLoading ? (
            Array.from({ length: 8 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Total Orders"
                value={kpis?.totalOrders ?? 0}
                change={12.5}
                trend="up"
                icon={<ShoppingCart className="h-5 w-5" />}
              />
              <KPICard
                title="Delivery Rate"
                value={kpis?.deliveryRate ?? 0}
                change={2.1}
                trend="up"
                format="percentage"
                icon={<Truck className="h-5 w-5" />}
              />
              <KPICard
                title="Revenue"
                value={kpis?.revenue ?? 0}
                change={8.3}
                trend="up"
                format="currency"
                icon={<DollarSign className="h-5 w-5" />}
              />
              <KPICard
                title="Notification Success"
                value={kpis?.notificationSuccessRate ?? 0}
                change={0.5}
                trend="up"
                format="percentage"
                icon={<Bell className="h-5 w-5" />}
              />
              <KPICard
                title="Active Subscriptions"
                value={kpis?.activeSubscriptions ?? 0}
                change={5.2}
                trend="up"
                icon={<RefreshCw className="h-5 w-5" />}
              />
              <KPICard
                title="IoT Alerts"
                value={kpis?.iotAlerts ?? 0}
                change={-15.3}
                trend="down"
                icon={<Cpu className="h-5 w-5" />}
              />
              <KPICard
                title="Active Incidents"
                value={kpis?.incidentCount ?? 0}
                change={-8.0}
                trend="down"
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Payment Failure Rate"
                value={kpis?.paymentFailureRate ?? 0}
                change={-0.2}
                trend="down"
                format="percentage"
                icon={<CreditCard className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Orders Timeline Chart */}
          {timelineLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard
              title="Orders Overview"
              description="Orders and deliveries over the last 30 days"
              action={
                <Link href="/orders">
                  <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground">
                    View details
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              }
            >
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline?.slice(-14) ?? []}>
                    <defs>
                      <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="deliveredGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
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
                    <Area
                      type="monotone"
                      dataKey="orders"
                      stroke="var(--chart-2)"
                      fill="url(#ordersGradient)"
                      strokeWidth={2}
                      name="Orders"
                    />
                    <Area
                      type="monotone"
                      dataKey="delivered"
                      stroke="var(--chart-1)"
                      fill="url(#deliveredGradient)"
                      strokeWidth={2}
                      name="Delivered"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Service Status */}
          {servicesLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard
              title="Service Status"
              description="Real-time health of all microservices"
            >
              <div className="space-y-3">
                {services?.map((service: ServiceStatus) => (
                  <div
                    key={service.name}
                    className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <StatusBadge status={service.status} />
                      <span className="font-medium text-foreground">{service.name}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-foreground">
                        {service.uptime.toFixed(2)}%
                      </div>
                      <div className="text-xs text-muted-foreground">uptime</div>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>

        {/* Bottom Row */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Critical Alerts */}
          {alertsLoading ? (
            <DataTableSkeleton rows={3} cols={2} />
          ) : (
            <Card className="bg-card border-border lg:col-span-1">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold text-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                    Critical Alerts
                  </CardTitle>
                </div>
                <Link href="/incidents">
                  <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                    View all
                  </Button>
                </Link>
              </CardHeader>
              <CardContent className="space-y-3">
                {alerts?.map((alert: Alert) => (
                  <div
                    key={alert.id}
                    className="rounded-lg border border-border/50 bg-muted/30 p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <SeverityBadge severity={alert.severity} />
                      <span className="text-xs text-muted-foreground">{alert.timestamp}</span>
                    </div>
                    <p className="font-medium text-foreground text-sm">{alert.title}</p>
                    <p className="text-xs text-muted-foreground">{alert.message}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Recent Activity */}
          {activitiesLoading ? (
            <DataTableSkeleton rows={5} cols={3} />
          ) : (
            <Card className="bg-card border-border lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base font-semibold text-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activities?.map((activity: Activity) => (
                    <div
                      key={activity.id}
                      className="flex items-start gap-3 rounded-lg border border-border/50 bg-muted/30 p-3"
                    >
                      <StatusBadge
                        status={activity.status || 'neutral'}
                        showDot={true}
                        label=""
                        className="mt-0.5 px-1"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-foreground">{activity.message}</p>
                        <p className="text-xs text-muted-foreground mt-1">{activity.timestamp}</p>
                      </div>
                      <span className="text-xs font-medium text-muted-foreground capitalize shrink-0">
                        {activity.type}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
