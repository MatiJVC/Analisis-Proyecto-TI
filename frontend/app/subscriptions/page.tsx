"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard, KPICardSkeleton } from "@/components/dashboard/kpi-card";
import {
  ChartCard,
  ChartCardSkeleton,
} from "@/components/dashboard/chart-card";
import {
  useSubscriptionKPIs,
  useSubscriptionTimeline,
  useSubscriptionRetentionRates
} from "@/hooks/use-analytics";
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  Zap,
  BanknoteX,
  BadgeQuestionMark,
  UserRoundPlus,
  UserMinus,
  BanknoteArrowUp,
  ClockCheck,
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
  ComposedChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SubscriptionsPage() {
  const { data: kpis, isLoading: kpisLoading } = useSubscriptionKPIs();
  const { data: timeline, isLoading: timelineLoading } =
    useSubscriptionTimeline();

  const {data: retentionRates, isLoading: retentionLoading} = useSubscriptionRetentionRates();
  console.log("Subscription KPIs:", kpis);
  console.log("Subscription Timeline:", timeline);
  console.log("Retention Rates:", retentionRates);
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Suscripciones y Contratos
          </h1>
          <p className="text-muted-foreground">
            Análisis del ciclo de vida de las suscripciones/contratos y de los
            ingresos{" "}
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Suscripciones actualmente activas."
                value={kpis?.stats?.active ?? 0}
                icon={<Users className="h-5 w-5" />}
              />
              <KPICard
                title="Porcentaje de suscripciones renovadas."
                value={kpis?.renewal_rate ?? 0}
                format="percentage"
                icon={<RefreshCw className="h-5 w-5" />}
              />

              <KPICard
                title="Porcentaje de errores en renovaciones o cobros."
                value={kpis?.error_rate ?? 0}
                format="percentage"
                icon={<BanknoteX className="h-5 w-5" />}
              />
              <KPICard
                title="Clientes que gestionaron contratos sin soporte."
                value={kpis?.auto_service_rate ?? 0}
                format="percentage"
                icon={<BadgeQuestionMark className="h-5 w-5" />}
              />
              <KPICard
                title="Nuevas suscripciones creadas."
                value={kpis?.stats?.new_subscriptions ?? 0}
                icon={<UserRoundPlus className="h-5 w-5" />}
              />

              <KPICard
                title="Suscripciones canceladas."
                value={kpis?.stats?.cancellations ?? 0}
                icon={<UserMinus className="h-5 w-5" />}
              />

              <KPICard
                title="Cobros procesados correctamente."
                value={kpis?.stats?.with_billing_success ?? 0}
                icon={<BanknoteArrowUp className="h-5 w-5" />}
              />

              <KPICard
                title="Porcentaje de clientes perdidos."
                value={kpis?.stats?.churn_rate ?? 0}
                format="percentage"
                icon={<TrendingDown className="h-5 w-5" />}
              />

              <KPICard
                title="Tiempo promedio de permanencia de clientes."
                value={kpis?.stats?.avg_lifetime_months ?? 0}
                format="months"
                icon={<ClockCheck className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* Timeline Chart */}
        {timelineLoading ? (
          <ChartCardSkeleton />
        ) : (
          <ChartCard
            title="Cronograma de Suscripciones/Contratos"
            description="Renovaciones mensuales, cancelaciones y nuevas suscripciones"
          >
            <div className="h-87.5">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={timeline?.timeline ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
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
                  <Bar
                    dataKey="renewals"
                    fill="var(--chart-1)"
                    name="Renewals"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="new_subscriptions"
                    fill="var(--chart-2)"
                    name="New"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="cancellations"
                    fill="var(--chart-5)"
                    name="Cancellations"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {/* Metrics Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Retention Metrics */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Métricas de Retención
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {retentionLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-6 bg-muted rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      30 días de retención
                    </span>
                    <span className="text-lg font-semibold text-success">
                      {retentionRates?.retention_rates?.["30_days"]?.toFixed(1) ?? 0}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      90 días de retención
                    </span>
                    <span className="text-lg font-semibold text-foreground">
                      {retentionRates?.retention_rates?.["90_days"]?.toFixed(1) ?? 0}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Año de retención
                    </span>
                    <span className="text-lg font-semibold text-foreground">
                      {retentionRates?.retention_rates?.annual?.toFixed(1) ?? 0}%
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Plan Distribution */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Plan Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  name: "Enterprise",
                  count: 342,
                  percentage: 4.0,
                  color: "var(--chart-1)",
                },
                {
                  name: "Professional",
                  count: 2180,
                  percentage: 25.8,
                  color: "var(--chart-2)",
                },
                {
                  name: "Business",
                  count: 3456,
                  percentage: 40.9,
                  color: "var(--chart-3)",
                },
                {
                  name: "Starter",
                  count: 2474,
                  percentage: 29.3,
                  color: "var(--chart-4)",
                },
              ].map((plan) => (
                <div key={plan.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">
                      {plan.name}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {plan.count.toLocaleString()} ({plan.percentage}%)
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${plan.percentage}%`,
                        backgroundColor: plan.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Revenue Breakdown */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Revenue Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">MRR</span>
                <span className="text-lg font-semibold text-foreground">
                  $423,600
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">ARR</span>
                <span className="text-lg font-semibold text-foreground">
                  $5,083,200
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">ARPU</span>
                <span className="text-lg font-semibold text-foreground">
                  $50.12
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Expansion MRR
                </span>
                <span className="text-lg font-semibold text-success">
                  +$12,450
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Churn Analysis */}
        <ChartCard
          title="Churn Analysis"
          description="Reasons for subscription cancellation"
        >
          <div className="grid gap-4 md:grid-cols-5">
            {[
              { reason: "Price", percentage: 32, color: "var(--chart-5)" },
              { reason: "Features", percentage: 24, color: "var(--chart-3)" },
              {
                reason: "Competition",
                percentage: 18,
                color: "var(--chart-2)",
              },
              { reason: "Support", percentage: 14, color: "var(--chart-4)" },
              {
                reason: "Other",
                percentage: 12,
                color: "var(--muted-foreground)",
              },
            ].map((item) => (
              <div
                key={item.reason}
                className="text-center p-4 rounded-lg border border-border bg-muted/30"
              >
                <div
                  className="text-3xl font-bold"
                  style={{ color: item.color }}
                >
                  {item.percentage}%
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {item.reason}
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </DashboardLayout>
  );
}
