'use client';

/**
 * =============================================================================
 * WARRANTY CLAIM LENS - Full Page View
 * =============================================================================
 *
 * CREATED: FE-03-04
 *
 * PURPOSE: Full-page lens for warranty claim entities.
 *
 * FLOW:
 * -----
 * 1. Resolves claim UUID from URL params: /warranty/[id]
 * 2. Fetches claim data via Supabase with JWT auth
 * 3. Renders WarrantyLens component with full claim data
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error state if not authenticated
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/WarrantyLens.tsx — Lens component
 * - /src/hooks/useWarrantyActions.ts — Action hook
 * - /src/components/lens/sections/warranty/ — Warranty sections
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { WarrantyLens, type WarrantyLensData } from '@/components/lens/WarrantyLens';
import { supabase } from '@/lib/supabaseClient';
import { AlertTriangle, Loader2 } from 'lucide-react';

// ---------------------------------------------------------------------------
// LEDGER LOGGING
// Per CLAUDE.md: Every navigate logged to ledger, fire-and-forget.
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

// ---------------------------------------------------------------------------
// DATA FETCHING
// ---------------------------------------------------------------------------

async function fetchWarrantyClaim(
  claimId: string,
  yachtId: string,
  accessToken: string
): Promise<WarrantyLensData> {
  const response = await fetch(
    `${RENDER_API_URL}/v1/warranty/view`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        yacht_id: yachtId,
        claim_id: claimId,
      }),
    }
  );

  if (!response.ok) {
    const json = await response.json().catch(() => ({}));
    const msg =
      (json as { error?: string; detail?: string }).error ||
      (json as { error?: string; detail?: string }).detail ||
      `Request failed (${response.status})`;
    throw new Error(msg);
  }

  const json = await response.json();
  // API returns { claim: { ... } }
  const raw = (json as { claim: Record<string, unknown> }).claim ?? json;

  return {
    id: raw.id as string,
    claim_number: raw.claim_number as string | undefined,
    title: (raw.title as string) || 'Warranty Claim',
    description: raw.description as string | undefined,
    status: (raw.status as WarrantyLensData['status']) || 'draft',
    equipment_id: raw.equipment_id as string | undefined,
    equipment_name: raw.equipment_name as string | undefined,
    fault_id: raw.fault_id as string | undefined,
    fault_code: raw.fault_code as string | undefined,
    supplier: raw.supplier as string | undefined,
    claimed_amount: raw.claimed_amount as number | undefined,
    approved_amount: raw.approved_amount as number | undefined,
    currency: (raw.currency as string) || 'USD',
    submitted_at: raw.submitted_at as string | undefined,
    resolved_at: raw.resolved_at as string | undefined,
    resolution_notes: raw.resolution_notes as string | undefined,
    created_at: raw.created_at as string,
    documents: (raw.documents as WarrantyLensData['documents']) || [],
    history: (raw.history as WarrantyLensData['history']) || [],
  };
}

// ---------------------------------------------------------------------------
// PAGE COMPONENT
// ---------------------------------------------------------------------------

export default function WarrantyLensPage() {
  // -------------------------------------------------------------------------
  // ROUTING & AUTH
  // -------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, session, loading: authLoading, bootstrapping } = useAuth();

  // -------------------------------------------------------------------------
  // STATE
  // -------------------------------------------------------------------------
  const [claim, setClaim] = useState<WarrantyLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const claimId = params.id as string;

  // -------------------------------------------------------------------------
  // DATA FETCHING
  // -------------------------------------------------------------------------
  const loadClaim = useCallback(async () => {
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId || !session?.access_token) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const data = await fetchWarrantyClaim(claimId, user.yachtId, session.access_token);
      setClaim(data);
      setLoading(false);

      // Log navigate_to_lens event
      logNavigationEvent('navigate_to_lens', {
        entity_type: 'warranty_claim',
        entity_id: claimId,
        claim_number: data.claim_number,
        title: data.title,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load warranty claim');
      setLoading(false);
    }
  }, [claimId, user, session, authLoading, bootstrapping]);

  useEffect(() => {
    loadClaim();
  }, [loadClaim]);

  // -------------------------------------------------------------------------
  // NAVIGATION HANDLERS — declared before early returns (Rules of Hooks)
  // -------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: 'warranty_claim',
      entity_id: claimId,
    });
    router.back();
  }, [claimId, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: 'warranty_claim',
      entity_id: claimId,
    });
    router.push('/app');
  }, [claimId, router]);

  const handleRefresh = useCallback(() => {
    loadClaim();
  }, [loadClaim]);

  // -------------------------------------------------------------------------
  // LOADING STATE
  // -------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading warranty claim...</p>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // ERROR STATE
  // -------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-4">
        <div className="bg-surface-primary rounded-[var(--radius-md)] p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-10 h-10 text-status-critical mx-auto mb-4" />
          <h2 className="text-[18px] font-semibold text-txt-primary mb-2">
            Unable to load warranty claim
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

  // -------------------------------------------------------------------------
  // NULL CHECK
  // -------------------------------------------------------------------------
  if (!claim) {
    return null;
  }

  // -------------------------------------------------------------------------
  // RENDER — Delegate entirely to WarrantyLens component
  // -------------------------------------------------------------------------
  return (
    <WarrantyLens
      claim={claim}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
