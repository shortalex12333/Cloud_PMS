'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { UpcomingTasksWidgetProps, UpcomingTaskItem } from '@/types/dashboard'
import { Calendar } from 'lucide-react'

export function UpcomingTasksWidget({ data, loading, className }: UpcomingTasksWidgetProps) {
  const router = useRouter()

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'scheduled':
        return 'default'
      case 'corrective':
        return 'destructive'
      case 'inspection':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const getUrgencyColor = (daysUntilDue: number) => {
    if (daysUntilDue < 0) return 'text-red-600'
    if (daysUntilDue <= 3) return 'text-orange-600'
    if (daysUntilDue <= 7) return 'text-yellow-600'
    return 'text-muted-foreground'
  }

  const formatDueDate = (daysUntilDue: number) => {
    if (daysUntilDue < 0) return `${Math.abs(daysUntilDue)}d overdue`
    if (daysUntilDue === 0) return 'Due today'
    if (daysUntilDue === 1) return 'Due tomorrow'
    if (daysUntilDue <= 7) return `Due in ${daysUntilDue}d`
    return `Due in ${daysUntilDue}d`
  }

  const handleTaskClick = (task: UpcomingTaskItem) => {
    router.push(`/search?q=${encodeURIComponent(task.title)}`)
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Upcoming Tasks</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data || data.tasks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Upcoming Tasks</CardTitle>
          <CardDescription>Scheduled maintenance</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No upcoming tasks</p>
        </CardContent>
      </Card>
    )
  }

  // Group by urgency
  const overdue = data.tasks.filter(t => t.days_until_due < 0)
  const urgent = data.tasks.filter(t => t.days_until_due >= 0 && t.days_until_due <= 7)
  const upcoming = data.tasks.filter(t => t.days_until_due > 7)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Upcoming Tasks</CardTitle>
        <CardDescription>Next {data.tasks.length} scheduled tasks</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Overdue Tasks */}
        {overdue.length > 0 && (
          <div className="mb-4">
            <p className="text-sm font-medium text-red-600 mb-2">Overdue ({overdue.length})</p>
            <div className="space-y-2">
              {overdue.slice(0, 3).map((task) => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task)}
                  className="p-2 rounded border border-red-500 bg-red-50 hover:bg-red-100 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{task.title}</p>
                      {task.equipment_name && (
                        <p className="text-xs text-muted-foreground">{task.equipment_name}</p>
                      )}
                    </div>
                    <Badge variant={getTypeColor(task.type)} className="ml-2 text-xs">
                      {task.type}
                    </Badge>
                  </div>
                  <p className={`text-xs font-medium ${getUrgencyColor(task.days_until_due)}`}>
                    {formatDueDate(task.days_until_due)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Urgent (Next 7 days) */}
        {urgent.length > 0 && (
          <div className="mb-4">
            <p className="text-sm font-medium text-orange-600 mb-2">This Week ({urgent.length})</p>
            <div className="space-y-2">
              {urgent.slice(0, 5).map((task) => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task)}
                  className="p-2 rounded border hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{task.title}</p>
                      {task.equipment_name && (
                        <p className="text-xs text-muted-foreground">{task.equipment_name}</p>
                      )}
                    </div>
                    <Badge variant={getTypeColor(task.type)} className="ml-2 text-xs">
                      {task.type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3 text-muted-foreground" />
                    <p className={`text-xs ${getUrgencyColor(task.days_until_due)}`}>
                      {formatDueDate(task.days_until_due)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upcoming (Beyond 7 days) */}
        {upcoming.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Later ({upcoming.length})</p>
            <div className="space-y-2">
              {upcoming.slice(0, 3).map((task) => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task)}
                  className="p-2 rounded border hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{task.title}</p>
                      {task.equipment_name && (
                        <p className="text-xs text-muted-foreground">{task.equipment_name}</p>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground ml-2">
                      {task.days_until_due}d
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.total_count > data.tasks.length && (
          <button
            onClick={() => router.push('/search?q=upcoming maintenance')}
            className="w-full mt-3 text-xs text-primary hover:underline"
          >
            View all ({data.total_count} tasks)
          </button>
        )}
      </CardContent>
    </Card>
  )
}
