'use client';

/**
 * Fault Situation View
 *
 * Fault/defect viewing environment per situation framework.
 * Displays fault details, status, and available actions based on permissions.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { X, AlertTriangle, CheckCircle, Loader2, Calendar, Wrench, MessageSquare, Camera, Search, RotateCcw } from 'lucide-react';
import type { SituationContext } from '@/types/situation';
import { useFaultActions, useFaultPermissions } from '@/hooks/useFaultActions';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

export interface FaultSituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

interface FaultData {
  id: string;
  fault_code?: string;
  title: string;
  description?: string;
  severity: 'cosmetic' | 'minor' | 'major' | 'critical' | 'safety';
  status: 'open' | 'investigating' | 'work_ordered' | 'resolved' | 'closed' | 'deferred';
  equipment_id?: string;
  equipment_name?: string;
  work_order_id?: string;
  work_order_title?: string;
  detected_at: string;
  resolved_at?: string;
  resolved_by?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function FaultSituationView({
  situation,
  onClose,
  onAction,
}: FaultSituationViewProps) {
  const [fault, setFault] = useState<FaultData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const faultId = situation.primary_entity_id;
  const metadata = situation.evidence as any;
  const faultTitle = metadata?.title || metadata?.name || 'Fault';

  const { isLoading: actionLoading, acknowledgeFault, closeFault, diagnoseFault, reopenFault, addNote } = useFaultActions(faultId);
  const permissions = useFaultPermissions();

  /**
   * Load fault data on mount
   */
  useEffect(() => {
    async function loadFault() {
      setIsLoading(true);
      setError(null);

      try {
        const { data, error: fetchError } = await supabase
          .from('pms_faults')
          .select(`
            *,
            pms_equipment (name),
            pms_work_orders (title)
          `)
          .eq('id', faultId)
          .is('deleted_at', null)
          .single();

        if (fetchError) {
          console.error('[FaultSituationView] Fetch error:', fetchError);
          setError(fetchError.message);
          return;
        }

        if (!data) {
          setError('Fault not found');
          return;
        }

        setFault({
          ...data,
          equipment_name: data.pms_equipment?.name,
          work_order_title: data.pms_work_orders?.title,
        });
      } catch (err) {
        console.error('[FaultSituationView] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    if (faultId) {
      loadFault();
    }
  }, [faultId]);

  /**
   * Handle acknowledge fault
   */
  const handleAcknowledge = useCallback(async () => {
    const result = await acknowledgeFault();
    if (result.success) {
      if (onAction) {
        onAction('fault_acknowledged', result.data);
      }
      setFault((prev) => prev ? { ...prev, status: 'investigating' } : null);
      alert('Fault acknowledged');
    } else {
      alert(`Failed to acknowledge fault: ${result.error}`);
    }
  }, [acknowledgeFault, onAction]);

  /**
   * Handle close fault
   */
  const handleClose = useCallback(async () => {
    const notes = prompt('Enter resolution notes:');
    if (!notes) return;

    const result = await closeFault(notes);
    if (result.success) {
      if (onAction) {
        onAction('fault_closed', result.data);
      }
      setFault((prev) => prev ? { ...prev, status: 'closed' } : null);
      alert('Fault closed');
    } else {
      alert(`Failed to close fault: ${result.error}`);
    }
  }, [closeFault, onAction]);

  /**
   * Handle diagnose fault
   */
  const handleDiagnose = useCallback(async () => {
    const diagnosis = prompt('Enter diagnosis/root cause:');
    if (!diagnosis) return;

    const recommendedAction = prompt('Enter recommended action (optional):');
    const result = await diagnoseFault(diagnosis, recommendedAction || undefined);

    if (result.success) {
      if (onAction) {
        onAction('fault_diagnosed', result.data);
      }
      alert('Diagnosis recorded');
    } else {
      alert(`Failed to record diagnosis: ${result.error}`);
    }
  }, [diagnoseFault, onAction]);

  /**
   * Handle reopen fault
   */
  const handleReopen = useCallback(async () => {
    const reason = prompt('Enter reason for reopening:');
    if (!reason) return;

    const result = await reopenFault(reason);
    if (result.success) {
      if (onAction) {
        onAction('fault_reopened', result.data);
      }
      setFault((prev) => prev ? { ...prev, status: 'open' } : null);
      alert('Fault reopened');
    } else {
      alert(`Failed to reopen fault: ${result.error}`);
    }
  }, [reopenFault, onAction]);

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
   * Get severity badge color
   */
  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'safety':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'major':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'minor':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'cosmetic':
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
      default:
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
    }
  };

  /**
   * Get status badge color
   */
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'open':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'investigating':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'work_ordered':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'resolved':
      case 'closed':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'deferred':
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
      default:
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
    }
  };

  const isOpen = fault?.status === 'open';
  const isClosed = fault?.status === 'closed' || fault?.status === 'resolved';
  const canClose = !isClosed && fault?.status !== 'deferred';

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
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="typo-title font-semibold text-zinc-900 dark:text-zinc-100">
                  {fault?.title || faultTitle}
                </h2>
                {fault?.fault_code && (
                  <p className="typo-body text-zinc-500 dark:text-zinc-400">
                    Code: {fault.fault_code}
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
                <Loader2 className="h-8 w-8 animate-spin text-red-500" />
                <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading fault...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Failed to load fault</span>
                </div>
                <p className="mt-2 text-zinc-600 dark:text-zinc-400 typo-body">{error}</p>
              </div>
            )}

            {!isLoading && !error && fault && (
              <div className="space-y-6">
                {/* Status and Severity */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="typo-body text-zinc-500 dark:text-zinc-400">Status:</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(fault.status)}`}>
                      {fault.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="typo-body text-zinc-500 dark:text-zinc-400">Severity:</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(fault.severity)}`}>
                      {fault.severity}
                    </span>
                  </div>
                </div>

                {/* Description */}
                {fault.description && (
                  <div>
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400 mb-2">Description</p>
                    <p className="typo-body text-zinc-700 dark:text-zinc-300">{fault.description}</p>
                  </div>
                )}

                {/* Key Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {fault.equipment_name && (
                    <div className="flex items-start gap-2">
                      <Wrench className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Equipment</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{fault.equipment_name}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-start gap-2">
                    <Calendar className="h-4 w-4 text-zinc-400 mt-0.5" />
                    <div>
                      <p className="typo-meta text-zinc-500 dark:text-zinc-400">Detected</p>
                      <p className="typo-body text-zinc-900 dark:text-zinc-100">
                        {new Date(fault.detected_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {fault.work_order_title && (
                    <div className="flex items-start gap-2">
                      <Wrench className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Work Order</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{fault.work_order_title}</p>
                      </div>
                    </div>
                  )}

                  {fault.resolved_at && (
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Resolved</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">
                          {new Date(fault.resolved_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
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

              {permissions.canDiagnose && !isClosed && (
                <button
                  onClick={handleDiagnose}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 rounded-lg transition-colors text-blue-700 dark:text-blue-400"
                >
                  <Search className="h-4 w-4" />
                  Diagnose
                </button>
              )}

              {permissions.canAcknowledge && isOpen && (
                <button
                  onClick={handleAcknowledge}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 rounded-lg transition-colors text-amber-700 dark:text-amber-400"
                >
                  <CheckCircle className="h-4 w-4" />
                  Acknowledge
                </button>
              )}

              {permissions.canReopen && isClosed && (
                <button
                  onClick={handleReopen}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 rounded-lg transition-colors text-amber-700 dark:text-amber-400"
                >
                  <RotateCcw className="h-4 w-4" />
                  Reopen
                </button>
              )}

              {permissions.canClose && canClose && (
                <button
                  onClick={handleClose}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors text-white"
                >
                  <CheckCircle className="h-4 w-4" />
                  Close Fault
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
