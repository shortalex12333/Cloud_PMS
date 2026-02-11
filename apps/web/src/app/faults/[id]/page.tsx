'use client';

/**
 * =============================================================================
 * FAULT LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-05
 * PURPOSE: Full-page lens for fault entities accessed via handover export links
 *
 * HANDOVER EXPORT FLOW:
 * ---------------------
 * 1. User clicks link in handover PDF/HTML: https://app.celeste7.ai/open?t=<JWS_TOKEN>
 * 2. /open page resolves token via POST /api/v1/open/resolve (handover-export service)
 * 3. Token returns: { focus: { type: "fault", id: "uuid" }, yacht_id, scope }
 * 4. /open page redirects to this lens: /faults/{id}
 * 5. This page fetches full fault data and renders it
 *
 * DATA FETCHING:
 * --------------
 * - Uses microaction handler: viewFault() from @/lib/microactions/handlers/faults
 * - Requires ActionContext with yacht_id (from useAuth bootstrap)
 * - Queries Supabase table: pms_faults
 *
 * =============================================================================
 * WHAT THIS SKELETON PROVIDES:
 * =============================================================================
 * - Route structure: /faults/[id]
 * - Auth check pattern (wait for authLoading + bootstrapping)
 * - Data fetching via microaction handler
 * - Loading/error/success states
 * - Basic layout with severity badges
 * - RelatedEmailsPanel integration
 *
 * =============================================================================
 * WHAT'S MISSING (for engineers to implement):
 * =============================================================================
 * - [ ] Diagnose fault action + modal
 * - [ ] Create work order from fault action
 * - [ ] View manual section action
 * - [ ] Fault history display
 * - [ ] Suggested parts section
 * - [ ] Add note/photo functionality
 * - [ ] Acknowledge fault action
 * - [ ] Update/edit fault modal
 * - [ ] Add to handover action
 * - [ ] AI diagnosis display (if available)
 * - [ ] Link to equipment lens
 * - [ ] Link to created work order (if has_work_order)
 *
 * =============================================================================
 * RELATED FILES:
 * =============================================================================
 * - /src/lib/microactions/handlers/faults.ts - Data fetching logic
 * - /src/components/cards/FaultCard.tsx - Card component (has all action modals)
 * - /src/app/open/page.tsx - Token resolution (redirects here)
 * - /src/app/app/DeepLinkHandler.tsx - Query param handling (redirects here)
 *
 * =============================================================================
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewFault } from '@/lib/microactions/handlers/faults';
import type { ActionContext } from '@/lib/microactions/types';
import {
  Loader2,
  ArrowLeft,
  AlertTriangle,
  Settings,
  User,
  Calendar,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { RelatedEmailsPanel } from '@/components/email/RelatedEmailsPanel';
import { cn } from '@/lib/utils';

/**
 * Fault data shape returned from viewFault handler
 * Maps to pms_faults table + computed fields
 */
interface FaultData {
  id: string;
  title?: string;
  fault_code?: string;       // System fault code (e.g., "E001")
  description?: string;
  severity: string;          // low, medium, high, critical
  equipment_id?: string;     // FK to pms_equipment
  equipment_name?: string;   // Denormalized for display
  detected_at?: string;      // When fault was detected
  created_at: string;        // Record creation time
  resolved_at?: string;      // When fault was resolved
  reported_by?: string;      // User who reported
  is_active?: boolean;       // Computed: !resolved_at
  days_open?: number;        // Computed: days since detected_at
  has_work_order?: boolean;  // Whether a WO exists for this fault
}

