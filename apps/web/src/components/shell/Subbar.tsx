'use client';

/**
 * Subbar — Phase 1C of the Interface Pivot
 *
 * 46px context bar below the topbar. Changes per active domain.
 * Contains: Breadcrumb + Tier 2 scoped search + filter chips + primary action.
 * Hidden when Vessel Surface is active.
 *
 * Spec: celeste-interface-pivot-spec.pdf §02, §05
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { Search, Plus } from 'lucide-react';
import type { DomainId } from './Sidebar';

/** Per-domain config for the subbar */
interface DomainSubbarConfig {
  label: string;
  icon: React.ElementType;
  searchPlaceholder: string;
  chips: string[];
  primaryAction: string;
}

const SUBBAR_CONFIGS: Partial<Record<DomainId, DomainSubbarConfig>> = {
  'work-orders': {
    label: 'Work Orders',
    icon: () => null, // Will use lucide icon from parent
    searchPlaceholder: 'Search work orders\u2026 e.g. \u201coverdue generator\u201d, \u201cMorrison\u201d',
    chips: ['All', 'Open', 'Overdue', 'My Tasks', 'Unassigned', 'Running Hours'],
    primaryAction: 'Create Work Order',
  },
  faults: {
    label: 'Faults',
    icon: () => null,
    searchPlaceholder: 'Search faults\u2026 e.g. \u201ccritical engine\u201d, \u201cunassigned bilge\u201d',
    chips: ['All', 'Critical', 'Open', 'Unassigned', 'Engine', 'Pending Parts'],
    primaryAction: 'Log Fault',
  },
  equipment: {
    label: 'Equipment',
    icon: () => null,
    searchPlaceholder: 'Search equipment\u2026 e.g. \u201cmain engine\u201d, \u201cE-007\u201d, \u201cstarboard\u201d',
    chips: ['All', 'Active', 'Fault Logged', 'Due Service'],
    primaryAction: 'Add Equipment',
  },
  'handover-export': {
    label: 'Handover',
    icon: () => null,
    searchPlaceholder: 'Search handovers\u2026 e.g. \u201cMorrison\u201d, \u201cMarch\u201d, \u201cengine notes\u201d',
    chips: ['All', 'Draft', 'Pending', 'Signed'],
    primaryAction: 'Create Handover',
  },
  'hours-of-rest': {
    label: 'Hours of Rest',
    icon: () => null,
    searchPlaceholder: 'Search rest records\u2026 crew name or date',
    chips: ['All', 'Today', 'Non-Compliant', 'Pending Sign-off'],
    primaryAction: 'Log Hours',
  },
  inventory: {
    label: 'Parts / Inventory',
    icon: () => null,
    searchPlaceholder: 'Search parts\u2026 e.g. \u201coil filter\u201d, \u201cP-0441\u201d, \u201cengine room\u201d',
    chips: ['All', 'Low Stock', 'Zero Stock', 'Engine Room', 'Electrical'],
    primaryAction: 'Add Part',
  },
  'shopping-list': {
    label: 'Shopping List',
    icon: () => null,
    searchPlaceholder: 'Search shopping list\u2026',
    chips: ['All', 'Pending', 'Approved', 'Ordered'],
    primaryAction: 'Add to List',
  },
  purchasing: {
    label: 'Purchase Orders',
    icon: () => null,
    searchPlaceholder: 'Search purchase orders\u2026 supplier, part, PO number',
    chips: ['All', 'Draft', 'Sent', 'Received', 'Overdue'],
    primaryAction: 'Create PO',
  },
  receiving: {
    label: 'Receiving',
    icon: () => null,
    searchPlaceholder: 'Search receiving records\u2026',
    chips: ['All', 'Pending', 'Inspected', 'Accepted', 'Rejected'],
    primaryAction: 'Log Receipt',
  },
  certificates: {
    label: 'Certificates',
    icon: () => null,
    searchPlaceholder: 'Search certificates\u2026 e.g. \u201cSOLAS\u201d, \u201cexpiring\u201d, \u201cclass\u201d',
    chips: ['All', 'Expiring Soon', 'Expired', 'Valid'],
    primaryAction: 'Add Certificate',
  },
  documents: {
    label: 'Documents',
    icon: () => null,
    searchPlaceholder: 'Search documents\u2026 e.g. \u201cMTU manual\u201d, \u201cschematic\u201d, \u201cinvoice\u201d',
    chips: ['All', 'Manuals', 'Drawings', 'Invoices'],
    primaryAction: 'Upload Document',
  },
  warranties: {
    label: 'Warranty',
    icon: () => null,
    searchPlaceholder: 'Search warranty records\u2026 supplier, equipment, claim number',
    chips: ['All', 'Active', 'Expiring', 'Expired', 'Claimed'],
    primaryAction: 'Add Warranty',
  },
};

/** Sort options per domain */
const SORT_OPTIONS: Partial<Record<DomainId, { options: string[]; defaultSort: string }>> = {
  'work-orders': { options: ['Urgency', 'Due Date', 'Newest', 'Assigned'], defaultSort: 'Urgency' },
  faults: { options: ['Severity', 'Newest', 'Assigned', 'Equipment'], defaultSort: 'Severity' },
  inventory: { options: ['Stock Level', 'Name', 'Location'], defaultSort: 'Stock Level' },
  equipment: { options: ['Name', 'Location', 'Newest'], defaultSort: 'Name' },
  certificates: { options: ['Expiry Date', 'Name', 'Newest'], defaultSort: 'Expiry Date' },
};

