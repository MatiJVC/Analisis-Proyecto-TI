// API Service - Using mock data for now, ready to connect to real endpoints
import * as mockData from "./mock-data";
import { getAccessToken } from "@/lib/keycloak";
import type { DashboardMetricas, ReporteHistorico, DetalleReporteHisto } from "@/types/analytics";
import type { SensorsByTypeResponse, SensorsStatusResponse } from "@/types/analytics";
import type {
  PaymentConciliationResponse,
  PaymentFailuresResponse,
  SlaTimelinePoint,
  CierreDescuadrePoint,
} from "@/types/analytics";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(
  /\/+$/,
  "",
);

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly path: string,
  ) {
    super(`[api] ${status} ${path}`);
    this.name = "ApiError";
  }
}

// When API_BASE_URL is not set, returns fallback (offline / local dev without backend).
// When API_BASE_URL is configured, throws ApiError on any non-OK response or network
// failure so callers (SWR hooks, try/catch) can surface the error to the user instead
// of silently showing stale mock data.
async function fetchAPI<T>(endpoint: string, fallback: T): Promise<T> {
  if (!API_BASE_URL) {
    return fallback;
  }

  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      console.info(`[api] ${response.status} ${path} (sin permiso)`);
    } else {
      console.error(`[api] Error ${response.status} en ${path}`);
    }
    throw new ApiError(response.status, path);
  }
  return response.json();
}

// Orders API
export const ordersAPI = {
  getKPIs: (days: number = 30) =>
    fetchAPI(`/v1/kpis/orders/kpis?days=${days}`, mockData.ordersKPIs),
  getChannels: (days: number = 30) =>
    fetchAPI(`/v1/kpis/orders/channels?days=${days}`, mockData.orderChannels),
  getStatuses: (days: number = 30) =>
    fetchAPI(`/v1/kpis/orders/status?days=${days}`, mockData.orderStatuses),
  getTimeline: (days: number = 30) =>
    fetchAPI(`/v1/kpis/orders/timeline?days=${days}`, mockData.orderTimeline),
};

// Subscriptions API
export const subscriptionsAPI = {
  getKPIs: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/subscriptions/summary?days=${days}`,
      mockData.subscriptionKPIs,
    ),
  getTimeline: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/subscriptions/timeline?days=${days}`,
      mockData.subscriptionTimeline,
    ),
  getRetentionRates: () =>
    fetchAPI("/v1/kpis/subscriptions/retention", mockData.retentionRates),
};

