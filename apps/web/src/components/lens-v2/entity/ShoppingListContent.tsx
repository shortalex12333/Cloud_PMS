'use client';

/**
 * ShoppingListContent — lens-v2 entity view for a single shopping-list item.
 * Prototype: public/prototypes/lens-shopping-list.html
 * UX spec:   /Users/celeste7/Desktop/lens_card_upgrades.md § "shopping list"
 *
 * Layout (2026-04-24 — tabbed workflow-lens pattern, matches WorkOrderContent.tsx):
 *   IdentityStrip       ← overline, title, pills, details, primary action
 *   Lifecycle stepper   ← 7 happy-path statuses + rejected off-ramp banner
 *   LensTabBar          ← Details / Approval / Procurement / Fulfilment / Attachments / Audit
 *
 * All backend-specific data (actions, prefill, audit_history, resolved user
 * names, linked entity nav URLs) comes from useEntityLensContext() via
 * GET /v1/entity/shopping_list/{id}. Nothing hits Supabase directly.
 *
 * UX rules baked in:
 *   1. NULL fields render as "—". Never hide a planned slot (CEO 2026-04-24:
 *      fix for the M8x30 Bolt "only Qty + Source" empty-card bug).
 *   2. Every FK UUID surfaces as a clickable row via `getEntityRoute`.
 *      Users never see raw UUIDs.
 *   3. Resolved user names come from the backend single-batch lookup.
 *   4. Role-gated actions stay in the SplitButton header; tabs are read-only
 *      + inline nudges (Promote to Catalogue panel for candidate parts).
 *   5. Token-driven styling only — no hardcoded colours or spacing.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { LensTabBar, type LensTab } from '../LensTabBar';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/entityRoutes';

import {
  AuditTrailSection,
  DocRowsSection,
  KVSection,
  type AuditEvent,
  type DocRowItem,
  type KVItem,
} from '../sections';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

// ── Pill + format helpers ─────────────────────────────────────────────────────

function statusPillVariant(status: string): PillDef['variant'] {
  switch (status?.toLowerCase()) {
    case 'approved':
    case 'fulfilled':
    case 'installed':
    case 'ordered':
    case 'partially_fulfilled':
      return 'green';
    case 'rejected':
      return 'red';
    case 'under_review':
      return 'amber';
    case 'candidate':
    default:
      return 'neutral';
  }
}

function urgencyPillVariant(urgency: string): PillDef['variant'] {
  switch (urgency?.toLowerCase()) {
    case 'critical':
      return 'red';
    case 'high':
      return 'amber';
    default:
      return 'neutral';
  }
}

function fmt(str?: string): string {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(d?: string): string {
  if (!d) return '';
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return '';
  return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatMoney(n?: number): string {
  if (n == null) return '—';
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** KV helper: keeps empty slots visible ("—") so the card exposes gaps
 *  rather than collapsing them — per CEO 2026-04-24 directive. */
function kv(label: string, value: React.ReactNode, opts?: { mono?: boolean }): KVItem {
  const v = value === null || value === undefined || value === '' ? '—' : value;
  return { label, value: v, mono: opts?.mono };
}

// ── Component ────────────────────────────────────────────────────────────────

