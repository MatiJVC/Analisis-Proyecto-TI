import type {
  OrdersKPIs,
  OrderChannel,
  OrderStatus,
  OrderTimeline,
  SubscriptionKPIs,
  SubscriptionTimeline,
  NotificationKPIs,
  NotificationChannel,
  IoTKPIs,
  IoTDevice,
  IoTAlert,
  PaymentKPIs,
  LogisticsKPIs,
  Route,
  ServiceStatus,
  Activity,
  Alert,
  RetentionRates,
  SubscriptionTimelineResponse,
  NotificationTimelinePoint,
  NotificationStatusResponse,
  NotificationTimelineResponse,
  InventoryKPIs,
  WarehouseCapacity,
  LowStockItem,
  StockStatusSummary,
  LocationsCatalogResponse,
  ProductsThresholdsResponse,
  CRMKPIs,
  CRMTimeline,
  CRMTicketsResponse,
  CRMSLASummary,
  CRMExternalTicketResponse,
  CRMDistributionResponse,
} from "@/types/analytics";

// Orders Mock Data
export const ordersKPIs: OrdersKPIs = {
  totalOrders: 15847,
  deliveryRate: 94.2,
  revenue: 1284500,
  avgOrderValue: 81.05,
  slaCompliance: 97.8,
  pendingOrders: 234,
};

export const orderChannels: OrderChannel[] = [
  { name: "Web", value: 6420, percentage: 40.5 },
  { name: "Mobile App", value: 5280, percentage: 33.3 },
  { name: "API", value: 2847, percentage: 18.0 },
  { name: "POS", value: 1300, percentage: 8.2 },
];

export const orderStatuses: OrderStatus[] = [
  { status: "Delivered", count: 14930, color: "var(--chart-1)" },
  { status: "In Transit", count: 512, color: "var(--chart-2)" },
  { status: "Processing", count: 234, color: "var(--chart-3)" },
  { status: "Failed", count: 171, color: "var(--chart-5)" },
];

export const orderTimeline: OrderTimeline[] = Array.from(
  { length: 30 },
  (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    const orders = Math.floor(400 + Math.random() * 200);
    return {
      date: date.toISOString().split("T")[0],
      orders,
      delivered: Math.floor(orders * (0.92 + Math.random() * 0.06)),
      failed: Math.floor(orders * (0.01 + Math.random() * 0.02)),
    };
  },
);

// Subscriptions Mock Data
export const subscriptionKPIs: SubscriptionKPIs = {
  activeSubscriptions: 8452,
  renewalRate: 87.3,
  churn: 2.8,
  monthlyRevenue: 423600,
  autoserviceRate: 76.5,
  newSubscriptions: 342,
};

export const subscriptionTimeline: SubscriptionTimelineResponse = {
  start_date: new Date(new Date().setMonth(new Date().getMonth() - 11))
    .toISOString()
    .slice(0, 7),
  end_date: new Date().toISOString().slice(0, 7),
  total_subscriptions: Math.floor(8000 + Math.random() * 500),
  timeline: Array.from({ length: 12 }, (_, i) => {
    const date = new Date();
    date.setMonth(date.getMonth() - (11 - i));
    return {
      date: date.toISOString().slice(0, 7),
      renewals: Math.floor(600 + Math.random() * 200),
      cancellations: Math.floor(50 + Math.random() * 50),
      new_subscriptions: Math.floor(200 + Math.random() * 150),
    };
  }),
};

export const retentionRates: RetentionRates = {
  retention_rates: {
    ["90_days"]: 78.5,
    ["30_days"]: 85.2,
    annual: 65.4,
  },
  multi_subscription_rate: 12.4,
};

// Notifications Mock Data


// Notifications Mock Data
export const notificationKPIs: NotificationKPIs = {
  total_notifications: 892450,
  delivered_notifications: 881050,
  failed_notifications: 11600,
  fallback_notifications: 24500,
  delivery_rate: 98.7,
  failure_rate: 1.3,
  backpressure_ratio: 2.7,
  avg_attempts: 1.3,
}

export const notificationChannels: NotificationChannel[] = [
  { canal: 'email', total: 425000, delivered: 419750, failed: 5250,  fallbacks: 8500,  avg_attempts: 1.2, delivery_rate: 98.8, failure_rate: 1.2 },
  { canal: 'sms',   total: 287000, delivered: 283290, failed: 3710,  fallbacks: 12000, avg_attempts: 1.4, delivery_rate: 98.7, failure_rate: 1.3 },
  { canal: 'push',  total: 180450, delivered: 178010, failed: 2440,  fallbacks: 4000,  avg_attempts: 1.1, delivery_rate: 98.6, failure_rate: 1.4 },
]

