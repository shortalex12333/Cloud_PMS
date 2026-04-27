'use client';

/**
 * ReceivingDiscrepancies — auto-aggregated list of issues found while
 * reconciling this delivery. Two sources merged into a single ruled
 * section:
 *
 *   1. Per-line dispositions on pms_receiving_items where the crew clicked
 *      [⚠ Short] / [⚠ Damaged] / [⚠ Wrong Item] / [⚠ Over]. Surfaced as
 *      structured rows with the part / qty / reason.
 *
 *   2. Free-text flag_discrepancy events from ledger_events
 *      (entity_type='receiving' AND event_category='discrepancy'). These are
 *      whole-receiving notes — not tied to a specific line. Surfaced as
 *      annotated rows with actor name+role, timestamp, payload.
 *
 * Per philosophy: hide the section entirely when there is nothing to show.
 * Empty Discrepancies is just noise.
 */

import * as React from 'react';
import { CollapsibleSection } from '../CollapsibleSection';

// ── Types ──────────────────────────────────────────────────────────────────

export type DiscrepancyKind = 'short' | 'over' | 'damaged' | 'wrong_item' | 'partial' | 'missing';

export interface LineDiscrepancy {
  source: 'line';
  itemId: string;
  partLabel: string;            // "@ HVC-0106-314 Compressor Clutch" or freeform desc
  kind: DiscrepancyKind;
  expected: number | null;
  received: number;
  rejected: number;             // quantity_rejected from pms_receiving_items
}

export interface FlagDiscrepancy {
  source: 'flag';
  ledgerId: string;
  kind: DiscrepancyKind;
  description: string;
  actor: string | null;         // already resolved name+role server-side
  timestamp: string;            // ISO from ledger_events.created_at
  affectedItems?: Array<Record<string, unknown>>;
}

export type Discrepancy = LineDiscrepancy | FlagDiscrepancy;

export interface ReceivingDiscrepanciesProps {
  entries: Discrepancy[];
  onDraftEmail?: () => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtQty(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return Number.isInteger(Number(n)) ? String(Number(n)) : Number(n).toFixed(2);
}

function fmtRelative(iso: string): string {
  if (!iso) return '';
  try {
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return '';
    const seconds = Math.max(1, Math.floor((Date.now() - t) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  } catch {
    return '';
  }
}

const KIND_PALETTE: Record<DiscrepancyKind, { color: string; bg: string; border: string; label: string }> = {
  short:      { color: 'var(--red)',   bg: 'var(--red-bg)',   border: 'var(--red-border)',   label: 'SHORT' },
  missing:    { color: 'var(--red)',   bg: 'var(--red-bg)',   border: 'var(--red-border)',   label: 'MISSING' },
  damaged:    { color: 'var(--red)',   bg: 'var(--red-bg)',   border: 'var(--red-border)',   label: 'DAMAGED' },
  wrong_item: { color: 'var(--red)',   bg: 'var(--red-bg)',   border: 'var(--red-border)',   label: 'WRONG ITEM' },
  partial:    { color: 'var(--amber)', bg: 'var(--amber-bg)', border: 'var(--amber-border)', label: 'PARTIAL' },
  over:       { color: 'var(--amber)', bg: 'var(--amber-bg)', border: 'var(--amber-border)', label: 'OVER' },
};

function KindBadge({ kind }: { kind: DiscrepancyKind }) {
  const p = KIND_PALETTE[kind];
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
        background: p.bg,
        color: p.color,
        border: `1px solid ${p.border}`,
      }}
    >
      ⚠ {p.label}
    </span>
  );
}

// ── Section icon (warning triangle) ────────────────────────────────────────

const SECTION_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M8 1.5l6.5 11.5h-13L8 1.5z"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinejoin="round"
    />
    <path d="M8 5.5v4M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

// ── Component ──────────────────────────────────────────────────────────────

export function ReceivingDiscrepancies({ entries, onDraftEmail }: ReceivingDiscrepanciesProps) {
  // Per philosophy: empty discrepancies = hide the section entirely.
  if (entries.length === 0) return null;

  return (
    <CollapsibleSection
      id="sec-discrepancies"
      title="Discrepancies"
      count={entries.length}
      icon={SECTION_ICON}
      action={onDraftEmail ? { label: 'Draft Email to Supplier', onClick: onDraftEmail, testid: 'draft-supplier-email' } : undefined}
    >
      <div role="list" aria-label="Discrepancy entries" style={{ display: 'grid', rowGap: 8 }}>
        {entries.map((entry, idx) => {
          if (entry.source === 'line') {
            const shortBy = entry.expected !== null ? entry.expected - entry.received : 0;
            return (
              <div
                key={`line-${entry.itemId}-${idx}`}
                role="listitem"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '110px 1fr',
                  gap: 12,
                  padding: '10px 12px',
                  borderLeft: `2px solid ${KIND_PALETTE[entry.kind].color}`,
                  borderTop: '1px solid var(--border-faint)',
                  borderBottom: '1px solid var(--border-faint)',
                  background: 'var(--surface-elevated)',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'flex-start', paddingTop: 1 }}>
                  <KindBadge kind={entry.kind} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: 'var(--txt)',
                      lineHeight: 1.4,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {entry.partLabel}
                  </div>
                  <div
                    style={{
                      fontSize: 11.5,
                      color: 'var(--txt3)',
                      marginTop: 2,
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    Expected {fmtQty(entry.expected)} · Received {fmtQty(entry.received)}
                    {shortBy > 0 ? ` · Short by ${fmtQty(shortBy)}` : ''}
                    {entry.rejected > 0 ? ` · Rejected ${fmtQty(entry.rejected)}` : ''}
                  </div>
                </div>
              </div>
            );
          }

          // Flag entry (free-text from crew)
          return (
            <div
              key={`flag-${entry.ledgerId}`}
              role="listitem"
              style={{
                display: 'grid',
                gridTemplateColumns: '110px 1fr',
                gap: 12,
                padding: '10px 12px',
                borderLeft: `2px solid ${KIND_PALETTE[entry.kind].color}`,
                borderTop: '1px solid var(--border-faint)',
                borderBottom: '1px solid var(--border-faint)',
                background: 'var(--surface-elevated)',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'flex-start', paddingTop: 1 }}>
                <KindBadge kind={entry.kind} />
              </span>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    color: 'var(--txt)',
                    lineHeight: 1.45,
                  }}
                >
                  {entry.description}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: 'var(--txt3)',
                    marginTop: 4,
                    fontFamily: 'var(--font-sans)',
                  }}
                >
                  {entry.actor ?? 'Unknown'} · <span style={{ fontFamily: 'var(--font-mono)' }}>{fmtRelative(entry.timestamp)}</span>
                  {entry.affectedItems && entry.affectedItems.length > 0 && (
                    <> · {entry.affectedItems.length} affected line{entry.affectedItems.length === 1 ? '' : 's'}</>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </CollapsibleSection>
  );
}
