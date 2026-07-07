'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard, KPICardSkeleton } from '@/components/dashboard/kpi-card'
import { ChartCard, ChartCardSkeleton } from '@/components/dashboard/chart-card'
import {
  useInventoryKPIs,
  useWarehouseCapacity,
  useLowStockItems,
  useStockStatusSummary,
} from '@/hooks/use-analytics'
import type {
  WarehouseCapacity,
  LowStockItem,
  StockStatusSummary,
  LocationType,
} from '@/types/analytics'
import {
  Package,
  Warehouse,
  TrendingDown,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  Filter,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Constantes visuales ──────────────────────────────────────────────────────

const LOCATION_TYPE_LABELS: Record<LocationType, string> = {
  WAREHOUSE:           'Bodega',
  DISTRIBUTION_CENTER: 'Centro Distribución',
  RETAIL_POINT:        'Punto de Venta',
}

const LOCATION_TYPE_COLOR: Record<LocationType, string> = {
  WAREHOUSE:           'var(--chart-1)',
  DISTRIBUTION_CENTER: 'var(--chart-2)',
  RETAIL_POINT:        'var(--chart-3)',
}

const STATUS_COLOR: Record<string, string> = {
  NORMAL:       'var(--chart-1)',
  CRITICAL:     'var(--warning)',
  OUT_OF_STOCK: 'var(--destructive)',
}

const STATUS_LABEL: Record<string, string> = {
  NORMAL:       'Normal',
  CRITICAL:     'Crítico',
  OUT_OF_STOCK: 'Sin stock',
}

// ─── Componente de alerta de stock bajo ───────────────────────────────────────

function LowStockRow({ item }: { item: LowStockItem }) {
  const isOut = item.is_out_of_stock
  return (
    <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4 transition-colors hover:bg-muted/50">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-foreground truncate">{item.product_name}</span>
          {isOut && (
            <Badge variant="destructive" className="shrink-0 text-xs">Sin stock</Badge>
          )}
          {!isOut && (
            <Badge className="shrink-0 text-xs bg-warning/10 text-warning border-warning/20">
              Crítico
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm text-muted-foreground">{item.sku_id}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">{item.category}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">
            {item.locations_count} ubicación{item.locations_count !== 1 ? 'es' : ''}
          </span>
        </div>
      </div>
      <div className="text-right shrink-0 ml-4">
        <div className={`text-lg font-semibold ${isOut ? 'text-destructive' : 'text-warning'}`}>
          {item.total_available_stock} {item.unit}
        </div>
        <div className="text-sm text-muted-foreground">
          Mínimo: {item.critical_threshold}
        </div>
      </div>
    </div>
  )
}

function LowStockSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4">
      <div className="space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-56" />
      </div>
      <div className="text-right space-y-1">
        <Skeleton className="h-6 w-20 ml-auto" />
        <Skeleton className="h-3 w-16 ml-auto" />
      </div>
    </div>
  )
}

// ─── Tooltip personalizado para el gráfico de barras ─────────────────────────

function CapacityTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload ?? {}
  const stock       = row.stock ?? 0
  const hasCapacity = typeof row.capacity === 'number' && row.capacity > 0
  const pct         = hasCapacity ? Math.round((stock / row.capacity) * 100) : null
  return (
    <div
      className="rounded-lg border border-border bg-popover p-3 shadow-lg text-sm"
      style={{ minWidth: 180 }}
    >
      <p className="font-semibold text-foreground mb-1">{label}</p>
      <p className="text-muted-foreground">
        Stock físico: <span className="text-foreground font-medium">{stock.toLocaleString()}</span>
      </p>
      {typeof row.available === 'number' && (
        <p className="text-muted-foreground">
          Disponible: <span className="text-foreground font-medium">{row.available.toLocaleString()}</span>
        </p>
      )}
      {typeof row.reserved === 'number' && (
        <p className="text-muted-foreground">
          Reservado: <span className="text-foreground font-medium">{row.reserved.toLocaleString()}</span>
        </p>
      )}
      {hasCapacity && (
        <>
          <p className="text-muted-foreground">
            Capacidad: <span className="text-foreground font-medium">{row.capacity.toLocaleString()}</span>
          </p>
          <p className="text-muted-foreground">
            Utilización: <span className="font-medium" style={{ color: pct! > 90 ? 'var(--destructive)' : pct! > 75 ? 'var(--warning)' : 'var(--chart-1)' }}>{pct}%</span>
          </p>
        </>
      )}
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function InventoryPage() {
  const [locationTypeFilter, setLocationTypeFilter] = useState<string>('ALL')

  const { data: kpis,      isLoading: kpisLoading      } = useInventoryKPIs()
  const { data: warehouses, isLoading: warehouseLoading } = useWarehouseCapacity()
  const { data: lowStock,   isLoading: lowStockLoading  } = useLowStockItems()
  const { data: statusData, isLoading: statusLoading    } = useStockStatusSummary()

  // Filtrar bodegas según el selector
  const filteredWarehouses = (warehouses as WarehouseCapacity[] | undefined)?.filter(
    (w) => locationTypeFilter === 'ALL' || w.location_type === locationTypeFilter,
  ) ?? []

  const lowStockList = lowStock as LowStockItem[]   | undefined
  const statusList   = statusData as StockStatusSummary[] | undefined

  return (
    <DashboardLayout>
      <div className="space-y-6">

        {/* ── Encabezado ── */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Inventario Distribuido
          </h1>
          <p className="text-muted-foreground">
            Gestión de stock multi-bodega y analítica en tiempo real
          </p>
        </div>

        {/* ── KPI Cards ── */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)
          ) : (
            <>
              <KPICard
                title="Total SKUs"
                value={kpis?.total_skus ?? 0}
                icon={<Package className="h-5 w-5" />}
              />
              <KPICard
                title="Valor en Stock"
                value={kpis?.total_stock_value ?? 0}
                format="currency"
                icon={<BarChart3 className="h-5 w-5" />}
              />
              <KPICard
                title="Bodegas activas"
                value={kpis?.warehouses_count ?? 0}
                icon={<Warehouse className="h-5 w-5" />}
              />
              <KPICard
                title="Stock bajo mínimo"
                value={kpis?.low_stock_count ?? 0}
                icon={<TrendingDown className="h-5 w-5" />}
              />
              <KPICard
                title="Sin stock"
                value={kpis?.out_of_stock_count ?? 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <KPICard
                title="Rotación (x)"
                value={kpis?.turnover_rate ?? 0}
                icon={<RefreshCw className="h-5 w-5" />}
              />
            </>
          )}
        </div>

        {/* ── Fila de gráficos ── */}
        <div className="grid gap-6 lg:grid-cols-3">

          {/* Capacidad por bodega (2/3) */}
          {warehouseLoading ? (
            <div className="lg:col-span-2">
              <ChartCardSkeleton />
            </div>
          ) : (
            <ChartCard
              title="Stock por Ubicación"
              description="Stock físico agregado por ubicación (todos los SKUs)"
              className="lg:col-span-2"
              action={
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <Select value={locationTypeFilter} onValueChange={setLocationTypeFilter}>
                    <SelectTrigger className="h-8 w-44 text-xs border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">Todos los tipos</SelectItem>
                      <SelectItem value="WAREHOUSE">Bodegas</SelectItem>
                      <SelectItem value="DISTRIBUTION_CENTER">C. Distribución</SelectItem>
                      <SelectItem value="RETAIL_POINT">Puntos de Venta</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              }
            >
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={filteredWarehouses} layout="vertical" barCategoryGap="25%">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                    <XAxis
                      type="number"
                      stroke="var(--muted-foreground)"
                      fontSize={11}
                      tickFormatter={(v) => v.toLocaleString()}
                    />
                    <YAxis
                      dataKey="location_code"
                      type="category"
                      stroke="var(--muted-foreground)"
                      fontSize={11}
                      width={112}
                    />
                    <Tooltip content={<CapacityTooltip />} />
                    <Bar dataKey="capacity" name="Capacidad" fill="var(--chart-2)" opacity={0.25} radius={[0, 4, 4, 0]} />
                    <Bar dataKey="stock"    name="Stock actual" radius={[0, 4, 4, 0]}>
                      {filteredWarehouses.map((w) => (
                        <Cell
                          key={w.location_id}
                          fill={LOCATION_TYPE_COLOR[w.location_type] ?? 'var(--chart-1)'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              {/* Leyenda de tipos */}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
                {Object.entries(LOCATION_TYPE_LABELS).map(([type, label]) => (
                  <span key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ background: LOCATION_TYPE_COLOR[type as LocationType] }}
                    />
                    {label}
                  </span>
                ))}
              </div>
            </ChartCard>
          )}

          {/* Distribución de estado de stock (1/3) */}
          {statusLoading ? (
            <ChartCardSkeleton />
          ) : (
            <ChartCard
              title="Estado del Stock"
              description="Distribución de SKUs por nivel de criticidad"
            >
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusList}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      strokeWidth={0}
                    >
                      {statusList?.map((entry) => (
                        <Cell
                          key={entry.status}
                          fill={STATUS_COLOR[entry.status] ?? 'var(--chart-4)'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        `${value.toLocaleString()} SKUs`,
                        STATUS_LABEL[name] ?? name,
                      ]}
                      contentStyle={{
                        backgroundColor: 'var(--popover)',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 mt-2">
                {statusList?.map((s) => (
                  <div key={s.status} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: STATUS_COLOR[s.status] }}
                      />
                      {STATUS_LABEL[s.status] ?? s.status}
                    </span>
                    <span className="font-medium text-foreground">
                      {s.count.toLocaleString()}
                      <span className="text-muted-foreground font-normal ml-1">({s.percentage}%)</span>
                    </span>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>

        {/* ── Tabla de alertas de stock bajo ── */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-warning" />
              Alertas de Stock Bajo
              {!lowStockLoading && lowStockList && (
                <Badge variant="secondary" className="ml-1 font-normal">
                  {lowStockList.length} ítems
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {lowStockLoading
                ? Array.from({ length: 4 }).map((_, i) => <LowStockSkeleton key={i} />)
                : lowStockList?.length
                  ? lowStockList.map((item) => (
                      <LowStockRow key={item.sku_id} item={item} />
                    ))
                  : (
                    <div className="py-8 text-center text-muted-foreground text-sm">
                      No hay alertas de stock bajo en este momento.
                    </div>
                  )
              }
            </div>
          </CardContent>
        </Card>

      </div>
    </DashboardLayout>
  )
}
