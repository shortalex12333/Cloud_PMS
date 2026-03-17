'use client';

/**
 * WorkOrderLensContent - Work Order detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /work-orders/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * This component contains:
 * - LensHeader with back/close via useRouter
 * - Title block with status/priority pills
 * - VitalSignsRow (5 indicators)
 * - Checklist section (progress bar + items from pms_checklist_items)
 * - Primary action button + "More Actions" dropdown
 * - Sections: Notes, Parts, Attachments, History
 * - Action modals
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { getEntityRoute } from '@/lib/featureFlags';

// Sections
import {
  NotesSection,
  PartsSection,
  AttachmentsSection,
  HistorySection,
  RelatedEntitiesSection,
  ChecklistSection,
  type WorkOrderNote,
  type WorkOrderPart,
  type Attachment,
  type AuditLogEntry,
  type RelatedEntity,
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
  type SignaturePayload,
} from './actions';

// Context
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';

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
// WorkOrderLensContent component — zero props
// ---------------------------------------------------------------------------

export function WorkOrderLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Modal visibility
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [addPartOpen, setAddPartOpen] = React.useState(false);
  const [markCompleteOpen, setMarkCompleteOpen] = React.useState(false);
  const [reassignOpen, setReassignOpen] = React.useState(false);
  const [archiveOpen, setArchiveOpen] = React.useState(false);
  const [addHoursOpen, setAddHoursOpen] = React.useState(false);
  const [editOpen, setEditOpen] = React.useState(false);

  // Map entity to typed fields.
  // Handle both flat and nested payload structures from F1.
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const wo_number = (entity?.wo_number ?? payload.wo_number) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Work Order';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const priority = ((entity?.priority ?? payload.priority) as string | undefined) ?? 'medium';
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const assigned_to = (entity?.assigned_to ?? payload.assigned_to) as string | undefined;
  const created_at = ((entity?.created_at ?? payload.created_at) as string | undefined) ?? new Date().toISOString();
  const parts_count = (entity?.parts_count ?? payload.parts_count) as number | undefined;
  const due_date = (entity?.due_date ?? payload.due_date) as string | undefined;
  const wo_type = (entity?.type ?? payload.type) as string | undefined;

  // Section data — handle both flat and nested payload structures
  const notes = ((entity?.notes ?? payload.notes) as WorkOrderNote[] | undefined) ?? [];
  const parts = ((entity?.parts ?? payload.parts) as WorkOrderPart[] | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as AuditLogEntry[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  // Available options for modals (populated by future crew/parts fetch)
  const availableParts: PartOption[] = [];
  const availableCrew: CrewMember[] = [];

  // Derived display values
  const displayTitle = wo_number ? `${wo_number} — ${title}` : title;
  const statusColor = mapStatusToColor(status);
  const priorityColor = mapPriorityToColor(priority);
  const statusLabel = formatStatusLabel(status);
  const priorityLabel = formatPriorityLabel(priority);

  // Permission gates — null means no permission = don't render the button
  const startAction = getAction('start_work_order');
  const closeAction = getAction('close_work_order');
  const updateAction = getAction('update_work_order');
  const addNoteAction = getAction('add_wo_note');
  const addPartAction = getAction('add_wo_part');
  const addHoursAction = getAction('add_wo_hours');
  const assignAction = getAction('reassign_work_order');
  const archiveAction = getAction('archive_work_order');
  const addPhotoAction = getAction('add_wo_photo');

  // State-derived display conditions
  // canStart: WO is in a startable status (and backend says the action is available)
  const canStart = startAction !== null && ['draft', 'planned', 'open'].includes(status);
  // isCloseable: WO has not already reached a terminal state
  const isCloseable = !['completed', 'closed', 'cancelled'].includes(status);

  // Whether any action controls should be shown at all
  const hasAnyAction =
    startAction !== null ||
    closeAction !== null ||
    updateAction !== null ||
    addHoursAction !== null ||
    assignAction !== null ||
    archiveAction !== null;

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
      onClick: equipment_id
        ? () => router.push(getEntityRoute('equipment', equipment_id))
        : undefined,
    },
  ];

  // ---------------------------------------------------------------------------
  // Action handlers — call executeAction directly, no onRefresh needed
  // executeAction triggers refetch automatically via EntityLensPage
  // ---------------------------------------------------------------------------

  const handleAddNote = React.useCallback(
    async (noteText: string) => executeAction('add_wo_note', { note_text: noteText }),
    [executeAction]
  );

  const handleAddPart = React.useCallback(
    async (partId: string, qty: number, unit?: string) =>
      executeAction('add_wo_part', { part_id: partId, quantity: qty, unit }),
    [executeAction]
  );

  const handleMarkComplete = React.useCallback(
    async (completionNotes?: string) =>
      executeAction('close_work_order', { completion_notes: completionNotes }),
    [executeAction]
  );

  const handleReassign = React.useCallback(
    async (assigneeId: string, reason: string, signature: SignaturePayload) =>
      executeAction('reassign_work_order', { assignee_id: assigneeId, reason, signature }),
    [executeAction]
  );

  const handleArchive = React.useCallback(
    async (reason: string, signature: SignaturePayload) =>
      executeAction('archive_work_order', { deletion_reason: reason, signature }),
    [executeAction]
  );

  const handleStartWork = React.useCallback(
    async () => executeAction('start_work_order'),
    [executeAction]
  );

  const handleAddHours = React.useCallback(
    async (hours: number, notes?: string) =>
      executeAction('add_wo_hours', { hours, notes }),
    [executeAction]
  );

  const handleUpdateWorkOrder = React.useCallback(
    async (changes: WorkOrderEditData) =>
      executeAction('update_work_order', changes as Record<string, unknown>),
    [executeAction]
  );

  // ChecklistSection callbacks — wired to executeAction
  const handleViewChecklist = React.useCallback(
    () => executeAction('view_work_order_checklist', {}),
    [executeAction]
  );

  const handleMarkChecklistItem = React.useCallback(
    (checklistItemId: string) =>
      executeAction('mark_checklist_item_complete', { checklist_item_id: checklistItemId }),
    [executeAction]
  );

  // Navigation callbacks
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => router.push('/work-orders'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Fixed navigation header — 56px */}
      <LensHeader
        entityType="Work Order"
        title={displayTitle}
        onBack={handleBack}
        onClose={handleClose}
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

        {/* Checklist Section — between vitals and actions */}
        <div className="mt-4">
          <ChecklistSection
            workOrderId={(entity?.id as string) ?? ''}
            viewChecklist={handleViewChecklist}
            markComplete={handleMarkChecklistItem}
          />
        </div>

        {/* Actions — primary CTA + dropdown for secondary */}
        {hasAnyAction && (
          <div className="mt-4 flex items-center gap-2">
            {/* Primary CTA — only one visible at a time */}
            {canStart && (
              <PrimaryButton
                onClick={handleStartWork}
                disabled={startAction?.disabled ?? isLoading}
                title={startAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                {isLoading ? 'Starting...' : 'Start Work'}
              </PrimaryButton>
            )}
            {closeAction !== null && isCloseable && !canStart && (
              <PrimaryButton
                onClick={() => setMarkCompleteOpen(true)}
                disabled={closeAction?.disabled ?? isLoading}
                title={closeAction?.disabled_reason ?? undefined}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Mark Complete
              </PrimaryButton>
            )}

            {/* Secondary actions dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <GhostButton
                  className="text-[13px] min-h-9 px-3 py-2"
                  disabled={isLoading}
                  aria-label="More actions"
                >
                  <MoreHorizontal className="w-4 h-4" />
                </GhostButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="min-w-[180px]">
                {updateAction !== null && isCloseable && (
                  <DropdownMenuItem onClick={() => setEditOpen(true)}>
                    Edit
                  </DropdownMenuItem>
                )}
                {addNoteAction !== null && (
                  <DropdownMenuItem onClick={() => setAddNoteOpen(true)}>
                    Add Note
                  </DropdownMenuItem>
                )}
                {addPartAction !== null && (
                  <DropdownMenuItem onClick={() => setAddPartOpen(true)}>
                    Add Part
                  </DropdownMenuItem>
                )}
                {addHoursAction !== null && status === 'in_progress' && (
                  <DropdownMenuItem onClick={() => setAddHoursOpen(true)}>
                    Log Hours
                  </DropdownMenuItem>
                )}
                {assignAction !== null && (
                  <DropdownMenuItem onClick={() => setReassignOpen(true)}>
                    Reassign
                  </DropdownMenuItem>
                )}
                {archiveAction !== null && (
                  <DropdownMenuItem
                    onClick={() => setArchiveOpen(true)}
                    className="text-status-critical focus:text-status-critical"
                  >
                    Archive
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}

        {/* Section divider */}
        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Notes Section */}
        <div className="mt-6">
          <NotesSection
            notes={notes}
            onAddNote={() => setAddNoteOpen(true)}
            canAddNote={addNoteAction !== null}
            stickyTop={56}
          />
        </div>

        {/* Parts Section */}
        <div className="mt-6">
          <PartsSection
            parts={parts}
            onAddPart={() => setAddPartOpen(true)}
            canAddPart={addPartAction !== null}
            stickyTop={56}
          />
        </div>

        {/* Attachments Section */}
        <div className="mt-6">
          <AttachmentsSection
            attachments={attachments}
            onAddFile={() => {}}
            canAddFile={addPhotoAction !== null}
            stickyTop={56}
          />
        </div>

        {/* History Section */}
        <div className="mt-6">
          <HistorySection history={history} stickyTop={56} />
        </div>

        {related_entities.length > 0 && (
          <div className="mt-6">
            <RelatedEntitiesSection
              entities={related_entities}
              onNavigate={handleNavigate}
              stickyTop={56}
            />
          </div>
        )}
      </main>

      {/* Action Modals */}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleAddNote}
        isLoading={isLoading}
      />

      <AddPartModal
        open={addPartOpen}
        onClose={() => setAddPartOpen(false)}
        onSubmit={handleAddPart}
        isLoading={isLoading}
        parts={availableParts}
      />

      <MarkCompleteModal
        open={markCompleteOpen}
        onClose={() => setMarkCompleteOpen(false)}
        onSubmit={handleMarkComplete}
        isLoading={isLoading}
        workOrderTitle={displayTitle}
      />

      <ReassignModal
        open={reassignOpen}
        onClose={() => setReassignOpen(false)}
        onSubmit={handleReassign}
        isLoading={isLoading}
        crew={availableCrew}
        currentAssigneeId={assigned_to}
      />

      <ArchiveModal
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        onSubmit={handleArchive}
        isLoading={isLoading}
        workOrderTitle={displayTitle}
      />

      <AddHoursModal
        open={addHoursOpen}
        onClose={() => setAddHoursOpen(false)}
        onSubmit={handleAddHours}
        isLoading={isLoading}
        workOrderTitle={displayTitle}
      />

      <EditWorkOrderModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSubmit={handleUpdateWorkOrder}
        isLoading={isLoading}
        currentData={{
          title,
          description,
          priority,
          due_date,
          type: wo_type,
        }}
      />
    </div>
  );
}
