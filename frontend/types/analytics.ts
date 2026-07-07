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
  total_notifications: number
  delivered_notifications: number
  failed_notifications: number
  fallback_notifications: number
  failure_rate: number       // % notificaciones fallidas
  delivery_rate: number      // % notificaciones entregadas (uptime del servicio)
  backpressure_ratio: number // % notificaciones con fallback activado
  avg_attempts: number
}
 
export interface NotificationChannel {
  canal: string              // "sms" | "email" | "push"
  total: number
  delivered: number
  failed: number
  fallbacks: number
  avg_attempts: number
  delivery_rate: number      // %
  failure_rate: number       // %
}
 
export interface NotificationChannelsResponse {
  total_notifications: number
  channels: NotificationChannel[]
}
 
export interface NotificationStatus {
  estado: string             // "enviado" | "entregado" | "fallido"
  count: number
  percentage: number
}
 
export interface NotificationStatusResponse {
  total_notifications: number
  statuses: NotificationStatus[]
}
 
export interface NotificationTimelinePoint {
  date: string
  total: number
  delivered: number
  failed: number
  fallbacks: number
}
 
export interface NotificationTimelineResponse {
  start_date: string
  end_date: string
  total_notifications: number
  timeline: NotificationTimelinePoint[]
}

// IoT
export interface IoTKPIs {
  total_sensors: number
  online_sensors: number
  offline_sensors: number
  availability_rate: number
  avg_battery_level: number
  low_battery_count: number
  data_validity_rate: number
  anomalies_detected: number
  avg_processing_latency_seconds: number
  avg_processing_latency_ms: number
}

export interface IoTDevice {
  sensor_id: string
  asset_id: string
  sensor_type: string
  is_online: boolean
  battery_level?: number
  last_reading_at?: string
  location?: string
  has_anomaly: boolean
  low_battery_alert: boolean
}

export interface SensorsStatusResponse {
  total_sensors: number
  online_count: number
  offline_count: number
  sensors: IoTDevice[]
}

export interface IoTAlert {
  event_id: string
  sensor_id: string
  event_type: string
  severity: 'critical' | 'warning' | 'info'
  message: string
  timestamp: string
  data?: any
}

export interface EventsResponse {
  total_events: number
  critical_count: number
  warning_count: number
  info_count: number
  events: IoTAlert[]
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

export interface PaymentFailuresResponse {
  rejection_rate: number
  total: number
  failed: number
  reasons: PaymentFailure[]
}

export interface ConciliationStatus {
  status: string
  count: number
  percentage: number
}

export interface PaymentConciliationResponse {
  statuses: ConciliationStatus[]
  total: number
  approval_rate: number
}

export interface PaymentTimeline {
  date: string
  successful: number
  failed: number
  amount: number
}

export interface PaymentMethodPoint {
  name: string
  value: number
  count: number
}

export interface PaymentMethodsResponse {
  methods: PaymentMethodPoint[]
  total: number
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

// ─── Inventory ────────────────────────────────────────────────────────────────

export type LocationType = 'WAREHOUSE' | 'DISTRIBUTION_CENTER' | 'RETAIL_POINT'
export type StockStatus  = 'NORMAL' | 'CRITICAL' | 'OUT_OF_STOCK'

export interface InventoryKPIs {
  total_skus:        number
  total_stock_value: number
  warehouses_count:  number
  low_stock_count:   number
  out_of_stock_count:number
  turnover_rate:     number
}

export interface WarehouseCapacity {
  location_id:   string
  location_code: string
  location_name: string
  location_type: LocationType
  city:          string | null
  stock:         number
  // reserved/available provienen del snapshot real (agregado por ubicación).
  // capacity/utilization solo existen en los datos mock (no hay fuente de
  // capacidad instalada en el módulo de inventario todavía) → opcionales.
  reserved?:     number
  available?:    number
  capacity?:     number
  utilization?:  number
}

export interface LowStockItem {
  sku_id:                string
  product_name:          string
  category:              string
  unit:                  string
  critical_threshold:    number
  total_available_stock: number
  total_physical_stock:  number
  total_reserved_stock:  number
  locations_count:       number
  is_out_of_stock:       boolean
  last_updated:          string
}

export interface StockStatusSummary {
  status:     StockStatus
  count:      number
  percentage: number
}

export interface LocationRow {
  location_id:   string
  location_code: string
  location_name: string
  location_type: LocationType
  address:       string | null
  city:          string | null
  country:       string
  is_active:     boolean
  created_at:    string
}

export interface LocationsCatalogResponse {
  data:         LocationRow[]
  total:        number
  generated_at: string
}

export interface ProductThresholdRow {
  sku_id:                string
  product_name:          string
  category:              string
  unit:                  string
  critical_threshold:    number
  total_physical_stock:  number
  total_reserved_stock:  number
  total_available_stock: number
  locations_count:       number
  is_below_threshold:    boolean
  is_out_of_stock:       boolean
  last_updated:          string
}

export interface ProductsThresholdsResponse {
  data:                  ProductThresholdRow[]
  total:                 number
  total_below_threshold: number
  total_out_of_stock:    number
  generated_at:          string
}

// ─── CRM ─────────────────────────────────────────────────────────────────────

export interface CRMKPIs {
  totalCustomers: number
  openTickets: number
  avgResponseTimeMinutes: number
  csatScore: number
  messagesToday: number
  resolutionRate: number
}

export interface CRMTimelinePoint {
  date: string
  opened: number
  resolved: number
}

export interface CRMTimeline {
  days: number
  points: CRMTimelinePoint[]
}

export interface CRMTicketRow {
  ticketId: string
  asunto: string
  estado: string
  prioridad: string
  canal: string
  sourceProject: string
  openedAt: string
  updatedAt: string
}

export interface CRMTicketsResponse {
  tickets: CRMTicketRow[]
}

export interface CRMSLASummary {
  totalViolations: number
  criticalViolations: number
  slaComplianceRate: number
}

// ─── Pagos — Dashboard & Auditoría ───────────────────────────────────────────

export interface KpiResumen {
  volumenTransDiario: number
  crecimientoVolumen: number
  tasaRechazo: number
  uptimeSLA: number
}

export interface TransaccionDiaria {
  hora: string
  exitosas: number
  rechazadas: number
}

export interface VolumenPorMetodo {
  metodo: string
  volumenTrans: number
}

export interface DashboardMetricas {
  kpiResumen: KpiResumen
  transaccionesDiarias: TransaccionDiaria[]
  volumenPorMetodo: VolumenPorMetodo[]
}

export interface ReporteHistorico {
  id: string
  fecha: string
  tipo: string
  estado: 'completo' | 'en_proceso' | 'fallido'
}

export interface DetalleReporteHisto {
  id_reporte: string
  fecha: string
  kpiResumen: KpiResumen
  volumenPorMetodo: VolumenPorMetodo[]
}
