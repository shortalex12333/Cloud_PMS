/**
 * EquipmentCard Component
 *
 * Displays equipment details with maintenance history and actions
 */

'use client';

import { Settings, AlertCircle, Wrench, Calendar } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface EquipmentCardProps {
  equipment: {
    id: string;
    name: string;
    equipment_type: string;
    manufacturer?: string;
    model?: string;
    serial_number?: string;
    location: string;
    status: 'operational' | 'faulty' | 'maintenance' | 'offline';
    installation_date?: string;
    last_maintenance?: string;
    next_maintenance?: string;
    fault_count?: number;
    work_order_count?: number;
  };
  actions?: MicroAction[];
}

export function EquipmentCard({ equipment, actions = [] }: EquipmentCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'text-restricted-green bg-restricted-green/10 border-restricted-green/30';
      case 'maintenance':
        return 'text-celeste-accent bg-celeste-accent/10 border-celeste-accent/30';
      case 'faulty':
        return 'text-restricted-red bg-restricted-red/10 border-restricted-red/30';
      default:
        return 'text-celeste-text-muted bg-celeste-bg-secondary border-celeste-border';
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Equipment Icon */}
        <div className="mt-1 text-primary">
          <Settings className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Name & Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{equipment.name}</h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                getStatusColor(equipment.status)
              )}
            >
              {equipment.status}
            </span>
          </div>

          {/* Type & Model */}
          <p className="text-sm text-muted-foreground mb-1">
            <span className="font-medium">{equipment.equipment_type}</span>
            {equipment.manufacturer && ` · ${equipment.manufacturer}`}
            {equipment.model && ` ${equipment.model}`}
          </p>

          {/* Location */}
          <p className="text-sm text-muted-foreground mb-2">
            <span className="font-medium">Location:</span> {equipment.location}
          </p>

          {/* Serial Number */}
          {equipment.serial_number && (
            <p className="text-xs text-muted-foreground mb-2">
              S/N: {equipment.serial_number}
            </p>
          )}

          {/* Maintenance Info */}
          {equipment.last_maintenance && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-2">
              <Calendar className="h-4 w-4" />
              <span>Last maintained: {formatDate(equipment.last_maintenance)}</span>
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            {equipment.fault_count !== undefined && (
              <div className="flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5" />
                <span>{equipment.fault_count} faults</span>
              </div>
            )}
            {equipment.work_order_count !== undefined && (
              <div className="flex items-center gap-1">
                <Wrench className="h-3.5 w-3.5" />
                <span>{equipment.work_order_count} work orders</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{
                  equipment_id: equipment.id,
                }}
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
