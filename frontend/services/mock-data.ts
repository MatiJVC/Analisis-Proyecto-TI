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
  IncidentKPIs,
  IncidentTimeline,
  Incident,
  PaymentKPIs,
  PaymentTimeline,
  LogisticsKPIs,
  Route,
  ServiceStatus,
  Activity,
  Alert,
  RetentionRates,
  SubscriptionTimelineResponse,
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
};
// Notifications Mock Data
export const notificationKPIs: NotificationKPIs = {
  totalSent: 892450,
  deliveryRate: 98.7,
  failureRate: 1.3,
  uptime: 99.95,
  avgLatency: 145,
};

export const notificationChannels: NotificationChannel[] = [
  { channel: "Email", sent: 425000, delivered: 419750, failed: 5250 },
  { channel: "SMS", sent: 287000, delivered: 283290, failed: 3710 },
  { channel: "Push", sent: 156000, delivered: 154440, failed: 1560 },
  { channel: "WhatsApp", sent: 24450, delivered: 24206, failed: 244 },
];

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

// Incidents Mock Data
export const incidentKPIs: IncidentKPIs = {
  activeIncidents: 12,
  resolvedToday: 8,
  avgResolutionTime: 2.4,
  slaCompliance: 94.5,
  criticalCount: 2,
};

export const incidentTimeline: IncidentTimeline[] = Array.from(
  { length: 14 },
  (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (13 - i));
    return {
      date: date.toISOString().split("T")[0],
      opened: Math.floor(5 + Math.random() * 10),
      resolved: Math.floor(4 + Math.random() * 12),
      critical: Math.floor(Math.random() * 3),
    };
  },
);

export const incidents: Incident[] = [
  {
    id: "INC-001",
    title: "Payment Gateway Timeout",
    severity: "critical",
    status: "investigating",
    assignee: "John D.",
    createdAt: "2 hours ago",
    updatedAt: "30 min ago",
  },
  {
    id: "INC-002",
    title: "High API Latency",
    severity: "high",
    status: "open",
    assignee: "Sarah M.",
    createdAt: "4 hours ago",
    updatedAt: "1 hour ago",
  },
  {
    id: "INC-003",
    title: "Email Delivery Delays",
    severity: "medium",
    status: "investigating",
    assignee: "Mike R.",
    createdAt: "6 hours ago",
    updatedAt: "2 hours ago",
  },
  {
    id: "INC-004",
    title: "Database Connection Pool",
    severity: "critical",
    status: "open",
    assignee: "Lisa K.",
    createdAt: "1 hour ago",
    updatedAt: "45 min ago",
  },
  {
    id: "INC-005",
    title: "CDN Cache Miss Rate",
    severity: "low",
    status: "resolved",
    assignee: "Tom H.",
    createdAt: "8 hours ago",
    updatedAt: "3 hours ago",
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

export const paymentTimeline: PaymentTimeline[] = Array.from(
  { length: 24 },
  (_, i) => {
    const date = new Date();
    date.setHours(date.getHours() - (23 - i));
    const successful = Math.floor(1500 + Math.random() * 500);
    return {
      date: `${date.getHours()}:00`,
      successful,
      failed: Math.floor(successful * (0.005 + Math.random() * 0.01)),
      amount: successful * (60 + Math.random() * 30),
    };
  },
);

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

// Global KPIs for Overview
export const globalKPIs = {
  totalOrders: ordersKPIs.totalOrders,
  deliveryRate: ordersKPIs.deliveryRate,
  revenue: paymentKPIs.revenue,
  notificationSuccessRate: notificationKPIs.deliveryRate,
  activeSubscriptions: subscriptionKPIs.activeSubscriptions,
  iotAlerts: iotKPIs.totalAlerts,
  incidentCount: incidentKPIs.activeIncidents,
  paymentFailureRate: paymentKPIs.failureRate,
};