export const notificationStatus: NotificationStatusResponse = {
  total_notifications: 892450,
  statuses: [
    { estado: 'entregado', count: 881050, percentage: 98.7 },
    { estado: 'enviado',   count:   7420, percentage:  0.8 },
    { estado: 'fallido',   count:   3980, percentage:  0.5 },
  ],
}

export const notificationTimeline: NotificationTimelineResponse = {
  start_date: '2026-05-03',
  end_date:   '2026-06-02',
  total_notifications: 892450,
  timeline: [
    { date: '2026-05-03', total: 28500, delivered: 28150, failed: 350, fallbacks: 620 },
    { date: '2026-05-04', total: 31200, delivered: 30820, failed: 380, fallbacks: 710 },
    { date: '2026-05-05', total: 29800, delivered: 29430, failed: 370, fallbacks: 680 },
    { date: '2026-05-06', total: 33400, delivered: 33010, failed: 390, fallbacks: 750 },
    { date: '2026-05-07', total: 30100, delivered: 29740, failed: 360, fallbacks: 690 },
    { date: '2026-05-08', total: 27600, delivered: 27260, failed: 340, fallbacks: 600 },
    { date: '2026-05-09', total: 25900, delivered: 25570, failed: 330, fallbacks: 560 },
    { date: '2026-05-10', total: 32100, delivered: 31710, failed: 390, fallbacks: 730 },
    { date: '2026-05-11', total: 34500, delivered: 34080, failed: 420, fallbacks: 790 },
    { date: '2026-05-12', total: 31800, delivered: 31410, failed: 390, fallbacks: 720 },
    { date: '2026-05-13', total: 29200, delivered: 28840, failed: 360, fallbacks: 650 },
    { date: '2026-05-14', total: 30700, delivered: 30320, failed: 380, fallbacks: 700 },
    { date: '2026-05-15', total: 28400, delivered: 28050, failed: 350, fallbacks: 630 },
    { date: '2026-05-16', total: 26800, delivered: 26470, failed: 330, fallbacks: 590 },
    { date: '2026-05-17', total: 33600, delivered: 33190, failed: 410, fallbacks: 760 },
    { date: '2026-05-18', total: 35200, delivered: 34760, failed: 440, fallbacks: 810 },
    { date: '2026-05-19', total: 32400, delivered: 32000, failed: 400, fallbacks: 730 },
    { date: '2026-05-20', total: 30900, delivered: 30520, failed: 380, fallbacks: 700 },
    { date: '2026-05-21', total: 29300, delivered: 28940, failed: 360, fallbacks: 660 },
    { date: '2026-05-22', total: 27700, delivered: 27370, failed: 330, fallbacks: 610 },
    { date: '2026-05-23', total: 26100, delivered: 25780, failed: 320, fallbacks: 570 },
    { date: '2026-05-24', total: 34800, delivered: 34370, failed: 430, fallbacks: 790 },
    { date: '2026-05-25', total: 36100, delivered: 35640, failed: 460, fallbacks: 830 },
    { date: '2026-05-26', total: 33500, delivered: 33080, failed: 420, fallbacks: 760 },
    { date: '2026-05-27', total: 31200, delivered: 30820, failed: 380, fallbacks: 710 },
    { date: '2026-05-28', total: 29600, delivered: 29230, failed: 370, fallbacks: 670 },
    { date: '2026-05-29', total: 28000, delivered: 27660, failed: 340, fallbacks: 620 },
    { date: '2026-05-30', total: 26500, delivered: 26170, failed: 330, fallbacks: 580 },
    { date: '2026-05-31', total: 35400, delivered: 34960, failed: 440, fallbacks: 800 },
    { date: '2026-06-01', total: 37200, delivered: 36720, failed: 480, fallbacks: 860 },
  ],
}


// IoT Mock Data
export const iotKPIs: IoTKPIs = {
  activeSensors: 1247,
  totalAlerts: 89,
  avgLatency: 23,
  invalidPackets: 0.02,
  uptime: 99.8,
};

