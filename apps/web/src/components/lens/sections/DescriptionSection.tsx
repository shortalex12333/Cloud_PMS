import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export interface DescriptionSectionProps {
  /** Full fault description text */
  description: string;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// DESCRIPTION SECTION
// ============================================================================

/**
 * DescriptionSection - Read-only fault description section.
 *
 * Displays the full fault description in a section container with sticky header.
 * No action buttons — description is read-only in the fault lens.
 *
 * FE-02-01: Fault Lens — Description section.
 */
export function DescriptionSection({ description, stickyTop }: DescriptionSectionProps) {
  return (
    <SectionContainer
      title="Description"
      stickyTop={stickyTop}
    >
      <p
        className="text-body text-txt-primary whitespace-pre-wrap"
      >
        {description}
      </p>
    </SectionContainer>
  );
}

export default DescriptionSection;
