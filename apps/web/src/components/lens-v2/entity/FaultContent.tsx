'use client';

/**
 * FaultContent — lens-v2 entity view (full redesign, Issue 7 v2).
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections (document metaphor, top → bottom):
 * 1. Hero image (first attachment photo, or placeholder)
 * 2. Identity strip (title, fault code, status pills, context line)
 * 3. Detail lines (severity, location, reported date)
 * 4. Corrective Action / Description KV block
 * 5. Root Cause Analysis
 * 6. Related Entities
 * 7. NOTES
 * 8. ATTACHMENTS
 * 9. LINKED PARTS
 * 10. AUDIT TRAIL
 *
 * History section deliberately omitted — not applicable to faults entity.
 * Duplicate audit-trail section removed in PR #706.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/entityRoutes';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';

// Sections
import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  DocRowsSection,
  KVSection,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
} from '../sections';

// ─── Colour mapping helpers ───────────────────────────────────────────────────

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'open':
      return 'red';
    case 'investigating':
    case 'under_review':
      return 'amber';
    case 'acknowledged':
      return 'amber';
    case 'resolved':
      return 'green';
    case 'closed':
      return 'neutral';
    default:
      return 'neutral';
  }
}

function severityToPillVariant(severity: string): PillDef['variant'] {
  switch (severity) {
    case 'critical':
      return 'red';
    case 'high':
      return 'red';
    case 'medium':
      return 'amber';
    case 'low':
      return 'neutral';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Hero Image ───────────────────────────────────────────────────────────────

interface HeroImageProps {
  url: string | undefined;
  alt: string;
}

function HeroImage({ url, alt }: HeroImageProps) {
  if (url) {
    return (
      <div style={{ marginBottom: '16px', borderRadius: '8px', overflow: 'hidden', maxHeight: '280px' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt={alt}
          style={{
            width: '100%',
            maxHeight: '280px',
            objectFit: 'cover',
            display: 'block',
          }}
        />
      </div>
    );
  }
  return (
    <div
      style={{
        marginBottom: '16px',
        borderRadius: '8px',
        background: 'var(--surface)',
        border: '1px solid var(--border-sub)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        minHeight: '120px',
        color: 'var(--txt-ghost)',
      }}
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" />
        <circle cx="12" cy="13" r="4" />
      </svg>
      <span style={{ fontSize: '12px', letterSpacing: '0.04em' }}>No photos yet</span>
    </div>
  );
}

// ─── Linked Parts Section ─────────────────────────────────────────────────────

interface LinkedPart {
  part_id: string;
  part_name: string;
  part_number?: string;
  stock_level?: number | string;
  notes?: string;
  created_at?: string;
}

interface LinkedPartsSectionProps {
  parts: LinkedPart[];
  canLink: boolean;
  onLink: () => void;
  onUnlink: (partId: string) => void;
}

function LinkedPartsSection({ parts, canLink, onLink, onUnlink }: LinkedPartsSectionProps) {
  return (
    <section style={{ padding: '0 0 16px 0' }}>
      {/* Section heading — design system pattern */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderTop: '1px solid var(--border-sub)',
        paddingTop: '16px',
        marginBottom: '12px',
      }}>
        <span style={{
          fontSize: '14px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--txt3)',
        }}>
          Linked Parts
        </span>
        {canLink && (
          <button
            type="button"
            onClick={onLink}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--mark)',
              fontSize: '13px',
              fontWeight: 500,
              padding: '4px 0',
            }}
          >
            + Link Parts
          </button>
        )}
      </div>

      {parts.length === 0 ? (
        <p style={{ fontSize: '12px', color: 'var(--txt-ghost)', margin: 0 }}>No parts linked</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {parts.map((part) => (
            <LinkedPartRow key={part.part_id} part={part} onUnlink={onUnlink} />
          ))}
        </ul>
      )}
    </section>
  );
}

function LinkedPartRow({ part, onUnlink }: { part: LinkedPart; onUnlink: (id: string) => void }) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <li
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        minHeight: '44px',
        padding: '8px 12px',
        background: hovered ? 'var(--surface-hover)' : 'transparent',
        borderRadius: '6px',
        transition: 'background 0.15s ease',
      }}
    >
      <span style={{ fontSize: '14px', color: 'var(--txt2)' }}>
        {part.part_name}
        {part.part_number && (
          <>
            {' · '}
            <span style={{ fontFamily: 'monospace', fontSize: '13px' }}>{part.part_number}</span>
          </>
        )}
        {part.stock_level !== undefined && part.stock_level !== null && (
          <> · Stock: {part.stock_level}</>
        )}
      </span>
      {hovered && (
        <button
          type="button"
          aria-label={`Unlink ${part.part_name}`}
          onClick={() => onUnlink(part.part_id)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--txt3)',
            fontSize: '16px',
            lineHeight: 1,
            padding: '0 4px',
          }}
        >
          ×
        </button>
      )}
    </li>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────

