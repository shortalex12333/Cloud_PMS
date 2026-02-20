'use client';

/**
 * Work Order Situation View
 *
 * Work order viewing environment per situation framework.
 * Displays work order details, status, and available actions based on permissions.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { X, ClipboardList, AlertTriangle, Play, CheckCircle, Loader2, Calendar, User, Wrench, MessageSquare } from 'lucide-react';
import type { SituationContext } from '@/types/situation';
import { useWorkOrderActions, useWorkOrderPermissions } from '@/hooks/useWorkOrderActions';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

export interface WorkOrderSituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

interface WorkOrderData {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority?: string;
  equipment_id?: string;
  equipment_name?: string;
  assigned_to?: string;
  assigned_to_name?: string;
  due_date?: string;
  created_at: string;
  completed_at?: string;
  notes?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function WorkOrderSituationView({
  situation,
  onClose,
  onAction,
}: WorkOrderSituationViewProps) {
  const [workOrder, setWorkOrder] = useState<WorkOrderData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const workOrderId = situation.primary_entity_id;
  const metadata = situation.evidence as any;
  const workOrderTitle = metadata?.title || metadata?.name || 'Work Order';

  const { isLoading: actionLoading, startWorkOrder, closeWorkOrder, addNote } = useWorkOrderActions(workOrderId);
  const permissions = useWorkOrderPermissions();

  /**
   * Load work order data on mount
   */
  useEffect(() => {
    async function loadWorkOrder() {
      setIsLoading(true);
      setError(null);

      try {
        const { data, error: fetchError } = await supabase
          .from('pms_work_orders')
          .select(`
            *,
            pms_equipment (name)
          `)
          .eq('id', workOrderId)
          .single();

        if (fetchError) {
          console.error('[WorkOrderSituationView] Fetch error:', fetchError);
          setError(fetchError.message);
          return;
        }

        if (!data) {
          setError('Work order not found');
          return;
        }

        setWorkOrder({
          ...data,
          equipment_name: data.pms_equipment?.name,
        });
      } catch (err) {
        console.error('[WorkOrderSituationView] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    if (workOrderId) {
      loadWorkOrder();
    }
  }, [workOrderId]);

  /**
   * Handle start work order
   */
  const handleStart = useCallback(async () => {
    const result = await startWorkOrder();
    if (result.success) {
      if (onAction) {
        onAction('work_order_started', result.data);
      }
      setWorkOrder((prev) => prev ? { ...prev, status: 'in_progress' } : null);
    } else {
      alert(`Failed to start work order: ${result.error}`);
    }
  }, [startWorkOrder, onAction]);

  /**
   * Handle complete work order
   */
  const handleComplete = useCallback(async () => {
    const notes = prompt('Enter completion notes (optional):');
    const result = await closeWorkOrder(notes || undefined);
    if (result.success) {
      if (onAction) {
        onAction('work_order_completed', result.data);
      }
      setWorkOrder((prev) => prev ? { ...prev, status: 'completed' } : null);
    } else {
      alert(`Failed to complete work order: ${result.error}`);
    }
  }, [closeWorkOrder, onAction]);

  /**
   * Handle add note
   */
  const handleAddNote = useCallback(async () => {
    const noteText = prompt('Enter note:');
    if (!noteText) return;

    const result = await addNote(noteText);
    if (result.success) {
      if (onAction) {
        onAction('note_added', result.data);
      }
      alert('Note added successfully');
    } else {
      alert(`Failed to add note: ${result.error}`);
    }
  }, [addNote, onAction]);

  /**
   * Get status badge color
   */
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'pending':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'in_progress':
      case 'active':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'completed':
      case 'closed':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'cancelled':
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
      case 'overdue':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      default:
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
    }
  };

  /**
   * Get priority badge color
   */
  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'critical':
      case 'urgent':
        return 'bg-red-500/20 text-red-400';
      case 'high':
        return 'bg-orange-500/20 text-orange-400';
      case 'medium':
      case 'normal':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'low':
        return 'bg-green-500/20 text-green-400';
      default:
        return 'bg-zinc-500/20 text-zinc-400';
    }
  };

  const canStart = workOrder?.status === 'open' || workOrder?.status === 'pending';
  const canComplete = workOrder?.status === 'in_progress';

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[8vh] pb-8 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl mx-4">
        <div className="bg-white dark:bg-zinc-900 rounded-celeste-lg shadow-modal overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-amber-50 dark:bg-amber-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500 rounded-lg">
                <ClipboardList className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="typo-title font-semibold text-zinc-900 dark:text-zinc-100">
                  {workOrder?.title || workOrderTitle}
                </h2>
                {workOrder?.equipment_name && (
                  <p className="typo-body text-zinc-500 dark:text-zinc-400">
                    Equipment: {workOrder.equipment_name}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-5">
            {isLoading && (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
                <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading work order...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Failed to load work order</span>
                </div>
                <p className="mt-2 text-zinc-600 dark:text-zinc-400 typo-body">{error}</p>
              </div>
            )}

            {!isLoading && !error && workOrder && (
              <div className="space-y-6">
                {/* Status and Priority */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="typo-body text-zinc-500 dark:text-zinc-400">Status:</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(workOrder.status)}`}>
                      {workOrder.status || 'Unknown'}
                    </span>
                  </div>
                  {workOrder.priority && (
                    <div className="flex items-center gap-2">
                      <span className="typo-body text-zinc-500 dark:text-zinc-400">Priority:</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(workOrder.priority)}`}>
                        {workOrder.priority}
                      </span>
                    </div>
                  )}
                </div>

                {/* Description */}
                {workOrder.description && (
                  <div>
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400 mb-2">Description</p>
                    <p className="typo-body text-zinc-700 dark:text-zinc-300">{workOrder.description}</p>
                  </div>
                )}

                {/* Key Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {workOrder.assigned_to_name && (
                    <div className="flex items-start gap-2">
                      <User className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Assigned To</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{workOrder.assigned_to_name}</p>
                      </div>
                    </div>
                  )}

                  {workOrder.due_date && (
                    <div className="flex items-start gap-2">
                      <Calendar className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Due Date</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">
                          {new Date(workOrder.due_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  )}

                  {workOrder.equipment_name && (
                    <div className="flex items-start gap-2">
                      <Wrench className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Equipment</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{workOrder.equipment_name}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-start gap-2">
                    <Calendar className="h-4 w-4 text-zinc-400 mt-0.5" />
                    <div>
                      <p className="typo-meta text-zinc-500 dark:text-zinc-400">Created</p>
                      <p className="typo-body text-zinc-900 dark:text-zinc-100">
                        {new Date(workOrder.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Notes */}
                {workOrder.notes && (
                  <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4">
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400 mb-2">Notes</p>
                    <p className="typo-body text-zinc-700 dark:text-zinc-300">{workOrder.notes}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
            <button
              onClick={onClose}
              className="px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
            >
              Close
            </button>

            <div className="flex items-center gap-2">
              {permissions.canAddNote && (
                <button
                  onClick={handleAddNote}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-zinc-100 dark:bg-zinc-700 hover:bg-zinc-200 dark:hover:bg-zinc-600 rounded-lg transition-colors text-zinc-700 dark:text-zinc-300"
                >
                  <MessageSquare className="h-4 w-4" />
                  Add Note
                </button>
              )}

              {permissions.canStart && canStart && (
                <button
                  onClick={handleStart}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors text-white"
                >
                  <Play className="h-4 w-4" />
                  Start Work
                </button>
              )}

              {permissions.canClose && canComplete && (
                <button
                  onClick={handleComplete}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors text-white"
                >
                  <CheckCircle className="h-4 w-4" />
                  Complete
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
