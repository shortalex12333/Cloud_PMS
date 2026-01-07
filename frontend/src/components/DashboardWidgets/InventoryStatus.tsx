'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Package, AlertTriangle, Search } from 'lucide-react';

interface LowStockItem {
  id: string;
  name: string;
  part_number?: string;
  quantity: number;
  min_quantity: number;
  system?: string;
}

interface InventoryStats {
  low_stock_count: number;
  on_order: number;
  total_parts: number;
  low_stock_items: LowStockItem[];
}

// Mock data fallback
const MOCK_STATS: InventoryStats = {
  low_stock_count: 5,
  on_order: 8,
  total_parts: 234,
  low_stock_items: [
    { id: '1', name: 'Racor 2040 Filter', part_number: '2040N2', quantity: 1, min_quantity: 4, system: 'Fuel System' },
    { id: '2', name: 'MTU Coolant Temp Sensor', part_number: 'MTU-TEMP-01', quantity: 0, min_quantity: 2, system: 'Cooling' },
    { id: '3', name: 'O-Ring Kit (Stabiliser)', part_number: 'STAB-ORING-KIT', quantity: 2, min_quantity: 5, system: 'Stabilizer' },
    { id: '4', name: 'Generator Coolant 5L', part_number: 'MTU-COOL-5L', quantity: 3, min_quantity: 8, system: 'Cooling' },
  ],
};

export default function InventoryStatus() {
  const router = useRouter();
  const [stats, setStats] = useState<InventoryStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook').replace(/\/+$/, '');
        const response = await fetch(`${baseUrl}/v1/inventory/low-stock`);

        if (!response.ok) throw new Error('API unavailable');

        const data = await response.json();
        setStats(data);
      } catch (err) {
        console.log('[InventoryStatus] Using mock data:', err);
        setStats(MOCK_STATS);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleSearch = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  if (loading || !stats) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 w-36 bg-muted rounded mb-4" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="h-16 bg-muted rounded" />
            <div className="h-16 bg-muted rounded" />
          </div>
          <div className="space-y-2">
            <div className="h-8 bg-muted rounded" />
            <div className="h-8 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Package className="h-5 w-5 text-primary" />
          Inventory Status
        </h2>
        <span className="text-xs text-muted-foreground">
          {stats.total_parts} parts
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div
          onClick={() => handleSearch('low stock parts inventory')}
          className="p-3 bg-destructive/10 border border-destructive/20 rounded-md cursor-pointer hover:bg-destructive/20 transition-colors"
        >
          <span className="text-xs font-medium text-destructive">Low Stock</span>
          <p className="text-xl font-bold text-destructive mt-1">
            {stats.low_stock_count}
          </p>
        </div>
        <div
          onClick={() => handleSearch('parts on order')}
          className="p-3 bg-background border border-border rounded-md cursor-pointer hover:bg-accent/50 transition-colors"
        >
          <span className="text-xs font-medium text-muted-foreground">
            On Order
          </span>
          <p className="text-xl font-bold mt-1">{stats.on_order}</p>
        </div>
      </div>

      {/* Low Stock Items */}
      <div className="mb-4">
        <h3 className="text-xs font-medium text-muted-foreground mb-2">
          Items Needing Reorder
        </h3>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {stats.low_stock_items.slice(0, 4).map((item) => (
            <div
              key={item.id}
              onClick={() => handleSearch(item.name)}
              className="flex items-center justify-between p-2 bg-background border border-border rounded text-xs cursor-pointer hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <AlertTriangle className={`h-3 w-3 flex-shrink-0 ${
                  item.quantity === 0 ? 'text-destructive' : 'text-yellow-600'
                }`} />
                <span className="truncate">{item.name}</span>
              </div>
              <span className={`font-medium whitespace-nowrap ml-2 ${
                item.quantity === 0 ? 'text-destructive' : 'text-yellow-600'
              }`}>
                {item.quantity}/{item.min_quantity}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Search prompt instead of "Order Parts" button */}
      <button
        onClick={() => handleSearch('inventory parts')}
        className="w-full px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 flex items-center justify-center gap-2"
      >
        <Search className="h-4 w-4" />
        Search Inventory
      </button>

      {/* Read-only notice */}
      <p className="mt-2 text-xs text-muted-foreground text-center">
        Order parts via Search bar
      </p>
    </div>
  );
}
