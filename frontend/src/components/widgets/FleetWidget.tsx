'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FleetWidgetProps } from '@/types/dashboard'
import { TrendingUp, TrendingDown } from 'lucide-react'

export function FleetWidget({ data, loading, className }: FleetWidgetProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Fleet Comparison</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data) {
    return null // Hide widget if no fleet data
  }

  const getComparisonIcon = (thisYacht: number, average: number) => {
    if (thisYacht < average) {
      return <TrendingDown className="h-4 w-4 text-green-500" />
    }
    return <TrendingUp className="h-4 w-4 text-red-500" />
  }

  const getComparisonText = (thisYacht: number, average: number) => {
    const diff = ((thisYacht - average) / average * 100).toFixed(0)
    if (thisYacht < average) {
      return `${Math.abs(Number(diff))}% below average`
    }
    return `${diff}% above average`
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Fleet Comparison</CardTitle>
        <CardDescription>vs {data.yacht_count} similar yachts</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Comparisons */}
        <div className="space-y-3 mb-4">
          {data.comparisons.map((comparison, idx) => (
            <div key={idx} className="p-2 rounded border">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium">{comparison.metric}</p>
                {getComparisonIcon(comparison.this_yacht, comparison.fleet_average)}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-bold">{comparison.this_yacht}</span>
                <span className="text-xs text-muted-foreground">vs {comparison.fleet_average} avg</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {getComparisonText(comparison.this_yacht, comparison.fleet_average)}
              </p>
              {comparison.ranking && (
                <p className="text-xs text-muted-foreground">
                  Rank: {comparison.ranking}/{data.yacht_count}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Fleet Alerts */}
        {data.alerts && data.alerts.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Fleet Alerts</p>
            <div className="space-y-2">
              {data.alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-2 rounded border ${
                    alert.severity === 'critical'
                      ? 'border-red-500 bg-red-50'
                      : alert.severity === 'warning'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-blue-500 bg-blue-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <p className="text-sm flex-1">{alert.message}</p>
                    <Badge
                      variant={alert.severity === 'critical' ? 'destructive' : 'default'}
                      className="ml-2 text-xs"
                    >
                      {alert.severity}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(alert.date).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
