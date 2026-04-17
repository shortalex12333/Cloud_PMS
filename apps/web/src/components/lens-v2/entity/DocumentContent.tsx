'use client';

/**
 * DocumentContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-document.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Preview → Details → Revision History → History → Audit Trail → Acknowledgements → Notes → Attachments → Related
 *
 * TODO notes for next engineer:
 * - Add Note handler not wired
 * - File upload modal not wired
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

import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  DocRowsSection,
  KVSection,
  HistorySection,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
  type HistoryPeriod,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';

// ─── Colour mapping helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'current':
    case 'effective':
      return 'green';
    case 'superseded':
      return 'amber';
    case 'archived':
    case 'expired':
      return 'red';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatFileSize(bytes: number | undefined): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getDocTypeLabel(mimeType: string): string {
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.startsWith('image/')) return 'Image';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'Spreadsheet';
  if (mimeType.includes('document') || mimeType.includes('word')) return 'Document';
  return 'File';
}

// ─── Component ───

export function DocumentContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const document_code = (entity?.document_code ?? payload.document_code) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Document';
  const document_type = (entity?.document_type ?? payload.document_type) as string | undefined;
  const category = (entity?.category ?? payload.category) as string | undefined;
  const revision = (entity?.revision ?? payload.revision) as string | number | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const author = (entity?.author ?? payload.author) as string | undefined;
  const effective_date = (entity?.effective_date ?? payload.effective_date) as string | undefined;
  const file_name = (entity?.file_name ?? entity?.filename ?? payload.file_name ?? payload.filename) as string | undefined;
  const file_size = (entity?.file_size ?? payload.file_size) as number | undefined;
  const mime_type = ((entity?.mime_type ?? payload.mime_type) as string | undefined) ?? 'application/octet-stream';
  const file_url = (entity?.file_url ?? entity?.url ?? payload.file_url ?? payload.url) as string | undefined;
  const description = (entity?.description ?? payload.description) as string | undefined;
  const supersedes = (entity?.supersedes ?? payload.supersedes) as string | undefined;
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const vessel_name = (entity?.vessel_name ?? payload.vessel_name) as string | undefined;
  const page_count = (entity?.page_count ?? payload.page_count) as number | undefined;

  // Section data
  const revisions = ((entity?.revisions ?? payload.revisions ?? entity?.revision_history ?? payload.revision_history) as Array<Record<string, unknown>> | undefined) ?? [];
  const acknowledgements = ((entity?.acknowledgements ?? payload.acknowledgements ?? entity?.read_acknowledgements ?? payload.read_acknowledgements) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];

  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const archiveAction = getAction('archive_document');
  const addNoteAction = getAction('add_document_note');

  // BACKEND_AUTO moved to mapActionFields.ts
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_document_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  // ── Derived display ──
  const statusLabel = formatLabel(status);
  const docType = getDocTypeLabel(mime_type);
  const sizeDisplay = formatFileSize(file_size);

  // Pills
  const pills: PillDef[] = [];
  if (revision !== undefined) {
    const revLabel = `Rev. ${revision}`;
    const effectiveLabel = effective_date ? ` · Effective ${effective_date}` : '';
    pills.push({ label: `${revLabel}${effectiveLabel}`, variant: statusToPillVariant(status) });
  } else {
    pills.push({ label: statusLabel, variant: statusToPillVariant(status) });
  }

  const fileMeta: string[] = [];
  if (docType) fileMeta.push(docType);
  if (sizeDisplay !== '—') fileMeta.push(sizeDisplay);
  if (page_count) fileMeta.push(`${page_count} pages`);
  if (fileMeta.length > 0) {
    pills.push({ label: fileMeta.join(' · '), variant: 'neutral' });
  }

  // Detail lines
  const details: DetailLine[] = [];
  if (file_name) {
    details.push({ label: 'Filename', value: file_name, mono: true });
  }
  if (author) {
    details.push({ label: 'Author', value: author });
  }
  if (supersedes) {
    details.push({ label: 'Supersedes', value: supersedes });
  }

  // Context line
  const contextParts: string[] = [];
  if (category ?? document_type) contextParts.push((category ?? document_type) as string);
  if (department) contextParts.push(department);
  if (vessel_name) contextParts.push(vessel_name);
  const contextNode = contextParts.length > 0 ? (
    <>{contextParts.join(' · ')}</>
  ) : undefined;

  // ── Split button config ──
  const handlePrimary = React.useCallback(async () => {
    if (file_url) {
      // Download is a browser action, not a server action
      const a = document.createElement('a');
      a.href = file_url;
      a.download = file_name ?? 'document';
      a.click();
    }
  }, [file_url, file_name]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_document', 'delete_document']);

  const dropdownItems: DropdownItem[] = availableActions
    .map((a) => ({
      label: a.label,
      onClick: SPECIAL_HANDLERS[a.action_id]
        ? SPECIAL_HANDLERS[a.action_id]
        : () => {
            const hasFields = actionHasFields(a as any);
            if (hasFields || a.requires_signature) { openActionPopup(a); } else { executeAction(a.action_id); }
          },
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
    }));

  // ── Map section data ──

  // Revision history → AuditTrail events
  const revisionEvents: AuditEvent[] = revisions.map((r, i) => ({
    id: (r.id as string) ?? `rev-${i}`,
    action: `Rev. ${r.revision ?? r.version ?? i + 1}${r.note ? ` — ${r.note}` : ''}${r.description ? ` — ${r.description}` : ''}`,
    actor: (r.author ?? r.created_by ?? r.user_name) as string | undefined,
    timestamp: (r.effective_date ?? r.created_at ?? r.date) as string ?? '',
  }));

  // Read acknowledgements → KV items
  const ackItems: KVItem[] = acknowledgements.map((a, i) => ({
    label: (a.user_name ?? a.acknowledged_by ?? `User ${i + 1}`) as string,
    value: (a.acknowledged_at ?? a.date ?? a.timestamp) as string ?? '—',
    mono: true,
  }));

  // Notes
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // Attachments
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  // Related entities → DocRows
  const relatedItems: DocRowItem[] = related_entities.map((r, i) => ({
    id: (r.id as string) ?? `rel-${i}`,
    name: (r.name ?? r.title) as string ?? 'Entity',
    code: (r.code ?? r.reference) as string | undefined,
    meta: (r.type ?? r.entity_type) as string | undefined,
    onClick: r.id && r.entity_type
      ? () => router.push(getEntityRoute(r.entity_type as Parameters<typeof getEntityRoute>[0], r.id as string))
      : undefined,
  }));

  // History periods
  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  // Audit trail events
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Document Details KV
  const docDetailItems: KVItem[] = [];
  if (document_type) docDetailItems.push({ label: 'Type', value: formatLabel(document_type) });
  if (category) docDetailItems.push({ label: 'Category', value: category });
  if (mime_type !== 'application/octet-stream') docDetailItems.push({ label: 'MIME Type', value: mime_type, mono: true });
  if (file_size) docDetailItems.push({ label: 'File Size', value: sizeDisplay });
  if (page_count) docDetailItems.push({ label: 'Pages', value: `${page_count}` });
  if (effective_date) docDetailItems.push({ label: 'Effective Date', value: effective_date, mono: true });
  if (equipment_name) {
    docDetailItems.push({
      label: 'Equipment',
      value: equipment_id ? (
        <span
          className={styles.equipLink}
          onClick={() => router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipment_id))}
        >
          {equipment_name}
        </span>
      ) : equipment_name,
    });
  }

  return (
    <div data-testid="document-content">
      {/* Identity Strip */}
      <IdentityStrip
        overline={document_code}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          file_url ? (
            <SplitButton
              label="Download"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              }
              onClick={handlePrimary}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label="Actions"
              onClick={() => {}}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Document Preview */}
      <ScrollReveal>
        <div className={styles.section}>
          <div className={styles.previewArea}>
            <div className={styles.previewBadge}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {statusLabel} Document
            </div>

            {/* Minimal preview representation */}
            <div style={{
              width: '100%', maxWidth: 560,
              background: 'var(--surface-base)',
              border: '1px solid var(--border-sub)',
              borderRadius: 4,
              padding: '40px 36px',
              display: 'flex', flexDirection: 'column', gap: 14,
              userSelect: 'text',
              textAlign: 'center',
            }}>
              <div style={{
                fontSize: 16, fontWeight: 700,
                color: 'var(--txt)', letterSpacing: '-0.01em',
                paddingBottom: 12,
                borderBottom: '2px solid var(--border-sub)',
              }}>
                {title}
              </div>
              {(category ?? document_type) && (
                <div style={{
                  fontSize: 11, fontWeight: 500,
                  color: 'var(--txt3)', textTransform: 'uppercase',
                  letterSpacing: '0.06em', marginTop: -8,
                }}>
                  {category ?? document_type}
                </div>
              )}
              <div className={styles.mono} style={{
                fontSize: 11, color: 'var(--txt3)', textAlign: 'center',
              }}>
                {document_code}{revision !== undefined && ` · Rev. ${revision}`}{effective_date && ` · Effective ${effective_date}`}
              </div>
              {file_name && (
                <div className={styles.mono} style={{
                  fontSize: 11, color: 'var(--txt3)',
                }}>
                  {file_name}
                </div>
              )}
            </div>
          </div>
          {page_count && (
            <div className={styles.previewActions}>
              <span className={styles.mono} style={{ fontSize: 11, color: 'var(--txt3)' }}>
                {page_count} pages
              </span>
            </div>
          )}
        </div>
      </ScrollReveal>

      {/* Document Details */}
      {docDetailItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Document Details"
            items={docDetailItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Revision History */}
      <ScrollReveal>
        <AuditTrailSection events={revisionEvents} defaultCollapsed={false} />
      </ScrollReveal>

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal><AuditTrailSection events={auditEvents} defaultCollapsed /></ScrollReveal>

      {/* Read Acknowledgements */}
      {ackItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Read Acknowledgements"
            items={ackItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M14 4L6 12l-4-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {/* TODO: file upload modal (no component exists yet) */}}
          canAddFile
        />
      </ScrollReveal>

      {/* Related Entities */}
      {relatedItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Entities" docs={relatedItems} />
        </ScrollReveal>
      )}

      {actionPopupConfig && (
        <ActionPopup
          mode="mutate"
          title={actionPopupConfig.title}
          fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)}
        />
      )}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
    </div>
  );
}
