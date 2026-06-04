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
  useSubscriptionRetentionRates,
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
  Calendar,
  ChevronDown,
  TrendingUpDown,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { RoleGate } from "@/components/auth/role-gate";

function SubscriptionContent() {
  const [selectedDays, setSelectedDays] = useState<AllowedDays>(30);
  type AllowedDays = 1 | 7 | 30 | 90 | 180 | 365;
  const { data: kpis, isLoading: kpisLoading } = useSubscriptionKPIs(selectedDays);
  const { data: timeline, isLoading: timelineLoading } =
    useSubscriptionTimeline(selectedDays);

  const { data: retentionRates, isLoading: retentionLoading } =
    useSubscriptionRetentionRates();

  const filterDaysLabel: Record<AllowedDays, string> = {
    1: "Último día",
    7: "Últimos 7 días",
    30: "Últimos 30 días",
    90: "Últimos 90 días",
    180: "Últimos 180 días",
    365: "Últimos 365 días",
  };

  return (
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <div className="flex justify-between items-center mr-5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Suscripciones y Contratos
            </h1>
            <div>
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
          </div>
          <p className="text-muted-foreground">
            Análisis del ciclo de vida de las suscripciones/contratos y de los
            ingresos{" "}
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {kpisLoading ? (
            Array.from({ length: 10 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Porcentaje de suscripciones renovadas."
                value={(kpis?.renewal_rate ?? 0) * 100}
                format="percentage"
                icon={<RefreshCw className="h-5 w-5" />}
              />
              <KPICard
                title={`Porcentaje de clientes perdidos en ${selectedDays==1 ? "el" : "los"} ${filterDaysLabel[selectedDays].toLowerCase()}.`}
                value={kpis?.stats?.churn_rate ?? 0}
                format="percentage"
                icon={<TrendingDown className="h-5 w-5" />}
              />

              <KPICard
                title={`Crecimiento neto de suscripciones en ${selectedDays==1 ? "el" : "los"} ${filterDaysLabel[selectedDays].toLowerCase()}.`}
                value={kpis?.stats?.net_growth ?? 0}
                format="number"
                icon={<TrendingUpDown className="h-5 w-5" />}
              />

              <KPICard
                title={`Suscripciones activas creadas en ${selectedDays==1 ? "el" : "los"} ${filterDaysLabel[selectedDays].toLowerCase()}.`}
                value={kpis?.stats?.active ?? 0}
                icon={<Users className="h-5 w-5" />}
              />

              <KPICard
                title="Cobros procesados correctamente."
                value={kpis?.stats?.with_billing_success ?? 0}
                icon={<BanknoteArrowUp className="h-5 w-5" />}
              />

              <KPICard
                title="Porcentaje de errores en renovaciones o cobros."
                value={(kpis?.error_rate ?? 0) * 100}
                format="percentage"
                icon={<BanknoteX className="h-5 w-5" />}
              />
              <KPICard
                title="Clientes que gestionaron contratos sin soporte."
                value={(kpis?.auto_service_rate ?? 0) * 100}
                format="percentage"
                icon={<BadgeQuestionMark className="h-5 w-5" />}
              />
              <KPICard
                title={`Nuevas suscripciones creadas en ${selectedDays==1 ? "el" : "los"} ${filterDaysLabel[selectedDays].toLowerCase()}.`}
                value={kpis?.stats?.new_subscriptions ?? 0}
                icon={<UserRoundPlus className="h-5 w-5" />}
              />

              <KPICard
                title={`Suscripciones canceladas en ${selectedDays==1 ? "el" : "los"} ${filterDaysLabel[selectedDays].toLowerCase()}.`}
                value={kpis?.stats?.cancellations ?? 0}
                icon={<UserMinus className="h-5 w-5" />}
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
                    name="Renovaciones"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="new_subscriptions"
                    fill="var(--chart-2)"
                    name="Nuevas Suscripciones"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="cancellations"
                    fill="var(--chart-5)"
                    name="Cancelaciones"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {/* Metrics Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
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
                    <div
                      key={i}
                      className="h-6 bg-muted rounded animate-pulse"
                    />
                  ))}
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      30 días de retención
                    </span>
                    <span className="text-lg font-semibold text-success">
                      {retentionRates?.retention_rates?.["30_days"]?.toFixed(
                        1,
                      ) ?? 0}
                      %
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      90 días de retención
                    </span>
                    <span className="text-lg font-semibold text-foreground">
                      {retentionRates?.retention_rates?.["90_days"]?.toFixed(
                        1,
                      ) ?? 0}
                      %
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Año de retención
                    </span>
                    <span className="text-lg font-semibold text-foreground">
                      {retentionRates?.retention_rates?.annual?.toFixed(1) ?? 0}
                      %
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>



   
        </div>
      </div>
  );
}

export default function SubscriptionPage() {
  return (
    <DashboardLayout>
      <RoleGate domain="subscriptions">
        <SubscriptionContent />
      </RoleGate>
    </DashboardLayout>
  );
}