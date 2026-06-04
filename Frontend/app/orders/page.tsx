"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { RoleGate } from "@/components/auth/role-gate";
import { KPICard, KPICardSkeleton } from "@/components/dashboard/kpi-card";
import {
  ChartCard,
  ChartCardSkeleton,
} from "@/components/dashboard/chart-card";
import { StatusBadge } from "@/components/dashboard/status-badge";
import {
  useOrdersKPIs,
  useOrderChannels,
  useOrderStatuses,
  useOrderTimeline,
} from "@/hooks/use-analytics";
import {
  ShoppingCart,
  Truck,
  DollarSign,
  Clock,
  CheckCircle,
  Package,
  Target,
  AlertCircle,
  Check,
  BanknoteArrowUp,
  BanknoteArrowDown,
  BanknoteX,
  Calendar,
  ChevronDown,
} from "lucide-react";
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
} from "recharts";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  OrderChannel,
  OrderStatus,
  OrderChannelsResponse,
  OrderStatusResponse,
  OrderTimelineResponse,
} from "@/types/analytics";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-5)",
];

const channelsFormat: Record<string, string> = {
  web: "Web",
  app: "Aplicación",
  call_center: "Call Center",
};

const statusFormat: Record<string, string> = {
  delivered: "Pedido entregado",
  paid: "Pedido pagado",
  payment_failed: "Fallo en pago de pedido",
  stock_unavailable: "Stock no disponible",
  stock_reserved: "Stock reservado",
  created: "Recien creado",
};
type AllowedDays = 1 | 7 | 30 | 90 | 180 | 365;

const filterDaysLabel: Record<AllowedDays, string> = {
  1: "Último día",
  7: "Últimos 7 días",
  30: "Últimos 30 días",
  90: "Últimos 90 días",
  180: "Últimos 180 días",
  365: "Últimos 365 días",
};

