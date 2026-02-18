'use client';

/**
 * Equipment Lens Page — /equipment/[id]
 *
 * Full-screen equipment lens page using the new EquipmentLens component.
 * Follows the same pattern as the Work Order lens page.
 *
 * DATA FETCHING:
 * - Equipment details: viewEquipmentDetails() microaction
 * - Linked faults: viewLinkedFaults() microaction
 * - Maintenance history (work orders): viewEquipmentHistory() microaction
 *
 * NAVIGATION:
 * - onBack: router.back()
 * - onClose: router.push('/app')
 *
 * LEDGER:
 * - Logs view_equipment event on mount (fire-and-forget)
 *
 * FE-02-02: Equipment Lens Rebuild
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import {
  viewEquipmentDetails,
  viewLinkedFaults,
  viewEquipmentHistory,
} from '@/lib/microactions/handlers/equipment';
import type { ActionContext } from '@/lib/microactions/types';
import { Loader2, AlertTriangle } from 'lucide-react';
import { EquipmentLens, type EquipmentLensData } from '@/components/lens/EquipmentLens';
import type { LinkedFault, LinkedWorkOrder, MaintenanceHistoryEntry } from '@/components/lens/sections/equipment';

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function EquipmentLensPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  const [equipment, setEquipment] = useState<EquipmentLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const equipmentId = params.id as string;

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetchEquipment = useCallback(async () => {
    if (!user?.yachtId) return;

    const context: ActionContext = {
      yacht_id: user.yachtId!,
      user_id: user.id,
      user_role: user.role || 'member',
      entity_id: equipmentId,
      entity_type: 'equipment',
    };

    try {
      // Fetch core equipment data + linked faults + maintenance history in parallel
      const [eqResult, faultsResult, historyResult] = await Promise.all([
        viewEquipmentDetails(context, { equipment_id: equipmentId }),
        viewLinkedFaults(context, { equipment_id: equipmentId, limit: 20 }),
        viewEquipmentHistory(context, { equipment_id: equipmentId, limit: 20 }),
      ]);

      if (!eqResult.success || !eqResult.data) {
        setError(
          (eqResult.error as { message?: string })?.message || 'Equipment not found'
        );
        setLoading(false);
        return;
      }

      // Type the raw equipment data
      const raw = (eqResult.data as { equipment: EquipmentLensData }).equipment;

      // Map linked faults
      const linkedFaults: LinkedFault[] = faultsResult.success && faultsResult.data
        ? ((faultsResult.data as { faults?: LinkedFault[] }).faults ?? []).map((f: LinkedFault) => ({
            id: f.id,
            title: f.title,
            severity: f.severity,
            status: f.status,
            created_at: f.created_at,
            reported_by: f.reported_by,
          }))
        : [];

      // Map work orders to maintenance history entries
      const rawWOs: LinkedWorkOrder[] = historyResult.success && historyResult.data
        ? (historyResult.data as { work_orders?: LinkedWorkOrder[] }).work_orders ?? []
        : [];

      const maintenanceHistory: MaintenanceHistoryEntry[] = rawWOs.map((wo) => ({
        id: wo.id,
        event_type: 'work_order',
        title: wo.title,
        performed_at: wo.created_at,
        work_order_id: wo.id,
        work_order_number: wo.wo_number,
      }));

      // Map work orders for LinkedWorkOrdersSection
      const linkedWorkOrders: LinkedWorkOrder[] = rawWOs.map((wo) => ({
        id: wo.id,
        wo_number: wo.wo_number,
        title: wo.title,
        status: wo.status,
        priority: wo.priority,
        assigned_to_name: wo.assigned_to_name,
        created_at: wo.created_at,
        due_date: wo.due_date,
      }));

      // Count open faults
      const openFaultsCount = linkedFaults.filter(
        (f) => f.status !== 'resolved'
      ).length;

      // Count active WOs
      const activeWoCount = linkedWorkOrders.filter(
        (wo) => !['completed', 'closed', 'cancelled'].includes(wo.status)
      ).length;

      const enriched: EquipmentLensData = {
        ...raw,
        faults: linkedFaults,
        open_faults_count: openFaultsCount,
        work_orders: linkedWorkOrders,
        active_wo_count: activeWoCount,
        maintenance_history: maintenanceHistory,
        documents: [], // Documents section placeholder — linked via link_document action
      };

      setEquipment(enriched);
      setLoading(false);

      // Fire-and-forget ledger log
      logViewEvent(equipmentId, user.yachtId!, raw.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load equipment');
      setLoading(false);
    }
  }, [equipmentId, user]);

  useEffect(() => {
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    fetchEquipment();
  }, [equipmentId, user, authLoading, bootstrapping, fetchEquipment]);

  // ---------------------------------------------------------------------------
  // Ledger logging — fire-and-forget
  // ---------------------------------------------------------------------------

  function logViewEvent(entityId: string, yachtId: string, entityName: string) {
    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

      // Do not block on this — no await
      fetch(`${API_BASE}/v1/ledger/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          yacht_id: yachtId,
          action: 'view_equipment',
          entity_type: 'equipment',
          entity_id: entityId,
          entity_label: entityName,
        }),
      }).catch(() => {
        // Ledger logging is best-effort — never propagate errors
      });
    } catch {
      // Ignore all ledger errors
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation handlers
  // ---------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleClose = useCallback(() => {
    router.push('/app');
  }, [router]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    fetchEquipment();
  }, [fetchEquipment]);

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-brand-interactive animate-spin mx-auto mb-4" />
          <p className="text-txt-secondary text-[14px]">Loading equipment...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------

  if (error) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-4">
        <div className="bg-surface-secondary rounded-lg p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-12 h-12 text-status-critical mx-auto mb-4" />
          <h2 className="text-[20px] font-semibold text-txt-primary mb-2">Error</h2>
          <p className="text-txt-secondary text-[14px] mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-4 py-2 bg-brand-interactive hover:bg-brand-hover text-white rounded-lg transition-colors text-[14px]"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Null check
  // ---------------------------------------------------------------------------

  if (!equipment) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <EquipmentLens
      equipment={equipment}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
