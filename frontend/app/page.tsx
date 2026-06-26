'use client'

import { useAuth } from '@/components/auth/auth-provider'
import { canAccess, type Domain } from '@/lib/roles'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import {
  Bell,
  Cpu,
  ShoppingCart,
  RefreshCw,
  Activity as ActivityLucide,
  ChevronRight,
  Heart,
  AlertTriangle,
  CreditCard,
  Truck,
  Box,
  User,
} from 'lucide-react'
import Link from 'next/link'

const DOMAINS = [
  {
    key: 'orders',
    label: 'Pedidos',
    description: 'Seguimiento omnicanal de órdenes y métricas de entrega',
    href: '/orders',
    icon: ShoppingCart,
    accent: 'var(--chart-2)',
  },
  {
    key: 'subscriptions',
    label: 'Suscripciones',
    description: 'Renovaciones, retención y ciclo de vida de contratos',
    href: '/subscriptions',
    icon: RefreshCw,
    accent: 'var(--chart-2)',
  },
  {
    key: 'notifications',
    label: 'Notificaciones',
    description: 'Entrega multicanal, fallbacks y uptime del servicio',
    href: '/notifications',
    icon: Bell,
    accent: 'var(--chart-2)',
  },
  {
    key: 'iot',
    label: 'IoT',
    description: 'Estado de sensores, telemetría y detección de anomalías',
    href: '/iot',
    icon: Cpu,
    accent: 'var(--chart-2)',
  },
  {
    key: 'health',
    label: 'Salud',
    description: 'Indicadores de bienestar, historial y alertas médicas',
    href: '/health',
    icon: Heart,
    accent: 'var(--chart-2)',
  },
  {
    key: 'incidents',
    label: 'Incidentes',
    description: 'Gestión de alertas, resolución y trazabilidad de fallas',
    href: '/incidents',
    icon: AlertTriangle,
    accent: 'var(--chart-2)',
  },
  {
    key: 'pagos',
    label: 'Pagos',
    description: 'Procesamiento seguro, conciliación y métricas financieras',
    href: '/pagos',
    icon: CreditCard,
    accent: 'var(--chart-2)',
  },
  {
    key: 'inventory',
    label: 'Inventario',
    description: 'Stock disponible, rotación de productos y alertas',
    href: '/inventory',
    icon: Box,
    accent: 'var(--chart-2)',
  },
  {
    key: 'crm',
    label: 'CRM',
    description: 'Gestión de clientes, interacciones y métricas de fidelización',
    href: '/crm',
    icon: User,
    accent: 'var(--chart-2)',
  },
]

const CARD_TO_DOMAIN: Record<string, string> = {
  health: 'salud',
  pagos: 'payments',
}

export default function HomePage() {
  const { roles } = useAuth()

  const visibleDomains = DOMAINS.filter((d) => {
    const domainKey = (CARD_TO_DOMAIN[d.key] || d.key) as Domain
    return canAccess(roles, domainKey)
  })

  return (
    <DashboardLayout>
      <div className="space-y-8 pb-8">

        {/* Hero */}
        <div className="relative overflow-hidden rounded-2xl border border-border bg-card px-8 py-10">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                'linear-gradient(var(--foreground) 1px, transparent 1px), linear-gradient(90deg, var(--foreground) 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />
          <div
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full blur-3xl"
            style={{ background: 'var(--chart-1)', opacity: 0.08 }}
          />
          <div className="relative flex flex-col gap-2 max-w-2xl">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
              <ActivityLucide className="h-3.5 w-3.5" />
              Sistema centralizado de análisis
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              Bienvenido al Panel de Control
            </h1>
            <p className="text-muted-foreground leading-relaxed">
              Monitorea en tiempo real el rendimiento de todos los dominios operacionales
            </p>
          </div>
        </div>

        {/* Domain Cards */}
        <div>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
            Dominios
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {visibleDomains.map((d) => {
              const Icon = d.icon
              return (
                <Link
                  key={d.key}
                  href={d.href}
                  className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:border-border/80 hover:shadow-md hover:-translate-y-0.5"
                >
                  <div
                    className="absolute inset-x-0 top-0 h-0.5 opacity-60 transition-opacity group-hover:opacity-100"
                    style={{ background: d.accent }}
                  />
                  <div className="flex items-start justify-between">
                    <div
                      className="flex h-10 w-10 items-center justify-center rounded-lg"
                      style={{ background: `${d.accent}18`, color: d.accent }}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <div className="mt-4">
                    <div className="font-semibold text-foreground">{d.label}</div>
                    <div className="mt-1 text-sm text-muted-foreground leading-snug">
                      {d.description}
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>

      </div>
    </DashboardLayout>
  )
}
