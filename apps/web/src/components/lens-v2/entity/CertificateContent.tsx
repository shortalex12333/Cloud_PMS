'use client';

/**
 * CertificateContent — lens-v2 Certificate entity view.
 * Matches lens-certificate.html prototype.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines
 * 2. Certificate Details (KVSection — coverage/scope)
 * 3. Related Equipment (DocRows — for machinery certs)
 * 4. Renewal History (AuditTrail)
 * 5. Related Certificates (DocRows with teal cert-link)
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
    case 'valid':
      return 'green';
    case 'expiring_soon':
      return 'amber';
    case 'expired':
    case 'revoked':
      return 'red';
    default:
      return 'neutral';
  }
}

function certTypeToPillVariant(certType: string): PillDef['variant'] {
  switch (certType) {
    case 'machinery':
      return 'amber';
    case 'vessel':
      return 'blue';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function CertificateContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const certificate_number = (entity?.certificate_number ?? payload.certificate_number) as string | undefined;
  const title = ((entity?.title ?? entity?.name ?? payload.title ?? payload.name) as string | undefined) ?? 'Certificate';
  const cert_type = ((entity?.cert_type ?? entity?.certificate_type ?? payload.cert_type ?? payload.certificate_type) as string | undefined) ?? 'general';
  const issuing_authority = (entity?.issuing_authority ?? payload.issuing_authority) as string | undefined;
  const issue_date = (entity?.issue_date ?? payload.issue_date) as string | undefined;
  const expiry_date = (entity?.expiry_date ?? payload.expiry_date) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'valid';
  const holder_name = (entity?.holder_name ?? payload.holder_name) as string | undefined;
  const holder_role = (entity?.holder_role ?? payload.holder_role) as string | undefined;
  const vessel_name = (entity?.vessel_name ?? payload.vessel_name) as string | undefined;
  const description = (entity?.description ?? payload.description) as string | undefined;

  // Coverage / scope fields (prototype "Coverage Details" section)
  const scope = (entity?.scope ?? payload.scope) as string | undefined;
  const capacity = (entity?.capacity ?? payload.capacity) as string | undefined;
  const flag_state = (entity?.flag_state ?? payload.flag_state) as string | undefined;
  const trading_area = (entity?.trading_area ?? payload.trading_area) as string | undefined;
  const endorsement = (entity?.endorsement ?? payload.endorsement) as string | undefined;
  const conditions = (entity?.conditions ?? payload.conditions) as string | undefined;
  const survey_window_start = (entity?.survey_window_start ?? payload.survey_window_start) as string | undefined;
  const survey_window_end = (entity?.survey_window_end ?? payload.survey_window_end) as string | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const renewal_history = ((entity?.renewal_history ?? payload.renewal_history ?? entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_equipment = ((entity?.related_equipment ?? payload.related_equipment ?? entity?.equipment ?? payload.equipment) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_certificates = ((entity?.related_certificates ?? payload.related_certificates) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const renewAction = getAction('renew_certificate');
  const suspendAction = getAction('suspend_certificate');
  const archiveAction = getAction('archive_certificate');
  const addNoteAction = getAction('add_certificate_note');
  const uploadDocAction = getAction('link_document_to_certificate');

  const isRenewable = renewAction !== null && !['revoked'].includes(status);

  // ── Derived display ──
  const statusLabel = formatLabel(status);
  const certTypeLabel = formatLabel(cert_type);

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (cert_type && cert_type !== 'general') {
    pills.push({ label: certTypeLabel, variant: certTypeToPillVariant(cert_type) });
  }

  // Days until expiry for display
  let daysUntilExpiry: number | undefined;
  if (expiry_date) {
    daysUntilExpiry = Math.floor((new Date(expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry > 0 && daysUntilExpiry <= 120) {
      pills.push({ label: `Renewal due in ${daysUntilExpiry} days`, variant: 'neutral' });
    }
  }

  const details: DetailLine[] = [];
  if (issuing_authority) {
    details.push({ label: 'Issuing Authority', value: issuing_authority });
  }
  if (certificate_number) {
    details.push({ label: 'Certificate No', value: certificate_number, mono: true });
  }
  if (issue_date) {
    details.push({ label: 'Issue Date', value: issue_date, mono: true });
  }
  if (expiry_date) {
    details.push({ label: 'Expiry Date', value: expiry_date, mono: true });
  }
  if (survey_window_start && survey_window_end) {
    details.push({ label: 'Survey Window', value: `${survey_window_start} — ${survey_window_end}`, mono: true });
  }
  if (holder_name) {
    const holderDisplay = holder_role ? `${holder_name} · ${holder_role}` : holder_name;
    details.push({ label: 'Holder', value: holderDisplay });
  }
  if (vessel_name) {
    details.push({ label: 'Vessel', value: vessel_name });
  }

  // Context line
  const contextParts: string[] = [];
  if (holder_name) contextParts.push(`Issued to ${holder_name}`);
  if (holder_role && !holder_name) contextParts.push(holder_role);
  if (vessel_name) contextParts.push(vessel_name);
  const contextNode = contextParts.length > 0 ? (
    <>
      {holder_name && (
        <>Issued to <span className={styles.crewLink}>{holder_name}</span></>
      )}
      {holder_role && holder_name && ` · ${holder_role}`}
      {vessel_name && (
        <>
          {(holder_name || holder_role) && ' · '}
          {vessel_name}
        </>
      )}
    </>
  ) : undefined;

  // ── Split button config ──
  const primaryLabel = isRenewable ? 'Upload Renewed' : 'Renew Certificate';
  const primaryDisabled = renewAction?.disabled ?? false;
  const primaryDisabledReason = renewAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('renew_certificate', {});
  }, [executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (uploadDocAction !== null) {
    dropdownItems.push({
      label: 'Upload Document',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.49" /></svg>,
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
  if (suspendAction !== null) {
    dropdownItems.push({
      label: 'Suspend',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6M9 9l6 6" /></svg>,
      onClick: () => executeAction('suspend_certificate', {}),
      danger: true,
    });
  }
  if (archiveAction !== null) {
    dropdownItems.push({
      label: 'Archive',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>,
      onClick: () => executeAction('archive_certificate', {}),
      danger: true,
    });
  }

  // ── Map section data ──

  // Certificate details (KV)
  const certDetailItems: KVItem[] = [];
  if (scope) certDetailItems.push({ label: 'Scope', value: scope });
  if (capacity) certDetailItems.push({ label: 'Capacity', value: capacity });
  if (flag_state) certDetailItems.push({ label: 'Flag State', value: flag_state });
  if (trading_area) certDetailItems.push({ label: 'Trading Area', value: trading_area });
  if (endorsement) certDetailItems.push({ label: 'Endorsement', value: endorsement, mono: true });
  if (conditions) certDetailItems.push({ label: 'Conditions', value: conditions });

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

  // Renewal history (AuditTrail)
  const renewalEvents: AuditEvent[] = renewal_history.map((h, i) => ({
    id: (h.id as string) ?? `renewal-${i}`,
    action: (h.action ?? h.description ?? h.label ?? h.event) as string ?? '',
    actor: (h.actor ?? h.authority ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.date ?? h.timestamp) as string ?? '',
  }));

  // Related certificates (DocRows — teal cert-link)
  const relatedCertItems: DocRowItem[] = related_certificates.map((c, i) => ({
    id: (c.id as string) ?? `cert-${i}`,
    name: (c.name ?? c.title) as string ?? 'Certificate',
    code: (c.certificate_number ?? c.code) as string | undefined,
    meta: (c.meta ?? c.status) as string | undefined,
    date: (c.expiry_date ?? c.date) as string | undefined,
    onClick: c.certificate_id
      ? () => router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], c.certificate_id as string))
      : c.id
        ? () => router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], c.id as string))
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
        overline={certificate_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          renewAction ? (
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

      {/* Certificate Details / Coverage */}
      {certDetailItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Coverage Details"
            items={certDetailItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Related Equipment (for machinery certs) */}
      {equipmentItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Equipment" docs={equipmentItems} />
        </ScrollReveal>
      )}

      {/* Renewal History */}
      {renewalEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection
            events={renewalEvents}
            title="Renewal History"
          />
        </ScrollReveal>
      )}

      {/* Related Certificates */}
      {relatedCertItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Certificates" docs={relatedCertItems} />
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
