'use client';

/**
 * FaultContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-fault.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Corrective Action → RCA → Related → Notes → Docs → History → Audit Trail → Attachments
 *
 * TODO notes for next engineer:
 * - Add Comment handler not wired (onClick is noop)
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
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';

// Sections
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

// ─── Colour mapping helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'open':
      return 'red';
    case 'investigating':
    case 'under_review':
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

// ─── Component ───

export function FaultContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

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
  const reported_by = (entity?.reported_by ?? payload.reported_by) as string | undefined;
  const reported_date = (entity?.reported_date ?? payload.reported_date ?? entity?.reported_at ?? payload.reported_at ?? entity?.created_at ?? payload.created_at) as string | undefined;
  const resolved_date = (entity?.resolved_date ?? payload.resolved_date ?? entity?.resolved_at ?? payload.resolved_at) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const category = (entity?.category ?? payload.category) as string | undefined;
  const root_cause = (entity?.root_cause ?? payload.root_cause) as string | undefined;
  const corrective_action = (entity?.corrective_action ?? payload.corrective_action) as string | undefined;
  const vessel = (entity?.vessel_name ?? payload.vessel_name ?? entity?.yacht_name ?? payload.yacht_name) as string | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes ?? entity?.comments ?? payload.comments ?? entity?.journal ?? payload.journal) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];
  const documents = ((entity?.documents ?? payload.documents ?? entity?.reference_documents ?? payload.reference_documents) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const root_cause_items = ((entity?.root_cause_analysis ?? payload.root_cause_analysis) as Array<Record<string, unknown>> | undefined) ?? [];
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const investigateAction = getAction('investigate_fault');
  const resolveAction = getAction('resolve_fault');
  const closeAction = getAction('close_fault');
  const addNoteAction = getAction('add_fault_note');
  const archiveAction = getAction('archive_fault');

  // BACKEND_AUTO moved to mapActionFields.ts
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
  const severityLabel = formatLabel(severity);

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
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

  // ── Split button config ──
  // Primary action depends on current status
  const isOpen = status === 'open';
  const isInvestigating = ['investigating', 'under_review', 'acknowledged'].includes(status);
  const isResolved = status === 'resolved';
  const isClosed = status === 'closed';

  let primaryLabel: string;
  let primaryAction: string;
  if (isOpen && investigateAction !== null) {
    primaryLabel = 'Investigate';
    primaryAction = 'investigate_fault';
  } else if (isInvestigating && resolveAction !== null) {
    primaryLabel = 'Resolve Fault';
    primaryAction = 'resolve_fault';
  } else if ((isOpen || isInvestigating) && closeAction !== null) {
    primaryLabel = 'Close Fault';
    primaryAction = 'close_fault';
  } else if (isResolved && closeAction !== null) {
    primaryLabel = 'Close Fault';
    primaryAction = 'close_fault';
  } else {
    primaryLabel = 'Edit Details';
    primaryAction = '';
  }

  const hasPrimaryAction = primaryAction !== '';
  const primaryActionGate = primaryAction ? getAction(primaryAction) : null;
  const primaryDisabled = primaryActionGate?.disabled ?? false;
  const primaryDisabledReason = primaryActionGate?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    if (primaryAction) {
      await executeAction(primaryAction, {});
    }
  }, [primaryAction, executeAction]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_fault', 'delete_fault']);
  const primaryActionId = primaryAction;

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
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

  // Root Cause Analysis → KVItems
  const rcaItems: KVItem[] = root_cause_items.map((r) => ({
    label: (r.label ?? r.key ?? r.name) as string ?? '',
    value: (r.value ?? r.val) as string ?? '',
    mono: (r.mono as boolean | undefined) ?? false,
  }));

  // Notes → NoteItems
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
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

  // History → AuditEvents
  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Prior Periods → HistoryPeriods
  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  // Audit Trail → AuditEvents (distinct from history)
  const auditEvents2: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit2-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
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

  // Add note handler
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const handleAddNote = React.useCallback(() => setAddNoteOpen(true), []);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_fault_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  return (
    <>
      {/* Identity Strip */}
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

      {/* Corrective Action */}
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

      {/* Description (only if no corrective_action, to avoid duplication) */}
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

      {/* Root Cause Analysis */}
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

      {/* Related Entities */}
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

      {/* Comments / Journal */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? handleAddNote : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* Reference Documents */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Reference Documents" docs={docItems} />
        </ScrollReveal>
      )}

      {/* Evidence & Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {/* TODO: file upload modal (no component exists yet) */}}
          canAddFile
        />
      </ScrollReveal>

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* Audit Trail (audit_trail field) */}
      <ScrollReveal><AuditTrailSection events={auditEvents2} defaultCollapsed /></ScrollReveal>

      {actionPopupConfig && (
        <ActionPopup mode="mutate" title={actionPopupConfig.title} fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)} />
      )}
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
    </>
  );
}
