"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard, KPICardSkeleton } from "@/components/dashboard/kpi-card";
import { ChartCard, ChartCardSkeleton } from "@/components/dashboard/chart-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import {
  usePaymentDashboard,
  useReportesHistoricos,
  useDetalleReporte,
} from "@/hooks/use-analytics";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ShieldCheck,
  CreditCard,
  Plus,
  Download,
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
  BarChart,
  Legend,
} from "recharts";
import { auditoriaAPI } from "@/services/api";
import { toast } from "sonner";
import type { ReporteHistorico } from "@/types/analytics";

const ESTADO_BADGE: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" }
> = {
  completo:   { label: "Completo",   variant: "default" },
  en_proceso: { label: "En proceso", variant: "secondary" },
  fallido:    { label: "Fallido",    variant: "destructive" },
};

export default function PaymentsPage() {
  const { data: dashboard, isLoading: dashboardLoading } = usePaymentDashboard();
  const { data: reportes, isLoading: reportesLoading, mutate: mutateReportes } = useReportesHistoricos();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [generando, setGenerando] = useState(false);
  const { data: detalle, isLoading: detalleLoading } = useDetalleReporte(selectedId);

  const kpis         = dashboard?.kpiResumen;
  const transacciones = dashboard?.transaccionesDiarias ?? [];
  const volumen       = dashboard?.volumenPorMetodo ?? [];
  const crecimiento   = kpis?.crecimientoVolumen ?? 0;

  async function handleGenerarReporte() {
    setGenerando(true);
    try {
      await auditoriaAPI.generarReporte();
      toast.success("Reporte diario generado correctamente");
      mutateReportes();
    } catch {
      toast.error("Error al generar el reporte diario");
    } finally {
      setGenerando(false);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Módulo de Pagos
          </h1>
          <p className="text-muted-foreground">
            Monitoreo de transacciones, métricas diarias y reportes de auditoría
          </p>
        </div>

        <Tabs defaultValue="analitica">
          <TabsList>
            <TabsTrigger value="analitica">Analítica</TabsTrigger>
            <TabsTrigger value="auditoria">Auditoría</TabsTrigger>
          </TabsList>

          {/* ── Tab: Analítica ───────────────────────────────────────────── */}
          <TabsContent value="analitica" className="space-y-6 pt-4">
            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {dashboardLoading ? (
                Array.from({ length: 4 }).map((_, i) => <KPICardSkeleton key={i} />)
              ) : (
                <>
                  <KPICard
                    title="Volumen de transacciones"
                    value={kpis?.volumenTransDiario ?? 0}
                    icon={<CreditCard className="h-5 w-5" />}
                  />
                  <KPICard
                    title="Crecimiento vs semana anterior"
                    value={kpis?.crecimientoVolumen ?? 0}
                    format="percentage"
                    icon={
                      crecimiento >= 0
                        ? <TrendingUp className="h-5 w-5" />
                        : <TrendingDown className="h-5 w-5" />
                    }
                  />
                  <KPICard
                    title="Tasa de rechazo"
                    value={kpis?.tasaRechazo ?? 0}
                    format="percentage"
                    icon={<AlertTriangle className="h-5 w-5" />}
                  />
                  <KPICard
                    title="Uptime SLA"
                    value={kpis?.uptimeSLA ?? 0}
                    format="percentage"
                    icon={<ShieldCheck className="h-5 w-5" />}
                  />
                </>
              )}
            </div>

            {/* Timeline */}
            {dashboardLoading ? (
              <ChartCardSkeleton />
            ) : (
              <ChartCard
                title="Transacciones por hora — últimas 24h"
                description="Volumen de transacciones exitosas y rechazadas hora a hora"
              >
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={transacciones}>
                      <defs>
                        <linearGradient id="exitosasGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="var(--chart-1)" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="hora"
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
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="exitosas"
                        stroke="var(--chart-1)"
                        fill="url(#exitosasGrad)"
                        strokeWidth={2}
                        name="Exitosas"
                      />
                      <Bar
                        dataKey="rechazadas"
                        fill="var(--chart-5)"
                        radius={[2, 2, 0, 0]}
                        name="Rechazadas"
                        opacity={0.8}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            )}

            {/* Volumen por método */}
            {dashboardLoading ? (
              <ChartCardSkeleton />
            ) : (
              <ChartCard
                title="Volumen por método de pago"
                description="Transacciones aprobadas agrupadas por instrumento de pago"
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={volumen}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="metodo"
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
                        dataKey="volumenTrans"
                        fill="var(--chart-2)"
                        radius={[4, 4, 0, 0]}
                        name="Transacciones"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            )}
          </TabsContent>

          {/* ── Tab: Auditoría ───────────────────────────────────────────── */}
          <TabsContent value="auditoria" className="space-y-6 pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">
                  Reportes de cierre diario
                </h2>
                <p className="text-sm text-muted-foreground">
                  Historial de cierres generados con su estado de conciliación
                </p>
              </div>
              <Button onClick={handleGenerarReporte} disabled={generando}>
                <Plus className="h-4 w-4 mr-2" />
                {generando ? "Generando..." : "Generar reporte"}
              </Button>
            </div>

            {reportesLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-12 rounded bg-muted animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(reportes ?? []).length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={5}
                          className="text-center py-10 text-muted-foreground"
                        >
                          No hay reportes generados aún. Usa el botón para crear el primero.
                        </TableCell>
                      </TableRow>
                    ) : (
                      (reportes ?? []).map((r: ReporteHistorico) => {
                        const badge =
                          ESTADO_BADGE[r.estado] ?? {
                            label: r.estado,
                            variant: "secondary" as const,
                          };
                        return (
                          <TableRow key={r.id}>
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              #{r.id}
                            </TableCell>
                            <TableCell>{r.fecha}</TableCell>
                            <TableCell>{r.tipo}</TableCell>
                            <TableCell>
                              <Badge variant={badge.variant}>{badge.label}</Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedId(r.id)}
                              >
                                Ver detalle
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* ── Sheet: Detalle de reporte ────────────────────────────────────── */}
        <Sheet
          open={selectedId !== null}
          onOpenChange={(open) => !open && setSelectedId(null)}
        >
          <SheetContent className="w-[480px] sm:w-[540px] overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Reporte #{selectedId}</SheetTitle>
            </SheetHeader>

            {detalleLoading ? (
              <div className="space-y-4 mt-6">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-10 rounded bg-muted animate-pulse" />
                ))}
              </div>
            ) : detalle ? (
              <div className="space-y-6 mt-6">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Fecha del cierre
                  </p>
                  <p className="text-lg font-semibold mt-1">{detalle.fecha}</p>
                </div>

                <Separator />

                {/* KPIs */}
                <div>
                  <p className="text-sm font-medium text-foreground mb-3">
                    Métricas del día
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border p-4 space-y-1">
                      <p className="text-xs text-muted-foreground">Volumen</p>
                      <p className="text-2xl font-bold">
                        {detalle.kpiResumen.volumenTransDiario.toLocaleString("es-CL")}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border p-4 space-y-1">
                      <p className="text-xs text-muted-foreground">Crecimiento</p>
                      <p className="text-2xl font-bold">
                        {detalle.kpiResumen.crecimientoVolumen >= 0 ? "+" : ""}
                        {detalle.kpiResumen.crecimientoVolumen.toFixed(1)}%
                      </p>
                    </div>
                    <div className="rounded-lg border border-border p-4 space-y-1">
                      <p className="text-xs text-muted-foreground">Tasa de rechazo</p>
                      <p className="text-2xl font-bold">
                        {detalle.kpiResumen.tasaRechazo.toFixed(2)}%
                      </p>
                    </div>
                    <div className="rounded-lg border border-border p-4 space-y-1">
                      <p className="text-xs text-muted-foreground">Uptime SLA</p>
                      <p className="text-2xl font-bold">
                        {detalle.kpiResumen.uptimeSLA.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Volumen por método */}
                <div>
                  <p className="text-sm font-medium text-foreground mb-3">
                    Volumen por método de pago
                  </p>
                  <div className="space-y-0 divide-y divide-border">
                    {detalle.volumenPorMetodo.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-2">
                        Sin datos para esta fecha
                      </p>
                    ) : (
                      detalle.volumenPorMetodo.map((m) => (
                        <div
                          key={m.metodo}
                          className="flex justify-between items-center py-3"
                        >
                          <span className="text-sm text-foreground">{m.metodo}</span>
                          <span className="text-sm font-medium tabular-nums">
                            {m.volumenTrans.toLocaleString("es-CL")}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => window.print()}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Descargar PDF
                </Button>
              </div>
            ) : null}
          </SheetContent>
        </Sheet>
      </div>
    </DashboardLayout>
  );
}
