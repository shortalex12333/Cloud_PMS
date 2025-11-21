/**
 * FaultCard Component
 *
 * Displays a fault with relevant actions
 * Example integration with CreateWorkOrderModal
 */

'use client';

import { useState } from 'react';
import { AlertTriangle, Wrench } from 'lucide-react';
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface FaultCardProps {
  fault: {
    id: string;
    title: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    equipment_id: string;
    equipment_name: string;
    reported_at: string;
    reporter: string;
  };
  actions?: MicroAction[];
}

export function FaultCard({ fault, actions = [] }: FaultCardProps) {
  const [showCreateWO, setShowCreateWO] = useState(false);

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <>
      <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
        <div className="flex items-start gap-3">
          {/* Fault Icon */}
          <div className="mt-1 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title & Severity */}
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-medium text-foreground">{fault.title}</h3>
              <span
                className={cn(
                  'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                  getSeverityColor(fault.severity)
                )}
              >
                {fault.severity}
              </span>
            </div>

            {/* Equipment */}
            <p className="text-sm text-muted-foreground mb-1">
              <span className="font-medium">Equipment:</span> {fault.equipment_name}
            </p>

            {/* Description */}
            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
              {fault.description}
            </p>

            {/* Reporter & Date */}
            <p className="text-xs text-muted-foreground mb-3">
              Reported by <span className="font-medium">{fault.reporter}</span> on{' '}
              {new Date(fault.reported_at).toLocaleDateString()}
            </p>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              {/* PRIMARY ACTION: Create Work Order (custom button with modal) */}
              <button
                onClick={() => setShowCreateWO(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Wrench className="h-3.5 w-3.5" />
                Create Work Order
              </button>

              {/* OTHER ACTIONS: Use ActionButton component */}
              {actions
                .filter((action) => action !== 'create_work_order') // Already shown above
                .map((action) => (
                  <ActionButton
                    key={action}
                    action={action}
                    context={{
                      fault_id: fault.id,
                      equipment_id: fault.equipment_id,
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

      {/* Create Work Order Modal */}
      <CreateWorkOrderModal
        open={showCreateWO}
        onOpenChange={setShowCreateWO}
        context={{
          equipment_id: fault.equipment_id,
          equipment_name: fault.equipment_name,
          fault_id: fault.id,
          fault_description: fault.description,
          suggested_title: `Fix: ${fault.title}`,
        }}
        onSuccess={(workOrderId: string) => {
          console.log('Work order created:', workOrderId);
          // Optionally: refresh data, navigate to WO, etc.
        }}
      />
    </>
  );
}

/**
 * Example Usage:
 *
 * ```tsx
 * <FaultCard
 *   fault={{
 *     id: '123',
 *     title: 'Hydraulic pump leaking',
 *     description: 'Discovered oil leak from main hydraulic pump during routine inspection.',
 *     severity: 'high',
 *     equipment_id: '456',
 *     equipment_name: 'Main Hydraulic Pump #1',
 *     reported_at: '2025-11-20T14:30:00Z',
 *     reporter: 'John Smith (Chief Engineer)',
 *   }}
 *   actions={[
 *     'diagnose_fault',
 *     'suggest_parts',
 *     'add_to_handover',
 *     'attach_photo',
 *     'add_note',
 *   ]}
 * />
 * ```
 */
