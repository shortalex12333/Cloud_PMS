'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FaultsWidgetProps, FaultItem } from '@/types/dashboard'

export function FaultsWidget({ data, loading, className }: FaultsWidgetProps) {
  const router = useRouter()

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'destructive'
      case 'medium':
        return 'default'
      case 'low':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const handleFaultClick = (fault: FaultItem) => {
    const query = fault.fault_code
      ? `fault ${fault.fault_code} ${fault.equipment_name}`
      : `${fault.equipment_name} ${fault.title}`
    router.push(`/search?q=${encodeURIComponent(query)}`)
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Faults</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Faults</CardTitle>
          <CardDescription>Recent fault activity</CardDescription>
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
        <CardTitle>Faults</CardTitle>
        <CardDescription>Recent fault activity</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-xl font-bold">{data.last_7_days}</p>
            <p className="text-xs text-muted-foreground">Last 7 days</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-xl font-bold">{data.last_30_days}</p>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-accent">
            <p className="text-xl font-bold text-red-600">{data.critical_count}</p>
            <p className="text-xs text-muted-foreground">Critical</p>
          </div>
        </div>

        {/* Recent Critical Faults */}
        {data.recent_critical.length > 0 && (
          <div className="mb-4">
            <p className="text-sm font-medium mb-2">Recent Critical</p>
            <div className="space-y-2">
              {data.recent_critical.slice(0, 3).map((fault) => (
                <div
                  key={fault.id}
                  onClick={() => handleFaultClick(fault)}
                  className="p-2 rounded border hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex-1 min-w-0">
                      {fault.fault_code && (
                        <p className="text-xs font-mono text-muted-foreground mb-0.5">
                          {fault.fault_code}
                        </p>
                      )}
                      <p className="text-sm font-medium truncate">{fault.title}</p>
                      <p className="text-xs text-muted-foreground">{fault.equipment_name}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1 ml-2">
                      <Badge variant={getSeverityColor(fault.severity)} className="text-xs">
                        {fault.severity}
                      </Badge>
                      {fault.resolved && (
                        <Badge variant="secondary" className="text-xs">Resolved</Badge>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(fault.detected_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Repeating Faults */}
        {data.repeating_faults && data.repeating_faults.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Repeating Issues</p>
            <div className="space-y-2">
              {data.repeating_faults.slice(0, 3).map((fault) => (
                <div
                  key={fault.id}
                  onClick={() => handleFaultClick(fault)}
                  className="p-2 rounded border border-orange-500 bg-orange-50 hover:bg-orange-100 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{fault.title}</p>
                      <p className="text-xs text-muted-foreground">{fault.equipment_name}</p>
                    </div>
                    {fault.occurrences && (
                      <span className="text-xs font-bold text-orange-600 ml-2">
                        {fault.occurrences}x
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.recent_critical.length === 0 && (!data.repeating_faults || data.repeating_faults.length === 0) && (
          <p className="text-sm text-muted-foreground">No recent critical faults</p>
        )}

        <button
          onClick={() => router.push('/search?q=fault history')}
          className="w-full mt-3 text-xs text-primary hover:underline"
        >
          View all faults
        </button>
      </CardContent>
    </Card>
  )
}
