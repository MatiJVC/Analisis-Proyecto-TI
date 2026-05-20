// KPI Types
export interface KPIData {
  label: string
  value: string | number
  change?: number
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: string
}

// Orders
export interface OrdersKPIs {
  average_order_value: number
  avg_processing_time_hours: number
  delivery_rate: number
  fulfillment_rate: number
  payment_failure_rate: number
  payment_success_rate: number
  total_orders: number
  revenue_total: number
  sla_compliance: number
  stock_reservation_rate: number
  pendingOrders: number
}

export interface OrderChannel {
  channels: Array<OrderChannel>
  channel: string
  order_count: number
  percentage_of_total: number
  revenue: number
}

export interface OrderChannelsResponse {
  total_orders: number
  channels: OrderChannel[]
}

export interface OrderStatus {
  status: string
  count: number
  color: string
}

export interface OrderStatusResponse {
  total_orders: number
  statuses: OrderStatus[]
}

export interface OrderTimeline {
  date: string
  order_count: number
  delivered_count: number
  failed_count: number
  revenue: number
  avg_order_value: number
}

export interface OrderTimelineResponse {
  start_date: string
  end_date: string
  total_orders: number
  timeline: OrderTimeline[]
}

// Subscriptions
export interface SubscriptionKPIs {
  stats:{
    with_billing_success: number
    total: number
    renewed: number
    active: number
    with_auto_service: number
    new_subscriptions: number
    cancellations: number
    net_growth: number
    churn_rate: number
    avg_lifetime_months: number
  }
  active_subscriptions: number
  renewal_rate : number
  error_rate: number
  auto_service_rate: number

}

export interface SubscriptionTimelinePoint {
  date: string
  renewals: number
  cancellations: number
  new_subscriptions: number 
}

export interface SubscriptionTimelineResponse {
  start_date: string
  end_date: string
  total_subscriptions: number
  timeline: SubscriptionTimelinePoint[]
}

export interface RetentionRates {
  retention_rates: {
    annual: number
    ["90_days"]: number
    ["30_days"]: number
  }
}
// Notifications
export interface NotificationKPIs {
  totalSent: number
  deliveryRate: number
  failureRate: number
  uptime: number
  avgLatency: number
}

export interface NotificationChannel {
  channel: string
  sent: number
  delivered: number
  failed: number
}

export interface NotificationStatus {
  status: string
  count: number
  percentage: number
}

// IoT
export interface IoTKPIs {
  activeSensors: number
  totalAlerts: number
  avgLatency: number
  invalidPackets: number
  uptime: number
}

export interface IoTDevice {
  id: string
  name: string
  status: 'online' | 'offline' | 'warning'
  lastSeen: string
  batteryLevel: number
}

export interface IoTAlert {
  id: string
  deviceId: string
  type: string
  severity: 'critical' | 'warning' | 'info'
  message: string
  timestamp: string
}

// Incidents
export interface IncidentKPIs {
  activeIncidents: number
  resolvedToday: number
  avgResolutionTime: number
  slaCompliance: number
  criticalCount: number
}

export interface IncidentTimeline {
  date: string
  opened: number
  resolved: number
  critical: number
}

export interface Incident {
  id: string
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  status: 'open' | 'investigating' | 'resolved'
  assignee: string
  createdAt: string
  updatedAt: string
}

// Payments
export interface PaymentKPIs {
  totalTransactions: number
  failedPayments: number
  failureRate: number
  revenue: number
  avgTransactionValue: number
  uptime: number
}

export interface PaymentFailure {
  reason: string
  count: number
  percentage: number
}

export interface PaymentTimeline {
  date: string
  successful: number
  failed: number
  amount: number
}

// Logistics
export interface LogisticsKPIs {
  activeRoutes: number
  onTimeDelivery: number
  avgDeliveryTime: number
  pendingDeliveries: number
  driversActive: number
}

export interface Route {
  id: string
  driver: string
  status: 'active' | 'completed' | 'delayed'
  deliveries: number
  completed: number
  eta: string
}

// Service Status
export interface ServiceStatus {
  name: string
  status: 'operational' | 'degraded' | 'outage'
  uptime: number
  lastIncident?: string
}

// Activity
export interface Activity {
  id: string
  type: 'order' | 'payment' | 'incident' | 'notification' | 'iot'
  message: string
  timestamp: string
  status?: 'success' | 'warning' | 'error'
}

// Alert
export interface Alert {
  id: string
  title: string
  message: string
  severity: 'critical' | 'warning' | 'info'
  source: string
  timestamp: string
}
