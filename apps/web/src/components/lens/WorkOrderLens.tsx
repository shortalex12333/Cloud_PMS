'use client';

/**
 * WorkOrderLens - Reference implementation for the lens header pattern.
 *
 * Per CLAUDE.md and UI_SPEC.md:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: 28px display title, status + priority pills
 * - VitalSignsRow: 5 indicators (status, priority, parts, created, equipment)
 * - NO UUID visible anywhere in the header
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * This is the reference implementation — all other lenses inherit this structure.
 *
 * FE-01-03: All 4 sections + 5 action modals + role-based visibility
 * FE-01-05: Full-Screen Lens Layout + Glass Transitions
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
  NotesSection,
  PartsSection,
  AttachmentsSection,
  HistorySection,
  type WorkOrderNote,
  type WorkOrderPart,
  type Attachment,
  type AuditLogEntry,
} from './sections';

// Action modals
import {
  AddNoteModal,
  AddPartModal,
  MarkCompleteModal,
  ReassignModal,
  ArchiveModal,
  type PartOption,
  type CrewMember,
} from './actions';

// Action hook + permissions
import { useWorkOrderActions, useWorkOrderPermissions } from '@/hooks/useWorkOrderActions';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface WorkOrderLensData {
  id: string;
  /** Human-readable number e.g. "WO-2026-001" — NEVER show raw id UUID */
  wo_number?: string;
  title: string;
  description?: string;
  /** Status enum: draft | open | in_progress | pending_parts | completed | closed | cancelled */
  status: string;
  /** Priority enum: low | medium | high | critical */
  priority: string;
  equipment_id?: string;
  /** Denormalized equipment name for display */
  equipment_name?: string;
  assigned_to?: string;
  assigned_to_name?: string;
  created_at: string;
  completed_at?: string;
  due_date?: string;
  is_overdue?: boolean;
  days_open?: number;
  /** Count of linked work order parts */
  parts_count?: number;
  /** Notes for the work order */
  notes?: WorkOrderNote[];
  /** Parts used on the work order */
  parts?: WorkOrderPart[];
  /** Attachments on the work order */
  attachments?: Attachment[];
  /** Audit log entries */
  history?: AuditLogEntry[];
}

export interface WorkOrderLensProps {
  /** The work order data to render */
  workOrder: WorkOrderLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
  /** Available parts for the AddPart modal (from inventory) */
  availableParts?: PartOption[];
  /** Available crew for the Reassign modal */
  availableCrew?: CrewMember[];
}

// ---------------------------------------------------------------------------
// Colour mapping helpers
// ---------------------------------------------------------------------------

/**
 * Map work order status string to StatusPill color level.
 * Per UI_SPEC.md status colour mapping.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'overdue':
    case 'cancelled':
      return 'critical';
    case 'in_progress':
    case 'pending_parts':
      return 'warning';
    case 'completed':
    case 'closed':
      return 'success';
    case 'draft':
    case 'open':
    default:
      return 'neutral';
  }
}

/**
 * Map work order priority string to StatusPill color level.
 */
function mapPriorityToColor(
  priority: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (priority) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'warning';
    case 'medium':
      return 'neutral';
    case 'low':
    default:
      return 'neutral';
  }
}

/**
 * Format a status enum value to a human-readable display label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    open: 'Open',
    in_progress: 'In Progress',
    pending_parts: 'Pending Parts',
    completed: 'Completed',
    closed: 'Closed',
    cancelled: 'Cancelled',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Format a priority enum value to a human-readable display label.
 */
function formatPriorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

// ---------------------------------------------------------------------------
// WorkOrderLens component
// ---------------------------------------------------------------------------

