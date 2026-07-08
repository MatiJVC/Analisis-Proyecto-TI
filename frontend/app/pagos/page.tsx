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
  usePaymentConciliation,
  usePaymentFailures,
  usePaymentSlaTimeline,
  useCierresDescuadre,
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
  AreaChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
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

// Etiqueta humana + color por estado de conciliación (donut).
const CONCILIACION_LABEL: Record<string, string> = {
  "Aprobado": "Aprobado",
  "esperando_revisión": "En revisión",
  "discrepancia_de_monto": "Discrep. monto",
  "discrepancia_de_transacciones": "Discrep. transac.",
  "Rechazado": "Rechazado",
};
const CONCILIACION_COLOR: Record<string, string> = {
  "Aprobado": "var(--chart-1)",
  "esperando_revisión": "var(--chart-3)",
  "discrepancia_de_monto": "var(--chart-4)",
  "discrepancia_de_transacciones": "var(--chart-2)",
  "Rechazado": "var(--chart-5)",
};

// Color por categoría de error (barras horizontales de rechazos).
const CATEGORIA_COLOR: Record<string, string> = {
  tarjeta: "var(--chart-2)",
  proveedor: "var(--chart-4)",
  validacion: "var(--chart-3)",
  interno: "var(--chart-5)",
};
const _FALLBACK_COLOR = "var(--chart-1)";

