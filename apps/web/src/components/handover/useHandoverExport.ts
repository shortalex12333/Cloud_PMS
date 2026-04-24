'use client';

/**
 * useHandoverExport — Shared handover export flow.
 *
 * Extracted from HandoverDraftPanel.handleExport so the Subbar "Create Handover"
 * primary action button (AppShell.handlePrimaryAction for the 'handover-export'
 * domain) can trigger the exact same backend flow without duplicating logic.
 *
 * The hook:
 *   1. Loads the caller's queued handover_items via GET /v1/handover/items
 *      (filtered server-side by user + not-exported). Exposes `items` +
 *      `itemCount` + `loading` so callers can guard the button.
 *   2. Exposes `exportHandover()` which:
 *        a. POST /v1/handover/export { export_type: 'html', filter_by_user: true }
 *        b. POST /v1/handover/items/mark-exported { item_ids: items.map(i=>i.id) }
 *        c. Routes to /handover-export/{export_id}
 *      — exactly mirroring HandoverDraftPanel's original handler.
 *   3. Exposes `isExporting` for loading state.
 *
 * B4 will wrap the trigger in a pre-export confirm modal. This hook is shaped
 * so B4 can simply gate the click on confirm → then call `exportHandover()`.
 * No transformation of the hook body is required.
 *
 * Backend endpoints used:
 *   - GET  {NEXT_PUBLIC_API_URL}/v1/handover/items            (fetch queued)
 *   - POST {NEXT_PUBLIC_API_URL}/v1/handover/export           (generate)
 *   - POST {NEXT_PUBLIC_API_URL}/v1/handover/items/mark-exported  (clear queue)
 */

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

interface HandoverItem {
  id: string;
}

export interface UseHandoverExportOptions {
  /**
   * When false the hook does not fetch the queued-items list on mount.
   * `exportHandover()` still works but will lazily refresh first.
   * Default true. Callers mounted on non-handover pages (e.g. AppShell on
   * every route) should pass `enabled: activeDomain === 'handover-export'`
   * to avoid a useless GET on every page load.
   */
  enabled?: boolean;
}

export interface UseHandoverExportResult {
  /** Raw queued items belonging to the current user (not-exported). */
  items: HandoverItem[];
  /** Convenience count for disabled/empty-state UI. */
  itemCount: number;
  /** True while the initial items fetch is in-flight. */
  loading: boolean;
  /** True while the export POST + mark-exported POST are running. */
  isExporting: boolean;
  /**
   * Fire the full export flow (POST /v1/handover/export → mark-exported →
   * route to /handover-export/{id}). Safe no-op when there are no items or
   * auth is not ready — callers should typically disable their trigger in
   * those cases for a better UX.
   */
  exportHandover: () => Promise<void>;
  /** Manual refresh of the queued items list (e.g. after adding a draft item). */
  refresh: () => Promise<void>;
}

export function useHandoverExport(opts: UseHandoverExportOptions = {}): UseHandoverExportResult {
  const { enabled = true } = opts;
  const { user } = useAuth();
  const { vesselId: activeVesselId } = useActiveVessel();
  const router = useRouter();

  const [items, setItems] = useState<HandoverItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // ── Fetch queued items (same endpoint HandoverDraftPanel uses) ─────────────
  // We only need the ids here (for mark-exported + count), so we keep the
  // shape minimal — the draft panel keeps its own rich local state for
  // rendering, this hook is only about the export trigger.
  const refresh = useCallback(async () => {
    if (!enabled || !user?.id) return;
    setLoading(true);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) {
        setItems([]);
        return;
      }
      const res = await fetch(`${RENDER_API_URL}/v1/handover/items`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        // Silent failure — button will fall back to disabled state.
        setItems([]);
        return;
      }
      const body = await res.json();
      const fetched: HandoverItem[] = Array.isArray(body?.items)
        ? body.items.map((i: { id: string }) => ({ id: i.id }))
        : [];
      setItems(fetched);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [enabled, user?.id]);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [enabled, refresh]);

  // ── Export — mirrors HandoverDraftPanel.handleExport exactly ──────────────
  const exportHandover = useCallback(async () => {
    if (!user?.id || !(activeVesselId || user?.yachtId)) return;
    if (items.length === 0) {
      // Mirror the draft panel's empty-state behaviour: show a friendly
      // toast instead of silently no-op'ing so the user knows why nothing
      // happened when they click via the subbar (which has no drawer view
      // of the queue alongside it).
      toast.info('Add items to your draft first');
      return;
    }

    setIsExporting(true);
    const pendingToastId = toast.info(
      'Generating handover — this may take up to 2 minutes',
      { duration: 120_000 }
    );
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) throw new Error('Authentication required — please log in again');

      const response = await fetch(`${RENDER_API_URL}/v1/handover/export`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ export_type: 'html', filter_by_user: true }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Export failed' }));
        throw new Error(err.detail || `Export failed (${response.status})`);
      }
      const result = await response.json();

      // Mark items exported via Render API (not direct supabase — wrong DB).
      await fetch(`${RENDER_API_URL}/v1/handover/items/mark-exported`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: items.map((i) => i.id) }),
      });

      toast.dismiss(pendingToastId);
      toast.success(`Handover exported — ${result.total_items ?? items.length} items`, {
        duration: 10_000,
        action: {
          label: 'View',
          onClick: () => router.push(`/handover-export/${result.export_id}`),
        },
      });

      // Navigate straight to the export view — matches draft-panel intent
      // (it offered a "View" button; from the subbar we drive the user there
      // directly since the subbar click is itself the primary action).
      router.push(`/handover-export/${result.export_id}`);

      // Refresh the local list so the next click sees the cleared queue.
      await refresh();
    } catch (err) {
      toast.dismiss(pendingToastId);
      toast.error(err instanceof Error ? err.message : 'Failed to export handover');
    } finally {
      setIsExporting(false);
    }
  }, [user?.id, user?.yachtId, activeVesselId, items, router, refresh]);

  return {
    items,
    itemCount: items.length,
    loading,
    isExporting,
    exportHandover,
    refresh,
  };
}
