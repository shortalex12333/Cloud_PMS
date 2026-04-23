'use client';

/**
 * PurchaseOrderContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-purchase-order.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Line Items → Budget → Delivery → Approvals → Notes → Attachments → History → Receiving Log → Audit Trail
 *
 * TODO notes for next engineer:
 * - Edit handler not wired
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
import { getEntityRoute } from '@/lib/entityRoutes';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';
import { AddNoteModal } from '@/components/lens-v2/actions/AddNoteModal';

// Sections
import {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  PartsSection,
  KVSection,
  HistorySection,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type PartItem,
  type KVItem,
  type HistoryPeriod,
} from '../sections';

// ─── Status colour mapping ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'draft':
      return 'neutral';
    case 'submitted':
    case 'partially_received':
      return 'amber';
    case 'approved':
    case 'received':
      return 'green';
    case 'cancelled':
      return 'red';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatCurrency(amount: number, currency?: string): string {
  const sym = currency === 'EUR' ? '\u20AC' : currency === 'GBP' ? '\u00A3' : '$';
  return `${sym}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ─── Component ───

export function PurchaseOrderContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const po_number = (entity?.po_number ?? payload.po_number) as string | undefined;
  const title = ((entity?.title ?? payload.title ?? entity?.description ?? payload.description) as string | undefined) ?? 'Purchase Order';
  const supplier = ((entity?.supplier ?? entity?.supplier_name ?? entity?.vendor_name ?? payload.supplier ?? payload.supplier_name ?? payload.vendor_name) as string | undefined);
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const total_amount = (entity?.total_amount ?? payload.total_amount) as number | undefined;
  const currency = ((entity?.currency ?? payload.currency) as string | undefined) ?? 'USD';
  const ordered_date = (entity?.ordered_date ?? entity?.order_date ?? payload.ordered_date ?? payload.order_date) as string | undefined;
  const expected_delivery = (entity?.expected_delivery ?? payload.expected_delivery) as string | undefined;
  const approved_by = (entity?.approved_by ?? entity?.approved_by_name ?? payload.approved_by ?? payload.approved_by_name) as string | undefined;
  const requested_by = (entity?.requested_by ?? entity?.requested_by_name ?? payload.requested_by ?? payload.requested_by_name) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const description = (entity?.description ?? payload.description) as string | undefined;
  const shipping_cost = (entity?.shipping_cost ?? payload.shipping_cost) as number | undefined;

  // Section data
  const line_items = ((entity?.line_items ?? entity?.items ?? payload.line_items ?? payload.items) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const audit_history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const receiving_log = ((entity?.receiving_log ?? payload.receiving_log ?? entity?.deliveries ?? payload.deliveries) as Array<Record<string, unknown>> | undefined) ?? [];
  const budget_context = ((entity?.budget_context ?? payload.budget_context ?? entity?.budget ?? payload.budget) as Record<string, unknown> | undefined);
  const approval_signatures = ((entity?.approval_signatures ?? payload.approval_signatures ?? entity?.approvals ?? payload.approvals) as Array<Record<string, unknown>> | undefined) ?? [];
  const delivery = ((entity?.delivery ?? payload.delivery) as Record<string, unknown> | undefined);

  // ── Action gates ──
  const submitAction = getAction('submit_purchase_order');
  const approveAction = getAction('approve_purchase_order');
  const receiveAction = getAction('mark_po_received');
  const cancelAction = getAction('cancel_po');
  const addNoteAction = getAction('add_po_note');
  const editAction = getAction('edit_purchase_order');
  const addAttachmentAction = getAction('add_po_attachment');

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

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];

  const details: DetailLine[] = [];
  if (ordered_date) {
    details.push({ label: 'Order Date', value: ordered_date, mono: true });
  }
  if (expected_delivery) {
    details.push({ label: 'Expected Delivery', value: expected_delivery, mono: true });
  }
  if (total_amount !== undefined) {
    details.push({ label: 'Total', value: formatCurrency(total_amount, currency), mono: true });
  }
  if (department) {
    details.push({ label: 'Department', value: department });
  }

  // Context line
  const contextParts: string[] = [];
  if (supplier) contextParts.push(supplier);
  const contextNode = (
    <>
      {contextParts.join(' \u00B7 ')}
      {requested_by && (
        <>
          {contextParts.length > 0 && ' \u00B7 '}
          Requested by <span className={styles.crewLink}>{requested_by}</span>
        </>
      )}
    </>
  );

  // ── Split button config ──
  const isDraft = status === 'draft';
  const isSubmitted = status === 'submitted';
  const isApproved = ['approved', 'partially_received'].includes(status);
  const isFinal = ['received', 'cancelled'].includes(status);

  let primaryLabel = 'Submit';
  let primaryAction = submitAction;
  let primaryActionKey = 'submit_purchase_order';
  if (isDraft && submitAction) {
    primaryLabel = 'Submit';
    primaryAction = submitAction;
    primaryActionKey = 'submit_purchase_order';
  } else if (isSubmitted && approveAction) {
    primaryLabel = 'Approve';
    primaryAction = approveAction;
    primaryActionKey = 'approve_purchase_order';
  } else if (isApproved && receiveAction) {
    primaryLabel = 'Receive Goods';
    primaryAction = receiveAction;
    primaryActionKey = 'mark_po_received';
  } else {
    primaryAction = null;
  }

  const primaryDisabled = primaryAction?.disabled ?? false;
  const primaryDisabledReason = primaryAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    if (!primaryAction) return;
    await executeAction(primaryActionKey, {});
  }, [primaryAction, primaryActionKey, executeAction]);

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['cancel_po', 'delete_po']);
  const primaryActionId2 = primaryActionKey;

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId2)
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

  // Line items as part rows with quantity x price
  const lineItemRows: PartItem[] = line_items.map((item, i) => {
    const qty = (item.quantity as number | undefined) ?? 1;
    const unitPrice = (item.unit_price ?? item.price) as number | undefined;
    const lineTotal = unitPrice !== undefined ? qty * unitPrice : undefined;
    const partNumber = (item.part_number ?? item.sku ?? item.part_id) as string | undefined;
    const itemName = (item.description ?? item.name ?? item.part_name) as string ?? `Item ${i + 1}`;

    return {
      id: (item.id as string) ?? `line-${i}`,
      name: itemName,
      partNumber: partNumber,
      quantity: `\u00D7 ${qty}`,
      stock: unitPrice !== undefined
        ? `${formatCurrency(unitPrice, currency)} ea`
        : undefined,
      onNavigate: item.part_id
        ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], item.part_id as string))
        : undefined,
    };
  });

  // Budget context KV
  const budgetItems: KVItem[] = [];
  if (budget_context) {
    const budgetTotal = (budget_context.total ?? budget_context.budget_total) as number | undefined;
    const budgetSpent = (budget_context.spent ?? budget_context.budget_spent) as number | undefined;
    const budgetRemaining = (budget_context.remaining ?? budget_context.budget_remaining) as number | undefined;
    const budgetName = (budget_context.name ?? budget_context.budget_name) as string | undefined;
    if (budgetName) budgetItems.push({ label: 'Budget', value: budgetName });
    if (budgetTotal !== undefined) budgetItems.push({ label: 'Total Budget', value: formatCurrency(budgetTotal, currency), mono: true });
    if (budgetSpent !== undefined) budgetItems.push({ label: 'Spent', value: formatCurrency(budgetSpent, currency), mono: true });
    if (budgetRemaining !== undefined) budgetItems.push({ label: 'Remaining', value: formatCurrency(budgetRemaining, currency), mono: true });
  }
  if (total_amount !== undefined) {
    budgetItems.push({ label: 'This Order', value: formatCurrency(total_amount, currency), mono: true });
  }
  if (shipping_cost !== undefined) {
    budgetItems.push({ label: 'Shipping', value: formatCurrency(shipping_cost, currency), mono: true });
  }

  // Approval signatures KV
  const approvalItems: KVItem[] = approval_signatures.map((s) => ({
    label: (s.role ?? s.title ?? 'Approval') as string,
    value: (s.name ?? s.signed_by ?? s.approved_by) as string ?? 'Pending',
  }));
  if (approved_by && approvalItems.length === 0) {
    approvalItems.push({ label: 'Approved By', value: approved_by });
  }

  // Delivery KV
  const deliveryItems: KVItem[] = [];
  if (delivery) {
    const carrier = (delivery.carrier ?? delivery.shipping_carrier) as string | undefined;
    const tracking = (delivery.tracking ?? delivery.tracking_number) as string | undefined;
    const deliverTo = (delivery.deliver_to ?? delivery.delivery_address) as string | undefined;
    const contact = (delivery.contact ?? delivery.contact_name) as string | undefined;
    if (expected_delivery) deliveryItems.push({ label: 'Expected', value: expected_delivery, mono: true });
    if (carrier) deliveryItems.push({ label: 'Carrier', value: carrier });
    if (tracking) deliveryItems.push({ label: 'Tracking', value: tracking, mono: true });
    if (deliverTo) deliveryItems.push({ label: 'Deliver To', value: deliverTo });
    if (contact) deliveryItems.push({ label: 'Contact', value: contact });
  }

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

  // Receiving log as audit trail
  const receivingEvents: AuditEvent[] = receiving_log.map((r, i) => ({
    id: (r.id as string) ?? `recv-${i}`,
    action: (r.action ?? r.description ?? r.event) as string ?? '',
    actor: (r.actor ?? r.received_by ?? r.user_name) as string | undefined,
    timestamp: (r.created_at ?? r.timestamp ?? r.date) as string ?? '',
  }));

  // Audit trail
  const auditEvents: AuditEvent[] = audit_history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // History periods
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
  }));

  const [addNoteOpen, setAddNoteOpen] = React.useState(false);
  const handleNoteSubmit = React.useCallback(
    async (noteText: string) => {
      const result = await executeAction('add_po_note', { note_text: noteText });
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
        overline={po_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description !== title ? description : undefined}
        actionSlot={
          (primaryAction || dropdownItems.length > 0) ? (
            <SplitButton
              label={primaryAction ? primaryLabel : 'Actions'}
              onClick={primaryAction ? handlePrimary : () => {}}
              disabled={primaryAction ? primaryDisabled : false}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Line Items */}
      <ScrollReveal>
        <PartsSection
          parts={lineItemRows}
          defaultCollapsed={false}
        />
      </ScrollReveal>

      {/* Budget Context */}
      {budgetItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Budget Context"
            items={budgetItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Delivery */}
      {deliveryItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Delivery"
            items={deliveryItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="1" y="3" width="15" height="13" />
                <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
                <circle cx="5.5" cy="18.5" r="2.5" />
                <circle cx="18.5" cy="18.5" r="2.5" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Approval Signatures */}
      {approvalItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Approval Signatures"
            items={approvalItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
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

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Receiving Log */}
      <ScrollReveal>
        <AuditTrailSection events={receivingEvents} defaultCollapsed />
      </ScrollReveal>

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
      <AddNoteModal
        open={addNoteOpen}
        onClose={() => setAddNoteOpen(false)}
        onSubmit={handleNoteSubmit}
        isLoading={isLoading}
      />
    </>
  );
}
