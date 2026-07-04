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
import { useIoTSensorsByType } from "@/hooks/use-analytics";
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
import type { IoTAlert } from "@/types/analytics";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { RoleGate } from "@/components/auth/role-gate";
type AllowedDays = 1 | 7 | 30 | 90 | 180 | 365;
type SensorStatusFilter = "all" | "active" | "inactive";

const sensorTypeTranslations: Record<string, string> = {
  glucometer: "Glucómetro",
  thermometer: "Termómetro",
  pulse_oximeter: "Oxímetro de pulso",
  sphygmomanometer: "Esfigmomanómetro",
};

const translateSensorType = (type: string): string => {
  if (!type) return "";
  return sensorTypeTranslations[type.toLowerCase()] || type;
};

const mapSearchQueryToEnglish = (query: string): string => {
  const q = query.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // remove accents
  if (q.includes("glucometro")) return "glucometer";
  if (q.includes("termometro")) return "thermometer";
  if (q.includes("oximetro")) return "pulse_oximeter";
  if (q.includes("esfigmomanometro") || q.includes("tensiometro")) return "sphygmomanometer";
  return query;
};

function IotContent() {
  const [selectedDays, setSelectedDays] = useState<AllowedDays>(30);
  const [selectedStatus, setSelectedStatus] = useState<SensorStatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const pageSize = 10;

  const filterDaysLabel: Record<AllowedDays, string> = {
    1: "Último día",
    7: "Últimos 7 días",
    30: "Últimos 30 días",
    90: "Últimos 90 días",
    180: "Últimos 180 días",
    365: "Últimos 365 días",
  };

  const statusLabel: Record<SensorStatusFilter, string> = {
    all: "Todos",
    active: "Activos",
    inactive: "Inactivos",
  };

  const { data: kpis, isLoading: kpisLoading } = useIoTKPIs(selectedDays);
  const { data: devices, isLoading: devicesLoading } = useIoTDevices(
    selectedDays,
    selectedStatus,
    searchQuery,
    pageSize,
    (currentPage - 1) * pageSize,
  );
  const { data: sensorsByType, isLoading: typesLoading } = useIoTSensorsByType(selectedDays);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedDays, selectedStatus, searchQuery]);

  const applySearch = () => {
    setCurrentPage(1);
    const mappedQuery = mapSearchQueryToEnglish(searchInput.trim());
    setSearchQuery(mappedQuery);
  };

  const getStatusColor = (status: string | boolean) => {
    if (typeof status === "boolean") {
      return status ? "text-success" : "text-destructive";
    }
    switch (status) {
      case "online":
        return "text-success";
      case "offline":
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
  const sensorsByTypeChartData = (sensorsByType?.sensor_types ?? []).map((item) => ({
    ...item,
    sensor_type: translateSensorType(item.sensor_type),
  }));
  const totalSensors = devices?.total_sensors ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalSensors / pageSize));
  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < totalPages;
  const hasSensors = sensorsList.length > 0;

  const SensorTypeTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;

    const item = payload[0].payload;

    return (
      <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-md">
        <p className="text-sm font-medium text-foreground">
          {item.sensor_type}
        </p>
        <p className="text-xs text-muted-foreground">
          Cantidad: {item.count}
        </p>
      </div>
    );
  };

  return (
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Monitoreo IOT
          </h1>
          <p className="text-muted-foreground">
            Telemetría en tiempo real de dispositivos y análisis de sensores
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
                    title="Tasa de Sensores sin Anomalías"
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
                    value={`${kpis.avg_processing_latency_seconds?.toFixed(3) ?? 0}s`}
                    icon={<Clock className="h-5 w-5" />}
                  />
                </>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {/* Sensores por Tipo */}
        {typesLoading ? (
          <ChartCardSkeleton />
        ) : sensorsByTypeChartData.length > 0 ? (
          <ChartCard
            title="Distribución por Tipo de Sensor"
            description="Cantidad de sensores agrupados por tipo"
          >
            <div className="h-70">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sensorsByTypeChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="sensor_type"
                    stroke="var(--muted-foreground)"
                    fontSize={12}
                  />
                  <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                  <Tooltip content={<SensorTypeTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
                  <Bar dataKey="count" fill="var(--chart-1)" name="Cantidad" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : null}

        {/* Estado de Sensores */}
        {devicesLoading ? (
          <ChartCardSkeleton />
        ) : (
          <Card className="bg-card border-border">
            <CardHeader className="space-y-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <CardTitle className="text-base font-semibold text-foreground flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-primary" />
                  Estado de Sensores ({totalSensors})
                </CardTitle>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-end">
                  <div className="w-full md:w-72">
                    <Input
                      value={searchInput}
                      onChange={(event) => setSearchInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          applySearch();
                        }
                      }}
                      placeholder="Buscar por sensor, activo o tipo"
                      className="bg-background"
                    />
                  </div>
                  <Button
                    variant="default"
                    size="sm"
                    className="whitespace-nowrap"
                    onClick={applySearch}
                  >
                    Buscar
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2 bg-background border-border text-foreground hover:bg-muted whitespace-nowrap"
                      >
                        <span>Estado: {statusLabel[selectedStatus]}</span>
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44">
                      <DropdownMenuItem onClick={() => setSelectedStatus("all")}>Todos</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setSelectedStatus("active")}>Activos</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setSelectedStatus("inactive")}>Inactivos</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3 max-h-125 overflow-y-auto">
                {hasSensors ? (
                  sensorsList.map((device) => (
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
                            {translateSensorType(device.sensor_type)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {device.battery_level !== null && (
                          <div
                            className={`flex items-center gap-1 ${getBatteryColor(device.battery_level ?? 0)}`}
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
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-8 text-center">
                    <p className="text-sm font-medium text-foreground">
                      No hay sensores que coincidan con la búsqueda
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Prueba con otro texto, cambia el estado o limpia el filtro.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
                <p className="text-xs text-muted-foreground">
                  Página {currentPage} de {totalPages}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2 bg-background border-border text-foreground hover:bg-muted whitespace-nowrap"
                      >
                        <span>Ir a página</span>
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="max-h-64 overflow-y-auto w-40">
                      {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
                        <DropdownMenuItem
                          key={pageNumber}
                          onClick={() => setCurrentPage(pageNumber)}
                          className={pageNumber === currentPage ? "font-medium" : ""}
                        >
                          Página {pageNumber}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canGoPrevious}
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  >
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canGoNext}
                    onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
  );
}

export default function IotPage() {
  return (
    <DashboardLayout>
      <RoleGate domain="iot">
        <IotContent />
      </RoleGate>
    </DashboardLayout>
  );
}