'use client'

import useSWR from 'swr'
import {
  ordersAPI,
  subscriptionsAPI,
  notificationsAPI,
  iotAPI,
  incidentsAPI,
  overviewAPI,
  inventoryAPI,
  crmAPI,
  auditoriaAPI,
} from '@/services/api'
import type { OrderChannelsResponse, OrderStatusResponse, OrderTimelineResponse } from '@/types/analytics'

// SWR configuration
const swrConfig = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  refreshInterval: 30000, // Refresh every 30 seconds
}

// Orders hooks
export function useOrdersKPIs(days: number = 30) {
  return useSWR(`orders-kpis-${days}`, () => ordersAPI.getKPIs(days), swrConfig)
}

export function useOrderChannels(days: number = 30) {
  return useSWR(`orders-channels-${days}`, () => ordersAPI.getChannels(days), swrConfig)
}

export function useOrderStatuses(days: number = 30) {
  return useSWR(`orders-statuses-${days}`, () => ordersAPI.getStatuses(days), swrConfig)
}

export function useOrderTimeline(days: number = 30) {
  return useSWR(`orders-timeline-${days}`, () => ordersAPI.getTimeline(days), swrConfig)
}

// Subscriptions hooks
export function useSubscriptionKPIs(days: number = 1) {
  return useSWR(`subscriptions-kpis-${days}`, () => subscriptionsAPI.getKPIs(days), swrConfig)
}

export function useSubscriptionTimeline(days: number = 1) {
  return useSWR(`subscriptions-timeline-${days}`, () => subscriptionsAPI.getTimeline(days), swrConfig)
}

export function useSubscriptionRetentionRates() {
  return useSWR('subscriptions-retention-rates', subscriptionsAPI.getRetentionRates, swrConfig)
}

// Notifications hooks
export function useNotificationKPIs(days: number = 1) {
  return useSWR(`notifications-kpis-${days}`, () => notificationsAPI.getKPIs(days), swrConfig)
}

export function useNotificationChannels(days: number = 1) {
  return useSWR(`notifications-channels-${days}`, () => notificationsAPI.getChannels(days), swrConfig)
}
export function useNotificationStatus(days: number = 1) {
  return useSWR(`notifications-status-${days}`, () => notificationsAPI.getStatus(days), swrConfig)
}

export function useNotificationTimeline(days: number = 1) {
  return useSWR(`notifications-timeline-${days}`, () => notificationsAPI.getTimeline(days), swrConfig)
}
// IoT hooks
export function useIoTKPIs(days: number = 30) {
  return useSWR(`iot-kpis-${days}`, () => iotAPI.getKPIs(days), swrConfig)
}

export function useIoTDevices(
  days: number = 30,
  status: "all" | "active" | "inactive" = "all",
  search: string = "",
  limit: number = 10,
  offset: number = 0,
) {
  return useSWR(
    `iot-devices-${days}-${status}-${search}-${limit}-${offset}`,
    () => iotAPI.getDevices(days, status, search, limit, offset),
    swrConfig,
  )
}

export function useIoTAlerts(days: number = 30, limit: number = 50) {
  return useSWR(`iot-alerts-${days}-${limit}`, () => iotAPI.getAlerts(days, limit), swrConfig)
}

export function useIoTSensorsByType(days: number = 30) {
  return useSWR(`iot-sensors-by-type-${days}`, () => iotAPI.getSensorsByType(days), swrConfig)
}

export function useIoTTimeline(days: number = 30) {
  return useSWR(`iot-timeline-${days}`, () => iotAPI.getTimeline(days), swrConfig)
}

// Incidents hooks
export function useIncidentKPIs() {
  return useSWR('incidents-kpis', incidentsAPI.getKPIs, swrConfig)
}

export function useIncidentTimeline() {
  return useSWR('incidents-timeline', incidentsAPI.getTimeline, swrConfig)
}

export function useIncidents() {
  return useSWR('incidents-list', incidentsAPI.getList, swrConfig)
}

// Payments hooks
export function usePaymentDashboard() {
  return useSWR('payments-dashboard', auditoriaAPI.getDashboard, swrConfig)
}

export function useReportesHistoricos() {
  return useSWR('auditoria-reportes', auditoriaAPI.getReportes, swrConfig)
}

export function useDetalleReporte(id: string | null) {
  return useSWR(
    id ? `auditoria-reporte-${id}` : null,
    () => auditoriaAPI.getDetalle(id!),
    { ...swrConfig, refreshInterval: 0 },
  )
}

// Overview hooks
export function useGlobalKPIs() {
  return useSWR('overview-kpis', overviewAPI.getGlobalKPIs, swrConfig)
}

export function useServiceStatuses() {
  return useSWR('overview-services', overviewAPI.getServiceStatuses, swrConfig)
}

export function useRecentActivities() {
  return useSWR('overview-activities', overviewAPI.getRecentActivities, swrConfig)
}

export function useCriticalAlerts() {
  return useSWR('overview-alerts', overviewAPI.getCriticalAlerts, swrConfig)
}

// CRM hooks
export function useCRMKPIs() {
  return useSWR('crm-kpis', crmAPI.getKPIs, swrConfig)
}

export function useCRMTimeline(days = 14) {
  return useSWR(`crm-timeline-${days}`, () => crmAPI.getTimeline(days), swrConfig)
}

export function useCRMTickets() {
  return useSWR('crm-tickets', crmAPI.getTickets, swrConfig)
}

export function useCRMSLA() {
  return useSWR('crm-sla', crmAPI.getSLA, swrConfig)
}

export function useCRMChannels() {
  return useSWR('crm-channels', crmAPI.getChannels, swrConfig)
}

export function useCRMPriority() {
  return useSWR('crm-priority', crmAPI.getPriority, swrConfig)
}

export function useCRMSourceProjects() {
  return useSWR('crm-source-projects', crmAPI.getSourceProjects, swrConfig)
}

export function useCRMCsat() {
  return useSWR('crm-csat', crmAPI.getCsatDistribution, swrConfig)
}

// Inventory hooks
export function useInventoryKPIs() {
  return useSWR('inventory-kpis', inventoryAPI.getKPIs, swrConfig)
}

export function useWarehouseCapacity() {
  return useSWR('inventory-warehouse-capacity', inventoryAPI.getWarehouseCapacity, swrConfig)
}

export function useLowStockItems() {
  return useSWR('inventory-low-stock', inventoryAPI.getLowStockItems, swrConfig)
}

export function useStockStatusSummary() {
  return useSWR('inventory-stock-status', inventoryAPI.getStockStatus, swrConfig)
}

export function useLocationsCatalog(locationType?: string) {
  return useSWR(
    `inventory-locations-${locationType ?? 'all'}`,
    () => inventoryAPI.getLocationsCatalog(locationType),
    swrConfig,
  )
}

export function useProductsThresholds(belowThreshold?: boolean) {
  return useSWR(
    `inventory-thresholds-${String(belowThreshold)}`,
    () => inventoryAPI.getProductsThresholds(belowThreshold),
    swrConfig,
  )
}
