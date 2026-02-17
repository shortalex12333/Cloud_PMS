'use client';

/**
 * EquipmentLens - Full-screen entity lens for equipment.
 *
 * Per UI_SPEC.md and CLAUDE.md:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: 28px display title, status pill
 * - VitalSignsRow: 5 indicators (status, location, make/model, faults, work orders)
 * - NO UUID visible anywhere in the header
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * FE-02-02: Equipment Lens Rebuild — follows WorkOrderLens reference pattern.
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';

// Sections
import {
  SpecificationsSection,
  MaintenanceHistorySection,
  LinkedFaultsSection,
  LinkedWorkOrdersSection,
  DocumentsSection,
  type EquipmentSpecification,
  type MaintenanceHistoryEntry,
  type LinkedFault,
  type LinkedWorkOrder,
  type EquipmentDocument,
} from './sections/equipment';

// Action hook + permissions
import {
  useEquipmentActions,
  useEquipmentPermissions,
} from '@/hooks/useEquipmentActions';
import { GhostButton } from '@/components/ui/GhostButton';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface EquipmentLensData {
  id: string;
  name: string;
  /** Status enum: active | inactive | maintenance */
  status: string;
  /** Physical location on the yacht, e.g. "Engine Room / Station 2" */
  location?: string;
  /** Manufacturer name */
  manufacturer?: string;
  /** Model number/name */
  model?: string;
  serial_number?: string;
  installation_date?: string;
  warranty_expiry?: string;
  running_hours?: number;
  risk_score?: number;
  created_at?: string;
  /** Linked faults (fetched separately for count + list display) */
  faults?: LinkedFault[];
  /** Count of open faults (may be denormalized for performance) */
  open_faults_count?: number;
  /** Linked work orders */
  work_orders?: LinkedWorkOrder[];
  /** Count of active work orders */
  active_wo_count?: number;
  /** Specification details */
  specifications?: EquipmentSpecification;
  /** Maintenance history entries */
  maintenance_history?: MaintenanceHistoryEntry[];
  /** Linked documents (manuals, certificates) */
  documents?: EquipmentDocument[];
}

export interface EquipmentLensProps {
  /** The equipment data to render */
  equipment: EquipmentLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers (local — domain-specific logic stays with domain)
// ---------------------------------------------------------------------------

/**
 * Map equipment status string to StatusPill color level.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'inactive':
    case 'offline':
    case 'faulty':
      return 'critical';
    case 'maintenance':
    case 'under_maintenance':
      return 'warning';
    case 'active':
    case 'operational':
      return 'success';
    default:
      return 'neutral';
  }
}

/**
 * Format equipment status enum to a human-readable display label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: 'Active',
    inactive: 'Inactive',
    maintenance: 'Maintenance',
    under_maintenance: 'Under Maintenance',
    operational: 'Operational',
    faulty: 'Faulty',
    offline: 'Offline',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// EquipmentLens component
// ---------------------------------------------------------------------------

/**
 * EquipmentLens — Full-screen entity lens for equipment.
 *
 * Usage:
 * ```tsx
 * <EquipmentLens
 *   equipment={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const EquipmentLens = React.forwardRef<
  HTMLDivElement,
  EquipmentLensProps
>(({ equipment, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Actions and permissions
  const actions = useEquipmentActions(equipment.id);
  const perms = useEquipmentPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values
  const statusColor = mapStatusToColor(equipment.status);
  const statusLabel = formatStatusLabel(equipment.status);

  // Combined make/model string
  const makeModel = [equipment.manufacturer, equipment.model]
    .filter(Boolean)
    .join(' ');

  // Fault and work order counts (safe fallback to array length)
  const openFaultsCount = equipment.open_faults_count ?? equipment.faults?.length ?? 0;
  const activeWoCount = equipment.active_wo_count ?? equipment.work_orders?.length ?? 0;

  // Build the 5 vital signs per plan spec
  const equipmentVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Location',
      value: equipment.location ?? 'Unknown',
    },
    {
      label: 'Make / Model',
      value: makeModel || 'Unknown',
    },
    {
      label: 'Faults',
      value: `${openFaultsCount} open fault${openFaultsCount === 1 ? '' : 's'}`,
      // Teal link to fault list filtered for this equipment
      href: `/faults?equipment_id=${equipment.id}`,
    },
    {
      label: 'Work Orders',
      value: `${activeWoCount} active WO${activeWoCount === 1 ? '' : 's'}`,
      href: `/work-orders?equipment_id=${equipment.id}`,
    },
  ];

  // Section data (safe fallbacks)
  const faults = equipment.faults ?? [];
  const workOrders = equipment.work_orders ?? [];
  const maintenanceHistory = equipment.maintenance_history ?? [];
  const documents = equipment.documents ?? [];

  // Handle close with exit animation: flip isOpen → false, then call onClose after 200ms
  const handleClose = React.useCallback(() => {
    setIsOpen(false);
    if (onClose) {
      setTimeout(onClose, 210); // Wait for exit animation (200ms + buffer)
    }
  }, [onClose]);

  const handleBack = React.useCallback(() => {
    if (onBack) {
      onBack();
    } else {
      handleClose();
    }
  }, [onBack, handleClose]);

  // Action handlers — wrap hook methods with refresh callback
  const handleCreateWorkOrder = React.useCallback(async () => {
    const result = await actions.createWorkOrder(equipment.id);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, equipment.id, onRefresh]);

  const handleReportFault = React.useCallback(async () => {
    const result = await actions.reportFault(equipment.id);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, equipment.id, onRefresh]);

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Equipment"
        title={equipment.name}
        onBack={handleBack}
        onClose={handleClose}
      />

      {/* Main content — padded top to clear fixed header (56px = h-14) */}
      <main
        className={cn(
          // Clear the fixed header
          'pt-14',
          // Lens body padding: 40px desktop, responsive
          'px-10 md:px-6 sm:px-4',
          // Max content width: 800px centered per spec
          'max-w-[800px] mx-auto',
          // Top breathing room below header
          'pb-12'
        )}
      >
        {/* ---------------------------------------------------------------
            Title block: title, status pill
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={equipment.name}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={equipmentVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Header action buttons (Create WO, Report Fault)
            Visible only if user has relevant permissions — hidden, not disabled
            --------------------------------------------------------------- */}
        {(perms.canCreateWorkOrder || perms.canReportFault) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {perms.canCreateWorkOrder && (
              <GhostButton
                onClick={handleCreateWorkOrder}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Create Work Order
              </GhostButton>
            )}
            {perms.canReportFault && (
              <GhostButton
                onClick={handleReportFault}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Report Fault
              </GhostButton>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px per spec
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Specifications Section
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <SpecificationsSection
            equipment={equipment}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Linked Faults Section
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LinkedFaultsSection
            faults={faults}
            equipmentId={equipment.id}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Linked Work Orders Section
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LinkedWorkOrdersSection
            workOrders={workOrders}
            equipmentId={equipment.id}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Maintenance History Section
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <MaintenanceHistorySection
            entries={maintenanceHistory}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Documents Section
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <DocumentsSection
            documents={documents}
            canLinkDocument={perms.canLinkDocument}
            stickyTop={56}
          />
        </div>
      </main>
    </LensContainer>
  );
});

EquipmentLens.displayName = 'EquipmentLens';

export default EquipmentLens;