export const iotDevices: IoTDevice[] = [
  {
    id: "IOT-001",
    name: "Temperature Sensor A1",
    status: "online",
    lastSeen: "2 min ago",
    batteryLevel: 87,
  },
  {
    id: "IOT-002",
    name: "Humidity Sensor B2",
    status: "online",
    lastSeen: "1 min ago",
    batteryLevel: 92,
  },
  {
    id: "IOT-003",
    name: "Motion Detector C3",
    status: "warning",
    lastSeen: "15 min ago",
    batteryLevel: 23,
  },
  {
    id: "IOT-004",
    name: "Pressure Sensor D4",
    status: "online",
    lastSeen: "3 min ago",
    batteryLevel: 78,
  },
  {
    id: "IOT-005",
    name: "GPS Tracker E5",
    status: "offline",
    lastSeen: "2 hours ago",
    batteryLevel: 0,
  },
];

export const iotAlerts: IoTAlert[] = [
  {
    id: "ALT-001",
    deviceId: "IOT-003",
    type: "Low Battery",
    severity: "warning",
    message: "Battery below 25%",
    timestamp: "10 min ago",
  },
  {
    id: "ALT-002",
    deviceId: "IOT-005",
    type: "Device Offline",
    severity: "critical",
    message: "Device not responding",
    timestamp: "2 hours ago",
  },
  {
    id: "ALT-003",
    deviceId: "IOT-001",
    type: "Temperature Alert",
    severity: "warning",
    message: "Temperature exceeds threshold",
    timestamp: "30 min ago",
  },
];

// Payments Mock Data
export const paymentKPIs: PaymentKPIs = {
  totalTransactions: 45892,
  failedPayments: 412,
  failureRate: 0.9,
  revenue: 3245800,
  avgTransactionValue: 70.72,
  uptime: 99.99,
};

// Logistics Mock Data
export const logisticsKPIs: LogisticsKPIs = {
  activeRoutes: 128,
  onTimeDelivery: 91.2,
  avgDeliveryTime: 42,
  pendingDeliveries: 567,
  driversActive: 89,
};

export const routes: Route[] = [
  {
    id: "RT-001",
    driver: "Carlos M.",
    status: "active",
    deliveries: 12,
    completed: 8,
    eta: "14:30",
  },
  {
    id: "RT-002",
    driver: "Ana P.",
    status: "active",
    deliveries: 15,
    completed: 12,
    eta: "15:45",
  },
  {
    id: "RT-003",
    driver: "Luis G.",
    status: "delayed",
    deliveries: 10,
    completed: 4,
    eta: "16:20",
  },
  {
    id: "RT-004",
    driver: "Maria S.",
    status: "completed",
    deliveries: 8,
    completed: 8,
    eta: "Done",
  },
  {
    id: "RT-005",
    driver: "Pedro R.",
    status: "active",
    deliveries: 14,
    completed: 7,
    eta: "15:00",
  },
];

// Service Status
export const serviceStatuses: ServiceStatus[] = [
  { name: "Orders Service", status: "operational", uptime: 99.98 },
  {
    name: "Payments Gateway",
    status: "degraded",
    uptime: 99.85,
    lastIncident: "2 hours ago",
  },
  { name: "Notifications", status: "operational", uptime: 99.95 },
  { name: "IoT Platform", status: "operational", uptime: 99.9 },
  { name: "CRM Service", status: "operational", uptime: 99.99 },
  { name: "Logistics Engine", status: "operational", uptime: 99.92 },
  { name: "Auth Service", status: "operational", uptime: 99.99 },
  { name: "Analytics Pipeline", status: "operational", uptime: 99.87 },
];

// Recent Activity
export const recentActivities: Activity[] = [
  {
    id: "ACT-001",
    type: "order",
    message: "New bulk order received from Enterprise Client",
    timestamp: "2 min ago",
    status: "success",
  },
  {
    id: "ACT-002",
    type: "payment",
    message: "Payment reconciliation completed for batch #4521",
    timestamp: "5 min ago",
    status: "success",
  },
  {
    id: "ACT-003",
    type: "incident",
    message: "High latency detected in payment gateway",
    timestamp: "15 min ago",
    status: "warning",
  },
  {
    id: "ACT-004",
    type: "notification",
    message: "SMS campaign sent to 15,000 subscribers",
    timestamp: "22 min ago",
    status: "success",
  },
  {
    id: "ACT-005",
    type: "iot",
    message: "Sensor IOT-003 battery critically low",
    timestamp: "30 min ago",
    status: "warning",
  },
  {
    id: "ACT-006",
    type: "order",
    message: "500 orders processed in last hour",
    timestamp: "45 min ago",
    status: "success",
  },
  {
    id: "ACT-007",
    type: "incident",
    message: "Database connection pool exhausted",
    timestamp: "1 hour ago",
    status: "error",
  },
];

