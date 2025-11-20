'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { InventoryWidgetProps, InventoryItem } from '@/types/dashboard'

export function InventoryWidget({ data, loading, className }: InventoryWidgetProps) {
  const router = useRouter()

  const getCriticalityColor = (criticality: string) => {
    switch (criticality) {
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

  const getStockPercentage = (current: number, min: number) => {
    if (min === 0) return 100
    return (current / min) * 100
  }

  const handlePartClick = (part: InventoryItem) => {
    router.push(`/search?q=${encodeURIComponent(part.part_name + ' stock')}`)
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Inventory</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Inventory</CardTitle>
          <CardDescription>Low stock alerts</CardDescription>
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
        <CardTitle>Inventory</CardTitle>
        <CardDescription>Low stock alerts</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Summary */}
        <div className="mb-4 p-3 rounded-lg bg-accent">
          <p className="text-2xl font-bold text-orange-600">{data.low_stock_count}</p>
          <p className="text-sm text-muted-foreground">Parts below minimum</p>
        </div>

        {/* Critical Parts List */}
        {data.critical_items.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium mb-2">Critical Items</p>
            {data.critical_items.slice(0, 5).map((part) => {
              const percentage = getStockPercentage(part.current_qty, part.min_qty)
              return (
                <div
                  key={part.id}
                  onClick={() => handlePartClick(part)}
                  className="p-2 rounded border hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{part.part_name}</p>
                      <p className="text-xs text-muted-foreground">{part.part_number}</p>
                    </div>
                    <Badge variant={getCriticalityColor(part.criticality)} className="ml-2 text-xs">
                      {part.criticality}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          percentage < 50 ? 'bg-red-500' : percentage < 100 ? 'bg-orange-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                      {part.current_qty}/{part.min_qty}
                    </span>
                  </div>

                  {part.location && (
                    <p className="text-xs text-muted-foreground mt-1">📍 {part.location}</p>
                  )}
                </div>
              )
            })}

            {data.critical_items.length > 5 && (
              <button
                onClick={() => router.push('/search?q=low stock inventory')}
                className="w-full mt-2 text-xs text-primary hover:underline"
              >
                View all ({data.critical_items.length} items)
              </button>
            )}
          </div>
        )}

        {data.critical_items.length === 0 && (
          <p className="text-sm text-muted-foreground">All stock levels normal</p>
        )}
      </CardContent>
    </Card>
  )
}
