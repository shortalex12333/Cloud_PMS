'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Wrench, Clock, CheckCircle2, Search, AlertCircle } from 'lucide-react';

interface WorkOrderStats {
  total: number;
  overdue: number;
  in_progress: number;
  completed_this_week: number;
  overdue_items?: Array<{
    id: string;
    title: string;
    equipment_name: string;
    days_overdue: number;
  }>;
}

// Mock data fallback
const MOCK_STATS: WorkOrderStats = {
  total: 42,
  overdue: 3,
  in_progress: 8,
  completed_this_week: 12,
  overdue_items: [
    { id: '1', title: 'Replace HVAC filters', equipment_name: 'HVAC System', days_overdue: 5 },
    { id: '2', title: 'Generator coolant flush', equipment_name: 'Port Generator', days_overdue: 3 },
    { id: '3', title: 'Stabilizer inspection', equipment_name: 'Stabilizer System', days_overdue: 2 },
  ],
};

export default function WorkOrderStatus() {
  const router = useRouter();
  const [stats, setStats] = useState<WorkOrderStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook';
        const response = await fetch(`${baseUrl}/v1/work-orders/status`);

        if (!response.ok) throw new Error('API unavailable');

        const data = await response.json();
        setStats(data);
      } catch (err) {
        console.log('[WorkOrderStatus] Using mock data:', err);
        setStats(MOCK_STATS);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleSearchWorkOrders = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  if (loading || !stats) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 w-32 bg-muted rounded mb-4" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-20 bg-muted rounded" />
            <div className="h-20 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Wrench className="h-5 w-5 text-primary" />
          Work Orders
        </h2>
        <span className="text-xs text-muted-foreground">
          {stats.total} total
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Overdue */}
        <div
          onClick={() => handleSearchWorkOrders('overdue work orders')}
          className="p-4 bg-destructive/10 border border-destructive/20 rounded-md cursor-pointer hover:bg-destructive/20 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1">
            <Clock className="h-4 w-4 text-destructive" />
            <span className="text-xs font-medium text-destructive">Overdue</span>
          </div>
          <p className="text-2xl font-bold text-destructive">{stats.overdue}</p>
        </div>

        {/* In Progress */}
        <div
          onClick={() => handleSearchWorkOrders('work orders in progress')}
          className="p-4 bg-primary/10 border border-primary/20 rounded-md cursor-pointer hover:bg-primary/20 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1">
            <Wrench className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium text-primary">Active</span>
          </div>
          <p className="text-2xl font-bold text-primary">{stats.in_progress}</p>
        </div>

        {/* Completed This Week */}
        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-md col-span-2">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-xs font-medium text-green-600">
              Completed This Week
            </span>
          </div>
          <p className="text-2xl font-bold text-green-600">
            {stats.completed_this_week}
          </p>
        </div>
      </div>

      {/* Overdue Items List */}
      {stats.overdue_items && stats.overdue_items.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Overdue Items
          </h3>
          <div className="space-y-2">
            {stats.overdue_items.slice(0, 3).map((item) => (
              <div
                key={item.id}
                onClick={() => handleSearchWorkOrders(item.equipment_name)}
                className="flex items-center justify-between p-2 bg-background border border-border rounded text-xs cursor-pointer hover:bg-accent/50"
              >
                <span className="truncate">{item.title}</span>
                <span className="text-destructive font-medium whitespace-nowrap ml-2">
                  {item.days_overdue}d overdue
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search prompt instead of action button */}
      <button
        onClick={() => handleSearchWorkOrders('work orders')}
        className="w-full px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 flex items-center justify-center gap-2"
      >
        <Search className="h-4 w-4" />
        Search Work Orders
      </button>

      {/* Read-only notice */}
      <p className="mt-2 text-xs text-muted-foreground text-center">
        Create new work orders via Search bar
      </p>
    </div>
  );
}
