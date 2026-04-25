'use client';

/**
 * PurchaseOrderContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-purchase-order.html
 *
 * Layout: IdentityStrip (sticky) → 7-tab LensTabBar
 * Tabs: Items | Invoice | Supplier | Related Parts | Docs | Notes | Audit Trail
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { LensTabBar, type LensTab } from '../LensTabBar';
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
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type PartItem,
  type KVItem,
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
  const sym = currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$';
  return `${sym}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ─── Component ───

export function PurchaseOrderContent() {
  const router = useRouter();
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const po_number = (entity?.po_number ?? payload.po_number) as string | undefined;
  const supplier = ((entity?.supplier_name ?? (entity?.supplier as { name?: string } | undefined)?.name ?? entity?.vendor_name ?? payload.supplier_name ?? payload.supplier ?? payload.vendor_name) as string | undefined);
  const title = supplier ?? ((entity?.title ?? payload.title) as string | undefined) ?? 'Purchase Order';
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const total_amount = (entity?.total_amount ?? payload.total_amount) as number | undefined;
  const item_count = (entity?.item_count ?? payload.item_count) as number | undefined;
  const currency = ((entity?.currency ?? payload.currency) as string | undefined) ?? 'USD';
  const ordered_date = (entity?.ordered_at ?? entity?.order_date ?? entity?.ordered_date ?? payload.ordered_at ?? payload.order_date) as string | undefined;
  const received_date = (entity?.received_at ?? payload.received_at) as string | undefined;
  const approved_at = (entity?.approved_at ?? payload.approved_at) as string | undefined;
  const expected_delivery = (entity?.expected_delivery ?? payload.expected_delivery) as string | undefined;
  type Actor = { id?: string | null; name?: string | null; role?: string | null } | null | undefined;
  const orderedByActor  = (entity?.ordered_by_actor  as Actor) ?? null;
  const approvedByActor = (entity?.approved_by_actor as Actor) ?? null;
  const receivedByActor = (entity?.received_by_actor as Actor) ?? null;
  const deletedByActor  = (entity?.deleted_by_actor  as Actor) ?? null;
  const approved_by = approvedByActor?.name ?? ((entity?.approved_by_name ?? payload.approved_by_name) as string | undefined);
  const requested_by = orderedByActor?.name ?? ((entity?.ordered_by_name ?? entity?.requested_by_name ?? payload.ordered_by_name ?? payload.requested_by_name) as string | undefined);
  const received_by = receivedByActor?.name ?? ((entity?.received_by_name ?? payload.received_by_name) as string | undefined);
  const deleted_at = (entity?.deleted_at ?? payload.deleted_at) as string | undefined;
  const deletion_reason = (entity?.deletion_reason ?? payload.deletion_reason) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const description = (entity?.description ?? entity?.notes ?? payload.description ?? payload.notes) as string | undefined;
  const shipping_cost = (entity?.shipping_cost ?? payload.shipping_cost) as number | undefined;

  // Supplier block — entity_routes.py:get_purchase_order_entity resolves this
  type SupplierBlock = { id?: string | null; name?: string | null; contact_name?: string | null; email?: string | null; phone?: string | null; address?: string | null } | null | undefined;
  const supplierBlock = (entity?.supplier as SupplierBlock) ?? null;

  // Section data
  const line_items = ((entity?.line_items ?? entity?.items ?? payload.line_items ?? payload.items) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const audit_history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const receiving_log = ((entity?.receiving_log ?? payload.receiving_log ?? entity?.deliveries ?? payload.deliveries) as Array<Record<string, unknown>> | undefined) ?? [];
  const budget_context = ((entity?.budget_context ?? payload.budget_context ?? entity?.budget ?? payload.budget) as Record<string, unknown> | undefined);
  const approval_signatures = ((entity?.approval_signatures ?? payload.approval_signatures ?? entity?.approvals ?? payload.approvals) as Array<Record<string, unknown>> | undefined) ?? [];
  const delivery = ((entity?.delivery ?? payload.delivery) as Record<string, unknown> | undefined);
  const related_parts = ((entity?.related_parts ?? payload.related_parts) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const submitAction = getAction('submit_purchase_order');
  const approveAction = getAction('approve_purchase_order');
  const receiveAction = getAction('mark_po_received');
  const addNoteAction = getAction('add_po_note');
  const uploadInvoiceAction = getAction('upload_invoice');

  // Upload invoice file-picker state
  const [invoicePickerOpen, setInvoicePickerOpen] = React.useState(false);
  const [invoiceFile, setInvoiceFile] = React.useState<File | null>(null);
  const [invoiceTitle, setInvoiceTitle] = React.useState('');
  const [invoiceDesc, setInvoiceDesc] = React.useState('');
  const [invoiceUploading, setInvoiceUploading] = React.useState(false);
  const invoiceInputRef = React.useRef<HTMLInputElement>(null);

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

  function fmtDate(iso?: string): string | undefined {
    if (!iso) return undefined;
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  function actorLine(actor: Actor, fallback?: string): string | undefined {
    if (actor?.name) {
      return actor.role ? `${actor.name} (${formatLabel(actor.role)})` : actor.name;
    }
    return fallback;
  }
  const details: DetailLine[] = [];
  if (ordered_date) details.push({ label: 'Ordered', value: fmtDate(ordered_date)!, mono: true });
  if (received_date) details.push({ label: 'Received', value: fmtDate(received_date)!, mono: true });
  else if (expected_delivery) details.push({ label: 'Expected Delivery', value: fmtDate(expected_delivery)!, mono: true });
  if (total_amount !== undefined && total_amount !== null) {
    const totalLabel = item_count !== undefined && item_count !== null
      ? `${formatCurrency(total_amount, currency)}  ·  ${item_count} item${item_count === 1 ? '' : 's'}`
      : formatCurrency(total_amount, currency);
    details.push({ label: 'Total', value: totalLabel, mono: true });
  }
  if (department) details.push({ label: 'Department', value: department });
  const requestedLine = actorLine(orderedByActor, requested_by);
  if (requestedLine) details.push({ label: 'Requested by', value: requestedLine });
  const approvedLine = actorLine(approvedByActor, approved_by);
  if (approvedLine) {
    const approvedDate = fmtDate(approved_at);
    details.push({ label: 'Approved by', value: approvedDate ? `${approvedLine}  ·  ${approvedDate}` : approvedLine });
  }
  const receivedLine = actorLine(receivedByActor, received_by);
  if (receivedLine) {
    const recDate = fmtDate(received_date);
    details.push({ label: 'Received by', value: recDate ? `${receivedLine}  ·  ${recDate}` : receivedLine });
  }

  const contextNode = supplier ? <>{supplier}</> : null;

  // ── Split button config ──
  const isDraft = status === 'draft';
  const isSubmitted = status === 'submitted';
  const isApproved = ['approved', 'partially_received'].includes(status);

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

  const SPECIAL_HANDLERS: Record<string, () => void> = {
    upload_invoice: () => {
      setInvoiceFile(null);
      setInvoiceTitle('');
      setInvoiceDesc('');
      setInvoicePickerOpen(true);
    },
  };
  const DANGER_ACTIONS = new Set(['cancel_po', 'delete_po']);

  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionKey)
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

  const lineItemRows: PartItem[] = line_items.map((item, i) => {
    const qty = (item.quantity as number | undefined) ?? 1;
    const unitPrice = (item.unit_price ?? item.price) as number | undefined;
    const partNumber = (item.part_number ?? item.sku ?? item.part_id) as string | undefined;
    const itemName = (item.description ?? item.name ?? item.part_name) as string ?? `Item ${i + 1}`;
    return {
      id: (item.id as string) ?? `line-${i}`,
      name: itemName,
      partNumber: partNumber,
      quantity: `× ${qty}`,
      stock: unitPrice !== undefined ? `${formatCurrency(unitPrice, currency)} ea` : undefined,
      onNavigate: item.part_id
        ? () => router.push(getEntityRoute('inventory', item.part_id as string))
        : undefined,
    };
  });

  const relatedPartRows: PartItem[] = related_parts.map((p, i) => ({
    id: (p.id as string) ?? `rp-${i}`,
    name: (p.name ?? p.part_name ?? p.description) as string ?? `Part ${i + 1}`,
    partNumber: (p.part_number ?? p.sku) as string | undefined,
    quantity: (p.quantity as number | undefined) !== undefined ? `× ${p.quantity}` : undefined,
    onNavigate: p.id
      ? () => router.push(getEntityRoute('inventory', p.id as string))
      : undefined,
  }));

  const supplierItems: KVItem[] = [];
  if (supplierBlock) {
    if (supplierBlock.name)         supplierItems.push({ label: 'Supplier',  value: supplierBlock.name });
    if (supplierBlock.contact_name) supplierItems.push({ label: 'Contact',   value: supplierBlock.contact_name });
    if (supplierBlock.email)        supplierItems.push({ label: 'Email',     value: supplierBlock.email, mono: true });
    if (supplierBlock.phone)        supplierItems.push({ label: 'Phone',     value: supplierBlock.phone, mono: true });
    if (supplierBlock.address)      supplierItems.push({ label: 'Address',   value: supplierBlock.address });
  } else if (supplier) {
    supplierItems.push({ label: 'Supplier', value: supplier });
  }

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

  const approvalItems: KVItem[] = approval_signatures.map((s) => ({
    label: (s.role ?? s.title ?? 'Approval') as string,
    value: (s.name ?? s.signed_by ?? s.approved_by) as string ?? 'Pending',
  }));
  if (approved_by && approvalItems.length === 0) {
    approvalItems.push({ label: 'Approved By', value: approved_by });
  }

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

  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // Split attachments: invoice vs general docs
  const invoiceAttachments: AttachmentItem[] = [];
  const docAttachments: AttachmentItem[] = [];
  attachments.forEach((a, i) => {
    const item: AttachmentItem = {
      id: (a.id as string) ?? `att-${i}`,
      name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
      caption: (a.caption ?? a.description) as string | undefined,
      size: (a.size ?? a.file_size) as string | undefined,
      kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
    };
    const cat = ((a.category ?? a.document_type ?? a.attachment_type) as string ?? '').toLowerCase();
    if (cat === 'invoice' || ((a.name ?? a.file_name ?? '') as string).toLowerCase().includes('invoice')) {
      invoiceAttachments.push(item);
    } else {
      docAttachments.push(item);
    }
  });

  const receivingEvents: AuditEvent[] = receiving_log.map((r, i) => ({
    id: (r.id as string) ?? `recv-${i}`,
    action: (r.action ?? r.description ?? r.event) as string ?? '',
    actor: (r.actor ?? r.received_by ?? r.user_name) as string | undefined,
    timestamp: (r.created_at ?? r.timestamp ?? r.date) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = audit_history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
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

  // ── Tabs ──
  const tabs: LensTab[] = [
    { key: 'items',   label: 'Items',    count: line_items.length || undefined },
    { key: 'invoice', label: 'Invoice',  count: invoiceAttachments.length || undefined },
    { key: 'supplier',label: 'Supplier' },
    { key: 'parts',   label: 'Related Parts', count: related_parts.length || undefined },
    { key: 'docs',    label: 'Docs',     count: docAttachments.length || undefined },
    { key: 'notes',   label: 'Notes',    count: noteItems.length || undefined },
    { key: 'audit',   label: 'Audit Trail', count: (auditEvents.length + receivingEvents.length) || undefined },
  ];

  const renderTabBody = React.useCallback((key: string): React.ReactNode => {
    switch (key) {

      case 'items':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '0 4px' }}>
            <PartsSection parts={lineItemRows} defaultCollapsed={false} />
            {budgetItems.length > 0 && (
              <KVSection title="Budget" items={budgetItems}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                  </svg>
                }
              />
            )}
            {deliveryItems.length > 0 && (
              <KVSection title="Delivery" items={deliveryItems}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <rect x="1" y="3" width="15" height="13" />
                    <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
                    <circle cx="5.5" cy="18.5" r="2.5" />
                    <circle cx="18.5" cy="18.5" r="2.5" />
                  </svg>
                }
              />
            )}
          </div>
        );

      case 'invoice':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '0 4px' }}>
            {invoiceAttachments.length > 0 ? (
              <AttachmentsSection attachments={invoiceAttachments} canAddFile={false} />
            ) : (
              <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'var(--txt-ghost)' }}>
                No invoice attached
              </div>
            )}
            {uploadInvoiceAction && (
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <button
                  onClick={() => {
                    setInvoiceFile(null); setInvoiceTitle(''); setInvoiceDesc('');
                    setInvoicePickerOpen(true);
                  }}
                  style={{
                    height: 30, padding: '0 16px', borderRadius: 4,
                    border: '1px solid var(--mark-hover)',
                    background: 'var(--teal-bg)', color: 'var(--mark)',
                    fontSize: 11, fontWeight: 500, cursor: 'pointer',
                  }}
                >
                  Upload Invoice
                </button>
              </div>
            )}
          </div>
        );

      case 'supplier':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '0 4px' }}>
            {supplierItems.length > 0 ? (
              <KVSection title="Supplier" items={supplierItems}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                    <polyline points="9 22 9 12 15 12 15 22" />
                  </svg>
                }
              />
            ) : (
              <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'var(--txt-ghost)' }}>
                No supplier linked
              </div>
            )}
            {approvalItems.length > 0 && (
              <KVSection title="Approvals" items={approvalItems}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                }
              />
            )}
          </div>
        );

      case 'parts':
        return (
          <div style={{ padding: '0 4px' }}>
            {relatedPartRows.length > 0 ? (
              <PartsSection parts={relatedPartRows} defaultCollapsed={false} />
            ) : (
              <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'var(--txt-ghost)' }}>
                No related parts
              </div>
            )}
          </div>
        );

      case 'docs':
        return (
          <div style={{ padding: '0 4px' }}>
            <AttachmentsSection
              attachments={docAttachments}
              onAddFile={() => {/* TODO: general doc upload */}}
              canAddFile
            />
          </div>
        );

      case 'notes':
        return (
          <div style={{ padding: '0 4px' }}>
            <NotesSection
              notes={noteItems}
              onAddNote={addNoteAction ? () => setAddNoteOpen(true) : undefined}
              canAddNote={!!addNoteAction}
            />
          </div>
        );

      case 'audit':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '0 4px' }}>
            {receivingEvents.length > 0 && (
              <AuditTrailSection title="Receiving Log" events={receivingEvents} defaultCollapsed={false} />
            )}
            <AuditTrailSection title="Audit Trail" events={auditEvents} defaultCollapsed={receivingEvents.length > 0} />
          </div>
        );

      default:
        return null;
    }
  }, [
    lineItemRows, budgetItems, deliveryItems,
    invoiceAttachments, uploadInvoiceAction,
    supplierItems, approvalItems,
    relatedPartRows, docAttachments,
    noteItems, addNoteAction,
    receivingEvents, auditEvents,
  ]);

  return (
    <>
      {deleted_at && (
        <div role="alert" style={{ padding: '10px 14px', marginBottom: '12px', borderLeft: '3px solid var(--red)', background: 'var(--red-bg)', color: 'var(--red)', borderRadius: 4, fontSize: 12, lineHeight: 1.45 }}>
          <strong style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', fontSize: 10, display: 'block', marginBottom: 4 }}>Deleted</strong>
          This purchase order was deleted on {fmtDate(deleted_at)}
          {deletedByActor?.name && (<> by {deletedByActor.name}{deletedByActor.role ? ` (${formatLabel(deletedByActor.role)})` : ''}</>)}
          .{deletion_reason ? ` Reason: ${deletion_reason}` : ''}
        </div>
      )}

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

      <LensTabBar
        tabs={tabs}
        defaultActiveKey="items"
        aria-label="Purchase order sections"
        renderBody={renderTabBody}
      />

      {/* Upload Invoice — file-picker modal */}
      {invoicePickerOpen && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', zIndex: 1000 }}
            onClick={() => setInvoicePickerOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: 'fixed', left: '50%', top: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 1001,
              width: 480, maxWidth: 'calc(100vw - 32px)',
              background: 'var(--surface-elevated)',
              border: '1px solid var(--border-sub)',
              borderRadius: 8,
              padding: '20px 24px 20px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: 'var(--txt)' }}>
              Upload Invoice
            </div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--txt3)', marginBottom: 5 }}>
                File
              </div>
              <div
                onClick={() => invoiceInputRef.current?.click()}
                style={{
                  padding: '10px 14px',
                  border: `1px dashed ${invoiceFile ? 'var(--green-border)' : 'var(--border-sub)'}`,
                  borderRadius: 5,
                  background: invoiceFile ? 'var(--green-bg)' : 'var(--surface-primary)',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: invoiceFile ? 'var(--green)' : 'var(--txt3)',
                  textAlign: 'center',
                }}
              >
                {invoiceFile ? `${invoiceFile.name}  ·  ${(invoiceFile.size / 1024).toFixed(1)} KB` : 'Click to choose file…'}
              </div>
              <input
                ref={invoiceInputRef}
                type="file"
                accept="application/pdf,image/*,.doc,.docx,.xls,.xlsx"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setInvoiceFile(f);
                  if (f && !invoiceTitle) setInvoiceTitle(f.name.replace(/\.[^.]+$/, ''));
                }}
              />
            </div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--txt3)', marginBottom: 5 }}>
                Title (optional)
              </div>
              <input
                type="text"
                value={invoiceTitle}
                onChange={(e) => setInvoiceTitle(e.target.value)}
                placeholder={invoiceFile ? invoiceFile.name.replace(/\.[^.]+$/, '') : 'Invoice title…'}
                style={{
                  width: '100%', padding: '7px 10px',
                  border: '1px solid var(--border-sub)',
                  borderRadius: 4, background: 'var(--surface-primary)',
                  color: 'var(--txt)', fontSize: 12, boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--txt3)', marginBottom: 5 }}>
                Description (optional)
              </div>
              <textarea
                value={invoiceDesc}
                onChange={(e) => setInvoiceDesc(e.target.value)}
                placeholder="Any notes about this invoice…"
                rows={2}
                style={{
                  width: '100%', padding: '7px 10px',
                  border: '1px solid var(--border-sub)',
                  borderRadius: 4, background: 'var(--surface-primary)',
                  color: 'var(--txt)', fontSize: 12, resize: 'none',
                  boxSizing: 'border-box', fontFamily: 'inherit',
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                onClick={() => setInvoicePickerOpen(false)}
                style={{
                  height: 30, padding: '0 14px', borderRadius: 4,
                  border: '1px solid var(--border-sub)',
                  background: 'var(--surface-el)', color: 'var(--txt3)',
                  fontSize: 11, cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                disabled={!invoiceFile || invoiceUploading}
                onClick={async () => {
                  if (!invoiceFile) return;
                  setInvoiceUploading(true);
                  try {
                    const fakePath = `pending/${Date.now()}_${invoiceFile.name}`;
                    await executeAction('upload_invoice', {
                      storage_path: fakePath,
                      filename: invoiceFile.name,
                      mime_type: invoiceFile.type || 'application/octet-stream',
                      file_size: invoiceFile.size,
                      description: invoiceDesc.trim() || undefined,
                      title: invoiceTitle.trim() || undefined,
                    });
                    setInvoicePickerOpen(false);
                  } finally {
                    setInvoiceUploading(false);
                  }
                }}
                style={{
                  height: 30, padding: '0 14px', borderRadius: 4,
                  border: '1px solid var(--mark-hover)',
                  background: (!invoiceFile || invoiceUploading) ? 'var(--surface-raised)' : 'var(--teal-bg)',
                  color: (!invoiceFile || invoiceUploading) ? 'var(--txt-ghost)' : 'var(--mark)',
                  fontSize: 11, fontWeight: 500,
                  cursor: (!invoiceFile || invoiceUploading) ? 'not-allowed' : 'pointer',
                  opacity: (!invoiceFile || invoiceUploading) ? 0.5 : 1,
                }}
              >
                {invoiceUploading ? 'Saving…' : 'Attach Invoice'}
              </button>
            </div>
          </div>
        </>
      )}

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