export default function PaymentsPage() {
  const { data: dashboard, isLoading: dashboardLoading } = usePaymentDashboard();
  const { data: reportes, isLoading: reportesLoading, mutate: mutateReportes } = useReportesHistoricos();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [generando, setGenerando] = useState(false);
  const { data: detalle, isLoading: detalleLoading } = useDetalleReporte(selectedId);
  const { data: conciliation, isLoading: conciliationLoading } = usePaymentConciliation();
  const { data: failures, isLoading: failuresLoading } = usePaymentFailures();
  const { data: slaTimeline, isLoading: slaLoading } = usePaymentSlaTimeline();
  const { data: cierres, isLoading: cierresLoading } = useCierresDescuadre();

  const conciliationItems = conciliation?.statuses ?? [];
  const failureReasons     = failures?.reasons ?? [];
  const slaPoints          = slaTimeline ?? [];
  const slaHasData         = slaPoints.some((p) => p.downtimeMinutes > 0 || p.degradedMinutes > 0);
  const cierresList        = cierres ?? [];

  const kpis         = dashboard?.kpiResumen;
  const transacciones = dashboard?.transaccionesDiarias ?? [];
  const volumen       = dashboard?.volumenPorMetodo ?? [];
  const crecimiento   = kpis?.crecimientoVolumen ?? 0;

  function handleDescargarPDF() {
    if (!detalle) return;
    const vol   = detalle.kpiResumen.volumenTransDiario;
    const rej   = detalle.kpiResumen.tasaRechazo;
    const apr   = 100 - rej;
    const totalMet = detalle.volumenPorMetodo.reduce((s, m) => s + m.volumenTrans, 0);
    const COLORS = ["#0f766e","#0284c7","#7c3aed","#b45309","#be123c","#16a34a"];

    // Donut SVG (aprobado vs rechazado)
    const R = 54, cx = 80, cy = 80, stroke = 22;
    const circ = 2 * Math.PI * R;
    const aprDash = (apr / 100) * circ;
    const rejDash = (rej / 100) * circ;
    const rot2 = -90 + (apr / 100) * 360;
    const donutSvg = `<svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#e5e7eb" stroke-width="${stroke}"/>
      ${apr > 0 ? `<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#0f766e" stroke-width="${stroke}"
        stroke-dasharray="${aprDash} ${circ}" transform="rotate(-90 ${cx} ${cy})"/>` : ""}
      ${rej > 0 ? `<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#ef4444" stroke-width="${stroke}"
        stroke-dasharray="${rejDash} ${circ}" transform="rotate(${rot2} ${cx} ${cy})"/>` : ""}
      <text x="${cx}" y="${cy - 5}" text-anchor="middle" font-size="20" font-weight="800" fill="#111">${vol}</text>
      <text x="${cx}" y="${cy + 13}" text-anchor="middle" font-size="11" fill="#6b7280">transacciones</text>
    </svg>`;

    // Bar chart SVG para métodos de pago
    const ROW_H = 50, LABEL_H = 16, BAR_H = 22, BAR_W = 300;
    const maxVal = Math.max(...detalle.volumenPorMetodo.map(m => m.volumenTrans), 1);
    const svgH = detalle.volumenPorMetodo.length * ROW_H + 8;
    const barsSvg = detalle.volumenPorMetodo.length === 0 ? "<p style='color:#6b7280;font-size:13px'>Sin datos</p>" :
      `<svg width="${BAR_W + 120}" height="${svgH}" viewBox="0 0 ${BAR_W + 120} ${svgH}">
        ${detalle.volumenPorMetodo.map((m, i) => {
          const rowTop  = i * ROW_H;
          const labelY  = rowTop + LABEL_H;
          const barY    = rowTop + LABEL_H + 6;
          const barW    = Math.max(Math.round((m.volumenTrans / maxVal) * BAR_W), 4);
          const pct     = totalMet > 0 ? Math.round((m.volumenTrans / totalMet) * 100) : 0;
          return `<text x="0" y="${labelY}" font-size="12" fill="#6b7280">${m.metodo}</text>
            <rect x="0" y="${barY}" width="${barW}" height="${BAR_H}" rx="5" fill="${COLORS[i % COLORS.length]}"/>
            <text x="${barW + 8}" y="${barY + BAR_H - 5}" font-size="13" fill="#111" font-weight="700">${m.volumenTrans} <tspan fill="#6b7280" font-weight="400">(${pct}%)</tspan></text>`;
        }).join("")}
      </svg>`;

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Cierre Diario #${selectedId}</title>
    <style>
      @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: -apple-system, sans-serif; padding: 40px; color: #111; background: #fff; }
      .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f766e; padding-bottom: 16px; margin-bottom: 28px; }
      .header h1 { font-size: 22px; color: #0f766e; margin-bottom: 4px; }
      .header .meta { font-size: 13px; color: #6b7280; }
      .header .badge { background: #ecfdf5; color: #065f46; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid #6ee7b7; }
      .section-title { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 14px; }
      .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 32px; }
      .kpi { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
      .kpi .label { font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
      .kpi .value { font-size: 26px; font-weight: 800; line-height: 1; }
      .kpi .note { font-size: 11px; color: #9ca3af; margin-top: 4px; }
      .kpi.green { border-color: #6ee7b7; background: #f0fdf4; }
      .kpi.green .value { color: #065f46; }
      .kpi.red .value { color: #b91c1c; }
      .kpi.red { border-color: #fca5a5; background: #fff7f7; }
      .charts { display: grid; grid-template-columns: 160px 1fr; gap: 32px; align-items: center; margin-bottom: 32px; }
      .donut-legend { display: flex; flex-direction: column; gap: 10px; }
      .legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
      .dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
      .footer { margin-top: 32px; border-top: 1px solid #e5e7eb; padding-top: 12px; font-size: 11px; color: #9ca3af; display: flex; justify-content: space-between; }
    </style></head><body>
    <div class="header">
      <div>
        <h1>Reporte de Cierre Diario #${selectedId}</h1>
        <div class="meta">Fecha: ${detalle.fecha} &nbsp;·&nbsp; Generado: ${new Date().toLocaleString("es-CL")}</div>
      </div>
      <div class="badge">Módulo de Pagos</div>
    </div>

    <div class="section-title">Métricas del día</div>
    <div class="kpi-grid">
      <div class="kpi ${apr >= 90 ? "green" : ""}">
        <div class="label">Volumen</div>
        <div class="value">${vol.toLocaleString("es-CL")}</div>
        <div class="note">transacciones únicas</div>
      </div>
      <div class="kpi ${detalle.kpiResumen.crecimientoVolumen > 0 ? "green" : detalle.kpiResumen.crecimientoVolumen < 0 ? "red" : ""}">
        <div class="label">Crecimiento</div>
        <div class="value">${detalle.kpiResumen.crecimientoVolumen === 0 ? "—" : (detalle.kpiResumen.crecimientoVolumen > 0 ? "+" : "") + detalle.kpiResumen.crecimientoVolumen.toFixed(1) + "%"}</div>
        <div class="note">${detalle.kpiResumen.crecimientoVolumen === 0 ? "sin datos previos" : "vs semana anterior"}</div>
      </div>
      <div class="kpi ${rej > 10 ? "red" : "green"}">
        <div class="label">Tasa de rechazo</div>
        <div class="value">${rej.toFixed(1)}%</div>
        <div class="note">del total resuelto</div>
      </div>
      <div class="kpi green">
        <div class="label">Uptime SLA</div>
        <div class="value">${detalle.kpiResumen.uptimeSLA.toFixed(1)}%</div>
        <div class="note">disponibilidad</div>
      </div>
    </div>

    <div class="section-title">Distribución de resultados</div>
    <div class="charts">
      ${donutSvg}
      <div class="donut-legend">
        <div class="legend-item"><div class="dot" style="background:#0f766e"></div><span><b>${apr.toFixed(1)}%</b> Aprobadas</span></div>
        <div class="legend-item"><div class="dot" style="background:#ef4444"></div><span><b>${rej.toFixed(1)}%</b> Rechazadas</span></div>
      </div>
    </div>

    <div class="section-title">Volumen por método de pago</div>
    ${barsSvg}

    <div class="footer">
      <span>Analytics Platform — Módulo de Pagos</span>
      <span>Reporte #${selectedId} · ${detalle.fecha}</span>
    </div>
    </body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, "_blank");
    if (!w) return;
    w.focus();
    setTimeout(() => { w.print(); URL.revokeObjectURL(url); }, 600);
  }

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
                title="Transacciones — últimas 24h (cada 30 min)"
                description="Volumen de transacciones exitosas y rechazadas en bloques de 30 minutos"
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
                        fontSize={11}
                        interval={3}
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

            {/* Conciliación por estado (donut) */}
            {conciliationLoading ? (
              <ChartCardSkeleton />
            ) : (
              <ChartCard
                title="Estado de conciliación"
                description="Distribución de transacciones por estado — dónde queda detenido el dinero (últimas 24h)"
              >
                {conciliationItems.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-10 text-center">
                    Sin transacciones en el período.
                  </p>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 items-center">
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={conciliationItems}
                            dataKey="count"
                            nameKey="status"
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={90}
                            paddingAngle={2}
                          >
                            {conciliationItems.map((s) => (
                              <Cell
                                key={s.status}
                                fill={CONCILIACION_COLOR[s.status] ?? _FALLBACK_COLOR}
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "var(--popover)",
                              border: "1px solid var(--border)",
                              borderRadius: "8px",
                            }}
                            labelStyle={{ color: "var(--foreground)" }}
                            formatter={(value: any, _n: any, item: any) => [
                              `${value} (${item?.payload?.percentage ?? 0}%)`,
                              CONCILIACION_LABEL[item?.payload?.status] ?? item?.payload?.status,
                            ]}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground mb-1">
                        Tasa de aprobación:{" "}
                        <span className="font-bold text-foreground">
                          {conciliation?.approval_rate?.toFixed(1) ?? 0}%
                        </span>
                      </p>
                      {conciliationItems.map((s) => (
                        <div key={s.status} className="flex items-center gap-2 text-sm">
                          <span
                            className="h-3 w-3 rounded-sm flex-shrink-0"
                            style={{ background: CONCILIACION_COLOR[s.status] ?? _FALLBACK_COLOR }}
                          />
                          <span className="flex-1 text-foreground">
                            {CONCILIACION_LABEL[s.status] ?? s.status}
                          </span>
                          <span className="tabular-nums text-muted-foreground">
                            {s.count} · {s.percentage}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </ChartCard>
            )}

            {/* Motivos de rechazo (barras horizontales) */}
            {failuresLoading ? (
              <ChartCardSkeleton />
            ) : (
              <ChartCard
                title="Motivos de rechazo"
                description="Top razones de fallo, coloreadas por categoría de error (últimas 24h)"
              >
                {failureReasons.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-10 text-center">
                    Sin rechazos con motivo registrado en el período.
                  </p>
                ) : (
                  <>
                    <div style={{ height: Math.max(failureReasons.length * 48, 160) }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={failureReasons}
                          layout="vertical"
                          margin={{ left: 12, right: 24 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="var(--border)"
                            horizontal={false}
                          />
                          <XAxis
                            type="number"
                            stroke="var(--muted-foreground)"
                            fontSize={12}
                            allowDecimals={false}
                          />
                          <YAxis
                            type="category"
                            dataKey="reason"
                            stroke="var(--muted-foreground)"
                            fontSize={11}
                            width={160}
                          />
                          <Tooltip
                            cursor={{ fill: "var(--muted)", opacity: 0.3 }}
                            contentStyle={{
                              backgroundColor: "var(--popover)",
                              border: "1px solid var(--border)",
                              borderRadius: "8px",
                            }}
                            labelStyle={{ color: "var(--foreground)" }}
                            formatter={(value: any, _n: any, item: any) => [
                              `${value} (${item?.payload?.percentage ?? 0}%)`,
                              item?.payload?.categoria ?? "—",
                            ]}
                          />
                          <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Transacciones">
                            {failureReasons.map((r) => (
                              <Cell
                                key={r.reason}
                                fill={CATEGORIA_COLOR[r.categoria ?? ""] ?? _FALLBACK_COLOR}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-3">
                      {Object.entries(CATEGORIA_COLOR).map(([cat, color]) => (
                        <div
                          key={cat}
                          className="flex items-center gap-1.5 text-xs text-muted-foreground"
                        >
                          <span
                            className="h-2.5 w-2.5 rounded-sm"
                            style={{ background: color }}
                          />
                          <span className="capitalize">{cat}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </ChartCard>
            )}

            {/* Incidentes SLA — downtime vs degradación (área apilada) */}
            {slaLoading ? (
              <ChartCardSkeleton />
            ) : (
              <ChartCard
                title="Incidentes de SLA — últimos 14 días"
                description="Minutos de downtime y degradación por día"
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={slaPoints}>
                      <defs>
                        <linearGradient id="downtimeGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--chart-5)" stopOpacity={0.5} />
                          <stop offset="95%" stopColor="var(--chart-5)" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="degradedGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--chart-4)" stopOpacity={0.5} />
                          <stop offset="95%" stopColor="var(--chart-4)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="date"
                        stroke="var(--muted-foreground)"
                        fontSize={11}
                        tickFormatter={(d: string) => d?.slice(5)}
                      />
                      <YAxis stroke="var(--muted-foreground)" fontSize={12} width={54} unit=" m" />
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
                        dataKey="downtimeMinutes"
                        stackId="1"
                        stroke="var(--chart-5)"
                        fill="url(#downtimeGrad)"
                        strokeWidth={2}
                        name="Downtime (min)"
                      />
                      <Area
                        type="monotone"
                        dataKey="degradedMinutes"
                        stackId="1"
                        stroke="var(--chart-4)"
                        fill="url(#degradedGrad)"
                        strokeWidth={2}
                        name="Degradación (min)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                {!slaHasData && (
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    Sin incidentes de disponibilidad registrados en el período.
                  </p>
                )}
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

            {/* Descuadre reportado vs. interno (líneas) */}
            {cierresLoading ? (
              <ChartCardSkeleton />
            ) : cierresList.length === 0 ? null : (
              <ChartCard
                title="Descuadre reportado vs. interno"
                description="Monto total reportado por el origen frente al conciliado internamente, por cierre diario"
              >
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={cierresList}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="fecha"
                        stroke="var(--muted-foreground)"
                        fontSize={11}
                        tickFormatter={(d: string) => d?.slice(5)}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={12}
                        width={72}
                        tickFormatter={(v: number) => v.toLocaleString("es-CL")}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--popover)",
                          border: "1px solid var(--border)",
                          borderRadius: "8px",
                        }}
                        labelStyle={{ color: "var(--foreground)" }}
                        formatter={(value: any) =>
                          value == null ? "—" : Number(value).toLocaleString("es-CL")
                        }
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="reportedTotal"
                        stroke="var(--chart-1)"
                        strokeWidth={2}
                        name="Reportado"
                        dot={{ r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="internalTotal"
                        stroke="var(--chart-2)"
                        strokeWidth={2}
                        name="Interno"
                        dot={{ r: 3 }}
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            )}

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
          <SheetContent className="w-[480px] sm:w-[560px] overflow-y-auto p-0">
            {/* Header con fondo */}
            <div className="bg-muted/40 border-b border-border px-6 py-5">
              <SheetHeader>
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <CreditCard className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <SheetTitle className="text-base">Cierre diario #{selectedId}</SheetTitle>
                    {detalle && (
                      <p className="text-xs text-muted-foreground mt-0.5">{detalle.fecha}</p>
                    )}
                  </div>
                </div>
              </SheetHeader>
            </div>

            {detalleLoading ? (
              <div className="space-y-4 p-6">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-12 rounded-lg bg-muted animate-pulse" />
                ))}
              </div>
            ) : detalle ? (
              <div className="p-6 space-y-6">

                {/* KPIs en grid 2×2 */}
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                    Métricas del día
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-primary/5 border border-primary/10 p-4">
                      <p className="text-xs text-muted-foreground mb-1">Volumen</p>
                      <p className="text-3xl font-bold text-foreground">
                        {detalle.kpiResumen.volumenTransDiario.toLocaleString("es-CL")}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">transacciones</p>
                    </div>
                    <div className={`rounded-xl border p-4 ${
                      detalle.kpiResumen.crecimientoVolumen >= 0
                        ? "bg-emerald-500/5 border-emerald-500/10"
                        : "bg-rose-500/5 border-rose-500/10"
                    }`}>
                      <p className="text-xs text-muted-foreground mb-1">Crecimiento</p>
                      <p className={`text-3xl font-bold ${
                        detalle.kpiResumen.crecimientoVolumen >= 0 ? "text-emerald-600" : "text-rose-600"
                      }`}>
                        {detalle.kpiResumen.crecimientoVolumen >= 0 ? "+" : ""}
                        {detalle.kpiResumen.crecimientoVolumen.toFixed(1)}%
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">vs semana anterior</p>
                    </div>
                    <div className={`rounded-xl border p-4 ${
                      detalle.kpiResumen.tasaRechazo > 10
                        ? "bg-amber-500/5 border-amber-500/10"
                        : "bg-muted/40 border-border"
                    }`}>
                      <p className="text-xs text-muted-foreground mb-1">Tasa de rechazo</p>
                      <p className={`text-3xl font-bold ${
                        detalle.kpiResumen.tasaRechazo > 10 ? "text-amber-600" : "text-foreground"
                      }`}>
                        {detalle.kpiResumen.tasaRechazo.toFixed(1)}%
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">del total</p>
                    </div>
                    <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/10 p-4">
                      <p className="text-xs text-muted-foreground mb-1">Uptime SLA</p>
                      <p className="text-3xl font-bold text-emerald-600">
                        {detalle.kpiResumen.uptimeSLA.toFixed(1)}%
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">disponibilidad</p>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Volumen por método */}
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                    Volumen por método de pago
                  </p>
                  {detalle.volumenPorMetodo.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-2">Sin datos para esta fecha</p>
                  ) : (
                    <div className="space-y-2">
                      {(() => {
                        const total = detalle.volumenPorMetodo.reduce((s, m) => s + m.volumenTrans, 0);
                        return detalle.volumenPorMetodo.map((m) => {
                          const pct = total > 0 ? Math.round((m.volumenTrans / total) * 100) : 0;
                          return (
                            <div key={m.metodo} className="rounded-lg border border-border bg-muted/20 p-3">
                              <div className="flex justify-between items-center mb-1.5">
                                <span className="text-sm font-medium text-foreground">{m.metodo}</span>
                                <span className="text-sm font-bold tabular-nums">
                                  {m.volumenTrans.toLocaleString("es-CL")}
                                </span>
                              </div>
                              <div className="h-1.5 rounded-full bg-border overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-primary"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">{pct}% del total</p>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  )}
                </div>

                <Button
                  variant="outline"
                  className="w-full h-10 font-medium"
                  onClick={handleDescargarPDF}
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
