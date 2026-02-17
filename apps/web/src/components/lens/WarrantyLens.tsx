'use client';

/**
 * WarrantyLens - Full-screen entity lens for warranty claims.
 *
 * Per CLAUDE.md and UI_SPEC.md — mirrors WorkOrderLens structure:
 * - Fixed LensHeader (56px): back button, "Warranty Claim" overline, close button
 * - LensTitleBlock: claim_number — title, status pill
 * - VitalSignsRow: 5 indicators (status, equipment link, fault link, supplier, submitted)
 * - Section containers: Claim Details, Linked Entities, Documents, History
 * - useWarrantyActions hook for all workflow actions
 * - Role-based button visibility (hide, not disable)
 * - Glass transition via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * Workflow: Draft → Submit → Approve/Reject (HOD+ required for Approve/Reject)
 *
 * FE-03-04: Warranty Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { formatRelativeTime } from '@/lib/utils';

// Shared sections (re-used from Work Order lens)
import { HistorySection, type AuditLogEntry } from './sections';

// Warranty-specific sections
import {
  WarrantyDocumentsSection,
  type WarrantyDocument,
} from './sections/warranty';

// Action hook + permissions
import {
  useWarrantyActions,
  useWarrantyPermissions,
} from '@/hooks/useWarrantyActions';

// Shared UI
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// Action modals
import { SubmitClaimModal } from './actions/warranty/SubmitClaimModal';
import { ApproveClaimModal } from './actions/warranty/ApproveClaimModal';
import { RejectClaimModal } from './actions/warranty/RejectClaimModal';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface WarrantyLensData {
  id: string;
  /** Human-readable claim number e.g. "WC-2026-001" — NEVER show raw UUID */
  claim_number?: string;
  /** Short claim title */
  title: string;
  /** Detailed claim description */
  description?: string;
  /** Status: draft | submitted | approved | rejected */
  status: 'draft' | 'submitted' | 'approved' | 'rejected';
  /** FK to pms_equipment */
  equipment_id?: string;
  /** Denormalized equipment name for display */
  equipment_name?: string;
  /** FK to pms_faults */
  fault_id?: string;
  /** Denormalized fault code for display e.g. "FLT-2026-000001" */
  fault_code?: string;
  /** Warranty supplier / provider name */
  supplier?: string;
  /** Claimed amount */
  claimed_amount?: number;
  /** Approved amount (set on approval) */
  approved_amount?: number;
  /** Currency code e.g. "USD" */
  currency?: string;
  /** ISO timestamp when claim was submitted */
  submitted_at?: string;
  /** ISO timestamp when approved or rejected */
  resolved_at?: string;
  /** Resolution notes (set on approve/reject) */
  resolution_notes?: string;
  /** ISO timestamp of record creation */
  created_at: string;
  /** Documents attached to this claim */
  documents?: WarrantyDocument[];
  /** Audit log entries */
  history?: AuditLogEntry[];
}

export interface WarrantyLensProps {
  /** The warranty claim data to render */
  claim: WarrantyLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers (domain-specific, local to this lens)
// ---------------------------------------------------------------------------

/**
 * Map warranty claim status to StatusPill color level.
 * draft/submitted → neutral/warning; approved → success; rejected → critical
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected':
      return 'critical';
    case 'submitted':
      return 'warning';
    case 'approved':
      return 'success';
    case 'draft':
    default:
      return 'neutral';
  }
}

/**
 * Format a warranty status enum value to a human-readable display label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    submitted: 'Submitted',
    approved: 'Approved',
    rejected: 'Rejected',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// ClaimDetailsSection — Inline section for claim description and financials
// ---------------------------------------------------------------------------

interface ClaimDetailsSectionProps {
  claim: WarrantyLensData;
  stickyTop?: number;
}

function ClaimDetailsSection({ claim, stickyTop }: ClaimDetailsSectionProps) {
  const hasFinancials = claim.claimed_amount !== undefined || claim.approved_amount !== undefined;
  const currency = claim.currency ?? 'USD';

  return (
    <SectionContainer title="Claim Details" stickyTop={stickyTop}>
      {/* Description */}
      {claim.description ? (
        <p className="text-[14px] text-txt-secondary leading-[1.6] whitespace-pre-wrap">
          {claim.description}
        </p>
      ) : (
        <p className="text-[14px] text-txt-tertiary italic">No description provided.</p>
      )}

      {/* Financials */}
      {hasFinancials && (
        <div className="mt-4 flex flex-col gap-2">
          <div className="h-px bg-surface-border-subtle" />
          <div className="mt-2 flex flex-col gap-1.5">
            {claim.claimed_amount !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-txt-tertiary">Claimed Amount</span>
                <span className="text-[14px] font-semibold text-txt-primary">
                  {currency} {claim.claimed_amount.toFixed(2)}
                </span>
              </div>
            )}
            {claim.approved_amount !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-txt-tertiary">Approved Amount</span>
                <span
                  className={cn(
                    'text-[14px] font-semibold',
                    claim.status === 'approved'
                      ? 'text-status-success'
                      : 'text-txt-primary'
                  )}
                >
                  {currency} {claim.approved_amount.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Resolution Notes */}
      {claim.resolution_notes && (
        <div className="mt-4">
          <div className="h-px bg-surface-border-subtle mb-3" />
          <p className="text-[12px] font-medium text-txt-tertiary uppercase tracking-wide mb-1">
            Resolution Notes
          </p>
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            {claim.resolution_notes}
          </p>
        </div>
      )}
    </SectionContainer>
  );
}

