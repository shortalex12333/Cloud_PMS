'use client';

/**
 * EquipmentContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-equipment.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Specs → Spare Parts → Work Orders → Faults → Upcoming Maint → Certs → Notes → History → Audit Trail → Attachments
 *
 * TODO notes for next engineer:
 * - Add Note modal not wired (onClick is noop)
 *
 * PR-EQ-4 (2026-04-24) — attachment wiring completed:
 * - `onAddFile` now opens AttachmentUploadModal (default pms_attachments mode).
 * - Image-type attachments render via the cohort-shared `LensImageViewer`;
 *   non-image rows continue through `AttachmentsSection` unchanged.
 * - Threaded comments render in a panel adjacent to the viewer — NOT inside
 *   the shared component (brief: "safest option: render threaded-comment UI
 *   OUTSIDE the viewer, visually adjacent"). Comments lazy-load per image.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { useAuth } from '@/hooks/useAuth';
import { getEntityRoute } from '@/lib/entityRoutes';

// Sections
import {
  AuditTrailSection,
  AttachmentsSection,
  DocRowsSection,
  HistorySection,
  KVSection,
  LensImageViewer,
  NotesSection,
  PartsSection,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type HistoryPeriod,
  type KVItem,
  type LensImage,
  type NoteItem,
  type PartItem,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';

// ── Threaded-comment shape (from list_attachment_comments) ──
// Kept local to this file — the cohort LensImageViewer is single-caption MVP and
// must not be forked. Threads render beside it in EquipmentContent.
interface AttachmentCommentNode {
  id: string;
  comment: string;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
  parent_comment_id: string | null;
  author_department?: string | null;
  replies?: AttachmentCommentNode[];
}

// ─── Helpers ───

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function EquipmentContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading, entityId, refetch } = useEntityLensContext();
  const { user } = useAuth();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code ?? entity?.code ?? payload.code) as string | undefined;
  const name = ((entity?.name ?? payload.name) as string | undefined) ?? 'Equipment';
  const equipment_type = ((entity?.equipment_type ?? payload.equipment_type ?? entity?.category ?? payload.category) as string | undefined) ?? 'General';
  const manufacturer = (entity?.manufacturer ?? payload.manufacturer) as string | undefined;
  const model = (entity?.model ?? payload.model) as string | undefined;
  const serial_number = (entity?.serial_number ?? payload.serial_number) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const installation_date = (entity?.installation_date ?? payload.installation_date) as string | undefined;
  const last_maintenance = (entity?.last_maintenance ?? payload.last_maintenance) as string | undefined;
  const next_maintenance = (entity?.next_maintenance ?? payload.next_maintenance) as string | undefined;
  const responsible = (entity?.responsible ?? payload.responsible ?? entity?.assigned_to_name ?? payload.assigned_to_name) as string | undefined;
  const criticality = (entity?.criticality ?? payload.criticality) as string | undefined;
  const running_hours = (entity?.running_hours ?? payload.running_hours) as number | string | undefined;
  const hierarchy = (entity?.hierarchy ?? payload.hierarchy) as string | undefined;

  // Specifications (custom key-value data)
  const specifications = ((entity?.specifications ?? payload.specifications) as Array<Record<string, unknown>> | undefined) ?? [];
  // Sub-entity arrays
  const work_orders = ((entity?.work_orders ?? payload.work_orders ?? entity?.active_work_orders ?? payload.active_work_orders) as Array<Record<string, unknown>> | undefined) ?? [];
  const faults = ((entity?.faults ?? payload.faults ?? entity?.active_faults ?? payload.active_faults) as Array<Record<string, unknown>> | undefined) ?? [];
  const certificates = ((entity?.certificates ?? payload.certificates) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history ?? entity?.maintenance_history ?? payload.maintenance_history) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const spare_parts = ((entity?.spare_parts ?? payload.spare_parts) as Array<Record<string, unknown>> | undefined) ?? [];
  const upcoming_maintenance = ((entity?.upcoming_maintenance ?? payload.upcoming_maintenance) as Array<Record<string, unknown>> | undefined) ?? [];
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const createWOAction = getAction('create_work_order_for_equipment');
  const flagAction = getAction('flag_equipment_attention');
  const addNoteAction = getAction('add_equipment_note');
  const decommissionAction = getAction('decommission_equipment');

  // BACKEND_AUTO moved to mapActionFields.ts
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_equipment_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  // ── Attachment upload modal (PR-EQ-4) ──
  // FIXME: migrate to pms-equipment-photos once CEO creates that bucket.
  // pms-work-order-photos is RLS-correct for polymorphic attachments today.
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false);

  // ── Threaded-comment state (PR-EQ-4) ──
  // Key = attachment_id; value = root comment tree (with nested `replies`).
  // Populated lazily when the user opens an image in the viewer.
  const [commentsByAttachment, setCommentsByAttachment] = React.useState<
    Record<string, AttachmentCommentNode[]>
  >({});
  const [openCommentAttachmentId, setOpenCommentAttachmentId] = React.useState<string | null>(null);
  const [commentDraft, setCommentDraft] = React.useState('');
  const [commentBusy, setCommentBusy] = React.useState(false);
  const [commentsLoading, setCommentsLoading] = React.useState(false);

  const loadComments = React.useCallback(
    async (attachment_id: string) => {
      setCommentsLoading(true);
      try {
        const result = await executeAction('list_attachment_comments', { attachment_id });
        const data = result.data as { comments?: AttachmentCommentNode[] } | undefined;
        setCommentsByAttachment((prev) => ({
          ...prev,
          [attachment_id]: data?.comments ?? [],
        }));
      } finally {
        setCommentsLoading(false);
      }
    },
    [executeAction],
  );

  const handleOpenComments = React.useCallback(
    async (attachment_id: string) => {
      setOpenCommentAttachmentId(attachment_id);
      setCommentDraft('');
      // Lazy-load: only fetch once per attachment until a mutation invalidates.
      if (commentsByAttachment[attachment_id] === undefined) {
        await loadComments(attachment_id);
      }
    },
    [commentsByAttachment, loadComments],
  );

  const handleAddComment = React.useCallback(
    async (parent_comment_id: string | null) => {
      if (!openCommentAttachmentId || !commentDraft.trim()) return;
      setCommentBusy(true);
      try {
        await executeAction('add_attachment_comment', {
          attachment_id: openCommentAttachmentId,
          comment: commentDraft.trim(),
          parent_comment_id,
        });
        setCommentDraft('');
        await loadComments(openCommentAttachmentId);
      } finally {
        setCommentBusy(false);
      }
    },
    [openCommentAttachmentId, commentDraft, executeAction, loadComments],
  );

  const handleDeleteComment = React.useCallback(
    async (comment_id: string) => {
      if (!openCommentAttachmentId) return;
      setCommentBusy(true);
      try {
        await executeAction('delete_attachment_comment', { comment_id });
        await loadComments(openCommentAttachmentId);
      } finally {
        setCommentBusy(false);
      }
    },
    [openCommentAttachmentId, executeAction, loadComments],
  );

  // NOTE: LensImageViewer.onEditComment intentionally NOT wired. No backend action
  // exists to mutate pms_attachments.description after upload; the richer thread UI
  // below replaces single-caption edits. Viewer renders description read-only.

  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; subtitle?: string;
    fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  // ── Derived display ──
  // Owner correction: DO NOT render status indicators (low fidelity, misleading)
  const pills: PillDef[] = [];

  const details: DetailLine[] = [];
  if (manufacturer) {
    details.push({ label: 'Manufacturer', value: manufacturer });
  }
  if (model) {
    details.push({ label: 'Model', value: model, mono: true });
  }
  if (serial_number) {
    details.push({ label: 'Serial', value: serial_number, mono: true });
  }
  if (installation_date) {
    details.push({ label: 'Installed', value: installation_date, mono: true });
  }
  if (next_maintenance) {
    details.push({ label: 'Next Service', value: next_maintenance, mono: true });
  }
  if (running_hours !== undefined) {
    details.push({ label: 'Running Hours', value: String(running_hours), mono: true });
  }

  // Context line (location + responsible)
  const contextParts: string[] = [];
  if (location) contextParts.push(location);
  if (equipment_type && equipment_type !== 'General') contextParts.push(equipment_type);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {responsible && (
        <>
          {contextParts.length > 0 && ' · '}
          Responsible: <span className={styles.crewLink}>{responsible}</span>
        </>
      )}
    </>
  );

  // ── Split button config ──
  const primaryLabel = 'Create Work Order';
  const primaryDisabled = createWOAction?.disabled ?? false;
  const primaryDisabledReason = createWOAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('create_work_order_for_equipment', { type: 'corrective', priority: 'routine' });
  }, [executeAction]);

  // PR-EQ-5: File Warranty Claim is a navigation stub — CEO brief marks it
  // PARAMOUNT and wants router.push rather than invoking the backend action
  // (which would open the warranty modal with partial prefill). Routed to
  // /warranties?equipment_id=<id> because no dedicated /warranties/new page
  // exists yet (folder is `warranties` plural, and only list + [id] routes
  // are present). A follow-up PR can either add a /warranties/new page that
  // reads ?equipment_id= to prefill a create form, or replace this handler
  // with a modal — the stub keeps the user-visible contract stable.
  const SPECIAL_HANDLERS: Record<string, () => void> = {
    file_warranty_claim: () => {
      const qs = entityId ? `?equipment_id=${encodeURIComponent(entityId)}` : '';
      router.push(`/warranties${qs}`);
    },
  };
  const DANGER_ACTIONS = new Set(['decommission_equipment', 'archive_equipment']);
  const primaryActionId = 'create_work_order_for_equipment';

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .map((a) => ({
      label: a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => {
            const hasFields = actionHasFields(a as any);
            if (hasFields || a.requires_signature) {
              openActionPopup(a);
            } else {
              executeAction(a.action_id);
            }
          },
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
    }));

  // ── Map section data ──

  // Specifications → KVItems
  const specItems: KVItem[] = specifications.map((s) => ({
    label: (s.label ?? s.key ?? s.name) as string ?? '',
    value: (s.value ?? s.val) as string ?? '',
    mono: (s.mono as boolean | undefined) ?? false,
  }));

  // Work orders → DocRows
  const woItems: DocRowItem[] = work_orders.map((wo, i) => ({
    id: (wo.id as string) ?? `wo-${i}`,
    name: (wo.title ?? wo.name) as string ?? 'Work Order',
    code: (wo.wo_number ?? wo.code) as string | undefined,
    meta: (wo.assigned_to_name ?? wo.assigned_to ?? wo.meta) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="1" /></svg>,
    onClick: wo.id ? () => router.push(getEntityRoute('work_orders' as Parameters<typeof getEntityRoute>[0], wo.id as string)) : undefined,
  }));

  // Faults → DocRows
  const faultItems: DocRowItem[] = faults.map((f, i) => ({
    id: (f.id as string) ?? `fault-${i}`,
    name: (f.title ?? f.name) as string ?? 'Fault',
    code: (f.fault_number ?? f.code) as string | undefined,
    meta: (f.reported_by ?? f.meta) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
    onClick: f.id ? () => router.push(getEntityRoute('faults' as Parameters<typeof getEntityRoute>[0], f.id as string)) : undefined,
  }));

  // Certificates → DocRows
  const certItems: DocRowItem[] = certificates.map((c, i) => ({
    id: (c.id as string) ?? `cert-${i}`,
    name: (c.title ?? c.name) as string ?? 'Certificate',
    code: (c.certificate_number ?? c.code) as string | undefined,
    meta: (c.meta ?? c.description) as string | undefined,
    date: (c.expires_at ?? c.expiry_date ?? c.date) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
    onClick: c.id ? () => router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], c.id as string)) : undefined,
  }));

  // History → AuditEvents
  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event ?? h.title) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by ?? h.assigned_to) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp ?? h.completed_at) as string ?? '',
  }));

  // ── Attachments split: images → LensImageViewer, others → AttachmentsSection ──
  // (PR-EQ-4 — mime_type-gated; keeps legacy row UI for PDFs/docs.)
  const imageAttachments = React.useMemo(
    () => attachments.filter((a) => {
      const mime = (a.mime_type ?? a.content_type) as string | undefined;
      return typeof mime === 'string' && mime.startsWith('image/');
    }),
    [attachments],
  );
  const nonImageAttachments = React.useMemo(
    () => attachments.filter((a) => {
      const mime = (a.mime_type ?? a.content_type) as string | undefined;
      return !(typeof mime === 'string' && mime.startsWith('image/'));
    }),
    [attachments],
  );

  const lensImages: LensImage[] = imageAttachments.map((a, i) => ({
    id: (a.id as string) ?? `img-${i}`,
    url: (a.signed_url ?? a.url) as string ?? '',
    thumbnail_url: (a.thumbnail_path ?? undefined) as string | undefined,
    description: (a.description ?? a.caption ?? null) as string | null,
    uploaded_by_name: (a.uploaded_by_name ?? null) as string | null,
    uploaded_at: (a.uploaded_at ?? a.created_at ?? null) as string | null,
    category: (a.category ?? null) as string | null,
    filename: (a.filename ?? a.name ?? a.file_name ?? null) as string | null,
  }));

  // Non-image rows keep their existing AttachmentItem shape.
  const attachmentItems: AttachmentItem[] = nonImageAttachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: 'document' as const,
    url: (a.signed_url ?? a.url) as string | undefined,
  }));

  // Spare Parts → PartItems
  const sparePartItems: PartItem[] = spare_parts.map((sp, i) => ({
    id: (sp.id as string) ?? `spare-${i}`,
    name: (sp.name ?? sp.part_name) as string ?? 'Part',
    partNumber: (sp.part_number ?? sp.sku) as string | undefined,
    quantity: (sp.required ?? sp.quantity) !== undefined
      ? `Req: ${sp.required ?? sp.quantity}`
      : undefined,
    stock: (sp.on_hand ?? sp.stock ?? sp.in_stock) !== undefined
      ? `On hand: ${sp.on_hand ?? sp.stock ?? sp.in_stock}`
      : undefined,
    onNavigate: sp.part_id
      ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], sp.part_id as string))
      : undefined,
  }));

  // Upcoming Maintenance → KVItems
  const upcomingMaintItems: KVItem[] = upcoming_maintenance.map((m, i) => {
    const title = (m.title ?? m.name ?? m.description) as string ?? `Maintenance ${i + 1}`;
    const trigger = (m.trigger ?? m.trigger_type) as string | undefined;
    const due = (m.due_at ?? m.due_date ?? m.due) as string | undefined;
    const remaining = (m.remaining ?? m.remaining_hours ?? m.remaining_days) as string | number | undefined;
    const parts: string[] = [];
    if (trigger) parts.push(`Trigger: ${trigger}`);
    if (due) parts.push(`Due: ${due}`);
    if (remaining !== undefined) parts.push(`${remaining} remaining`);
    return {
      label: title,
      value: parts.join(' · ') || '—',
      mono: true,
    };
  });

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const auditEvents2: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit2-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={equipment_code}
        title={manufacturer && model ? `${name} \u2014 ${manufacturer} ${model}` : name}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          createWOAction !== null ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label={dropdownItems[0].label}
              onClick={dropdownItems[0].onClick}
              items={dropdownItems.slice(1)}
            />
          ) : undefined
        }
      />

      {/* Specifications */}
      {specItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Specifications"
            items={specItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <line x1="5" y1="9" x2="11" y2="9" stroke="currentColor" strokeWidth="1.3" />
                <line x1="5" y1="12" x2="9" y2="12" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Spare Parts */}
      {sparePartItems.length > 0 && (
        <ScrollReveal>
          <PartsSection
            parts={sparePartItems}
            canAddPart
          />
        </ScrollReveal>
      )}

      {/* Active Work Orders */}
      {woItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Work Orders"
            docs={woItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 3H5a1 1 0 00-1 1v9a1 1 0 001 1h6a1 1 0 001-1V4a1 1 0 00-1-1h-1" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <rect x="6" y="1.5" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Active Faults */}
      {faultItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Active Faults"
            docs={faultItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M7.13 2.58L1.22 12a1.33 1.33 0 001.14 2h11.28a1.33 1.33 0 001.14-2L8.87 2.58a1.33 1.33 0 00-2.28 0z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <line x1="8" y1="6" x2="8" y2="9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <circle cx="8" cy="11" r="0.5" fill="currentColor" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Upcoming Maintenance */}
      {upcomingMaintItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Upcoming Maintenance"
            items={upcomingMaintItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="2" y="2.67" width="12" height="12" rx="1.33" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <line x1="10.67" y1="1.33" x2="10.67" y2="4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <line x1="5.33" y1="1.33" x2="5.33" y2="4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <line x1="2" y1="6.67" x2="14" y2="6.67" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Certificates */}
      {certItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Certificates"
            docs={certItems}
            defaultCollapsed
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 14s5.33-2.67 5.33-6.67V3.33L8 1.33 2.67 3.33v4C2.67 11.33 8 14 8 14z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Maintenance History */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* History — prior periods */}
      <ScrollReveal>
        <HistorySection periods={historyPeriods} defaultCollapsed />
      </ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents2} defaultCollapsed />
      </ScrollReveal>

      {/* Photos — cohort-shared viewer (PR-EQ-4) */}
      <ScrollReveal>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 4px',
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--txt2)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Photos ({lensImages.length})
            </span>
          </div>
          <LensImageViewer
            images={lensImages}
            onUpload={() => setUploadModalOpen(true)}
            canUpload
            emptyMessage="No photos yet."
          />
          {/* Per-image comment thread button — opens threaded panel below */}
          {lensImages.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {lensImages.map((img) => (
                <button
                  key={img.id}
                  type="button"
                  onClick={() => handleOpenComments(img.id)}
                  aria-pressed={openCommentAttachmentId === img.id}
                  style={{
                    appearance: 'none',
                    background:
                      openCommentAttachmentId === img.id
                        ? 'var(--teal-bg)'
                        : 'var(--surface)',
                    border: '1px solid var(--border-sub)',
                    borderRadius: 4,
                    padding: '4px 8px',
                    cursor: 'pointer',
                    fontSize: 11,
                    color:
                      openCommentAttachmentId === img.id ? 'var(--mark)' : 'var(--txt2)',
                  }}
                >
                  {img.filename ?? 'image'} — comments
                </button>
              ))}
            </div>
          )}
          {openCommentAttachmentId && (
            <AttachmentCommentThread
              attachmentId={openCommentAttachmentId}
              comments={commentsByAttachment[openCommentAttachmentId] ?? []}
              loading={commentsLoading}
              busy={commentBusy}
              draft={commentDraft}
              onDraftChange={setCommentDraft}
              onAdd={handleAddComment}
              onDelete={handleDeleteComment}
              onClose={() => setOpenCommentAttachmentId(null)}
              currentUserId={user?.id ?? null}
            />
          )}
        </div>
      </ScrollReveal>

      {/* Attachments (non-image rows only) */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => setUploadModalOpen(true)}
          canAddFile
        />
      </ScrollReveal>

      {/* ActionPopup */}
      {actionPopupConfig && (
        <ActionPopup
          mode="mutate"
          title={actionPopupConfig.title}
          fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => {
            await executeAction(actionPopupConfig.actionId, values);
            setActionPopupConfig(null);
          }}
          onClose={() => setActionPopupConfig(null)}
        />
      )}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
      <AttachmentUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        entityType="equipment"
        entityId={entityId}
        // FIXME: migrate to pms-equipment-photos once CEO creates that bucket.
        // pms-work-order-photos is RLS-correct for polymorphic attachments today.
        bucket="pms-work-order-photos"
        category="equipment_photo"
        yachtId={(entity?.yacht_id as string) ?? user?.yachtId ?? ''}
        userId={user?.id ?? ''}
        title="Upload Equipment Photo"
        description="Attach a photo, schematic, or document to this equipment."
        onComplete={() => { refetch(); }}
      />
    </>
  );
}