// Critical Alerts
export const criticalAlerts: Alert[] = [
  {
    id: "CRT-001",
    title: "Payment Gateway Issues",
    message: "Increased failure rate detected",
    severity: "critical",
    source: "Payments",
    timestamp: "15 min ago",
  },
  {
    id: "CRT-002",
    title: "Database Connection Pool",
    message: "Pool utilization at 95%",
    severity: "critical",
    source: "Infrastructure",
    timestamp: "1 hour ago",
  },
  {
    id: "CRT-003",
    title: "IoT Device Offline",
    message: "GPS Tracker E5 not responding",
    severity: "warning",
    source: "IoT",
    timestamp: "2 hours ago",
  },
];

// ─── Inventory Mock Data ──────────────────────────────────────────────────────

export const inventoryKPIs: InventoryKPIs = {
  total_skus:         28456,
  total_stock_value:  4250000,
  warehouses_count:   4,
  low_stock_count:    24,
  out_of_stock_count: 3,
  turnover_rate:      4.2,
}

export const warehouseCapacity: WarehouseCapacity[] = [
  {
    location_id:   '00000000-0000-0000-0000-000000000001',
    location_code: 'BODEGA-SCL-01',
    location_name: 'Bodega Central Santiago',
    location_type: 'WAREHOUSE',
    city:          'Santiago',
    stock:         8540,
    capacity:      10000,
    utilization:   85.4,
  },
  {
    location_id:   '00000000-0000-0000-0000-000000000002',
    location_code: 'BODEGA-VLP-01',
    location_name: 'Bodega Valparaíso',
    location_type: 'WAREHOUSE',
    city:          'Valparaíso',
    stock:         6230,
    capacity:      8000,
    utilization:   77.9,
  },
  {
    location_id:   '00000000-0000-0000-0000-000000000004',
    location_code: 'DC-NORTE-01',
    location_name: 'CD Norte Antofagasta',
    location_type: 'DISTRIBUTION_CENTER',
    city:          'Antofagasta',
    stock:         4120,
    capacity:      6000,
    utilization:   68.7,
  },
  {
    location_id:   '00000000-0000-0000-0000-000000000005',
    location_code: 'DC-SUR-01',
    location_name: 'CD Sur Concepción',
    location_type: 'DISTRIBUTION_CENTER',
    city:          'Concepción',
    stock:         9200,
    capacity:      12000,
    utilization:   76.7,
  },
]

export const lowStockItems: LowStockItem[] = [
  {
    sku_id:                'SKU-MECH-001',
    product_name:          'Widget Pro',
    category:              'Partes mecánicas',
    unit:                  'unidad',
    critical_threshold:    50,
    total_available_stock: 12,
    total_physical_stock:  15,
    total_reserved_stock:  3,
    locations_count:       2,
    is_out_of_stock:       false,
    last_updated:          '2026-05-28T08:30:00Z',
  },
  {
    sku_id:                'SKU-ELEC-042',
    product_name:          'Connector A',
    category:              'Componentes electrónicos',
    unit:                  'unidad',
    critical_threshold:    30,
    total_available_stock: 8,
    total_physical_stock:  8,
    total_reserved_stock:  0,
    locations_count:       1,
    is_out_of_stock:       false,
    last_updated:          '2026-05-28T07:15:00Z',
  },
  {
    sku_id:                'SKU-ELEC-089',
    product_name:          'Sensor Module T200',
    category:              'Componentes electrónicos',
    unit:                  'unidad',
    critical_threshold:    25,
    total_available_stock: 0,
    total_physical_stock:  0,
    total_reserved_stock:  0,
    locations_count:       1,
    is_out_of_stock:       true,
    last_updated:          '2026-05-28T06:00:00Z',
  },
  {
    sku_id:                'SKU-TOOL-156',
    product_name:          'Power Unit B12',
    category:              'Herramientas',
    unit:                  'unidad',
    critical_threshold:    40,
    total_available_stock: 15,
    total_physical_stock:  20,
    total_reserved_stock:  5,
    locations_count:       2,
    is_out_of_stock:       false,
    last_updated:          '2026-05-27T23:45:00Z',
  },
  {
    sku_id:                'SKU-CHEM-003',
    product_name:          'Lubricante Industrial LX',
    category:              'Insumos químicos',
    unit:                  'litro',
    critical_threshold:    20,
    total_available_stock: 0,
    total_physical_stock:  0,
    total_reserved_stock:  0,
    locations_count:       1,
    is_out_of_stock:       true,
    last_updated:          '2026-05-28T05:30:00Z',
  },
]

