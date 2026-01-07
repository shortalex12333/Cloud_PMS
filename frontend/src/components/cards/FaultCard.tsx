/**
 * FaultCard Component
 *
 * Apple-inspired design with:
 * - Status dot indicator (not pill badge)
 * - 12px card radius
 * - Subtle shadows
 * - Precise typography
 */

'use client';

import { useState } from 'react';
import { AlertTriangle, Wrench, ChevronRight } from 'lucide-react';
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

  // Get severity styling (Apple-style: subtle background, muted colors)
  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          dot: 'celeste-dot-critical',
          badge: 'celeste-badge-critical',
          label: 'Critical',
        };
      case 'high':
        return {
          dot: 'celeste-dot-high',
          badge: 'celeste-badge-high',
          label: 'High',
        };
      case 'medium':
        return {
          dot: 'celeste-dot-medium',
          badge: 'celeste-badge-medium',
          label: 'Medium',
        };
      default:
        return {
          dot: 'celeste-dot-low',
          badge: 'celeste-badge-low',
          label: 'Low',
        };
    }
  };

  const severity = getSeverityStyles(fault.severity);

  return (
    <>
      <div className="celeste-card p-4 hover:shadow-[var(--shadow-md)] transition-shadow duration-200">
        <div className="flex items-start gap-3">
          {/* Severity Indicator - Minimal dot + icon */}
          <div className="flex flex-col items-center gap-2 pt-0.5">
            <span className={cn('celeste-dot', severity.dot)} />
            <AlertTriangle className="h-4 w-4 text-zinc-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                {fault.title}
              </h3>
              <span className={cn('celeste-badge flex-shrink-0', severity.badge)}>
                {severity.label}
              </span>
            </div>

            {/* Equipment - Subtle secondary text */}
            <p className="text-[13px] text-zinc-500 dark:text-zinc-400 mb-2">
              {fault.equipment_name}
            </p>

            {/* Description - Truncated */}
            <p className="text-[14px] text-zinc-600 dark:text-zinc-300 line-clamp-2 mb-3">
              {fault.description}
            </p>

            {/* Metadata Row */}
            <p className="text-[12px] text-zinc-400 dark:text-zinc-500 mb-4">
              {fault.reporter} · {new Date(fault.reported_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
              })}
            </p>

            {/* Actions - Apple-style buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Primary Action */}
              <button
                onClick={() => setShowCreateWO(true)}
                className="celeste-button celeste-button-primary h-8 px-3 text-[13px]"
              >
                <Wrench className="h-3.5 w-3.5" />
                Create Work Order
              </button>

              {/* Secondary Actions */}
              {actions
                .filter((action) => action !== 'create_work_order')
                .slice(0, 2)
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

              {/* More indicator */}
              {actions.filter(a => a !== 'create_work_order').length > 2 && (
                <button className="h-8 px-2 text-[13px] text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
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
        onSuccess={(workOrderId) => {
          console.log('Work order created:', workOrderId);
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
