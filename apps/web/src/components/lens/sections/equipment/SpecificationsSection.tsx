import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import type { EquipmentLensData } from '@/components/lens/types';

// ============================================================================
// TYPES
// ============================================================================

export interface EquipmentSpecification {
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  installation_date?: string;
  warranty_expiry?: string;
  running_hours?: number;
  equipment_type?: string;
  category?: string;
}

export interface SpecificationsSectionProps {
  equipment: Pick<
    EquipmentLensData,
    | 'serial_number'
    | 'manufacturer'
    | 'model'
    | 'installation_date'
    | 'warranty_expiry'
    | 'running_hours'
    | 'specifications'
  >;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// ============================================================================
// SPEC ROW
// ============================================================================

interface SpecRowProps {
  label: string;
  value: string;
}

function SpecRow({ label, value }: SpecRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px]">
      <span className="text-[13px] font-medium text-txt-tertiary leading-[1.4] shrink-0">
        {label}
      </span>
      <span className="text-[14px] font-normal text-txt-primary leading-[1.4] text-right">
        {value}
      </span>
    </div>
  );
}

// ============================================================================
// SPECIFICATIONS SECTION
// ============================================================================

/**
 * SpecificationsSection - Displays equipment technical specifications.
 *
 * Shows: serial number, manufacturer, model, installation date, warranty,
 * and running hours. All fields are optional — omitted when not present.
 */
export function SpecificationsSection({
  equipment,
  stickyTop,
}: SpecificationsSectionProps) {
  // Merge top-level fields with nested specifications object
  const specs = equipment.specifications ?? {};
  const serial = equipment.serial_number ?? specs.serial_number;
  const manufacturer = equipment.manufacturer ?? specs.manufacturer;
  const model = equipment.model ?? specs.model;
  const installDate = equipment.installation_date ?? specs.installation_date;
  const warranty = equipment.warranty_expiry ?? specs.warranty_expiry;
  const runningHours = equipment.running_hours ?? specs.running_hours;

  // Build list of rows — only include fields that have values
  const rows: Array<{ label: string; value: string }> = [];

  if (serial) rows.push({ label: 'Serial Number', value: serial });
  if (manufacturer) rows.push({ label: 'Manufacturer', value: manufacturer });
  if (model) rows.push({ label: 'Model', value: model });
  if (installDate) rows.push({ label: 'Installed', value: formatDate(installDate) });
  if (warranty) rows.push({ label: 'Warranty Expires', value: formatDate(warranty) });
  if (runningHours !== undefined) {
    rows.push({ label: 'Running Hours', value: `${runningHours.toLocaleString()} hrs` });
  }

  return (
    <SectionContainer
      title="Specifications"
      stickyTop={stickyTop}
    >
      {rows.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No specifications recorded for this equipment.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {rows.map((row) => (
            <SpecRow key={row.label} label={row.label} value={row.value} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default SpecificationsSection;