export const stockStatusSummary: StockStatusSummary[] = [
  { status: 'NORMAL',       count: 28429, percentage: 99.9 },
  { status: 'CRITICAL',     count: 24,    percentage: 0.08 },
  { status: 'OUT_OF_STOCK', count: 3,     percentage: 0.01 },
]

export const locationsCatalog: LocationsCatalogResponse = {
  data: [
    {
      location_id:   '00000000-0000-0000-0000-000000000001',
      location_code: 'BODEGA-SCL-01',
      location_name: 'Bodega Central Santiago',
      location_type: 'WAREHOUSE',
      address:       'Av. Industrial 4500, Quilicura',
      city:          'Santiago',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-01-15T08:00:00Z',
    },
    {
      location_id:   '00000000-0000-0000-0000-000000000002',
      location_code: 'BODEGA-VLP-01',
      location_name: 'Bodega Valparaíso',
      location_type: 'WAREHOUSE',
      address:       'Ruta 68 Km 90',
      city:          'Valparaíso',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-02-01T09:00:00Z',
    },
    {
      location_id:   '00000000-0000-0000-0000-000000000003',
      location_code: 'BODEGA-SCL-02',
      location_name: 'Bodega Sur Santiago',
      location_type: 'WAREHOUSE',
      address:       'Camino a Melipilla 1200',
      city:          'Santiago',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-03-01T10:00:00Z',
    },
    {
      location_id:   '00000000-0000-0000-0000-000000000004',
      location_code: 'DC-NORTE-01',
      location_name: 'CD Norte Antofagasta',
      location_type: 'DISTRIBUTION_CENTER',
      address:       'Ruta 1 Norte Km 12',
      city:          'Antofagasta',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-03-10T10:00:00Z',
    },
    {
      location_id:   '00000000-0000-0000-0000-000000000005',
      location_code: 'DC-SUR-01',
      location_name: 'CD Sur Concepción',
      location_type: 'DISTRIBUTION_CENTER',
      address:       'Av. Industrial Sur 800',
      city:          'Concepción',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-04-01T08:30:00Z',
    },
    {
      location_id:   '00000000-0000-0000-0000-000000000008',
      location_code: 'RETAIL-RM-01',
      location_name: 'Tienda Providencia',
      location_type: 'RETAIL_POINT',
      address:       'Av. Providencia 1234, Local 5',
      city:          'Santiago',
      country:       'Chile',
      is_active:     true,
      created_at:    '2025-06-01T09:30:00Z',
    },
  ],
  total:        6,
  generated_at: new Date().toISOString(),
}

export const productsThresholds: ProductsThresholdsResponse = {
  data: [
    ...lowStockItems,
    {
      sku_id:                'SKU-PACK-201',
      product_name:          'Caja Corrugada 30x30',
      category:              'Embalaje',
      unit:                  'unidad',
      critical_threshold:    200,
      total_available_stock: 1450,
      total_physical_stock:  1500,
      total_reserved_stock:  50,
      locations_count:       3,
      is_below_threshold:    false,
      is_out_of_stock:       false,
      last_updated:          '2026-05-28T09:00:00Z',
    },
  ].map((item) => ({ ...item, is_below_threshold: (item as LowStockItem).total_available_stock <= (item as LowStockItem).critical_threshold })),
  total:                 6,
  total_below_threshold: 5,
  total_out_of_stock:    2,
  generated_at:          new Date().toISOString(),
}

// ─── CRM Mock Data ───────────────────────────────────────────────────────────

export const crmKPIs: CRMKPIs = {
  totalCustomers:         24856,
  openTickets:            142,
  avgResponseTimeMinutes: 18,
  criticalTickets:        23,
  ticketsCreatedToday:    31,
  resolutionRate:         94.5,
}

export const crmTimeline: CRMTimeline = {
  days: 14,
  points: Array.from({ length: 14 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (13 - i))
    return {
      date:     d.toISOString().split('T')[0],
      opened:   Math.floor(80 + Math.random() * 40),
      resolved: Math.floor(75 + Math.random() * 45),
    }
  }),
}

