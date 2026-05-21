'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { KPICard } from '@/components/dashboard/kpi-card'
import { ChartCard } from '@/components/dashboard/chart-card'
import { StatusBadge } from '@/components/dashboard/status-badge'
import {
  Users,
  Headphones,
  Clock,
  ThumbsUp,
  MessageSquare,
  TrendingUp,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const ticketData = Array.from({ length: 14 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() - (13 - i))
  return {
    date: date.toISOString().split('T')[0],
    opened: Math.floor(80 + Math.random() * 40),
    resolved: Math.floor(75 + Math.random() * 45),
  }
})

const recentTickets = [
  { id: 'TKT-4521', subject: 'Payment issue with subscription', customer: 'John D.', status: 'open', priority: 'high', time: '10 min ago' },
  { id: 'TKT-4520', subject: 'Cannot access account', customer: 'Sarah M.', status: 'investigating', priority: 'medium', time: '25 min ago' },
  { id: 'TKT-4519', subject: 'Feature request: Export to CSV', customer: 'Mike R.', status: 'open', priority: 'low', time: '1 hour ago' },
  { id: 'TKT-4518', subject: 'Integration not working', customer: 'Lisa K.', status: 'resolved', priority: 'high', time: '2 hours ago' },
]

export default function CRMPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">CRM & Support</h1>
          <p className="text-muted-foreground">
            Customer relationship management and support analytics
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <KPICard
            title="Total Customers"
            value={24856}
            change={8.2}
            trend="up"
            icon={<Users className="h-5 w-5" />}
          />
          <KPICard
            title="Open Tickets"
            value={142}
            change={-12.5}
            trend="down"
            icon={<Headphones className="h-5 w-5" />}
          />
          <KPICard
            title="Avg Response Time"
            value="18min"
            change={-25.0}
            trend="down"
            icon={<Clock className="h-5 w-5" />}
          />
          <KPICard
            title="CSAT Score"
            value={4.7}
            change={5.0}
            trend="up"
            icon={<ThumbsUp className="h-5 w-5" />}
          />
          <KPICard
            title="Messages Today"
            value={1245}
            change={15.2}
            trend="up"
            icon={<MessageSquare className="h-5 w-5" />}
          />
          <KPICard
            title="Resolution Rate"
            value={94.5}
            change={2.1}
            trend="up"
            format="percentage"
            icon={<TrendingUp className="h-5 w-5" />}
          />
        </div>

        <ChartCard title="Support Tickets" description="Daily ticket volume over the last 14 days">
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={ticketData}>
                <defs>
                  <linearGradient id="openedGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="resolvedGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  stroke="var(--muted-foreground)"
                  fontSize={12}
                />
                <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                  }}
                />
                <Area type="monotone" dataKey="opened" stroke="var(--chart-2)" fill="url(#openedGradient)" strokeWidth={2} name="Opened" />
                <Area type="monotone" dataKey="resolved" stroke="var(--chart-1)" fill="url(#resolvedGradient)" strokeWidth={2} name="Resolved" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-foreground">Recent Tickets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-foreground">{ticket.subject}</span>
                      <StatusBadge
                        status={ticket.priority === 'high' ? 'warning' : ticket.priority === 'medium' ? 'info' : 'neutral'}
                        label={ticket.priority}
                      />
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {ticket.id} &middot; {ticket.customer} &middot; {ticket.time}
                    </div>
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
