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
    searchPlaceholder: 'Search work orders\u2026 e.g. "overdue unassigned"',
    chips: ['All', 'Open', 'Overdue', 'My Tasks', 'Unassigned', 'Running Hours'],
    primaryAction: 'Create Work Order',
  },
  faults: {
    label: 'Faults',
    icon: () => null,
    searchPlaceholder: 'Search faults\u2026 e.g. "critical engine"',
    chips: ['All', 'Critical', 'Open', 'Unassigned', 'Engine', 'Pending Parts'],
    primaryAction: 'Log Fault',
  },
  equipment: {
    label: 'Equipment',
    icon: () => null,
    searchPlaceholder: 'Search equipment\u2026',
    chips: ['All', 'Active', 'Fault Logged', 'Due Service'],
    primaryAction: 'Add Equipment',
  },
  'handover-export': {
    label: 'Handover',
    icon: () => null,
    searchPlaceholder: 'Search handovers\u2026',
    chips: ['All', 'Draft', 'Pending', 'Signed'],
    primaryAction: 'Create Handover',
  },
  'hours-of-rest': {
    label: 'Hours of Rest',
    icon: () => null,
    searchPlaceholder: 'Search rest records\u2026',
    chips: ['All', 'Today', 'Non-Compliant', 'Pending Sign-off'],
    primaryAction: 'Log Hours',
  },
  inventory: {
    label: 'Parts / Inventory',
    icon: () => null,
    searchPlaceholder: 'Search parts\u2026 e.g. "oil filter low stock"',
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
    searchPlaceholder: 'Search purchase orders\u2026',
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
    searchPlaceholder: 'Search certificates\u2026 e.g. "expiring 30 days"',
    chips: ['All', 'Expiring Soon', 'Expired', 'Valid'],
    primaryAction: 'Add Certificate',
  },
  documents: {
    label: 'Documents',
    icon: () => null,
    searchPlaceholder: 'Search documents\u2026',
    chips: ['All', 'Manuals', 'Drawings', 'Invoices'],
    primaryAction: 'Upload Document',
  },
  warranties: {
    label: 'Warranty',
    icon: () => null,
    searchPlaceholder: 'Search warranties\u2026',
    chips: ['All', 'Active', 'Expiring', 'Expired', 'Claimed'],
    primaryAction: 'Add Warranty',
  },
};

interface SubbarProps {
  activeDomain: DomainId;
  totalCount?: number;
  activeChip?: string;
  onChipClick?: (chip: string) => void;
  onSearch?: (query: string) => void;
  onPrimaryAction?: () => void;
}

export function Subbar({
  activeDomain,
  totalCount,
  activeChip = 'All',
  onChipClick,
  onSearch,
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

      {/* Filter chips */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          flexShrink: 0,
        }}
      >
        {config.chips.map((chip) => (
          <button
            key={chip}
            onClick={() => onChipClick?.(chip)}
            style={{
              height: 20,
              padding: '0 8px',
              borderRadius: 3,
              border: `1px solid ${
                activeChip === chip
                  ? 'var(--mark-hover)'
                  : 'var(--border-sub)'
              }`,
              background:
                activeChip === chip ? 'var(--teal-bg)' : 'var(--surface-el)',
              fontSize: 9.5,
              fontWeight: 500,
              color:
                activeChip === chip ? 'var(--mark)' : 'var(--txt3)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'background 70ms, color 70ms, border-color 70ms',
            }}
          >
            {chip}
          </button>
        ))}
      </div>

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
