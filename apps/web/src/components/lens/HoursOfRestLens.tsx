'use client';

/**
 * HoursOfRestLens - Full-screen entity lens for STCW Hours of Rest compliance.
 *
 * Per CLAUDE.md and UI_SPEC.md — mirrors WorkOrderLens structure exactly:
 * - Fixed LensHeader (56px): back button, "Hours of Rest" overline, close button
 * - LensTitleBlock: crew name — period, compliance status pill
 * - VitalSignsRow: 5 indicators (compliance, crew member, period, violations, sign-off)
 * - Section containers: DailyLog (visual timeline), Warnings (STCW violations), MonthlySignOff
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * STCW Compliance Colours (per plan spec):
 * - Green (success): Meets minimum rest requirements
 * - Amber (warning): Close to violation threshold
 * - Red (critical): STCW violation — requires acknowledgment
 *
 * NO UUID visible anywhere in the header.
 * Status colour mappers are local to this lens (domain-specific logic).
 *
 * FE-03-03: Hours of Rest Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';

// HOR-specific sections
import { DailyLogSection } from './sections/hor/DailyLogSection';
import { WarningsSection } from './sections/hor/WarningsSection';
import { MonthlySignOffSection } from './sections/hor/MonthlySignOffSection';

// Action hook + permissions
import { useHoursOfRestActions, useHoursOfRestPermissions } from '@/hooks/useHoursOfRestActions';

// Shared UI
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface RestPeriod {
  /** Start time as "HH:MM" (24-hour) */
  start: string;
  /** End time as "HH:MM" (24-hour) */
  end: string;
  /** Duration in hours */
  hours: number;
}

export interface DailyLogEntry {
  id: string;
  /** ISO date: "2026-02-01" */
  record_date: string;
  /** Array of rest periods logged for this day */
  rest_periods: RestPeriod[];
  /** Total rest hours for the day */
  total_rest_hours: number;
  /**
   * Compliance status for this day.
   * compliant = meets minimum, warning = close to threshold, violation = STCW breach
   */
  compliance_status: 'compliant' | 'warning' | 'violation';
}

export interface HorWarning {
  id: string;
  /** ISO date when the warning was raised */
  warning_date: string;
  /** Human-readable violation description */
  description: string;
  /** Severity of the STCW violation */
  severity: 'warning' | 'violation';
  /** Whether the crew member has acknowledged this warning */
  acknowledged_at?: string;
  /** Who acknowledged it */
  acknowledged_by?: string;
}

export interface MonthlySignOff {
  id: string;
  /** "YYYY-MM" — e.g., "2026-02" */
  month: string;
  /** Department: "deck" | "engine" | "interior" */
  department: string;
  /** Whether the crew member has signed */
  crew_signed_at?: string;
  /** Whether the HOD has signed */
  hod_signed_at?: string;
  /** Whether the captain has countersigned */
  captain_signed_at?: string;
  /** Overall sign-off status */
  status: 'pending' | 'crew_signed' | 'hod_signed' | 'captain_signed' | 'complete';
}

export interface HoursOfRestLensData {
  id: string;
  /** Crew member UUID */
  user_id: string;
  /** Display name of the crew member */
  crew_name: string;
  /** Department: "deck" | "engine" | "interior" */
  department?: string;
  /**
   * Compliance status for the displayed period.
   * compliant = all days OK, warning = close to threshold, violation = STCW breach
   */
  compliance_status: 'compliant' | 'warning' | 'violation';
  /** Period start — ISO date "2026-02-01" */
  period_start: string;
  /** Period end — ISO date "2026-02-28" */
  period_end: string;
  /** Number of STCW violation days in the period */
  violations_count: number;
  /** Sign-off status for the current month */
  signoff_status: 'signed' | 'pending' | 'not_required';
  /** Daily log entries for the period */
  daily_log?: DailyLogEntry[];
  /** Active STCW warnings (unacknowledged violations) */
  warnings?: HorWarning[];
  /** Current month's sign-off record */
  monthly_signoff?: MonthlySignOff;
}

