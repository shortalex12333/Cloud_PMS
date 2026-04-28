'use client';

/**
 * ReceivingLinkedPO — side-by-side reconciliation against the originating
 * purchase order. Closes the procurement loop:
 *   shopping_list  → purchase_order  → receiving (you are here)
 *
 * For each PO line we pair it to a receiving line by part_id (or by
 * description fallback). Render columns:
 *
 *   Part / Description | Ordered | Received | Δ | Unit $
 *
 * Footer:
 *   Order total / Received total / Outstanding
 *
 * Render rules:
 *   - Section is hidden entirely when there is no linked PO.
 *   - "Visit PO" link sits in the section-header action slot.
 *   - Token-only styling. No new tokens.
 *   - Mono numbers.
 *
 * Backend contract: see `entity_routes.py:get_receiving_entity` —
 * the response includes `po_id`, `po_number`, and `linked_po_items[]`.
 * Receiving items come from the existing `items[]` array.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { CollapsibleSection } from '../CollapsibleSection';
import { getEntityRoute } from '@/lib/entityRoutes';

// ── Types ──────────────────────────────────────────────────────────────────

export interface POItem {
  id: string;
  part_id?: string | null;
  description?: string | null;
  quantity_ordered: number;
  quantity_received?: number | null; // already rolled up across all receivings on the PO
  unit_price?: number | null;
}

export interface ReceivingLineSummary {
  part_id?: string | null;
  description?: string | null;
  quantity_received: number;
}

export interface ReceivingLinkedPOProps {
  poId: string | null;
  poNumber: string | null;
  poItems: POItem[];
  /** Items on THIS receiving (used to compare what we received this round). */
  receivingItems: ReceivingLineSummary[];
  /** Currency to render alongside money values. */
  currency?: string | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtQty(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return Number.isInteger(Number(n)) ? String(Number(n)) : Number(n).toFixed(2);
}

function fmtMoney(n: number | null | undefined, ccy?: string | null): string {
  if (n === null || n === undefined) return '—';
  const num = Number(n).toFixed(2);
  return ccy ? `${ccy} ${num}` : num;
}

/**
 * Build the merged grid: one row per PO line. The "received this delivery"
 * count comes from this receiving's items, matched first by part_id then by
 * description fallback. Items the supplier sent that AREN'T on the PO are
 * surfaced as extra rows at the bottom under "Not on PO".
 */
function reconcile(poItems: POItem[], rcvItems: ReceivingLineSummary[]) {
  type Row = {
    key: string;
    label: string;
    quantityOrdered: number;
    quantityReceived: number;
    unitPrice: number | null;
    onPO: boolean;
  };

  const rows: Row[] = poItems.map((p) => {
    let received = 0;
    for (const r of rcvItems) {
      if (p.part_id && r.part_id && p.part_id === r.part_id) {
        received += Number(r.quantity_received ?? 0);
        continue;
      }
      if (!p.part_id && r.description && p.description && r.description.trim() === p.description.trim()) {
        received += Number(r.quantity_received ?? 0);
      }
    }
    return {
      key: p.id,
      label: p.description ?? p.part_id ?? 'Item',
      quantityOrdered: Number(p.quantity_ordered),
      quantityReceived: received,
      unitPrice: p.unit_price === null || p.unit_price === undefined ? null : Number(p.unit_price),
      onPO: true,
    };
  });

  // Items on this receiving with no match on the PO
  const matchedKeys = new Set<string>();
  for (const p of poItems) {
    for (const r of rcvItems) {
      if (p.part_id && r.part_id && p.part_id === r.part_id) {
        matchedKeys.add(`${r.part_id}|${r.description ?? ''}`);
      } else if (!p.part_id && r.description && p.description && r.description.trim() === p.description.trim()) {
        matchedKeys.add(`${r.part_id ?? ''}|${r.description ?? ''}`);
      }
    }
  }
  for (const r of rcvItems) {
    const k = `${r.part_id ?? ''}|${r.description ?? ''}`;
    if (matchedKeys.has(k)) continue;
    rows.push({
      key: `extra-${k}-${rows.length}`,
      label: r.description ?? r.part_id ?? 'Unmatched item',
      quantityOrdered: 0,
      quantityReceived: Number(r.quantity_received ?? 0),
      unitPrice: null,
      onPO: false,
    });
  }

  const orderTotal = rows
    .filter((r) => r.onPO)
    .reduce((acc, r) => acc + (r.unitPrice ?? 0) * r.quantityOrdered, 0);
  const receivedTotal = rows
    .filter((r) => r.onPO)
    .reduce((acc, r) => acc + (r.unitPrice ?? 0) * r.quantityReceived, 0);
  const outstanding = orderTotal - receivedTotal;

  return { rows, orderTotal, receivedTotal, outstanding };
}

