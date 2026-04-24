'use client';

/**
 * WorkOrderContent — lens-v2 Work Order entity view.
 * Matches lens-work-order.html prototype exactly.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines, description
 * 2. Official Documents (doc rows)
 * 3. Checklist (progress bar + items)
 * 4. Notes (timeline)
 * 5. History — prior periods of same WO (collapsed by default)
 * 6. Audit Trail — user actions: created, edited, closed, etc. (collapsed by default)
 * 7. Attachments
 * 8. Parts (collapsed by default)
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/entityRoutes';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';

// Sections
import {
  NotesSection,
  AuditTrailSection,
  HistorySection,
  AttachmentsSection,
  PartsSection,
  ChecklistSection,
  DocRowsSection,
  type NoteItem,
  type AuditEvent,
  type HistoryPeriod,
  type AttachmentItem,
  type PartItem,
  type ChecklistItem,
  type DocRowItem,
} from '../sections';

// ─── Colour mapping helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'overdue':
    case 'cancelled':
      return 'red';
    case 'in_progress':
    case 'pending_parts':
      return 'amber';
    case 'completed':
    case 'closed':
      return 'green';
    default:
      return 'neutral';
  }
}

function priorityToPillVariant(priority: string): PillDef['variant'] {
  switch (priority) {
    case 'critical':
      return 'red';
    case 'high':
      return 'amber';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function WorkOrderContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // Modal states (simplified — full modals come from production actions/)
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [addPartOpen, setAddPartOpen] = React.useState(false);

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const wo_number = (entity?.wo_number ?? payload.wo_number) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Work Order';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const priority = ((entity?.priority ?? payload.priority) as string | undefined) ?? 'medium';
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code) as string | undefined;
  const assigned_to = (entity?.assigned_to_name ?? payload.assigned_to_name ?? entity?.assigned_to ?? payload.assigned_to) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const due_date = (entity?.due_date ?? payload.due_date) as string | undefined;
  const wo_type = (entity?.type ?? payload.type) as string | undefined;
  const est_hours = (entity?.estimated_hours ?? payload.estimated_hours) as number | undefined;
  const actual_hours = (entity?.actual_hours ?? payload.actual_hours) as number | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  // TODO: Parts data depends on backend view_work_order handler joining pms_wo_parts.
  // If parts array is empty, verify the backend returns parts for this work order.
  const parts = ((entity?.parts ?? payload.parts) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  // Audit trail = user actions (created, edited, closed, etc.)
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];
  // History = prior periods of the same entity (year-grouped)
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const checklist = ((entity?.checklist ?? payload.checklist ?? entity?.checklist_items ?? payload.checklist_items) as Array<Record<string, unknown>> | undefined) ?? [];
  const documents = ((entity?.documents ?? payload.documents ?? entity?.official_documents ?? payload.official_documents) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  // Canonical long-form action_ids matching registry + entity_prefill.
  // Pre-2026-04-23 this block used short aliases (add_wo_*) that only
  // half-existed; getAction() returned null for half of them, silently
  // disabling buttons. See Issue 6 button audit.
  const startAction = getAction('start_work_order');
  const closeAction = getAction('close_work_order');
  const updateAction = getAction('update_work_order');
  const addNoteAction = getAction('add_work_order_note') ?? getAction('add_note_to_work_order') ?? getAction('add_wo_note');
  const addPartAction = getAction('add_parts_to_work_order') ?? getAction('add_wo_part');
  const addHoursAction = getAction('add_work_order_hours') ?? getAction('add_wo_hours');
  const assignAction = getAction('assign_work_order') ?? getAction('reassign_work_order');
  const archiveAction = getAction('archive_work_order');
  const addAttachmentAction = getAction('add_work_order_photo') ?? getAction('add_wo_photo');

  const canStart = startAction !== null && ['draft', 'planned', 'open'].includes(status);
  const isCloseable = !['completed', 'closed', 'cancelled'].includes(status);

  // ── Derived display ──
  const statusLabel = formatLabel(status);
  const priorityLabel = formatLabel(priority);

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (priority !== 'medium') {
    pills.push({ label: priorityLabel, variant: priorityToPillVariant(priority) });
  }

  const details: DetailLine[] = [];
  if (equipment_name) {
    details.push({ label: 'Equipment', value: `${equipment_code ?? ''} ${equipment_name}`.trim() });
  }
  if (due_date) {
    details.push({ label: 'Due', value: due_date, mono: true });
  }
  if (est_hours !== undefined || actual_hours !== undefined) {
    const parts: string[] = [];
    if (est_hours !== undefined) parts.push(`Est: ${est_hours} hrs`);
    if (actual_hours !== undefined) parts.push(`Actual: ${actual_hours} hrs`);
    details.push({ label: 'Time', value: parts.join(' · ') });
  }

  // Context line
  const contextParts: string[] = [];
  if (location) contextParts.push(location);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {assigned_to && (
        <>
          {contextParts.length > 0 && ' · '}
          Assigned to <span className={styles.crewLink}>{assigned_to}</span>
        </>
      )}
    </>
  );

  // ── Split button config ──
  const primaryLabel = canStart ? 'Start Work' : 'Mark Complete';
  const primaryDisabled = canStart
    ? (startAction?.disabled ?? false)
    : !isCloseable || (closeAction?.disabled ?? false);
  const primaryDisabledReason = canStart
    ? startAction?.disabled_reason
    : closeAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    if (canStart) {
      await executeAction('start_work_order');
    } else {
      await executeAction('close_work_order', {});
    }
  }, [canStart, executeAction]);

  // Build dropdown from ALL available actions (except the primary action)
  // Actions with special handlers get wired; everything else calls executeAction directly
  const SPECIAL_HANDLERS: Record<string, () => void> = {
    add_work_order_note:    () => setAddNoteOpen(true),
    add_note_to_work_order: () => setAddNoteOpen(true),
    add_wo_note:            () => setAddNoteOpen(true),
    add_parts_to_work_order: () => setAddPartOpen(true),
    add_wo_part:             () => setAddPartOpen(true),
  };
  const DANGER_ACTIONS = new Set(['archive_work_order', 'cancel_work_order', 'delete_work_order']);

  // ── Hidden-in-dropdown list ──
  // Issue 6 button audit (list_of_faults.md:195-245). Mirrors the cohort
  // pattern shipped in documents a2afd097 and certificates #681.
  //
  //   Duplicates / short-aliases (keep one canonical per semantic action):
  //     add_wo_note / add_note_to_work_order  → canonical: add_work_order_note
  //     add_wo_part                           → canonical: add_parts_to_work_order
  //     add_part_to_work_order                → duplicate of add_parts_to_work_order
  //     add_wo_hours / add_work_order_hours   → PR-WO-3 renames to "change hours preset"
  //     add_wo_photo                          → canonical: add_work_order_photo
  //     reassign_work_order                   → canonical: assign_work_order (HOD-gated)
  //
  //   Removed per Issue 6 KEEP/REMOVE table:
  //     cancel_work_order          — duplicate of archive
  //     delete_work_order          — duplicate of archive
  //     create_work_order          — belongs on AppShell, not per-WO
  //     view_work_order_detail     — the lens card IS the view
  //     view_work_order_history    — history is already a section on the card
  //     view_work_order_checklist  — redundant with view_checklist
  //     view_my_work_orders        — wasteful list reshuffle
  //     view_related_entities      — Show Related is a separate feature
  //     view_smart_summary         — wasteful
  //     record_voice_note          — wasteful, not MVP
  //     upload_photo               — duplicate of add_work_order_photo
  const HIDDEN_FROM_DROPDOWN = new Set<string>([
    'add_wo_note',
    'add_note_to_work_order',
    'add_wo_part',
    'add_part_to_work_order',
    'add_wo_hours',
    'add_work_order_hours',
    'add_wo_photo',
    'reassign_work_order',
    'cancel_work_order',
    'delete_work_order',
    'create_work_order',
    'view_work_order_detail',
    'view_work_order_history',
    'view_work_order_checklist',
    'view_my_work_orders',
    'view_related_entities',
    'view_smart_summary',
    'record_voice_note',
    'upload_photo',
  ]);

  const primaryActionId = canStart ? 'start_work_order' : 'close_work_order';
  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .filter((a) => !HIDDEN_FROM_DROPDOWN.has(a.action_id))
    .map((a) => ({
      label: a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => executeAction(a.action_id),
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
    }));

  // ── Map section data ──
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  const partItems: PartItem[] = parts.map((p, i) => ({
    id: (p.id as string) ?? `part-${i}`,
    name: (p.name ?? p.part_name) as string ?? 'Part',
    partNumber: (p.part_number ?? p.sku) as string | undefined,
    quantity: (p.quantity as number | undefined) !== undefined ? `× ${p.quantity}` : undefined,
    stock: (p.stock_level as number | undefined) !== undefined ? `Stock: ${p.stock_level}` : undefined,
    onNavigate: p.part_id ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], p.part_id as string)) : undefined,
  }));

  const checklistItems: ChecklistItem[] = checklist.map((c, i) => ({
    id: (c.id as string) ?? `check-${i}`,
    step: (c.step ?? c.order ?? i + 1) as number | undefined,
    description: (c.description ?? c.text ?? c.title) as string ?? '',
    completed: (c.completed ?? c.is_completed ?? c.done) as boolean ?? false,
    completedBy: (c.completed_by ?? c.completed_by_name) as string | undefined,
    completedAt: (c.completed_at) as string | undefined,
  }));

  const docItems: DocRowItem[] = documents.map((d, i) => ({
    id: (d.id as string) ?? `doc-${i}`,
    name: (d.name ?? d.title ?? d.file_name) as string ?? 'Document',
    code: (d.code ?? d.document_code ?? d.reference) as string | undefined,
    meta: (d.meta ?? d.description) as string | undefined,
    date: (d.date ?? d.effective_date ?? d.expires_at) as string | undefined,
    onClick: d.document_id ? () => router.push(getEntityRoute('documents' as Parameters<typeof getEntityRoute>[0], d.document_id as string)) : undefined,
  }));

  // ── Handle checklist toggle ──
  const handleChecklistToggle = React.useCallback(
    (itemId: string) => executeAction('mark_checklist_item_complete', { checklist_item_id: itemId }),
    [executeAction]
  );

  const handleAddNote = React.useCallback(
    () => setAddNoteOpen(true),
    []
  );

  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      // Use whichever canonical action_id the backend currently exposes
      // (see addNoteAction resolution above). Survives registry rename.
      const addNoteActionId = addNoteAction?.action_id ?? 'add_work_order_note';
      const result = await executeAction(addNoteActionId, { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction, addNoteAction]
  );

  const handleAddPart = React.useCallback(
    () => setAddPartOpen(true),
    []
  );

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={wo_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          (startAction || closeAction) ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Official Documents */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Official Documents" docs={docItems} />
        </ScrollReveal>
      )}

      {/* Checklist */}
      {checklistItems.length > 0 && (
        <ScrollReveal>
          <ChecklistSection items={checklistItems} onToggle={handleChecklistToggle} />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={handleAddNote}
          canAddNote
        />
      </ScrollReveal>

      {/* History — prior periods of the same work order */}
      <ScrollReveal>
        <HistorySection periods={historyPeriods} defaultCollapsed />
      </ScrollReveal>

      {/* Audit Trail — user actions on this entity */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {/* TODO: wire to file upload modal */}}
          canAddFile
        />
      </ScrollReveal>

      {/* Parts */}
      <ScrollReveal>
        <PartsSection
          parts={partItems}
          onAddPart={handleAddPart}
          canAddPart
          defaultCollapsed
        />
      </ScrollReveal>

      {/* Modals */}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
    </>
  );
}
