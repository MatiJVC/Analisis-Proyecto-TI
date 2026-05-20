"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard, KPICardSkeleton } from "@/components/dashboard/kpi-card";
import { ChartCard, ChartCardSkeleton } from "@/components/dashboard/chart-card";
import { usePaymentKPIs, usePaymentTimeline } from "@/hooks/use-analytics";
import {
  CreditCard,
  DollarSign,
  AlertTriangle,
  TrendingDown,
  Activity,
  ShieldCheck,
} from "lucide-react";
import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PaymentTimeline } from "@/types/analytics";

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

const paymentMethods = [
  { name: "Tarjeta de Crédito", value: 48.5 },
  { name: "Tarjeta de Débito", value: 27.3 },
  { name: "Transferencia", value: 14.2 },
  { name: "Billetera Digital", value: 10.0 },
];

const failureReasons = [
  { reason: "Fondos insuficientes", count: 186, percentage: 45.1 },
  { reason: "Tarjeta rechazada", count: 98, percentage: 23.8 },
  { reason: "Timeout de gateway", count: 72, percentage: 17.5 },
  { reason: "Error de validación", count: 56, percentage: 13.6 },
];

const conciliationStatus = [
  { status: "Aprobado", count: 44820, color: "var(--chart-1)" },
  { status: "Pendiente", count: 660, color: "var(--chart-3)" },
  { status: "Rechazado", count: 412, color: "var(--chart-5)" },
];

export default function PaymentsPage() {
  const { data: kpis, isLoading: kpisLoading } = usePaymentKPIs();
  const { data: timeline, isLoading: timelineLoading } = usePaymentTimeline();

  const timelineData = (timeline as PaymentTimeline[] | undefined) ?? [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Módulo de Pagos
          </h1>
          <p className="text-muted-foreground">
            Monitoreo de transacciones, conciliación y rendimiento del gateway de pagos
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Total de transacciones procesadas"
                value={kpis?.totalTransactions ?? 0}
                icon={<CreditCard className="h-5 w-5" />}
              />
              <KPICard
                title="Pagos fallidos en el período"
                value={kpis?.failedPayments ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Tasa de fallos"
                value={kpis?.failureRate ?? 0}
                format="percentage"
                icon={<TrendingDown className="h-5 w-5" />}
              />
              <KPICard
                title="Ingresos procesados"
                value={kpis?.revenue ?? 0}
                format="currency"
                icon={<DollarSign className="h-5 w-5" />}
              />
              <KPICard
                title="Valor promedio por transacción"
                value={kpis?.avgTransactionValue ?? 0}
                format="currency"
                icon={<Activity className="h-5 w-5" />}
              />
              <KPICard
                title="Disponibilidad del gateway"
                value={kpis?.uptime ?? 0}
                format="percentage"
                icon={<ShieldCheck className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Timeline Chart — full width */}
        <div className="grid gap-6">
          {timelineLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard
              title="Actividad de transacciones — últimas 24 horas"
              description="Volumen de pagos exitosos, fallidos y monto procesado por hora"
            >
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={timelineData}>
                    <defs>
                      <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="amountGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis
                      dataKey="date"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                    />
                    <YAxis
                      yAxisId="left"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      stroke="var(--muted-foreground)"
                      fontSize={12}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                      formatter={(value: number, name: string) => {
                        if (name === "Monto") return [`$${value.toLocaleString()}`, name];
                        return [value.toLocaleString(), name];
                      }}
                    />
                    <Legend />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="successful"
                      stroke="var(--chart-1)"
                      fill="url(#successGradient)"
                      strokeWidth={2}
                      name="Exitosos"
                    />
                    <Bar
                      yAxisId="left"
                      dataKey="failed"
                      fill="var(--chart-5)"
                      radius={[2, 2, 0, 0]}
                      name="Fallidos"
                      opacity={0.8}
                    />
                    <Area
                      yAxisId="right"
                      type="monotone"
                      dataKey="amount"
                      stroke="var(--chart-2)"
                      fill="url(#amountGradient)"
                      strokeWidth={2}
                      name="Monto"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}
        </div>

        {/* Bottom row: 3 cards */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Payment Methods */}
          <ChartCard
            title="Métodos de pago"
            description="Distribución por tipo de instrumento"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={paymentMethods}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                  >
                    {paymentMethods.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--popover)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                    }}
                    formatter={(value: number) => [`${value}%`, "Participación"]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Failure Reasons */}
          <ChartCard
            title="Razones de fallo"
            description="Principales causas de rechazo de transacciones"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={failureReasons} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} />
                  <YAxis
                    dataKey="reason"
                    type="category"
                    stroke="var(--muted-foreground)"
                    fontSize={11}
                    width={130}
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
                    dataKey="count"
                    fill="var(--chart-5)"
                    radius={[0, 4, 4, 0]}
                    name="Fallos"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          {/* Conciliation Status */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Estado de conciliación
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Desglose del resultado de transacciones
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {conciliationStatus.map((item) => {
                  const total = conciliationStatus.reduce((s, c) => s + c.count, 0);
                  const pct = ((item.count / total) * 100).toFixed(1);
                  return (
                    <div key={item.status} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">
                          {item.status}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {item.count.toLocaleString('es-CL')} ({pct}%)
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${pct}%`, backgroundColor: item.color }}
                        />
                      </div>
                    </div>
                  );
                })}

                <div className="pt-4 border-t border-border space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Tasa de aprobación</span>
                    <span className="font-semibold text-foreground">
                      {(
                        (conciliationStatus[0].count /
                          conciliationStatus.reduce((s, c) => s + c.count, 0)) *
                        100
                      ).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Total procesado</span>
                    <span className="font-semibold text-foreground">
                      {conciliationStatus
                        .reduce((s, c) => s + c.count, 0)
                        .toLocaleString('es-CL')}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