// ---------------------------------------------------------------------------
// LinkedEntitiesSection — Equipment + Fault links
// ---------------------------------------------------------------------------

interface LinkedEntitiesSectionProps {
  equipmentId?: string;
  equipmentName?: string;
  faultId?: string;
  faultCode?: string;
  stickyTop?: number;
}

function LinkedEntitiesSection({
  equipmentId,
  equipmentName,
  faultId,
  faultCode,
  stickyTop,
}: LinkedEntitiesSectionProps) {
  const hasEntities = equipmentId || faultId;

  return (
    <SectionContainer title="Linked Entities" stickyTop={stickyTop}>
      {!hasEntities ? (
        <p className="text-[14px] text-txt-tertiary italic">
          No linked equipment or fault.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {/* Equipment link */}
          {equipmentId && (
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-txt-tertiary">Equipment</span>
              <a
                href={`/equipment/${equipmentId}`}
                className="text-[14px] font-medium text-[var(--celeste-accent)] hover:underline"
              >
                {equipmentName ?? equipmentId}
              </a>
            </div>
          )}

          {/* Fault link */}
          {faultId && (
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-txt-tertiary">Fault</span>
              <a
                href={`/faults/${faultId}`}
                className="text-[14px] font-medium text-[var(--celeste-accent)] hover:underline"
              >
                {faultCode ?? faultId}
              </a>
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

// ---------------------------------------------------------------------------
// WarrantyLens component
// ---------------------------------------------------------------------------

/**
 * WarrantyLens — Full-screen entity lens for warranty claims.
 *
 * Usage:
 * ```tsx
 * <WarrantyLens
 *   claim={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const WarrantyLens = React.forwardRef<
  HTMLDivElement,
  WarrantyLensProps
>(({ claim, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility
  const [submitOpen, setSubmitOpen] = React.useState(false);
  const [approveOpen, setApproveOpen] = React.useState(false);
  const [rejectOpen, setRejectOpen] = React.useState(false);

  // Actions and permissions
  const actions = useWarrantyActions(claim.id);
  const perms = useWarrantyPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  const displayTitle = claim.claim_number
    ? `${claim.claim_number} — ${claim.title}`
    : claim.title;

  const statusColor = mapStatusToColor(claim.status);
  const statusLabel = formatStatusLabel(claim.status);

  // Build the 5 vital signs per plan spec
  const warrantyVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Equipment',
      value: claim.equipment_name ?? 'None',
      href: claim.equipment_id
        ? `/equipment/${claim.equipment_id}`
        : undefined,
    },
    {
      label: 'Fault',
      value: claim.fault_code ?? (claim.fault_id ? 'Linked' : 'None'),
      href: claim.fault_id
        ? `/faults/${claim.fault_id}`
        : undefined,
    },
    {
      label: 'Supplier',
      value: claim.supplier ?? '—',
    },
    {
      label: 'Submitted',
      value: claim.submitted_at
        ? formatRelativeTime(claim.submitted_at)
        : 'Not submitted',
    },
  ];

  // Section data (safe fallbacks)
  const documents = claim.documents ?? [];
  const history = claim.history ?? [];

  // Workflow state flags
  const isDraft = claim.status === 'draft';
  const isSubmitted = claim.status === 'submitted';

  // Action handlers — wrap hook methods with refresh callback
  const handleSubmitClaim = React.useCallback(async () => {
    const result = await actions.submitClaim();
    if (result.success) {
      setSubmitOpen(false);
      onRefresh?.();
    }
    return result;
  }, [actions, onRefresh]);

  const handleApproveClaim = React.useCallback(
    async (approvedAmount?: number, notes?: string) => {
      const result = await actions.approveClaim(approvedAmount, notes);
      if (result.success) {
        setApproveOpen(false);
        onRefresh?.();
      }
      return result;
    },
    [actions, onRefresh]
  );

  const handleRejectClaim = React.useCallback(
    async (reason: string) => {
      const result = await actions.rejectClaim(reason);
      if (result.success) {
        setRejectOpen(false);
        onRefresh?.();
      }
      return result;
    },
    [actions, onRefresh]
  );

  const handleAddDocument = React.useCallback(async () => {
    // Document upload — future file-picker integration
  }, []);

  // Handle close with exit animation
  const handleClose = React.useCallback(() => {
    setIsOpen(false);
    if (onClose) {
      setTimeout(onClose, 210);
    }
  }, [onClose]);

  const handleBack = React.useCallback(() => {
    if (onBack) {
      onBack();
    } else {
      handleClose();
    }
  }, [onBack, handleClose]);

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Warranty Claim"
        title={displayTitle}
        onBack={handleBack}
        onClose={handleClose}
      />

      {/* Main content — padded top to clear fixed header (56px = h-14) */}
      <main
        className={cn(
          'pt-14',
          'px-10 md:px-6 sm:px-4',
          'max-w-[800px] mx-auto',
          'pb-12'
        )}
      >
        {/* -------------------------------------------------------------------
            Title block: title, status pill
            Gap from header: 24px (--space-6)
            ------------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={claim.description}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
          />
        </div>

        {/* -------------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md
            ------------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={warrantyVitalSigns} />
        </div>

        {/* -------------------------------------------------------------------
            Workflow action buttons
            - Draft: Submit button (any crew)
            - Submitted: Approve + Reject buttons (HOD+ only)
            Visible only if user has relevant permissions — hidden, not disabled
            ------------------------------------------------------------------- */}
        {(
          (isDraft && perms.canSubmit) ||
          (isSubmitted && perms.canApprove)
        ) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {isDraft && perms.canSubmit && (
              <PrimaryButton
                onClick={() => setSubmitOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Submit Claim
              </PrimaryButton>
            )}
            {isSubmitted && perms.canApprove && (
              <>
                <PrimaryButton
                  onClick={() => setApproveOpen(true)}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Approve
                </PrimaryButton>
                <GhostButton
                  onClick={() => setRejectOpen(true)}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2 text-status-critical hover:text-status-critical"
                >
                  Reject
                </GhostButton>
              </>
            )}
          </div>
        )}

        {/* Section divider */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* -------------------------------------------------------------------
            Claim Details Section
            ------------------------------------------------------------------- */}
        <div className="mt-6">
          <ClaimDetailsSection claim={claim} stickyTop={56} />
        </div>

        {/* -------------------------------------------------------------------
            Linked Entities Section — Equipment + Fault
            ------------------------------------------------------------------- */}
        <div className="mt-6">
          <LinkedEntitiesSection
            equipmentId={claim.equipment_id}
            equipmentName={claim.equipment_name}
            faultId={claim.fault_id}
            faultCode={claim.fault_code}
            stickyTop={56}
          />
        </div>

        {/* -------------------------------------------------------------------
            Documents Section — warranty certificates, claim forms, correspondence
            ------------------------------------------------------------------- */}
        <div className="mt-6">
          <WarrantyDocumentsSection
            documents={documents}
            onAddDocument={handleAddDocument}
            canAddDocument={perms.canAddDocument}
            stickyTop={56}
          />
        </div>

        {/* -------------------------------------------------------------------
            History Section — read-only audit log
            ------------------------------------------------------------------- */}
        <div className="mt-6">
          <HistorySection history={history} stickyTop={56} />
        </div>
      </main>

      {/* -------------------------------------------------------------------
          Action Modals — rendered at lens root for correct z-index stacking
          ------------------------------------------------------------------- */}

      <SubmitClaimModal
        open={submitOpen}
        onClose={() => setSubmitOpen(false)}
        onSubmit={handleSubmitClaim}
        isLoading={actions.isLoading}
        claimTitle={displayTitle}
      />

      <ApproveClaimModal
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        onSubmit={handleApproveClaim}
        isLoading={actions.isLoading}
        claimTitle={displayTitle}
        claimedAmount={claim.claimed_amount}
        currency={claim.currency ?? 'USD'}
      />

      <RejectClaimModal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        onSubmit={handleRejectClaim}
        isLoading={actions.isLoading}
        claimTitle={displayTitle}
      />
    </LensContainer>
  );
});

WarrantyLens.displayName = 'WarrantyLens';

export default WarrantyLens;
