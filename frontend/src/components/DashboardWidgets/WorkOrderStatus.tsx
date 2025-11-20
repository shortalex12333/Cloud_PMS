'use client';

import { Wrench, Clock, CheckCircle2 } from 'lucide-react';

export default function WorkOrderStatus() {
  // TODO: Fetch from API
  const stats = {
    total: 42,
    overdue: 3,
    in_progress: 8,
    completed_this_week: 12,
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Wrench className="h-5 w-5 text-primary" />
          Work Orders
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Overdue */}
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="h-4 w-4 text-destructive" />
            <span className="text-xs font-medium text-destructive">Overdue</span>
          </div>
          <p className="text-2xl font-bold text-destructive">{stats.overdue}</p>
        </div>

        {/* In Progress */}
        <div className="p-4 bg-primary/10 border border-primary/20 rounded-md">
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

      <button className="w-full mt-4 px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80">
        View All Work Orders
      </button>
    </div>
  );
}
