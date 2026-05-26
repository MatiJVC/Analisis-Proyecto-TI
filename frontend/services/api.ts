// API Service - Using mock data for now, ready to connect to real endpoints
import * as mockData from './mock-data'

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

// Helper function for API calls (ready for real endpoints)
async function fetchAPI<T>(endpoint: string, fallback: T): Promise<T> {
  console.log(`Fetching data from API: ${endpoint}`)
  if (!API_BASE_URL) {
    return fallback
  }

  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  try {
    const response = await fetch(`${API_BASE_URL}${path}`)
    if (!response.ok) throw new Error(`API Error ${response.status}`)
    return response.json()
  } catch (err) {
    console.warn(`Using mock data for ${path}:`, err)
    return fallback
  }
}

// Orders API
export const ordersAPI = {
  getKPIs: (days: number = 30) => fetchAPI(`/kpis/orders/kpis?days=${days}`, mockData.ordersKPIs),
  getChannels: (days: number = 30) => fetchAPI(`/kpis/orders/channels?days=${days}`, mockData.orderChannels),
  getStatuses: (days: number = 30) => fetchAPI(`/kpis/orders/status?days=${days}`, mockData.orderStatuses),
  getTimeline: (days: number = 30) => fetchAPI(`/kpis/orders/timeline?days=${days}`, mockData.orderTimeline),
}

// Subscriptions API
export const subscriptionsAPI = {
  getKPIs: (days: number = 30) => fetchAPI(`/kpis/subscriptions/summary?days=${days}`, mockData.subscriptionKPIs),
  getTimeline: (days: number = 30) => fetchAPI(`/kpis/subscriptions/timeline?days=${days}`, mockData.subscriptionTimeline),
  getRetentionRates: () => fetchAPI('/kpis/subscriptions/retention', mockData.retentionRates),
}

// Notifications API
export const notificationsAPI = {
  getKPIs: () => fetchAPI('/analytics/notifications/kpis', mockData.notificationKPIs),
  getChannels: () => fetchAPI('/analytics/notifications/channels', mockData.notificationChannels),
}

// IoT API
export const iotAPI = {
  getKPIs: (days: number = 30) => fetchAPI(`/kpis/iot/kpis?days=${days}`, mockData.iotKPIs),
  getDevices: (days: number = 30) => fetchAPI(`/kpis/iot/status?days=${days}`, mockData.iotDevices),
  getAlerts: (days: number = 30, limit: number = 50) => fetchAPI(`/kpis/iot/events?days=${days}&limit=${limit}`, mockData.iotAlerts),
  getSensorsByType: (days: number = 30) => fetchAPI(`/kpis/iot/by-type?days=${days}`, []),
  getTimeline: (days: number = 30) => fetchAPI(`/kpis/iot/timeline?days=${days}`, []),
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