export const crmTickets: CRMTicketsResponse = {
  tickets: [
    { ticketId: 'TKT-4521', asunto: 'Problema con pago de suscripción', estado: 'Abierto',  prioridad: 'Alta',    canal: 'Email',    sourceProject: 'pagos',      openedAt: new Date(Date.now() - 10 * 60000).toISOString(),  updatedAt: new Date(Date.now() - 10 * 60000).toISOString() },
    { ticketId: 'TKT-4520', asunto: 'No puede acceder a su cuenta',     estado: 'Progreso', prioridad: 'Media',   canal: 'Chat',     sourceProject: 'auth',       openedAt: new Date(Date.now() - 25 * 60000).toISOString(),  updatedAt: new Date(Date.now() - 20 * 60000).toISOString() },
    { ticketId: 'TKT-4519', asunto: 'Solicitud: exportar a CSV',        estado: 'Abierto',  prioridad: 'Baja',    canal: 'App',      sourceProject: 'analytics',  openedAt: new Date(Date.now() - 60 * 60000).toISOString(),  updatedAt: new Date(Date.now() - 60 * 60000).toISOString() },
    { ticketId: 'TKT-4518', asunto: 'Integración no funciona',          estado: 'Cerrado',  prioridad: 'Alta',    canal: 'Email',    sourceProject: 'inventario', openedAt: new Date(Date.now() - 120 * 60000).toISOString(), updatedAt: new Date(Date.now() - 30 * 60000).toISOString() },
    { ticketId: 'TKT-4517', asunto: 'Error al generar reporte mensual', estado: 'Progreso', prioridad: 'Crítica', canal: 'Teléfono', sourceProject: 'orders',     openedAt: new Date(Date.now() - 180 * 60000).toISOString(), updatedAt: new Date(Date.now() - 45 * 60000).toISOString() },
  ],
}

export const crmSLA: CRMSLASummary = {
  totalViolations:    8,
  criticalViolations: 2,
  slaComplianceRate:  94.5,
}

export const crmChannels: CRMDistributionResponse = {
  total: 142,
  items: [
    { name: 'Chat', count: 58, percentage: 40.8 },
    { name: 'Email', count: 42, percentage: 29.6 },
    { name: 'Teléfono', count: 30, percentage: 21.1 },
    { name: 'App', count: 12, percentage: 8.5 },
  ],
}

export const crmPriority: CRMDistributionResponse = {
  total: 142,
  items: [
    { name: 'Baja', count: 40, percentage: 28.2 },
    { name: 'Media', count: 55, percentage: 38.7 },
    { name: 'Alta', count: 35, percentage: 24.6 },
    { name: 'Crítica', count: 12, percentage: 8.5 },
  ],
}

export const crmSourceProjects: CRMDistributionResponse = {
  total: 142,
  items: [
    { name: 'orders', count: 48, percentage: 33.8 },
    { name: 'pagos', count: 34, percentage: 23.9 },
    { name: 'subscriptions', count: 26, percentage: 18.3 },
    { name: 'salud', count: 20, percentage: 14.1 },
    { name: 'inventario', count: 14, percentage: 9.9 },
  ],
}

export const crmCriticalByModule: CRMDistributionResponse = {
  total: 23,
  items: [
    { name: 'Pagos', count: 8, percentage: 34.8 },
    { name: 'Pedidos', count: 6, percentage: 26.1 },
    { name: 'CRM', count: 4, percentage: 17.4 },
    { name: 'Salud', count: 3, percentage: 13.0 },
    { name: 'IoT', count: 2, percentage: 8.7 },
  ],
}

export const crmTicketLive: CRMExternalTicketResponse = {
  ticket_id: 'TKT-4521',
  estado: 'Progreso',
  prioridad: 'Alta',
  canal: 'Email',
  asunto: 'Problema con pago de suscripción',
  cliente_id: 8823,
  cliente_nombre: 'María Fernández',
  pago_id_ref: 'PAY-2026-00981',
  salud_ref: undefined,
  resolucion: undefined,
  suscripcion_id_ref: 'SUB-2026-00312',
}

// Global KPIs for Overview
export const globalKPIs = {
  totalOrders: ordersKPIs.totalOrders,
  deliveryRate: ordersKPIs.deliveryRate,
  revenue: paymentKPIs.revenue,
  notificationSuccessRate: notificationKPIs.deliveryRate,
  activeSubscriptions: subscriptionKPIs.activeSubscriptions,
  iotAlerts: iotKPIs.totalAlerts,
  incidentCount: 0,
  paymentFailureRate: paymentKPIs.failureRate,
};