export function ShoppingListContent() {
  const { entity, availableActions, executeAction, getAction } = useEntityLensContext();
  const router = useRouter();

  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const get = <T = unknown>(key: string): T | undefined =>
    (entity?.[key] ?? payload[key]) as T | undefined;

  // Identity / header fields
  const title = get<string>('title') ?? get<string>('part_name') ?? 'Shopping List Item';
  const status = get<string>('status') ?? 'candidate';
  const urgency = get<string>('urgency') ?? get<string>('priority');
  const requesterName = get<string>('requester_name') ?? get<string>('created_by');
  const createdAt = get<string>('created_at');
  const requiredByDate = get<string>('required_by_date');
  const sourceNotes = get<string>('source_notes') ?? get<string>('description');
  const isCandidatePart = get<boolean>('is_candidate_part');
  const preferredSupplier = get<string>('preferred_supplier');

  const items = get<Array<Record<string, unknown>>>('items') ?? [];
  const item = items[0] ?? {};
  const itemField = <T = unknown>(key: string): T | undefined =>
    (item[key] ?? get<T>(key)) as T | undefined;

  const partNumber = itemField<string>('part_number');
  const manufacturer = itemField<string>('manufacturer');
  const unit = itemField<string>('unit');
  const sourceType = get<string>('source_type');
  const qtyRequested = itemField<number>('quantity_requested');
  const qtyApproved = itemField<number>('quantity_approved');
  const qtyOrdered = itemField<number>('quantity_ordered');
  const qtyReceived = itemField<number>('quantity_received');
  const qtyInstalled = itemField<number>('quantity_installed');
  const estimatedPrice = itemField<number>('estimated_unit_price');
  const orderLineNumber = itemField<number>('order_line_number');

  const approverName = get<string>('approver_name');
  const approvedAt = get<string>('approved_at');
  const approvalNotes = get<string>('approval_notes');
  const rejectedByName = get<string>('rejected_by_name');
  const rejectedAt = get<string>('rejected_at');
  const rejectionReason = get<string>('rejection_reason');
  const rejectionNotes = get<string>('rejection_notes');

  const fulfilledAt = get<string>('fulfilled_at');
  const installedAt = get<string>('installed_at');

  const promotedByName = get<string>('promoted_by_name');
  const promotedAt = get<string>('promoted_at');

  // Pure view computation — no DB change
  const projectedCost =
    qtyRequested != null && estimatedPrice != null
      ? qtyRequested * estimatedPrice
      : undefined;

  // Related entity nav rows (FK UUIDs → clickable rows via getEntityRoute).
  // Backend emits up to 6 possible FKs in related_entities.
  const relatedEntities = get<Array<Record<string, unknown>>>('related_entities') ?? [];

  function buildRow(entityType: string, matchLabel: string): DocRowItem | null {
    const match =
      relatedEntities.find(
        (e) =>
          e.entity_type === entityType &&
          (e.label as string | undefined) === matchLabel,
      ) ?? null;
    if (!match) return null;
    const id = match.entity_id as string | undefined;
    if (!id) return null;
    return {
      id,
      name: (match.label as string) ?? matchLabel,
      code: entityType,
      onClick: () =>
        router.push(
          getEntityRoute(
            entityType as Parameters<typeof getEntityRoute>[0],
            id,
          ),
        ),
    };
  }

  const linkedPartRow = buildRow('part', 'Linked Part');
  const linkedWORow = buildRow('work_order', 'Source Work Order');
  const linkedReceivingRow = buildRow('receiving', 'Source Receiving');
  const linkedPORow = buildRow('purchase_order', 'Linked Purchase Order');
  const installedEquipmentRow = buildRow('equipment', 'Installed to Equipment');
  const promotedPartRow = buildRow('part', 'Promoted Part');

  // Audit events from pms_shopping_list_state_history
  const history = get<Array<Record<string, unknown>>>('audit_history') ?? [];
  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  // Action popup plumbing
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

  const promoteAction = getAction('promote_candidate_to_part');

  function runAction(a: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean; disabled?: boolean }) {
    if (a.disabled) return;
    const hasFields = actionHasFields(a as Parameters<typeof actionHasFields>[0]);
    if (hasFields || a.requires_signature) {
      openPopup(a as Parameters<typeof openPopup>[0]);
    } else {
      executeAction(a.action_id);
    }
  }

  // Header pills + details
  const pills: PillDef[] = [{ label: fmt(status), variant: statusPillVariant(status) }];
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
  if (projectedCost != null) details.push({ label: 'Projected cost', value: formatMoney(projectedCost), mono: true });

  // SplitButton
  const approveAction = getAction('approve_shopping_list_item');
  const orderAction = getAction('mark_shopping_list_ordered');
  const primaryAction = approveAction ?? orderAction;
  const primaryLabel = primaryAction?.label ?? 'No Actions';
  const primaryDisabled = !primaryAction || (primaryAction.disabled ?? false);

  const handlePrimary = React.useCallback(async () => {
    if (!primaryAction) return;
    runAction(primaryAction as Parameters<typeof runAction>[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [primaryAction]);

  const DANGER_ACTIONS = new Set(['delete_shopping_item']);
  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryAction?.action_id)
    .map((a) => ({
      label: a.label,
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
      danger: DANGER_ACTIONS.has(a.action_id),
      onClick: () => runAction(a as Parameters<typeof runAction>[0]),
    }));

  // Lifecycle stepper
  const LIFECYCLE = [
    'candidate',
    'under_review',
    'approved',
    'ordered',
    'partially_fulfilled',
    'fulfilled',
    'installed',
  ] as const;
  const isRejected = status === 'rejected';
  const currentIdx = isRejected
    ? -1
    : LIFECYCLE.indexOf(status as typeof LIFECYCLE[number]);

  // Tab definitions
  const procurementCount = linkedPORow ? 1 : 0;
  const fulfilmentCount =
    (qtyReceived && qtyReceived > 0 ? 1 : 0) +
    (installedEquipmentRow || installedAt ? 1 : 0);
  const approvalCount =
    approverName || rejectedByName || approvalNotes || rejectionReason ? 1 : 0;

  const tabs: LensTab[] = [
    { key: 'details', label: 'Details' },
    { key: 'approval', label: 'Approval', count: approvalCount },
    {
      key: 'procurement',
      label: 'Procurement',
      count: procurementCount,
      disabled: !linkedPORow && qtyOrdered == null,
      disabledReason: 'No purchase order linked yet.',
    },
    {
      key: 'fulfilment',
      label: 'Fulfilment',
      count: fulfilmentCount,
      disabled:
        fulfilmentCount === 0 &&
        (qtyReceived ?? 0) === 0 &&
        !installedAt &&
        !fulfilledAt,
      disabledReason: 'Not yet received.',
    },
    {
      key: 'attachments',
      label: 'Attachments',
      count: 0,
      disabled: true,
      disabledReason: 'Photo upload + comments arrive in the next release.',
    },
    { key: 'audit', label: 'Audit', count: auditEvents.length },
  ];

  // Tab renderers

  function renderDetailsTab(): React.ReactNode {
    const detailItems: KVItem[] = [
      kv('Part Number', partNumber, { mono: true }),
      kv('Manufacturer', manufacturer),
      kv('Unit', unit),
      kv('Qty Requested', qtyRequested != null ? String(qtyRequested) : undefined),
      kv('Est. Unit Price', estimatedPrice != null ? formatMoney(estimatedPrice) : undefined, { mono: true }),
      kv('Projected Cost', projectedCost != null ? formatMoney(projectedCost) : undefined, { mono: true }),
      kv('Preferred Supplier', preferredSupplier),
    ];
    const sourceItems: KVItem[] = [
      kv('Source', sourceType ? fmt(sourceType) : undefined),
      kv('Reason / Notes', sourceNotes || 'No reason provided — click Update to add'),
    ];
    const linkedDocs: DocRowItem[] = [linkedPartRow, linkedWORow, linkedReceivingRow]
      .filter((r): r is DocRowItem => r !== null);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <KVSection title="Item Details" items={detailItems} />
        <KVSection title="Source & Context" items={sourceItems} />

        {isCandidatePart && !linkedPartRow && !promotedPartRow && (
          <CandidatePromotePanel
            promoteAction={promoteAction}
            onPromote={() =>
              promoteAction &&
              runAction(promoteAction as Parameters<typeof runAction>[0])
            }
          />
        )}

        {promotedPartRow && (
          <PromotedPartPanel
            promotedAt={promotedAt}
            promotedByName={promotedByName}
            row={promotedPartRow}
          />
        )}

        {linkedDocs.length > 0 && (
          <DocRowsSection title="Linked Entities" docs={linkedDocs} />
        )}
      </div>
    );
  }

  function renderApprovalTab(): React.ReactNode {
    if (status === 'candidate') {
      return <EmptyTab message="Awaiting HoD review — no approval decision yet." />;
    }
    const approvalItems: KVItem[] = [];
    if (approverName || approvedAt || approvalNotes || qtyApproved != null) {
      approvalItems.push(
        kv('Approved by', approverName),
        kv('Approved at', approvedAt ? formatDate(approvedAt) : undefined, { mono: true }),
        kv(
          'Qty Approved',
          qtyApproved != null
            ? `${qtyApproved}${qtyRequested != null ? ` / ${qtyRequested}` : ''}`
            : undefined,
        ),
        kv('Approval Notes', approvalNotes),
      );
    }
    const rejectionItems: KVItem[] = [];
    if (rejectedByName || rejectedAt || rejectionReason || rejectionNotes) {
      rejectionItems.push(
        kv('Rejected by', rejectedByName),
        kv('Rejected at', rejectedAt ? formatDate(rejectedAt) : undefined, { mono: true }),
        kv('Reason', rejectionReason),
        kv('Notes', rejectionNotes),
      );
    }
    if (approvalItems.length === 0 && rejectionItems.length === 0) {
      return <EmptyTab message="No approval data recorded yet." />;
    }
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {approvalItems.length > 0 && <KVSection title="Approval" items={approvalItems} />}
        {rejectionItems.length > 0 && <KVSection title="Rejection" items={rejectionItems} />}
      </div>
    );
  }

  function renderProcurementTab(): React.ReactNode {
    if (!linkedPORow && qtyOrdered == null) {
      return (
        <EmptyTab
          message={
            status === 'approved'
              ? 'Approved and awaiting purchase order.'
              : 'Procurement starts after approval.'
          }
        />
      );
    }
    const orderItems: KVItem[] = [
      kv('Line Number', orderLineNumber != null ? String(orderLineNumber) : undefined),
      kv('Qty Ordered', qtyOrdered != null ? String(qtyOrdered) : undefined),
    ];
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {linkedPORow ? (
          <DocRowsSection title="Linked Purchase Order" docs={[linkedPORow]} />
        ) : (
          <DiagnosticPanel message="Ordered flag is set but no purchase order linked. Ask the Purser to reconcile." />
        )}
        <KVSection title="Order Details" items={orderItems} />
      </div>
    );
  }

  function renderFulfilmentTab(): React.ReactNode {
    const anyFulfilment =
      (qtyReceived ?? 0) > 0 ||
      (qtyInstalled ?? 0) > 0 ||
      installedAt ||
      fulfilledAt ||
      linkedReceivingRow ||
      installedEquipmentRow;
    if (!anyFulfilment) {
      return <EmptyTab message="Not yet received." />;
    }
    const fulfilItems: KVItem[] = [
      kv(
        'Qty Received',
        qtyReceived != null
          ? `${qtyReceived}${qtyOrdered != null ? ` / ${qtyOrdered}` : ''}`
          : undefined,
      ),
      kv('Qty Installed', qtyInstalled != null ? String(qtyInstalled) : undefined),
      kv('Fulfilled at', fulfilledAt ? formatDate(fulfilledAt) : undefined, { mono: true }),
      kv('Installed at', installedAt ? formatDate(installedAt) : undefined, { mono: true }),
    ];
    const rows: DocRowItem[] = [linkedReceivingRow, installedEquipmentRow]
      .filter((r): r is DocRowItem => r !== null);
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <KVSection title="Receipt & Installation" items={fulfilItems} />
        {rows.length > 0 && <DocRowsSection title="Linked Entities" docs={rows} />}
      </div>
    );
  }

  function renderAttachmentsTab(): React.ReactNode {
    return (
      <EmptyTab message="Photo uploads + comments arrive in the next release — cohort-shared pms_attachments + pms_attachment_comments (PR #696)." />
    );
  }

  function renderAuditTab(): React.ReactNode {
    if (auditEvents.length === 0) {
      return <EmptyTab message="No audit events recorded yet." />;
    }
    return <AuditTrailSection events={auditEvents} />;
  }

  function renderTabBody(key: string): React.ReactNode {
    switch (key) {
      case 'details':
        return renderDetailsTab();
      case 'approval':
        return renderApprovalTab();
      case 'procurement':
        return renderProcurementTab();
      case 'fulfilment':
        return renderFulfilmentTab();
      case 'attachments':
        return renderAttachmentsTab();
      case 'audit':
        return renderAuditTab();
      default:
        return <EmptyTab message="Coming soon." />;
    }
  }

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

      <ScrollReveal>
        {isRejected ? (
          <RejectedBanner reason={rejectionReason} />
        ) : (
          <LifecycleStepper lifecycle={LIFECYCLE} currentIdx={currentIdx} />
        )}
      </ScrollReveal>

      <ScrollReveal>
        <LensTabBar tabs={tabs} defaultActiveKey="details" renderBody={renderTabBody} />
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

