// API Service - Using mock data for now, ready to connect to real endpoints
import * as mockData from './mock-data'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

// Helper function for API calls (ready for real endpoints)
async function fetchAPI<T>(endpoint: string, fallback: T): Promise<T> {
  if (!API_BASE_URL) {
    return fallback
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`)
    if (!response.ok) throw new Error('API Error')
    return response.json()
  } catch {
    console.warn(`Using mock data for ${endpoint}`)
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
  getKPIs: () => fetchAPI('/analytics/incidents/kpis', mockData.incidentKPIs),
  getTimeline: () => fetchAPI('/analytics/incidents/timeline', mockData.incidentTimeline),
  getList: () => fetchAPI('/analytics/incidents/list', mockData.incidents),
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
  getGlobalKPIs: () => fetchAPI('/analytics/overview/kpis', mockData.globalKPIs),
  getServiceStatuses: () => fetchAPI('/analytics/overview/services', mockData.serviceStatuses),
  getRecentActivities: () => fetchAPI('/analytics/overview/activities', mockData.recentActivities),
  getCriticalAlerts: () => fetchAPI('/analytics/overview/alerts', mockData.criticalAlerts),
}
