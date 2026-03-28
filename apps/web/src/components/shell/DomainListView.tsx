'use client';

/**
 * DomainListView — Phase 1E of the Interface Pivot
 *
 * Generic list view component used by all 12 domains.
 * Structural pattern is identical across domains — only the column config,
 * row rendering, and empty state text change per domain.
 *
 * Anatomy (from spec §05):
 *   - Column header bar: sticky, 8.5px/700/uppercase/--txt-ghost
 *   - Record rows: 44px min-height, left accent bar, cursor pointer
 *   - Row content: rec-icon + title (13px/500) + meta (10.5px/mono) + assigned + status pill + age
 *   - Empty state: centred icon + "No records match" + sub text
 *
 * The list view is NOT a lens. Clicking a row opens the full entity lens page.
 * The list view sits one level above the lens in the navigation hierarchy:
 *   Vessel Surface → domain list view → entity lens detail
 *
 * Spec: celeste-interface-pivot-spec.pdf §05
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { Search } from 'lucide-react';

/* ─────────────────────────────────────────────
   TYPES
   ───────────────────────────────────────────── */

export interface ListRecord {
  id: string;
  ref: string;
  title: string;
  meta: string;
  assignedTo?: string;
  status: string;
  statusVariant: 'open' | 'overdue' | 'critical' | 'warn' | 'signed' | 'pending' | 'monitor';
  severity?: 'critical' | 'warning' | 'info';
  age?: string;
  /** Lowercase string of all searchable fields for client-side Tier 2 filtering */
  searchText: string;
}

interface DomainListViewProps {
  /** Domain display name for empty state */
  domainLabel: string;
  /** Icon component for rows */
  rowIcon: React.ElementType;
  /** Records to display */
  records: ListRecord[];
  /** Called when a record row is clicked */
  onRecordClick: (id: string) => void;
  /** Client-side search query from Tier 2 bar (filters against searchText) */
  searchQuery?: string;
  /** Active filter chip value */
  activeChip?: string;
}

export function DomainListView({
  domainLabel,
  rowIcon: RowIcon,
  records,
  onRecordClick,
  searchQuery,
  activeChip,
}: DomainListViewProps) {
  // Client-side filtering: Tier 2 search + chip filter
  const filtered = React.useMemo(() => {
    let result = records;

    // Filter by chip (status)
    if (activeChip && activeChip !== 'All') {
      const chipLower = activeChip.toLowerCase();
      result = result.filter((r) =>
        r.status.toLowerCase() === chipLower ||
        r.statusVariant === chipLower ||
        r.searchText.includes(chipLower)
      );
    }

    // Filter by search query (client-side, instant)
    if (searchQuery && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((r) => r.searchText.includes(q));
    }

    return result;
  }, [records, searchQuery, activeChip]);

  if (filtered.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px 24px',
          gap: 8,
          color: 'var(--txt-ghost)',
          flex: 1,
        }}
      >
        <Search style={{ width: 28, height: 28, marginBottom: 4 }} />
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt3)' }}>
          No {domainLabel.toLowerCase()} match
        </span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {/* Column header bar — sticky */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 16px',
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-base)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <ColLabel style={{ flex: 1 }}>Title</ColLabel>
        <ColLabel style={{ width: 80, flexShrink: 0 }}>Assigned</ColLabel>
        <ColLabel style={{ width: 96, flexShrink: 0 }}>Status</ColLabel>
        <ColLabel style={{ width: 64, flexShrink: 0, textAlign: 'right' }}>Age</ColLabel>
      </div>

      {/* Record rows */}
      {filtered.map((record) => (
        <RecordRow
          key={record.id}
          record={record}
          icon={RowIcon}
          onClick={() => onRecordClick(record.id)}
        />
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   COLUMN HEADER LABEL
   ───────────────────────────────────────────── */

function ColLabel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        fontSize: 8.5,
        fontWeight: 700,
        letterSpacing: '0.10em',
        textTransform: 'uppercase',
        color: 'var(--txt-ghost)',
        userSelect: 'none',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────
   RECORD ROW — 44px min-height, left accent bar
   This is a PREVIEW of the lens, not a replacement.
   ───────────────────────────────────────────── */

const STATUS_PILL_STYLES: Record<string, { bg: string; color: string; border: string }> = {
  open:     { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
  overdue:  { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  critical: { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  warn:     { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  signed:   { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
  pending:  { bg: 'var(--teal-bg)', color: 'var(--mark)', border: 'var(--mark-hover)' },
  monitor:  { bg: 'var(--status-neutral-bg)', color: 'var(--txt-ghost)', border: 'var(--border-faint)' },
};

function RecordRow({
  record,
  icon: Icon,
  onClick,
}: {
  record: ListRecord;
  icon: React.ElementType;
  onClick: () => void;
}) {
  const accentColor =
    record.severity === 'critical' ? 'var(--red)'
    : record.severity === 'warning' ? 'var(--amber)'
    : record.severity === 'info' ? 'var(--teal)'
    : 'transparent';

  const iconColor =
    record.severity === 'critical' ? 'var(--red)'
    : record.severity === 'warning' ? 'var(--amber)'
    : record.severity === 'info' ? 'var(--mark)'
    : 'var(--txt3)';

  const timeColor =
    record.severity === 'critical' ? 'var(--red)'
    : record.severity === 'warning' ? 'var(--amber)'
    : 'var(--txt-ghost)';

  const pill = STATUS_PILL_STYLES[record.statusVariant] || STATUS_PILL_STYLES.open;

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 16px',
        minHeight: 44,
        borderBottom: '1px solid var(--border-faint)',
        borderLeft: `2px solid ${accentColor}`,
        cursor: 'pointer',
        transition: 'background 60ms',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      {/* Row icon */}
      <Icon style={{ width: 13, height: 13, flexShrink: 0, color: iconColor }} />

      {/* Title + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)', lineHeight: 1.4 }}>
          <span style={{ color: 'var(--mark)', fontSize: 11.5, fontWeight: 500 }}>{record.ref}</span>{' '}
          {record.title}
        </div>
        <div
          style={{
            fontSize: 10.5,
            color: 'var(--txt3)',
            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
            letterSpacing: '0.02em',
            marginTop: 1,
          }}
        >
          {record.meta}
        </div>
      </div>

      {/* Assigned */}
      <div style={{ width: 80, flexShrink: 0, fontSize: 11, color: 'var(--txt3)' }}>
        {record.assignedTo || '\u2014'}
      </div>

      {/* Status pill */}
      <div style={{ width: 96, flexShrink: 0 }}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            height: 17,
            padding: '0 5px',
            borderRadius: 3,
            fontSize: 8.5,
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            whiteSpace: 'nowrap',
            background: pill.bg,
            color: pill.color,
            border: `1px solid ${pill.border}`,
          }}
        >
          {record.status}
        </span>
      </div>

      {/* Age */}
      <div
        style={{
          width: 64,
          flexShrink: 0,
          textAlign: 'right',
          fontSize: 10.5,
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          color: timeColor,
          opacity: record.severity ? 0.75 : 1,
        }}
      >
        {record.age || '\u2014'}
      </div>
    </div>
  );
}
