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
 * 5. History (collapsed by default)
 * 6. Attachments
 * 7. Parts (collapsed by default)
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';
import { AddNoteModal } from '@/components/lens/actions/AddNoteModal';

// Sections
import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  PartsSection,
  ChecklistSection,
  DocRowsSection,
  type NoteItem,
  type AuditEvent,
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
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

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
  const parts = ((entity?.parts ?? payload.parts) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const checklist = ((entity?.checklist ?? payload.checklist ?? entity?.checklist_items ?? payload.checklist_items) as Array<Record<string, unknown>> | undefined) ?? [];
  const documents = ((entity?.documents ?? payload.documents ?? entity?.official_documents ?? payload.official_documents) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const startAction = getAction('start_work_order');
  const closeAction = getAction('close_work_order');
  const updateAction = getAction('update_work_order');
  const addNoteAction = getAction('add_wo_note');
  const addPartAction = getAction('add_wo_part');
  const addHoursAction = getAction('add_wo_hours');
  const assignAction = getAction('reassign_work_order');
  const archiveAction = getAction('archive_work_order');

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

  const dropdownItems: DropdownItem[] = [];
  if (updateAction !== null && isCloseable) {
    dropdownItems.push({
      label: 'Edit Details',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>,
      onClick: () => {},
    });
  }
  if (addNoteAction !== null) {
    dropdownItems.push({
      label: 'Add Note',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>,
      onClick: () => setAddNoteOpen(true),
    });
  }
  if (addHoursAction !== null && status === 'in_progress') {
    dropdownItems.push({
      label: 'Log Hours',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>,
      onClick: () => {},
    });
  }
  if (assignAction !== null) {
    dropdownItems.push({
      label: 'Reassign',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" /></svg>,
      onClick: () => {},
    });
  }
  if (archiveAction !== null) {
    dropdownItems.push({
      label: 'Archive',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>,
      onClick: () => {},
      danger: true,
    });
  }

  // ── Map section data ──
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
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
      const result = await executeAction('add_wo_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
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
          canAddNote={addNoteAction !== null}
        />
      </ScrollReveal>

      {/* History */}
      {auditEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection events={auditEvents} defaultCollapsed />
        </ScrollReveal>
      )}

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile={false}
        />
      </ScrollReveal>

      {/* Parts */}
      <ScrollReveal>
        <PartsSection
          parts={partItems}
          onAddPart={handleAddPart}
          canAddPart={addPartAction !== null}
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
