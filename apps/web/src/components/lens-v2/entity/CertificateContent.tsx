'use client';

/**
 * CertificateContent — lens-v2 entity view.
 *
 * Redesign — 2026-04-23 (PR: feat/cert-lens-redesign).
 * Spec: /Users/celeste7/Desktop/celeste-screenshots/doc_cert_ux_change.md
 * Philosophy: The *document itself* is the primary focus. Metadata is
 * subsidiary (identity strip). Everything else is collapsible history +
 * audit + linkage.
 *
 * Section order (top → bottom):
 *   SupersededBanner  — only when status=superseded and superseded_by is set
 *   IdentityStrip     — overline + title + pills + details + split button
 *   LensFileViewer    — PDF / image hero (the reason users opened this card)
 *   RenewalHistory    — prior cert chain, each row opens its own lens
 *   Notes             — author name+role, timestamp, body
 *   SupportingDocs    — additional attachments (renamed from "Attachments")
 *   RelatedEquipment  — linked pms_equipment rows, with Visit + picker
 *   AuditTrail        — all CUD ops with actor name+role; soft-delete → linethrough
 *
 * Data contract comes from /v1/entity/certificate/{id} (apps/api/routes/entity_routes.py).
 * See CERTIFICATE_LENS_REDESIGN_2026_04_23.md for the full wire-walk.
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
import { supabase } from '@/lib/supabaseClient';

// Sections — existing
import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
} from '../sections';

// Sections — introduced for the cert+doc redesign (shared)
import {
  LensFileViewer,
  RelatedEquipmentSection,
  type RelatedEquipmentItem,
  EquipmentPickerModal,
  type EquipmentPickerItem,
  RenewalHistorySection,
  SupersededBanner,
  type RenewalHistoryPeriod,
} from '../sections';

import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';

// ─── Colour + label helpers ───────────────────────────────────────────────────

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'valid':
      return 'green';
    case 'expiring_soon':
      return 'amber';
    case 'expired':
    case 'revoked':
      return 'red';
    case 'superseded':
    case 'suspended':
      return 'neutral';
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

/** Format an ISO timestamp → compact "dd MMM yyyy · HH:mm". Safe for null. */
function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const dd = String(d.getDate()).padStart(2, '0');
  const mon = d.toLocaleString('en-GB', { month: 'short' });
  const yr = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${dd} ${mon} ${yr} · ${hh}:${mm}`;
}

/**
 * Compose `actor` (name · role) from two optional fields. Backend enriches
 * pms_audit_log and pms_notes with actor_name/actor_role so UUIDs never reach
 * the user. Empty when both are missing.
 */
function composeActor(name: string | null | undefined, role: string | null | undefined): string | undefined {
  if (name && role) return `${name} · ${formatLabel(role)}`;
  if (name) return name;
  if (role) return formatLabel(role);
  return undefined;
}

/** Actions that, when logged, represent a soft-delete and should be rendered
 * with a linethrough per doc_cert_ux_change.md:161. */
const DELETED_AUDIT_ACTIONS = new Set([
  'archive_certificate',
  'delete_certificate',
  'revoke_certificate',
  'suspend_certificate',
]);

/** Dropdown filter: actions hidden from the lens dropdown.
 *  - create_* : only reachable from the list page, not a lens action.
 *  - assign_certificate : captain-only, surfaced elsewhere.
 *  - supersede_certificate : manual "Renew" supersedes via chain; the raw
 *    supersede action is an admin escape hatch.
 *  - link_document_to_certificate : removed from MVP surface per spec
 *    ("for mvp this is too complex. the attachments section will suffice.").
 */
const HIDDEN_FROM_DROPDOWN = new Set([
  'create_vessel_certificate',
  'create_crew_certificate',
  'assign_certificate',
  'supersede_certificate',
  'link_document_to_certificate',
]);

const DANGER_ACTIONS = new Set([
  'suspend_certificate',
  'archive_certificate',
  'revoke_certificate',
]);

// ─── Component ───────────────────────────────────────────────────────────────

export function CertificateContent() {
  const router = useRouter();
  const {
    entity,
    entityId,
    availableActions,
    executeAction,
    getAction,
    isLoading,
    refetch,
  } = useEntityLensContext();
  const { user } = useAuth();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const read = <T,>(...keys: string[]): T | undefined => {
    for (const k of keys) {
      const v = (entity as Record<string, unknown>)?.[k] ?? payload[k];
      if (v !== undefined && v !== null) return v as T;
    }
    return undefined;
  };

  const certificate_number = read<string>('certificate_number');
  const title = read<string>('title', 'name') ?? 'Certificate';
  const cert_type = read<string>('cert_type', 'certificate_type') ?? 'general';
  const issuing_authority = read<string>('issuing_authority');
  const issue_date = read<string>('issue_date');
  const expiry_date = read<string>('expiry_date');
  const last_survey_date = read<string>('last_survey_date');
  const next_survey_due = read<string>('next_survey_due');
  const status = read<string>('status') ?? 'valid';
  const holder_name = read<string>('holder_name', 'person_name');
  const yacht_name = read<string>('yacht_name', 'vessel_name');
  const description = read<string>('description');
  const document_id = read<string>('document_id');
  const yachtIdFromEntity = read<string>('yacht_id');

  // Responsible officer — stored in properties.assigned_to / assigned_to_name.
  const certProperties = (read<Record<string, unknown>>('properties') ?? {}) as Record<string, unknown>;
  const assigned_to = certProperties.assigned_to as string | undefined;
  const assigned_to_name = certProperties.assigned_to_name as string | undefined;

  // Section data
  const notes = (read<Array<Record<string, unknown>>>('notes') ?? []) as Array<Record<string, unknown>>;
  const attachments = (read<Array<Record<string, unknown>>>('attachments') ?? []) as Array<Record<string, unknown>>;
  const priorPeriods = (read<Array<Record<string, unknown>>>('prior_periods') ?? []) as Array<Record<string, unknown>>;
  const auditTrail = (read<Array<Record<string, unknown>>>('audit_trail') ?? []) as Array<Record<string, unknown>>;
  const relatedEquipmentRaw = (read<Array<Record<string, unknown>>>('related_equipment') ?? []) as Array<Record<string, unknown>>;
  const supersededBy = read<{ id?: string; label?: string; certificate_number?: string; status?: string }>('superseded_by');

  // ── Primary certificate document (for the hero viewer) ──
  // Backend appends document_id → attachments[]; find the matching row.
  const certDocAttachment = document_id
    ? attachments.find((a) => (a.id as string) === document_id) ?? null
    : null;
  const certDocUrl = (certDocAttachment?.url ?? certDocAttachment?.signed_url) as string | undefined;
  const certDocName = (certDocAttachment?.filename ?? certDocAttachment?.name ?? certDocAttachment?.file_name) as string | undefined;
  const certDocMime = (certDocAttachment?.mime_type ?? certDocAttachment?.content_type) as string | undefined;

  // ── Action gates ──
  const renewAction = getAction('renew_certificate');
  const addNoteAction = getAction('add_certificate_note');
  const uploadDocAction = getAction('link_document_to_certificate'); // kept as role-gate only; UI hidden
  const linkEquipmentAction = getAction('link_equipment_to_certificate');
  const unlinkEquipmentAction = getAction('unlink_equipment_from_certificate');

  // ── Popup state ──
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; subtitle?: string; fields: ActionPopupField[]; signatureLevel: 0 | 1 | 2 | 3 | 4 | 5;
  } | null>(null);
  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [pendingRenew, setPendingRenew] = React.useState(false);
  const [equipmentPickerOpen, setEquipmentPickerOpen] = React.useState(false);

  function openActionPopup(action: {
    action_id: string;
    label: string;
    required_fields: string[];
    prefill: Record<string, unknown>;
    requires_signature: boolean;
    confirmation_message?: string | null;
  }) {
    const fields = mapActionFields(action as never);
    const sigLevel = getSignatureLevel(action as never);
    setActionPopupConfig({
      actionId: action.action_id,
      title: action.label,
      subtitle: action.confirmation_message || undefined,
      fields,
      signatureLevel: sigLevel,
    });
  }

  // ── Superseded → banner renders a link to current version ──
  const isSuperseded = status === 'superseded' && !!supersededBy?.id;

  const isRenewable = renewAction !== null && !['revoked', 'superseded'].includes(status);

  // ── IdentityStrip data ──
  const pills: PillDef[] = [{ label: formatLabel(status), variant: statusToPillVariant(status) }];
  if (cert_type && cert_type !== 'general') {
    pills.push({ label: formatLabel(cert_type), variant: certTypeToPillVariant(cert_type) });
  }
  let daysUntilExpiry: number | undefined;
  if (expiry_date && !isSuperseded) {
    daysUntilExpiry = Math.floor((new Date(expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry > 0 && daysUntilExpiry <= 120) {
      pills.push({ label: `Renewal due in ${daysUntilExpiry} days`, variant: 'neutral' });
    }
  }

  const details: DetailLine[] = [];
  if (issuing_authority) details.push({ label: 'Issuing Authority', value: issuing_authority });
  if (certificate_number) details.push({ label: 'Certificate No', value: certificate_number, mono: true });
  if (issue_date) details.push({ label: 'Issue Date', value: issue_date, mono: true });
  if (expiry_date) details.push({ label: 'Expiry Date', value: expiry_date, mono: true });
  if (last_survey_date) details.push({ label: 'Last Survey', value: last_survey_date, mono: true });
  if (next_survey_due) details.push({ label: 'Next Survey Due', value: next_survey_due, mono: true });
  if (holder_name) details.push({ label: 'Holder', value: holder_name });
  if (yacht_name) details.push({ label: 'Vessel', value: yacht_name });
  if (assigned_to) {
    details.push({ label: 'Responsible Officer', value: assigned_to_name || assigned_to });
  }

  const contextParts: React.ReactNode[] = [];
  if (holder_name) contextParts.push(<>Issued to <span className={styles.crewLink} key="h">{holder_name}</span></>);
  if (yacht_name) contextParts.push(<span key="v">{yacht_name}</span>);
  const contextNode = contextParts.length > 0 ? (
    <>
      {contextParts.map((n, i) => (
        <React.Fragment key={i}>
          {i > 0 ? ' · ' : ''}
          {n}
        </React.Fragment>
      ))}
    </>
  ) : undefined;

  // ── Split button config ──
  const primaryLabel = isRenewable ? 'Upload Renewed' : 'Renew Certificate';
  const primaryDisabled = renewAction?.disabled ?? false;
  const primaryDisabledReason = renewAction?.disabled_reason;

  const handlePrimary = React.useCallback(() => {
    if (!renewAction) return;
    // Upload modal first (new cert doc), THEN renew-dates popup. Consistent with
    // prior flow; the warning copy on the upload modal is new (see below).
    if (user?.yachtId && user?.id) {
      setPendingRenew(true);
      setUploadOpen(true);
    } else {
      openActionPopup(renewAction as never);
    }
  }, [renewAction, user?.yachtId, user?.id]);

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== 'renew_certificate')
    .filter((a) => !HIDDEN_FROM_DROPDOWN.has(a.action_id))
    .map((a) => ({
      label: a.label,
      onClick: () => {
        const hasFields = actionHasFields(a as never);
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

  // Notes (with backend enrichment: author_name, author_role)
  const noteItems: NoteItem[] = notes.map((n, i) => {
    const author = composeActor(
      (n.author_name ?? n.author) as string | undefined,
      (n.author_role as string | undefined)
    );
    return {
      id: (n.id as string) ?? `note-${i}`,
      author: author ?? 'Unknown',
      timestamp: (n.created_at ?? n.timestamp) as string ?? '',
      body: (n.body ?? n.note_text ?? n.text) as string ?? '',
    };
  });

  // Supporting Documents (renamed from Attachments).
  // We filter OUT the hero certificate document from this list — it's already
  // rendered full-width above. Secondary attachments still belong here.
  const attachmentItems: AttachmentItem[] = attachments
    .filter((a) => !document_id || (a.id as string) !== document_id)
    .map((a, i) => ({
      id: (a.id as string) ?? `att-${i}`,
      name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
      caption: (a.caption ?? a.description) as string | undefined,
      size: (a.size ?? a.file_size) as string | undefined,
      kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
      url: (a.url ?? a.signed_url) as string | undefined,
    }));

  // Related Equipment — backend resolves properties.equipment_ids → rows.
  const equipmentItems: RelatedEquipmentItem[] = relatedEquipmentRaw.map((e) => ({
    id: (e.equipment_id ?? e.id) as string,
    code: e.code as string | null,
    name: (e.name as string) ?? 'Equipment',
    manufacturer: e.manufacturer as string | null,
    description: e.description as string | null,
  }));
  const alreadyLinkedEquipmentIds = equipmentItems.map((e) => e.id);

  // Prior-version chain → RenewalHistorySection rows.
  const renewalPeriods: RenewalHistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    label: (p.certificate_number ?? p.label) as string ?? 'Prior Certificate',
    period: (p.summary as string) ?? '',
    actor_name: (p.actor_name as string) ?? null,
    actor_role: (p.actor_role as string) ?? null,
    summary: (p.summary as string) ?? null,
    is_active: false,
  }));

  // Audit trail — actor_name / actor_role / deleted from backend.
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => {
    const action = (h.action ?? h.event ?? '') as string;
    const actor = composeActor(
      (h.actor_name ?? h.actor ?? h.performed_by) as string | undefined,
      h.actor_role as string | undefined
    );
    return {
      id: (h.id as string) ?? `audit-${i}`,
      action: formatLabel(action),
      actor,
      actor_role: (h.actor_role as string) ?? undefined,
      timestamp: formatWhen((h.created_at ?? h.timestamp) as string | undefined),
      deleted: (h.deleted as boolean) ?? DELETED_AUDIT_ACTIONS.has(action),
    } as AuditEvent;
  });

  // ── Handlers ──

  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_certificate_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  const handleVisitEquipment = React.useCallback(
    (equipmentId: string) => {
      router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipmentId));
    },
    [router]
  );

  const handleUnlinkEquipment = React.useCallback(
    async (equipmentId: string) => {
      await executeAction('unlink_equipment_from_certificate', { equipment_id: equipmentId });
      refetch();
    },
    [executeAction, refetch]
  );

  const handleLinkEquipmentSubmit = React.useCallback(
    async (equipmentId: string) => {
      await executeAction('link_equipment_to_certificate', { equipment_id: equipmentId });
      setEquipmentPickerOpen(false);
      refetch();
    },
    [executeAction, refetch]
  );

  /**
   * Loader for EquipmentPickerModal. Queries TENANT pms_equipment via Supabase
   * RLS — matches fetchEquipment() in features/equipment/api.ts but selects
   * `code` (needed for the "@ CODE — NAME" row layout) and filters soft-deletes.
   */
  const loadEquipment = React.useCallback(async (): Promise<EquipmentPickerItem[]> => {
    const targetYacht = user?.yachtId ?? yachtIdFromEntity;
    let query = supabase
      .from('pms_equipment')
      .select('id, code, name, manufacturer, description')
      .is('deleted_at', null)
      .order('name', { ascending: true })
      .limit(2000);
    if (targetYacht) query = query.eq('yacht_id', targetYacht);
    const { data, error } = await query;
    if (error) throw new Error(error.message);
    return (data ?? []) as EquipmentPickerItem[];
  }, [user?.yachtId, yachtIdFromEntity]);

  // ── Navigation ──
  const handleGoToSuperseding = React.useCallback(() => {
    if (supersededBy?.id) {
      router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], supersededBy.id));
    }
  }, [router, supersededBy?.id]);

  // ── Render ──
  return (
    <>
      {/* Old-version banner — spec doc_cert_ux_change.md:158 */}
      {isSuperseded && supersededBy && (
        <SupersededBanner
          entityLabel="certificate"
          currentRef={supersededBy.certificate_number}
          onViewCurrent={handleGoToSuperseding}
        />
      )}

      {/* Identity Strip (metadata + primary action) */}
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

      {/* HERO — the certificate itself */}
      <ScrollReveal>
        <div style={{ marginTop: 24 }}>
          <LensFileViewer
            url={certDocUrl ?? null}
            filename={certDocName}
            mimeType={certDocMime}
            onOpenNewTab={certDocUrl ? () => window.open(certDocUrl, '_blank', 'noopener,noreferrer') : undefined}
          />
        </div>
      </ScrollReveal>

      {/* Renewal History (prior superseded versions) */}
      <ScrollReveal>
        <RenewalHistorySection
          periods={renewalPeriods}
          onNavigate={(periodId) =>
            router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], periodId))
          }
        />
      </ScrollReveal>

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* Supporting Documents (additional attachments; cert hero is above) */}
      <ScrollReveal>
        <AttachmentsSection
          title="Supporting Documents"
          attachments={attachmentItems}
          onAddFile={user?.yachtId && uploadDocAction ? () => setUploadOpen(true) : undefined}
          canAddFile={!!uploadDocAction}
        />
      </ScrollReveal>

      {/* Related Equipment */}
      <ScrollReveal>
        <RelatedEquipmentSection
          items={equipmentItems}
          onOpenPicker={linkEquipmentAction ? () => setEquipmentPickerOpen(true) : undefined}
          canLink={!!linkEquipmentAction}
          onVisitEquipment={handleVisitEquipment}
          onUnlink={unlinkEquipmentAction ? handleUnlinkEquipment : undefined}
        />
      </ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* ── Modals ── */}

      {actionPopupConfig && (
        <ActionPopup
          mode="mutate"
          title={actionPopupConfig.title}
          subtitle={actionPopupConfig.subtitle}
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
          onClose={() => {
            setUploadOpen(false);
            if (pendingRenew) {
              setPendingRenew(false);
              if (renewAction) openActionPopup(renewAction as never);
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
              if (renewAction) openActionPopup(renewAction as never);
            }
          }}
          title={pendingRenew ? 'Upload Renewed Certificate' : 'Upload Supporting Document'}
          // Warning description per spec doc_cert_ux_change.md:159 — prevent users
          // confusing "supporting document upload" with "update the certificate".
          description={
            pendingRenew
              ? 'Upload the new certificate document. Dates are captured in the next step.'
              : 'Adds a supporting document to this certificate. This does NOT overwrite the certificate. To amend the certificate itself, use "Update Certificate".'
          }
        />
      )}

      <EquipmentPickerModal
        open={equipmentPickerOpen}
        onClose={() => setEquipmentPickerOpen(false)}
        loadEquipment={loadEquipment}
        alreadyLinkedIds={alreadyLinkedEquipmentIds}
        onSelect={handleLinkEquipmentSubmit}
      />
    </>
  );
}
