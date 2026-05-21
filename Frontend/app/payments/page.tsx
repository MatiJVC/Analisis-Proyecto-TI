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
  { name: "Credit Card", value: 48.5 },
  { name: "Debit Card", value: 27.3 },
  { name: "Bank Transfer", value: 14.2 },
  { name: "Digital Wallet", value: 10.0 },
];

const failureReasons = [
  { reason: "Insufficient funds", count: 186, percentage: 45.1 },
  { reason: "Card declined", count: 98, percentage: 23.8 },
  { reason: "Gateway timeout", count: 72, percentage: 17.5 },
  { reason: "Validation error", count: 56, percentage: 13.6 },
];

const conciliationStatus = [
  { status: "Approved", count: 44820, color: "var(--chart-1)" },
  { status: "Pending", count: 660, color: "var(--chart-3)" },
  { status: "Rejected", count: 412, color: "var(--chart-5)" },
];

export default function PaymentsPage() {
  const { data: kpis, isLoading: kpisLoading } = usePaymentKPIs();
  const { data: timeline, isLoading: timelineLoading } = usePaymentTimeline();

  const timelineData = (timeline as PaymentTimeline[] | undefined) ?? [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Payments
          </h1>
          <p className="text-muted-foreground">
            Transaction monitoring, reconciliation and payment gateway performance
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Total transactions processed"
                value={kpis?.totalTransactions ?? 0}
                icon={<CreditCard className="h-5 w-5" />}
              />
              <KPICard
                title="Failed payments"
                value={kpis?.failedPayments ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Failure rate"
                value={kpis?.failureRate ?? 0}
                format="percentage"
                icon={<TrendingDown className="h-5 w-5" />}
              />
              <KPICard
                title="Revenue processed"
                value={kpis?.revenue ?? 0}
                format="currency"
                icon={<DollarSign className="h-5 w-5" />}
              />
              <KPICard
                title="Avg transaction value"
                value={kpis?.avgTransactionValue ?? 0}
                format="currency"
                icon={<Activity className="h-5 w-5" />}
              />
              <KPICard
                title="Gateway uptime"
                value={kpis?.uptime ?? 0}
                format="percentage"
                icon={<ShieldCheck className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        <div className="grid gap-6">
          {timelineLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard
              title="Transaction activity — last 24 hours"
              description="Volume of successful, failed payments and amount processed per hour"
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
                    <XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={12} />
                    <YAxis yAxisId="left" stroke="var(--muted-foreground)" fontSize={12} />
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
                        if (name === "Amount") return [`$${value.toLocaleString()}`, name];
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
                      name="Successful"
                    />
                    <Bar
                      yAxisId="left"
                      dataKey="failed"
                      fill="var(--chart-5)"
                      radius={[2, 2, 0, 0]}
                      name="Failed"
                      opacity={0.8}
                    />
                    <Area
                      yAxisId="right"
                      type="monotone"
                      dataKey="amount"
                      stroke="var(--chart-2)"
                      fill="url(#amountGradient)"
                      strokeWidth={2}
                      name="Amount"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <ChartCard title="Payment methods" description="Distribution by instrument type">
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
                    formatter={(value: number) => [`${value}%`, "Share"]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard title="Failure reasons" description="Top causes for transaction rejection">
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
                  <Bar dataKey="count" fill="var(--chart-5)" radius={[0, 4, 4, 0]} name="Failures" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground">
                Reconciliation status
              </CardTitle>
              <p className="text-sm text-muted-foreground">Transaction result breakdown</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {conciliationStatus.map((item) => {
                  const total = conciliationStatus.reduce((s, c) => s + c.count, 0);
                  const pct = ((item.count / total) * 100).toFixed(1);
                  return (
                    <div key={item.status} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{item.status}</span>
                        <span className="text-sm text-muted-foreground">
                          {item.count.toLocaleString()} ({pct}%)
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
                    <span className="text-muted-foreground">Approval rate</span>
                    <span className="font-semibold text-foreground">
                      {(
                        (conciliationStatus[0].count /
                          conciliationStatus.reduce((s, c) => s + c.count, 0)) *
                        100
                      ).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Total processed</span>
                    <span className="font-semibold text-foreground">
                      {conciliationStatus.reduce((s, c) => s + c.count, 0).toLocaleString()}
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
