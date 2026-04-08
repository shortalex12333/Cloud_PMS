'use client';

/**
 * Sidebar — Phase 1B of the Interface Pivot
 *
 * 192px fixed left sidebar. The navigation centre.
 * Replaces the confusing topbar nav pills from v1.
 *
 * Structure:
 * - Vessel Surface item (top, separated by border)
 * - Operations group: Work Orders, Faults, Equipment, Handover, Hours of Rest
 * - Inventory & Supply group: Parts, Shopping List, Purchase Orders, Receiving
 * - Compliance group: Certificates, Documents, Warranty
 *
 * Spec: celeste-interface-pivot-spec.pdf §05
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import {
  LayoutGrid,
  ClipboardList,
  AlertTriangle,
  Wrench,
  FileSignature,
  Clock,
  Package,
  ShoppingCart,
  FileText,
  PackageCheck,
  Award,
  File,
  Shield,
  Mail,
} from 'lucide-react';

export type DomainId =
  | 'surface'
  | 'work-orders'
  | 'faults'
  | 'equipment'
  | 'handover-export'
  | 'hours-of-rest'
  | 'email'
  | 'inventory'
  | 'shopping-list'
  | 'purchasing'
  | 'receiving'
  | 'certificates'
  | 'documents'
  | 'warranties';

interface DomainItemConfig {
  id: DomainId;
  label: string;
  icon: React.ElementType;
  count?: number;
  severity?: 'critical' | 'warning' | 'ok' | null;
}

interface DomainGroup {
  label: string;
  items: DomainItemConfig[];
}

const DOMAIN_GROUPS: DomainGroup[] = [
  {
    label: 'Operations',
    items: [
      { id: 'work-orders', label: 'Work Orders', icon: ClipboardList },
      { id: 'faults', label: 'Faults', icon: AlertTriangle },
      { id: 'equipment', label: 'Equipment', icon: Wrench },
      { id: 'handover-export', label: 'Handover', icon: FileSignature },
      { id: 'hours-of-rest', label: 'Hours of Rest', icon: Clock },
      { id: 'email', label: 'Email', icon: Mail },
    ],
  },
  {
    label: 'Inventory & Supply',
    items: [
      { id: 'inventory', label: 'Parts / Inventory', icon: Package },
      { id: 'shopping-list', label: 'Shopping List', icon: ShoppingCart },
      { id: 'purchasing', label: 'Purchase Orders', icon: FileText },
      { id: 'receiving', label: 'Receiving', icon: PackageCheck },
    ],
  },
  {
    label: 'Compliance',
    items: [
      { id: 'certificates', label: 'Certificates', icon: Award },
      { id: 'documents', label: 'Documents', icon: File },
      { id: 'warranties', label: 'Warranty', icon: Shield },
    ],
  },
];

interface SidebarProps {
  activeDomain: DomainId;
  onSelectDomain: (domain: DomainId) => void;
  /** Domain record counts keyed by domain ID */
  counts?: Partial<Record<DomainId, { count: number; severity?: 'critical' | 'warning' | 'ok' | null }>>;
  /** Icon-only mode at narrow widths */
  compact?: boolean;
}

export function Sidebar({ activeDomain, onSelectDomain, counts, compact }: SidebarProps) {
  return (
    <nav
      data-testid="sidebar"
      style={{
        width: '100%',
        flexShrink: 0,
        borderRight: '1px solid var(--border-faint)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        overflowX: 'hidden',
        background: 'var(--surface-base)',
      }}
    >
      {/* Vessel Surface — top item */}
      <SurfaceItem
        active={activeDomain === 'surface'}
        onClick={() => onSelectDomain('surface')}
      />

      {/* Domain groups */}
      {DOMAIN_GROUPS.map((group, groupIndex) => (
        <React.Fragment key={group.label}>
          {/* Divider between groups */}
          {groupIndex > 0 && (
            <div style={{ height: 1, background: 'var(--border-faint)', margin: '6px 0' }} />
          )}
          {!compact && (
            <div
              style={{
                fontSize: 8,
                fontWeight: 600,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                color: 'var(--txt-ghost)',
                padding: '12px 14px 5px',
              }}
            >
              {group.label}
            </div>
          )}
          {group.items.map((item) => {
            const countData = counts?.[item.id];
            return (
              <DomainItem
                key={item.id}
                icon={item.icon}
                label={item.label}
                count={countData?.count}
                severity={countData?.severity}
                active={activeDomain === item.id}
                onClick={() => onSelectDomain(item.id)}
                compact={compact}
              />
            );
          })}
        </React.Fragment>
      ))}
    </nav>
  );
}

/** Vessel Surface top-level item */
function SurfaceItem({ active, onClick }: { active: boolean; onClick: () => void }) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 14px',
        cursor: 'pointer',
        borderLeft: `2px solid ${active ? 'var(--mark)' : 'transparent'}`,
        borderBottom: '1px solid var(--border-faint)',
        marginBottom: 4,
        transition: 'background 70ms',
        background: active
          ? 'var(--teal-bg)'
          : hovered
            ? 'var(--surface-hover)'
            : 'transparent',
      }}
    >
      <LayoutGrid
        style={{
          width: 13,
          height: 13,
          flexShrink: 0,
          color: active ? 'var(--mark)' : 'var(--txt3)',
        }}
      />
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: active ? 'var(--mark)' : 'var(--txt2)',
        }}
      >
        Vessel Surface
      </span>
    </div>
  );
}

/** Individual domain nav item */
function DomainItem({
  icon: Icon,
  label,
  count,
  severity,
  active,
  onClick,
  compact,
}: {
  icon: React.ElementType;
  label: string;
  count?: number;
  severity?: 'critical' | 'warning' | 'ok' | null;
  active: boolean;
  onClick: () => void;
  compact?: boolean;
}) {
  const [hovered, setHovered] = React.useState(false);

  const countColor =
    severity === 'critical'
      ? 'var(--red)'
      : severity === 'warning'
        ? 'var(--amber)'
        : severity === 'ok'
          ? 'var(--green)'
          : 'var(--txt-ghost)';

  const countWeight = severity === 'critical' || severity === 'warning' ? 600 : 400;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: compact ? 0 : 8,
        padding: compact ? '7px 0' : '7px 14px',
        justifyContent: compact ? 'center' : undefined,
        cursor: 'pointer',
        borderLeft: `2px solid ${active ? 'var(--mark)' : 'transparent'}`,
        transition: 'background 70ms',
        minHeight: 34,
        background: active
          ? 'var(--teal-bg)'
          : hovered
            ? 'var(--surface-hover)'
            : 'transparent',
      }}
    >
      <Icon
        style={{
          width: 13,
          height: 13,
          flexShrink: 0,
          color: active ? 'var(--mark)' : 'var(--txt3)',
          transition: 'color 70ms',
        }}
      />
      {!compact && (
        <span
          style={{
            flex: 1,
            minWidth: 0,
            fontSize: 12,
            fontWeight: 500,
            color: active ? 'var(--mark)' : 'var(--txt2)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            transition: 'color 70ms',
          }}
        >
          {label}
        </span>
      )}
      {!compact && count !== undefined && (
        <span
          style={{
            fontSize: 9.5,
            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
            color: countColor,
            fontWeight: countWeight,
            flexShrink: 0,
          }}
        >
          {count}
        </span>
      )}
    </div>
  );
}
