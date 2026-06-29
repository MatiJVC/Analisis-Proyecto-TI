// API Service - Using mock data for now, ready to connect to real endpoints
import * as mockData from "./mock-data";
import { getAccessToken } from "@/lib/keycloak";
import type { DashboardMetricas, ReporteHistorico, DetalleReporteHisto } from "@/types/analytics";

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
  getDevices: (days: number = 30) =>
    fetchAPI(`/v1/kpis/iot/status?days=${days}`, mockData.iotDevices),
  getAlerts: (days: number = 30, limit: number = 50) =>
    fetchAPI(
      `/v1/kpis/iot/events?days=${days}&limit=${limit}`,
      mockData.iotAlerts,
    ),
  getSensorsByType: (days: number = 30) =>
    fetchAPI(`/v1/kpis/iot/by-type?days=${days}`, []),
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

// Payments API
export const paymentsAPI = {
  getKPIs: () => fetchAPI("/v1/analytics/payments/kpis", mockData.paymentKPIs),
  getTimeline: () =>
    fetchAPI("/v1/analytics/payments/timeline", mockData.paymentTimeline),
  getFailures: (hours = 24, topN = 10) =>
    fetchAPI(
      `/v1/analytics/payments/failures?hours=${hours}&top_n=${topN}`,
      mockData.paymentFailures,
    ),
  getConciliation: (hours = 24) =>
    fetchAPI(
      `/v1/analytics/payments/conciliation?hours=${hours}`,
      mockData.paymentConciliation,
    ),
  getMethods: (hours = 24) =>
    fetchAPI(
      `/v1/analytics/payments/methods?hours=${hours}`,
      mockData.paymentMethods,
    ),
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
};

// Inventory API
export const inventoryAPI = {
  getKPIs: () => fetchAPI("/v1/inventory/kpis", mockData.inventoryKPIs),
  getStockStatus: () =>
    fetchAPI("/v1/inventory/stock-status", mockData.stockStatusSummary).then(
      (data: any) => data?.data ?? data,
    ),
  getWarehouseCapacity: () =>
    fetchAPI("/v1/inventory/snapshot", mockData.warehouseCapacity).then(
      (data: any) => data?.data ?? data,
    ),
  getLowStockItems: () =>
    fetchAPI(
      "/v1/inventory/products/thresholds?below_threshold=true",
      mockData.lowStockItems,
    ),
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
