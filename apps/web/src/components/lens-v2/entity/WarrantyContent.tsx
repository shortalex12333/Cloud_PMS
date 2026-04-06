'use client';

/**
 * WarrantyContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-warranty.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Coverage → Financials → Claims → Equipment → Related → History → Audit Trail → Notes → Attachments
 *
 * TODO notes for next engineer:
 * - Upload Document handler not wired
 * - Add Note handler not wired
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

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
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

// ─── Colour mapping helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'active':
      return 'green';
    case 'expiring':
      return 'amber';
    case 'expired':
    case 'claimed':
      return 'red';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function WarrantyContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const warranty_number = (entity?.warranty_number ?? payload.warranty_number) as string | undefined;
  const title = ((entity?.title ?? entity?.name ?? payload.title ?? payload.name) as string | undefined) ?? 'Warranty';
  const provider = (entity?.provider ?? entity?.supplier ?? payload.provider ?? payload.supplier) as string | undefined;
  const start_date = (entity?.start_date ?? payload.start_date) as string | undefined;
  const end_date = (entity?.end_date ?? entity?.expiry_date ?? payload.end_date ?? payload.expiry_date) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'active';
  const coverage_type = (entity?.coverage_type ?? entity?.coverage ?? payload.coverage_type ?? payload.coverage) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code) as string | undefined;
  const agreement_number = (entity?.agreement_number ?? payload.agreement_number) as string | undefined;
  const managed_by = (entity?.managed_by ?? payload.managed_by) as string | undefined;
  const vessel_name = (entity?.vessel_name ?? payload.vessel_name) as string | undefined;
  const description = (entity?.description ?? payload.description) as string | undefined;

  // Coverage detail fields
  const coverage_duration = (entity?.coverage_duration ?? payload.coverage_duration) as string | undefined;
  const components_covered = (entity?.components_covered ?? payload.components_covered) as string | undefined;
  const exclusions = (entity?.exclusions ?? payload.exclusions) as string | undefined;
  const labour_terms = (entity?.labour_terms ?? payload.labour_terms) as string | undefined;
  const parts_terms = (entity?.parts_terms ?? payload.parts_terms) as string | undefined;
  const response_time = (entity?.response_time ?? payload.response_time) as string | undefined;
  const max_claim_value = (entity?.max_claim_value ?? payload.max_claim_value) as string | undefined;

  // Financial fields
  const total_claimed = (entity?.total_claimed ?? payload.total_claimed) as string | number | undefined;
  const approved_amount = (entity?.approved_amount ?? payload.approved_amount) as string | number | undefined;
  const labour_cost = (entity?.labour_cost ?? payload.labour_cost) as string | number | undefined;
  const parts_cost = (entity?.parts_cost ?? payload.parts_cost) as string | number | undefined;
  const other_costs = (entity?.other_costs ?? payload.other_costs) as string | number | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const claims_history = ((entity?.claims_history ?? payload.claims_history ?? entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_equipment = ((entity?.related_equipment ?? payload.related_equipment ?? entity?.equipment ?? payload.equipment) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const fileClaimAction = getAction('file_warranty_claim');
  const extendAction = getAction('extend_warranty');
  const archiveAction = getAction('archive_warranty');
  const addNoteAction = getAction('add_warranty_note');
  const uploadDocAction = getAction('add_warranty_attachment');

  // BACKEND_AUTO moved to mapActionFields.ts
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  const canFileClaim = fileClaimAction !== null && ['active', 'expiring'].includes(status);

  // ── Derived display ──
  const statusLabel = formatLabel(status);

  // Calculate days remaining
  let days_remaining: number | undefined;
  if (end_date) {
    days_remaining = Math.floor((new Date(end_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  }
  // Also try explicit days_remaining from entity
  const explicit_days = (entity?.days_remaining ?? payload.days_remaining) as number | undefined;
  const daysRemaining = explicit_days ?? days_remaining;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (daysRemaining !== undefined && daysRemaining > 0) {
    pills.push({ label: `${daysRemaining} days remaining`, variant: statusToPillVariant(status) });
  }

  const details: DetailLine[] = [];
  if (equipment_name) {
    const equipDisplay = equipment_code ? `${equipment_code} ${equipment_name}` : equipment_name;
    details.push({ label: 'Equipment', value: equipDisplay });
  }
  if (provider) {
    details.push({ label: 'Supplier', value: provider });
  }
  if (start_date) {
    details.push({ label: 'Start Date', value: start_date, mono: true });
  }
  if (end_date) {
    details.push({ label: 'Expiry Date', value: end_date, mono: true });
  }
  if (coverage_type) {
    details.push({ label: 'Coverage', value: coverage_type });
  }
  if (agreement_number) {
    details.push({ label: 'Agreement No', value: agreement_number, mono: true });
  }
  if (managed_by) {
    details.push({ label: 'Managed By', value: managed_by });
  }
  // Days remaining with mono formatting (prominent display per spec)
  if (daysRemaining !== undefined) {
    details.push({ label: 'Days Remaining', value: `${daysRemaining}`, mono: true });
  }

  // Context line
  const contextParts: string[] = [];
  if (provider) contextParts.push(provider);
  if (vessel_name) contextParts.push(vessel_name);
  const contextNode = contextParts.length > 0 ? <>{contextParts.join(' · ')}</> : undefined;

  // ── Split button config ──
  const primaryLabel = 'Submit Claim';
  const primaryDisabled = !canFileClaim || (fileClaimAction?.disabled ?? false);
  const primaryDisabledReason = fileClaimAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('file_warranty_claim', {
      equipment_id: equipment_id ?? '',
    });
  }, [executeAction, equipment_id]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_warranty', 'void_warranty']);
  const primaryActionId = 'file_warranty_claim';

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

  // Coverage details (KVSection)
  const coverageItems: KVItem[] = [];
  if (coverage_type) coverageItems.push({ label: 'Type', value: coverage_type });
  if (coverage_duration) coverageItems.push({ label: 'Duration', value: coverage_duration });
  if (components_covered) coverageItems.push({ label: 'Components Covered', value: components_covered });
  if (exclusions) coverageItems.push({ label: 'Exclusions', value: exclusions });
  if (labour_terms) coverageItems.push({ label: 'Labour', value: labour_terms });
  if (parts_terms) coverageItems.push({ label: 'Parts', value: parts_terms });
  if (response_time) coverageItems.push({ label: 'Response Time', value: response_time });
  if (max_claim_value) coverageItems.push({ label: 'Max Claim Value', value: max_claim_value });

  // Financial summary (KVSection)
  const financialItems: KVItem[] = [];
  if (labour_cost !== undefined) financialItems.push({ label: 'Labour', value: `${labour_cost}`, mono: true });
  if (parts_cost !== undefined) financialItems.push({ label: 'Parts', value: `${parts_cost}`, mono: true });
  if (other_costs !== undefined) financialItems.push({ label: 'Travel / Shipping', value: `${other_costs}`, mono: true });
  if (total_claimed !== undefined) financialItems.push({ label: 'Total Claimed', value: `${total_claimed}`, mono: true });
  if (approved_amount !== undefined) financialItems.push({ label: 'Approved Amount', value: `${approved_amount}`, mono: true });

  // Claims history (AuditTrail)
  const claimEvents: AuditEvent[] = claims_history.map((h, i) => ({
    id: (h.id as string) ?? `claim-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.date ?? h.timestamp) as string ?? '',
  }));

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Related equipment (DocRows)
  const equipmentItems: DocRowItem[] = related_equipment.map((e, i) => ({
    id: (e.id as string) ?? `equip-${i}`,
    name: (e.name ?? e.equipment_name) as string ?? 'Equipment',
    code: (e.code ?? e.equipment_code) as string | undefined,
    meta: (e.meta ?? e.location ?? e.description) as string | undefined,
    onClick: e.equipment_id
      ? () => router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], e.equipment_id as string))
      : undefined,
  }));
  // If no related_equipment array but we have a single equipment reference, create one row
  if (equipmentItems.length === 0 && equipment_id && equipment_name) {
    equipmentItems.push({
      id: equipment_id,
      name: equipment_name,
      code: equipment_code,
      onClick: () => router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipment_id)),
    });
  }

  // Related entities (DocRows — general related)
  const relatedItems: DocRowItem[] = related_entities.map((r, i) => ({
    id: (r.id as string) ?? `related-${i}`,
    name: (r.name ?? r.title) as string ?? 'Entity',
    code: (r.code ?? r.reference) as string | undefined,
    meta: (r.meta ?? r.entity_type ?? r.type) as string | undefined,
    date: (r.date ?? r.created_at) as string | undefined,
    onClick: r.entity_id && r.entity_type
      ? () => router.push(getEntityRoute(r.entity_type as Parameters<typeof getEntityRoute>[0], r.entity_id as string))
      : undefined,
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

  const handleAddNote = React.useCallback(() => {}, []);

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={warranty_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          fileClaimAction ? (
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

      {/* Coverage Details */}
      {coverageItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Coverage Details"
            items={coverageItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Financial Summary */}
      {financialItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Claim Financials"
            items={financialItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" /></svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Claims History */}
      <ScrollReveal>
        <AuditTrailSection
          events={claimEvents}
          title="Audit Trail"
        />
      </ScrollReveal>

      {/* Related Equipment */}
      {equipmentItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Equipment" docs={equipmentItems} />
        </ScrollReveal>
      )}

      {/* Related Entities */}
      {relatedItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Entities" docs={relatedItems} />
        </ScrollReveal>
      )}

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal><AuditTrailSection events={auditEvents} defaultCollapsed /></ScrollReveal>

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={handleAddNote}
          canAddNote
        />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile
        />
      </ScrollReveal>

      {actionPopupConfig && (
        <ActionPopup mode="mutate" title={actionPopupConfig.title} fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)} />
      )}
    </>
  );
}
