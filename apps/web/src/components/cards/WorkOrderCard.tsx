/**
 * WorkOrderCard Component
 *
 * Apple-inspired design with:
 * - Status dot indicator (not pill badge)
 * - 12px card radius
 * - Subtle shadows
 * - Precise typography
 */

'use client';

import { Wrench, Clock, User, CheckCircle2, ChevronRight } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { RelatedEmailsPanel } from '@/components/email/RelatedEmailsPanel';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface WorkOrderCardProps {
  workOrder: {
    id: string;
    title: string;
    description: string;
    status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
    priority: 'low' | 'medium' | 'high' | 'urgent';
    equipment_id?: string;
    equipment_name?: string;
    assigned_to?: string;
    assigned_to_name?: string;
    created_at: string;
    completed_at?: string;
    due_date?: string;
  };
  actions?: MicroAction[];
}

export function WorkOrderCard({ workOrder, actions = [] }: WorkOrderCardProps) {
  // Get status styling (Apple-style: dot + badge)
  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          dot: 'celeste-dot-success',
          badge: 'celeste-badge-success',
          icon: <CheckCircle2 className="h-4 w-4 text-[--system-green]" />,
          label: 'Completed',
        };
      case 'in_progress':
        return {
          dot: 'celeste-dot-info',
          badge: 'celeste-badge-info',
          icon: <Clock className="h-4 w-4 text-[--system-blue]" />,
          label: 'In Progress',
        };
      case 'cancelled':
        return {
          dot: 'celeste-dot-low',
          badge: 'celeste-badge-low',
          icon: <Wrench className="h-4 w-4 text-zinc-400" />,
          label: 'Cancelled',
        };
      default:
        return {
          dot: 'celeste-dot-medium',
          badge: 'celeste-badge-medium',
          icon: <Wrench className="h-4 w-4 text-amber-500" />,
          label: 'Pending',
        };
    }
  };

  // Get priority styling
  const getPriorityStyles = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return { badge: 'celeste-badge-critical', label: 'Urgent' };
      case 'high':
        return { badge: 'celeste-badge-high', label: 'High' };
      case 'medium':
        return { badge: 'celeste-badge-medium', label: 'Medium' };
      default:
        return { badge: 'celeste-badge-low', label: 'Low' };
    }
  };

  const status = getStatusStyles(workOrder.status);
  const priority = getPriorityStyles(workOrder.priority);

  return (
    <div className="celeste-card p-4 hover:shadow-[var(--shadow-md)] transition-shadow duration-200">
      <div className="flex items-start gap-3">
        {/* Status Indicator - Minimal dot + icon */}
        <div className="flex flex-col items-center gap-2 pt-0.5">
          <span className={cn('celeste-dot', status.dot)} />
          {status.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title Row */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 truncate">
              {workOrder.title}
            </h3>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className={cn('celeste-badge', status.badge)}>
                {status.label}
              </span>
              <span className={cn('celeste-badge', priority.badge)}>
                {priority.label}
              </span>
            </div>
          </div>

          {/* Equipment - Subtle secondary text */}
          {workOrder.equipment_name && (
            <p className="text-[13px] text-zinc-500 dark:text-zinc-400 mb-2">
              {workOrder.equipment_name}
            </p>
          )}

          {/* Description - Truncated */}
          <p className="text-[14px] text-zinc-600 dark:text-zinc-300 line-clamp-2 mb-3">
            {workOrder.description}
          </p>

          {/* Assigned To */}
          {workOrder.assigned_to_name && (
            <div className="flex items-center gap-1.5 text-[13px] text-zinc-500 dark:text-zinc-400 mb-2">
              <User className="h-3.5 w-3.5" />
              <span>{workOrder.assigned_to_name}</span>
            </div>
          )}

          {/* Metadata Row */}
          <div className="flex items-center gap-3 text-[12px] text-zinc-400 dark:text-zinc-500 mb-4">
            <span>{formatDate(workOrder.created_at)}</span>
            {workOrder.due_date && (
              <span className="text-[--system-orange] font-medium">
                Due: {formatDate(workOrder.due_date)}
              </span>
            )}
            {workOrder.completed_at && (
              <span className="text-[--system-green]">
                Completed: {formatDate(workOrder.completed_at)}
              </span>
            )}
          </div>

          {/* Actions - Apple-style buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {actions.slice(0, 3).map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{
                  work_order_id: workOrder.id,
                  equipment_id: workOrder.equipment_id,
                }}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}

            {/* More indicator */}
            {actions.length > 3 && (
              <button className="h-8 px-2 text-[13px] text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Related Emails - Evidence panel */}
          <RelatedEmailsPanel
            objectType="work_order"
            objectId={workOrder.id}
            className="mt-4"
          />
        </div>
      </div>
    </div>
  );
}
