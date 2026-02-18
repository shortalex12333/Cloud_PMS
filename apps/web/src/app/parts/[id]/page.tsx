'use client';

/**
 * =============================================================================
 * PARTS LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-17 (FE-02-03) — Parts/Inventory lens page
 *
 * PURPOSE: Full-page lens for part/inventory entities
 *
 * DATA FETCHING:
 * --------------
 * - Uses inventory microaction handler: viewPartStock() from @/lib/microactions/handlers/inventory
 * - Requires ActionContext with yacht_id (from useAuth bootstrap)
 * - Queries Supabase table: pms_parts
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 *
 * LEDGER LOGGING:
 * ---------------
 * - Logs navigate_to_lens event on mount (fire-and-forget)
 * - Logs navigate_back and close_lens on navigation
 * - Per CLAUDE.md: every user action logged to ledger — every navigate
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/PartsLens.tsx — Lens component
 * - /src/components/lens/LensHeader.tsx — Fixed header component
 * - /src/lib/microactions/handlers/inventory.ts — Data fetching logic
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewPartStock } from '@/lib/microactions/handlers/inventory';
import type { ActionContext } from '@/lib/microactions/types';
import { PartsLens, type PartData } from '@/components/lens/PartsLens';
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
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_name: eventName, payload }),
    });
  } catch {
    // Navigation logging is fire-and-forget — never block UX on failure
  }
}

export default function PartLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [part, setPart] = useState<PartData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract part ID from URL: /parts/[id]
  const partId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  const fetchPart = useCallback(async () => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    try {
      const context: ActionContext = {
        yacht_id: user.yachtId!,
        user_id: user.id,
        user_role: user.role || 'member',
        entity_id: partId,
        entity_type: 'part',
      };

      const result = await viewPartStock(context, { part_id: partId });

      if (!result.success || !result.data) {
        setError(result.error?.message || 'Part not found');
        setLoading(false);
        return;
      }

      // Map the raw handler result to PartData shape
      const raw = (result.data as { part: Record<string, unknown> }).part;

      const data: PartData = {
        id: raw.id as string,
        name: (raw.name as string) || 'Unnamed Part',
        part_number: raw.part_number as string | undefined,
        description: raw.description as string | undefined,
        stock_level: (raw.quantity as number) ?? 0,
        reorder_point: raw.reorder_point as number | undefined,
        min_stock: raw.min_quantity as number | undefined,
        max_stock: raw.max_quantity as number | undefined,
        unit: raw.unit as string | undefined,
        location: (raw.location as string | undefined) || (raw.storage_location as string | undefined),
        unit_cost: raw.unit_cost as number | undefined,
        supplier: raw.supplier as string | undefined,
        is_low_stock: raw.is_low_stock as boolean | undefined,
        equipment_id: raw.equipment_id as string | undefined,
        equipment_name: raw.equipment_name as string | undefined,
      };

      setPart(data);
      setLoading(false);

      // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
      logNavigationEvent('navigate_to_lens', {
        entity_type: 'part',
        entity_id: partId,
        part_number: data.part_number,
        name: data.name,
        stock_level: data.stock_level,
        is_low_stock: data.is_low_stock,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load part');
      setLoading(false);
    }
  }, [partId, user, authLoading, bootstrapping]);

  useEffect(() => {
    fetchPart();
  }, [fetchPart]);

  // ---------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Must be declared before any early returns (Rules of Hooks)
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'part',
      entity_id: partId,
    });
    router.back();
  }, [partId, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: 'part',
      entity_id: partId,
    });
    router.push('/app');
  }, [partId, router]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    setError(null);
    setPart(null);
    fetchPart();
  }, [fetchPart]);

  // ---------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading part...</p>
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
            Unable to load part
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
  if (!part) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // RENDER — Delegate entirely to PartsLens component
  // ---------------------------------------------------------------------------
  return (
    <PartsLens
      part={part}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
