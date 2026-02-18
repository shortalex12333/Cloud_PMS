'use client';

/**
 * FaultLens - Full-screen entity lens for faults.
 *
 * Per CLAUDE.md and UI_SPEC.md — mirrors WorkOrderLens structure exactly:
 * - Fixed LensHeader (56px): back button, "Fault" overline, close button
 * - LensTitleBlock: fault_code — title, severity + status pills
 * - VitalSignsRow: 5 indicators (status, severity, equipment link, reporter, age)
 * - Section containers: Description, Photos, Notes, History (stickyTop={56})
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * NO UUID visible anywhere. fault_code (FLT-YYYY-000001) used as display prefix.
 * Status/severity colour mappers are local to this lens (domain-specific logic).
 *
 * FE-02-01: Fault Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';

// Sections (re-used from Work Order lens)
import {
  NotesSection,
  HistorySection,
  type WorkOrderNote,
  type AuditLogEntry,
} from './sections';

// Fault-specific sections
import { DescriptionSection } from './sections/DescriptionSection';
import { FaultPhotosSection } from './sections/FaultPhotosSection';

// Action hook + permissions
import { useFaultActions, useFaultPermissions } from '@/hooks/useFaultActions';

// Shared UI
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// Add note modal (reuse from work order actions)
import { AddNoteModal } from './actions';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface FaultLensData {
  id: string;
  /** System fault code e.g. "FLT-2026-000001" — NEVER show raw id UUID */
  fault_code?: string;
  /** Short fault title */
  title?: string;
  /** Detailed fault description */
  description?: string;
  /** Severity: cosmetic | minor | major | critical | safety */
  severity: string;
  /** Status: open | work_ordered | resolved | closed */
  status?: string;
  /** acknowledged_at: non-null when fault has been acknowledged */
  acknowledged_at?: string;
  /** FK to pms_equipment */
  equipment_id?: string;
  /** Denormalized equipment name for display */
  equipment_name?: string;
  /** ISO timestamp when fault was detected */
  detected_at?: string;
  /** ISO timestamp of record creation */
  created_at: string;
  /** ISO timestamp when fault was resolved (null = still open) */
  resolved_at?: string;
  /** User who reported (name string from metadata or denormalized join) */
  reporter_name?: string;
  /** Computed: days since detected_at */
  days_open?: number;
  /** Whether a work order has been raised from this fault */
  has_work_order?: boolean;
  /** Notes attached to the fault */
  notes?: WorkOrderNote[];
  /** Audit log entries */
  history?: AuditLogEntry[];
  /** Photo attachments */
  photos?: FaultPhoto[];
}

export interface FaultPhoto {
  id: string;
  storage_path: string;
  caption?: string;
  created_at: string;
  mime_type?: string;
  file_name?: string;
  file_size?: number;
}

