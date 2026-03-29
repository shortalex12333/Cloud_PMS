'use client';

/**
 * UrgencyGroupHeaders — Groups entity list rows by urgency tier
 *
 * WOs: OVERDUE → DUE SOON → IN PROGRESS → OPEN → COMPLETED/CANCELLED
 * Faults: CRITICAL → HIGH → MEDIUM → LOW → RESOLVED
 * Other domains: no grouping (flat list)
 *
 * Spec: v3-v5-prompts.md §FRONTEND01 Task 4.1
 */

import * as React from 'react';
import type { EntityListResult } from '../types';

/* ─────────────────────────────────────────────
   GROUP DEFINITIONS PER DOMAIN
   ───────────────────────────────────────────── */

interface GroupDef {
  key: string;
  label: string;
  colour: string;
  collapsed?: boolean;
  match: (item: EntityListResult) => boolean;
}

const WO_GROUPS: GroupDef[] = [
  { key: 'overdue', label: 'OVERDUE', colour: 'var(--red)', match: (i) => i.statusVariant === 'overdue' || i.statusVariant === 'critical' },
  { key: 'due_soon', label: 'DUE SOON', colour: 'var(--amber)', match: (i) => i.statusVariant === 'due_soon' || i.statusVariant === 'warning' },
  { key: 'in_progress', label: 'IN PROGRESS', colour: 'var(--teal)', match: (i) => i.statusVariant === 'in_progress' || i.statusVariant === 'pending' },
  { key: 'open', label: 'OPEN', colour: 'var(--txt-ghost)', match: (i) => i.statusVariant === 'open' || i.statusVariant === 'planned' },
  { key: 'closed', label: 'COMPLETED / CANCELLED', colour: 'var(--txt-ghost)', collapsed: true, match: (i) => i.statusVariant === 'completed' || i.statusVariant === 'signed' || i.statusVariant === 'cancelled' },
];

const FAULT_GROUPS: GroupDef[] = [
  { key: 'critical', label: 'CRITICAL', colour: 'var(--red)', match: (i) => i.severity === 'critical' || i.statusVariant === 'critical' },
  { key: 'high', label: 'HIGH', colour: 'var(--amber)', match: (i) => i.severity === 'warning' && i.statusVariant !== 'critical' },
  { key: 'medium', label: 'MEDIUM', colour: 'var(--txt3)', match: (i) => !i.severity && i.statusVariant === 'open' },
  { key: 'low', label: 'LOW', colour: 'var(--txt-ghost)', match: (i) => i.statusVariant === 'monitoring' },
  { key: 'resolved', label: 'RESOLVED', colour: 'var(--txt-ghost)', collapsed: true, match: (i) => i.statusVariant === 'completed' || i.statusVariant === 'signed' },
];

function getGroupsForDomain(domain?: string): GroupDef[] | null {
  if (domain === 'work-orders') return WO_GROUPS;
  if (domain === 'faults') return FAULT_GROUPS;
  return null;
}

/* ─────────────────────────────────────────────
   GROUP ITEMS
   ───────────────────────────────────────────── */

interface GroupedItems {
  group: GroupDef;
  items: EntityListResult[];
}

export function groupByUrgency(items: EntityListResult[], domain?: string): GroupedItems[] | null {
  const groups = getGroupsForDomain(domain);
  if (!groups) return null;

  const result: GroupedItems[] = groups.map((g) => ({
    group: g,
    items: items.filter(g.match),
  }));

  // Remove empty groups (except collapsed ones which show as expandable)
  return result.filter((g) => g.items.length > 0);
}

/* ─────────────────────────────────────────────
   SECTION HEADER COMPONENT
   ───────────────────────────────────────────── */

interface SectionHeaderProps {
  label: string;
  count: number;
  colour: string;
  collapsed?: boolean;
  onToggle?: () => void;
}

export function SectionHeader({ label, count, colour, collapsed, onToggle }: SectionHeaderProps) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 16px',
        borderBottom: '1px solid var(--border-faint)',
        position: 'sticky',
        top: 0,
        zIndex: 5,
        background: 'var(--surface-base)',
        cursor: onToggle ? 'pointer' : 'default',
      }}
    >
      <span
        style={{
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: colour,
          opacity: 0.6,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 9,
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          color: 'var(--txt-ghost)',
        }}
      >
        {count}
      </span>
      {collapsed !== undefined && (
        <span style={{ fontSize: 9, color: 'var(--txt-ghost)', marginLeft: 'auto' }}>
          {collapsed ? '▸' : '▾'}
        </span>
      )}
    </div>
  );
}
