'use client';

/**
 * EntityRecordRow — Proper list view row with full anatomy
 *
 * Replaces the flat SpotlightResultRow for domain list views.
 * SpotlightResultRow remains unchanged for search results.
 *
 * Row anatomy (left to right):
 *   [2px accent bar — severity colour]
 *   [icon 13px — entity type]
 *   [BODY flex:1]
 *     Line 1: [entityRef 11px mono teal] — [title 13px/500/--txt]
 *     Line 2: [equipmentRef 10.5px mono teal link] · [assigned 10.5px mono --txt3]
 *   [STATUS PILL — 17px height, 8.5px/600/uppercase]
 *   [AGE — 10px mono --txt-ghost, 64px wide]
 *
 * Min height: 44px. Hover = promise (only when onClick exists).
 *
 * Spec: celeste-v2-review.pdf §03, v3-v5-prompts.md §FRONTEND01 Task 3.1
 */

import * as React from 'react';
import {
  AlertTriangle,
  ClipboardList,
  Package,
  FileText,
  Award,
  ShoppingCart,
  Receipt,
  Clock,
  Shield,
  Wrench,
  FileSignature,
  PackageCheck,
  type LucideIcon,
} from 'lucide-react';

/* ─────────────────────────────────────────────
   TYPES
   ───────────────────────────────────────────── */

export interface RecordRowData {
  id: string;
  entityRef: string;
  title: string;
  equipmentRef?: string;
  equipmentName?: string;
  assignedTo?: string;
  meta?: string;
  status: string;
  statusVariant: StatusVariant;
  severity?: Severity;
  age?: string;
  entityType: string;
}

type Severity = 'critical' | 'warning' | 'info' | null;
type StatusVariant =
  | 'overdue' | 'critical'
  | 'due_soon' | 'warning' | 'expiring' | 'draft'
  | 'in_progress' | 'pending'
  | 'completed' | 'signed'
  | 'open' | 'planned'
  | 'cancelled' | 'monitoring';

/* ─────────────────────────────────────────────
   ICON MAP
   ───────────────────────────────────────────── */

const ENTITY_ICONS: Record<string, LucideIcon> = {
  work_order: ClipboardList,
  fault: AlertTriangle,
  equipment: Wrench,
  part: Package,
  inventory: Package,
  certificate: Award,
  document: FileText,
  warranty: Shield,
  shopping_list: ShoppingCart,
  purchase_order: Receipt,
  receiving: PackageCheck,
  hours_of_rest: Clock,
  handover: FileSignature,
  handover_export: FileSignature,
};

function getIcon(entityType: string): LucideIcon {
  return ENTITY_ICONS[entityType] || FileText;
}

/* ─────────────────────────────────────────────
   ACCENT BAR COLOURS
   ───────────────────────────────────────────── */

function getAccentColour(severity?: Severity, statusVariant?: StatusVariant): string {
  if (severity === 'critical') return 'var(--red)';
  if (severity === 'warning') return 'var(--amber)';
  if (severity === 'info') return 'var(--teal)';
  if (statusVariant === 'overdue' || statusVariant === 'critical') return 'var(--red)';
  if (statusVariant === 'due_soon' || statusVariant === 'warning' || statusVariant === 'expiring') return 'var(--amber)';
  if (statusVariant === 'in_progress' || statusVariant === 'pending') return 'var(--teal)';
  return 'transparent';
}

/* ─────────────────────────────────────────────
   STATUS PILL STYLES
   ───────────────────────────────────────────── */

const PILL_MAP: Record<string, { bg: string; color: string; border: string }> = {
  overdue:     { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  critical:    { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
  due_soon:    { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  warning:     { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  expiring:    { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  draft:       { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' },
  in_progress: { bg: 'var(--teal-bg)', color: 'var(--mark)', border: 'var(--mark-hover)' },
  pending:     { bg: 'var(--teal-bg)', color: 'var(--mark)', border: 'var(--mark-hover)' },
  completed:   { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
  signed:      { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
  open:        { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
  planned:     { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
  cancelled:   { bg: 'var(--status-neutral-bg)', color: 'var(--txt-ghost)', border: 'var(--border-faint)' },
  monitoring:  { bg: 'var(--status-neutral-bg)', color: 'var(--txt-ghost)', border: 'var(--border-faint)' },
};

function getPillStyle(variant: string) {
  return PILL_MAP[variant] || PILL_MAP.open;
}

/* ─────────────────────────────────────────────
   COMPONENT
   ───────────────────────────────────────────── */

interface EntityRecordRowProps {
  data: RecordRowData;
  onClick: () => void;
  onEquipmentClick?: (equipmentRef: string) => void;
}

export function EntityRecordRow({ data, onClick, onEquipmentClick }: EntityRecordRowProps) {
  const Icon = getIcon(data.entityType);
  const accent = getAccentColour(data.severity, data.statusVariant);
  const pill = getPillStyle(data.statusVariant);

  const iconColour =
    data.severity === 'critical' ? 'var(--red)'
    : data.severity === 'warning' ? 'var(--amber)'
    : data.severity === 'info' ? 'var(--mark)'
    : 'var(--txt3)';

  const ageColour =
    data.severity === 'critical' ? 'var(--red)'
    : data.severity === 'warning' ? 'var(--amber)'
    : 'var(--txt-ghost)';

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
        borderLeft: `2px solid ${accent}`,
        cursor: 'pointer',
        transition: 'background 60ms',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      {/* Icon */}
      <Icon style={{ width: 13, height: 13, flexShrink: 0, color: iconColour }} />

      {/* Body */}
      <div style={{ flex: 1, minWidth: 0, padding: '6px 0' }}>
        {/* Line 1: ref + title */}
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)', lineHeight: 1.4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          <span style={{ color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontWeight: 500 }}>
            {data.entityRef}
          </span>
          {' \u2014 '}
          {data.title}
        </div>

        {/* Line 2: equipment ref + assigned */}
        <div style={{ fontSize: 10.5, fontFamily: 'var(--font-mono, ui-monospace, monospace)', color: 'var(--txt3)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {data.equipmentRef && (
            <span
              style={{ color: 'var(--mark)', cursor: onEquipmentClick ? 'pointer' : 'inherit' }}
              onClick={(e) => {
                if (onEquipmentClick) {
                  e.stopPropagation();
                  onEquipmentClick(data.equipmentRef!);
                }
              }}
            >
              {data.equipmentRef}
              {data.equipmentName && ` ${data.equipmentName}`}
            </span>
          )}
          {data.equipmentRef && data.assignedTo && ' \u00b7 '}
          {data.assignedTo && (
            <span style={{ color: 'var(--txt3)' }}>{data.assignedTo}</span>
          )}
          {!data.equipmentRef && !data.assignedTo && data.meta && (
            <span>{data.meta}</span>
          )}
        </div>
      </div>

      {/* Status pill */}
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
          flexShrink: 0,
          background: pill.bg,
          color: pill.color,
          border: `1px solid ${pill.border}`,
        }}
      >
        {data.status}
      </span>

      {/* Age */}
      <div
        style={{
          width: 64,
          flexShrink: 0,
          textAlign: 'right',
          fontSize: 10,
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          color: ageColour,
          opacity: data.severity ? 0.8 : 1,
        }}
      >
        {data.age || '\u2014'}
      </div>
    </div>
  );
}
