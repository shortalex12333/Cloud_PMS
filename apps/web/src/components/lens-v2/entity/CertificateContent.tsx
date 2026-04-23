'use client';

/**
 * CertificateContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-certificate.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Holder Certs → Coverage → Equipment → Renewal History → History → Audit Trail → Related Certs → Notes → Attachments
 *
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
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';

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
  const { entity, entityId, availableActions, executeAction, getAction, isLoading, refetch } = useEntityLensContext();
  const { user } = useAuth();

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

  // Responsible officer — stored in properties.assigned_to / assigned_to_name
  // by the assign_certificate action. Read-only on the lens; writes happen
  // through ActionPopup('assign_certificate').
  const certProperties = (entity?.properties ?? payload.properties ?? {}) as Record<string, unknown>;
  const assigned_to = certProperties.assigned_to as string | undefined;
  const assigned_to_name = certProperties.assigned_to_name as string | undefined;

  // Coverage / scope fields (prototype "Coverage Details" section)
  const scope = (entity?.scope ?? payload.scope) as string | undefined;
  const capacity = (entity?.capacity ?? payload.capacity) as string | undefined;
  const flag_state = (entity?.flag_state ?? payload.flag_state) as string | undefined;
  const trading_area = (entity?.trading_area ?? payload.trading_area) as string | undefined;
  const endorsement = (entity?.endorsement ?? payload.endorsement) as string | undefined;
  const conditions = (entity?.conditions ?? payload.conditions) as string | undefined;
  const survey_window_start = (entity?.survey_window_start ?? payload.survey_window_start) as string | undefined;
  const survey_window_end = (entity?.survey_window_end ?? payload.survey_window_end) as string | undefined;

  // Primary cert document (linked via document_id FK on cert row)
  const document_id = (entity?.document_id ?? payload.document_id) as string | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const renewal_history = ((entity?.renewal_history ?? payload.renewal_history ?? entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_equipment = ((entity?.related_equipment ?? payload.related_equipment ?? entity?.equipment ?? payload.equipment) as Array<Record<string, unknown>> | undefined) ?? [];
  const related_certificates = ((entity?.related_certificates ?? payload.related_certificates) as Array<Record<string, unknown>> | undefined) ?? [];
  const holder_certificates = ((entity?.holder_certificates ?? payload.holder_certificates) as Array<Record<string, unknown>> | undefined) ?? [];
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];

  // Resolve primary certificate document for inline viewer
  const certDocAttachment = document_id
    ? attachments.find((a) => (a.id as string) === document_id) ?? null
    : null;
  const certDocUrl = (certDocAttachment?.url ?? certDocAttachment?.signed_url) as string | undefined;
  const certDocName = (certDocAttachment?.filename ?? certDocAttachment?.name ?? certDocAttachment?.file_name) as string | undefined;
  const certDocMime = (certDocAttachment?.mime_type ?? certDocAttachment?.content_type) as string | undefined;
  const certDocIsPdf = certDocMime ? certDocMime.includes('pdf') : (certDocName ? certDocName.toLowerCase().endsWith('.pdf') : false);

  // ── Action gates ──
  const renewAction = getAction('renew_certificate');
  const suspendAction = getAction('suspend_certificate');
  const archiveAction = getAction('archive_certificate');
  const addNoteAction = getAction('add_certificate_note');
  const uploadDocAction = getAction('link_document_to_certificate');

  // BACKEND_AUTO moved to mapActionFields.ts
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; subtitle?: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean; confirmation_message?: string | null }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, subtitle: action.confirmation_message || undefined, fields, signatureLevel: sigLevel });
  }

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
  if (assigned_to) {
    details.push({
      label: 'Responsible Officer',
      value: assigned_to_name || assigned_to,
    });
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

  const handlePrimary = React.useCallback(() => {
    if (!renewAction) return;
    // "Upload Renewed": open attachment modal first (upload the new cert document),
    // then open the renew dates popup. Fallback to direct popup if user not loaded.
    if (user?.yachtId && user?.id) {
      setPendingRenew(true);
      setUploadOpen(true);
    } else {
      openActionPopup(renewAction as any);
    }
  }, [renewAction, user?.yachtId, user?.id]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['suspend_certificate', 'archive_certificate', 'revoke_certificate']);
  const primaryActionId = 'renew_certificate';

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .filter((a) => !['create_vessel_certificate', 'create_crew_certificate', 'assign_certificate', 'supersede_certificate'].includes(a.action_id))
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

  // History periods — prior superseded certs in the renewal chain (backend: entity_routes.py prior_periods query)
  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.certificate_number ?? p.description) as string ?? 'Prior Certificate',
    status: 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  // Audit trail events
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
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

  // Holder's Certificates (DocRows — other certs for the same holder)
  const holderCertItems: DocRowItem[] = holder_certificates.map((hc, i) => ({
    id: (hc.id as string) ?? `hcert-${i}`,
    name: (hc.name ?? hc.title) as string ?? 'Certificate',
    code: (hc.certificate_number ?? hc.code) as string | undefined,
    meta: (hc.meta ?? hc.status) as string | undefined,
    date: (hc.expiry_date ?? hc.date) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
    onClick: (hc.certificate_id ?? hc.id)
      ? () => router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], (hc.certificate_id ?? hc.id) as string))
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
    url: (a.url ?? a.signed_url) as string | undefined,
  }));

  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);
  // When true: upload modal was opened from "Upload Renewed" — after close, open renew dates popup
  const [pendingRenew, setPendingRenew] = React.useState(false);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_certificate_note', { note_text: noteText });
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

      {/* Holder's Certificates */}
      {holderCertItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title={holder_name ? `${holder_name} \u2014 All Documents` : "Holder's Certificates"}
            docs={holderCertItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 00-3-3.87" /><path d="M16 3.13a4 4 0 010 7.75" /></svg>
            }
          />
        </ScrollReveal>
      )}

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
      <ScrollReveal>
        <AuditTrailSection
          events={renewalEvents}
          title="Renewal History"
        />
      </ScrollReveal>

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal><AuditTrailSection events={auditEvents} defaultCollapsed /></ScrollReveal>

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
          onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* Certificate Document Viewer */}
      {certDocUrl && (
        <ScrollReveal>
          <div className={styles.section}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 12 }}>
              <span className={styles.secTitle}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ width: 16, height: 16, display: 'inline-block', marginRight: 8, verticalAlign: 'middle', color: 'var(--txt3)' }}>
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                Certificate Document
              </span>
              <a
                href={certDocUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: 13, fontWeight: 500, color: 'var(--mark)', textDecoration: 'none', padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border-sub)', background: 'var(--surface-el)', transition: 'background 60ms' }}
              >
                Open in new tab ↗
              </a>
            </div>
            {certDocIsPdf ? (
              <iframe
                src={certDocUrl}
                title={certDocName ?? 'Certificate Document'}
                style={{ width: '100%', height: 640, border: 'none', borderRadius: 8, background: 'var(--surface-el)' }}
              />
            ) : (
              <div style={{ padding: '20px 16px', background: 'var(--surface-el)', borderRadius: 8, border: '1px solid var(--border-sub)', display: 'flex', alignItems: 'center', gap: 12 }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ width: 20, height: 20, color: 'var(--txt3)', flexShrink: 0 }}>
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <a href={certDocUrl} download={certDocName} style={{ color: 'var(--mark)', fontSize: 14, textDecoration: 'none', wordBreak: 'break-all' }}>
                  {certDocName ?? 'Download Document'}
                </a>
              </div>
            )}
          </div>
        </ScrollReveal>
      )}

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={user?.yachtId ? () => setUploadOpen(true) : undefined}
          canAddFile={!!uploadDocAction}
        />
      </ScrollReveal>

      {actionPopupConfig && (
        <ActionPopup mode="mutate" title={actionPopupConfig.title} subtitle={actionPopupConfig.subtitle}
          fields={actionPopupConfig.fields} signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => { await executeAction(actionPopupConfig.actionId, values); setActionPopupConfig(null); }}
          onClose={() => setActionPopupConfig(null)} />
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
          onClose={() => {
            setUploadOpen(false);
            // If opened from "Upload Renewed", proceed to renew dates popup even if upload was skipped
            if (pendingRenew) {
              setPendingRenew(false);
              if (renewAction) openActionPopup(renewAction as any);
            }
          }}
          entityType="certificate"
          entityId={entityId}
          bucket="pms-certificate-documents"
          category="certificate"
          yachtId={user.yachtId}
          userId={user.id}
          onComplete={() => {
            setUploadOpen(false);
            refetch();
            if (pendingRenew) {
              setPendingRenew(false);
              if (renewAction) openActionPopup(renewAction as any);
            }
          }}
        />
      )}
    </>
  );
}
