'use client';

/**
 * WorkOrderContent — lens entity view.
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
import { LensTabBar, type LensTab } from '../LensTabBar';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/entityRoutes';
import { AddNoteModal } from '@/components/lens/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';
import { API_BASE } from '@/lib/apiBase';

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

  const { session } = useAuth();
  const token = session?.access_token ?? null;

  // Modal states
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [addPartOpen, setAddPartOpen] = React.useState(false);
  const [assignOpen, setAssignOpen] = React.useState(false);
  const [checklistModalOpen, setChecklistModalOpen] = React.useState(false);
  const [checklistCategory, setChecklistCategory] = React.useState<'general' | 'safety'>('general');
  const [sopModalOpen, setSopModalOpen] = React.useState(false);
  const [archiveModalOpen, setArchiveModalOpen] = React.useState(false);
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false);

  // Toast feedback for generic dropdown actions
  const [actionFeedback, setActionFeedback] = React.useState<{ msg: string; ok: boolean } | null>(null);
  const showFeedback = React.useCallback((msg: string, ok: boolean) => {
    setActionFeedback({ msg, ok });
    setTimeout(() => setActionFeedback(null), 3500);
  }, []);

  const runAction = React.useCallback(
    async (actionId: string, payload?: Record<string, unknown>) => {
      try {
        const result = await executeAction(actionId, payload);
        const ok = result.success === true || (result as unknown as Record<string, unknown>).status === 'success';
        const msg = ok
          ? `Done.`
          : (result.error as string | undefined) ?? (result.message as string | undefined) ?? 'Action failed';
        showFeedback(msg, ok);
        return result;
      } catch (e) {
        showFeedback(e instanceof Error ? e.message : 'Unexpected error', false);
        throw e;
      }
    },
    [executeAction, showFeedback]
  );

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const wo_number = (entity?.wo_number ?? payload.wo_number) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Work Order';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const priority = ((entity?.priority ?? payload.priority) as string | undefined) ?? 'medium';
  const severity = (entity?.severity ?? payload.severity) as string | undefined;
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code) as string | undefined;
  // assigned_to may arrive as a resolved name (from the work-orders batch
  // enrichment in vessel_surface_routes.py) OR as a raw UUID if the entity
  // endpoint hasn't been enriched yet. Prefer the resolved form.
  const assigned_to = (entity?.assigned_to_name ?? payload.assigned_to_name ?? entity?.assigned_to ?? payload.assigned_to) as string | undefined;
  const assigned_to_role = (entity?.assigned_to_role ?? payload.assigned_to_role) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const due_date = (entity?.due_date ?? payload.due_date) as string | undefined;
  const due_at = (entity?.due_at ?? payload.due_at) as string | undefined;
  const created_at = (entity?.created_at ?? payload.created_at) as string | undefined;
  const wo_type = (entity?.type ?? payload.type ?? entity?.work_order_type ?? payload.work_order_type) as string | undefined;
  const frequency = (entity?.frequency ?? payload.frequency) as string | undefined;
  const completed_at = (entity?.completed_at ?? payload.completed_at) as string | undefined;
  const est_hours = (entity?.estimated_hours ?? payload.estimated_hours ?? entity?.estimated_duration_minutes) as number | undefined;
  const actual_hours = (entity?.actual_hours ?? payload.actual_hours) as number | undefined;
  const faults = ((entity?.faults ?? payload.faults ?? entity?.linked_faults ?? payload.linked_faults) as Array<Record<string, unknown>> | undefined) ?? [];

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
  // Checklist lives on `payload.metadata.checklist[]` today (see p2_mutation_light_handlers.add_checklist_item_execute).
  // We accept both top-level `checklist` (if an adapter flattens it) and the metadata path, plus a few legacy aliases.
  const metadataBlob = ((payload.metadata ?? entity?.metadata) as Record<string, unknown> | undefined) ?? {};
  const checklist = (
    (entity?.checklist ?? payload.checklist ?? entity?.checklist_items ?? payload.checklist_items ?? metadataBlob.checklist) as Array<Record<string, unknown>> | undefined
  ) ?? [];
  const documents = ((entity?.documents ?? payload.documents ?? entity?.official_documents ?? payload.official_documents) as Array<Record<string, unknown>> | undefined) ?? [];
  // SOP (PR-WO-4) — inline text + optional linked PDF document.
  const sopBlob = (metadataBlob.sop as Record<string, unknown> | undefined) ?? {};
  const sopText = (sopBlob.text ?? entity?.sop_text ?? payload.sop_text) as string | undefined;
  const sopDocumentId = (sopBlob.document_id ?? entity?.sop_document_id ?? payload.sop_document_id) as string | undefined;

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

  const yacht_id = (entity?.yacht_id ?? payload.yacht_id) as string | undefined;
  const wo_id = (entity?.id ?? payload.id) as string | undefined;

  const canStart = startAction !== null && ['draft', 'planned', 'open'].includes(status);
  const isCloseable = !['completed', 'closed', 'cancelled'].includes(status);

  // ── Derived display ──
  const statusLabel = formatLabel(status);
  const priorityLabel = formatLabel(priority);

  // Pills — UX sheet lines 374-380: status + priority + severity + wo_type
  // all surfaced in the header. Severity is distinct from priority (UX line
  // 340: "highly valuable, not visible").
  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (priority !== 'medium' && priority !== 'normal') {
    pills.push({ label: priorityLabel, variant: priorityToPillVariant(priority) });
  }
  if (severity) {
    const sev = severity.toLowerCase();
    const sevVariant: PillDef['variant'] =
      sev === 'critical' || sev === 'high' ? 'red' : sev === 'warning' || sev === 'medium' ? 'amber' : 'neutral';
    pills.push({ label: formatLabel(severity), variant: sevVariant });
  }
  if (wo_type) {
    pills.push({ label: formatLabel(wo_type), variant: 'neutral' });
  }

  // Detail lines — UX sheet lines 374-381: wo_number and title in header,
  // then assigned_to, created_at, due_date+due_at, severity as key/value.
  const details: DetailLine[] = [];
  if (equipment_name) {
    details.push({ label: 'Equipment', value: `${equipment_code ?? ''} ${equipment_name}`.trim() });
  }
  if (due_date || due_at) {
    const dueValue = [due_date, due_at].filter(Boolean).join(' · ');
    details.push({ label: 'Due', value: dueValue, mono: true });
  }
  if (created_at) {
    // "YYYY-MM-DD" is legible and stable. If consumer wants humanised, that's
    // a later UX polish — don't break the mono column for it.
    details.push({ label: 'Created', value: String(created_at).slice(0, 10), mono: true });
  }
  if (frequency) {
    details.push({ label: 'Frequency', value: formatLabel(frequency) });
  }
  if (completed_at) {
    details.push({ label: 'Completed', value: String(completed_at).slice(0, 10), mono: true });
  }
  if (est_hours !== undefined || actual_hours !== undefined) {
    const parts: string[] = [];
    if (est_hours !== undefined) parts.push(`Est: ${est_hours}`);
    if (actual_hours !== undefined) parts.push(`Actual: ${actual_hours}`);
    details.push({ label: 'Hours', value: parts.join(' · ') });
  }

  // Context line — UUIDs must never render. If assigned_to came through as a
  // raw UUID (entity endpoint hasn't been enriched) suppress rather than
  // displaying it.
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const assignedDisplay =
    assigned_to && !UUID_RE.test(assigned_to)
      ? assigned_to_role
        ? `${assigned_to} (${formatLabel(assigned_to_role)})`
        : assigned_to
      : undefined;
  const contextParts: string[] = [];
  if (location) contextParts.push(location);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {assignedDisplay && (
        <>
          {contextParts.length > 0 && ' · '}
          Assigned to <span className={styles.crewLink}>{assignedDisplay}</span>
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
  // Actions with special handlers open inline modals; everything else routes
  // through runAction (which shows toast feedback on success/failure).
  const SPECIAL_HANDLERS: Record<string, () => void> = {
    add_work_order_note:    () => setAddNoteOpen(true),
    add_note_to_work_order: () => setAddNoteOpen(true),
    add_wo_note:            () => setAddNoteOpen(true),
    add_parts_to_work_order: () => setAddPartOpen(true),
    add_wo_part:             () => setAddPartOpen(true),
    assign_work_order:       () => setAssignOpen(true),
    reassign_work_order:     () => setAssignOpen(true),
    archive_work_order:      () => setArchiveModalOpen(true),
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
    // ── Short-alias duplicates (canonical exposed instead) ──────────────────
    'add_wo_note',
    'add_note_to_work_order',
    'add_wo_part',
    'add_part_to_work_order',
    'add_wo_hours',
    'add_work_order_hours',
    'add_wo_photo',
    'reassign_work_order',          // alias — assign_work_order has SPECIAL_HANDLER
    // ── Issue 6 KEEP/REMOVE removals ────────────────────────────────────────
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
    // ── Inline-only actions (handled inside tabs, not from dropdown) ────────
    'add_checklist_item',           // Checklist tab inline
    'upsert_sop',                   // Safety tab inline
    'mark_checklist_item_complete', // Per-item toggle
    'add_work_order_photo',         // Uploads tab — needs photo_url, no dropdown form
    // ── Attachment comment thread actions (image viewer handles these) ──────
    'add_attachment_comment',
    'update_attachment_comment',
    'delete_attachment_comment',
    'list_attachment_comments',
    // ── Backend-only stubs with no meaningful dropdown UX ───────────────────
    'update_work_order',            // No-op without an edit form (updates only updated_at)
    'update_worklist_progress',     // Needs progress % form + broken registry config
    'view_checklist',
  ]);

  // Dropdown-display label overrides.
  // Issue 6 line 238: rename "Update Worklist Progress" → "Change Status".
  // Renaming at the display layer keeps the backend action_id stable
  // (update_worklist_progress), so in-flight callers / tests don't break.
  const LABEL_OVERRIDES: Record<string, string> = {
    update_worklist_progress: 'Change Status',
    assign_work_order: 'Assign',
    archive_work_order: 'Archive',
  };

  const primaryActionId = canStart ? 'start_work_order' : 'close_work_order';
  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .filter((a) => !HIDDEN_FROM_DROPDOWN.has(a.action_id))
    .map((a) => ({
      label: LABEL_OVERRIDES[a.action_id] ?? a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => runAction(a.action_id),
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

  // ── PR-WO-4b Safety tab callbacks ──
  const handleAddSafetyCheckpoint = React.useCallback(() => {
    setChecklistCategory('safety');
    setChecklistModalOpen(true);
  }, []);

  const handleAddGeneralCheckpoint = React.useCallback(() => {
    setChecklistCategory('general');
    setChecklistModalOpen(true);
  }, []);

  const handleEditSOP = React.useCallback(() => {
    setSopModalOpen(true);
  }, []);

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

  // ── Tab contract (UX sheet line 382) ──
  //   Checklist · Documents · Faults · Equipment · Parts · Uploads · Notes ·
  //   Audit Trail · History · Safety
  //
  // Safety is a placeholder in PR-WO-3 — LOTO/SOP + Checklist overhaul land
  // in PR-WO-4, where the `pms_work_order_checklist` / `pms_checklist` /
  // `pms_checklist_items` table audit unlocks the real content.
  // Safety tab badge: count of safety/loto checklist items (UX sheet line 382).
  const safetyItems = checklist.filter((c) => {
    const cat = ((c.category as string | undefined) ?? 'general').toLowerCase();
    return cat === 'safety' || cat === 'loto';
  });

  const tabs: LensTab[] = [
    { key: 'checklist', label: 'Checklist', count: checklistItems.length },
    { key: 'documents', label: 'Documents', count: docItems.length },
    { key: 'faults',    label: 'Faults',    count: faults.length },
    { key: 'equipment', label: 'Equipment', count: equipment_name ? 1 : 0 },
    { key: 'parts',     label: 'Parts',     count: partItems.length },
    { key: 'uploads',   label: 'Uploads',   count: attachmentItems.length },
    { key: 'notes',     label: 'Notes',     count: noteItems.length },
    { key: 'audit',     label: 'Audit Trail', count: auditEvents.length },
    { key: 'history',   label: 'History',   count: historyPeriods.length },
    { key: 'safety',    label: 'Safety',    count: safetyItems.length + (sopText ? 1 : 0) },
  ];

  const renderTabBody = (activeKey: string): React.ReactNode => {
    switch (activeKey) {
      case 'checklist':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <ChecklistSection items={checklistItems} onToggle={handleChecklistToggle} />
            <AddCheckpointButton onClick={handleAddGeneralCheckpoint} label="+ Add Checklist Item" />
          </div>
        );
      case 'documents':
        return docItems.length > 0 ? (
          <DocRowsSection title="Official Documents" docs={docItems} />
        ) : (
          <EmptyTab message="No supporting documents linked to this work order." />
        );
      case 'faults':
        return faults.length > 0 ? (
          <FaultsTabBody faults={faults} onOpen={(faultId) => router.push(getEntityRoute('faults' as Parameters<typeof getEntityRoute>[0], faultId))} />
        ) : (
          <EmptyTab message="No linked faults. Use 'Report Fault' from the Equipment lens to link one." />
        );
      case 'equipment':
        return equipment_id && equipment_name ? (
          <EquipmentTabBody
            equipmentId={equipment_id}
            equipmentName={equipment_name}
            equipmentCode={equipment_code}
            onOpen={() => router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipment_id))}
          />
        ) : (
          <EmptyTab message="No equipment linked." />
        );
      case 'parts':
        return (
          <PartsSection
            parts={partItems}
            onAddPart={handleAddPart}
            canAddPart
          />
        );
      case 'uploads':
        return (
          <AttachmentsSection
            attachments={attachmentItems}
            onAddFile={() => setUploadModalOpen(true)}
            canAddFile
          />
        );
      case 'notes':
        return <NotesSection notes={noteItems} onAddNote={handleAddNote} canAddNote />;
      case 'audit':
        return <AuditTrailSection events={auditEvents} />;
      case 'history':
        return <HistorySection periods={historyPeriods} />;
      case 'safety':
        return (
          <SafetyTabBody
            sopText={sopText}
            sopDocumentId={sopDocumentId}
            safetyItems={safetyItems}
            onToggle={handleChecklistToggle}
            onAddCheckpoint={handleAddSafetyCheckpoint}
            onEditSOP={handleEditSOP}
            onOpenSOPDoc={
              sopDocumentId
                ? () => router.push(
                    getEntityRoute('documents' as Parameters<typeof getEntityRoute>[0], sopDocumentId),
                  )
                : undefined
            }
          />
        );
      default:
        return <EmptyTab message="Coming soon." />;
    }
  };

  return (
    <>
      {/* Identity Strip — UX lines 373-381: wo_number overline, title, type/status/priority/severity pills, assigned_to + due + created + frequency + completed details */}
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

      {/* Tab bar replaces the legacy stacked ScrollReveal sections. */}
      <ScrollReveal>
        <LensTabBar
          tabs={tabs}
          defaultActiveKey="checklist"
          renderBody={renderTabBody}
        />
      </ScrollReveal>

      {/* Action feedback toast */}
      {actionFeedback && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
          padding: '10px 16px', borderRadius: 8,
          background: actionFeedback.ok ? 'var(--green-bg)' : 'var(--red-bg)',
          color: actionFeedback.ok ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${actionFeedback.ok ? 'var(--green)' : 'var(--red)'}`,
          fontSize: 13, maxWidth: 320,
          boxShadow: 'var(--shadow-card)',
        }}>
          {actionFeedback.msg}
        </div>
      )}

      {/* Modals */}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
      <AddPartModal
        open={addPartOpen}
        onClose={() => setAddPartOpen(false)}
        yachtId={yacht_id ?? ''}
        token={token ?? ''}
        onSubmit={async (partId, quantity) => {
          await runAction('add_parts_to_work_order', { part_id: partId, quantity });
          setAddPartOpen(false);
        }}
      />
      <AssignModal
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        yachtId={yacht_id ?? ''}
        token={token ?? ''}
        onSubmit={async (userId) => {
          await runAction('assign_work_order', { assigned_to: userId });
          setAssignOpen(false);
        }}
      />
      <AddChecklistItemModal
        open={checklistModalOpen}
        category={checklistCategory}
        onClose={() => setChecklistModalOpen(false)}
        onSubmit={async (itemTitle, itemDescription) => {
          await runAction('add_checklist_item', {
            title: itemTitle,
            description: itemDescription || undefined,
            category: checklistCategory,
            is_required: true,
          });
          setChecklistModalOpen(false);
        }}
      />
      <EditSOPModal
        open={sopModalOpen}
        current={sopText ?? ''}
        onClose={() => setSopModalOpen(false)}
        onSubmit={async (text) => {
          await runAction('upsert_sop', { sop_text: text });
          setSopModalOpen(false);
        }}
      />
      <ArchiveWorkOrderModal
        open={archiveModalOpen}
        onClose={() => setArchiveModalOpen(false)}
        onSubmit={async (reason, signature) => {
          await runAction('archive_work_order', { deletion_reason: reason, signature });
          setArchiveModalOpen(false);
        }}
      />
      {wo_id && yacht_id && session?.user?.id && (
        <AttachmentUploadModal
          open={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          onComplete={() => setUploadModalOpen(false)}
          title="Upload Photo / Document"
          description="Attach a file to this work order."
          entityType="work_order"
          entityId={wo_id}
          bucket="pms-work-order-photos"
          category="photo"
          yachtId={yacht_id}
          userId={session.user.id}
        />
      )}
    </>
  );
}

// ── Tab body helpers ───────────────────────────────────────────────────────

function EmptyTab({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '24px 16px',
        textAlign: 'center',
        color: 'var(--txt3)',
        fontSize: 13,
      }}
    >
      {message}
    </div>
  );
}

interface FaultRow {
  id: string;
  fault_code?: string;
  title?: string;
  status?: string;
  severity?: string;
}

function FaultsTabBody({
  faults,
  onOpen,
}: {
  faults: Array<Record<string, unknown>>;
  onOpen: (faultId: string) => void;
}) {
  const rows: FaultRow[] = faults.map((f, i) => ({
    id: (f.id as string) ?? `fault-${i}`,
    fault_code: (f.fault_code ?? f.code) as string | undefined,
    title: (f.title ?? f.description) as string | undefined,
    status: f.status as string | undefined,
    severity: f.severity as string | undefined,
  }));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {rows.map((r) => (
        <button
          key={r.id}
          type="button"
          onClick={() => onOpen(r.id)}
          style={{
            appearance: 'none',
            WebkitAppearance: 'none',
            textAlign: 'left',
            background: 'var(--surface)',
            border: '1px solid var(--border-faint)',
            borderRadius: 6,
            padding: '10px 12px',
            cursor: 'pointer',
            color: 'var(--txt)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            {r.fault_code && (
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt2)' }}>
                {r.fault_code}
              </span>
            )}
            <span style={{ fontWeight: 600 }}>{r.title ?? 'Fault'}</span>
          </div>
          {(r.status || r.severity) && (
            <div style={{ marginTop: 4, fontSize: 11, color: 'var(--txt3)' }}>
              {[r.severity, r.status].filter(Boolean).join(' · ')}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

function EquipmentTabBody({
  equipmentId: _equipmentId,
  equipmentName,
  equipmentCode,
  onOpen,
}: {
  equipmentId: string;
  equipmentName: string;
  equipmentCode?: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        textAlign: 'left',
        background: 'var(--surface)',
        border: '1px solid var(--border-faint)',
        borderRadius: 6,
        padding: '12px 14px',
        cursor: 'pointer',
        color: 'var(--txt)',
        width: '100%',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
        {equipmentCode && (
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt2)' }}>
            {equipmentCode}
          </span>
        )}
        <span style={{ fontWeight: 600 }}>{equipmentName}</span>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--txt3)' }}>
        Open equipment lens →
      </div>
    </button>
  );
}

// ── PR-WO-4 Safety tab helpers ─────────────────────────────────────────────

function AddCheckpointButton({
  onClick,
  label,
}: {
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        alignSelf: 'flex-start',
        background: 'var(--neutral-bg)',
        border: '1px dashed var(--border-sub)',
        borderRadius: 6,
        padding: '8px 12px',
        cursor: 'pointer',
        color: 'var(--txt2)',
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      {label}
    </button>
  );
}

interface SafetyRow {
  id: string;
  title?: string;
  description?: string;
  instructions?: string;
  is_completed?: boolean;
  completed_by?: string;
  completed_at?: string;
  category?: string;
}

function SafetyTabBody({
  sopText,
  sopDocumentId,
  safetyItems,
  onToggle,
  onAddCheckpoint,
  onEditSOP,
  onOpenSOPDoc,
}: {
  sopText?: string;
  sopDocumentId?: string;
  safetyItems: Array<Record<string, unknown>>;
  onToggle: (itemId: string) => void;
  onAddCheckpoint: () => void;
  onEditSOP: () => void;
  onOpenSOPDoc?: () => void;
}) {
  const rows: SafetyRow[] = safetyItems.map((i) => ({
    id: (i.id as string) ?? '',
    title: (i.title as string) ?? (i.description as string),
    description: i.description as string | undefined,
    instructions: i.instructions as string | undefined,
    is_completed: Boolean(i.is_completed ?? i.completed),
    completed_by: (i.completed_by_name ?? i.completed_by) as string | undefined,
    completed_at: i.completed_at as string | undefined,
    category: (i.category as string) ?? 'safety',
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* SOP block */}
      <section
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-faint)',
          borderRadius: 8,
          padding: '14px 16px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--txt2)',
            }}
          >
            Standard Operating Procedure
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {sopDocumentId && onOpenSOPDoc && (
              <button
                type="button"
                onClick={onOpenSOPDoc}
                style={{
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  background: 'var(--teal-bg)',
                  color: 'var(--mark)',
                  border: '1px solid var(--mark-hover)',
                  borderRadius: 4,
                  padding: '4px 10px',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                Open SOP PDF
              </button>
            )}
            <button
              type="button"
              onClick={onEditSOP}
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 4,
                padding: '4px 10px',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 500,
                color: 'var(--txt2)',
              }}
            >
              {sopText ? 'Edit' : 'Add SOP'}
            </button>
          </div>
        </div>
        {sopText ? (
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.55,
              color: 'var(--txt)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {sopText}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--txt3)', fontStyle: 'italic' }}>
            No SOP recorded. Click &quot;Add SOP&quot; to type one, or attach a PDF via the
            Documents tab then link it here.
          </div>
        )}
      </section>

      {/* Safety checklist block */}
      <section>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--txt2)',
            marginBottom: 8,
          }}
        >
          Safety Checklist &amp; Lock-Out-Tag-Out
        </div>
        {rows.length === 0 ? (
          <div
            style={{
              fontSize: 12,
              color: 'var(--txt3)',
              fontStyle: 'italic',
              marginBottom: 8,
            }}
          >
            No safety checkpoints yet. Add LOTO / isolation / test-for-dead steps
            below so the executor cannot complete the work order until each is
            ticked.
          </div>
        ) : (
          <div
            style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
            data-testid="safety-checklist-list"
          >
            {rows.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={!r.is_completed ? () => onToggle(r.id) : undefined}
                disabled={r.is_completed}
                style={{
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  textAlign: 'left',
                  background: r.is_completed
                    ? 'var(--green-bg)'
                    : 'var(--surface)',
                  border: `1px solid ${
                    r.is_completed ? 'var(--green-border)' : 'var(--border-faint)'
                  }`,
                  borderRadius: 6,
                  padding: '10px 12px',
                  cursor: r.is_completed ? 'default' : 'pointer',
                  color: 'var(--txt)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 18,
                    height: 18,
                    borderRadius: 3,
                    border: `1.5px solid ${
                      r.is_completed ? 'var(--green)' : 'var(--border-sub)'
                    }`,
                    background: r.is_completed ? 'var(--green)' : 'transparent',
                    color: 'white',
                    fontSize: 11,
                    fontWeight: 700,
                    flexShrink: 0,
                    marginTop: 1,
                  }}
                >
                  {r.is_completed ? '✓' : ''}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: r.is_completed ? 'var(--txt2)' : 'var(--txt)',
                      textDecoration: r.is_completed ? 'line-through' : undefined,
                    }}
                  >
                    {r.title ?? 'Safety step'}
                  </div>
                  {r.description && (
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--txt3)',
                        marginTop: 2,
                      }}
                    >
                      {r.description}
                    </div>
                  )}
                  {r.is_completed && r.completed_by && (
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--txt3)',
                        marginTop: 4,
                      }}
                    >
                      Completed by {r.completed_by}
                      {r.completed_at && ` · ${String(r.completed_at).slice(0, 10)}`}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
        <div style={{ marginTop: 8 }}>
          <AddCheckpointButton
            onClick={onAddCheckpoint}
            label="+ Add Safety Checkpoint"
          />
        </div>
      </section>
    </div>
  );
}

// ── AddPartModal ────────────────────────���───────────────────────────────────

interface PartRecord {
  id: string;
  name: string;
  part_number?: string;
  quantity_on_hand?: number;
  location?: string;
}

function AddPartModal({
  open,
  onClose,
  yachtId,
  token,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  yachtId: string;
  token: string;
  onSubmit: (partId: string, quantity: number) => Promise<void>;
}) {
  const [parts, setParts] = React.useState<PartRecord[]>([]);
  const [search, setSearch] = React.useState('');
  const [selected, setSelected] = React.useState<PartRecord | null>(null);
  const [quantity, setQuantity] = React.useState(1);
  const [loading, setLoading] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!open || !token || !yachtId) return;
    setLoading(true);
    setSelected(null);
    setSearch('');
    setQuantity(1);
    fetch(`${API_BASE}/v1/${yachtId}/domain/parts/records?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => setParts((d.records ?? []) as PartRecord[]))
      .catch(() => setParts([]))
      .finally(() => setLoading(false));
  }, [open, token, yachtId]);

  if (!open) return null;

  const filtered = parts.filter(
    (p) =>
      !search ||
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.part_number?.toLowerCase().includes(search.toLowerCase()),
  );

  const handleSubmit = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await onSubmit(selected.id, quantity);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'var(--overlay-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--surface)', borderRadius: 10, padding: 24,
        width: 420, maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        border: '1px solid var(--border-sub)', boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          Add Part to Work Order
        </div>
        <input
          placeholder="Search by name or part number…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'var(--bg)', color: 'var(--txt)', fontSize: 13,
            marginBottom: 8, fontFamily: 'var(--font-sans)',
          }}
        />
        {loading ? (
          <div style={{ color: 'var(--txt3)', fontSize: 13, padding: '12px 0' }}>Loading parts…</div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-faint)', borderRadius: 6, marginBottom: 12 }}>
            {filtered.length === 0 ? (
              <div style={{ padding: 12, color: 'var(--txt3)', fontSize: 13 }}>No parts found.</div>
            ) : filtered.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelected(p)}
                style={{
                  width: '100%', textAlign: 'left', padding: '10px 12px',
                  background: selected?.id === p.id ? 'var(--teal-bg)' : 'transparent',
                  border: 'none', borderBottom: '1px solid var(--border-faint)',
                  cursor: 'pointer', color: 'var(--txt)', fontSize: 13,
                  fontFamily: 'var(--font-sans)',
                }}
              >
                <div style={{ fontWeight: 500 }}>{p.name}</div>
                {p.part_number && (
                  <div style={{ fontSize: 11, color: 'var(--txt3)' }}>
                    {p.part_number}{p.quantity_on_hand != null ? ` · Stock: ${p.quantity_on_hand}` : ''}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
        {selected && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <label style={{ fontSize: 13, color: 'var(--txt2)', whiteSpace: 'nowrap' }}>Qty:</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              style={{
                width: 72, padding: '6px 8px', borderRadius: 6,
                border: '1px solid var(--border-sub)', background: 'var(--bg)',
                color: 'var(--txt)', fontSize: 13, fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!selected || submitting}
            style={{
              padding: '8px 14px', borderRadius: 6, border: 'none',
              background: selected ? 'var(--mark)' : 'var(--border-faint)',
              color: selected ? 'var(--surface)' : 'var(--txt3)',
              fontSize: 13, cursor: selected ? 'pointer' : 'not-allowed',
              fontFamily: 'var(--font-sans)', fontWeight: 500,
            }}
          >
            {submitting ? 'Adding…' : 'Add Part'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AssignModal ─────────────────────────────────────────────────────────────

function AssignModal({
  open,
  onClose,
  yachtId,
  token,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  yachtId: string;
  token: string;
  onSubmit: (userId: string) => Promise<void>;
}) {
  const [userId, setUserId] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) setUserId('');
  }, [open]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!userId.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(userId.trim());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'var(--overlay-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--surface)', borderRadius: 10, padding: 24,
        width: 360, border: '1px solid var(--border-sub)',
        boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          Assign Work Order
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 6 }}>
          User ID (crew member)
        </label>
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Paste crew member user ID…"
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!userId.trim() || submitting}
            style={{
              padding: '8px 14px', borderRadius: 6, border: 'none',
              background: userId.trim() ? 'var(--mark)' : 'var(--border-faint)',
              color: userId.trim() ? 'var(--surface)' : 'var(--txt3)',
              fontSize: 13, cursor: userId.trim() ? 'pointer' : 'not-allowed',
              fontFamily: 'var(--font-sans)', fontWeight: 500,
            }}
          >
            {submitting ? 'Assigning…' : 'Assign'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AddChecklistItemModal ───────────────────────────────────────────────────

function AddChecklistItemModal({
  open,
  category,
  onClose,
  onSubmit,
}: {
  open: boolean;
  category: 'general' | 'safety';
  onClose: () => void;
  onSubmit: (title: string, description: string) => Promise<void>;
}) {
  const [itemTitle, setItemTitle] = React.useState('');
  const [itemDesc, setItemDesc] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setItemTitle(''); setItemDesc(''); setSubmitting(false); }
  }, [open]);

  if (!open) return null;

  const isSafety = category === 'safety';
  const placeholder = isSafety ? 'e.g. Lock out breaker 17B' : 'e.g. Inspect filter housing';

  const handleSubmit = async () => {
    if (!itemTitle.trim() || submitting) return;
    setSubmitting(true);
    try { await onSubmit(itemTitle.trim(), itemDesc.trim()); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 420, background: 'var(--surface)',
        border: '1px solid var(--border-faint)', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          {isSafety ? 'Add Safety Checkpoint' : 'Add Checklist Item'}
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Title <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <input
          value={itemTitle}
          onChange={(e) => setItemTitle(e.target.value)}
          placeholder={placeholder}
          autoFocus
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 14,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Guidance / Instructions <span style={{ color: 'var(--txt3)', fontWeight: 400 }}>(optional)</span>
        </label>
        <textarea
          value={itemDesc}
          onChange={(e) => setItemDesc(e.target.value)}
          placeholder={isSafety ? 'Isolation steps, test-for-dead procedure…' : 'Additional guidance…'}
          rows={3}
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16, resize: 'vertical',
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!itemTitle.trim() || submitting} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: itemTitle.trim() ? 'var(--mark)' : 'var(--border-faint)',
            color: itemTitle.trim() ? 'var(--surface)' : 'var(--txt3)',
            fontSize: 13, cursor: itemTitle.trim() ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Adding…' : 'Add Item'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── EditSOPModal ────────────────────────────────────────────────────────────

function EditSOPModal({
  open,
  current,
  onClose,
  onSubmit,
}: {
  open: boolean;
  current: string;
  onClose: () => void;
  onSubmit: (text: string) => Promise<void>;
}) {
  const [text, setText] = React.useState(current);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setText(current); setSubmitting(false); }
  }, [open, current]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try { await onSubmit(text); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 520, background: 'var(--surface)',
        border: '1px solid var(--border-faint)', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 8 }}>
          Standard Operating Procedure
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', marginBottom: 14 }}>
          Describe the step-by-step procedure. Leave blank to clear.
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="1. Isolate system&#10;2. Verify de-energised&#10;3. ..."
          rows={8}
          autoFocus
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16, resize: 'vertical',
            fontFamily: 'var(--font-mono)', lineHeight: 1.6, boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={submitting} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: 'var(--mark)', color: 'var(--surface)',
            fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Saving…' : 'Save SOP'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ArchiveWorkOrderModal ───────────────────────────────────────────────────

