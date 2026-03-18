'use client';

/**
 * ShoppingListContent — lens-v2 Shopping List entity view.
 * Matches lens-shopping-list.html prototype.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines, description
 * 2. Line Items (PartsSection — items with quantity, unit price, status per line)
 * 3. Cross-Entity Links (DocRows — linked POs, WOs)
 * 4. Notes (timeline)
 * 5. Audit Trail (collapsed by default)
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
  PartsSection,
  DocRowsSection,
  KVSection,
  type NoteItem,
  type AuditEvent,
  type PartItem,
  type DocRowItem,
  type KVItem,
} from '../sections';

// --- Colour mapping helpers ---

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'cancelled':
      return 'red';
    case 'submitted':
      return 'amber';
    case 'approved':
    case 'ordered':
    case 'received':
      return 'green';
    default:
      return 'neutral';
  }
}

function priorityToPillVariant(priority: string): PillDef['variant'] {
  switch (priority) {
    case 'critical':
      return 'red';
    case 'high':
      return 'amber';
    default:
      return 'neutral';
  }
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// --- Component ---

export function ShoppingListContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // -- Extract entity fields --
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const list_number = (entity?.list_number ?? payload.list_number) as string | undefined;
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? 'Shopping List';
  const description = (entity?.description ?? payload.description) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const priority = ((entity?.priority ?? payload.priority) as string | undefined) ?? 'normal';
  const created_by = (entity?.created_by ?? payload.created_by ?? entity?.requester_name ?? payload.requester_name) as string | undefined;
  const created_date = (entity?.created_date ?? payload.created_date ?? entity?.created_at ?? payload.created_at) as string | undefined;
  const port = (entity?.port ?? payload.port ?? entity?.delivery_location ?? payload.delivery_location) as string | undefined;
  const department = (entity?.department ?? payload.department) as string | undefined;
  const total_items = (entity?.total_items ?? payload.total_items) as number | undefined;
  const total_cost = (entity?.total_cost ?? payload.total_cost ?? entity?.estimated_total ?? payload.estimated_total) as number | undefined;
  const currency = ((entity?.currency ?? payload.currency) as string | undefined) ?? 'USD';
  const approver_name = (entity?.approver_name ?? payload.approver_name) as string | undefined;
  const approved_at = (entity?.approved_at ?? payload.approved_at) as string | undefined;

  // Section data
  const items = ((entity?.items ?? payload.items) as Array<Record<string, unknown>> | undefined) ?? [];
  const notes = ((entity?.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history) as Array<Record<string, unknown>> | undefined) ?? [];
  const linked_entities = ((entity?.linked_entities ?? payload.linked_entities ?? entity?.documents ?? payload.documents) as Array<Record<string, unknown>> | undefined) ?? [];

  // -- Action gates --
  const submitAction = getAction('submit_list');
  const approveAction = getAction('approve_list');
  const convertAction = getAction('convert_to_po');
  const addItemAction = getAction('add_list_item');
  const archiveAction = getAction('archive_list');

  const isArchivable = !['cancelled', 'archived'].includes(status);

  // -- Derived display --
  const statusLabel = formatLabel(status);
  const priorityLabel = formatLabel(priority);
  const itemCount = total_items ?? items.length;

  const pills: PillDef[] = [
    { label: statusLabel, variant: statusToPillVariant(status) },
  ];
  if (itemCount > 0) {
    pills.push({ label: `${itemCount} Item${itemCount === 1 ? '' : 's'}`, variant: 'neutral' });
  }
  if (priority !== 'normal' && priority !== 'medium') {
    pills.push({ label: priorityLabel, variant: priorityToPillVariant(priority) });
  }

  const details: DetailLine[] = [];
  if (created_by) {
    details.push({ label: 'Requester', value: created_by });
  }
  if (approver_name) {
    details.push({ label: 'Approver', value: approver_name });
  }
  if (created_date) {
    details.push({ label: 'Created', value: created_date, mono: true });
  }
  if (approved_at) {
    details.push({ label: 'Approved', value: approved_at, mono: true });
  }
  if (priority !== 'normal' && priority !== 'medium') {
    details.push({ label: 'Priority', value: priorityLabel });
  }
  if (department) {
    details.push({ label: 'Department', value: department });
  }
  if (port) {
    details.push({ label: 'Delivery', value: port });
  }
  if (total_cost !== undefined) {
    details.push({ label: 'Est. Total', value: `$${total_cost.toLocaleString()}`, mono: true });
  }

  // Context line
  const contextParts: string[] = [];
  if (department) contextParts.push(department);
  if (port) contextParts.push(port);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {created_by && (
        <>
          {contextParts.length > 0 && ' · '}
          Requested by <span className={styles.crewLink}>{created_by}</span>
        </>
      )}
    </>
  );

  // -- Split button config --
  const canConvert = convertAction !== null && ['approved'].includes(status);
  const canSubmit = submitAction !== null && ['draft'].includes(status);

  const primaryLabel = canConvert ? 'Convert to PO' : canSubmit ? 'Submit List' : 'Submit List';
  const primaryDisabled = canConvert
    ? (convertAction?.disabled ?? false)
    : canSubmit
      ? (submitAction?.disabled ?? false)
      : true;
  const primaryDisabledReason = canConvert
    ? convertAction?.disabled_reason
    : canSubmit
      ? submitAction?.disabled_reason
      : undefined;

  const handlePrimary = React.useCallback(async () => {
    if (canConvert) {
      await executeAction('convert_to_po', {});
    } else if (canSubmit) {
      await executeAction('submit_list', {});
    }
  }, [canConvert, canSubmit, executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (addItemAction !== null) {
    dropdownItems.push({
      label: 'Add Item',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>,
      onClick: () => {},
    });
  }
  if (approveAction !== null && status === 'submitted') {
    dropdownItems.push({
      label: 'Approve List',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>,
      onClick: () => executeAction('approve_list', {}),
    });
  }
  if (archiveAction !== null && isArchivable) {
    dropdownItems.push({
      label: 'Archive List',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>,
      onClick: () => executeAction('archive_list', {}),
      danger: true,
    });
  }

  // -- Map section data --
  const partItems: PartItem[] = items.map((item, i) => ({
    id: (item.id as string) ?? `item-${i}`,
    name: (item.part_name ?? item.name ?? item.description) as string ?? 'Item',
    partNumber: (item.part_number ?? item.sku) as string | undefined,
    quantity: (item.quantity_requested ?? item.quantity) !== undefined
      ? `x ${item.quantity_requested ?? item.quantity}`
      : undefined,
    stock: (item.unit_price ?? item.price) !== undefined
      ? `$${Number(item.unit_price ?? item.price).toLocaleString()}`
      : undefined,
    onNavigate: item.part_id
      ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], item.part_id as string))
      : undefined,
  }));

  const docItems: DocRowItem[] = linked_entities.map((d, i) => ({
    id: (d.id as string) ?? `link-${i}`,
    name: (d.name ?? d.title ?? d.entity_title) as string ?? 'Linked Entity',
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

  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  const handleAddNote = React.useCallback(
    () => {},
    []
  );

  const handleAddPart = React.useCallback(
    () => {},
    []
  );

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={list_number}
        title={title}
        context={contextNode}
        pills={pills}
        details={details}
        description={description}
        actionSlot={
          (submitAction || convertAction) ? (
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

      {/* Line Items */}
      <ScrollReveal>
        <PartsSection
          parts={partItems}
          onAddPart={handleAddPart}
          canAddPart={addItemAction !== null}
        />
      </ScrollReveal>

      {/* Cross-Entity Links */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Linked Entities" docs={docItems} />
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={handleAddNote}
          canAddNote={addItemAction !== null}
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
