'use client';

/**
 * ShoppingListContent — lens-v2 entity view.
 * Prototype: public/prototypes/lens-shopping-list.html
 *
 * Data flow:
 * - Entity data from useEntityLensContext() → backend /v1/entity/{type}/{id}
 * - Actions from availableActions[] → backend /v1/actions/execute
 * - ActionPopup auto-builds form fields from action.required_fields
 *
 * Sections: Identity → Lifecycle → Line Items → Links → Notes → History → Audit Trail → Attachments
 *
 * TODO notes for next engineer:
 * - Add Item handler not wired
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

// Sections
import {
  NotesSection,
  AuditTrailSection,
  PartsSection,
  DocRowsSection,
  KVSection,
  AttachmentsSection,
  HistorySection,
  type NoteItem,
  type AuditEvent,
  type PartItem,
  type DocRowItem,
  type KVItem,
  type AttachmentItem,
  type HistoryPeriod,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

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
  const { entity, availableActions, executeAction, getAction, isLoading } = useEntityLensContext();

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

  const SPECIAL_HANDLERS: Record<string, () => void> = {};
  const DANGER_ACTIONS = new Set(['archive_list', 'delete_list']);
  const primaryActionId = canConvert ? 'convert_to_po' : 'submit_list';

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

  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];
  const priorPeriods = ((entity?.prior_periods ?? payload.prior_periods ?? entity?.history_periods ?? payload.history_periods) as Array<Record<string, unknown>> | undefined) ?? [];

  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  const historyPeriods: HistoryPeriod[] = priorPeriods.map((p, i) => ({
    id: (p.id as string) ?? `period-${i}`,
    year: (p.year ?? p.period_year) as string ?? '',
    label: (p.label ?? p.period_label ?? p.description) as string ?? '',
    status: ((p.status as string) === 'active' || (p.status as string) === 'current') ? 'active' as const : 'closed' as const,
    summary: (p.summary ?? p.period_summary) as string ?? '',
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

      {/* Lifecycle Progress */}
      <ScrollReveal>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, padding: '16px 0', marginBottom: 8 }}>
          {(['draft', 'submitted', 'approved', 'ordered', 'received', 'archived'] as const).map((step, i, arr) => {
            const stepIndex = arr.indexOf(step);
            const currentIndex = arr.indexOf(status as typeof step);
            const isCompleted = currentIndex >= 0 && stepIndex < currentIndex;
            const isActive = stepIndex === currentIndex;
            const isFuture = currentIndex < 0 ? stepIndex > 0 : stepIndex > currentIndex;

            return (
              <React.Fragment key={step}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      width: isActive ? 12 : 10,
                      height: isActive ? 12 : 10,
                      borderRadius: '50%',
                      background: isCompleted || isActive ? 'var(--green, #4caf50)' : 'none',
                      border: `2px solid ${isCompleted || isActive ? 'var(--green, #4caf50)' : 'var(--txt-ghost, #666)'}`,
                      boxShadow: isActive ? '0 0 0 4px var(--green-bg, rgba(76,175,80,0.15))' : 'none',
                      position: 'relative',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {isCompleted && (
                      <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
                        <polyline points="2.5 6 5 8.5 9.5 3.5" />
                      </svg>
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: isActive ? 600 : 500,
                      letterSpacing: '0.03em',
                      color: isActive ? 'var(--green, #4caf50)' : isCompleted ? 'var(--txt3, #999)' : 'var(--txt-ghost, #666)',
                      marginTop: 8,
                      textTransform: 'uppercase',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatLabel(step)}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <div
                    style={{
                      flex: 1,
                      height: 2,
                      background: isCompleted ? 'var(--green, #4caf50)' : 'var(--border-sub, #444)',
                      alignSelf: 'flex-start',
                      marginTop: isActive ? 6 : 5,
                      minWidth: 8,
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </ScrollReveal>

      {/* Line Items */}
      <ScrollReveal>
        <PartsSection
          parts={partItems}
          onAddPart={handleAddPart}
          canAddPart
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
          canAddNote
        />
      </ScrollReveal>

      {/* History */}
      <ScrollReveal><HistorySection periods={historyPeriods} defaultCollapsed /></ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile
        />
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
