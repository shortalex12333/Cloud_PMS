'use client';

/**
 * FaultLensPage — Full-page lens for fault entities.
 *
 * Replaces the old skeleton implementation with the FaultLens component,
 * following the same pattern as work-orders/[id]/page.tsx.
 *
 * FE-02-01: Fault Lens Rebuild
 *
 * Navigation flow:
 * 1. User arrives via /faults/{id} (deep link, handover export, or in-app nav)
 * 2. Page fetches fault data via viewFault microaction handler
 * 3. FaultLens renders in full-screen glass overlay
 * 4. onBack → router.back(); onClose → router.push('/app')
 * 5. Navigation event logged to ledger on open (fire-and-forget)
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewFault } from '@/lib/microactions/handlers/faults';
import type { ActionContext } from '@/lib/microactions/types';
import { FaultLens } from '@/components/lens/FaultLens';
import type { FaultLensData } from '@/components/lens/FaultLens';
import { Loader2, AlertTriangle } from 'lucide-react';

export default function FaultLensPage() {
  // ---------------------------------------------------------------------------
  // Routing + auth
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [fault, setFault] = useState<FaultLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const faultId = params.id as string;

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const fetchFault = useCallback(async () => {
    if (!user?.yachtId) return;

    setLoading(true);
    setError(null);

    try {
      const context: ActionContext = {
        yacht_id: user.yachtId,
        user_id: user.id,
        user_role: user.role || 'member',
        entity_id: faultId,
        entity_type: 'fault',
      };

      const result = await viewFault(context, { fault_id: faultId });

      if (!result.success || !result.data) {
        setError(result.error?.message || 'Fault not found');
        setLoading(false);
        return;
      }

      // viewFault returns { fault: FaultData, related_work_orders_count: number }
      const raw = (result.data as { fault: Record<string, unknown> }).fault;

      // Map raw DB row → FaultLensData
      const faultData: FaultLensData = {
        id: raw.id as string,
        fault_code: raw.fault_code as string | undefined,
        title: raw.title as string | undefined,
        description: raw.description as string | undefined,
        severity: (raw.severity as string) ?? 'minor',
        status: raw.status as string | undefined,
        acknowledged_at: raw.acknowledged_at as string | undefined,
        equipment_id: raw.equipment_id as string | undefined,
        equipment_name: raw.equipment_name as string | undefined,
        detected_at: raw.detected_at as string | undefined,
        created_at: raw.created_at as string,
        resolved_at: raw.resolved_at as string | undefined,
        // reporter_name: not yet denormalized from DB — future: join with users table
        reporter_name: undefined,
        days_open: raw.days_open as number | undefined,
        has_work_order: (result.data as { related_work_orders_count?: number })
          .related_work_orders_count
          ? (result.data as { related_work_orders_count: number }).related_work_orders_count > 0
          : false,
        // Notes, history, photos: not yet fetched in viewFault — future: hydrate separately
        notes: [],
        history: [],
        photos: [],
      };

      setFault(faultData);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load fault');
      setLoading(false);
    }
  }, [faultId, user]);

  useEffect(() => {
    // Wait for auth + bootstrap to complete
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    fetchFault();
  }, [faultId, user, authLoading, bootstrapping, fetchFault]);

  // ---------------------------------------------------------------------------
  // Log navigation event to ledger on open (fire-and-forget)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!fault || !user?.yachtId) return;

    const logNavigationEvent = async () => {
      try {
        const API_BASE =
          process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
        // fire-and-forget — never awaited in the component render path
        fetch(`${API_BASE}/v1/ledger/log`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            yacht_id: user.yachtId,
            event_type: 'navigate_to_lens',
            entity_type: 'fault',
            entity_id: fault.id,
            metadata: { fault_code: fault.fault_code },
          }),
        }).catch(() => {
          // Ignore ledger errors — never block navigation UX
        });
      } catch {
        // Ignore
      }
    };

    logNavigationEvent();
  }, [fault, user]);

  // ---------------------------------------------------------------------------
  // Navigation handlers
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleClose = useCallback(() => {
    router.push('/app');
  }, [router]);

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-brand-interactive animate-spin mx-auto mb-4" />
          <p className="text-txt-secondary text-[14px]">Loading fault report...</p>
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
        <div className="bg-surface-card rounded-lg p-8 max-w-md w-full text-center border border-surface-border">
          <AlertTriangle className="w-12 h-12 text-status-critical mx-auto mb-4" />
          <h2 className="text-[20px] font-semibold text-txt-primary mb-2">Error</h2>
          <p className="text-txt-secondary mb-6 text-[14px]">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-4 py-2 bg-brand-interactive hover:bg-brand-hover text-white rounded-md transition-colors text-[14px]"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Null guard
  // ---------------------------------------------------------------------------
  if (!fault) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // Render FaultLens
  // ---------------------------------------------------------------------------
  return (
    <FaultLens
      fault={fault}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={fetchFault}
    />
  );
}