function ArchiveWorkOrderModal({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string, signature: string) => Promise<void>;
}) {
  const [reason, setReason] = React.useState('');
  const [signature, setSignature] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setReason(''); setSignature(''); setSubmitting(false); }
  }, [open]);

  if (!open) return null;

  const canSubmit = reason.trim().length > 3 && signature.trim().length > 2 && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try { await onSubmit(reason.trim(), signature.trim()); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 420, background: 'var(--surface)',
        border: '1px solid var(--red-border, var(--border-faint))', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--red)', marginBottom: 8 }}>
          Archive Work Order
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', marginBottom: 16 }}>
          This action is permanent. The work order will be soft-deleted and removed
          from active views. Type your full name to confirm.
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Reason for archiving <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Duplicate entry created in error"
          rows={3}
          autoFocus
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 14, resize: 'vertical',
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Your full name (signature) <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <input
          value={signature}
          onChange={(e) => setSignature(e.target.value)}
          placeholder="Type your full name to confirm"
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!canSubmit} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: canSubmit ? 'var(--red)' : 'var(--border-faint)',
            color: canSubmit ? 'white' : 'var(--txt3)',
            fontSize: 13, cursor: canSubmit ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Archiving…' : 'Archive'}
          </button>
        </div>
      </div>
    </div>
  );
}
