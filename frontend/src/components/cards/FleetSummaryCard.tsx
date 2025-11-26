/**
 * FleetSummaryCard Component
 *
 * Displays multi-vessel overview for fleet management
 */

'use client';

import { Ship, AlertTriangle, Wrench, CheckCircle2 } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface FleetSummaryCardProps {
  fleetData: {
    fleet_name?: string;
    vessels: {
      yacht_id: string;
      yacht_name: string;
      location: string;
      status: 'operational' | 'maintenance' | 'offline';
      open_faults: number;
      pending_work_orders: number;
      compliance_issues: number;
    }[];
    totals: {
      total_vessels: number;
      operational_vessels: number;
      total_open_faults: number;
      total_pending_work_orders: number;
      vessels_with_compliance_issues: number;
    };
  };
  actions?: MicroAction[];
}

export function FleetSummaryCard({ fleetData, actions = [] }: FleetSummaryCardProps) {
  const operationalRate =
    fleetData.totals.total_vessels > 0
      ? (fleetData.totals.operational_vessels / fleetData.totals.total_vessels) * 100
      : 0;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'maintenance':
        return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Fleet Icon */}
        <div className="mt-1 text-primary">
          <Ship className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Fleet Name */}
          <div className="mb-3">
            <h3 className="font-medium text-foreground">
              {fleetData.fleet_name || 'Fleet Overview'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {fleetData.totals.total_vessels} vessels
            </p>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-xs text-muted-foreground">Operational</p>
              <p className="text-lg font-bold text-green-600">
                {operationalRate.toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className="text-sm">
                <span className="font-medium text-green-600">
                  {fleetData.totals.operational_vessels}
                </span>
                {' / '}
                <span className="text-muted-foreground">
                  {fleetData.totals.total_vessels}
                </span>
              </p>
            </div>
          </div>

          {/* Alerts */}
          {(fleetData.totals.total_open_faults > 0 ||
            fleetData.totals.vessels_with_compliance_issues > 0) && (
            <div className="space-y-2 mb-3">
              {fleetData.totals.total_open_faults > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-orange-600 bg-orange-50 border border-orange-200 rounded p-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span>{fleetData.totals.total_open_faults} open faults</span>
                </div>
              )}
              {fleetData.totals.vessels_with_compliance_issues > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span>
                    {fleetData.totals.vessels_with_compliance_issues} vessel(s) with compliance issues
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Vessel List */}
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
              Vessels
            </p>
            <ul className="space-y-2">
              {fleetData.vessels.map((vessel) => (
                <li
                  key={vessel.yacht_id}
                  className="flex items-center justify-between text-sm border-b border-muted pb-2"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{vessel.yacht_name}</p>
                    <p className="text-xs text-muted-foreground">{vessel.location}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span
                      className={cn(
                        'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                        getStatusColor(vessel.status)
                      )}
                    >
                      {vessel.status}
                    </span>
                    {(vessel.open_faults > 0 || vessel.compliance_issues > 0) && (
                      <AlertTriangle className="h-4 w-4 text-orange-600" />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{}}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