export interface HoursOfRestLensProps {
  /** The hours of rest data to render */
  hoursOfRest: HoursOfRestLensData;
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
// Colour mapping helpers — domain-specific, local to this lens
// ---------------------------------------------------------------------------

/**
 * Map STCW compliance status to StatusPill color level.
 *
 * Green = compliant (meets minimum rest)
 * Amber = warning (close to violation threshold)
 * Red = violation (STCW breach — requires acknowledgment)
 */
function mapComplianceToColor(
  status: 'compliant' | 'warning' | 'violation'
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'violation':
      return 'critical';
    case 'warning':
      return 'warning';
    case 'compliant':
    default:
      return 'success';
  }
}

/**
 * Human-readable compliance status label.
 */
function formatComplianceLabel(status: 'compliant' | 'warning' | 'violation'): string {
  switch (status) {
    case 'violation':
      return 'STCW Violation';
    case 'warning':
      return 'Near Threshold';
    case 'compliant':
    default:
      return 'Compliant';
  }
}

/**
 * Format a period range for display.
 * "2026-02-01" + "2026-02-28" → "Feb 1–28, 2026"
 */
function formatPeriod(startIso: string, endIso: string): string {
  const start = new Date(startIso + 'T00:00:00Z');
  const end = new Date(endIso + 'T00:00:00Z');

  const startMonth = start.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' });
  const endMonth = end.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' });
  const startDay = start.getUTCDate();
  const endDay = end.getUTCDate();
  const year = start.getUTCFullYear();

  if (startMonth === endMonth) {
    return `${startMonth} ${startDay}–${endDay}, ${year}`;
  }

  return `${startMonth} ${startDay} – ${endMonth} ${endDay}, ${year}`;
}

/**
 * Format violations count for display.
 */
function formatViolationsLabel(count: number): string {
  if (count === 0) return 'None';
  return `${count} violation${count === 1 ? '' : 's'}`;
}

/**
 * Format sign-off status for display.
 */
function formatSignoffLabel(status: 'signed' | 'pending' | 'not_required'): string {
  switch (status) {
    case 'signed':
      return 'Signed';
    case 'not_required':
      return 'Not Required';
    case 'pending':
    default:
      return 'Pending';
  }
}

// ---------------------------------------------------------------------------
// HoursOfRestLens component
// ---------------------------------------------------------------------------

