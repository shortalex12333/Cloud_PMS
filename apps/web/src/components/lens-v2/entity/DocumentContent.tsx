'use client';

/**
 * DocumentContent — lens-v2 entity view (v3 redesign).
 *
 * Per doc_cert_ux_change.md (2026-04-23), the file being rendered is the
 * primary focus of the lens. Metadata is subsidiary. The section order and
 * section list is:
 *
 *   Identity strip (overline + title + pills + action slot)
 *   ───────────────────────────────────────────────────────
 *   LensFileViewer hero (PDF / image / fallback)            ← primary focus
 *   ───────────────────────────────────────────────────────
 *   Renewal History      ─ collapsible (prior superseded versions)
 *   Notes                ─ collapsible
 *   Supporting Documents ─ collapsible (renamed from "Attachments")
 *   Related Equipment    ─ collapsible (NEW: picker + Visit button)
 *   Audit Trail          ─ collapsible (CUD events; soft-delete linethrough)
 *
 * Data flow:
 *   - Entity data (resolved names/roles, related_equipment[], audit_trail[])
 *     comes pre-hydrated from GET /v1/entity/document/{id} — the frontend
 *     never sees raw UUIDs for users or vessel names.
 *   - Signed URL for the viewer is fetched by loadDocumentWithBackend(); we
 *     intentionally keep the two fetches separate so the lens can render
 *     metadata + related equipment before the (potentially large) PDF blob
 *     arrives.
 *   - Mutations (link equipment, unlink equipment, note, upload) go through
 *     executeAction() → /v1/actions/execute.
 *
 * Width: the lens panel expands to `--lens-max-width-wide` (~1120px) for
 * entity types listed in `WIDE_LENS_TYPES` on `EntityLensPage.tsx`. The
 * 'document' type is already in that set alongside 'certificate'; no
 * per-render signal is needed from this component.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { loadDocumentWithBackend } from '@/lib/documentLoader';
import { getEntityRoute } from '@/lib/entityRoutes';
import { supabase } from '@/lib/supabaseClient';

import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  KVSection,
  LensFileViewer,
  RelatedEquipmentSection,
  EquipmentPickerModal,
  RenewalHistorySection,
  SupersededBanner,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type KVItem,
  type RelatedEquipmentItem,
  type EquipmentPickerItem,
  type RenewalHistoryPeriod,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';

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
  const { entity, entityId, availableActions, executeAction, getAction, isLoading, refetch } = useEntityLensContext();
  const { user } = useAuth();

  // ── PDF / file loading ──
  const [blobUrl, setBlobUrl] = React.useState<string | null>(null);
  const [fileLoading, setFileLoading] = React.useState(false);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const blobUrlRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    if (!entityId) return;
    setFileLoading(true);
    setFileError(null);
    setBlobUrl(null);
    loadDocumentWithBackend(entityId).then((result) => {
      if (result.success && result.url) {
        blobUrlRef.current = result.url;
        setBlobUrl(result.url);
      } else {
        setFileError(result.error ?? 'Failed to load document');
      }
      setFileLoading(false);
    });
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [entityId]);

  // ── Extract entity fields ──
  // Memoised so downstream callbacks that depend on payload don't rebuild on
  // every render (eslint react-hooks/exhaustive-deps requires this).
  const payload = React.useMemo(
    () => (entity?.payload as Record<string, unknown>) ?? {},
    [entity?.payload]
  );
  const document_code = (entity?.document_code ?? payload.document_code) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Document';
  const document_type = (entity?.document_type ?? payload.document_type) as string | undefined;
  const doc_type = (entity?.doc_type ?? payload.doc_type) as string | undefined;
  const system_type = (entity?.system_type ?? payload.system_type) as string | undefined;
  const oem = (entity?.oem ?? payload.oem) as string | undefined;
  const model = (entity?.model ?? payload.model) as string | undefined;
  const category = (entity?.category ?? payload.category) as string | undefined;
  const revision = (entity?.revision ?? payload.revision) as string | number | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const author = (entity?.author ?? payload.author) as string | undefined;
  const effective_date = (entity?.effective_date ?? payload.effective_date) as string | undefined;
  const file_name = (entity?.file_name ?? entity?.filename ?? payload.file_name ?? payload.filename) as string | undefined;
  const file_size = ((entity?.size_bytes ?? entity?.file_size ?? payload.file_size) as number | undefined);
  const mime_type = ((entity?.mime_type ?? payload.mime_type) as string | undefined) ?? 'application/octet-stream';
  const file_url = (entity?.url ?? entity?.file_url ?? payload.file_url ?? payload.url) as string | undefined;
  const description = (entity?.description ?? payload.description) as string | undefined;
  const supersedes = (entity?.supersedes ?? payload.supersedes) as string | undefined;
  const superseded_by = (entity?.superseded_by ?? payload.superseded_by) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const page_count = (entity?.page_count ?? payload.page_count) as number | undefined;

  // ── Resolved display labels from backend (/v1/entity/document/{id}) ──
  // All UUIDs resolved to name+role; the frontend never renders a raw UUID.
  const yacht_name = (entity?.yacht_name ?? payload.yacht_name) as string | undefined;
  const uploaded_by_name = (entity?.uploaded_by_name ?? payload.uploaded_by_name) as string | undefined;
  const uploaded_by_role = (entity?.uploaded_by_role ?? payload.uploaded_by_role) as string | undefined;

  // Related equipment — comes pre-hydrated from backend with full row shape
  const related_equipment = ((entity?.related_equipment ?? payload.related_equipment) as RelatedEquipmentItem[] | undefined) ?? [];
  const equipment_ids = ((entity?.equipment_ids ?? payload.equipment_ids) as string[] | undefined) ?? [];

  // Section data
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];

  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((entity?.audit_trail ?? payload.audit_trail ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const archiveAction = getAction('archive_document');
  const addNoteAction = getAction('add_document_note');
  const linkEquipmentAction = getAction('link_equipment_to_document');
  const unlinkEquipmentAction = getAction('unlink_equipment_from_document');
  const canLinkEquipment = !!linkEquipmentAction && !linkEquipmentAction.disabled;
  const uploadDocAction = getAction('upload_document');

  // ── Supporting-document upload modal state ──
  const [uploadOpen, setUploadOpen] = React.useState(false);

  // ── Equipment picker state ──
  const [pickerOpen, setPickerOpen] = React.useState(false);

  const loadEquipmentCandidates = React.useCallback(async (): Promise<EquipmentPickerItem[]> => {
    // Fetch all non-deleted equipment for the current yacht via Supabase anon
    // (RLS-filtered to the caller's yacht). Alphabetical ordering is applied
    // inside the picker modal; we just fetch the list here.
    const yachtId = (entity?.yacht_id ?? payload.yacht_id) as string | undefined;
    if (!yachtId) return [];
    const { data, error } = await supabase
      .from('pms_equipment')
      .select('id, code, name, manufacturer, description')
      .eq('yacht_id', yachtId)
      .is('deleted_at', null)
      .limit(2000);
    if (error) throw new Error(error.message);
    return (data ?? []) as EquipmentPickerItem[];
  }, [entity, payload]);

  const handleLinkEquipment = React.useCallback(
    async (equipmentId: string) => {
      await executeAction('link_equipment_to_document', {
        equipment_id: equipmentId,
      });
    },
    [executeAction]
  );

  const handleUnlinkEquipment = React.useCallback(
    async (equipmentId: string) => {
      if (!canLinkEquipment) return;
      const ok = typeof window !== 'undefined'
        ? window.confirm('Unlink this equipment from the document?')
        : true;
      if (!ok) return;
      await executeAction('unlink_equipment_from_document', {
        equipment_id: equipmentId,
      });
    },
    [executeAction, canLinkEquipment]
  );

  const handleVisitEquipment = React.useCallback(
    (equipmentId: string) => {
      router.push(
        getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipmentId)
      );
    },
    [router]
  );

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
  if (uploaded_by_name) {
    // Per spec: always show NAME + ROLE where applicable, never UUID
    const roleSuffix = uploaded_by_role ? ` · ${uploaded_by_role.replace(/_/g, ' ')}` : '';
    details.push({ label: 'Uploaded by', value: `${uploaded_by_name}${roleSuffix}` });
  } else if (author) {
    details.push({ label: 'Author', value: author });
  }
  if (oem) details.push({ label: 'OEM', value: oem });
  if (model) details.push({ label: 'Model', value: model, mono: true });
  if (supersedes) {
    details.push({ label: 'Supersedes', value: supersedes });
  }

  // Context line (overline-like text under title)
  const contextParts: string[] = [];
  const primaryType = (doc_type ?? document_type ?? category) as string | undefined;
  if (primaryType) contextParts.push(primaryType);
  if (system_type) contextParts.push(system_type);
  if (department) contextParts.push(department);
  if (yacht_name) contextParts.push(yacht_name);
  const contextNode = contextParts.length > 0 ? (
    <>{contextParts.join(' · ')}</>
  ) : undefined;

  // ── Split button config ──
  const handlePrimary = React.useCallback(async () => {
    const downloadUrl = blobUrl ?? file_url;
    if (downloadUrl) {
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = file_name ?? 'document';
      a.click();
    }
  }, [blobUrl, file_url, file_name]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_document', 'delete_document']);

  // ── Hidden-in-dropdown list ──
  // Per doc_cert_ux_change.md: the old "Link document to certificate" search
  // modal is removed for MVP — supporting documents / attachments cover the
  // need. Related equipment has its own dedicated section + picker, so we
  // also hide the backend link action from the generic action dropdown
  // (users open the picker via the section's "+ Link equipment" button).
  const HIDDEN_FROM_DROPDOWN = new Set([
    'link_document_to_certificate',
    'link_equipment_to_document',
    'unlink_equipment_from_document',
  ]);

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => !HIDDEN_FROM_DROPDOWN.has(a.action_id))
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

  // Notes: actor + role resolved upstream where possible
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author:
      ((n.author_name ?? n.author ?? n.created_by_name ?? n.user_name) as string | undefined) ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // Supporting documents (renamed from "attachments" per spec): no type change in storage
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  // Renewal history: prior version rows. Generic shape — maps flexibly from
  // either a dedicated revision_history field (legacy) or prior_periods.
  const renewalPeriods: RenewalHistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    label:
      ((p.label ?? p.period_label ?? p.version_label ?? p.filename) as string | undefined) ??
      `Version ${i + 1}`,
    period:
      ((p.effective_date ?? p.issue_date ?? p.created_at ?? p.year ?? p.period_year) as string | undefined) ?? '',
    actor_name: (p.actor_name ?? p.user_name ?? p.author_name ?? p.created_by_name) as string | undefined,
    actor_role: (p.actor_role ?? p.user_role) as string | undefined,
    summary: (p.summary ?? p.period_summary ?? p.change_summary ?? p.description) as string | undefined,
    is_active: false,
  }));

  // Audit trail: already pre-resolved server-side (actor_name / actor_role /
  // deleted flag). Fall back defensively for legacy entries still coming
  // through with raw fields.
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.actor_name ?? h.user_name ?? h.performed_by) as string | undefined,
    actor_role: (h.actor_role ?? h.user_role) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
    deleted: Boolean(h.deleted),
  }));

  // ── Open file in new tab callback (shared by the viewer header button) ──
  const openInNewTab = React.useCallback(() => {
    const url = blobUrl ?? file_url;
    if (url && typeof window !== 'undefined') {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }, [blobUrl, file_url]);

  return (
    <div data-testid="document-content">
      {/* ── Optional: "This is an old version" banner when the user is viewing a
           superseded document. Resolved from the backend superseded_by field. */}
      {superseded_by && (
        <SupersededBanner
          entityLabel="document"
          onViewCurrent={() =>
            router.push(getEntityRoute('document' as Parameters<typeof getEntityRoute>[0], superseded_by))
          }
        />
      )}

      {/* ── Identity strip (metadata header — unchanged per spec) ── */}
      <IdentityStrip
        overline={document_code}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          (blobUrl ?? file_url) ? (
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
            <SplitButton label="Actions" onClick={() => { /* dropdown-only mode */ }} items={dropdownItems} />
          ) : undefined
        }
      />

      {/* ── HERO: file viewer ── */}
      <ScrollReveal>
        <div className={styles.section} style={{ padding: 'var(--space-3) 0' }}>
          <LensFileViewer
            url={blobUrl}
            filename={file_name ?? title}
            mimeType={mime_type}
            isLoading={fileLoading}
            error={fileError}
            onOpenNewTab={blobUrl ? openInNewTab : undefined}
          />
        </div>
      </ScrollReveal>

      {/* ── Renewal History (prior superseded versions) ── */}
      <ScrollReveal>
        <RenewalHistorySection
          periods={renewalPeriods}
          onNavigate={(periodId) =>
            router.push(getEntityRoute('document' as Parameters<typeof getEntityRoute>[0], periodId))
          }
        />
      </ScrollReveal>

      {/* ── Notes ── */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
          canAddNote={!!addNoteAction}
        />
      </ScrollReveal>

      {/* ── Supporting Documents (renamed from Attachments per spec) ──
           The upload modal carries the "DOES NOT OVERWRITE" warning copy
           per doc_cert_ux_change.md:279 — passed via AttachmentUploadModal's
           `description` prop at the render site below, mirroring CERT04's
           pattern on CertificateContent.tsx. */}
      <ScrollReveal>
        <AttachmentsSection
          title="Supporting Documents"
          attachments={attachmentItems}
          onAddFile={user?.yachtId && uploadDocAction ? () => setUploadOpen(true) : undefined}
          canAddFile={!!uploadDocAction}
        />
      </ScrollReveal>

      {/* ── Related Equipment (NEW per spec) ── */}
      <ScrollReveal>
        <RelatedEquipmentSection
          items={related_equipment}
          onOpenPicker={() => setPickerOpen(true)}
          onVisitEquipment={handleVisitEquipment}
          onUnlink={canLinkEquipment ? handleUnlinkEquipment : undefined}
          canLink={canLinkEquipment}
        />
      </ScrollReveal>

      {/* ── Audit Trail (CUD events; soft-delete linethrough) ── */}
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

      <EquipmentPickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        loadEquipment={loadEquipmentCandidates}
        alreadyLinkedIds={equipment_ids}
        onSelect={handleLinkEquipment}
      />

      {/* Supporting-document upload. Lands in pms_attachments (NOT doc_metadata)
          so it sits alongside the primary document; replacing the primary
          file goes through the "Update Document" action instead. The
          description prop carries the spec-required warning copy so the
          user can't confuse the two paths. */}
      {user?.yachtId && user?.id && (
        <AttachmentUploadModal
          open={uploadOpen}
          onClose={() => setUploadOpen(false)}
          entityType="document"
          entityId={entityId}
          bucket="documents"
          category="document"
          yachtId={user.yachtId}
          userId={user.id}
          onComplete={() => {
            setUploadOpen(false);
            refetch();
          }}
          title="Upload Supporting Document"
          description="Adds a supporting document attached to this document record. This does NOT overwrite the document itself. To replace the document's file or metadata, use the Update Document action."
        />
      )}
    </div>
  );
}
