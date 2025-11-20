'use client';

import { Package, AlertTriangle } from 'lucide-react';

export default function InventoryStatus() {
  // TODO: Fetch from API
  const stats = {
    low_stock: 5,
    on_order: 8,
    total_parts: 234,
  };

  const lowStockItems = [
    { name: 'Racor 2040 Filter', quantity: 1, min: 4 },
    { name: 'MTU Coolant Temp Sensor', quantity: 0, min: 2 },
    { name: 'O-Ring Kit (Stabiliser)', quantity: 2, min: 5 },
  ];

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
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <span className="text-xs font-medium text-destructive">Low Stock</span>
          <p className="text-xl font-bold text-destructive mt-1">
            {stats.low_stock}
          </p>
        </div>
        <div className="p-3 bg-background border border-border rounded-md">
          <span className="text-xs font-medium text-muted-foreground">
            On Order
          </span>
          <p className="text-xl font-bold mt-1">{stats.on_order}</p>
        </div>
      </div>

      {/* Low Stock Items */}
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground mb-2">
          Items Needing Reorder
        </h3>
        {lowStockItems.map((item, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between p-2 bg-background border border-border rounded text-xs"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-3 w-3 text-destructive" />
              <span className="truncate">{item.name}</span>
            </div>
            <span className="text-destructive font-medium">
              {item.quantity}/{item.min}
            </span>
          </div>
        ))}
      </div>

      <button className="w-full mt-4 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
        Order Parts
      </button>
    </div>
  );
}
