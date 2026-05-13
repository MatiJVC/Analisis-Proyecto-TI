'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import { StatusBadge } from '@/components/dashboard/status-badge'
import {
  useOrdersKPIs,
  useOrderChannels,
  useOrderStatuses,
  useOrderTimeline,
} from '@/hooks/use-analytics'
import {
  ShoppingCart,
  Truck,
  DollarSign,
  Clock,
  CheckCircle,
  Package,
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
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { OrderChannel, OrderStatus } from '@/types/analytics'

const COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-5)']

export default function OrdersPage() {
  const { data: kpis, isLoading: kpisLoading } = useOrdersKPIs()
  const { data: channels, isLoading: channelsLoading } = useOrderChannels()
  const { data: statuses, isLoading: statusesLoading } = useOrderStatuses()
  const { data: timeline, isLoading: timelineLoading } = useOrderTimeline()

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Orders Analytics</h1>
          <p className="text-muted-foreground">
            Omnichannel order tracking and performance metrics
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
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
                title="Avg Order Value"
                value={kpis?.avgOrderValue ?? 0}
                change={3.2}
                trend="up"
                format="currency"
                icon={<Package className="h-5 w-5" />}
              />
              <KPICard
                title="SLA Compliance"
                value={kpis?.slaCompliance ?? 0}
                change={0.8}
                trend="up"
                format="percentage"
                icon={<CheckCircle className="h-5 w-5" />}
              />
              <KPICard
                title="Pending Orders"
                value={kpis?.pendingOrders ?? 0}
                change={-5.2}
                trend="down"
                icon={<Clock className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Orders Timeline */}
          {timelineLoading ? (
            <ChartCardSkeleton className="lg:col-span-2" />
          ) : (
            <ChartCard
              title="Orders Timeline"
              description="Daily order volume and delivery performance"
              className="lg:col-span-2"
            >
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline ?? []}>
                    <defs>
                      <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="deliveredGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
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
                      name="Total Orders"
                    />
                    <Area
                      type="monotone"
                      dataKey="delivered"
                      stroke="var(--chart-1)"
                      fill="url(#deliveredGradient)"
                      strokeWidth={2}
                      name="Delivered"
                    />
                    <Area
                      type="monotone"
                      dataKey="failed"
                      stroke="var(--chart-5)"
                      fill="var(--chart-5)"
                      fillOpacity={0.3}
                      strokeWidth={2}
                      name="Failed"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}
        </div>

        {/* Second Row */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Orders by Channel */}
          {channelsLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard title="Orders by Channel" description="Distribution across sales channels">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={channels ?? []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                      width={80}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--popover)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: 'var(--foreground)' }}
                    />
                    <Bar
                      dataKey="value"
                      fill="var(--chart-1)"
                      radius={[0, 4, 4, 0]}
                      name="Orders"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Order Status Distribution */}
          {statusesLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard title="Order Status" description="Current status breakdown">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statuses ?? []}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="status"
                    >
                      {statuses?.map((entry: OrderStatus, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--popover)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: 'var(--foreground)' }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}

          {/* Channel Performance Table */}
          {channelsLoading ? (
            <ChartCardSkeleton />
          ) : (
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="text-base font-semibold text-foreground">
                  Channel Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {channels?.map((channel: OrderChannel, index: number) => (
                    <div key={channel.name} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{channel.name}</span>
                        <span className="text-sm text-muted-foreground">
                          {channel.value.toLocaleString()} ({channel.percentage}%)
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${channel.percentage}%`,
                            backgroundColor: COLORS[index % COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* SLA Compliance Section */}
        <ChartCard title="SLA Compliance Metrics" description="Service level agreement tracking">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-success">97.8%</div>
              <div className="text-sm text-muted-foreground mt-1">On-Time Delivery</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">2.4h</div>
              <div className="text-sm text-muted-foreground mt-1">Avg Processing Time</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-foreground">99.2%</div>
              <div className="text-sm text-muted-foreground mt-1">Order Accuracy</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <div className="text-3xl font-bold text-warning">1.1%</div>
              <div className="text-sm text-muted-foreground mt-1">Return Rate</div>
            </div>
          </div>
        </ChartCard>
      </div>
    </DashboardLayout>
  )
}
