'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskOverviewWidgetProps, RiskItem } from '@/types/dashboard'
import { ArrowUp, ArrowDown, Minus } from 'lucide-react'

export function RiskOverviewWidget({ data, loading, className }: RiskOverviewWidgetProps) {
  const router = useRouter()

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-500 text-white'
      case 'high':
        return 'bg-orange-500 text-white'
      case 'medium':
        return 'bg-yellow-500 text-white'
      case 'low':
        return 'bg-green-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <ArrowUp className="h-3 w-3 text-red-500" />
      case 'down':
        return <ArrowDown className="h-3 w-3 text-green-500" />
      default:
        return <Minus className="h-3 w-3 text-gray-500" />
    }
  }

  const handleEquipmentClick = (equipment: RiskItem) => {
    router.push(`/search?q=${encodeURIComponent(equipment.equipment_name + ' risk')}`)
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Risk Overview</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data || data.topRisks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Risk Overview</CardTitle>
          <CardDescription>High-risk systems requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No high-risk items detected</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Risk Overview</CardTitle>
        <CardDescription>High-risk systems requiring attention</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.topRisks.slice(0, 5).map((risk) => (
            <div
              key={risk.equipment_id}
              onClick={() => handleEquipmentClick(risk)}
              className="flex items-start justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-medium text-sm truncate">{risk.equipment_name}</p>
                  {getTrendIcon(risk.trend)}
                </div>
                <p className="text-xs text-muted-foreground mb-2">{risk.system_type}</p>
                {risk.contributing_factors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {risk.contributing_factors[0]}
                  </p>
                )}
              </div>
              <div className="flex flex-col items-end gap-1 ml-2">
                <Badge className={getRiskColor(risk.risk_level)}>
                  {risk.risk_level.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {(risk.risk_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>

        {data.topRisks.length > 5 && (
          <button
            onClick={() => router.push('/search?q=predictive risk overview')}
            className="w-full mt-3 text-xs text-primary hover:underline"
          >
            View all ({data.topRisks.length} items)
          </button>
        )}
      </CardContent>
    </Card>
  )
}
