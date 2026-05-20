// API Service - Using mock data for now, ready to connect to real endpoints
import * as mockData from './mock-data'
import { getAccessToken } from '@/lib/keycloak'

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

// Helper function for API calls (ready for real endpoints)
async function fetchAPI<T>(endpoint: string, fallback: T): Promise<T> {
  if (!API_BASE_URL) {
    return fallback
  }

  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = await getAccessToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { headers })
    if (!response.ok) throw new Error(`API Error ${response.status}`)
    return response.json()
  } catch (err) {
    console.warn(`Using mock data for ${path}:`, err)
    return fallback
  }
}

// Orders API
export const ordersAPI = {
  getKPIs: () => fetchAPI('/kpis/orders/kpis', mockData.ordersKPIs),
  getChannels: () => fetchAPI('/kpis/orders/channels', mockData.orderChannels),
  getStatuses: () => fetchAPI('/kpis/orders/status', mockData.orderStatuses),
  getTimeline: (days: number = 30) => fetchAPI(`/kpis/orders/timeline?days=${days}`, mockData.orderTimeline),
}

// Subscriptions API
export const subscriptionsAPI = {
  getKPIs: () => fetchAPI('/analytics/subscriptions/kpis', mockData.subscriptionKPIs),
  getTimeline: () => fetchAPI('/analytics/subscriptions/timeline', mockData.subscriptionTimeline),
}

// Notifications API
export const notificationsAPI = {
  getKPIs: () => fetchAPI('/analytics/notifications/kpis', mockData.notificationKPIs),
  getChannels: () => fetchAPI('/analytics/notifications/channels', mockData.notificationChannels),
}

// IoT API
export const iotAPI = {
  getKPIs: () => fetchAPI('/analytics/iot/kpis', mockData.iotKPIs),
  getDevices: () => fetchAPI('/analytics/iot/devices', mockData.iotDevices),
  getAlerts: () => fetchAPI('/analytics/iot/alerts', mockData.iotAlerts),
}

// Incidents API
export const incidentsAPI = {
  getKPIs: () => fetchAPI('/kpis/incidents/kpis', mockData.incidentKPIs),
  getTimeline: () => fetchAPI('/kpis/incidents/timeline?days=14', mockData.incidentTimeline),
  getList: () => fetchAPI('/kpis/incidents/list', mockData.incidents),
}

// Payments API
export const paymentsAPI = {
  getKPIs: () => fetchAPI('/analytics/payments/kpis', mockData.paymentKPIs),
  getTimeline: () => fetchAPI('/analytics/payments/timeline', mockData.paymentTimeline),
}

// Logistics API
export const logisticsAPI = {
  getKPIs: () => fetchAPI('/analytics/logistics/kpis', mockData.logisticsKPIs),
  getRoutes: () => fetchAPI('/analytics/logistics/routes', mockData.routes),
}

// Overview API
export const overviewAPI = {
  getGlobalKPIs: () => fetchAPI('/kpis/overview/kpis', mockData.globalKPIs),
  getServiceStatuses: () => fetchAPI('/kpis/overview/services', mockData.serviceStatuses),
  getRecentActivities: () => fetchAPI('/kpis/overview/activities?limit=10', mockData.recentActivities),
  getCriticalAlerts: () => fetchAPI('/kpis/overview/alerts?limit=10', mockData.criticalAlerts),
}