export function FaultContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading, refetch } = useEntityLensContext();
  const { user } = useAuth();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const fault_number = (entity?.fault_number ?? payload.fault_number ?? entity?.code ?? payload.code) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Fault';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'open';
  const severity = ((entity?.severity ?? payload.severity) as string | undefined) ?? 'medium';
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code) as string | undefined;
  // UUID → human name enrichment: prefer *_name variants, fallback to truncated UUID
  const reported_by_raw = (entity?.reported_by ?? payload.reported_by) as string | undefined;
  const reported_by_name = (entity?.reported_by_name ?? payload.reported_by_name) as string | undefined;
  const reported_by = reported_by_name ?? (reported_by_raw && reported_by_raw.length > 12
    ? `${reported_by_raw.slice(0, 8)}…`
    : reported_by_raw);
  const reported_date = (entity?.reported_date ?? payload.reported_date ?? entity?.reported_at ?? payload.reported_at ?? entity?.created_at ?? payload.created_at) as string | undefined;
  const resolved_date = (entity?.resolved_date ?? payload.resolved_date ?? entity?.resolved_at ?? payload.resolved_at) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const category = (entity?.category ?? payload.category) as string | undefined;
  const root_cause = (entity?.root_cause ?? payload.root_cause) as string | undefined;
  const corrective_action = (entity?.corrective_action ?? payload.corrective_action) as string | undefined;
  const vessel = (entity?.vessel_name ?? payload.vessel_name ?? entity?.yacht_name ?? payload.yacht_name) as string | undefined;
  const deleted_at = (entity?.deleted_at ?? payload.deleted_at) as string | null | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes ?? entity?.comments ?? payload.comments) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];
  const documents = ((entity?.documents ?? payload.documents ?? entity?.reference_documents ?? payload.reference_documents) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const root_cause_items = ((entity?.root_cause_analysis ?? payload.root_cause_analysis) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];
  const linkedPartsRaw = ((entity?.linked_parts ?? payload.linked_parts) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Hero image: first attachment with a url ──
  const heroAttachment = attachments.find((a) => {
    const url = (a.url ?? a.signed_url ?? a.storage_path) as string | undefined;
    return !!url;
  });
  const heroUrl = heroAttachment
    ? ((heroAttachment.url ?? heroAttachment.signed_url) as string | undefined)
    : undefined;

  // ── Action gates ──
  const acknowledgeAction = getAction('acknowledge_fault');
  const resolveAction = getAction('resolve_fault');
  const closeAction = getAction('close_fault');
  const addNoteAction = getAction('add_fault_note');
  const addPhotoAction = getAction('add_fault_photo');
  const archiveAction = getAction('archive_fault');
  const linkPartsAction = getAction('link_parts_to_fault');
  const addToHandoverAction = getAction('add_to_handover');
  const reopenAction = getAction('reopen_fault');

  // ── Popup state ──
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as never);
    const sigLevel = getSignatureLevel(action as never);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  // ── Derived display ──
  const isArchived = Boolean(deleted_at);
  const isOpen = status === 'open';
  const isInvestigating = ['investigating', 'under_review', 'acknowledged'].includes(status);
  const isResolved = status === 'resolved';
  const isClosed = status === 'closed';
  const canMutate = !isArchived;

  const statusLabel = formatLabel(status);
  const severityLabel = formatLabel(severity);

  const pills: PillDef[] = [
    { label: isArchived ? 'Archived' : statusLabel, variant: isArchived ? 'neutral' : statusToPillVariant(status) },
  ];
  if (severity !== 'medium') {
    pills.push({ label: severityLabel, variant: severityToPillVariant(severity) });
  }

  const details: DetailLine[] = [];
  if (equipment_name) {
    details.push({ label: 'Equipment', value: `${equipment_code ?? ''} ${equipment_name}`.trim() });
  }
  if (reported_date) {
    details.push({ label: 'Date Reported', value: reported_date, mono: true });
  }
  if (category) {
    details.push({ label: 'Category', value: category });
  }
  if (root_cause) {
    details.push({ label: 'Root Cause', value: root_cause });
  }
  if (resolved_date) {
    details.push({ label: 'Resolved', value: resolved_date, mono: true });
  }

  // Context line (location + reporter + vessel)
  const contextParts: string[] = [];
  if (location) contextParts.push(location);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {reported_by && (
        <>
          {contextParts.length > 0 && ' · '}
          Reported by <span className={styles.crewLink}>{reported_by}</span>
        </>
      )}
      {vessel && (
        <>
          {(contextParts.length > 0 || reported_by) && ' · '}
          {vessel}
        </>
      )}
    </>
  );

  // ── Primary-action matrix ──
  // open           → Acknowledge Fault
  // investigating  → Create Work Order (spec §4 v2 update)
  // acknowledged   → Create Work Order
  // resolved       → Close Fault
  // closed         → no primary
  // archived       → no primary
  const createWOAction = getAction('create_work_order_from_fault');

  let primaryLabel = '';
  let primaryAction = '';
  if (!isArchived && !isClosed) {
    if (isOpen && acknowledgeAction !== null) {
      primaryLabel = 'Acknowledge Fault';
      primaryAction = 'acknowledge_fault';
    } else if (isInvestigating && createWOAction !== null) {
      primaryLabel = 'Create Work Order';
      primaryAction = 'create_work_order_from_fault';
    } else if (isInvestigating && resolveAction !== null) {
      primaryLabel = 'Resolve Fault';
      primaryAction = 'resolve_fault';
    } else if (isResolved && closeAction !== null) {
      primaryLabel = 'Close Fault';
      primaryAction = 'close_fault';
    }
  }

  const hasPrimaryAction = primaryAction !== '';
  const primaryActionGate = primaryAction ? getAction(primaryAction) : null;
  const primaryDisabled = primaryActionGate?.disabled ?? false;
  const primaryDisabledReason = primaryActionGate?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    if (primaryAction) {
      const gate = getAction(primaryAction);
      if (gate && (actionHasFields(gate as never) || gate.requires_signature)) {
        openActionPopup(gate);
      } else {
        await executeAction(primaryAction, {});
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [primaryAction, executeAction]);

  // ── Add note handler ──
  const handleAddNote = React.useCallback(() => setAddNoteOpen(true), []);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_fault_note', { text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  // ── Linked parts unlink handler ──
  const handleUnlinkPart = React.useCallback(async (partId: string) => {
    await executeAction('unlink_part_from_fault', { fault_id: entity?.id, part_id: partId });
    refetch();
  }, [executeAction, entity?.id, refetch]);

  // ── Build dropdown items explicitly (not from availableActions filter) ──
  const dropdownItems: DropdownItem[] = [];

  if (canMutate) {
    if (addNoteAction) {
      dropdownItems.push({
        label: 'Add Note',
        onClick: handleAddNote,
        disabled: addNoteAction.disabled,
        disabledReason: addNoteAction.disabled_reason ?? undefined,
      });
    }
    if (addPhotoAction) {
      dropdownItems.push({
        label: 'Add Photo',
        onClick: () => setUploadOpen(true),
        disabled: addPhotoAction.disabled,
        disabledReason: addPhotoAction.disabled_reason ?? undefined,
      });
    }
    if (addToHandoverAction) {
      dropdownItems.push({
        label: 'Add to Handover',
        onClick: () => openActionPopup(addToHandoverAction),
        disabled: addToHandoverAction.disabled,
        disabledReason: addToHandoverAction.disabled_reason ?? undefined,
      });
    }
    if (linkPartsAction) {
      dropdownItems.push({
        label: 'Link Parts',
        onClick: () => openActionPopup(linkPartsAction),
        disabled: linkPartsAction.disabled,
        disabledReason: linkPartsAction.disabled_reason ?? undefined,
      });
    }
    if ((isResolved || isClosed) && reopenAction) {
      dropdownItems.push({
        label: 'Reopen Fault',
        onClick: () => openActionPopup(reopenAction),
        disabled: reopenAction.disabled,
        disabledReason: reopenAction.disabled_reason ?? undefined,
      });
    }
    if (!isArchived && archiveAction) {
      dropdownItems.push({
        label: 'Archive Fault',
        onClick: () => openActionPopup(archiveAction),
        disabled: archiveAction.disabled,
        disabledReason: archiveAction.disabled_reason ?? undefined,
        danger: true,
      });
    }
  }

  // ── Map section data ──

  // Root Cause Analysis → KVItems
  const rcaItems: KVItem[] = root_cause_items.map((r) => ({
    label: (r.label ?? r.key ?? r.name) as string ?? '',
    value: (r.value ?? r.val) as string ?? '',
    mono: (r.mono as boolean | undefined) ?? false,
  }));

  // Notes → NoteItems
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by_name ?? n.created_by ?? n.user_name ?? n.added_by) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp ?? n.added_at) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // Related entities → DocRows
  const relatedItems: DocRowItem[] = related_entities.map((r, i) => ({
    id: (r.id as string) ?? `rel-${i}`,
    name: (r.title ?? r.name) as string ?? 'Entity',
    code: (r.code ?? r.reference ?? r.entity_code) as string | undefined,
    meta: (r.entity_type ?? r.type ?? r.meta) as string | undefined,
    onClick: r.id && r.entity_type
      ? () => router.push(getEntityRoute(r.entity_type as Parameters<typeof getEntityRoute>[0], r.id as string))
      : undefined,
  }));

  // Documents → DocRows
  const docItems: DocRowItem[] = documents.map((d, i) => ({
    id: (d.id as string) ?? `doc-${i}`,
    name: (d.name ?? d.title ?? d.file_name) as string ?? 'Document',
    code: (d.code ?? d.document_code ?? d.reference) as string | undefined,
    meta: (d.meta ?? d.description) as string | undefined,
    date: (d.date ?? d.effective_date ?? d.expires_at) as string | undefined,
    onClick: d.document_id ? () => router.push(getEntityRoute('documents' as Parameters<typeof getEntityRoute>[0], d.document_id as string)) : undefined,
  }));

  // Audit Trail → AuditEvents
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.actor_name ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Attachments → AttachmentItems
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  // Linked Parts
  const linkedParts: LinkedPart[] = linkedPartsRaw.map((p) => ({
    part_id: (p.part_id ?? p.id) as string,
    part_name: (p.part_name ?? p.name) as string ?? 'Unknown Part',
    part_number: (p.part_number ?? p.number) as string | undefined,
    stock_level: (p.stock_level ?? p.stock) as number | string | undefined,
    notes: (p.notes ?? p.note) as string | undefined,
    created_at: (p.created_at) as string | undefined,
  }));

  return (
    <>
      {/* 1. Hero Image */}
      <HeroImage url={heroUrl} alt={title} />

      {/* 2. Identity Strip */}
      <IdentityStrip
        overline={fault_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={corrective_action ? undefined : description}
        actionSlot={
          hasPrimaryAction ? (
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

      {/* 3. Corrective Action */}
      {corrective_action && (
        <ScrollReveal>
          <KVSection
            title="Corrective Action"
            items={[{ label: '', value: corrective_action }]}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M9.8 4.2a.67.67 0 000 .93l1.07 1.07a.67.67 0 00.93 0l2.51-2.51a4 4 0 01-5.29 5.29L4.41 13.6a1.41 1.41 0 01-2-2l4.61-4.61A4 4 0 0112.31 1.7L9.8 4.2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* 3b. Description (only if no corrective_action) */}
      {!corrective_action && description && (
        <ScrollReveal>
          <KVSection
            title="Description"
            items={[{ label: '', value: description }]}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* 4. Root Cause Analysis */}
      {rcaItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Root Cause Analysis"
            items={rcaItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" />
                <line x1="8" y1="5.5" x2="8" y2="8.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <circle cx="8" cy="10.5" r="0.5" fill="currentColor" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* 5. Related Entities */}
      {relatedItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Related Entities"
            docs={relatedItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" />
                <path d="M1.5 8h13M8 1.5a10 10 0 012.67 6.5A10 10 0 018 14.5a10 10 0 01-2.67-6.5A10 10 0 018 1.5z" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* 6. Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? handleAddNote : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* 7. Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={addPhotoAction ? () => setUploadOpen(true) : undefined}
          canAddFile={!!addPhotoAction}
        />
      </ScrollReveal>

      {/* 8. Reference Documents (when present) */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Reference Documents" docs={docItems} />
        </ScrollReveal>
      )}

      {/* 9. Linked Parts */}
      <ScrollReveal>
        <LinkedPartsSection
          parts={linkedParts}
          canLink={!!linkPartsAction && canMutate}
          onLink={() => linkPartsAction && openActionPopup(linkPartsAction)}
          onUnlink={handleUnlinkPart}
        />
      </ScrollReveal>

      {/* 10. Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* ── Modals ── */}
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

      {user?.yachtId && user?.id && (
        <AttachmentUploadModal
          open={uploadOpen}
          onClose={() => setUploadOpen(false)}
          entityType="fault"
          entityId={(entity?.id as string | undefined) ?? ''}
          bucket="pms-fault-photos"
          category="fault_photo"
          yachtId={user.yachtId}
          userId={user.id}
          onComplete={() => {
            setUploadOpen(false);
            refetch();
          }}
          title="Add Fault Photo"
        />
      )}
    </>
  );
}
