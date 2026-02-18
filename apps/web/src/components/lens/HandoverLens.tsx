'use client';

/**
 * HandoverLens - Full-screen entity lens for crew rotation handovers.
 *
 * Per CLAUDE.md and UI_SPEC.md — mirrors WorkOrderLens structure exactly:
 * - Fixed LensHeader (56px): back button, "Handover" overline, close button
 * - LensTitleBlock: handover title with status pill
 * - VitalSignsRow: 5 indicators (status, outgoing crew, incoming crew, items count, export status)
 * - Sections: HandoverItemsSection, SignaturesSection, HandoverExportsSection
 * - Dual signature flow: finalize → outgoing signs → incoming signs → complete
 * - Export to PDF after complete
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * NO UUID visible anywhere in the header.
 * Status colour mapper is local to this lens (domain-specific logic).
 *
 * FE-03-02: Handover Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';

// Handover-specific sections (co-located)
import { HandoverItemsSection } from './handover-sections/HandoverItemsSection';
import { SignaturesSection } from './handover-sections/SignaturesSection';
import { HandoverExportsSection } from './handover-sections/HandoverExportsSection';

// Action hook + permissions
import { useHandoverActions, useHandoverPermissions } from '@/hooks/useHandoverActions';

// Shared UI
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// SignaturePrompt for ownership transfer flow
import SignaturePrompt from '@/components/celeste/SignaturePrompt';
import type { DiffItem } from '@/components/celeste/MutationPreview';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export type HandoverStatus =
  | 'draft'
  | 'pending_signatures'
  | 'complete';

export type HandoverItemEntityType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'document'
  | 'note';

export interface HandoverItem {
  id: string;
  summary: string;
  section?: string;
  is_critical?: boolean;
  requires_action?: boolean;
  category?: 'fyi' | 'action_required' | 'critical' | 'resolved';
  entity_type: HandoverItemEntityType;
  entity_id: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  created_at: string;
  added_by?: string;
  risk_tags?: string[];
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  status?: 'pending' | 'acknowledged' | 'actioned' | 'closed';
}

export interface HandoverExport {
  id: string;
  export_date: string;
  department?: string;
  file_url?: string;
  outgoing_user_id?: string;
  outgoing_user_name?: string;
  outgoing_signed_at?: string;
  incoming_user_id?: string;
  incoming_user_name?: string;
  incoming_signed_at?: string;
  signoff_complete?: boolean;
}

export interface HandoverSignature {
  user_id: string;
  user_name: string;
  signed_at: string;
  role: 'outgoing' | 'incoming';
}

export interface HandoverLensData {
  id: string;
  /** Handover title for display — never show raw UUID */
  title: string;
  /** Status enum: draft | pending_signatures | complete */
  status: HandoverStatus;
  /** Outgoing crew member name */
  outgoing_crew_name?: string;
  /** Outgoing crew member user ID */
  outgoing_crew_id?: string;
  /** Incoming crew member name */
  incoming_crew_name?: string;
  /** Incoming crew member user ID */
  incoming_crew_id?: string;
  /** Handover items */
  items?: HandoverItem[];
  /** Exports with signature tracking */
  exports?: HandoverExport[];
  /** Outgoing signature record */
  outgoing_signature?: HandoverSignature;
  /** Incoming signature record */
  incoming_signature?: HandoverSignature;
  /** When handover was finalized (locked for signatures) */
  finalized_at?: string;
  /** Department context (engineering, deck, etc.) */
  department?: string;
  /** Record creation timestamp */
  created_at: string;
}

export interface HandoverLensProps {
  /** The handover data to render */
  handover: HandoverLensData;
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
// Colour mapping helpers
// ---------------------------------------------------------------------------

/**
 * Map handover status to StatusPill color.
 * draft = neutral, pending_signatures = warning, complete = success
 */
function mapStatusToColor(
  status: HandoverStatus
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'complete':
      return 'success';
    case 'pending_signatures':
      return 'warning';
    case 'draft':
    default:
      return 'neutral';
  }
}

/**
 * Format a handover status enum to a human-readable label.
 */
