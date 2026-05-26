"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard, KPICardSkeleton } from "@/components/dashboard/kpi-card";
import {
  ChartCard,
  ChartCardSkeleton,
} from "@/components/dashboard/chart-card";
import {
  StatusBadge,
  SeverityBadge,
} from "@/components/dashboard/status-badge";
import { useIoTKPIs, useIoTDevices } from "@/hooks/use-analytics";
import {
  Cpu,
  Activity,
  AlertTriangle,
  Clock,
  Wifi,
  Battery,
  Signal,
  Zap,
  TrendingUp,
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
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IoTDevice, IoTAlert } from "@/types/analytics";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useState } from "react";
type AllowedDays = 1 | 7 | 30 | 90 | 180 | 365;

export default function IoTPage() {
  const [selectedDays, setSelectedDays] = useState<AllowedDays>(30);

  const filterDaysLabel: Record<AllowedDays, string> = {
    1: "Último día",
    7: "Últimos 7 días",
    30: "Últimos 30 días",
    90: "Últimos 90 días",
    180: "Últimos 180 días",
    365: "Últimos 365 días",
  };

  const { data: kpis, isLoading: kpisLoading } = useIoTKPIs(selectedDays);
  const { data: devices, isLoading: devicesLoading } = useIoTDevices(selectedDays);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "online":
      case true:
        return "text-success";
      case "offline":
      case false:
        return "text-destructive";
      case "warning":
        return "text-warning";
      default:
        return "text-muted-foreground";
    }
  };

  const getBatteryColor = (level: number) => {
    if (level > 50) return "text-success";
    if (level > 20) return "text-warning";
    return "text-destructive";
  };

  // Preparar datos para gráfico de sensores por tipo
  const sensorsList = devices?.sensors || [];
  const sensorsByTypeChartData =
    sensorsList.length > 0
      ? Object.entries(
          sensorsList.reduce(
            (acc, device) => {
              acc[device.sensor_type] = (acc[device.sensor_type] || 0) + 1;
              return acc;
            },
            {} as Record<string, number>,
          ),
        ).map(([name, count]) => ({ name, count }))
      : [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            IoT Monitoring
          </h1>
          <p className="text-muted-foreground">
            Real-time device telemetry and sensor analytics
          </p>
        </div>

        {/* KPIs en Tiempo Real */}
        <ChartCard
          title="KPIs en Tiempo Real"
          description="Métricas actuales del estado de sensores"
        >
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {kpisLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <KPICardSkeleton key={i} />
              ))
            ) : kpis ? (
              <>
                <KPICard
                  title="Total de Sensores"
                  value={kpis.total_sensors ?? 0}
                  icon={<Cpu className="h-5 w-5" />}
                />
                <KPICard
                  title="Sensores en Línea"
                  value={kpis.online_sensors ?? 0}
                  icon={<Wifi className="h-5 w-5" />}
                />
                <KPICard
                  title="Sensores Offline"
                  value={kpis.offline_sensors ?? 0}
                  icon={<AlertTriangle className="h-5 w-5" />}
                />
                <KPICard
                  title="Tasa de Disponibilidad"
                  value={`${((kpis.availability_rate ?? 0) * 100).toFixed(1)}%`}
                  icon={<TrendingUp className="h-5 w-5" />}
                />
                <KPICard
                  title="Nivel Promedio de Batería"
                  value={`${kpis.avg_battery_level?.toFixed(1) ?? 0}%`}
                  icon={<Battery className="h-5 w-5" />}
                />
                <KPICard
                  title="Batería Baja"
                  value={kpis.low_battery_count ?? 0}
                  icon={<Zap className="h-5 w-5" />}
                />
              </>
            ) : null}
          </div>
        </ChartCard>

        {/* KPIs Históricos */}
        <Card className="bg-card border-border">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-semibold text-foreground">
                KPIs Históricos (últimos {selectedDays} días)
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Métricas calculadas en el período seleccionado
              </p>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2 bg-background border-border text-foreground hover:bg-muted whitespace-nowrap"
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
              </DropdownMenuContent>
            </DropdownMenu>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {kpisLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <KPICardSkeleton key={i} />
                ))
              ) : kpis ? (
                <>
                  <KPICard
                    title="Tasa de Validez de Datos"
                    value={`${((kpis.data_validity_rate ?? 0) * 100).toFixed(1)}%`}
                    icon={<Activity className="h-5 w-5" />}
                  />
                  <KPICard
                    title="Anomalías Detectadas"
                    value={kpis.anomalies_detected ?? 0}
                    icon={<AlertTriangle className="h-5 w-5" />}
                  />
                  <KPICard
                    title="Latencia Promedio"
                    value={`${kpis.avg_processing_latency_ms?.toFixed(0) ?? 0}ms`}
                    icon={<Clock className="h-5 w-5" />}
                  />
                </>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {/* Sensores por Tipo */}
        {devicesLoading ? (
          <ChartCardSkeleton />
        ) : sensorsByTypeChartData.length > 0 ? (
          <ChartCard
            title="Distribución por Tipo de Sensor"
            description="Cantidad de sensores agrupados por tipo"
          >
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sensorsByTypeChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="name"
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
                  <Bar dataKey="count" fill="var(--chart-1)" name="Cantidad" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : null}

        {/* Estado de Sensores */}
        {devicesLoading ? (
          <ChartCardSkeleton />
        ) : sensorsList.length > 0 ? (
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold text-foreground flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                Estado de Sensores ({sensorsList.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[500px] overflow-y-auto">
              {sensorsList.slice(0, 10).map((device: any) => (
                <div
                  key={device.sensor_id}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-lg bg-muted ${getStatusColor(device.is_online)}`}
                    >
                      <Signal className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-foreground text-sm truncate">
                        {device.sensor_id}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {device.sensor_type}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {device.battery_level !== null && (
                      <div
                        className={`flex items-center gap-1 ${getBatteryColor(device.battery_level)}`}
                      >
                        <Battery className="h-3 w-3" />
                        <span className="text-xs font-medium">
                          {device.battery_level?.toFixed(0)}%
                        </span>
                      </div>
                    )}
                    <StatusBadge
                      status={device.is_online ? "online" : "offline"}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