/**
 * HoursOfRestLens — Full-screen entity lens for STCW hours of rest compliance.
 *
 * Usage:
 * ```tsx
 * <HoursOfRestLens
 *   hoursOfRest={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const HoursOfRestLens = React.forwardRef<
  HTMLDivElement,
  HoursOfRestLensProps
>(({ hoursOfRest, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility for sign-off flow
  const [signOffOpen, setSignOffOpen] = React.useState(false);

  // Actions and permissions
  const actions = useHoursOfRestActions(hoursOfRest.user_id);
  const perms = useHoursOfRestPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values — never expose raw UUID
  const displayTitle = `${hoursOfRest.crew_name} — Hours of Rest`;

  const complianceColor = mapComplianceToColor(hoursOfRest.compliance_status);
  const complianceLabel = formatComplianceLabel(hoursOfRest.compliance_status);
  const periodLabel = formatPeriod(hoursOfRest.period_start, hoursOfRest.period_end);
  const violationsLabel = formatViolationsLabel(hoursOfRest.violations_count);
  const signoffLabel = formatSignoffLabel(hoursOfRest.signoff_status);

  // Sign-off color: signed = success, pending = warning, not_required = neutral
  const signoffColor =
    hoursOfRest.signoff_status === 'signed'
      ? 'success'
      : hoursOfRest.signoff_status === 'pending'
      ? 'warning'
      : 'neutral';

  // Violations color: none = neutral, any violations = critical, warnings = warning
  const violationsColor =
    hoursOfRest.violations_count > 0
      ? 'critical'
      : 'neutral';

  // Build the 5 vital signs per plan spec
  const horVitalSigns: VitalSign[] = [
    {
      label: 'Compliance',
      value: complianceLabel,
      color: complianceColor,
    },
    {
      label: 'Crew Member',
      value: hoursOfRest.crew_name,
    },
    {
      label: 'Period',
      value: periodLabel,
    },
    {
      label: 'Violations',
      value: violationsLabel,
      color: violationsColor,
    },
    {
      label: 'Sign-off',
      value: signoffLabel,
      color: signoffColor,
    },
  ];

  // Section data (safe fallbacks)
  const dailyLog = hoursOfRest.daily_log ?? [];
  const warnings = hoursOfRest.warnings ?? [];
  const monthlySignoff = hoursOfRest.monthly_signoff ?? null;

  // Derived state
  const hasActiveViolations = hoursOfRest.compliance_status === 'violation';
  const canSignOff =
    perms.canSignOff &&
    monthlySignoff !== null &&
    monthlySignoff.status !== 'complete';

  // Action handlers
  const handleAcknowledgeWarning = React.useCallback(
    async (warningId: string) => {
      const result = await actions.acknowledgeWarning(warningId);
      if (result.success) onRefresh?.();
      return result;
    },
    [actions, onRefresh]
  );

  const handleSignOff = React.useCallback(async () => {
    if (!monthlySignoff) return;
    const result = await actions.signMonthly(monthlySignoff.id, 'crew');
    if (result.success) {
      setSignOffOpen(false);
      onRefresh?.();
    }
    return result;
  }, [actions, monthlySignoff, onRefresh]);

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
        entityType="Hours of Rest"
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
          // Bottom breathing room
          'pb-12'
        )}
      >
        {/* ---------------------------------------------------------------
            Title block: crew name + compliance status pill
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={`${hoursOfRest.department ? `${hoursOfRest.department.charAt(0).toUpperCase() + hoursOfRest.department.slice(1)} Department · ` : ''}${periodLabel}`}
            status={{
              label: complianceLabel,
              color: complianceColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={horVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Header action buttons — Sign Off (captain/HOD), hidden per role
            --------------------------------------------------------------- */}
        {(canSignOff || (perms.canLogHours && hoursOfRest.compliance_status !== 'compliant')) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {/* Sign off — visible when sign-off is pending and user has permission */}
            {canSignOff && (
              <PrimaryButton
                onClick={() => setSignOffOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Sign Off Month
              </PrimaryButton>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            STCW Violation banner — shown when there are active violations
            --------------------------------------------------------------- */}
        {hasActiveViolations && (
          <div
            role="alert"
            className={cn(
              'mt-4 px-4 py-3 rounded-md',
              'bg-status-critical/10 border border-status-critical/30',
              'flex items-start gap-3'
            )}
          >
            <span className="text-status-critical text-[18px] leading-none mt-0.5">
              &#9888;
            </span>
            <div>
              <p className="text-[13px] font-semibold text-status-critical">
                STCW Violation — {hoursOfRest.violations_count} violation{hoursOfRest.violations_count === 1 ? '' : 's'}
              </p>
              <p className="text-[13px] text-txt-secondary mt-0.5">
                Rest requirements not met. Violations require acknowledgment below.
              </p>
            </div>
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
            Daily Log Section — visual timeline of rest vs work per day
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <DailyLogSection
            entries={dailyLog}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Warnings Section — STCW violations with acknowledge button
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <WarningsSection
            warnings={warnings}
            onAcknowledge={handleAcknowledgeWarning}
            canAcknowledge={perms.canAcknowledgeWarning}
            isLoading={actions.isLoading}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Monthly Sign-Off Section — sign-off status + signature flow
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <MonthlySignOffSection
            signoff={monthlySignoff}
            onSignOff={handleSignOff}
            canSignOff={canSignOff}
            isLoading={actions.isLoading}
            signOffOpen={signOffOpen}
            onSignOffOpenChange={setSignOffOpen}
            stickyTop={56}
          />
        </div>
      </main>
    </LensContainer>
  );
});

HoursOfRestLens.displayName = 'HoursOfRestLens';

export default HoursOfRestLens;
