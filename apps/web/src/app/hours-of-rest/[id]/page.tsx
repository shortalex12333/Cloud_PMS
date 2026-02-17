'use client';

/**
 * HoursOfRestLensPage — Full-page lens for hours-of-rest entities.
 *
 * Renders the HoursOfRestLens component for a specific crew member's
 * STCW hours-of-rest record, following the same pattern as
 * faults/[id]/page.tsx and work-orders/[id]/page.tsx.
 *
 * FE-03-03: Hours of Rest Lens Rebuild
 *
 * Navigation flow:
 * 1. User arrives via /hours-of-rest/{id} (deep link or in-app nav)
 * 2. Page fetches HOR data via getHoursOfRest microaction handler
 * 3. HoursOfRestLens renders in full-screen glass overlay
 * 4. onBack → router.back(); onClose → router.push('/app')
 * 5. Navigation event logged to ledger on open (fire-and-forget)
 *
 * The {id} param is the crew member user_id whose HOR record is being viewed.
 * The period defaults to the current calendar month.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { getHoursOfRest } from '@/lib/microactions/handlers/hours_of_rest';
import type { ActionContext } from '@/lib/microactions/types';
import { HoursOfRestLens } from '@/components/lens/HoursOfRestLens';
import type { HoursOfRestLensData } from '@/components/lens/HoursOfRestLens';
import { Loader2, AlertTriangle } from 'lucide-react';

export default function HoursOfRestLensPage() {
  // ---------------------------------------------------------------------------
  // Routing + auth
  // ---------------------------------------------------------------------------
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [hoursOfRest, setHoursOfRest] = useState<HoursOfRestLensData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // The user_id of the crew member whose HOR records we are viewing
  const crewUserId = params.id as string;

  // Optional date range from query params — defaults to current month
  const startDate = searchParams.get('start') ?? undefined;
  const endDate = searchParams.get('end') ?? undefined;

  // Compute default period (current calendar month) if no query params provided
  const defaultPeriodStart = (): string => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
  };

  const defaultPeriodEnd = (): string => {
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return `${lastDay.getFullYear()}-${String(lastDay.getMonth() + 1).padStart(2, '0')}-${String(lastDay.getDate()).padStart(2, '0')}`;
  };

  const periodStart = startDate ?? defaultPeriodStart();
  const periodEnd = endDate ?? defaultPeriodEnd();

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const fetchHoursOfRest = useCallback(async () => {
    if (!user?.yachtId) return;

    setLoading(true);
    setError(null);

    try {
      const context: ActionContext = {
        yacht_id: user.yachtId,
        user_id: user.id,
        user_role: user.role || 'member',
        entity_id: crewUserId,
        entity_type: 'hor_table',
      };

      const result = await getHoursOfRest(context, {
        user_id: crewUserId,
        start_date: periodStart,
        end_date: periodEnd,
      });

      if (!result.success || !result.data) {
        setError(result.error?.message || 'Hours of rest record not found');
        setLoading(false);
        return;
      }

      // Map raw API response → HoursOfRestLensData
      // The backend returns the raw record; we map to our typed interface.
      const raw = result.data as Record<string, unknown>;

      // Extract nested arrays with safe fallbacks
      const dailyRecords = Array.isArray(raw.records)
        ? (raw.records as Record<string, unknown>[]).map((rec) => ({
            id: (rec.id as string) ?? crypto.randomUUID(),
            record_date: rec.record_date as string,
            rest_periods: Array.isArray(rec.rest_periods)
              ? (rec.rest_periods as Array<{ start: string; end: string; hours: number }>)
              : [],
            total_rest_hours: (rec.total_rest_hours as number) ?? 0,
            compliance_status: (rec.compliance_status as 'compliant' | 'warning' | 'violation') ?? 'compliant',
          }))
        : [];

      const warnings = Array.isArray(raw.warnings)
        ? (raw.warnings as Record<string, unknown>[]).map((w) => ({
            id: w.id as string,
            warning_date: w.warning_date as string,
            description: (w.description as string) ?? 'STCW rest requirement not met',
            severity: (w.severity as 'warning' | 'violation') ?? 'warning',
            acknowledged_at: w.acknowledged_at as string | undefined,
            acknowledged_by: w.acknowledged_by as string | undefined,
          }))
        : [];

      const monthlySignoff = raw.current_signoff
        ? {
            id: (raw.current_signoff as Record<string, unknown>).id as string,
            month: (raw.current_signoff as Record<string, unknown>).month as string,
            department: (raw.current_signoff as Record<string, unknown>).department as string,
            crew_signed_at: (raw.current_signoff as Record<string, unknown>).crew_signed_at as string | undefined,
            hod_signed_at: (raw.current_signoff as Record<string, unknown>).hod_signed_at as string | undefined,
            captain_signed_at: (raw.current_signoff as Record<string, unknown>).captain_signed_at as string | undefined,
            status: ((raw.current_signoff as Record<string, unknown>).status as MonthlySignOffStatus) ?? 'pending',
          }
        : undefined;

      // Derive aggregate compliance status from daily records
      const hasViolations = dailyRecords.some((r) => r.compliance_status === 'violation');
      const hasWarnings = dailyRecords.some((r) => r.compliance_status === 'warning');
      const aggregateCompliance: 'compliant' | 'warning' | 'violation' = hasViolations
        ? 'violation'
        : hasWarnings
        ? 'warning'
        : 'compliant';

      const violationsCount = dailyRecords.filter((r) => r.compliance_status === 'violation').length;

      // Derive sign-off status from monthlySignoff
      const signoffStatus: 'signed' | 'pending' | 'not_required' = monthlySignoff
        ? monthlySignoff.status === 'complete' || monthlySignoff.status === 'captain_signed'
          ? 'signed'
          : 'pending'
        : 'not_required';

      const data: HoursOfRestLensData = {
        id: crewUserId,
        user_id: crewUserId,
        crew_name: (raw.crew_name as string) ?? (raw.user_name as string) ?? 'Crew Member',
        department: raw.department as string | undefined,
        compliance_status: (raw.compliance_status as 'compliant' | 'warning' | 'violation') ?? aggregateCompliance,
        period_start: periodStart,
        period_end: periodEnd,
        violations_count: (raw.violations_count as number) ?? violationsCount,
        signoff_status: signoffStatus,
        daily_log: dailyRecords,
        warnings,
        monthly_signoff: monthlySignoff,
      };

      setHoursOfRest(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load hours of rest');
      setLoading(false);
    }
  }, [crewUserId, user, periodStart, periodEnd]);

  useEffect(() => {
    // Wait for auth + bootstrap to complete
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    fetchHoursOfRest();
  }, [crewUserId, user, authLoading, bootstrapping, fetchHoursOfRest]);

  // ---------------------------------------------------------------------------
  // Log navigation event to ledger on open (fire-and-forget)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!hoursOfRest || !user?.yachtId) return;

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
            entity_type: 'hours_of_rest',
            entity_id: hoursOfRest.user_id,
            metadata: {
              crew_name: hoursOfRest.crew_name,
              period_start: hoursOfRest.period_start,
              period_end: hoursOfRest.period_end,
              compliance_status: hoursOfRest.compliance_status,
            },
          }),
        }).catch(() => {
          // Ignore ledger errors — never block navigation UX
        });
      } catch {
        // Ignore
      }
    };

    logNavigationEvent();
  }, [hoursOfRest, user]);

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
          <p className="text-txt-secondary text-[14px]">Loading hours of rest...</p>
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
  if (!hoursOfRest) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // Render HoursOfRestLens
  // ---------------------------------------------------------------------------
  return (
    <HoursOfRestLens
      hoursOfRest={hoursOfRest}
      onBack={handleBack}
      onClose={handleClose}
      onRefresh={fetchHoursOfRest}
    />
  );
}

// ---------------------------------------------------------------------------
// Local type alias (avoids importing MonthlySignOff type in page)
// ---------------------------------------------------------------------------
type MonthlySignOffStatus = 'pending' | 'crew_signed' | 'hod_signed' | 'captain_signed' | 'complete';
