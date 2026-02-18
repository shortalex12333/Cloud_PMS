import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export interface LinkedFault {
  id: string;
  title: string;
  /** Severity enum: low | medium | high | critical */
  severity?: string;
  /** Status enum: open | in_progress | resolved */
  status: string;
  created_at: string;
  reported_by?: string;
}

export interface LinkedFaultsSectionProps {
  faults: LinkedFault[];
  /** Equipment ID — used to build "View all faults" link */
  equipmentId: string;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function mapSeverityToColor(severity?: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'warning';
    case 'medium':
    case 'low':
    default:
      return 'neutral';
  }
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'open':
      return 'critical';
    case 'in_progress':
      return 'warning';
    case 'resolved':
      return 'success';
    default:
      return 'neutral';
  }
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoString;
  }
}

function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    open: 'Open',
    in_progress: 'In Progress',
    resolved: 'Resolved',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ============================================================================
// FAULT ROW — EntityLink pattern
// ============================================================================

interface FaultRowProps {
  fault: LinkedFault;
}

function FaultRow({ fault }: FaultRowProps) {
  const statusColor = mapStatusToColor(fault.status);
  const statusLabel = formatStatusLabel(fault.status);
  const severityColor = mapSeverityToColor(fault.severity);

  return (
    <a
      href={`/faults/${fault.id}`}
      className="flex items-start justify-between gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px] hover:bg-surface-hover transition-colors group"
      aria-label={`View fault: ${fault.title}`}
    >
      {/* Left: title + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-medium text-txt-primary leading-[1.4] group-hover:text-brand-interactive transition-colors truncate">
          {fault.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[12px] text-txt-tertiary">
            {formatDate(fault.created_at)}
          </span>
          {fault.reported_by && (
            <span className="text-[12px] text-txt-tertiary">
              · {fault.reported_by}
            </span>
          )}
        </div>
      </div>

      {/* Right: status + severity pills */}
      <div className="flex items-center gap-2 shrink-0">
        {fault.severity && (
          <StatusPill status={severityColor} label={fault.severity.charAt(0).toUpperCase() + fault.severity.slice(1)} />
        )}
        <StatusPill status={statusColor} label={statusLabel} showDot />
      </div>
    </a>
  );
}

// ============================================================================
// LINKED FAULTS SECTION
// ============================================================================

/**
 * LinkedFaultsSection - List of faults referencing this equipment.
 *
 * Each fault renders as an EntityLink (clickable row) navigating to /faults/{id}.
 * Shows status pill and severity pill per fault.
 * Empty state provides a contextual message.
 */
export function LinkedFaultsSection({
  faults,
  equipmentId,
  stickyTop,
}: LinkedFaultsSectionProps) {
  // Separate open from resolved for display order (open faults first)
  const openFaults = faults.filter((f) => f.status !== 'resolved');
  const resolvedFaults = faults.filter((f) => f.status === 'resolved');
  const sorted = [...openFaults, ...resolvedFaults];

  return (
    <SectionContainer
      title="Linked Faults"
      count={faults.length > 0 ? faults.length : undefined}
      action={
        faults.length > 0
          ? {
              label: 'View all',
              onClick: () => {
                window.location.href = `/faults?equipment_id=${equipmentId}`;
              },
            }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No faults reported for this equipment.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {sorted.map((fault) => (
            <FaultRow key={fault.id} fault={fault} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default LinkedFaultsSection;
