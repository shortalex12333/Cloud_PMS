'use client';

/**
 * ShoppingListContent — lens-v2 entity view for a single shopping list item.
 * Prototype: public/prototypes/lens-shopping-list.html
 *
 * Entity data comes from /v1/entity/shopping_list/{id} via useEntityLensContext().
 * Actions come from available_actions[] prefilled by entity_prefill.py.
 *
 * Sections: Identity → Lifecycle → Item Details → Links → Audit Trail
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';

import {
  AuditTrailSection,
  DocRowsSection,
  KVSection,
  type AuditEvent,
  type DocRowItem,
  type KVItem,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

function statusPillVariant(status: string): PillDef['variant'] {
  switch (status?.toLowerCase()) {
    case 'approved': return 'green';
    case 'ordered': return 'green';
    case 'fulfilled': return 'green';
    case 'rejected': return 'red';
    case 'under_review': return 'amber';
    case 'candidate': return 'neutral';
    default: return 'neutral';
  }
}

function urgencyPillVariant(urgency: string): PillDef['variant'] {
  switch (urgency?.toLowerCase()) {
    case 'critical': return 'red';
    case 'high': return 'amber';
    default: return 'neutral';
  }
}

function fmt(str?: string): string {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(d?: string): string {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function ShoppingListContent() {
  const { entity, availableActions, executeAction, getAction } = useEntityLensContext();

  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const get = <T = unknown>(key: string): T | undefined =>
    (entity?.[key] ?? payload[key]) as T | undefined;

  const id = get<string>('id');
  const title = get<string>('title') ?? get<string>('part_name') ?? 'Shopping List Item';
  const status = get<string>('status') ?? 'candidate';
  const urgency = get<string>('urgency') ?? get<string>('priority');
  const requesterName = get<string>('requester_name') ?? get<string>('created_by');
  const approverName = get<string>('approver_name');
  const approvedAt = get<string>('approved_at');
  const approvalNotes = get<string>('approval_notes');
  const rejectionReason = get<string>('rejection_reason');
  const createdAt = get<string>('created_at');
  const updatedAt = get<string>('updated_at');
  const sourceType = get<string>('source_type');
  const sourceNotes = get<string>('source_notes') ?? get<string>('description');
  const requiredByDate = get<string>('required_by_date');
  const isCandidatePart = get<boolean>('is_candidate_part');
  const preferredSupplier = get<string>('preferred_supplier');

  // Items array — the entity endpoint wraps the row in items:[...] for the lens
  const items = (get<Array<Record<string, unknown>>>('items') ?? []);
  const item = items[0] ?? {};
  const partNumber = (item.part_number ?? get<string>('part_number')) as string | undefined;
  const manufacturer = (item.manufacturer ?? get<string>('manufacturer')) as string | undefined;
  const unit = (item.unit ?? get<string>('unit')) as string | undefined;
  const qtyRequested = (item.quantity_requested ?? get<number>('quantity_requested')) as number | undefined;
  const qtyApproved = (item.quantity_approved ?? get<number>('quantity_approved')) as number | undefined;
  const estimatedPrice = (item.estimated_unit_price ?? get<number>('estimated_unit_price')) as number | undefined;

  const relatedEntities = (get<Array<Record<string, unknown>>>('related_entities') ?? []);

  // ── Action popup state ───────────────────────────────────────────────────────
  const [popupConfig, setPopupConfig] = React.useState<{
    actionId: string;
    title: string;
    fields: ActionPopupField[];
    signatureLevel: 0 | 1 | 2 | 3 | 4 | 5;
  } | null>(null);

  function openPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    setPopupConfig({
      actionId: action.action_id,
      title: action.label,
      fields: mapActionFields(action as Parameters<typeof mapActionFields>[0]),
      signatureLevel: getSignatureLevel(action as Parameters<typeof getSignatureLevel>[0]),
    });
  }

  // ── Pills & detail lines ─────────────────────────────────────────────────────
  const pills: PillDef[] = [
    { label: fmt(status), variant: statusPillVariant(status) },
  ];
  if (urgency && urgency !== 'normal') {
    pills.push({ label: fmt(urgency), variant: urgencyPillVariant(urgency) });
  }
  if (isCandidatePart) {
    pills.push({ label: 'Candidate', variant: 'neutral' });
  }

  const details: DetailLine[] = [];
  if (requesterName) details.push({ label: 'Requested by', value: requesterName });
  if (createdAt) details.push({ label: 'Created', value: formatDate(createdAt), mono: true });
  if (requiredByDate) details.push({ label: 'Required by', value: formatDate(requiredByDate), mono: true });
  if (approverName) details.push({ label: 'Approved by', value: approverName });
  if (approvedAt) details.push({ label: 'Approved', value: formatDate(approvedAt), mono: true });

  // ── KV section rows ──────────────────────────────────────────────────────────
  const kvItems: KVItem[] = [];
  if (partNumber) kvItems.push({ label: 'Part Number', value: partNumber, mono: true });
  if (manufacturer) kvItems.push({ label: 'Manufacturer', value: manufacturer });
  if (unit) kvItems.push({ label: 'Unit', value: unit });
  if (qtyRequested != null) kvItems.push({ label: 'Qty Requested', value: String(qtyRequested) });
  if (qtyApproved != null) kvItems.push({ label: 'Qty Approved', value: String(qtyApproved) });
  if (estimatedPrice != null) kvItems.push({ label: 'Est. Unit Price', value: `$${estimatedPrice.toLocaleString()}`, mono: true });
  if (preferredSupplier) kvItems.push({ label: 'Preferred Supplier', value: preferredSupplier });
  if (sourceType) kvItems.push({ label: 'Source', value: fmt(sourceType) });
  if (sourceNotes) kvItems.push({ label: 'Notes / Reason', value: sourceNotes });
  if (approvalNotes) kvItems.push({ label: 'Approval Notes', value: approvalNotes });
  if (rejectionReason) kvItems.push({ label: 'Rejection Reason', value: rejectionReason });

  // ── Related entity links ─────────────────────────────────────────────────────
  const docItems: DocRowItem[] = relatedEntities.map((e, i) => ({
    id: (e.entity_id as string) ?? `link-${i}`,
    name: (e.label as string) ?? 'Linked Entity',
    code: (e.entity_type as string) ?? undefined,
    meta: undefined,
    date: undefined,
  }));

  // ── Audit events ─────────────────────────────────────────────────────────────
  const history = (get<Array<Record<string, unknown>>>('audit_history') ?? []);
  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // ── SplitButton — primary action + dropdown ──────────────────────────────────
  const approveAction = getAction('approve_shopping_list_item');
  const rejectAction = getAction('reject_shopping_list_item');
  const promoteAction = getAction('promote_candidate_to_part');
  const orderAction = getAction('mark_shopping_list_ordered');

  // Primary: approve if available, else first non-approve action
  const primaryAction = approveAction ?? orderAction;
  const primaryLabel = primaryAction?.label ?? 'No Actions';
  const primaryDisabled = !primaryAction || (primaryAction.disabled ?? false);

  const handlePrimary = React.useCallback(async () => {
    if (!primaryAction) return;
    const hasFields = actionHasFields(primaryAction as Parameters<typeof actionHasFields>[0]);
    if (hasFields || primaryAction.requires_signature) {
      openPopup(primaryAction as Parameters<typeof openPopup>[0]);
    } else {
      await executeAction(primaryAction.action_id);
    }
  }, [primaryAction, executeAction]);

  const DANGER_ACTIONS = new Set(['delete_shopping_item']);
  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryAction?.action_id)
    .map((a) => ({
      label: a.label,
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
      onClick: () => {
        const hasFields = actionHasFields(a as Parameters<typeof actionHasFields>[0]);
        if (hasFields || a.requires_signature) {
          openPopup(a as Parameters<typeof openPopup>[0]);
        } else {
          executeAction(a.action_id);
        }
      },
    }));

  // ── Lifecycle steps ──────────────────────────────────────────────────────────
  const LIFECYCLE = ['candidate', 'under_review', 'approved', 'ordered', 'fulfilled'] as const;
  const currentIdx = LIFECYCLE.indexOf(status as typeof LIFECYCLE[number]);

  return (
    <>
      <IdentityStrip
        overline={partNumber ? `#${partNumber}` : undefined}
        title={title}
        context={requesterName ? <>Requested by <span className={styles.crewLink}>{requesterName}</span></> : undefined}
        pills={pills}
        details={details}
        description={sourceNotes}
        actionSlot={
          availableActions.length > 0 ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Lifecycle progress */}
      <ScrollReveal>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, padding: '16px 0', marginBottom: 8 }}>
          {LIFECYCLE.map((step, i) => {
            const isCompleted = currentIdx >= 0 && i < currentIdx;
            const isActive = i === currentIdx;

            return (
              <React.Fragment key={step}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 0 }}>
                  <div style={{
                    width: isActive ? 12 : 10, height: isActive ? 12 : 10, borderRadius: '50%',
                    background: isCompleted || isActive ? 'var(--green, #4caf50)' : 'none',
                    border: `2px solid ${isCompleted || isActive ? 'var(--green, #4caf50)' : 'var(--txt-ghost, #666)'}`,
                    boxShadow: isActive ? '0 0 0 4px var(--green-bg, rgba(76,175,80,0.15))' : 'none',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {isCompleted && (
                      <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
                        <polyline points="2.5 6 5 8.5 9.5 3.5" />
                      </svg>
                    )}
                  </div>
                  <span style={{
                    fontSize: 10, fontWeight: isActive ? 600 : 500,
                    letterSpacing: '0.03em',
                    color: isActive ? 'var(--green, #4caf50)' : isCompleted ? 'var(--txt3, #999)' : 'var(--txt-ghost, #666)',
                    marginTop: 8, textTransform: 'uppercase', whiteSpace: 'nowrap',
                  }}>
                    {fmt(step)}
                  </span>
                </div>
                {i < LIFECYCLE.length - 1 && (
                  <div style={{
                    flex: 1, height: 2,
                    background: isCompleted ? 'var(--green, #4caf50)' : 'var(--border-sub, #444)',
                    alignSelf: 'flex-start', marginTop: isActive ? 6 : 5, minWidth: 8,
                  }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </ScrollReveal>

      {/* Item detail KV rows */}
      {kvItems.length > 0 && (
        <ScrollReveal>
          <KVSection title="Item Details" items={kvItems} />
        </ScrollReveal>
      )}

      {/* Linked entities (part, work order) */}
      {docItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection title="Linked Entities" docs={docItems} />
        </ScrollReveal>
      )}

      {/* Audit trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {popupConfig && (
        <ActionPopup
          mode="mutate"
          title={popupConfig.title}
          fields={popupConfig.fields}
          signatureLevel={popupConfig.signatureLevel}
          onSubmit={async (values) => {
            await executeAction(popupConfig.actionId, values);
            setPopupConfig(null);
          }}
          onClose={() => setPopupConfig(null)}
        />
      )}
    </>
  );
}