// ─── AttachmentCommentThread — local, not shared ──────────────────────────────
// Renders the threaded comments tree returned by list_attachment_comments.
// Lives next to the LensImageViewer (which stays single-caption MVP). Tokenised.

interface AttachmentCommentThreadProps {
  attachmentId: string;
  comments: AttachmentCommentNode[];
  loading: boolean;
  busy: boolean;
  draft: string;
  onDraftChange: (next: string) => void;
  onAdd: (parentCommentId: string | null) => void | Promise<void>;
  onDelete: (commentId: string) => void | Promise<void>;
  onClose: () => void;
  currentUserId: string | null;
}

function AttachmentCommentThread({
  attachmentId,
  comments,
  loading,
  busy,
  draft,
  onDraftChange,
  onAdd,
  onDelete,
  onClose,
  currentUserId,
}: AttachmentCommentThreadProps) {
  const [replyTo, setReplyTo] = React.useState<string | null>(null);
  return (
    <div
      data-testid={`equipment-comment-thread-${attachmentId}`}
      style={{
        marginTop: 8,
        padding: 12,
        background: 'var(--surface)',
        border: '1px solid var(--border-faint)',
        borderRadius: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--txt)' }}>
          Comments
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            appearance: 'none',
            background: 'transparent',
            border: '1px solid var(--border-sub)',
            borderRadius: 4,
            padding: '2px 8px',
            fontSize: 11,
            color: 'var(--txt2)',
            cursor: 'pointer',
          }}
        >
          Close
        </button>
      </div>

      {loading && (
        <div style={{ fontSize: 12, color: 'var(--txt3)' }}>Loading comments…</div>
      )}

      {!loading && comments.length === 0 && (
        <div style={{ fontSize: 12, color: 'var(--txt3)', fontStyle: 'italic' }}>
          No comments yet. Be the first.
        </div>
      )}

      {!loading && comments.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {comments.map((c) => (
            <CommentNodeView
              key={c.id}
              node={c}
              depth={0}
              currentUserId={currentUserId}
              onReply={setReplyTo}
              onDelete={onDelete}
              busy={busy}
            />
          ))}
        </ul>
      )}

      <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
        <textarea
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          placeholder={replyTo ? 'Write a reply…' : 'Add a comment…'}
          rows={2}
          disabled={busy}
          style={{
            flex: 1,
            padding: '6px 8px',
            background: 'var(--neutral-bg)',
            border: '1px solid var(--border-sub)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--txt)',
            resize: 'vertical',
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <button
            type="button"
            onClick={() => onAdd(replyTo)}
            disabled={busy || !draft.trim()}
            style={{
              appearance: 'none',
              background: busy || !draft.trim() ? 'var(--neutral-bg)' : 'var(--teal-bg)',
              color: busy || !draft.trim() ? 'var(--txt3)' : 'var(--mark)',
              border: '1px solid var(--mark-hover)',
              borderRadius: 4,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              cursor: busy || !draft.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {replyTo ? 'Reply' : 'Post'}
          </button>
          {replyTo && (
            <button
              type="button"
              onClick={() => setReplyTo(null)}
              disabled={busy}
              style={{
                appearance: 'none',
                background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 4,
                padding: '2px 6px',
                fontSize: 10,
                color: 'var(--txt2)',
                cursor: busy ? 'not-allowed' : 'pointer',
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function CommentNodeView({
  node,
  depth,
  currentUserId,
  onReply,
  onDelete,
  busy,
}: {
  node: AttachmentCommentNode;
  depth: number;
  currentUserId: string | null;
  onReply: (commentId: string | null) => void;
  onDelete: (commentId: string) => void | Promise<void>;
  busy: boolean;
}) {
  const canDelete = currentUserId !== null && node.created_by === currentUserId;
  return (
    <li style={{ marginLeft: depth * 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div
        style={{
          padding: '6px 8px',
          background: 'var(--neutral-bg)',
          border: '1px solid var(--border-faint)',
          borderRadius: 4,
        }}
      >
        <div
          style={{
            fontSize: 10,
            color: 'var(--txt3)',
            fontFamily: 'var(--font-mono)',
            marginBottom: 2,
          }}
        >
          {node.author_department ? `${node.author_department} · ` : ''}
          {node.created_at?.slice(0, 19).replace('T', ' ')}
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt)', whiteSpace: 'pre-wrap' }}>
          {node.comment}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
          <button
            type="button"
            onClick={() => onReply(node.id)}
            disabled={busy}
            style={{
              appearance: 'none',
              background: 'transparent',
              border: 'none',
              padding: 0,
              fontSize: 10,
              color: 'var(--mark)',
              cursor: busy ? 'not-allowed' : 'pointer',
            }}
          >
            Reply
          </button>
          {canDelete && (
            <button
              type="button"
              onClick={() => onDelete(node.id)}
              disabled={busy}
              style={{
                appearance: 'none',
                background: 'transparent',
                border: 'none',
                padding: 0,
                fontSize: 10,
                color: 'var(--txt3)',
                cursor: busy ? 'not-allowed' : 'pointer',
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>
      {node.replies && node.replies.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {node.replies.map((child) => (
            <CommentNodeView
              key={child.id}
              node={child}
              depth={depth + 1}
              currentUserId={currentUserId}
              onReply={onReply}
              onDelete={onDelete}
              busy={busy}
            />
          ))}
        </ul>
      )}
    </li>
  );
}
