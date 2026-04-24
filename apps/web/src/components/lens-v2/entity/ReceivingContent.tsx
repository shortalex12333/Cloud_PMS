'use client';

/**
 * ReceivingContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-receiving.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Packing List → Print → Related → Notes → Attachments → History → Audit Trail
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
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { ReceivingPackingList, type PackingItem } from '../sections/ReceivingPackingList';

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

// --- Colour mapping helpers ---

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'discrepancy':
      return 'red';
    case 'in_progress':
      return 'amber';
    case 'completed':
      return 'green';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// --- Component ---

export function ReceivingContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // -- Extract entity fields --
  // Identity rules — every value appears AT MOST once across the strip:
  //   title    = vendor_name (or "Draft Receiving")
  //   pills    = [status, item count, optional total/currency money line]
  //   details  = vendor_reference, received_date, received_by NAME, vessel
  //   context  = clickable PO link (no supplier echo)
  // entity_routes.py:get_receiving_entity already resolves received_by UUID -> name.
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const po_number = (entity?.po_number ?? payload.po_number) as string | undefined;
  const po_id = (entity?.po_id ?? payload.po_id) as string | undefined;
  const vendor_name = (entity?.vendor_name ?? payload.vendor_name ?? entity?.supplier ?? payload.supplier) as string | undefined;
  const vendor_reference = (entity?.vendor_reference ?? payload.vendor_reference ?? entity?.supplier_ref ?? payload.supplier_ref) as string | undefined;
  const received_date = (entity?.received_date ?? payload.received_date) as string | undefined;
  const received_by = (entity?.received_by ?? payload.received_by) as string | undefined;
  const yacht_name = (entity?.yacht_name ?? payload.yacht_name ?? entity?.vessel ?? payload.vessel) as string | undefined;
  const total = (entity?.total ?? payload.total) as number | undefined;
  const currency = (entity?.currency ?? payload.currency) as string | undefined;
  const total_items = (entity?.total_items ?? payload.total_items) as number | undefined;
  const title = vendor_name ?? 'Draft Receiving';

  // Section data
  const items = ((entity?.items ?? payload.items) as Array<Record<string, unknown>> | undefined) ?? [];
  // pms_receiving.notes is a single text column. Wrap into a single note row so
  // the NotesSection can render it without crashing on `.map`. If a future
  // backend hands us an array (e.g. joined pms_notes rows), we use it directly.
  const rawNotes = entity?.notes ?? payload.notes;
  const notes: Array<Record<string, unknown>> = Array.isArray(rawNotes)
    ? (rawNotes as Array<Record<string, unknown>>)
    : (typeof rawNotes === 'string' && rawNotes.trim().length > 0
        ? [{ id: 'receiving-note', body: rawNotes, author: 'Receiving record', timestamp: (entity?.created_at ?? payload.created_at) as string ?? '' }]
        : []);
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const linked_entities = ((entity?.linked_entities ?? payload.linked_entities ?? entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];

  // -- Action gates --
  // Primary CTA = SIGNED accept_receiving (every status->accepted must be
  // cryptographically attested). confirm_receiving was the unsigned alias —
  // hidden via entity_actions.py:_RECEIVING_HIDDEN_ACTIONS.
  const acceptAction = getAction('accept_receiving');
  const flagAction = getAction('flag_discrepancy');

  // pms_receiving.status enum = draft|in_review|accepted|rejected
  const isAcceptable = ['draft', 'in_review'].includes(status);

  // BACKEND_AUTO moved to mapActionFields.ts
  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = getSignatureLevel(action as any);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel });
  }

  // -- Derived display --
  const statusLabel = formatLabel(status);
  const itemCount = total_items ?? items.length;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (itemCount > 0) {
    pills.push({ label: `${itemCount} Item${itemCount === 1 ? '' : 's'}`, variant: 'neutral' });
  }
  if (typeof total === 'number' && total > 0) {
    const money = currency ? `${currency} ${total.toFixed(2)}` : total.toFixed(2);
    pills.push({ label: money, variant: 'neutral' });
  }

  const details: DetailLine[] = [];
  if (vendor_reference) {
    details.push({ label: 'Vendor Ref', value: vendor_reference, mono: true });
  }
  if (received_date) {
    details.push({ label: 'Received', value: received_date, mono: true });
  }
  if (received_by) {
    details.push({ label: 'Received By', value: received_by });
  }
  if (yacht_name) {
    details.push({ label: 'Vessel', value: yacht_name });
  }

  // Context line — show only the PO link (no supplier echo; supplier IS the title above)
  const contextNode = po_number ? (
    <>
      PO Reference:{' '}
      <span
        className={styles.crewLink}
        onClick={po_id ? () => router.push(getEntityRoute('purchase-orders' as Parameters<typeof getEntityRoute>[0], po_id)) : undefined}
        role={po_id ? 'link' : undefined}
        tabIndex={po_id ? 0 : undefined}
      >
        {po_number}
      </span>
    </>
  ) : undefined;

  // -- Split button config --
  const primaryLabel = 'Accept (Sign)';
  const primaryDisabled = acceptAction
    ? (acceptAction.disabled ?? false) || !isAcceptable
    : true;
  const primaryDisabledReason = acceptAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    // safeExecute (parent EntityLensPage) raises PIN modal for SIGNED actions
    await executeAction('accept_receiving', {});
  }, [executeAction]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  // reject_receiving = terminal status change. flag_discrepancy = structured
  // issue logging (no status change) — surfaced as a normal item, not danger.
  const DANGER_ACTIONS = new Set(['reject_receiving']);
  const primaryActionId = 'accept_receiving';

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

  // -- Map section data --
  // Packing list = the reconciliation grid (canonical "Checklist" section
  // per the design philosophy spec). Maps backend pms_receiving_items rows
  // to the column shape the grid expects. Δ computed client-side in the
  // section component.
  const packingItems: PackingItem[] = items.map((item, i) => ({
    id: (item.id as string) ?? `item-${i}`,
    partId: (item.part_id as string | null | undefined) ?? null,
    partCode: (item.part_number ?? item.part_code ?? item.sku) as string | null | undefined,
    partName: (item.part_name ?? item.name) as string | null | undefined,
    description: (item.description) as string | null | undefined,
    manufacturer: (item.manufacturer) as string | null | undefined,
    quantityExpected: item.quantity_expected === null || item.quantity_expected === undefined
      ? null
      : Number(item.quantity_expected),
    quantityReceived: Number(item.quantity_received ?? 0),
    unitPrice: item.unit_price === null || item.unit_price === undefined
      ? null
      : Number(item.unit_price),
    currency: (item.currency) as string | null | undefined,
  }));

  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const docItems: DocRowItem[] = linked_entities.map((d, i) => ({
    id: (d.id as string) ?? `link-${i}`,
    name: (d.name ?? d.title ?? d.entity_title) as string ?? 'Related',
    code: (d.code ?? d.entity_code ?? d.reference) as string | undefined,
    meta: (d.meta ?? d.entity_type ?? d.description) as string | undefined,
    date: (d.date ?? d.created_at) as string | undefined,
    onClick: d.entity_id
      ? () => router.push(getEntityRoute(
          (d.entity_type as Parameters<typeof getEntityRoute>[0]) ?? 'work-orders',
          d.entity_id as string
        ))
      : undefined,
  }));

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          acceptAction ? (
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

      {/* Packing List — reconciliation grid (the hero section per philosophy) */}
      <ScrollReveal>
        <ReceivingPackingList
          items={packingItems}
          storedSubtotal={(entity?.subtotal ?? payload.subtotal) as number | null | undefined}
          storedTaxTotal={(entity?.tax_total ?? payload.tax_total) as number | null | undefined}
          storedTotal={total}
          headerCurrency={currency}
        />
      </ScrollReveal>

      {/* Related Work (linked entities) */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Related Work" docs={docItems} />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={undefined}
          canAddNote={false}
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

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
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
