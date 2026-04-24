'use client';

/**
 * ReceivingPackingList — the *hero* section of the receiving lens.
 *
 * Renders the line items as a reconciliation grid: one row per
 * `pms_receiving_items`, with Expected | Received | Δ | Unit $ | Status
 * columns. Subtotal / tax / total rollup at the bottom computed client-side
 * from the items (compared against stored header totals in a follow-up).
 *
 * Follows the canonical design philosophy (`.claude/skills/celeste-design-philosophy`):
 *   - Scroll-document metaphor — sits inside a `CollapsibleSection`, ruled line
 *     above, 14px/600/uppercase heading. NOT a tab, NOT a card.
 *   - Mono for numbers (quantities, prices, Δ). Inter elsewhere.
 *   - Token-only styling, no new tokens, no hex, no raw rgba.
 *   - Dark-mode primary — every colour via CSS var.
 *   - 44px min row height for touch.
 *
 * MVP scope (PR-A):
 *   - Read-only reconciliation grid.
 *   - Δ column computed client-side from (received − expected).
 *   - Status glyph derived from Δ (matched / short / over / pending).
 *   - Subtotal / tax / total footer rollup.
 *
 * Follow-up (PR-A2):
 *   - 3-column migration on pms_receiving_items (quantity_accepted,
 *     quantity_rejected, disposition) + interactive per-row accept/reject
 *     controls calling `adjust_receiving_item`.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';
import { getEntityRoute } from '@/lib/entityRoutes';

// ── Types ──────────────────────────────────────────────────────────────────

export interface PackingItem {
  id: string;
  /** Part catalog link. When set, row is click-through to the part lens. */
  partId?: string | null;
  partCode?: string | null;      // e.g. HVC-0109-813
  partName?: string | null;      // e.g. "AC Filter 20x20"
  /** Free-text fallback when partId is null (e.g. "Loose cardboard packaging") */
  description?: string | null;
  manufacturer?: string | null;
  quantityExpected?: number | null;
  quantityReceived: number;      // NOT NULL in DB
  unitPrice?: number | null;
  currency?: string | null;
}

export interface ReceivingPackingListProps {
  items: PackingItem[];
  /** Header-level money fields — shown alongside computed rollup for comparison. */
  storedSubtotal?: number | null;
  storedTaxTotal?: number | null;
  storedTotal?: number | null;
  headerCurrency?: string | null;
  /** Section-header action (HOD-only). When omitted, no action button. */
  onAddItem?: () => void;
}

// ── Formatters ─────────────────────────────────────────────────────────────

function fmtQty(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  // strip trailing .00 on whole numbers, keep 2dp otherwise
  return Number.isInteger(Number(n)) ? String(Number(n)) : Number(n).toFixed(2);
}

function fmtMoney(n: number | null | undefined, ccy?: string | null): string {
  if (n === null || n === undefined) return '—';
  const num = Number(n).toFixed(2);
  return ccy ? `${ccy} ${num}` : num;
}

function computeDelta(item: PackingItem): number | null {
  if (item.quantityExpected === null || item.quantityExpected === undefined) return null;
  return Number(item.quantityReceived) - Number(item.quantityExpected);
}

type Disposition = 'matched' | 'short' | 'over' | 'pending';

function deriveDisposition(item: PackingItem): Disposition {
  const d = computeDelta(item);
  if (d === null) return 'pending';
  if (d === 0) return 'matched';
  if (d < 0) return 'short';
  return 'over';
}

// ── Status glyph (mirrors StatusPill pattern) ──────────────────────────────

function StatusGlyph({ disposition }: { disposition: Disposition }) {
  const label = {
    matched: '✓ Matched',
    short: '⚠ Short',
    over: '⚠ Over',
    pending: '○ Pending',
  }[disposition];

  const palette = {
    matched: { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
    short:   { bg: 'var(--red-bg)',   color: 'var(--red)',   border: 'var(--red-border)' },
    over:    { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
    pending: { bg: 'var(--neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
  }[disposition];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 17,
        padding: '0 6px',
        borderRadius: 3,
        fontSize: 8.5,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        background: palette.bg,
        color: palette.color,
        border: `1px solid ${palette.border}`,
      }}
    >
      {label}
    </span>
  );
}

// ── Section icon (clipboard-check — reconciliation metaphor) ───────────────

const SECTION_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="3" y="2" width="10" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
    <path d="M6 1.5h4v2H6z" stroke="currentColor" strokeWidth="1.3" />
    <path d="M6 8l1.5 1.5L11 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ── Component ──────────────────────────────────────────────────────────────

