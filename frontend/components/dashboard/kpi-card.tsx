'use client'

import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  format?: 'number' | 'currency' | 'percentage'
  className?: string
}

export function KPICard({
  title,
  value,
  change,
  changeLabel = 'vs last period',
  icon,
  trend,
  format = 'number',
  className,
}: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'string') return val
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          notation: val >= 1000000 ? 'compact' : 'standard',
          maximumFractionDigits: val >= 1000000 ? 2 : 0,
        }).format(val)
      case 'percentage':
        return `${val.toFixed(1)}%`
      default:
        return new Intl.NumberFormat('en-US', {
          notation: val >= 10000 ? 'compact' : 'standard',
          maximumFractionDigits: 1,
        }).format(val)
    }
  }

  const getTrendColor = () => {
    if (!trend) return 'text-muted-foreground'
    if (trend === 'up') return 'text-success'
    if (trend === 'down') return 'text-destructive'
    return 'text-muted-foreground'
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  return (
    <Card className={cn('bg-card border-border', className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold tracking-tight text-foreground">
              {formatValue(value)}
            </p>
            {change !== undefined && (
              <div className={cn('flex items-center gap-1 text-sm', getTrendColor())}>
                <TrendIcon className="h-4 w-4" />
                <span className="font-medium">
                  {change > 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
                <span className="text-muted-foreground">{changeLabel}</span>
              </div>
            )}
          </div>
          {icon && (
            <div className="rounded-lg bg-primary/10 p-3 text-primary">
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
