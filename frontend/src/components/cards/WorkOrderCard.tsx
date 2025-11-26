/**
 * WorkOrderCard Component
 *
 * Displays a work order with status, priority, and relevant actions
 */

'use client';

import { useState } from 'react';
import { Wrench, Clock, User, CheckCircle2 } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
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
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'in_progress':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'cancelled':
        return 'text-gray-700 bg-gray-50 border-gray-200';
      default:
        return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = () => {
    switch (workOrder.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'in_progress':
        return <Clock className="h-5 w-5 text-blue-600 animate-pulse" />;
      default:
        return <Wrench className="h-5 w-5 text-yellow-600" />;
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Status Icon */}
        <div className="mt-1">{getStatusIcon()}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{workOrder.title}</h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                getStatusColor(workOrder.status)
              )}
            >
              {workOrder.status}
            </span>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                getPriorityColor(workOrder.priority)
              )}
            >
              {workOrder.priority}
            </span>
          </div>

          {/* Equipment */}
          {workOrder.equipment_name && (
            <p className="text-sm text-muted-foreground mb-1">
              <span className="font-medium">Equipment:</span> {workOrder.equipment_name}
            </p>
          )}

          {/* Description */}
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {workOrder.description}
          </p>

          {/* Assigned To */}
          {workOrder.assigned_to_name && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-2">
              <User className="h-4 w-4" />
              <span>Assigned to: {workOrder.assigned_to_name}</span>
            </div>
          )}

          {/* Dates */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            <span>Created: {formatDate(workOrder.created_at)}</span>
            {workOrder.due_date && (
              <span className="text-orange-600 font-medium">
                Due: {formatDate(workOrder.due_date)}
              </span>
            )}
            {workOrder.completed_at && (
              <span className="text-green-600">
                Completed: {formatDate(workOrder.completed_at)}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
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
          </div>
        </div>
      </div>
    </div>
  );
}