/**
 * WorkOrderLens — Full-screen entity lens for work orders.
 *
 * Usage:
 * ```tsx
 * <WorkOrderLens
 *   workOrder={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const WorkOrderLens = React.forwardRef<
  HTMLDivElement,
  WorkOrderLensProps
>(({ workOrder, onBack, onClose, className, onRefresh, availableParts = [], availableCrew = [] }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [addPartOpen, setAddPartOpen] = React.useState(false);
  const [markCompleteOpen, setMarkCompleteOpen] = React.useState(false);
  const [reassignOpen, setReassignOpen] = React.useState(false);
  const [archiveOpen, setArchiveOpen] = React.useState(false);

  // Actions and permissions
  const actions = useWorkOrderActions(workOrder.id);
  const perms = useWorkOrderPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  const displayTitle = workOrder.wo_number
    ? `${workOrder.wo_number} — ${workOrder.title}`
    : workOrder.title;

  const statusColor = mapStatusToColor(workOrder.status);
  const priorityColor = mapPriorityToColor(workOrder.priority);
  const statusLabel = formatStatusLabel(workOrder.status);
  const priorityLabel = formatPriorityLabel(workOrder.priority);

  // Build the 5 vital signs as per plan spec
  const workOrderVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Priority',
      value: priorityLabel,
      color: priorityColor,
    },
    {
      label: 'Parts',
      value:
        workOrder.parts_count !== undefined
          ? `${workOrder.parts_count} part${workOrder.parts_count === 1 ? '' : 's'}`
          : '0 parts',
    },
    {
      label: 'Created',
      value: workOrder.created_at
        ? formatRelativeTime(workOrder.created_at)
        : '—',
    },
    {
      label: 'Equipment',
      value: workOrder.equipment_name ?? 'None',
      // Equipment link is teal and clickable when equipment_id is present
      href: workOrder.equipment_id
        ? `/equipment/${workOrder.equipment_id}`
        : undefined,
    },
  ];

  // Section data (safe fallbacks)
  const notes = workOrder.notes ?? [];
  const parts = workOrder.parts ?? [];
  const attachments = workOrder.attachments ?? [];
  const history = workOrder.history ?? [];

  // Whether the WO can still be closed/completed
  const isCloseable = !['completed', 'closed', 'cancelled'].includes(workOrder.status);

  // Action handlers — wrap hook methods with refresh callback
  const handleAddNote = React.useCallback(async (noteText: string) => {
    const result = await actions.addNote(noteText);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleAddPart = React.useCallback(async (partId: string, qty: number, unit?: string) => {
    const result = await actions.addPart(partId, qty, unit);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleMarkComplete = React.useCallback(async (completionNotes?: string) => {
    const result = await actions.closeWorkOrder(completionNotes);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleReassign = React.useCallback(async (assigneeId: string) => {
    const result = await actions.assignWorkOrder(assigneeId);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleArchive = React.useCallback(async (reason: string) => {
    const result = await actions.archiveWorkOrder(reason, {});
    if (result.success) onRefresh?.();
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
        entityType="Work Order"
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
            Title block: title, status/priority pills
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={workOrder.description}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
            priority={{
              label: priorityLabel,
              color: priorityColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={workOrderVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Header action buttons (Mark Complete, Reassign, Archive)
            Visible only if user has relevant permissions — hidden, not disabled
            --------------------------------------------------------------- */}
        {(perms.canClose || perms.canAssign || perms.canArchive) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {perms.canClose && isCloseable && (
              <PrimaryButton
                onClick={() => setMarkCompleteOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Mark Complete
              </PrimaryButton>
            )}
            {perms.canAssign && (
              <GhostButton
                onClick={() => setReassignOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Reassign
              </GhostButton>
            )}
            {perms.canArchive && (
              <GhostButton
                onClick={() => setArchiveOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2 text-status-critical hover:text-status-critical"
              >
                Archive
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
            Notes Section — Add Note CTA shown for HOD+
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
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
            Parts Section — Add Part CTA shown for chief_engineer/captain
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <PartsSection
            parts={parts}
            onAddPart={() => setAddPartOpen(true)}
            canAddPart={perms.canAddPart}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Attachments Section — Add File CTA shown for chief_engineer/captain
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <AttachmentsSection
            attachments={attachments}
            onAddFile={() => {
              // Photo upload — future file-picker integration (add_work_order_photo)
            }}
            canAddFile={perms.canAddPhoto}
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

      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleAddNote}
        isLoading={actions.isLoading}
      />

      <AddPartModal
        open={addPartOpen}
        onClose={() => setAddPartOpen(false)}
        onSubmit={handleAddPart}
        isLoading={actions.isLoading}
        parts={availableParts}
      />

      <MarkCompleteModal
        open={markCompleteOpen}
        onClose={() => setMarkCompleteOpen(false)}
        onSubmit={handleMarkComplete}
        isLoading={actions.isLoading}
        workOrderTitle={displayTitle}
      />

      <ReassignModal
        open={reassignOpen}
        onClose={() => setReassignOpen(false)}
        onSubmit={handleReassign}
        isLoading={actions.isLoading}
        crew={availableCrew}
        currentAssigneeId={workOrder.assigned_to}
      />

      <ArchiveModal
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        onSubmit={handleArchive}
        isLoading={actions.isLoading}
        workOrderTitle={displayTitle}
      />
    </LensContainer>
  );
});

WorkOrderLens.displayName = 'WorkOrderLens';

export default WorkOrderLens;
