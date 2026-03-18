'use client';

/**
 * PartsInventoryContent — lens-v2 Parts/Inventory entity view.
 * Matches lens-parts.html prototype exactly.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline (part number mono), title, context, pills, detail lines, description
 * 2. Stock Details (KVSection — stock level, min, reorder, location)
 * 3. Specifications (KVSection)
 * 4. Where Used (DocRows — equipment/WOs that use this part)
 * 5. Purchase History (AuditTrail)
 * 6. Suppliers (KVSection)
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

// ─── Status colour mapping ───

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'in_stock':
      return 'green';
    case 'low_stock':
      return 'amber';
    case 'out_of_stock':
      return 'red';
    case 'on_order':
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

export function PartsInventoryContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const part_number = (entity?.part_number ?? payload.part_number) as string | undefined;
  const name = ((entity?.name ?? entity?.part_name ?? payload.name ?? payload.part_name) as string | undefined) ?? 'Part';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const category = (entity?.category ?? payload.category) as string | undefined;
  const manufacturer = (entity?.manufacturer ?? payload.manufacturer) as string | undefined;
  const unit_cost = (entity?.unit_cost ?? payload.unit_cost) as number | undefined;
  const currency = (entity?.currency ?? payload.currency) as string | undefined;
  const stock_level = ((entity?.stock_level ?? entity?.quantity_on_hand ?? entity?.stock_quantity ?? payload.stock_level ?? payload.quantity_on_hand) as number | undefined) ?? 0;
  const min_stock_level = ((entity?.min_stock_level ?? entity?.minimum_quantity ?? payload.min_stock_level ?? payload.minimum_quantity) as number | undefined) ?? 0;
  const reorder_quantity = (entity?.reorder_quantity ?? payload.reorder_quantity) as number | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'in_stock';
  const unit = (entity?.unit ?? payload.unit) as string | undefined;
  const supplier = (entity?.supplier ?? payload.supplier) as string | undefined;
  const barcode = (entity?.barcode ?? payload.barcode) as string | undefined;

  // Section data
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const purchase_history = ((entity?.purchase_history ?? payload.purchase_history ?? entity?.history ?? payload.history ?? entity?.audit_history ?? payload.audit_history) as Array<Record<string, unknown>> | undefined) ?? [];
  const where_used = ((entity?.where_used ?? payload.where_used ?? entity?.related_equipment ?? payload.related_equipment) as Array<Record<string, unknown>> | undefined) ?? [];
  const suppliers = ((entity?.suppliers ?? payload.suppliers) as Array<Record<string, unknown>> | undefined) ?? [];
  const specifications = ((entity?.specifications ?? payload.specifications ?? entity?.specs ?? payload.specs) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const takeStockAction = getAction('take_stock');
  const reorderAction = getAction('reorder_part');
  const updateAction = getAction('update_part_details');
  const archiveAction = getAction('archive_part');
  const addNoteAction = getAction('add_part_note');
  const adjustStockAction = getAction('adjust_stock_quantity');
  const logUsageAction = getAction('log_part_usage');

  // ── Derived display ──
  const statusLabel = formatLabel(status);
  const isLowStock = stock_level <= min_stock_level && stock_level > 0;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (isLowStock) {
    pills.push({ label: 'Below Minimum', variant: 'amber' });
  }

  const details: DetailLine[] = [];
  if (category) {
    details.push({ label: 'Category', value: category });
  }
  if (unit_cost !== undefined) {
    details.push({ label: 'Unit Cost', value: formatCurrency(unit_cost, currency), mono: true });
  }
  if (manufacturer) {
    details.push({ label: 'Manufacturer', value: manufacturer });
  }
  if (location) {
    details.push({ label: 'Location', value: location });
  }

  // Context line
  const contextParts: string[] = [];
  if (category) contextParts.push(category);
  if (manufacturer) contextParts.push(`OEM: ${manufacturer}`);
  const contextNode = contextParts.length > 0 ? (
    <>{contextParts.join(' \u00B7 ')}</>
  ) : undefined;

  // ── Split button config ──
  const primaryLabel = isLowStock || status === 'out_of_stock' ? 'Reorder' : 'Adjust Stock';
  const primaryAction = isLowStock || status === 'out_of_stock' ? reorderAction : adjustStockAction;
  const primaryDisabled = primaryAction?.disabled ?? false;
  const primaryDisabledReason = primaryAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    if (isLowStock || status === 'out_of_stock') {
      await executeAction('reorder_part', {});
    } else {
      await executeAction('adjust_stock_quantity', {});
    }
  }, [isLowStock, status, executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (takeStockAction !== null) {
    dropdownItems.push({
      label: 'Take Stock',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="5" y1="12" x2="19" y2="12" /></svg>,
      onClick: () => executeAction('take_stock', {}),
    });
  }
  if (logUsageAction !== null) {
    dropdownItems.push({
      label: 'Log Usage',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>,
      onClick: () => executeAction('log_part_usage', {}),
    });
  }
  if (updateAction !== null) {
    dropdownItems.push({
      label: 'Edit Details',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>,
      onClick: () => {},
    });
  }
  if (archiveAction !== null) {
    dropdownItems.push({
      label: 'Archive',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>,
      onClick: () => executeAction('archive_part', {}),
      danger: true,
    });
  }

  // ── Map section data ──

  // Stock details KV
  const stockItems: KVItem[] = [
    { label: 'Current Stock', value: `${stock_level}${unit ? ` ${unit}` : ''}`, mono: true },
    { label: 'Min Level', value: `${min_stock_level}${unit ? ` ${unit}` : ''}`, mono: true },
  ];
  if (reorder_quantity !== undefined) {
    stockItems.push({ label: 'Reorder Qty', value: `${reorder_quantity}${unit ? ` ${unit}` : ''}`, mono: true });
  }
  if (location) {
    stockItems.push({ label: 'Location', value: location });
  }
  if (unit_cost !== undefined) {
    const totalValue = unit_cost * stock_level;
    stockItems.push({ label: 'Unit Cost', value: formatCurrency(unit_cost, currency), mono: true });
    stockItems.push({ label: 'Total Value', value: formatCurrency(totalValue, currency), mono: true });
  }
  if (barcode) {
    stockItems.push({ label: 'Barcode', value: barcode, mono: true });
  }
  // Owner correction: barcode placeholder must always be present (design TBD, generated later)
  if (!barcode) {
    stockItems.push({ label: 'Barcode', value: 'Pending generation', mono: true });
  }

  // Specifications KV
  const specItems: KVItem[] = specifications.map((s) => ({
    label: (s.label ?? s.key ?? s.name) as string ?? 'Spec',
    value: (s.value ?? s.description) as string ?? '',
    mono: (s.mono as boolean | undefined) ?? false,
  }));

  // Where Used (equipment/WOs)
  const whereUsedItems: DocRowItem[] = where_used.map((w, i) => ({
    id: (w.id as string) ?? `where-${i}`,
    name: (w.name ?? w.equipment_name ?? w.title) as string ?? 'Equipment',
    code: (w.code ?? w.equipment_code ?? w.wo_number) as string | undefined,
    meta: (w.meta ?? w.description) as string | undefined,
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
      </svg>
    ),
    onClick: w.id
      ? () => router.push(getEntityRoute((w.entity_type ?? 'equipment') as Parameters<typeof getEntityRoute>[0], w.id as string))
      : undefined,
  }));

  // Purchase history as audit trail
  const purchaseEvents: AuditEvent[] = purchase_history.map((h, i) => ({
    id: (h.id as string) ?? `purchase-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.supplier ?? h.vendor ?? h.user_name) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp ?? h.date) as string ?? '',
  }));

  // Suppliers KV
  const supplierItems: KVItem[] = suppliers.length > 0
    ? suppliers.map((s) => ({
        label: (s.name ?? s.supplier_name) as string ?? 'Supplier',
        value: (s.url ?? s.website ?? s.contact ?? s.description ?? '') as string,
      }))
    : supplier
      ? [{ label: 'Primary Supplier', value: supplier }]
      : [];

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
        overline={part_number}
        title={name}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          primaryAction ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label="Actions"
              onClick={() => {}}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Stock Details */}
      <ScrollReveal>
        <KVSection
          title="Stock Details"
          items={stockItems}
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <path d="M16 10a4 4 0 01-8 0" />
            </svg>
          }
        />
      </ScrollReveal>

      {/* Barcode Placeholder — owner: must be present in lens (design TBD, generated later) */}
      <ScrollReveal>
        <div className={styles.section}>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            padding: '16px 0 12px',
            gap: 6,
          }}>
            <div style={{
              width: '100%', maxWidth: 200, height: 48,
              background: barcode
                ? 'repeating-linear-gradient(90deg, var(--txt) 0px, var(--txt) 2px, transparent 2px, transparent 4px)'
                : 'repeating-linear-gradient(90deg, var(--border-sub) 0px, var(--border-sub) 2px, transparent 2px, transparent 4px)',
              borderRadius: 2,
              opacity: barcode ? 0.8 : 0.3,
            }} />
            <span className={styles.mono} style={{
              fontSize: 10, letterSpacing: '0.08em',
              color: barcode ? 'var(--txt3)' : 'var(--txt-ghost)',
              textTransform: 'uppercase',
            }}>
              {barcode ?? 'Barcode pending'}
            </span>
          </div>
        </div>
      </ScrollReveal>

      {/* Specifications */}
      {specItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Specifications"
            items={specItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Where Used */}
      {whereUsedItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Related Equipment"
            docs={whereUsedItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Purchase History */}
      {purchaseEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection events={purchaseEvents} defaultCollapsed />
        </ScrollReveal>
      )}

      {/* Suppliers */}
      {supplierItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Suppliers"
            items={supplierItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
              </svg>
            }
          />
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
          canAddFile={false}
        />
      </ScrollReveal>
    </>
  );
}