export function ReceivingPackingList({
  items,
  storedSubtotal,
  storedTaxTotal,
  storedTotal,
  headerCurrency,
  onAddItem,
}: ReceivingPackingListProps) {
  const router = useRouter();

  // ── Rollup ───────────────────────────────────────────────────────────────
  const computed = React.useMemo(() => {
    let sub = 0;
    for (const it of items) {
      const price = it.unitPrice ?? 0;
      sub += Number(price) * Number(it.quantityReceived);
    }
    return { subtotal: sub };
  }, [items]);

  // Progress = share of lines that are NOT pending
  const resolvedCount = items.filter((i) => deriveDisposition(i) !== 'pending').length;
  const progress = items.length > 0 ? (resolvedCount / items.length) * 100 : 0;

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <CollapsibleSection
      id="sec-packing-list"
      title="Packing List"
      count={items.length}
      icon={SECTION_ICON}
      action={onAddItem ? { label: '+ Add Line Item', onClick: onAddItem, testid: 'packing-add-item' } : undefined}
    >
      {items.length > 0 && (
        <div className={styles.progressBar}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>
      )}

      {items.length === 0 ? (
        <div className={styles.emptyState}>No line items yet. Add items to begin reconciliation.</div>
      ) : (
        <div
          role="table"
          aria-label="Packing list reconciliation"
          style={{ width: '100%' }}
        >
          {/* Header row */}
          <div
            role="row"
            style={{
              display: 'grid',
              gridTemplateColumns: '28px 1fr 60px 60px 60px 90px 110px',
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
            <span role="columnheader">#</span>
            <span role="columnheader">Part / Description</span>
            <span role="columnheader" style={{ textAlign: 'right' }}>Exp</span>
            <span role="columnheader" style={{ textAlign: 'right' }}>Rcvd</span>
            <span role="columnheader" style={{ textAlign: 'right' }}>Δ</span>
            <span role="columnheader" style={{ textAlign: 'right' }}>Unit</span>
            <span role="columnheader">Status</span>
          </div>

          {/* Body rows */}
          {items.map((item, idx) => {
            const disposition = deriveDisposition(item);
            const delta = computeDelta(item);
            const deltaColour =
              disposition === 'matched' ? 'var(--txt3)'
              : disposition === 'short'  ? 'var(--red)'
              : disposition === 'over'   ? 'var(--amber)'
              : 'var(--txt-ghost)';

            const clickable = !!item.partId;
            const onRowClick = clickable
              ? () => router.push(getEntityRoute('parts' as Parameters<typeof getEntityRoute>[0], item.partId as string))
              : undefined;

            return (
              <div
                key={item.id}
                role="row"
                onClick={onRowClick}
                onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter') onRowClick(); } : undefined}
                tabIndex={clickable ? 0 : undefined}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '28px 1fr 60px 60px 60px 90px 110px',
                  gap: 8,
                  alignItems: 'center',
                  minHeight: 44,
                  padding: '8px 8px',
                  borderBottom: '1px solid var(--border-faint)',
                  cursor: clickable ? 'pointer' : 'default',
                  transition: 'background 60ms',
                }}
                onMouseEnter={clickable ? (e) => { (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-hover)'; } : undefined}
                onMouseLeave={clickable ? (e) => { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; } : undefined}
              >
                {/* # */}
                <span
                  role="cell"
                  style={{
                    fontSize: 10,
                    color: 'var(--txt-ghost)',
                    fontFamily: 'var(--font-mono)',
                    textAlign: 'right',
                  }}
                >
                  {idx + 1}
                </span>

                {/* Part / Description */}
                <span role="cell" style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      color: 'var(--txt)',
                      lineHeight: 1.4,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {item.partCode && (
                      <span
                        style={{
                          color: 'var(--mark)',
                          fontSize: 11,
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 500,
                          marginRight: 6,
                        }}
                      >
                        {item.partCode}
                      </span>
                    )}
                    {item.partName || item.description || '—'}
                  </div>
                  {item.manufacturer && (
                    <div
                      style={{
                        fontSize: 10.5,
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--txt3)',
                        marginTop: 1,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {item.manufacturer}
                    </div>
                  )}
                </span>

                {/* Expected */}
                <span
                  role="cell"
                  style={{
                    textAlign: 'right',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                    color: 'var(--txt2)',
                  }}
                >
                  {fmtQty(item.quantityExpected)}
                </span>

                {/* Received */}
                <span
                  role="cell"
                  style={{
                    textAlign: 'right',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                    color: 'var(--txt)',
                    fontWeight: 500,
                  }}
                >
                  {fmtQty(item.quantityReceived)}
                </span>

                {/* Δ */}
                <span
                  role="cell"
                  style={{
                    textAlign: 'right',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                    color: deltaColour,
                    fontWeight: disposition === 'matched' ? 400 : 500,
                  }}
                >
                  {delta === null ? '—' : (delta > 0 ? `+${fmtQty(delta)}` : fmtQty(delta))}
                </span>

                {/* Unit Price */}
                <span
                  role="cell"
                  style={{
                    textAlign: 'right',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11.5,
                    color: 'var(--txt3)',
                  }}
                >
                  {fmtMoney(item.unitPrice, item.currency ?? headerCurrency)}
                </span>

                {/* Status */}
                <span role="cell">
                  <StatusGlyph disposition={disposition} />
                </span>
              </div>
            );
          })}

          {/* Footer rollup */}
          <div
            role="row"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 160px',
              gap: 8,
              padding: '16px 8px 8px',
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span />
            <div style={{ display: 'grid', rowGap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--txt3)' }}>
                <span>Subtotal (computed)</span>
                <span style={{ color: 'var(--txt2)' }}>
                  {fmtMoney(computed.subtotal, headerCurrency)}
                </span>
              </div>
              {storedSubtotal !== null && storedSubtotal !== undefined && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--txt-ghost)' }}>
                  <span>Subtotal (header)</span>
                  <span>{fmtMoney(storedSubtotal, headerCurrency)}</span>
                </div>
              )}
              {storedTaxTotal !== null && storedTaxTotal !== undefined && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--txt-ghost)' }}>
                  <span>Tax</span>
                  <span>{fmtMoney(storedTaxTotal, headerCurrency)}</span>
                </div>
              )}
              {storedTotal !== null && storedTotal !== undefined && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    color: 'var(--txt)',
                    fontWeight: 600,
                    borderTop: '1px solid var(--border-sub)',
                    paddingTop: 4,
                    marginTop: 2,
                  }}
                >
                  <span>Total</span>
                  <span>{fmtMoney(storedTotal, headerCurrency)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </CollapsibleSection>
  );
}