// ── Section icon (chain link — procurement-loop metaphor) ──────────────────

const SECTION_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M6.5 9.5l3-3M5 11a2.5 2.5 0 010-3.5l1.5-1.5M11 5a2.5 2.5 0 010 3.5L9.5 10"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
);

// ── Component ──────────────────────────────────────────────────────────────

export function ReceivingLinkedPO({
  poId,
  poNumber,
  poItems,
  receivingItems,
  currency,
}: ReceivingLinkedPOProps) {
  const router = useRouter();
  const { rows, orderTotal, receivedTotal, outstanding } = React.useMemo(
    () => reconcile(poItems, receivingItems),
    [poItems, receivingItems],
  );

  // No PO linked → don't render the section at all (per philosophy: every
  // element earns its place — empty state would be noise).
  if (!poId || !poNumber || poItems.length === 0) return null;

  const visitPO = () => {
    router.push(getEntityRoute('purchase-orders' as Parameters<typeof getEntityRoute>[0], poId));
  };

  return (
    <CollapsibleSection
      id="sec-linked-po"
      title="Linked Purchase Order"
      count={poItems.length}
      icon={SECTION_ICON}
      action={{ label: `Visit ${poNumber} →`, onClick: visitPO, testid: 'linked-po-visit' }}
    >
      <div role="table" aria-label={`Reconciliation against ${poNumber}`} style={{ width: '100%' }}>
        {/* Header */}
        <div
          role="row"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 70px 70px 60px 100px',
            gap: 8,
            alignItems: 'center',
            minHeight: 28,
            padding: '6px 8px',
            borderBottom: '1px solid var(--border-sub)',
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--txt3)',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <span role="columnheader">Part / Description</span>
          <span role="columnheader" style={{ textAlign: 'right' }}>Ordered</span>
          <span role="columnheader" style={{ textAlign: 'right' }}>Received</span>
          <span role="columnheader" style={{ textAlign: 'right' }}>Δ</span>
          <span role="columnheader" style={{ textAlign: 'right' }}>Unit</span>
        </div>

        {rows.map((row) => {
          const delta = row.quantityReceived - row.quantityOrdered;
          const deltaColour =
            delta === 0 ? 'var(--txt3)'
            : delta < 0 ? 'var(--red)'
            : 'var(--amber)';

          return (
            <div
              key={row.key}
              role="row"
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 70px 70px 60px 100px',
                gap: 8,
                alignItems: 'center',
                minHeight: 36,
                padding: '6px 8px',
                borderBottom: '1px solid var(--border-faint)',
                opacity: row.onPO ? 1 : 0.85,
              }}
            >
              <span
                role="cell"
                style={{
                  fontSize: 13,
                  color: 'var(--txt)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {row.label}
                {!row.onPO && (
                  <span
                    style={{
                      marginLeft: 6,
                      fontSize: 9,
                      fontWeight: 600,
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase',
                      color: 'var(--amber)',
                      background: 'var(--amber-bg)',
                      border: '1px solid var(--amber-border)',
                      padding: '0 4px',
                      borderRadius: 3,
                    }}
                  >
                    Not on PO
                  </span>
                )}
              </span>
              <span role="cell" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt2)' }}>
                {row.onPO ? fmtQty(row.quantityOrdered) : '—'}
              </span>
              <span role="cell" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt)', fontWeight: 500 }}>
                {fmtQty(row.quantityReceived)}
              </span>
              <span role="cell" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: deltaColour }}>
                {row.onPO ? (delta > 0 ? `+${fmtQty(delta)}` : fmtQty(delta)) : '—'}
              </span>
              <span role="cell" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--txt3)' }}>
                {fmtMoney(row.unitPrice, currency)}
              </span>
            </div>
          );
        })}

        {/* Footer rollup */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 200px',
            gap: 8,
            padding: '12px 8px 4px',
            fontSize: 12,
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span />
          <div style={{ display: 'grid', rowGap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--txt3)' }}>
              <span>Order total</span>
              <span style={{ color: 'var(--txt2)' }}>{fmtMoney(orderTotal, currency)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--txt3)' }}>
              <span>Received total</span>
              <span style={{ color: 'var(--txt2)' }}>{fmtMoney(receivedTotal, currency)}</span>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                color: outstanding > 0 ? 'var(--amber)' : 'var(--txt)',
                fontWeight: 600,
                borderTop: '1px solid var(--border-sub)',
                paddingTop: 4,
                marginTop: 2,
              }}
            >
              <span>Outstanding</span>
              <span>{fmtMoney(outstanding, currency)}</span>
            </div>
          </div>
        </div>
      </div>
    </CollapsibleSection>
  );
}
