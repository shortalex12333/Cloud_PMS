import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { EntityLink } from '@/components/ui/EntityLink';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export type PartStatus = 'consumed' | 'reserved';

export interface WorkOrderPart {
  id: string;
  part_id: string;
  part_name: string;
  quantity: number;
  status: PartStatus;
  /** Optional: unit of measure (e.g. "pcs", "L", "m") */
  unit?: string;
  /** Called when user clicks the part entity link */
  onPartClick?: () => void;
}

export interface PartsSectionProps {
  parts: WorkOrderPart[];
  onAddPart: () => void;
  canAddPart: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Map part status to StatusPill status.
 * consumed → success (used, final state)
 * reserved → warning (in-flight, needs monitoring per UI_SPEC.md status mapping)
 */
function getPartStatusVariant(status: PartStatus): 'success' | 'warning' {
  return status === 'consumed' ? 'success' : 'warning';
}

function getPartStatusLabel(status: PartStatus): string {
  return status === 'consumed' ? 'Consumed' : 'Reserved';
}

// ============================================================================
// PART ROW
// ============================================================================

interface PartRowProps {
  part: WorkOrderPart;
}

function PartRow({ part }: PartRowProps) {
  const qtyLabel = part.unit
    ? `${part.quantity} ${part.unit}`
    : `${part.quantity}`;

  return (
    <div
      className={cn(
        // Entity card layout: 20px horizontal, 12px vertical per UI_SPEC.md
        'flex items-center justify-between',
        'px-5 py-3 min-h-[44px]',
        // Subtle internal divider between rows
        'border-b border-surface-border-subtle last:border-b-0',
        // Hover state for interactive rows
        'transition-colors duration-fast hover:bg-surface-hover'
      )}
    >
      {/* Left: Part name as EntityLink + quantity */}
      <div className="flex items-center gap-3 min-w-0">
        <EntityLink
          entityType="part"
          entityId={part.part_id}
          label={part.part_name}
          onClick={part.onPartClick}
          className="text-body-strong truncate"
        />
        <span className="text-label text-txt-secondary flex-shrink-0">
          {qtyLabel}
        </span>
      </div>

      {/* Right: Status pill */}
      <StatusPill
        status={getPartStatusVariant(part.status)}
        label={getPartStatusLabel(part.status)}
        className="flex-shrink-0 ml-3"
      />
    </div>
  );
}

// ============================================================================
// PARTS SECTION
// ============================================================================

/**
 * PartsSection - Displays parts used on a work order with sticky header.
 *
 * Each part row includes:
 * - Part name as EntityLink (navigates to Parts lens)
 * - Quantity consumed/reserved
 * - Status pill (consumed = success, reserved = warning)
 *
 * Empty state: contextual, not generic.
 */
export function PartsSection({ parts, onAddPart, canAddPart, stickyTop }: PartsSectionProps) {
  return (
    <SectionContainer
      title="Parts Used"
      count={parts.length > 0 ? parts.length : undefined}
      action={
        canAddPart
          ? { label: '+ Add Part', onClick: onAddPart }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {parts.length === 0 ? (
        // Contextual empty state: specific + actionable per UI_SPEC.md language rules
        <div className="py-8 text-center">
          <p className="text-body text-txt-secondary">
            No parts used yet. Add Part to track inventory consumption.
          </p>
          {canAddPart && (
            <GhostButton
              onClick={onAddPart}
              className="mt-3"
            >
              + Add Part
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="-mx-4">
          {parts.map((part) => (
            <PartRow key={part.id} part={part} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default PartsSection;