export default function FaultLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [fault, setFault] = useState<FaultData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract fault ID from URL: /faults/[id]
  const faultId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Wait for auth AND bootstrap to complete
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    const fetchFault = async () => {
      try {
        // Build ActionContext for microaction handler
        const context: ActionContext = {
          yacht_id: user.yachtId!,
          user_id: user.id,
          user_role: user.role || 'member',
          entity_id: faultId,
          entity_type: 'fault',
        };

        // Call microaction handler
        // See: /src/lib/microactions/handlers/faults.ts
        const result = await viewFault(context, { fault_id: faultId });

        if (!result.success || !result.data) {
          setError(result.error?.message || 'Fault not found');
          setLoading(false);
          return;
        }

        const data = result.data as { fault: FaultData };
        setFault(data.fault);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load fault');
        setLoading(false);
      }
    };

    fetchFault();
  }, [faultId, user, authLoading, bootstrapping]);

  // ---------------------------------------------------------------------------
  // STYLING HELPERS
  // ---------------------------------------------------------------------------

  /** Map severity to visual style */
  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'critical':
        return { bg: 'bg-red-500/10', text: 'text-red-400', label: 'Critical' };
      case 'high':
        return { bg: 'bg-orange-500/10', text: 'text-orange-400', label: 'High' };
      case 'medium':
        return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Medium' };
      default:
        return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Low' };
    }
  };

  /** Format date for display */
  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  // ---------------------------------------------------------------------------
  // LOADING STATE
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-celeste-accent animate-spin mx-auto mb-4" />
          <p className="text-celeste-text-muted">Loading fault report...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center p-4">
        <div className="bg-celeste-bg-tertiary rounded-lg p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
          <p className="text-celeste-text-muted mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-white rounded-lg transition-colors"
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
  if (!fault) {
    return null;
  }

  const severity = getSeverityStyle(fault.severity);
  const reportedDate = fault.detected_at || fault.created_at;

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-celeste-black">
      {/* ===================================================================
          HEADER
          TODO: Add action buttons (Diagnose, Create WO, etc.)
          =================================================================== */}
      <header className="bg-celeste-bg-tertiary/50 border-b border-celeste-text-secondary/50 sticky top-0 z-10 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-celeste-text-secondary/50 rounded-lg transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-celeste-text-muted" />
            </button>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <span className="text-sm text-celeste-text-muted uppercase tracking-wider">Fault Report</span>
            </div>
            {/* TODO: Add action buttons
            <div className="ml-auto flex gap-2">
              <button onClick={() => setShowDiagnose(true)}>Diagnose</button>
              <button onClick={() => setShowCreateWO(true)}>Create Work Order</button>
            </div>
            */}
          </div>
        </div>
      </header>

      {/* ===================================================================
          MAIN CONTENT
          =================================================================== */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* -----------------------------------------------------------------
            TITLE SECTION
            ----------------------------------------------------------------- */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-4">
            {fault.title || fault.fault_code || 'Fault Report'}
          </h1>

          {/* Severity & Status Badges */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={cn('px-3 py-1 rounded-full text-sm font-medium', severity.bg, severity.text)}>
              {severity.label} Severity
            </span>
            {fault.is_active !== false && !fault.resolved_at && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-500/10 text-red-400">
                Active
              </span>
            )}
            {fault.resolved_at && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-500/10 text-green-400">
                Resolved
              </span>
            )}
            {fault.has_work_order && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-celeste-accent-subtle text-celeste-accent">
                Work Order Created
              </span>
            )}
          </div>

          {/* Equipment Link - TODO: Make clickable */}
          {fault.equipment_name && (
            <div className="flex items-center gap-2 text-celeste-text-muted mb-2">
              <Settings className="w-4 h-4" />
              <span>{fault.equipment_name}</span>
              {/* TODO: onClick={() => router.push(`/equipment/${fault.equipment_id}`)} */}
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            DESCRIPTION
            ----------------------------------------------------------------- */}
        {fault.description && (
          <div className="bg-celeste-bg-tertiary/50 rounded-lg p-6 mb-6 border border-celeste-text-secondary/50">
            <h2 className="text-sm font-semibold text-celeste-text-muted uppercase tracking-wider mb-3">
              Description
            </h2>
            <p className="text-celeste-border whitespace-pre-wrap">
              {fault.description}
            </p>
          </div>
        )}

        {/* -----------------------------------------------------------------
            DETAILS GRID
            ----------------------------------------------------------------- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Reported Date */}
          <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-celeste-text-disabled" />
              <div>
                <p className="text-xs text-celeste-text-disabled uppercase">Reported</p>
                <p className="text-celeste-border">{formatDate(reportedDate)}</p>
              </div>
            </div>
          </div>

          {/* Reported By */}
          {fault.reported_by && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <User className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Reported By</p>
                  <p className="text-celeste-border">{fault.reported_by}</p>
                </div>
              </div>
            </div>
          )}

          {/* Resolved Date */}
          {fault.resolved_at && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Resolved</p>
                  <p className="text-green-400">{formatDate(fault.resolved_at)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Days Open */}
          {fault.days_open !== undefined && fault.days_open > 0 && !fault.resolved_at && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Days Open</p>
                  <p className="text-amber-400">{fault.days_open} days</p>
                </div>
              </div>
            </div>
          )}

          {/* Fault Code */}
          {fault.fault_code && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Fault Code</p>
                  <p className="text-celeste-border font-mono">{fault.fault_code}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            TODO: AI DIAGNOSIS SECTION
            If fault has AI diagnosis, display it here
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            TODO: FAULT HISTORY SECTION
            Show previous occurrences of similar faults
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            RELATED EMAILS
            ----------------------------------------------------------------- */}
        <div className="bg-celeste-bg-tertiary/50 rounded-lg p-6 border border-celeste-text-secondary/50">
          <h2 className="text-sm font-semibold text-celeste-text-muted uppercase tracking-wider mb-4">
            Related Emails
          </h2>
          <RelatedEmailsPanel
            objectType="fault"
            objectId={fault.id}
          />
        </div>
      </main>
    </div>
  );
}