interface SubbarProps {
  activeDomain: DomainId;
  totalCount?: number;
  activeChip?: string;
  onChipClick?: (chip: string) => void;
  onSearch?: (query: string) => void;
  onSortChange?: (sort: string) => void;
  onPrimaryAction?: () => void;
}

export function Subbar({
  activeDomain,
  totalCount,
  activeChip = 'All',
  onChipClick,
  onSearch,
  onSortChange,
  onPrimaryAction,
}: SubbarProps) {
  // Hide when Vessel Surface is active
  if (activeDomain === 'surface') return null;

  const config = SUBBAR_CONFIGS[activeDomain];
  if (!config) return null;

  return (
    <div
      style={{
        height: 46,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        paddingRight: 16,
        background: 'var(--topbar-bg)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-faint)',
        zIndex: 90,
        overflow: 'hidden',
      }}
    >
      {/* Breadcrumb */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '0 14px',
          borderRight: '1px solid var(--border-faint)',
          height: '100%',
          flexShrink: 0,
          minWidth: 200,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--txt3)',
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          {config.label}
        </span>
        {totalCount !== undefined && (
          <span
            style={{
              fontSize: 10,
              fontFamily: 'var(--font-mono, ui-monospace, monospace)',
              color: 'var(--txt-ghost)',
              marginLeft: 2,
            }}
          >
            {totalCount}
          </span>
        )}
      </div>

      {/* Tier 2 scoped search — UI only for now, wired to ENGINEER01's endpoint later */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 7,
          height: 28,
          padding: '0 10px',
          /* Asymmetric border physics — no single token covers this. See spec §06. */
          background: 'var(--split-bg)',
          border: '1px solid var(--border-faint)',
          borderRadius: 4,
          transition: 'background 100ms, border-color 100ms',
        }}
      >
        <Search
          style={{
            width: 12,
            height: 12,
            color: 'var(--txt-ghost)',
            flexShrink: 0,
          }}
        />
        <input
          type="text"
          placeholder={config.searchPlaceholder}
          onChange={(e) => onSearch?.(e.target.value)}
          style={{
            flex: 1,
            fontSize: 12,
            color: 'var(--txt)',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            caretColor: 'var(--mark)',
          }}
        />
      </div>

      {/* Filter chips — horizontal scroll on narrow widths */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          flexShrink: 1,
          minWidth: 0,
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
      >
        {config.chips.map((chip) => {
          const active = activeChip === chip;
          const cs = active ? getChipColour(chip) : null;
          return (
            <button
              key={chip}
              onClick={() => onChipClick?.(chip)}
              style={{
                height: 20,
                padding: '0 8px',
                borderRadius: 3,
                border: `1px solid ${active ? (cs?.border || 'var(--mark-hover)') : 'var(--border-sub)'}`,
                background: active ? (cs?.bg || 'var(--teal-bg)') : 'var(--surface-el)',
                fontSize: 9.5,
                fontWeight: 500,
                color: active ? (cs?.color || 'var(--mark)') : 'var(--txt3)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'background 70ms, color 70ms, border-color 70ms',
              }}
            >
              {chip}
            </button>
          );
        })}
      </div>

      {/* Sort control */}
      {SORT_OPTIONS[activeDomain] && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <span style={{ fontSize: 10, color: 'var(--txt-ghost)' }}>Sort by</span>
          <select
            defaultValue={SORT_OPTIONS[activeDomain]!.defaultSort}
            onChange={(e) => onSortChange?.(e.target.value)}
            style={{
              height: 20,
              padding: '0 4px',
              borderRadius: 3,
              border: '1px solid var(--border-sub)',
              background: 'var(--surface-el)',
              fontSize: 9.5,
              color: 'var(--txt3)',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {SORT_OPTIONS[activeDomain]!.options.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
      )}

      {/* Primary action button */}
      <button
        onClick={onPrimaryAction}
        style={{
          height: 28,
          padding: '0 12px',
          borderRadius: 4,
          background: 'var(--teal-bg)',
          border: '1px solid var(--mark-hover)',
          fontSize: 11,
          fontWeight: 500,
          color: 'var(--mark)',
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          cursor: 'pointer',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          transition: 'background 80ms',
        }}
      >
        <Plus style={{ width: 11, height: 11 }} />
        {config.primaryAction}
      </button>
    </div>
  );
}

/** Map chip label to severity colour when active */
function getChipColour(chip: string): { bg: string; color: string; border: string } | null {
  const c = chip.toLowerCase();
  if (c === 'emergency' || c === 'critical' || c === 'overdue' || c === 'zero stock' || c === 'rejected')
    return { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' };
  if (c === 'warning' || c === 'due soon' || c === 'expiring' || c === 'low stock' || c === 'non-compliant')
    return { bg: 'var(--amber-bg)', color: 'var(--amber)', border: 'var(--amber-border)' };
  if (c === 'completed' || c === 'signed' || c === 'accepted' || c === 'compliant')
    return { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' };
  if (c === 'cancelled' || c === 'monitoring')
    return { bg: 'var(--status-neutral-bg)', color: 'var(--txt-ghost)', border: 'var(--border-faint)' };
  return null; // default teal for All, Open, Engine, Pending Parts, etc.
}
