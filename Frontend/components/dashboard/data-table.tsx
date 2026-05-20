'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface Column<T> {
  key: keyof T | string
  header: string
  render?: (value: T[keyof T], row: T) => React.ReactNode
  className?: string
}

interface DataTableProps<T> {
  title: string
  description?: string
  columns: Column<T>[]
  data: T[]
  action?: React.ReactNode
  className?: string
}

export function DataTable<T extends Record<string, unknown>>({
  title,
  description,
  columns,
  data,
  action,
  className,
}: DataTableProps<T>) {
  return (
    <Card className={cn('bg-card border-border', className)}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base font-semibold text-foreground">{title}</CardTitle>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {columns.map((column) => (
                  <th
                    key={String(column.key)}
                    className={cn(
                      'px-4 py-3 text-left text-sm font-medium text-muted-foreground',
                      column.className
                    )}
                  >
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, index) => (
                <tr
                  key={index}
                  className="border-b border-border/50 transition-colors hover:bg-muted/30"
                >
                  {columns.map((column) => {
                    const value = row[column.key as keyof T]
                    return (
                      <td
                        key={String(column.key)}
                        className={cn(
                          'px-4 py-3 text-sm text-foreground',
                          column.className
                        )}
                      >
                        {column.render
                          ? column.render(value, row)
                          : String(value ?? '')}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function DataTableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <div className="h-5 w-32 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex gap-4">
              {Array.from({ length: cols }).map((_, j) => (
                <div key={j} className="h-6 flex-1 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
