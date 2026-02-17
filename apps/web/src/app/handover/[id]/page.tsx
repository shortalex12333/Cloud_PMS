'use client';

/**
 * HandoverLensPage — Full-page lens for handover entities.
 *
 * FE-03-02: Handover Lens Rebuild
 *
 * Navigation flow:
 * 1. User arrives via /handover/{id} (deep link, handover export, or in-app nav)
 * 2. Page fetches handover data via Supabase direct query (no dedicated view handler yet)
 * 3. HandoverLens renders in full-screen glass overlay
 * 4. onBack → router.back(); onClose → router.push('/app')
 * 5. Navigation event logged to ledger on open (fire-and-forget)
 *
 * Data model:
 * - handover_items table: items for this handover (yacht-scoped)
 * - handover_exports table: PDF exports with signature tracking
 * - pms_handovers table (if exists) or derived from handover_items yacht-scoped
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { HandoverLens, type HandoverLensData, type HandoverItem, type HandoverExport } from '@/components/lens/HandoverLens';
import { Loader2, AlertTriangle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function HandoverLensPage() {
  // -------------------------------------------------------------------------
  // Routing + auth
  // -------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const [handover, setHandover] = useState<HandoverLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handoverId = params.id as string;

  // -------------------------------------------------------------------------
  // Data fetching
  // -------------------------------------------------------------------------
  const fetchHandover = useCallback(async () => {
    if (!user?.yachtId) return;

    setLoading(true);
    setError(null);

    try {
      // Fetch handover items for this yacht (grouped by a handover record)
      // If a pms_handovers table exists, query it; otherwise derive from handover_items
      const { data: items, error: itemsError } = await supabase
        .from('handover_items')
        .select('*')
        .eq('yacht_id', user.yachtId)
        .is('deleted_at', null)
        .order('created_at', { ascending: false });

      if (itemsError) {
        setError(itemsError.message);
        setLoading(false);
        return;
      }

      // Fetch exports for this handover
      const { data: exportsData, error: exportsError } = await supabase
        .from('handover_exports')
        .select('*')
        .eq('yacht_id', user.yachtId)
        .order('created_at', { ascending: false });

      if (exportsError) {
        // Non-fatal: exports may not exist yet
        console.warn('Handover exports fetch failed:', exportsError.message);
      }

      // Map DB rows → HandoverItem[]
      const handoverItems: HandoverItem[] = (items ?? []).map((row) => ({
        id: row.id as string,
        summary: (row.summary as string) ?? '',
        section: row.section as string | undefined,
        is_critical: (row.is_critical as boolean) ?? false,
        requires_action: (row.requires_action as boolean) ?? false,
        category: row.category as HandoverItem['category'],
        entity_type: row.entity_type as HandoverItem['entity_type'],
        entity_id: row.entity_id as string,
        acknowledged_by: row.acknowledged_by as string | undefined,
        acknowledged_at: row.acknowledged_at as string | undefined,
        created_at: row.created_at as string,
        added_by: row.added_by as string | undefined,
        risk_tags: row.risk_tags as string[] | undefined,
        priority: row.priority as HandoverItem['priority'],
        status: row.status as HandoverItem['status'],
      }));

      // Map DB rows → HandoverExport[]
      const handoverExports: HandoverExport[] = ((exportsData ?? []) as Array<Record<string, unknown>>).map((row) => ({
        id: row.id as string,
        export_date: (row.created_at as string) ?? (row.export_date as string),
        department: row.department as string | undefined,
        file_url: row.file_url as string | undefined,
        outgoing_user_id: row.outgoing_user_id as string | undefined,
        outgoing_user_name: row.outgoing_user_name as string | undefined,
        outgoing_signed_at: row.outgoing_signed_at as string | undefined,
        incoming_user_id: row.incoming_user_id as string | undefined,
        incoming_user_name: row.incoming_user_name as string | undefined,
        incoming_signed_at: row.incoming_signed_at as string | undefined,
        signoff_complete: (row.signoff_complete as boolean) ?? false,
      }));

      // Determine overall handover status from exports + signatures
      // - No exports + items exist = draft
      // - Export exists but not fully signed = pending_signatures
      // - Export exists and fully signed = complete
      const latestExport = handoverExports[0];
      let status: HandoverLensData['status'] = 'draft';
      if (latestExport) {
        status = latestExport.signoff_complete ? 'complete' : 'pending_signatures';
      }

      // Build the HandoverLensData object
      const handoverData: HandoverLensData = {
        // Use handoverId from URL (or yacht_id as scoped identifier)
        id: handoverId,
        title: 'Active Handover',
        status,
        // Crew names from latest export (if available)
        outgoing_crew_name: latestExport?.outgoing_user_name,
        outgoing_crew_id: latestExport?.outgoing_user_id,
        incoming_crew_name: latestExport?.incoming_user_name,
        incoming_crew_id: latestExport?.incoming_user_id,
        items: handoverItems,
        exports: handoverExports,
        // Signatures derived from latest export
        outgoing_signature: latestExport?.outgoing_signed_at
          ? {
              user_id: latestExport.outgoing_user_id ?? '',
              user_name: latestExport.outgoing_user_name ?? '',
              signed_at: latestExport.outgoing_signed_at,
              role: 'outgoing',
            }
          : undefined,
        incoming_signature: latestExport?.incoming_signed_at
          ? {
              user_id: latestExport.incoming_user_id ?? '',
              user_name: latestExport.incoming_user_name ?? '',
              signed_at: latestExport.incoming_signed_at,
              role: 'incoming',
            }
          : undefined,
        created_at: items?.[0]?.created_at ?? new Date().toISOString(),
      };

      setHandover(handoverData);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load handover');
      setLoading(false);
    }
  }, [handoverId, user]);

  useEffect(() => {
    // Wait for auth + bootstrap to complete
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    fetchHandover();
  }, [handoverId, user, authLoading, bootstrapping, fetchHandover]);

  // -------------------------------------------------------------------------
  // Log navigation event to ledger on open (fire-and-forget)
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!handover || !user?.yachtId) return;

    const logNavigationEvent = async () => {
      try {
        fetch(`${API_BASE}/v1/ledger/log`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            yacht_id: user.yachtId,
            event_type: 'navigate_to_lens',
            entity_type: 'handover',
            entity_id: handover.id,
            metadata: { status: handover.status },
          }),
        }).catch(() => {
          // Ignore ledger errors — never block navigation UX
        });
      } catch {
        // Ignore
      }
    };

    logNavigationEvent();
  }, [handover, user]);

  // -------------------------------------------------------------------------
  // Navigation handlers
  // -------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleClose = useCallback(() => {
    router.push('/app');
  }, [router]);

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-brand-interactive animate-spin mx-auto mb-4" />
          <p className="text-txt-secondary text-[14px]">Loading handover...</p>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // Null guard
  // -------------------------------------------------------------------------
  if (!handover) {
    return null;
  }

  // -------------------------------------------------------------------------
  // Render HandoverLens
  // -------------------------------------------------------------------------
  return (
    <HandoverLens
      handover={handover}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={fetchHandover}
    />
  );
}
