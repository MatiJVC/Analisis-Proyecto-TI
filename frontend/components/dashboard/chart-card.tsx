'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ChartCardProps {
  title: string
  description?: string
  children: React.ReactNode
  action?: React.ReactNode
  className?: string
}

export function ChartCard({
  title,
  description,
  children,
  action,
  className,
}: ChartCardProps) {
  return (
    <Card className={cn('bg-card border-border', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-base font-semibold text-foreground">{title}</CardTitle>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </CardHeader>
      <CardContent className="pt-0">{children}</CardContent>
    </Card>
  )
}

export function ChartCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn('bg-card border-border', className)}>
      <CardHeader className="pb-2">
        <div className="h-5 w-32 animate-pulse rounded bg-muted" />
        <div className="h-4 w-48 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  )
}