// Notifications API
export const notificationsAPI = {
  getKPIs: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/notifications/kpis?days=${days}`,
      mockData.notificationKPIs,
    ),

  getChannels: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/notifications/channels?days=${days}`,
      mockData.notificationChannels,
    ).then((data: any) => data?.channels ?? data),

  getStatus: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/notifications/status?days=${days}`,
      mockData.notificationStatus,
    ).then((data: any) => data?.statuses ?? data),

  getTimeline: (days: number = 30) =>
    fetchAPI(
      `/v1/kpis/notifications/timeline?days=${days}`,
      mockData.notificationTimeline,
    ).then((data: any) => data?.timeline ?? data),
};

// IoT API
export const iotAPI = {
  getKPIs: (days: number = 30) =>
    fetchAPI(`/v1/kpis/iot/kpis?days=${days}`, mockData.iotKPIs),
  getDevices: (
    days: number = 30,
    status: "all" | "active" | "inactive" = "all",
    search: string = "",
    limit: number = 10,
    offset: number = 0,
  ) =>
    fetchAPI<SensorsStatusResponse>(
      `/v1/kpis/iot/status?days=${days}&status=${status}${search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ""}&limit=${limit}&offset=${offset}`,
      mockData.iotDevices,
    ),
  getAlerts: (days: number = 30, limit: number = 50) =>
    fetchAPI(
      `/v1/kpis/iot/events?days=${days}&limit=${limit}`,
      mockData.iotAlerts,
    ),
  getSensorsByType: (days: number = 30) =>
    fetchAPI<SensorsByTypeResponse>(`/v1/kpis/iot/by-type?days=${days}`, {
      total_sensors: 0,
      sensor_types: [],
    }),
  getTimeline: (days: number = 30) =>
    fetchAPI(`/v1/kpis/iot/timeline?days=${days}`, []),
};

const _emptyIncidentKPIs = {
  activeIncidents: 0,
  resolvedToday: 0,
  avgResolutionTime: 0,
  slaCompliance: 0,
  criticalCount: 0,
};

// Incidents API
export const incidentsAPI = {
  getKPIs: () => fetchAPI("/v1/kpis/incidents/kpis", _emptyIncidentKPIs),
  getTimeline: () =>
    fetchAPI("/v1/kpis/incidents/timeline?days=14", []),
  getList: () => fetchAPI("/v1/kpis/incidents/list", []),
};

// Auditoría API
async function postFetch<T>(endpoint: string): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("API_BASE_URL no configurado");
  }
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = await getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers });
  if (!response.ok) throw new ApiError(response.status, path);
  return response.json();
}

const _mockDashboard: DashboardMetricas = {
  kpiResumen: { volumenTransDiario: 0, crecimientoVolumen: 0, tasaRechazo: 0, uptimeSLA: 100 },
  transaccionesDiarias: [],
  volumenPorMetodo: [],
};

const _mockReportes: ReporteHistorico[] = [];

const _mockConciliation: PaymentConciliationResponse = {
  statuses: [
    { status: "Aprobado", count: 820, percentage: 82.0 },
    { status: "esperando_revisión", count: 90, percentage: 9.0 },
    { status: "discrepancia_de_monto", count: 45, percentage: 4.5 },
    { status: "discrepancia_de_transacciones", count: 25, percentage: 2.5 },
    { status: "Rechazado", count: 20, percentage: 2.0 },
  ],
  total: 1000,
  approval_rate: 82.0,
};

const _mockFailures: PaymentFailuresResponse = {
  rejection_rate: 9.0,
  total: 1000,
  failed: 90,
  reasons: [
    { reason: "Fondos insuficientes", categoria: "tarjeta", count: 34, percentage: 37.8 },
    { reason: "Proveedor no disponible", categoria: "proveedor", count: 22, percentage: 24.4 },
    { reason: "Tarjeta expirada", categoria: "tarjeta", count: 14, percentage: 15.6 },
    { reason: "Monto inválido o fuera de rango permitido", categoria: "validacion", count: 12, percentage: 13.3 },
    { reason: "Error interno del sistema de pagos", categoria: "interno", count: 8, percentage: 8.9 },
  ],
};

const _mockSlaTimeline: SlaTimelinePoint[] = Array.from({ length: 14 }).map((_, i) => {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - (13 - i));
  const iso = d.toISOString().slice(0, 10);
  // Un par de días con incidentes para que el mock no sea plano.
  const downtimeMinutes = i === 4 ? 22.5 : i === 10 ? 8.0 : 0;
  const degradedMinutes = i === 4 ? 5.0 : i === 8 ? 12.0 : 0;
  return { date: iso, downtimeMinutes, degradedMinutes };
});

const _mockCierres: CierreDescuadrePoint[] = Array.from({ length: 7 }).map((_, i) => {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - (6 - i));
  const fecha = d.toISOString().slice(0, 10);
  const reportedTotal = 80000 + i * 4000;
  const reportedCount = 120 + i * 6;
  return {
    fecha,
    reportedTotal,
    internalTotal: reportedTotal - (i % 3 === 0 ? 350 : 0),
    reportedCount,
    internalCount: reportedCount - (i % 3 === 0 ? 1 : 0),
  };
});

export const auditoriaAPI = {
  getDashboard: (): Promise<DashboardMetricas> =>
    fetchAPI("/v1/analitica/dashboard", _mockDashboard),
  getReportes: (): Promise<ReporteHistorico[]> =>
    fetchAPI("/v1/auditoria/reportes", _mockReportes),
  getDetalle: (id: string): Promise<DetalleReporteHisto> =>
    fetchAPI(`/v1/auditoria/reportes/${id}`, {
      id_reporte: id,
      fecha: "",
      kpiResumen: { volumenTransDiario: 0, crecimientoVolumen: 0, tasaRechazo: 0, uptimeSLA: 0 },
      volumenPorMetodo: [],
    } as DetalleReporteHisto),
  generarReporte: (): Promise<{ success: boolean }> =>
    postFetch("/v1/auditoria/reportes/generar"),
  getConciliation: (): Promise<PaymentConciliationResponse> =>
    fetchAPI("/v1/analytics/payments/conciliation", _mockConciliation),
  getFailures: (): Promise<PaymentFailuresResponse> =>
    fetchAPI("/v1/analytics/payments/failures", _mockFailures),
  getSlaTimeline: (): Promise<SlaTimelinePoint[]> =>
    fetchAPI("/v1/analytics/payments/sla/timeline", _mockSlaTimeline),
  getCierresDescuadre: (): Promise<CierreDescuadrePoint[]> =>
    fetchAPI("/v1/auditoria/cierres?limit=30", _mockCierres),
};

// Overview API
export const overviewAPI = {
  getGlobalKPIs: () => fetchAPI("/v1/kpis/overview/kpis", mockData.globalKPIs),
  getServiceStatuses: () =>
    fetchAPI("/v1/kpis/overview/services", mockData.serviceStatuses),
  getRecentActivities: () =>
    fetchAPI("/v1/kpis/overview/activities?limit=10", mockData.recentActivities),
  getCriticalAlerts: () =>
    fetchAPI("/v1/kpis/overview/alerts?limit=10", mockData.criticalAlerts),
};

// CRM API
export const crmAPI = {
  getKPIs: () => fetchAPI("/v1/kpis/crm/kpis", mockData.crmKPIs),
  getTimeline: (days = 14) =>
    fetchAPI(`/v1/kpis/crm/timeline?days=${days}`, mockData.crmTimeline),
  getTickets: () => fetchAPI("/v1/kpis/crm/tickets", mockData.crmTickets),
  getSLA: () => fetchAPI("/v1/kpis/crm/sla", mockData.crmSLA),
  getTicketLive: (ticketId: string) =>
    fetchAPI(`/v1/kpis/crm/tickets/${ticketId}/live`, mockData.crmTicketLive),
  getChannels: () => fetchAPI("/v1/kpis/crm/channels", mockData.crmChannels),
  getPriority: () => fetchAPI("/v1/kpis/crm/priority", mockData.crmPriority),
  getSourceProjects: () =>
    fetchAPI("/v1/kpis/crm/source-projects", mockData.crmSourceProjects),
  getCriticalByModule: () =>
    fetchAPI("/v1/kpis/crm/critical-by-module", mockData.crmCriticalByModule),
};

// Inventory API
export const inventoryAPI = {
  getKPIs: () => fetchAPI("/v1/inventory/kpis", mockData.inventoryKPIs),
  getStockStatus: () =>
    fetchAPI("/v1/inventory/stock-status", mockData.stockStatusSummary).then(
      (data: any) => data?.data ?? data,
    ),
  getWarehouseCapacity: () =>
    fetchAPI("/v1/inventory/snapshot?limit=500", mockData.warehouseCapacity).then(
      (data: any) => {
        const rows = data?.data ?? data;
        if (!Array.isArray(rows)) return rows;
        // El snapshot viene por SKU×ubicación; el gráfico es por ubicación.
        // Si las filas ya traen el shape agregado (mock offline), pasan tal cual.
        if (rows.length === 0 || rows[0]?.physical_stock === undefined) {
          return rows;
        }
        // Agregamos stock físico/reservado/disponible de todos los SKUs por ubicación.
        const byLocation = new Map<string, any>();
        for (const r of rows) {
          const key = r.location_id;
          const existing = byLocation.get(key);
          if (existing) {
            existing.stock += r.physical_stock ?? 0;
            existing.reserved += r.reserved_stock ?? 0;
            existing.available += r.available_stock ?? 0;
          } else {
            byLocation.set(key, {
              location_id:   r.location_id,
              location_code: r.location_code ?? r.location_id,
              location_name: r.location_name ?? r.location_id,
              location_type: r.location_type ?? "WAREHOUSE",
              city:          r.city ?? null,
              stock:         r.physical_stock ?? 0,
              reserved:      r.reserved_stock ?? 0,
              available:     r.available_stock ?? 0,
            });
          }
        }
        return Array.from(byLocation.values());
      },
    ),
  getLowStockItems: () =>
    fetchAPI(
      "/v1/inventory/products/thresholds?below_threshold=true",
      mockData.lowStockItems,
    ).then((data: any) => data?.data ?? data),
  getLocationsCatalog: (locationType?: string) =>
    fetchAPI(
      `/v1/inventory/locations/catalog${locationType ? `?location_type=${locationType}` : ""}`,
      mockData.locationsCatalog,
    ),
  getProductsThresholds: (belowThreshold?: boolean) =>
    fetchAPI(
      `/v1/inventory/products/thresholds${belowThreshold !== undefined ? `?below_threshold=${belowThreshold}` : ""}`,
      mockData.productsThresholds,
    ),
};