// ── Inline presentational helpers ────────────────────────────────────────────

function EmptyTab({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '32px 16px',
        textAlign: 'center',
        color: 'var(--txt3)',
        fontSize: 13,
        fontFamily: 'var(--font-sans)',
      }}
    >
      {message}
    </div>
  );
}

function DiagnosticPanel({ message }: { message: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 14px',
        borderRadius: 8,
        background: 'var(--amber-bg)',
        border: '1px solid var(--amber-border)',
        color: 'var(--amber)',
        fontSize: 12.5,
        fontFamily: 'var(--font-sans)',
      }}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>{message}</span>
    </div>
  );
}

function RejectedBanner({ reason }: { reason?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 16px',
        margin: '16px 0 8px',
        borderRadius: 8,
        background: 'var(--red-bg)',
        border: '1px solid var(--red-border)',
      }}
    >
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: 'var(--red)',
          boxShadow: '0 0 0 4px var(--red-bg)',
          flexShrink: 0,
        }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.03em',
            color: 'var(--red)',
            textTransform: 'uppercase',
          }}
        >
          Rejected
        </span>
        {reason && (
          <span style={{ fontSize: 12, color: 'var(--txt2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {reason}
          </span>
        )}
      </div>
    </div>
  );
}

function LifecycleStepper({
  lifecycle,
  currentIdx,
}: {
  lifecycle: ReadonlyArray<string>;
  currentIdx: number;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, padding: '16px 0', marginBottom: 8 }}>
      {lifecycle.map((step, i) => {
        const isCompleted = currentIdx >= 0 && i < currentIdx;
        const isActive = i === currentIdx;
        return (
          <React.Fragment key={step}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 0 }}>
              <div
                style={{
                  width: isActive ? 12 : 10,
                  height: isActive ? 12 : 10,
                  borderRadius: '50%',
                  background: isCompleted || isActive ? 'var(--green)' : 'none',
                  border: `2px solid ${isCompleted || isActive ? 'var(--green)' : 'var(--txt-ghost)'}`,
                  boxShadow: isActive ? '0 0 0 4px var(--green-bg)' : 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {isCompleted && (
                  <svg width="8" height="8" viewBox="0 0 12 12" fill="none" stroke="var(--surface-base)" strokeWidth="2" strokeLinecap="round">
                    <polyline points="2.5 6 5 8.5 9.5 3.5" />
                  </svg>
                )}
              </div>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: isActive ? 600 : 500,
                  letterSpacing: '0.03em',
                  color: isActive ? 'var(--green)' : isCompleted ? 'var(--txt3)' : 'var(--txt-ghost)',
                  marginTop: 8,
                  textTransform: 'uppercase',
                  whiteSpace: 'nowrap',
                }}
              >
                {fmt(step)}
              </span>
            </div>
            {i < lifecycle.length - 1 && (
              <div
                style={{
                  flex: 1,
                  height: 2,
                  background: isCompleted ? 'var(--green)' : 'var(--border-sub)',
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
  );
}

function CandidatePromotePanel({
  promoteAction,
  onPromote,
}: {
  promoteAction:
    | { action_id: string; label: string; disabled?: boolean; disabled_reason?: string | null }
    | null;
  onPromote: () => void;
}) {
  const disabled = !promoteAction || (promoteAction.disabled ?? false);
  const reason = promoteAction?.disabled_reason ?? undefined;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '12px 16px',
        borderRadius: 8,
        background: 'var(--surface)',
        border: '1px solid var(--border-faint)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--txt)', fontFamily: 'var(--font-sans)' }}>
          Candidate part — not in the catalogue
        </span>
        <span style={{ fontSize: 11.5, color: 'var(--txt2)', fontFamily: 'var(--font-sans)' }}>
          An Engineer can promote this request to a permanent catalogued part once it&apos;s approved.
        </span>
      </div>
      <button
        onClick={onPromote}
        disabled={disabled}
        title={disabled ? reason : undefined}
        style={{
          appearance: 'none',
          border: '1px solid var(--mark)',
          background: disabled ? 'var(--surface)' : 'var(--teal-bg)',
          color: 'var(--mark)',
          padding: '6px 12px',
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 600,
          fontFamily: 'var(--font-sans)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        Promote to Catalogue
      </button>
    </div>
  );
}

function PromotedPartPanel({
  promotedAt,
  promotedByName,
  row,
}: {
  promotedAt?: string;
  promotedByName?: string;
  row: DocRowItem;
}) {
  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: 8,
        background: 'var(--green-bg)',
        border: '1px solid var(--green-border)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--green)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
          Promoted to catalogue
        </span>
        {promotedAt && (
          <span style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
            {formatDate(promotedAt)}
            {promotedByName ? ` · by ${promotedByName}` : ''}
          </span>
        )}
      </div>
      <DocRowsSection title="" docs={[row]} />
    </div>
  );
}
