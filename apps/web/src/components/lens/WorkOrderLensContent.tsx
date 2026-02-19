'use client';

/**
 * WorkOrderLensContent - Inner content for Work Order lens (no LensContainer).
 *
 * Designed to render inside ContextPanel following the 1-URL philosophy.
 * Per rules.md: No fragmented URLs, everything at app.celeste7.ai.
 *
 * This component contains:
 * - LensHeader with back/close callbacks
 * - Title block with status/priority pills
 * - VitalSignsRow (5 indicators)
 * - Action buttons (Mark Complete, Reassign, Archive)
 * - Sections: Notes, Parts, Attachments, History
 * - Action modals
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
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
  AddHoursModal,
  EditWorkOrderModal,
  type PartOption,
  type CrewMember,
  type WorkOrderEditData,
} from './actions';

// Action hook + permissions
import { useWorkOrderActions, useWorkOrderPermissions } from '@/hooks/useWorkOrderActions';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// ---------------------------------------------------------------------------
// Props interface
// ---------------------------------------------------------------------------

export interface WorkOrderLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers
// ---------------------------------------------------------------------------

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

function formatPriorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

// ---------------------------------------------------------------------------
// WorkOrderLensContent component
// ---------------------------------------------------------------------------

export function WorkOrderLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: WorkOrderLensContentProps) {
  // Modal visibility
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [addPartOpen, setAddPartOpen] = React.useState(false);
  const [markCompleteOpen, setMarkCompleteOpen] = React.useState(false);
  const [reassignOpen, setReassignOpen] = React.useState(false);
  const [archiveOpen, setArchiveOpen] = React.useState(false);
  const [addHoursOpen, setAddHoursOpen] = React.useState(false);
  const [editOpen, setEditOpen] = React.useState(false);

  // Actions and permissions
  const actions = useWorkOrderActions(id);
  const perms = useWorkOrderPermissions();

  // Map data to typed structure
  const wo_number = data.wo_number as string | undefined;
  const title = (data.title as string) || 'Work Order';
  const description = data.description as string | undefined;
  const status = (data.status as string) || 'draft';
  const priority = (data.priority as string) || 'medium';
  const equipment_id = data.equipment_id as string | undefined;
  const equipment_name = data.equipment_name as string | undefined;
  const assigned_to = data.assigned_to as string | undefined;
  const created_at = (data.created_at as string) || new Date().toISOString();
  const parts_count = data.parts_count as number | undefined;

  // Section data
  const notes = (data.notes as WorkOrderNote[]) || [];
  const parts = (data.parts as WorkOrderPart[]) || [];
  const attachments = (data.attachments as Attachment[]) || [];
  const history = (data.audit_history as AuditLogEntry[]) || (data.history as AuditLogEntry[]) || [];

  // Available options for modals
  const availableParts: PartOption[] = [];
  const availableCrew: CrewMember[] = [];

  // Derived display values
  const displayTitle = wo_number ? `${wo_number} — ${title}` : title;
  const statusColor = mapStatusToColor(status);
  const priorityColor = mapPriorityToColor(priority);
  const statusLabel = formatStatusLabel(status);
  const priorityLabel = formatPriorityLabel(priority);

  // Build vital signs
  const vitalSigns: VitalSign[] = [
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
      value: parts_count !== undefined
        ? `${parts_count} part${parts_count === 1 ? '' : 's'}`
        : '0 parts',
    },
    {
      label: 'Created',
      value: created_at ? formatRelativeTime(created_at) : '—',
    },
    {
      label: 'Equipment',
      value: equipment_name ?? 'None',
      // Cross-lens navigation: click equipment to navigate
      onClick: equipment_id && onNavigate
        ? () => onNavigate('equipment', equipment_id)
        : undefined,
    },
  ];

  // Whether the WO can still be closed/completed
  const isCloseable = !['completed', 'closed', 'cancelled'].includes(status);

  // Whether the WO can be started (transition from draft/planned to in_progress)
  const canStart = ['draft', 'planned', 'open'].includes(status);

  // Action handlers
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

  const handleStartWork = React.useCallback(async () => {
    const result = await actions.startWorkOrder();
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleAddHours = React.useCallback(async (hours: number, notes?: string) => {
    const result = await actions.addHours(hours, notes);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleUpdateWorkOrder = React.useCallback(async (changes: WorkOrderEditData) => {
    const result = await actions.updateWorkOrder(changes as Record<string, unknown>);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  return (
    <div className="flex flex-col h-full">
      {/* Fixed navigation header — 56px */}
      <LensHeader
        entityType="Work Order"
        title={displayTitle}
        onBack={onBack}
        onClose={onClose}
      />

      {/* Main content — scrollable */}
      <main
        className={cn(
          'flex-1 overflow-y-auto',
          'pt-14', // Clear fixed header
          'px-10 md:px-6 sm:px-4',
          'max-w-[800px] mx-auto w-full',
          'pb-12'
        )}
      >
        {/* Title block */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={description}
            status={{ label: statusLabel, color: statusColor }}
            priority={{ label: priorityLabel, color: priorityColor }}
          />
        </div>

        {/* Vital Signs Row */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Action buttons */}
        {(perms.canStart || perms.canClose || perms.canUpdate || perms.canAddHours || perms.canAssign || perms.canArchive) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {/* Start Work Order - primary action when WO is draft/planned */}
            {perms.canStart && canStart && (
              <PrimaryButton
                onClick={handleStartWork}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                {actions.isLoading ? 'Starting...' : 'Start Work'}
              </PrimaryButton>
            )}
            {/* Mark Complete - primary action when WO is in progress */}
            {perms.canClose && isCloseable && !canStart && (
              <PrimaryButton
                onClick={() => setMarkCompleteOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Mark Complete
              </PrimaryButton>
            )}
            {/* Edit work order */}
            {perms.canUpdate && isCloseable && (
              <GhostButton
                onClick={() => setEditOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Edit
              </GhostButton>
            )}
            {/* Add Hours */}
            {perms.canAddHours && status === 'in_progress' && (
              <GhostButton
                onClick={() => setAddHoursOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Log Hours
              </GhostButton>
            )}
            {perms.canAssign && (
              <GhostButton
                onClick={() => setReassignOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Reassign
              </GhostButton>
            )}
            {perms.canArchive && (
              <GhostButton
                onClick={() => setArchiveOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-9 px-4 py-2 text-status-critical hover:text-status-critical"
              >
                Archive
              </GhostButton>
            )}
          </div>
        )}

        {/* Section divider */}
        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Notes Section */}
        <div className="mt-6">
          <NotesSection
            notes={notes}
            onAddNote={() => setAddNoteOpen(true)}
            canAddNote={perms.canAddNote}
            stickyTop={56}
          />
        </div>

        {/* Parts Section */}
        <div className="mt-6">
          <PartsSection
            parts={parts}
            onAddPart={() => setAddPartOpen(true)}
            canAddPart={perms.canAddPart}
            stickyTop={56}
          />
        </div>

        {/* Attachments Section */}
        <div className="mt-6">
          <AttachmentsSection
            attachments={attachments}
            onAddFile={() => {}}
            canAddFile={perms.canAddPhoto}
            stickyTop={56}
          />
        </div>

        {/* History Section */}
        <div className="mt-6">
          <HistorySection history={history} stickyTop={56} />
        </div>
      </main>

      {/* Action Modals */}
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
        currentAssigneeId={assigned_to}
      />

      <ArchiveModal
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        onSubmit={handleArchive}
        isLoading={actions.isLoading}
        workOrderTitle={displayTitle}
      />

      <AddHoursModal
        open={addHoursOpen}
        onClose={() => setAddHoursOpen(false)}
        onSubmit={handleAddHours}
        isLoading={actions.isLoading}
        workOrderTitle={displayTitle}
      />

      <EditWorkOrderModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSubmit={handleUpdateWorkOrder}
        isLoading={actions.isLoading}
        currentData={{
          title: title,
          description: description,
          priority: priority,
          due_date: data.due_date as string | undefined,
          type: data.type as string | undefined,
        }}
      />
    </div>
  );
}

export default WorkOrderLensContent;
