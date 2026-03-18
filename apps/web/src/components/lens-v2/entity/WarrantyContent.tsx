'use client';

/**
 * WarrantyContent — lens-v2 Warranty entity view.
 * Matches lens-warranty.html prototype.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines (days remaining)
 * 2. Coverage Details (KVSection)
 * 3. Financial Summary (KVSection)
 * 4. Claims History (AuditTrail)
 * 5. Related Equipment (DocRows)
 * 6. Notes
 * 7. Attachments
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
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
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
} from '../sections';

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
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

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

  // ── Action gates ──
  const fileClaimAction = getAction('file_warranty_claim');
  const extendAction = getAction('extend_warranty');
  const archiveAction = getAction('archive_warranty');
  const addNoteAction = getAction('add_warranty_note');
  const uploadDocAction = getAction('add_warranty_attachment');

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

  const dropdownItems: DropdownItem[] = [];
  if (uploadDocAction !== null) {
    dropdownItems.push({
      label: 'Upload Document',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>,
      onClick: () => {},
    });
  }
  if (addNoteAction !== null) {
    dropdownItems.push({
      label: 'Add Note',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>,
      onClick: () => {},
    });
  }
  if (extendAction !== null) {
    dropdownItems.push({
      label: 'Extend Warranty',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>,
      onClick: () => executeAction('extend_warranty', {}),
    });
  }
  if (archiveAction !== null) {
    dropdownItems.push({
      label: 'Void Warranty',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>,
      onClick: () => executeAction('archive_warranty', {}),
      danger: true,
    });
  }

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
      {claimEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection
            events={claimEvents}
            title="Claim Log"
          />
        </ScrollReveal>
      )}

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

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={handleAddNote}
          canAddNote={addNoteAction !== null}
        />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile={uploadDocAction !== null}
        />
      </ScrollReveal>
    </>
  );
}