function OrdersContent() {
  const [selectedDays, setSelectedDays] = useState<AllowedDays>(30);
  const { data: kpis, isLoading: kpisLoading } = useOrdersKPIs(selectedDays);
  const { data: channelsData, isLoading: channelsLoading } = useOrderChannels(selectedDays);
  const { data: statusesData, isLoading: statusesLoading } = useOrderStatuses(selectedDays);
  const { data: timelineData, isLoading: timelineLoading } = useOrderTimeline(selectedDays);

  const channels = channelsData as OrderChannelsResponse | undefined;
  const statuses = statusesData as OrderStatusResponse | undefined;
  const timeline = timelineData as OrderTimelineResponse | undefined;
  return (
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <div className="flex justify-between items-center mr-5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Análisis de Pedidos
            </h1>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2 bg-background border-border text-foreground hover:bg-muted"
                >
                  <Calendar className="h-4 w-4" />
                  <span>{filterDaysLabel[selectedDays]}</span>
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem onClick={() => setSelectedDays(1)}>
                  Último día
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSelectedDays(7)}>
                  Últimos 7 días
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSelectedDays(30)}>
                  Últimos 30 días
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSelectedDays(90)}>
                  Últimos 90 días
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSelectedDays(180)}>
                  Últimos 180 días
                </DropdownMenuItem>

                <DropdownMenuItem onClick={() => setSelectedDays(365)}>
                  Últimos 365 días
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem>Custom range</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>{" "}
          </div>
          <p className="text-muted-foreground">
            Seguimiento de pedidos omnicanal y métricas de rendimiento{" "}
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {kpisLoading ? (
            Array.from({ length: 10 }).map((_, i) => (
              <KPICardSkeleton key={i} />
            ))
          ) : (
            <>
              <KPICard
                title="Ingresos totales generados por ventas."
                value={kpis?.revenue_total ?? 0}
                format="currency"
                icon={<DollarSign className="h-5 w-5" />}
              />
              <KPICard
                title="Cantidad total de pedidos procesados."
                value={kpis?.total_orders ?? 0}
                icon={<ShoppingCart className="h-5 w-5" />}
              />
              <KPICard
                title="Porcentaje de pedidos entregados correctamente."
                value={(kpis?.delivery_rate ?? 0) * 100}
                format="percentage"
                icon={<Truck className="h-5 w-5" />}
              />
              <KPICard
                title="Pedidos que cumplieron tiempos SLA."
                value={(kpis?.sla_compliance ?? 0) * 100}
                format="percentage"
                icon={<Target className="h-5 w-5" />}
              />

              <KPICard
                title="Tiempo promedio desde creación hasta entrega."
                value={kpis?.avg_processing_time_hours ?? 0}
                format="hours"
                icon={<Clock className="h-5 w-5" />}
              />

              <KPICard
                title="Tasa de reserva de stock"
                value={(kpis?.stock_reservation_rate ?? 0) * 100}
                format="percentage"
                icon={<CheckCircle className="h-5 w-5" />}
              />

              <KPICard
                title="Pedidos completados exitosamente de punta a punta."
                value={(kpis?.fulfillment_rate ?? 0) * 100}
                format="percentage"
                icon={<CheckCircle className="h-5 w-5" />}
              />

              <KPICard
                title="Tasa de pagos fallidos"
                value={(kpis?.payment_failure_rate ?? 0) * 100}
                format="percentage"
                icon={<BanknoteX className="h-5 w-5" />}
              />
              <KPICard
                title="Promedio de dinero generado por pedido."
                value={kpis?.average_order_value ?? 0}
                format="currency"
                icon={<Package className="h-5 w-5" />}
              />

              <KPICard
                title="Tasa de pagos exitosos"
                value={(kpis?.payment_success_rate ?? 0) * 100}
                format="percentage"
                icon={<BanknoteArrowUp className="h-5 w-5" />}
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
              title="Cronograma de pedidos"
              description="Volumen diario de pedidos y rendimiento de las entregas"
              className="lg:col-span-2"
            >
              <div className="h-87.5">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline?.timeline ?? []}>
                    <defs>
                      <linearGradient
                        id="ordersGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="var(--chart-2)"
                          stopOpacity={0.4}
                        />
                        <stop
                          offset="95%"
                          stopColor="var(--chart-2)"
                          stopOpacity={0}
                        />
                      </linearGradient>
                      <linearGradient
                        id="revenueGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="var(--chart-1)"
                          stopOpacity={0.4}
                        />
                        <stop
                          offset="95%"
                          stopColor="var(--chart-1)"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(val) =>
                        new Date(val).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })
                      }
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                    />
                    <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="order_count"
                      stroke="var(--chart-2)"
                      fill="url(#ordersGradient)"
                      strokeWidth={2}
                      name="Pedidos totales"
                    />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="var(--chart-1)"
                      fill="url(#revenueGradient)"
                      strokeWidth={2}
                      name="Ganancias"
                    />
                    <Area
                      type="monotone"
                      dataKey="avg_order_value"
                      stroke="var(--chart-5)"
                      fill="var(--chart-5)"
                      fillOpacity={0.3}
                      strokeWidth={2}
                      name="Valor promedio del pedido"
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
            <ChartCard
              title="Pedidos por canal"
              description="Distribución a través de canales de venta."
            >
              <div className="h-75">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={(channels?.channels ?? []).map((channel) => ({
                      ...channel,
                      channel:
                        channelsFormat[channel.channel] || channel.channel,
                    }))}
                    layout="vertical"
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                    />
                    <XAxis
                      type="number"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                    />
                    <YAxis
                      dataKey="channel"
                      type="category"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                      width={80}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Bar
                      dataKey="order_count"
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
            <ChartCard
              title="Estado de pedidos"
              description="Desglose del estado actual"
            >
              <div className="h-75">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={(statuses?.statuses ?? []).map((status) => ({
                        ...status,
                        status: statusFormat[status.status] || status.status,
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="status"
                    >
                      {statuses?.statuses?.map(
                        (entry: OrderStatus, index: number) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ),
                      )}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
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
                  Rendimiento por canal
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {channels?.channels?.map(
                    (channel: OrderChannel, index: number) => (
                      <div key={channel.channel} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground">
                            {channelsFormat[channel.channel] || channel.channel}
                          </span>
                          <span className="text-sm text-muted-foreground">
                            {channel.order_count.toLocaleString()} (
                            {channel.percentage_of_total}%)
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${channel.percentage_of_total}%`,
                              backgroundColor: COLORS[index % COLORS.length],
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
  );
}

export default function OrdersPage() {
  return (
    <DashboardLayout>
      <RoleGate domain="orders">
        <OrdersContent />
      </RoleGate>
    </DashboardLayout>
  );
}
