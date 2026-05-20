'use client'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string | number
  icon?: React.ReactNode
  format?: 'number' | 'currency' | 'percentage' | 'hours' | 'months'
  className?: string
}

export function KPICard({
  title,
  value,
  icon,
  format = 'number',
  className,
}: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'string') return val
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('es-CL', {
          style: 'currency',
          currency: 'CLP',
          notation: val >= 1000000 ? 'compact' : 'standard',
          maximumFractionDigits: val >= 1000000 ? 2 : 0,
        }).format(val)
      case 'percentage':
        return `${val.toFixed(0)}%`
      case 'hours':
        return `${val.toFixed(2)} h`
      case 'months':
        return `${val.toFixed(0)} meses`
      default:
        return new Intl.NumberFormat('en-US', {
          notation: val >= 10000 ? 'compact' : 'standard',
          maximumFractionDigits: 1,
        }).format(val)
    }
  }

  return (
    <Card className={cn('bg-card border-border', className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground min-h-10 h-20 mb-3">
              {title}
            </p>
            <p className="text-3xl font-bold tracking-tight text-foreground  ">
              {formatValue(value)}
            </p>
          </div>
          {icon && (
            <div className="rounded-lg bg-primary/10 p-3 text-primary ml-3">
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function KPICardSkeleton() {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-6">
        <div className="space-y-2">
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
          <div className="h-8 w-32 animate-pulse rounded bg-muted" />
          <div className="h-4 w-28 animate-pulse rounded bg-muted" />
        </div>
      </CardContent>
    </Card>
  )
}
