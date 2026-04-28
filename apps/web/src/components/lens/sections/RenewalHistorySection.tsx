'use client';

/**
 * RenewalHistorySection — prior versions of the current entity (certificate or
 * document). Each row represents a superseded version; clicking the row opens
 * that version's lens.
 *
 * Per doc_cert_ux_change.md:
 *   - Prior rows show the same metadata as the current (issue date, edited-by
 *     user+role, expiry date, name, etc.).
 *   - Opening a prior version renders a NEW lens card, with a banner at the
 *     top: "This is an old version, click here to view superseding …".
 *     The banner itself is rendered by the parent lens (not this section);
 *     this section only displays the list.
 *
 * Shared between certificate and document lenses. Generic over the metadata
 * shape via string-valued cells.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface RenewalHistoryPeriod {
  /** UUID of the prior entity (cert/doc row). Used for navigation. */
  id: string;
  /** Display number/name — e.g. "EPT-2025-5664" for cert, "Rev 2 — v4.pdf" for doc. */
  label: string;
  /** Secondary context line — typically issue or created date + status. */
  period: string;
  /** Resolved name of the user who last edited this version. */
  actor_name?: string | null;
  /** Resolved role of the editor. */
  actor_role?: string | null;
  /** Free-text summary of what this version contained or why it was superseded. */
  summary?: string | null;
  /** Whether this version is currently active. False for all history rows. */
  is_active?: boolean;
}

export interface RenewalHistorySectionProps {
  periods: RenewalHistoryPeriod[];
  /** Called with the prior version's id when the row is clicked. */
  onNavigate?: (periodId: string) => void;
  defaultCollapsed?: boolean;
  title?: string;
}

export function RenewalHistorySection({
  periods,
  onNavigate,
  defaultCollapsed = true,
  title = 'Renewal History',
}: RenewalHistorySectionProps) {
  return (
    <CollapsibleSection
      id={`sec-${title.toLowerCase().replace(/\s+/g, '-')}`}
      title={title}
      count={periods.length}
      defaultCollapsed={defaultCollapsed}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M3 8a5 5 0 0 1 8.5-3.5L13 3v3h-3M13 8a5 5 0 0 1-8.5 3.5L3 13v-3h3"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      }
    >
      {periods.length === 0 ? (
        <div className={styles.emptyState}>No prior versions.</div>
      ) : (
        <div role="list">
          {periods.map((p) => (
            <button
              type="button"
              key={p.id}
              role="listitem"
              onClick={() => onNavigate?.(p.id)}
              disabled={!onNavigate}
              style={{
                width: '100%',
                display: 'block',
                textAlign: 'left',
                background: 'transparent',
                border: 0,
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--border-faint)',
                cursor: onNavigate ? 'pointer' : 'default',
                color: 'var(--text-primary)',
                transition: 'background var(--duration-fast) var(--ease-out)',
              }}
              onMouseEnter={(e) => {
                if (onNavigate) e.currentTarget.style.background = 'var(--surface-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 'var(--space-3)' }}>
                <span style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-body-strong)' }}>
                  {p.label}
                </span>
                <span style={{ fontSize: 'var(--font-size-caption)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                  {p.period}
                </span>
              </div>
              {(p.actor_name || p.summary) && (
                <div
                  style={{
                    marginTop: 4,
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {p.actor_name && (
                    <span>
                      {p.actor_name}
                      {p.actor_role ? ` · ${p.actor_role.replace(/_/g, ' ')}` : ''}
                    </span>
                  )}
                  {p.actor_name && p.summary && <span aria-hidden> — </span>}
                  {p.summary && <span>{p.summary}</span>}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </CollapsibleSection>
  );
}

/**
 * SupersededBanner — renders at the top of a lens card when the user is
 * viewing a prior version. Exported separately so both cert and doc lenses
 * can drop it in above the metadata strip.
 *
 * Per spec: "This is an old version, click here to view superseding …"
 */
export interface SupersededBannerProps {
  /** Entity-type label for the link text, e.g. "certificate" or "document". */
  entityLabel: string;
  /** Called when the banner link is clicked. Parent routes to the current version's lens. */
  onViewCurrent: () => void;
  /** Optional: short identifier (e.g. current cert's number) for context. */
  currentRef?: string | null;
}

export function SupersededBanner({ entityLabel, onViewCurrent, currentRef }: SupersededBannerProps) {
  return (
    <div
      role="status"
      style={{
        padding: 'var(--space-3) var(--space-4)',
        marginBottom: 'var(--space-4)',
        background: 'var(--amber-bg)',
        border: '1px solid var(--amber-border)',
        borderRadius: 'var(--radius-md)',
        fontSize: 'var(--font-size-body)',
        color: 'var(--text-primary)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
      }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden style={{ flexShrink: 0, color: 'var(--amber)' }}>
        <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
        <path d="M8 5v3M8 10.5v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <span>
        This is an old version of this {entityLabel}.{' '}
        <button
          type="button"
          onClick={onViewCurrent}
          style={{
            background: 'transparent',
            border: 0,
            padding: 0,
            color: 'var(--brand-interactive)',
            textDecoration: 'underline',
            cursor: 'pointer',
            fontSize: 'inherit',
            fontFamily: 'inherit',
          }}
        >
          View the superseding {entityLabel}{currentRef ? ` (${currentRef})` : ''}
        </button>
        .
      </span>
    </div>
  );
}
