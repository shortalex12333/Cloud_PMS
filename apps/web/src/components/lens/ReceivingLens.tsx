'use client';

/**
 * ReceivingLens - Full-screen entity lens for receiving records.
 *
 * Per CLAUDE.md and UI_SPEC.md:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: supplier name as display title
 * - VitalSignsRow: 5 indicators (status, supplier, PO number, items count, receiver)
 * - Sections: Line Items, Documents, History
 * - Rejection flow: RejectModal with reason dropdown + signature (HOD+)
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * FE-03-01: Receiving Lens Rebuild with rejection flow
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';

// Sections
import {
  ReceivingLineItemsSection,
  ReceivingDocumentsSection,
  type ReceivingLineItem,
  type ReceivingDocument,
} from './receiving-sections';

import {
  HistorySection,
  type AuditLogEntry,
} from './sections';

// Rejection flow
import { RejectModal } from './actions/RejectModal';

// Actions hook + permissions
import { useReceivingActions, useReceivingPermissions } from '@/hooks/useReceivingActions';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface ReceivingLensData {
  id: string;
  /** Human-readable reference — NEVER show raw id UUID */
  reference?: string;
  /** Supplier / vendor name */
  supplier_name?: string;
  /** Purchase order number */
  po_number?: string;
  /** Status enum: draft | pending | accepted | rejected */
  status: string;
  /** Name of the crew member who received the delivery */
  received_by_name?: string;
  received_by?: string;
  /** When the receiving record was created */
  created_at: string;
  /** When the receiving was accepted */
  accepted_at?: string;
  /** When the receiving was rejected */
  rejected_at?: string;
  /** Reason for rejection */
  rejection_reason?: string;
  /** Line items from pms_receiving_items */
  items?: ReceivingLineItem[];
  /** Documents from pms_receiving_documents */
  documents?: ReceivingDocument[];
  /** Audit log entries */
  history?: AuditLogEntry[];
}

export interface ReceivingLensProps {
  /** The receiving record data to render */
  receiving: ReceivingLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers
// ---------------------------------------------------------------------------

/**
 * Map receiving status string to StatusPill color level.
 * Per UI_SPEC.md status colour mapping.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected':
      return 'critical';
    case 'pending':
    case 'in_review':
      return 'warning';
    case 'accepted':
      return 'success';
    case 'draft':
    default:
      return 'neutral';
  }
}

/**
 * Format a receiving status enum to a human-readable display label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    pending: 'Pending',
    in_review: 'In Review',
    accepted: 'Accepted',
    rejected: 'Rejected',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// ReceivingLens component
// ---------------------------------------------------------------------------

/**
 * ReceivingLens — Full-screen entity lens for receiving records.
 *
 * Usage:
 * ```tsx
 * <ReceivingLens
 *   receiving={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const ReceivingLens = React.forwardRef<
  HTMLDivElement,
  ReceivingLensProps
>(({ receiving, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility
  const [rejectOpen, setRejectOpen] = React.useState(false);

  // Actions and permissions
  const actions = useReceivingActions(receiving.id);
  const perms = useReceivingPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  // Use supplier name as display title, falling back to reference
  const displayTitle = receiving.supplier_name
    ? receiving.supplier_name
    : receiving.reference ?? 'Receiving Record';

  const statusColor = mapStatusToColor(receiving.status);
  const statusLabel = formatStatusLabel(receiving.status);

  // Item count
  const itemCount = receiving.items?.length ?? 0;

  // Build the 5 vital signs per plan spec
  const receivingVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Supplier',
      value: receiving.supplier_name ?? '—',
    },
    {
      label: 'PO Number',
      value: receiving.po_number ?? '—',
    },
    {
      label: 'Items',
      value: `${itemCount} item${itemCount === 1 ? '' : 's'}`,
    },
    {
      label: 'Receiver',
      value: receiving.received_by_name ?? '—',
    },
  ];

  // Section data (safe fallbacks)
  const items = receiving.items ?? [];
  const documents = receiving.documents ?? [];
  const history = receiving.history ?? [];

  // Whether the record can still be acted on
  const isActionable = !['accepted', 'rejected'].includes(receiving.status);

  // Action handlers — wrap hook methods with refresh callback
  const handleAccept = React.useCallback(async (signature: Record<string, unknown>) => {
    const result = await actions.acceptReceiving(signature);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleReject = React.useCallback(async (reason: string, customReason?: string, signature?: Record<string, unknown>) => {
    const finalReason = reason === 'other' && customReason ? customReason : reason;
    const result = await actions.rejectReceiving(finalReason, signature ?? {});
    if (result.success) {
      setRejectOpen(false);
      onRefresh?.();
    }
    return result;
  }, [actions, onRefresh]);

  // Handle close with exit animation: flip isOpen → false, then call onClose after 200ms
  const handleClose = React.useCallback(() => {
    setIsOpen(false);
    if (onClose) {
      setTimeout(onClose, 210); // Wait for exit animation (200ms + buffer)
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
        entityType="Receiving"
        title={displayTitle}
        onBack={handleBack}
        onClose={handleClose}
      />

      {/* Main content — padded top to clear fixed header (56px = h-14) */}
      <main
        className={cn(
          // Clear the fixed header
          'pt-14',
          // Lens body padding: 40px desktop, responsive
          'px-10 md:px-6 sm:px-4',
          // Max content width: 800px centered per spec
          'max-w-[800px] mx-auto',
          // Top breathing room below header
          'pb-12'
        )}
      >
        {/* ---------------------------------------------------------------
            Title block: supplier name as title, optional reference subtitle
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={receiving.reference ? `Ref: ${receiving.reference}` : undefined}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={receivingVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Header action buttons (Accept, Reject)
            Visible only if user has relevant permissions — hidden, not disabled
            --------------------------------------------------------------- */}
        {(perms.canAccept || perms.canReject) && isActionable && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {perms.canAccept && (
              <PrimaryButton
                onClick={() => handleAccept({ signed_by: 'user', timestamp: new Date().toISOString() })}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Accept
              </PrimaryButton>
            )}
            {perms.canReject && (
              <GhostButton
                onClick={() => setRejectOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2 text-status-critical hover:text-status-critical"
              >
                Reject
              </GhostButton>
            )}
          </div>
        )}

        {/* Rejected state: show rejection reason if set */}
        {receiving.status === 'rejected' && receiving.rejection_reason && (
          <div className="mt-4 px-4 py-3 rounded-[var(--radius-sm)] bg-status-critical-bg border border-status-critical/30">
            <p className="text-[13px] font-medium text-status-critical">Rejection reason</p>
            <p className="text-[14px] text-txt-primary mt-1">{receiving.rejection_reason}</p>
          </div>
        )}

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px per spec
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Line Items Section
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <ReceivingLineItemsSection
            items={items}
            canAddItem={false}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Documents Section
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <ReceivingDocumentsSection
            documents={documents}
            canAddDocument={false}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            History Section — read-only, no action button per spec
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <HistorySection history={history} stickyTop={56} />
        </div>
      </main>

      {/* ---------------------------------------------------------------
          Action Modals — rendered at lens root for correct z-index stacking
          --------------------------------------------------------------- */}

      <RejectModal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        onSubmit={handleReject}
        isLoading={actions.isLoading}
        entityTitle={displayTitle}
        entityType="receiving"
      />
    </LensContainer>
  );
});

ReceivingLens.displayName = 'ReceivingLens';

export default ReceivingLens;
