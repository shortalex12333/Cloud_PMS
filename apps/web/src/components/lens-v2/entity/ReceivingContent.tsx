'use client';

/**
 * ReceivingContent — lens-v2 Receiving entity view.
 * Matches lens-receiving.html prototype.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines
 * 2. Packing List (PartsSection — items with expected vs received quantities)
 * 3. Print / Barcode button
 * 4. Notes
 * 5. Attachments
 * 6. Audit Trail
 *
 * Per owner review: discrepancy reason is per-line-item (merged into line items),
 * not a separate section. Confirm button is ghost teal 44px height.
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
  PartsSection,
  DocRowsSection,
  KVSection,
  type NoteItem,
  type AuditEvent,
  type AttachmentItem,
  type PartItem,
  type DocRowItem,
  type KVItem,
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
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // -- Extract entity fields --
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const receiving_number = (entity?.receiving_number ?? payload.receiving_number) as string | undefined;
  const title = ((entity?.title ?? payload.title ?? entity?.description ?? payload.description) as string | undefined) ?? 'Receiving';
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'pending';
  const po_number = (entity?.po_number ?? payload.po_number) as string | undefined;
  const po_id = (entity?.po_id ?? payload.po_id) as string | undefined;
  const supplier = (entity?.supplier ?? payload.supplier ?? entity?.vendor_name ?? payload.vendor_name) as string | undefined;
  const supplier_ref = (entity?.supplier_ref ?? payload.supplier_ref ?? entity?.vendor_reference ?? payload.vendor_reference) as string | undefined;
  const delivery_date = (entity?.delivery_date ?? payload.delivery_date ?? entity?.expected_date ?? payload.expected_date) as string | undefined;
  const received_by = (entity?.received_by ?? payload.received_by) as string | undefined;
  const vessel = (entity?.vessel ?? payload.vessel ?? entity?.yacht_name ?? payload.yacht_name) as string | undefined;
  const total_items = (entity?.total_items ?? payload.total_items) as number | undefined;

  // Section data
  const items = ((entity?.items ?? payload.items) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const linked_entities = ((entity?.linked_entities ?? payload.linked_entities ?? entity?.related_entities ?? payload.related_entities) as Array<Record<string, unknown>> | undefined) ?? [];

  // -- Action gates --
  const acceptAction = getAction('accept_delivery');
  const flagAction = getAction('flag_discrepancy');
  const confirmAction = getAction('confirm_receiving');
  const barcodeAction = getAction('generate_barcode');

  const isConfirmable = ['pending', 'in_progress'].includes(status);

  // -- Derived display --
  const statusLabel = formatLabel(status);
  const itemCount = total_items ?? items.length;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (itemCount > 0) {
    pills.push({ label: `${itemCount} Item${itemCount === 1 ? '' : 's'}`, variant: 'neutral' });
  }

  const details: DetailLine[] = [];
  if (supplier) {
    details.push({ label: 'Supplier', value: supplier });
  }
  if (supplier_ref) {
    details.push({ label: 'Supplier Ref', value: supplier_ref, mono: true });
  }
  if (po_number) {
    details.push({ label: 'PO Reference', value: po_number, mono: true });
  }
  if (delivery_date) {
    details.push({ label: 'Expected', value: delivery_date, mono: true });
  }
  if (received_by) {
    details.push({ label: 'Received By', value: received_by });
  }
  if (vessel) {
    details.push({ label: 'Vessel', value: vessel });
  }

  // Context line
  const contextParts: string[] = [];
  if (supplier) contextParts.push(supplier);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {po_number && (
        <>
          {contextParts.length > 0 && ' · '}
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
      )}
    </>
  );

  // -- Split button config --
  const primaryLabel = 'Confirm Receipt';
  const primaryDisabled = confirmAction
    ? (confirmAction.disabled ?? false) || !isConfirmable
    : true;
  const primaryDisabledReason = confirmAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('confirm_receiving', {});
  }, [executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (barcodeAction !== null) {
    dropdownItems.push({
      label: 'Print Barcodes',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="6" y="6" width="12" height="12" rx="1" /><path d="M6 10h12M10 6v12" /></svg>,
      onClick: () => executeAction('generate_barcode', {}),
    });
  }
  if (flagAction !== null && status !== 'discrepancy') {
    dropdownItems.push({
      label: 'Flag Discrepancy',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
      onClick: () => executeAction('flag_discrepancy', {}),
    });
  }
  if (acceptAction !== null && status !== 'completed') {
    dropdownItems.push({
      label: 'Accept Delivery',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>,
      onClick: () => executeAction('accept_delivery', {}),
    });
  }

  // -- Map section data --
  const partItems: PartItem[] = items.map((item, i) => {
    const expected = item.quantity_ordered ?? item.quantity_expected ?? item.quantity;
    const received = item.quantity_received ?? item.received;
    const itemStatus = (item.status as string) ?? '';
    const discrepancyReason = (item.discrepancy_reason ?? item.reason) as string | undefined;

    let stockDisplay: string | undefined;
    if (expected !== undefined && received !== undefined) {
      stockDisplay = `Exp: ${expected} / Rcvd: ${received}`;
      if (discrepancyReason) {
        stockDisplay += ` — ${discrepancyReason}`;
      }
    } else if (itemStatus) {
      stockDisplay = formatLabel(itemStatus);
    }

    return {
      id: (item.id as string) ?? `item-${i}`,
      name: (item.name ?? item.description ?? item.part_name) as string ?? 'Item',
      partNumber: (item.part_number ?? item.sku) as string | undefined,
      quantity: received !== undefined ? `x ${received}` : undefined,
      stock: stockDisplay,
      onNavigate: item.part_id
        ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], item.part_id as string))
        : undefined,
    };
  });

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

  const handleAddNote = React.useCallback(() => {}, []);

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={receiving_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          (confirmAction || acceptAction) ? (
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

      {/* Packing List (line items with expected vs received) */}
      <ScrollReveal>
        <PartsSection
          parts={partItems}
        />
      </ScrollReveal>

      {/* Print Barcodes button */}
      {barcodeAction !== null && (
        <ScrollReveal>
          <div style={{ padding: '0 0 8px' }}>
            <button
              className={styles.printBtn}
              onClick={() => executeAction('generate_barcode', {})}
              disabled={barcodeAction.disabled ?? false}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polyline points="6 9 6 2 18 2 18 9" />
                <path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2" />
                <rect x="6" y="14" width="12" height="8" />
              </svg>
              Print Labels
            </button>
          </div>
        </ScrollReveal>
      )}

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
          onAddNote={handleAddNote}
          canAddNote={false}
        />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile={false}
        />
      </ScrollReveal>

      {/* Audit Trail */}
      {auditEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection events={auditEvents} defaultCollapsed />
        </ScrollReveal>
      )}
    </>
  );
}
