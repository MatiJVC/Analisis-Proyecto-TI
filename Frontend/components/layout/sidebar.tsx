'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  ShoppingCart,
  CreditCard,
  Bell,
  Cpu,
  Truck,
  Package,
  Users,
  AlertTriangle,
  Heart,
  Shield,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Activity,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Pedidos', href: '/orders', icon: ShoppingCart },
  { name: 'Suscripciones', href: '/subscriptions', icon: RefreshCw },
  { name: 'Notificaciones', href: '/notifications', icon: Bell },
  { name: 'IoT', href: '/iot', icon: Cpu },
  { name: 'Pagos', href: '/payments', icon: CreditCard },
  { name: 'Logística', href: '/logistics', icon: Truck },
  { name: 'Inventario', href: '/inventory', icon: Package },
  { name: 'CRM', href: '/crm', icon: Users },
  { name: 'Incidentes', href: '/incidents', icon: AlertTriangle },
  { name: 'Salud', href: '/health', icon: Heart },
  { name: 'Identidad', href: '/security', icon: Shield },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r border-border bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold text-foreground">
              Codex-Analytics
            </span>
          </Link>
        )}
        {collapsed && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary mx-auto">
            <Activity className="h-5 w-5 text-primary-foreground" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                  title={collapsed ? item.name : undefined}
                >
                  <item.icon className={cn('h-5 w-5 shrink-0', isActive && 'text-primary-foreground')} />
                  {!collapsed && <span>{item.name}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Collapse Toggle */}
      <div className="border-t border-border p-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'w-full justify-center text-muted-foreground hover:bg-muted hover:text-foreground',
            collapsed && 'px-0'
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 mr-2" />
              <span>Collapse</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  )
}