export interface FaultLensProps {
  /** The fault data to render */
  fault: FaultLensData;
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
// Colour mapping helpers — domain-specific, local to this lens
// ---------------------------------------------------------------------------

/**
 * Map fault status string to StatusPill color level.
 * Fault lifecycle: open → work_ordered → resolved → closed
 * acknowledged_at is a boolean flag on the fault, not a status transition.
 */
function mapStatusToColor(
  status: string,
  acknowledgedAt?: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  // If acknowledged but still open, show warning (in progress)
  if (acknowledgedAt && status === 'open') return 'warning';

  switch (status) {
    case 'resolved':
    case 'closed':
      return 'success';
    case 'work_ordered':
      return 'warning';
    case 'open':
    default:
      return 'critical'; // Open unacknowledged fault is urgent
  }
}

/**
 * Human-readable fault status label.
 * Acknowledges the fault's acknowledged state when status is still 'open'.
 */
function formatStatusLabel(status: string, acknowledgedAt?: string): string {
  if (acknowledgedAt && status === 'open') return 'Acknowledged';
  const labels: Record<string, string> = {
    open: 'Open',
    work_ordered: 'Work Ordered',
    resolved: 'Resolved',
    closed: 'Closed',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Map fault severity string to StatusPill color level.
 * Severities: cosmetic | minor | major | critical | safety
 */
function mapSeverityToColor(
  severity: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity) {
    case 'critical':
    case 'safety':
      return 'critical';
    case 'major':
      return 'warning';
    case 'minor':
    case 'cosmetic':
    default:
      return 'neutral';
  }
}

/**
 * Human-readable severity label.
 */
function formatSeverityLabel(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

// ---------------------------------------------------------------------------
// FaultLens component
// ---------------------------------------------------------------------------

/**
 * FaultLens — Full-screen entity lens for faults.
 *
 * Usage:
 * ```tsx
 * <FaultLens
 *   fault={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const FaultLens = React.forwardRef<HTMLDivElement, FaultLensProps>(
  ({ fault, onBack, onClose, className, onRefresh }, ref) => {
    // Glass transition: lens mounts as closed then opens on first render
    const [isOpen, setIsOpen] = React.useState(false);

    // Modal visibility
    const [addNoteOpen, setAddNoteOpen] = React.useState(false);

    // Actions and permissions
    const actions = useFaultActions(fault.id);
    const perms = useFaultPermissions();

    useEffect(() => {
      // Trigger glass enter animation on mount
      setIsOpen(true);
    }, []);

    // Derived display values — never expose raw UUID
    const displayTitle = fault.fault_code
      ? `${fault.fault_code} — ${fault.title ?? 'Fault Report'}`
      : (fault.title ?? 'Fault Report');

    const currentStatus = fault.status ?? 'open';
    const statusColor = mapStatusToColor(currentStatus, fault.acknowledged_at);
    const severityColor = mapSeverityToColor(fault.severity);
    const statusLabel = formatStatusLabel(currentStatus, fault.acknowledged_at);
    const severityLabel = formatSeverityLabel(fault.severity);

    // Build the 5 vital signs per plan spec
    const faultVitalSigns: VitalSign[] = [
      {
        label: 'Status',
        value: statusLabel,
        color: statusColor,
      },
      {
        label: 'Severity',
        value: severityLabel,
        color: severityColor,
      },
      {
        label: 'Equipment',
        value: fault.equipment_name ?? 'None',
        // Equipment link is teal and clickable when equipment_id is present
        href: fault.equipment_id ? `/equipment/${fault.equipment_id}` : undefined,
      },
      {
        label: 'Reporter',
        value: fault.reporter_name ?? '—',
      },
      {
        label: 'Age',
        value: fault.detected_at
          ? formatRelativeTime(fault.detected_at)
          : fault.created_at
          ? formatRelativeTime(fault.created_at)
          : '—',
      },
    ];

    // Section data (safe fallbacks)
    const notes = fault.notes ?? [];
    const history = fault.history ?? [];
    const photos = fault.photos ?? [];

    // Whether the fault can still be acted on
    const isOpen_ = !['resolved', 'closed'].includes(currentStatus);
    const isClosed = ['resolved', 'closed'].includes(currentStatus);

    // Action handlers — wrap hook methods with refresh callback
    const handleAddNote = React.useCallback(
      async (noteText: string) => {
        const result = await actions.addNote(noteText);
        if (result.success) onRefresh?.();
        return result;
      },
      [actions, onRefresh]
    );

    const handleAcknowledge = React.useCallback(async () => {
      const result = await actions.acknowledgeFault();
      if (result.success) onRefresh?.();
    }, [actions, onRefresh]);

    const handleClose_ = React.useCallback(() => {
      setIsOpen(false);
      if (onClose) {
        setTimeout(onClose, 210); // Wait for exit animation (200ms + buffer)
      }
    }, [onClose]);

    const handleBack = React.useCallback(() => {
      if (onBack) {
        onBack();
      } else {
        handleClose_();
      }
    }, [onBack, handleClose_]);

    return (
      <LensContainer
        ref={ref}
        isOpen={isOpen}
        onClose={handleClose_}
        className={className}
      >
        {/* Fixed navigation header — 56px, at z-header */}
        <LensHeader
          entityType="Fault"
          title={displayTitle}
          onBack={handleBack}
          onClose={handleClose_}
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
            // Bottom breathing room
            'pb-12'
          )}
        >
          {/* ---------------------------------------------------------------
              Title block: fault code + title, severity + status pills
              Gap from header: 24px (--space-6)
              --------------------------------------------------------------- */}
          <div className="mt-6">
            <LensTitleBlock
              title={displayTitle}
              subtitle={fault.description}
              status={{
                label: statusLabel,
                color: statusColor,
              }}
              priority={{
                label: severityLabel,
                color: severityColor,
              }}
            />
          </div>

          {/* ---------------------------------------------------------------
              Vital Signs Row — 5 indicators
              Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
              --------------------------------------------------------------- */}
          <div className="mt-3">
            <VitalSignsRow signs={faultVitalSigns} />
          </div>

          {/* ---------------------------------------------------------------
              Header action buttons — hidden (not disabled) per role
              --------------------------------------------------------------- */}
          {(perms.canAcknowledge || perms.canClose || perms.canReopen) && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              {/* Acknowledge — visible for HOD+ when fault is open and not yet acknowledged */}
              {perms.canAcknowledge && !fault.acknowledged_at && isOpen_ && (
                <GhostButton
                  onClick={handleAcknowledge}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Acknowledge
                </GhostButton>
              )}
              {/* Close Fault — visible for chief_engineer/chief_officer/captain when fault is open */}
              {perms.canClose && isOpen_ && (
                <PrimaryButton
                  onClick={() => {
                    // Close fault — future: dedicated CloseModal with resolution notes
                    actions.closeFault().then((r) => { if (r.success) onRefresh?.(); });
                  }}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Close Fault
                </PrimaryButton>
              )}
              {/* Reopen — visible for chief_engineer/chief_officer/captain when fault is closed */}
              {perms.canReopen && isClosed && (
                <GhostButton
                  onClick={() => {
                    actions.reopenFault().then((r) => { if (r.success) onRefresh?.(); });
                  }}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Reopen Fault
                </GhostButton>
              )}
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
              Description Section — read-only fault description
              stickyTop={56}: sticky headers clear the 56px fixed LensHeader
              --------------------------------------------------------------- */}
          {fault.description && (
            <div className="mt-6">
              <DescriptionSection
                description={fault.description}
                stickyTop={56}
              />
            </div>
          )}

          {/* ---------------------------------------------------------------
              Photos Section — fault photos, Add Photo button for crew+
              --------------------------------------------------------------- */}
          <div className="mt-6">
            <FaultPhotosSection
              photos={photos}
              onAddPhoto={() => {
                // Photo upload — future file-picker integration (add_fault_photo)
              }}
              canAddPhoto={perms.canAddPhoto}
              stickyTop={56}
            />
          </div>

          {/* ---------------------------------------------------------------
              Notes Section — Add Note CTA shown for crew+
              --------------------------------------------------------------- */}
          <div className="mt-6">
            <NotesSection
              notes={notes}
              onAddNote={() => setAddNoteOpen(true)}
              canAddNote={perms.canAddNote}
              stickyTop={56}
            />
          </div>

          {/* ---------------------------------------------------------------
              History Section — read-only audit trail
              --------------------------------------------------------------- */}
          <div className="mt-6">
            <HistorySection history={history} stickyTop={56} />
          </div>
        </main>

        {/* ---------------------------------------------------------------
            Action Modals — rendered at lens root for correct z-index stacking
            --------------------------------------------------------------- */}

        <AddNoteModal
          open={addNoteOpen}
          onClose={() => setAddNoteOpen(false)}
          onSubmit={handleAddNote}
          isLoading={actions.isLoading}
        />
      </LensContainer>
    );
  }
);

FaultLens.displayName = 'FaultLens';

export default FaultLens;
