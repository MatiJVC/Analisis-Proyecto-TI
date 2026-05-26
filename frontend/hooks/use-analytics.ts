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
export function useNotificationKPIs() {
  return useSWR('notifications-kpis', notificationsAPI.getKPIs, swrConfig)
}

export function useNotificationChannels() {
  return useSWR('notifications-channels', notificationsAPI.getChannels, swrConfig)
}

// IoT hooks
export function useIoTKPIs(days: number = 30) {
  return useSWR(`iot-kpis-${days}`, () => iotAPI.getKPIs(days), swrConfig)
}

export function useIoTDevices(days: number = 30) {
  return useSWR(`iot-devices-${days}`, () => iotAPI.getDevices(days), swrConfig)
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
