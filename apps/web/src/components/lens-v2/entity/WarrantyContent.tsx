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
 * Sections: Identity → Claim Details → Financials → Equipment → Related → Audit Trail → Notes → Attachments → Email Draft
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
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';
import { AttachmentUploadModal } from '@/components/lens-v2/actions/AttachmentUploadModal';
import { useAuth } from '@/hooks/useAuth';

// ─── Helpers ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'approved':
      return 'green';
    case 'submitted':
      return 'amber';
    case 'rejected':
    case 'closed':
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
  const { entity, availableActions, executeAction, getAction, isLoading, entityId, refetch } = useEntityLensContext();
  const { user } = useAuth();

  // ── Extract entity fields ──
  const title = ((entity?.title ?? entity?.name) as string | undefined) ?? 'Warranty Claim';
  const status = ((entity?.status) as string | undefined) ?? 'draft';
  const description = (entity?.description) as string | undefined;
  const claim_number = (entity?.claim_number) as string | undefined;
  const vendor_name = (entity?.vendor_name) as string | undefined;
  const expiry_date = (entity?.expiry_date) as string | undefined;
  const claimed_amount = (entity?.claimed_amount) as string | number | undefined;
  const approved_amount = (entity?.approved_amount) as string | number | undefined;
  const days_until_expiry = (entity?.days_until_expiry) as number | undefined;
  const status_label = (entity?.status_label as string | undefined) ?? formatLabel(status);
  const drafted_at = (entity?.drafted_at) as string | undefined;
  const rejection_reason = (entity?.rejection_reason) as string | undefined;
  const email_draft = entity?.email_draft as Record<string, string> | null | undefined;
  const metadata = (entity?.metadata as Record<string, unknown> | null | undefined) ?? {};
  const manufacturer_email = metadata?.manufacturer_email as string | undefined;
  const equipment_name = (entity?.equipment_name) as string | undefined;
  const equipment_id = (entity?.equipment_id) as string | undefined;
  const equipment_code = (entity?.equipment_code) as string | undefined;
  const claim_type = (entity?.claim_type) as string | undefined;

  // Section data (arrays guaranteed by normalizer)
  const notes = (entity?.notes as Array<Record<string, unknown>>) ?? [];
  const attachments = (entity?.attachments as Array<Record<string, unknown>>) ?? [];
  const related_entities = (entity?.related_entities as Array<Record<string, unknown>>) ?? [];
  const auditTrail = ((entity?.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action popup state ──
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  // ── Action feedback ──
  const [actionFeedback, setActionFeedback] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);

  React.useEffect(() => {
    if (!actionFeedback) return;
    const t = setTimeout(() => setActionFeedback(null), 4000);
    return () => clearTimeout(t);
  }, [actionFeedback]);

  // ── Status-aware action gates ──
  // Real DB statuses: draft | submitted | approved | rejected | closed
  const submitAction   = getAction('submit_warranty_claim');
  const approveAction  = getAction('approve_warranty_claim');
  const rejectAction   = getAction('reject_warranty_claim');
  const closeAction    = getAction('close_warranty_claim');
  const composeAction  = getAction('compose_warranty_email');
  const archiveAction  = getAction('archive_warranty');
  const addNoteAction  = getAction('add_warranty_note');

  type PrimaryConfig = { label: string; action: typeof submitAction; confirmFields?: boolean };
  const primaryConfig: PrimaryConfig | null = (() => {
    if (status === 'draft'        && submitAction)  return { label: 'Submit Claim',       action: submitAction };
    if (status === 'submitted'    && approveAction) return { label: 'Approve',            action: approveAction };
    if (status === 'approved'     && closeAction)   return { label: 'Close Claim',        action: closeAction };
    if (status === 'rejected'     && submitAction)  return { label: 'Revise & Resubmit',  action: submitAction };
    return null;
  })();

  const handlePrimary = React.useCallback(() => {
    if (!primaryConfig?.action) return;
    const a = primaryConfig.action;
    const hasFields = actionHasFields(a as any);
    if (hasFields || a.requires_signature) {
      openActionPopup(a as any);
    } else {
      executeAction(a.action_id).then((result) => {
        if (!result.success) {
          setActionFeedback({ type: 'error', message: result.message ?? (result as any).error ?? 'Action failed' });
        } else {
          setActionFeedback({ type: 'success', message: `${primaryConfig.label} — done` });
        }
      });
    }
  }, [primaryConfig, executeAction]);

  // ── Pills ──
  const pills: PillDef[] = [
    { label: status_label, variant: statusToPillVariant(status) },
  ];

  // ── Identity strip details ──
  const details: DetailLine[] = [];
  if (equipment_name) details.push({ label: 'Equipment', value: equipment_code ? `${equipment_code} ${equipment_name}` : equipment_name });
  if (vendor_name) details.push({ label: 'Supplier', value: vendor_name });
  if (expiry_date) details.push({ label: 'Warranty Expiry', value: expiry_date, mono: true });
  if (days_until_expiry !== undefined && days_until_expiry !== null) {
    details.push({ label: 'Days Remaining', value: `${days_until_expiry}`, mono: true });
  }
  if (claim_type) details.push({ label: 'Claim Type', value: formatLabel(claim_type) });
  if (drafted_at) details.push({ label: 'Filed', value: drafted_at.slice(0, 10), mono: true });

  // ── Claim Details (KVSection) ──
  const claimItems: KVItem[] = [];
  if (claim_type) claimItems.push({ label: 'Claim Type', value: formatLabel(claim_type) });
  if (vendor_name) claimItems.push({ label: 'Supplier / Vendor', value: vendor_name });
  if (entity?.manufacturer) claimItems.push({ label: 'Manufacturer', value: entity.manufacturer as string });
  if (manufacturer_email) claimItems.push({ label: 'Manufacturer Email', value: manufacturer_email });
  if (entity?.serial_number) claimItems.push({ label: 'Serial Number', value: entity.serial_number as string, mono: true });
  if (entity?.part_number) claimItems.push({ label: 'Part Number', value: entity.part_number as string, mono: true });
  if (entity?.purchase_date) claimItems.push({ label: 'Purchase Date', value: entity.purchase_date as string, mono: true });
  if (rejection_reason) claimItems.push({ label: 'Rejection Reason', value: rejection_reason });

  // ── Financial Summary (KVSection) ──
  const financialItems: KVItem[] = [];
  if (claimed_amount !== undefined) financialItems.push({ label: 'Claimed Amount', value: `${entity?.currency ?? ''} ${claimed_amount}`.trim(), mono: true });
  if (approved_amount !== undefined) financialItems.push({ label: 'Approved Amount', value: `${entity?.currency ?? ''} ${approved_amount}`.trim(), mono: true });

  // ── Split button dropdown ──
  const dropdownItems: DropdownItem[] = [
    ...(rejectAction && status === 'submitted' ? [{
      label: 'Reject Claim',
      onClick: () => openActionPopup(rejectAction as any),
      danger: true,
      disabled: false,
    }] : []),
    ...(composeAction && status !== 'draft' ? [{
      label: 'Compose Email Draft',
      onClick: () => {
        const hasF = actionHasFields(composeAction as any);
        if (hasF) openActionPopup(composeAction as any);
        else executeAction('compose_warranty_email');
      },
      disabled: composeAction.disabled,
    }] : []),
    ...(addNoteAction ? [{
      label: 'Add Note',
      onClick: () => setAddNoteOpen(true),
      disabled: false,
    }] : []),
    ...(archiveAction && (status === 'draft' || status === 'rejected') ? [{
      label: 'Archive',
      onClick: () => executeAction('archive_warranty'),
      danger: true,
      disabled: archiveAction.disabled,
    }] : []),
  ];

  // ── Audit trail ──
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by ?? h.user_id) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // ── Related equipment row (from single reference) ──
  const equipmentItems: DocRowItem[] = [];
  if (equipment_id && equipment_name) {
    equipmentItems.push({
      id: equipment_id,
      name: equipment_name,
      code: equipment_code,
      onClick: () => router.push(getEntityRoute('equipment' as Parameters<typeof getEntityRoute>[0], equipment_id)),
    });
  }

  // ── Related entities ──
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

  // ── Notes ──
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.created_by_role ?? n.author ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // ── Attachments ──
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
    url: (a.url) as string | undefined,
  }));

  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_warranty_note', { note_text: noteText });
      const isSuccess = result.success === true ||
        (result as unknown as { status?: string }).status === 'success';
      return { success: isSuccess, error: result.error ?? result.message };
    },
    [executeAction]
  );

  return (
    <>
      {/* Action feedback banner */}
      {actionFeedback && (
        <div style={{
          padding: '10px 16px',
          marginBottom: '8px',
          borderRadius: '6px',
          fontSize: '13px',
          background: actionFeedback.type === 'success' ? 'var(--teal-bg)' : 'var(--status-critical-bg)',
          color: actionFeedback.type === 'success' ? 'var(--mark)' : 'var(--status-critical)',
          border: `1px solid ${actionFeedback.type === 'success' ? 'var(--mark)' : 'var(--status-critical)'}`,
        }}>
          {actionFeedback.message}
        </div>
      )}

      {/* Identity Strip */}
      <IdentityStrip
        overline={claim_number}
        title={title}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          primaryConfig ? (
            <SplitButton
              label={primaryConfig.label}
              onClick={handlePrimary}
              disabled={primaryConfig.action?.disabled ?? false}
              disabledReason={primaryConfig.action?.disabled_reason ?? undefined}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label="Actions"
              onClick={() => {}}
              disabled={false}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Claim Details */}
      {claimItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Claim Details"
            items={claimItems}
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

      {/* Audit Trail */}
      <ScrollReveal><AuditTrailSection events={auditEvents} defaultCollapsed /></ScrollReveal>

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
          onAddFile={() => setUploadModalOpen(true)}
          canAddFile
        />
      </ScrollReveal>

      {/* Email Draft */}
      {email_draft && (
        <ScrollReveal>
          <KVSection
            title="Email Draft"
            items={[
              { label: 'Subject', value: email_draft.subject ?? '' },
              { label: 'To', value: email_draft.to ?? '' },
              { label: 'Composed', value: email_draft.composed_at ? email_draft.composed_at.slice(0, 10) : '' },
            ]}
            icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>}
          />
        </ScrollReveal>
      )}

      <AttachmentUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        entityType="warranty"
        entityId={entityId}
        bucket="pms-warranty-documents"
        category="claim_document"
        yachtId={(entity?.yacht_id as string) ?? user?.yachtId ?? ''}
        userId={user?.id ?? ''}
        onComplete={() => { refetch(); }}
      />

      {actionPopupConfig && (
        <ActionPopup mode="mutate" title={actionPopupConfig.title} fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => {
            const result = await executeAction(actionPopupConfig.actionId, values);
            setActionPopupConfig(null);
            if (!result.success) {
              setActionFeedback({ type: 'error', message: result.message ?? (result as any).error ?? 'Action failed' });
            } else {
              setActionFeedback({ type: 'success', message: `${actionPopupConfig.title} — completed` });
            }
          }}
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
