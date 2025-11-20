'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { WorkOrdersWidgetProps, WorkOrderItem } from '@/types/dashboard'

export function WorkOrdersWidget({ data, loading, className }: WorkOrdersWidgetProps) {
  const router = useRouter()

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'destructive'
      case 'important':
        return 'default'
      case 'routine':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const handleWorkOrderClick = (wo: WorkOrderItem) => {
    router.push(`/search?q=${encodeURIComponent(`work order ${wo.title}`)}`)
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Work Orders</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Work Orders</CardTitle>
          <CardDescription>Status overview</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Work Orders</CardTitle>
        <CardDescription>Status overview</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-2xl font-bold text-red-600">{data.overdue_count}</p>
            <p className="text-xs text-muted-foreground">Overdue</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-2xl font-bold text-orange-600">{data.due_this_week}</p>
            <p className="text-xs text-muted-foreground">This Week</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-2xl font-bold text-blue-600">{data.high_priority}</p>
            <p className="text-xs text-muted-foreground">High Priority</p>
          </div>
        </div>

        {/* Recent Overdue List */}
        {data.recent_overdue.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Recent Overdue</p>
            <div className="space-y-2">
              {data.recent_overdue.slice(0, 5).map((wo) => (
                <div
                  key={wo.id}
                  onClick={() => handleWorkOrderClick(wo)}
                  className="flex items-start justify-between p-2 rounded border hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{wo.title}</p>
                    {wo.equipment_name && (
                      <p className="text-xs text-muted-foreground">{wo.equipment_name}</p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1 ml-2">
                    <Badge variant={getPriorityColor(wo.priority)} className="text-xs">
                      {wo.priority}
                    </Badge>
                    {wo.days_overdue && (
                      <span className="text-xs text-red-600">
                        {wo.days_overdue}d overdue
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {data.recent_overdue.length > 5 && (
              <button
                onClick={() => router.push('/search?q=overdue work orders')}
                className="w-full mt-2 text-xs text-primary hover:underline"
              >
                View all overdue
              </button>
            )}
          </div>
        )}

        {data.recent_overdue.length === 0 && (
          <p className="text-sm text-muted-foreground">No overdue work orders</p>
        )}
      </CardContent>
    </Card>
  )
}
