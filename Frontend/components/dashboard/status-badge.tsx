'use client'

import { cn } from '@/lib/utils'

type StatusType = 'success' | 'warning' | 'error' | 'info' | 'neutral'

interface StatusBadgeProps {
  status: StatusType | string
  label?: string
  showDot?: boolean
  className?: string
}

const statusStyles: Record<StatusType, string> = {
  success: 'bg-success/10 text-success border-success/20',
  warning: 'bg-warning/10 text-warning border-warning/20',
  error: 'bg-destructive/10 text-destructive border-destructive/20',
  info: 'bg-chart-2/10 text-chart-2 border-chart-2/20',
  neutral: 'bg-muted text-muted-foreground border-muted',
}

const dotStyles: Record<StatusType, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-destructive',
  info: 'bg-chart-2',
  neutral: 'bg-muted-foreground',
}

// Map common status strings to status types
function getStatusType(status: string): StatusType {
  const statusMap: Record<string, StatusType> = {
    // Common status values
    operational: 'success',
    online: 'success',
    active: 'success',
    completed: 'success',
    delivered: 'success',
    resolved: 'success',
    success: 'success',
    
    degraded: 'warning',
    warning: 'warning',
    delayed: 'warning',
    investigating: 'warning',
    pending: 'warning',
    processing: 'warning',
    'in transit': 'warning',
    
    outage: 'error',
    offline: 'error',
    failed: 'error',
    error: 'error',
    critical: 'error',
    open: 'error',
    
    info: 'info',
    low: 'info',
    medium: 'info',
    high: 'warning',
  }
  
  return statusMap[status.toLowerCase()] || 'neutral'
}

export function StatusBadge({
  status,
  label,
  showDot = true,
  className,
}: StatusBadgeProps) {
  const statusType = typeof status === 'string' && !['success', 'warning', 'error', 'info', 'neutral'].includes(status)
    ? getStatusType(status)
    : (status as StatusType)
  
  const displayLabel = label || status

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize',
        statusStyles[statusType],
        className
      )}
    >
      {showDot && (
        <span className={cn('h-1.5 w-1.5 rounded-full', dotStyles[statusType])} />
      )}
      {displayLabel}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: 'critical' | 'high' | 'medium' | 'low' }) {
  const severityMap: Record<string, StatusType> = {
    critical: 'error',
    high: 'warning',
    medium: 'info',
    low: 'neutral',
  }
  
  return <StatusBadge status={severityMap[severity]} label={severity} />
}
