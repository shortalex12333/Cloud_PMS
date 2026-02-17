'use client';

/**
 * =============================================================================
 * WORK ORDER LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-05
 * UPDATED: 2026-02-17 (FE-01-01) — Refactored to use WorkOrderLens component
 *
 * PURPOSE: Full-page lens for work order entities accessed via handover export links
 *
 * HANDOVER EXPORT FLOW:
 * ---------------------
 * 1. User clicks link in handover PDF/HTML: https://app.celeste7.ai/open?t=<JWS_TOKEN>
 * 2. /open page resolves token via POST /api/v1/open/resolve (handover-export service on Render)
 * 3. Token returns: { focus: { type: "work_order", id: "uuid" }, yacht_id, scope }
 * 4. /open page redirects to this lens: /work-orders/{id}
 * 5. This page fetches full work order data and renders it
 *
 * ALTERNATIVE FLOW (direct deep link):
 * ------------------------------------
 * 1. URL: /app?entity=work_order&id=uuid
 * 2. DeepLinkHandler.tsx intercepts and redirects to /work-orders/{id}
 *
 * DATA FETCHING:
 * --------------
 * - Uses microaction handler: viewWorkOrder() from @/lib/microactions/handlers/workOrders
 * - Requires ActionContext with yacht_id (from useAuth bootstrap)
 * - Queries Supabase table: pms_work_orders
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/WorkOrderLens.tsx — Lens component (reference implementation)
 * - /src/components/lens/LensHeader.tsx — Fixed header component
 * - /src/lib/microactions/handlers/workOrders.ts — Data fetching logic
 * - /src/app/open/page.tsx — Token resolution (redirects here)
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewWorkOrder } from '@/lib/microactions/handlers/workOrders';
import type { ActionContext } from '@/lib/microactions/types';
import { WorkOrderLens, type WorkOrderLensData } from '@/components/lens/WorkOrderLens';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

// ---------------------------------------------------------------------------
// LEDGER LOGGING
// Logs navigation events to pms_audit_log via backend API.
// Per CLAUDE.md: Every user action logged to ledger. Every navigate — all of it.
// ---------------------------------------------------------------------------
const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

async function logNavigationEvent(
  eventName: string,
  payload: Record<string, unknown>
): Promise<void> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) return;

    await fetch(`${RENDER_API_URL}/v1/ledger/record`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_name: eventName, payload }),
    });
  } catch {
    // Navigation logging is fire-and-forget — never block UX on failure
  }
}

export default function WorkOrderLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [workOrder, setWorkOrder] = useState<WorkOrderLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract work order ID from URL: /work-orders/[id]
  const workOrderId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    const fetchWorkOrder = async () => {
      try {
        const context: ActionContext = {
          yacht_id: user.yachtId!,
          user_id: user.id,
          user_role: user.role || 'member',
          entity_id: workOrderId,
          entity_type: 'work_order',
        };

        const result = await viewWorkOrder(context, { work_order_id: workOrderId });

        if (!result.success || !result.data) {
          setError(result.error?.message || 'Work order not found');
          setLoading(false);
          return;
        }

        // Map the raw handler result to WorkOrderLensData shape
        const raw = (result.data as { work_order: Record<string, unknown> }).work_order;
        const data: WorkOrderLensData = {
          id: raw.id as string,
          wo_number: raw.wo_number as string | undefined,
          title: raw.title as string,
          description: raw.description as string | undefined,
          status: raw.status as string,
          priority: raw.priority as string,
          equipment_id: raw.equipment_id as string | undefined,
          equipment_name: raw.equipment_name as string | undefined,
          assigned_to: raw.assigned_to as string | undefined,
          assigned_to_name: raw.assigned_to_name as string | undefined,
          created_at: raw.created_at as string,
          completed_at: raw.completed_at as string | undefined,
          due_date: raw.due_date as string | undefined,
          is_overdue: raw.is_overdue as boolean | undefined,
          days_open: raw.days_open as number | undefined,
          parts_count: raw.parts_count as number | undefined,
        };

        setWorkOrder(data);
        setLoading(false);

        // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
        logNavigationEvent('navigate_to_lens', {
          entity_type: 'work_order',
          entity_id: workOrderId,
          wo_number: data.wo_number,
          title: data.title,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load work order');
        setLoading(false);
      }
    };

    fetchWorkOrder();
  }, [workOrderId, user, authLoading, bootstrapping]);

  // ---------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading work order...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-4">
        <div className="bg-surface-primary rounded-[var(--radius-md)] p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-10 h-10 text-status-critical mx-auto mb-4" />
          <h2 className="text-[18px] font-semibold text-txt-primary mb-2">
            Unable to load work order
          </h2>
          <p className="text-[14px] text-txt-secondary mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-6 py-3 bg-brand-interactive hover:bg-brand-hover text-txt-inverse text-[14px] font-semibold rounded-[var(--radius-sm)] transition-colors duration-[120ms] ease-out"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // NULL CHECK
  // ---------------------------------------------------------------------------
  if (!workOrder) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Log to ledger before navigating
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'work_order',
      entity_id: workOrderId,
    });
    router.back();
  }, [workOrderId, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: 'work_order',
      entity_id: workOrderId,
    });
    router.push('/app');
  }, [workOrderId, router]);

  // ---------------------------------------------------------------------------
  // RENDER — Delegate entirely to WorkOrderLens component
  // ---------------------------------------------------------------------------
  return (
    <WorkOrderLens
      workOrder={workOrder}
      onBack={handleBack}
      onClose={handleClose}
    />
  );
}
