'use client'

import useSWR from 'swr'
import {
  ordersAPI,
  subscriptionsAPI,
  notificationsAPI,
  iotAPI,
  incidentsAPI,
  paymentsAPI,
  logisticsAPI,
  overviewAPI,
} from '@/services/api'
import type { OrderChannelsResponse, OrderStatusResponse, OrderTimelineResponse } from '@/types/analytics'

// SWR configuration
const swrConfig = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  refreshInterval: 30000, // Refresh every 30 seconds
}

// Orders hooks
export function useOrdersKPIs() {
  return useSWR('orders-kpis', ordersAPI.getKPIs, swrConfig)
}

export function useOrderChannels() {
  return useSWR('orders-channels', ordersAPI.getChannels, swrConfig)
}

export function useOrderStatuses() {
  return useSWR('orders-statuses', ordersAPI.getStatuses, swrConfig)
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
export function useNotificationKPIs() {
  return useSWR('notifications-kpis', notificationsAPI.getKPIs, swrConfig)
}

export function useNotificationChannels() {
  return useSWR('notifications-channels', notificationsAPI.getChannels, swrConfig)
}

// IoT hooks
export function useIoTKPIs() {
  return useSWR('iot-kpis', iotAPI.getKPIs, swrConfig)
}

export function useIoTDevices() {
  return useSWR('iot-devices', iotAPI.getDevices, swrConfig)
}

export function useIoTAlerts() {
  return useSWR('iot-alerts', iotAPI.getAlerts, swrConfig)
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
export function usePaymentKPIs() {
  return useSWR('payments-kpis', paymentsAPI.getKPIs, swrConfig)
}

export function usePaymentTimeline() {
  return useSWR('payments-timeline', paymentsAPI.getTimeline, swrConfig)
}

// Logistics hooks
export function useLogisticsKPIs() {
  return useSWR('logistics-kpis', logisticsAPI.getKPIs, swrConfig)
}

export function useRoutes() {
  return useSWR('logistics-routes', logisticsAPI.getRoutes, swrConfig)
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
