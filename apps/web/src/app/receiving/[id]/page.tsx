'use client';

/**
 * =============================================================================
 * RECEIVING LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-17
 *
 * PURPOSE: Full-page lens for receiving records
 *
 * FLOW:
 * -----
 * 1. URL: /receiving/{id}
 * 2. This page fetches full receiving record data and renders ReceivingLens
 *
 * DATA FETCHING:
 * --------------
 * - Queries Supabase tables: pms_receiving, pms_receiving_items, pms_receiving_documents
 * - Requires authenticated session with yachtId from bootstrap
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/ReceivingLens.tsx — Lens component
 * - /src/components/lens/LensHeader.tsx — Fixed header component
 * - /src/hooks/useReceivingActions.ts — Actions hook
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { ReceivingLens, type ReceivingLensData } from '@/components/lens/ReceivingLens';
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

export default function ReceivingLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [receiving, setReceiving] = useState<ReceivingLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract receiving ID from URL: /receiving/[id]
  const receivingId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  const fetchReceiving = useCallback(async () => {
    if (!user?.yachtId) return;

    try {
      setLoading(true);

      // Fetch main receiving record
      const { data: raw, error: fetchError } = await supabase
        .from('pms_receiving')
        .select('*')
        .eq('id', receivingId)
        .eq('yacht_id', user.yachtId)
        .single();

      if (fetchError || !raw) {
        setError(fetchError?.message ?? 'Receiving record not found');
        setLoading(false);
        return;
      }

      // Fetch line items
      const { data: itemsData } = await supabase
        .from('pms_receiving_items')
        .select('*')
        .eq('receiving_id', receivingId)
        .eq('yacht_id', user.yachtId)
        .order('created_at', { ascending: true });

      // Fetch documents
      const { data: docsData } = await supabase
        .from('pms_receiving_documents')
        .select('*')
        .eq('receiving_id', receivingId)
        .eq('yacht_id', user.yachtId)
        .order('created_at', { ascending: false });

      // Fetch audit history
      const { data: historyData } = await supabase
        .from('pms_audit_log')
        .select('*')
        .eq('entity_id', receivingId)
        .eq('yacht_id', user.yachtId)
        .order('timestamp', { ascending: false })
        .limit(50);

      // Map raw DB record to ReceivingLensData shape
      const data: ReceivingLensData = {
        id: raw.id as string,
        reference: (raw.vendor_reference as string | undefined) ?? undefined,
        supplier_name: (raw.vendor_name as string | undefined) ?? undefined,
        po_number: (raw.po_number as string | undefined) ?? undefined,
        status: (raw.status as string) || 'draft',
        received_by: (raw.received_by as string | undefined) ?? undefined,
        received_by_name: (raw.received_by_name as string | undefined) ?? undefined,
        created_at: raw.created_at as string,
        accepted_at: (raw.accepted_at as string | undefined) ?? undefined,
        rejected_at: (raw.rejected_at as string | undefined) ?? undefined,
        rejection_reason: (raw.rejection_reason as string | undefined) ?? undefined,
        items: itemsData ?? [],
        documents: docsData ?? [],
        history: (historyData ?? []).map((entry: Record<string, unknown>) => ({
          id: entry.id as string,
          action: entry.action as string,
          actor: (entry.actor_name ?? entry.actor ?? 'Unknown') as string,
          actor_id: entry.actor_id as string | undefined,
          timestamp: (entry.timestamp ?? entry.created_at) as string,
          description: entry.description as string | undefined,
          details: entry.details as Record<string, unknown> | undefined,
        })),
      };

      setReceiving(data);
      setLoading(false);

      // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
      logNavigationEvent('navigate_to_lens', {
        entity_type: 'receiving',
        entity_id: receivingId,
        supplier_name: data.supplier_name,
        status: data.status,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load receiving record');
      setLoading(false);
    }
  }, [receivingId, user?.yachtId]);

  useEffect(() => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    fetchReceiving();
  }, [receivingId, user, authLoading, bootstrapping, fetchReceiving]);

  // ---------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Must be declared before any early returns (Rules of Hooks)
  // ---------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'receiving',
      entity_id: receivingId,
    });
    router.back();
  }, [receivingId, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: 'receiving',
      entity_id: receivingId,
    });
    router.push('/app');
  }, [receivingId, router]);

  const handleRefresh = useCallback(() => {
    fetchReceiving();
  }, [fetchReceiving]);

  // ---------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading receiving record...</p>
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
            Unable to load receiving record
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
  if (!receiving) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // RENDER — Delegate entirely to ReceivingLens component
  // ---------------------------------------------------------------------------
  return (
    <ReceivingLens
      receiving={receiving}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
