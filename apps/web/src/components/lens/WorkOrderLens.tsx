'use client';

/**
 * WorkOrderLens - Reference implementation for the lens header pattern.
 *
 * Per CLAUDE.md and UI_SPEC.md:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: 28px display title, status + priority pills
 * - VitalSignsRow: 5 indicators (status, priority, parts, created, equipment)
 * - NO UUID visible anywhere in the header
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * This is the reference implementation — all other lenses inherit this structure.
 *
 * FE-01-05: Full-Screen Lens Layout + Glass Transitions
 */

import * as React from 'react';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface WorkOrderLensData {
  id: string;
  /** Human-readable number e.g. "WO-2026-001" — NEVER show raw id UUID */
  wo_number?: string;
  title: string;
  description?: string;
  /** Status enum: draft | open | in_progress | pending_parts | completed | closed | cancelled */
  status: string;
  /** Priority enum: low | medium | high | critical */
  priority: string;
  equipment_id?: string;
  /** Denormalized equipment name for display */
  equipment_name?: string;
  assigned_to?: string;
  assigned_to_name?: string;
  created_at: string;
  completed_at?: string;
  due_date?: string;
  is_overdue?: boolean;
  days_open?: number;
  /** Count of linked work order parts */
  parts_count?: number;
}

export interface WorkOrderLensProps {
  /** The work order data to render */
  workOrder: WorkOrderLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers
// ---------------------------------------------------------------------------

/**
 * Map work order status string to StatusPill color level.
 * Per UI_SPEC.md status colour mapping.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'overdue':
    case 'cancelled':
      return 'critical';
    case 'in_progress':
    case 'pending_parts':
      return 'warning';
    case 'completed':
    case 'closed':
      return 'success';
    case 'draft':
    case 'open':
    default:
      return 'neutral';
  }
}

/**
 * Map work order priority string to StatusPill color level.
 */
function mapPriorityToColor(
  priority: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (priority) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'warning';
    case 'medium':
      return 'neutral';
    case 'low':
    default:
      return 'neutral';
  }
}

/**
 * Format a status enum value to a human-readable display label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    open: 'Open',
    in_progress: 'In Progress',
    pending_parts: 'Pending Parts',
    completed: 'Completed',
    closed: 'Closed',
    cancelled: 'Cancelled',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Format a priority enum value to a human-readable display label.
 */
function formatPriorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

// ---------------------------------------------------------------------------
// WorkOrderLens component
// ---------------------------------------------------------------------------

/**
 * WorkOrderLens — Full-screen entity lens for work orders.
 *
 * Usage:
 * ```tsx
 * <WorkOrderLens
 *   workOrder={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const WorkOrderLens = React.forwardRef<
  HTMLDivElement,
  WorkOrderLensProps
>(({ workOrder, onBack, onClose, className }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  const displayTitle = workOrder.wo_number
    ? `${workOrder.wo_number} — ${workOrder.title}`
    : workOrder.title;

  const statusColor = mapStatusToColor(workOrder.status);
  const priorityColor = mapPriorityToColor(workOrder.priority);
  const statusLabel = formatStatusLabel(workOrder.status);
  const priorityLabel = formatPriorityLabel(workOrder.priority);

  // Build the 5 vital signs as per plan spec
  const workOrderVitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Priority',
      value: priorityLabel,
      color: priorityColor,
    },
    {
      label: 'Parts',
      value:
        workOrder.parts_count !== undefined
          ? `${workOrder.parts_count} part${workOrder.parts_count === 1 ? '' : 's'}`
          : '0 parts',
    },
    {
      label: 'Created',
      value: workOrder.created_at
        ? formatRelativeTime(workOrder.created_at)
        : '—',
    },
    {
      label: 'Equipment',
      value: workOrder.equipment_name ?? 'None',
      // Equipment link is teal and clickable when equipment_id is present
      href: workOrder.equipment_id
        ? `/equipment/${workOrder.equipment_id}`
        : undefined,
    },
  ];

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

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Work Order"
        title={displayTitle}
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
            Title block: title, status/priority pills
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={workOrder.description}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
            priority={{
              label: priorityLabel,
              color: priorityColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={workOrderVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px per spec
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Content sections placeholder
            (Notes, Parts, Attachments, History — implemented in future plans)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          {/* Notes section, Parts section, History etc. will follow here */}
        </div>
      </main>
    </LensContainer>
  );
});

WorkOrderLens.displayName = 'WorkOrderLens';

export default WorkOrderLens;
