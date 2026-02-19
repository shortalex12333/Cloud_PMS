'use client';

/**
 * Equipment Situation View
 *
 * Equipment viewing environment per situation framework.
 * Displays equipment details, status, and available actions based on permissions.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { X, Wrench, AlertTriangle, Plus, Loader2, Clock, MapPin, FileText, RefreshCw } from 'lucide-react';
import type { SituationContext } from '@/types/situation';
import { useEquipmentActions, useEquipmentPermissions } from '@/hooks/useEquipmentActions';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

export interface EquipmentSituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

interface EquipmentData {
  id: string;
  name: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  status: string;
  location?: string;
  running_hours?: number;
  last_service_date?: string;
  next_service_date?: string;
  notes?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function EquipmentSituationView({
  situation,
  onClose,
  onAction,
}: EquipmentSituationViewProps) {
  const [equipment, setEquipment] = useState<EquipmentData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const equipmentId = situation.primary_entity_id;
  const metadata = situation.evidence as any;
  const equipmentTitle = metadata?.title || metadata?.name || 'Equipment';

  const { isLoading: actionLoading, createWorkOrder, reportFault, logHours } = useEquipmentActions(equipmentId);
  const permissions = useEquipmentPermissions();

  /**
   * Load equipment data on mount
   */
  useEffect(() => {
    async function loadEquipment() {
      setIsLoading(true);
      setError(null);

      try {
        const { data, error: fetchError } = await supabase
          .from('pms_equipment')
          .select('*')
          .eq('id', equipmentId)
          .single();

        if (fetchError) {
          console.error('[EquipmentSituationView] Fetch error:', fetchError);
          setError(fetchError.message);
          return;
        }

        if (!data) {
          setError('Equipment not found');
          return;
        }

        setEquipment(data);
      } catch (err) {
        console.error('[EquipmentSituationView] Load error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    if (equipmentId) {
      loadEquipment();
    }
  }, [equipmentId]);

  /**
   * Handle create work order
   */
  const handleCreateWorkOrder = useCallback(async () => {
    const result = await createWorkOrder(equipmentId);
    if (result.success) {
      if (onAction) {
        onAction('work_order_created', result.data);
      }
      alert('Work order created successfully');
    } else {
      alert(`Failed to create work order: ${result.error}`);
    }
  }, [createWorkOrder, equipmentId, onAction]);

  /**
   * Handle report fault
   */
  const handleReportFault = useCallback(async () => {
    const result = await reportFault(equipmentId);
    if (result.success) {
      if (onAction) {
        onAction('fault_reported', result.data);
      }
      alert('Fault reported successfully');
    } else {
      alert(`Failed to report fault: ${result.error}`);
    }
  }, [reportFault, equipmentId, onAction]);

  /**
   * Handle log hours
   */
  const handleLogHours = useCallback(async () => {
    const hoursInput = prompt('Enter running hours reading:');
    if (!hoursInput) return;

    const hours = parseFloat(hoursInput);
    if (isNaN(hours)) {
      alert('Please enter a valid number');
      return;
    }

    const result = await logHours(equipmentId, hours);
    if (result.success) {
      if (onAction) {
        onAction('hours_logged', result.data);
      }
      alert('Hours logged successfully');
    } else {
      alert(`Failed to log hours: ${result.error}`);
    }
  }, [logHours, equipmentId, onAction]);

  /**
   * Get status badge color
   */
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'operational':
      case 'active':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'maintenance':
      case 'in_maintenance':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'fault':
      case 'faulty':
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'inactive':
      case 'decommissioned':
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    }
  };

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
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-blue-50 dark:bg-blue-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500 rounded-lg">
                <Wrench className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="typo-title font-semibold text-zinc-900 dark:text-zinc-100">
                  {equipment?.name || equipmentTitle}
                </h2>
                {equipment?.manufacturer && (
                  <p className="typo-body text-zinc-500 dark:text-zinc-400">
                    {equipment.manufacturer} {equipment.model && `- ${equipment.model}`}
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
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading equipment...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Failed to load equipment</span>
                </div>
                <p className="mt-2 text-zinc-600 dark:text-zinc-400 typo-body">{error}</p>
              </div>
            )}

            {!isLoading && !error && equipment && (
              <div className="space-y-6">
                {/* Status Badge */}
                <div className="flex items-center gap-3">
                  <span className="typo-body text-zinc-500 dark:text-zinc-400">Status:</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(equipment.status)}`}>
                    {equipment.status || 'Unknown'}
                  </span>
                </div>

                {/* Key Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {equipment.serial_number && (
                    <div className="flex items-start gap-2">
                      <FileText className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Serial Number</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{equipment.serial_number}</p>
                      </div>
                    </div>
                  )}

                  {equipment.location && (
                    <div className="flex items-start gap-2">
                      <MapPin className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Location</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{equipment.location}</p>
                      </div>
                    </div>
                  )}

                  {equipment.running_hours !== undefined && (
                    <div className="flex items-start gap-2">
                      <Clock className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Running Hours</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">{equipment.running_hours.toLocaleString()} hrs</p>
                      </div>
                    </div>
                  )}

                  {equipment.last_service_date && (
                    <div className="flex items-start gap-2">
                      <RefreshCw className="h-4 w-4 text-zinc-400 mt-0.5" />
                      <div>
                        <p className="typo-meta text-zinc-500 dark:text-zinc-400">Last Service</p>
                        <p className="typo-body text-zinc-900 dark:text-zinc-100">
                          {new Date(equipment.last_service_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Notes */}
                {equipment.notes && (
                  <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4">
                    <p className="typo-meta text-zinc-500 dark:text-zinc-400 mb-2">Notes</p>
                    <p className="typo-body text-zinc-700 dark:text-zinc-300">{equipment.notes}</p>
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
              {permissions.canLogHours && (
                <button
                  onClick={handleLogHours}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-zinc-100 dark:bg-zinc-700 hover:bg-zinc-200 dark:hover:bg-zinc-600 rounded-lg transition-colors text-zinc-700 dark:text-zinc-300"
                >
                  <Clock className="h-4 w-4" />
                  Log Hours
                </button>
              )}

              {permissions.canReportFault && (
                <button
                  onClick={handleReportFault}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 rounded-lg transition-colors text-amber-700 dark:text-amber-400"
                >
                  <AlertTriangle className="h-4 w-4" />
                  Report Fault
                </button>
              )}

              {permissions.canCreateWorkOrder && (
                <button
                  onClick={handleCreateWorkOrder}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors text-white"
                >
                  <Plus className="h-4 w-4" />
                  Create Work Order
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
