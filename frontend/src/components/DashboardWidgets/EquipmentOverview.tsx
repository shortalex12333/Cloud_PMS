'use client';

import { Settings, AlertCircle, CheckCircle } from 'lucide-react';

export default function EquipmentOverview() {
  // TODO: Fetch from API
  const stats = {
    total: 156,
    critical: 12,
    operational: 144,
    needs_attention: 8,
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          Equipment Overview
        </h2>
        <span className="text-xs text-muted-foreground">
          {stats.total} systems
        </span>
      </div>

      <div className="space-y-3">
        {/* Operational */}
        <div className="flex items-center justify-between p-3 bg-background border border-border rounded-md">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-sm">Operational</span>
          </div>
          <span className="text-sm font-medium">{stats.operational}</span>
        </div>

        {/* Needs Attention */}
        <div className="flex items-center justify-between p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-md">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <span className="text-sm text-yellow-600">Needs Attention</span>
          </div>
          <span className="text-sm font-medium text-yellow-600">
            {stats.needs_attention}
          </span>
        </div>

        {/* Critical Systems */}
        <div className="flex items-center justify-between p-3 bg-background border border-border rounded-md">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">Critical Systems</span>
          </div>
          <span className="text-sm font-medium">{stats.critical}</span>
        </div>
      </div>

      <button className="w-full mt-4 px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80">
        View Equipment List
      </button>
    </div>
  );
}
