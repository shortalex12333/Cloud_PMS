import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export interface LinkedEquipment {
  id: string;
  name: string;
  /** Location of the equipment on the vessel */
  location?: string;
  /** Equipment operational status */
  status?: string;
}

export interface LinkedEquipmentSectionProps {
  equipment: LinkedEquipment[];
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// EQUIPMENT ROW
// ============================================================================

interface EquipmentRowProps {
  eq: LinkedEquipment;
}

function EquipmentRow({ eq }: EquipmentRowProps) {
  return (
    <div
      className={cn(
        'px-5 py-3 min-h-[44px]',
        'border-b border-surface-border-subtle last:border-b-0',
        'flex items-center justify-between gap-3'
      )}
    >
      <div className="flex-1 min-w-0">
        {/* Equipment name as teal link — navigates to equipment lens */}
        <a
          href={`/equipment/${eq.id}`}
          className="text-[14px] font-medium text-brand-interactive hover:text-brand-hover transition-colors duration-[var(--duration-fast)] hover:underline underline-offset-2"
        >
          {eq.name}
        </a>
        {eq.location && (
          <p className="text-[13px] text-txt-tertiary mt-0.5 leading-[1.4]">
            {eq.location}
          </p>
        )}
      </div>

      {eq.status && (
        <span className="text-[12px] text-txt-tertiary flex-shrink-0 capitalize">
          {eq.status.replace(/_/g, ' ')}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// LINKED EQUIPMENT SECTION
// ============================================================================

/**
 * LinkedEquipmentSection - Equipment that uses this part.
 *
 * Each row links to the equipment lens via EntityLink.
 * Equipment name and location are displayed.
 * Empty state: contextual message.
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function LinkedEquipmentSection({
  equipment,
  stickyTop,
}: LinkedEquipmentSectionProps) {
  return (
    <SectionContainer
      title="Linked Equipment"
      count={equipment.length > 0 ? equipment.length : undefined}
      stickyTop={stickyTop}
    >
      {equipment.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No equipment linked to this part.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {equipment.map((eq) => (
            <EquipmentRow key={eq.id} eq={eq} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default LinkedEquipmentSection;
