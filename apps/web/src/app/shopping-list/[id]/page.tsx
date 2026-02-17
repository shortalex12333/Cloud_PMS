'use client';

/**
 * =============================================================================
 * SHOPPING LIST LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-17 (FE-03-05) — Shopping List Lens Rebuild
 *
 * PURPOSE: Full-page lens for shopping list entities.
 * Supports direct deep links: /shopping-list/{id}
 *
 * DATA FETCHING:
 * --------------
 * - Fetches shopping list + items directly from Supabase
 * - pms_shopping_lists joined with pms_shopping_list_items
 * - Requires authenticated session with yachtId from bootstrap
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/ShoppingListLens.tsx — Lens component
 * - /src/hooks/useShoppingListActions.ts — Actions hook
 * - /src/components/lens/shopping-sections/ — Section components
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { ShoppingListLens, type ShoppingListLensData } from '@/components/lens/ShoppingListLens';
import { AlertTriangle, Loader2 } from 'lucide-react';

// ---------------------------------------------------------------------------
// LEDGER LOGGING
// Logs navigation events to pms_audit_log via backend API.
// Per CLAUDE.md: Every user action logged to ledger. Every navigate — all of it.
// ---------------------------------------------------------------------------
const RENDER_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

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
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_name: eventName, payload }),
    });
  } catch {
    // Navigation logging is fire-and-forget — never block UX on failure
  }
}

// ---------------------------------------------------------------------------
// PAGE COMPONENT
// ---------------------------------------------------------------------------

export default function ShoppingListLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [shoppingList, setShoppingList] = useState<ShoppingListLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract shopping list ID from URL: /shopping-list/[id]
  const shoppingListId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  const fetchShoppingList = useCallback(async () => {
    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    try {
      // Fetch shopping list with items
      const { data: list, error: listError } = await supabase
        .from('pms_shopping_lists')
        .select(`
          id,
          title,
          status,
          requester_id,
          requester_name,
          approver_id,
          approver_name,
          created_at,
          approved_at,
          pms_shopping_list_items (
            id,
            part_name,
            part_number,
            manufacturer,
            quantity_requested,
            quantity_approved,
            unit,
            status,
            urgency,
            source_type,
            source_notes,
            part_id,
            is_candidate_part,
            candidate_promoted_to_part_id,
            source_work_order_id,
            source_receiving_id,
            created_at,
            created_by,
            created_by_name,
            approved_at,
            approved_by,
            approved_by_name,
            approval_notes,
            rejected_at,
            rejected_by,
            rejected_by_name,
            rejection_reason,
            rejection_notes,
            promoted_at,
            promoted_by,
            promoted_by_name
          )
        `)
        .eq('id', shoppingListId)
        .eq('yacht_id', user.yachtId)
        .single();

      if (listError || !list) {
        setError(listError?.message || 'Shopping list not found');
        setLoading(false);
        return;
      }

      // Fetch approval history from audit log
      const { data: historyRows } = await supabase
        .from('pms_audit_log')
        .select('id, action, actor_id, actor_name, created_at, details')
        .eq('entity_type', 'shopping_list')
        .eq('entity_id', shoppingListId)
        .order('created_at', { ascending: false })
        .limit(50);

      // Map raw DB row to ShoppingListLensData
      const raw = list as Record<string, unknown>;
      const rawItems = (raw.pms_shopping_list_items as Record<string, unknown>[]) ?? [];

      const data: ShoppingListLensData = {
        id: raw.id as string,
        title: raw.title as string | undefined,
        status: (raw.status as string) || 'pending',
        requester_id: raw.requester_id as string | undefined,
        requester_name: raw.requester_name as string | undefined,
        approver_id: raw.approver_id as string | undefined,
        approver_name: raw.approver_name as string | undefined,
        created_at: raw.created_at as string,
        approved_at: raw.approved_at as string | undefined,
        items: rawItems.map((item) => ({
          id: item.id as string,
          part_name: item.part_name as string,
          part_number: item.part_number as string | undefined,
          manufacturer: item.manufacturer as string | undefined,
          quantity_requested: item.quantity_requested as number,
          quantity_approved: item.quantity_approved as number | undefined,
          unit: item.unit as string | undefined,
          status: item.status as 'candidate' | 'under_review' | 'approved' | 'ordered' | 'partially_fulfilled' | 'fulfilled' | 'installed' | 'rejected',
          urgency: item.urgency as 'low' | 'normal' | 'high' | 'critical' | undefined,
          source_type: item.source_type as 'inventory_low' | 'inventory_oos' | 'work_order_usage' | 'receiving_missing' | 'receiving_damaged' | 'manual_add',
          source_notes: item.source_notes as string | undefined,
          part_id: item.part_id as string | undefined,
          is_candidate_part: item.is_candidate_part as boolean | undefined,
          candidate_promoted_to_part_id: item.candidate_promoted_to_part_id as string | undefined,
          source_work_order_id: item.source_work_order_id as string | undefined,
          source_receiving_id: item.source_receiving_id as string | undefined,
          created_at: item.created_at as string,
          created_by: item.created_by as string | undefined,
          created_by_name: item.created_by_name as string | undefined,
          approved_at: item.approved_at as string | undefined,
          approved_by: item.approved_by as string | undefined,
          approved_by_name: item.approved_by_name as string | undefined,
          approval_notes: item.approval_notes as string | undefined,
          rejected_at: item.rejected_at as string | undefined,
          rejected_by: item.rejected_by as string | undefined,
          rejected_by_name: item.rejected_by_name as string | undefined,
          rejection_reason: item.rejection_reason as string | undefined,
          rejection_notes: item.rejection_notes as string | undefined,
          promoted_at: item.promoted_at as string | undefined,
          promoted_by: item.promoted_by as string | undefined,
          promoted_by_name: item.promoted_by_name as string | undefined,
        })),
        history: (historyRows ?? []).map((row) => ({
          id: row.id as string,
          action: row.action as string,
          actor_id: row.actor_id as string | undefined,
          actor_name: row.actor_name as string | undefined,
          timestamp: row.created_at as string,
          details: row.details as string | undefined,
        })),
      };

      setShoppingList(data);
      setLoading(false);

      // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
      logNavigationEvent('navigate_to_lens', {
        entity_type: 'shopping_list',
        entity_id: shoppingListId,
        title: data.title,
        status: data.status,
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load shopping list'
      );
      setLoading(false);
    }
  }, [shoppingListId, user]);

  useEffect(() => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;
    fetchShoppingList();
  }, [authLoading, bootstrapping, fetchShoppingList]);

  // ---------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Must be declared before any early returns (Rules of Hooks)
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'shopping_list',
      entity_id: shoppingListId,
    });
    router.back();
  }, [shoppingListId, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: 'shopping_list',
      entity_id: shoppingListId,
    });
    router.push('/app');
  }, [shoppingListId, router]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    fetchShoppingList();
  }, [fetchShoppingList]);

  // ---------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">
            Loading shopping list...
          </p>
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
            Unable to load shopping list
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
  if (!shoppingList) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // RENDER — Delegate entirely to ShoppingListLens component
  // ---------------------------------------------------------------------------
  return (
    <ShoppingListLens
      shoppingList={shoppingList}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
