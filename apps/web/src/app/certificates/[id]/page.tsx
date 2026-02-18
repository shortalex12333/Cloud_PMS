'use client';

/**
 * =============================================================================
 * CERTIFICATE LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-17 (FE-02-04) — Certificate Lens Rebuild
 *
 * PURPOSE: Full-page lens for vessel and crew certificates.
 * Supports both certificate types via URL param: ?type=vessel or ?type=crew
 *
 * FLOW:
 * -----
 * 1. User navigates to /certificates/{id}?type=vessel|crew
 * 2. Page determines certificate type from query param (default: vessel)
 * 3. Page fetches certificate data from Supabase via backend API
 * 4. Renders CertificateLens component
 * 5. Navigation events logged to pms_audit_log (fire-and-forget)
 *
 * DATA FETCHING:
 * --------------
 * - Calls GET /v1/certificates/{id}?type=vessel|crew
 * - Requires authenticated session with yachtId from bootstrap
 *
 * RELATED FILES:
 * ==============
 * - /src/components/lens/CertificateLens.tsx — Lens component
 * - /src/hooks/useCertificateActions.ts — Action hook
 * - /src/components/lens/LensHeader.tsx — Fixed header component
 *
 * =============================================================================
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { CertificateLens, type CertificateData } from '@/components/lens/CertificateLens';
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

// ---------------------------------------------------------------------------
// Data fetching — calls backend API (not Supabase direct)
// ---------------------------------------------------------------------------

async function fetchCertificate(
  certificateId: string,
  certificateType: 'vessel' | 'crew',
  yachtId: string,
  accessToken: string
): Promise<CertificateData> {
  const url = `${RENDER_API_URL}/v1/certificates/${certificateId}?type=${certificateType}&yacht_id=${encodeURIComponent(yachtId)}`;

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const json = await response.json().catch(() => ({}));
    const msg =
      (json as { error?: string; detail?: string }).error ||
      (json as { error?: string; detail?: string }).detail ||
      `Failed to load certificate (${response.status})`;
    throw new Error(msg);
  }

  const json = await response.json();
  // API returns { certificate: { ... } } or the object directly
  const raw = (json.certificate ?? json) as Record<string, unknown>;

  // Map raw API response to CertificateData shape
  const cert: CertificateData = {
    id: raw.id as string,
    certificate_name: (raw.certificate_name ?? raw.name ?? 'Certificate') as string,
    certificate_type_name: raw.certificate_type_name as string | undefined,
    certificate_number: raw.certificate_number as string | undefined,
    status: (raw.status as CertificateData['status']) ?? 'valid',
    issue_date: raw.issue_date as string,
    expiry_date: raw.expiry_date as string,
    issuing_authority: (raw.issuing_authority ?? 'Unknown') as string,
    notes: raw.notes as string | undefined,
    crew_member_id: raw.crew_member_id as string | undefined,
    crew_member_name: raw.crew_member_name as string | undefined,
    vessel_name: raw.vessel_name as string | undefined,
    days_until_expiry: raw.days_until_expiry as number | undefined,
    documents: (raw.documents as CertificateData['documents']) ?? [],
    renewal_history: (raw.renewal_history as CertificateData['renewal_history']) ?? [],
  };

  return cert;
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function CertificateLensPage() {
  // -------------------------------------------------------------------------
  // ROUTING & AUTH
  // -------------------------------------------------------------------------
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // Extract certificate ID from URL: /certificates/[id]
  const certificateId = params.id as string;

  // Determine certificate type from query param (default: vessel)
  const rawType = searchParams.get('type');
  const certificateType: 'vessel' | 'crew' =
    rawType === 'crew' ? 'crew' : 'vessel';

  // -------------------------------------------------------------------------
  // STATE
  // -------------------------------------------------------------------------
  const [certificate, setCertificate] = useState<CertificateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // DATA FETCHING
  // -------------------------------------------------------------------------
  useEffect(() => {
    // Wait for BOTH authLoading AND bootstrapping to complete.
    // yacht_id from bootstrap is required to scope the tenant query.
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    const fetch = async () => {
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        const accessToken = sessionData?.session?.access_token;

        if (!accessToken) {
          setError('Session expired. Please log in again.');
          setLoading(false);
          return;
        }

        const data = await fetchCertificate(
          certificateId,
          certificateType,
          user.yachtId!,
          accessToken
        );

        setCertificate(data);
        setLoading(false);

        // Log navigate_to_lens event — per CLAUDE.md every navigate is logged
        logNavigationEvent('navigate_to_lens', {
          entity_type: `${certificateType}_certificate`,
          entity_id: certificateId,
          certificate_name: data.certificate_name,
          certificate_type: certificateType,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load certificate');
        setLoading(false);
      }
    };

    fetch();
  }, [certificateId, certificateType, user, authLoading, bootstrapping]);

  // -------------------------------------------------------------------------
  // NAVIGATION HANDLERS — Must be declared before early returns (Rules of Hooks)
  // -------------------------------------------------------------------------
  const handleBack = useCallback(() => {
    logNavigationEvent('navigate_back', {
      entity_type: `${certificateType}_certificate`,
      entity_id: certificateId,
    });
    router.back();
  }, [certificateId, certificateType, router]);

  const handleClose = useCallback(() => {
    logNavigationEvent('close_lens', {
      entity_type: `${certificateType}_certificate`,
      entity_id: certificateId,
    });
    router.push('/app');
  }, [certificateId, certificateType, router]);

  const handleRefresh = useCallback(async () => {
    if (!user?.yachtId) return;

    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const accessToken = sessionData?.session?.access_token;
      if (!accessToken) return;

      const data = await fetchCertificate(
        certificateId,
        certificateType,
        user.yachtId,
        accessToken
      );
      setCertificate(data);
    } catch {
      // Refresh errors are non-blocking — data stays stale
    }
  }, [certificateId, certificateType, user]);

  // -------------------------------------------------------------------------
  // LOADING STATE — Skeleton per UI_SPEC.md (no full-page spinners)
  // -------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-interactive animate-spin" />
          <p className="text-[14px] text-txt-secondary">Loading certificate...</p>
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
            Unable to load certificate
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
  if (!certificate) {
    return null;
  }

  // -------------------------------------------------------------------------
  // RENDER — Delegate entirely to CertificateLens component
  // -------------------------------------------------------------------------
  return (
    <CertificateLens
      certificate={certificate}
      certificateType={certificateType}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={handleRefresh}
    />
  );
}