function formatStatusLabel(status: HandoverStatus): string {
  const labels: Record<HandoverStatus, string> = {
    draft: 'Draft',
    pending_signatures: 'Pending Signatures',
    complete: 'Complete',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Signature flow types
// ---------------------------------------------------------------------------

type SignatureStep = 'none' | 'outgoing' | 'incoming';

// ---------------------------------------------------------------------------
// HandoverLens component
// ---------------------------------------------------------------------------

/**
 * HandoverLens — Full-screen entity lens for crew rotation handovers.
 *
 * Usage:
 * ```tsx
 * <HandoverLens
 *   handover={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const HandoverLens = React.forwardRef<
  HTMLDivElement,
  HandoverLensProps
>(({ handover, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Dual signature flow state
  // 'none' = no signature prompt visible
  // 'outgoing' = outgoing crew is signing
  // 'incoming' = incoming crew is signing
  const [signatureStep, setSignatureStep] = React.useState<SignatureStep>('none');

  // Actions and permissions
  const actions = useHandoverActions(handover.id);
  const perms = useHandoverPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  const displayTitle = handover.title;
  const statusColor = mapStatusToColor(handover.status);
  const statusLabel = formatStatusLabel(handover.status);

  // Item counts
  const items = handover.items ?? [];
  const exports = handover.exports ?? [];
  const itemCount = items.length;

  // Export status display
  const latestExport = exports[0];
  const exportStatusValue = latestExport?.signoff_complete
    ? 'PDF Ready'
    : exports.length > 0
    ? 'PDF Pending'
    : 'Not Exported';

  // Build the 5 vital signs per plan spec
  const handoverVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Outgoing',
      value: handover.outgoing_crew_name ?? 'Unassigned',
    },
    {
      label: 'Incoming',
      value: handover.incoming_crew_name ?? 'Unassigned',
    },
    {
      label: 'Items',
      value: `${itemCount} item${itemCount === 1 ? '' : 's'}`,
    },
    {
      label: 'Export',
      value: exportStatusValue,
      // Teal color when PDF is ready
      color: latestExport?.signoff_complete ? 'success' : undefined,
    },
  ];

  // Determine which action buttons to show based on status and permissions
  const isDraft = handover.status === 'draft';
  const isPendingSignatures = handover.status === 'pending_signatures';
  const isComplete = handover.status === 'complete';

  // Outgoing has signed when outgoing_signature is present
  const hasOutgoingSigned = !!handover.outgoing_signature;
  // Incoming can only sign after outgoing has signed
  const hasIncomingSigned = !!handover.incoming_signature;

  // Can the current user sign as outgoing?
  // Only if status=pending_signatures and outgoing hasn't signed yet
  const canSignOutgoing =
    perms.canSignOutgoing && isPendingSignatures && !hasOutgoingSigned;

  // Can the current user sign as incoming?
  // Only if status=pending_signatures and outgoing has signed but incoming hasn't
  const canSignIncoming =
    perms.canSignIncoming && isPendingSignatures && hasOutgoingSigned && !hasIncomingSigned;

  // Can export? Only if complete
  const canExport = perms.canExport && isComplete;

  // -------------------------------------------------------------------------
  // Signature prompt diffs
  // -------------------------------------------------------------------------

  const outgoingDiffs: DiffItem[] = [
    {
      field: 'Handover',
      before: handover.title,
      after: 'Signed by Outgoing Crew',
    },
    {
      field: 'Items',
      before: `${itemCount} items`,
      after: 'Handed over',
    },
    {
      field: 'Outgoing Crew',
      before: handover.outgoing_crew_name ?? 'Unknown',
      after: 'Signed',
    },
  ];

  const incomingDiffs: DiffItem[] = [
    {
      field: 'Handover',
      before: handover.title,
      after: 'Signed by Incoming Crew',
    },
    {
      field: 'Incoming Crew',
      before: handover.incoming_crew_name ?? 'Unknown',
      after: 'Signed — Handover Complete',
    },
  ];

  // -------------------------------------------------------------------------
  // Action handlers
  // -------------------------------------------------------------------------

  const handleFinalizeHandover = React.useCallback(async () => {
    const result = await actions.finalizeHandover();
    if (result.success) onRefresh?.();
  }, [actions, onRefresh]);

  const handleAddItem = React.useCallback(async () => {
    // AddItem flows through modal — future: wire AddHandoverItemModal
    // For now, trigger the add_handover_item action placeholder
  }, []);

  const handleAcknowledgeItem = React.useCallback(async (itemId: string) => {
    const result = await actions.acknowledgeItem(itemId);
    if (result.success) onRefresh?.();
  }, [actions, onRefresh]);

  const handleExport = React.useCallback(async () => {
    const result = await actions.exportHandover();
    if (result.success) onRefresh?.();
  }, [actions, onRefresh]);

  const handleNavigateToEntity = React.useCallback((entityType: string, entityId: string) => {
    // Navigate to entity lens — standard pattern
    const routeMap: Record<string, string> = {
      fault: 'faults',
      work_order: 'work-orders',
      equipment: 'equipment',
      part: 'parts',
      document: 'documents',
    };
    const route = routeMap[entityType];
    if (route) {
      window.location.href = `/${route}/${entityId}`;
    }
  }, []);

  // Sign outgoing: submit signature then refresh
  const handleSignOutgoing = React.useCallback(async () => {
    const result = await actions.signOutgoing();
    if (result.success) {
      setSignatureStep('none');
      onRefresh?.();
    }
  }, [actions, onRefresh]);

  // Sign incoming: submit signature then refresh
  const handleSignIncoming = React.useCallback(async () => {
    const result = await actions.signIncoming();
    if (result.success) {
      setSignatureStep('none');
      onRefresh?.();
    }
  }, [actions, onRefresh]);

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

  // -------------------------------------------------------------------------
  // Render SignaturePrompt overlay (dual signature flow)
  // -------------------------------------------------------------------------

  if (signatureStep === 'outgoing') {
    return (
      <SignaturePrompt
        diffs={outgoingDiffs}
        userName={handover.outgoing_crew_name ?? 'Outgoing Crew'}
        onSign={handleSignOutgoing}
        onCancel={() => setSignatureStep('none')}
        isCommitting={actions.isLoading}
      />
    );
  }

  if (signatureStep === 'incoming') {
    return (
      <SignaturePrompt
        diffs={incomingDiffs}
        userName={handover.incoming_crew_name ?? 'Incoming Crew'}
        onSign={handleSignIncoming}
        onCancel={() => setSignatureStep('none')}
        isCommitting={actions.isLoading}
      />
    );
  }

  // -------------------------------------------------------------------------
  // Main lens render
  // -------------------------------------------------------------------------

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Handover"
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
        {/* ---------------------------------------------------------------
            Title block: title + status pill
            Gap from header: 24px
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={handover.department ? `${handover.department} Department` : undefined}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={handoverVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Action buttons — role-gated, hidden not disabled
            --------------------------------------------------------------- */}
        {(perms.canFinalize || canSignOutgoing || canSignIncoming || canExport) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {/* Finalize — locks the handover for signatures (draft only) */}
            {perms.canFinalize && isDraft && (
              <PrimaryButton
                onClick={handleFinalizeHandover}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Finalize Handover
              </PrimaryButton>
            )}

            {/* Sign as Outgoing — outgoing crew signs first */}
            {canSignOutgoing && (
              <PrimaryButton
                onClick={() => setSignatureStep('outgoing')}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Sign as Outgoing
              </PrimaryButton>
            )}

            {/* Sign as Incoming — only after outgoing has signed */}
            {canSignIncoming && (
              <PrimaryButton
                onClick={() => setSignatureStep('incoming')}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Sign as Incoming
              </PrimaryButton>
            )}

            {/* Export to PDF — only after complete */}
            {canExport && (
              <GhostButton
                onClick={handleExport}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Export to PDF
              </GhostButton>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            Dual signature progress banner (pending_signatures state)
            Shows which signatures are still needed
            --------------------------------------------------------------- */}
        {isPendingSignatures && (
          <div className="mt-4 p-3 rounded-md border border-status-warning/30 bg-status-warning-bg">
            <div className="flex items-center gap-3 text-[13px]">
              <div className={cn(
                'flex items-center gap-1.5',
                hasOutgoingSigned ? 'text-status-success' : 'text-status-warning'
              )}>
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  hasOutgoingSigned ? 'bg-status-success' : 'bg-status-warning'
                )} />
                <span>Outgoing: {hasOutgoingSigned ? 'Signed' : 'Awaiting'}</span>
              </div>
              <span className="text-txt-tertiary">·</span>
              <div className={cn(
                'flex items-center gap-1.5',
                hasIncomingSigned ? 'text-status-success' : 'text-status-neutral'
              )}>
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  hasIncomingSigned ? 'bg-status-success' : 'bg-surface-border'
                )} />
                <span>Incoming: {hasIncomingSigned ? 'Signed' : 'Awaiting'}</span>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Handover Items Section
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <HandoverItemsSection
            items={items}
            onNavigate={handleNavigateToEntity}
            onAcknowledge={handleAcknowledgeItem}
            onAddItem={perms.canAddItem && isDraft ? handleAddItem : undefined}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Signatures Section — shows outgoing + incoming signature status
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <SignaturesSection
            outgoingSignature={handover.outgoing_signature}
            incomingSignature={handover.incoming_signature}
            outgoingCrewName={handover.outgoing_crew_name}
            incomingCrewName={handover.incoming_crew_name}
            status={handover.status}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Exports Section — export history + download links
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <HandoverExportsSection
            exports={exports}
            onExport={canExport ? handleExport : undefined}
            onViewExport={(exportId) => {
              const exp = exports.find((e) => e.id === exportId);
              if (exp?.file_url) window.open(exp.file_url, '_blank');
            }}
            stickyTop={56}
          />
        </div>
      </main>
    </LensContainer>
  );
});

HandoverLens.displayName = 'HandoverLens';

export default HandoverLens;
