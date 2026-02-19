import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import type { HorWarning } from '../../types';

// ============================================================================
// TYPES
// ============================================================================

export interface WarningsSectionProps {
  /** STCW warnings to display */
  warnings: HorWarning[];
  /** Callback to acknowledge a warning by ID */
  onAcknowledge: (warningId: string) => Promise<{ success: boolean; error?: string }>;
  /** Whether the current user can acknowledge warnings */
  canAcknowledge: boolean;
  /** Whether an action is in flight */
  isLoading: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format warning date for display.
 * "2026-02-15" → "15 Feb 2026"
 */
function formatWarningDate(isoDate: string): string {
  const date = new Date(isoDate + 'T00:00:00Z');
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/**
 * Format acknowledged timestamp.
 */
function formatAcknowledgedAt(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }) + ' at ' + date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ============================================================================
// WARNING ROW
// ============================================================================

interface WarningRowProps {
  warning: HorWarning;
  onAcknowledge: (id: string) => Promise<{ success: boolean; error?: string }>;
  canAcknowledge: boolean;
  isLoading: boolean;
}

function WarningRow({ warning, onAcknowledge, canAcknowledge, isLoading }: WarningRowProps) {
  const [acknowledging, setAcknowledging] = React.useState(false);
  const [ackError, setAckError] = React.useState<string | null>(null);

  const isAcknowledged = !!warning.acknowledged_at;
  const isViolation = warning.severity === 'violation';

  const handleAcknowledge = async () => {
    setAcknowledging(true);
    setAckError(null);

    try {
      const result = await onAcknowledge(warning.id);
      if (!result.success) {
        setAckError(result.error ?? 'Failed to acknowledge warning');
      }
    } finally {
      setAcknowledging(false);
    }
  };

  return (
    <div
      className={cn(
        'px-5 py-4',
        'border-b border-surface-border-subtle last:border-b-0',
        // Tint unacknowledged violations with a critical background
        isViolation && !isAcknowledged && 'bg-status-critical/5'
      )}
    >
      <div className="flex items-start gap-3">
        {/* Severity indicator dot */}
        <span
          className={cn(
            'inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1',
            isViolation ? 'bg-status-critical' : 'bg-status-warning'
          )}
          aria-hidden="true"
        />

        <div className="flex-1 min-w-0">
          {/* Warning date + severity label */}
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={cn(
                'text-[12px] font-semibold uppercase tracking-wide',
                isViolation ? 'text-status-critical' : 'text-status-warning'
              )}
            >
              {isViolation ? 'STCW Violation' : 'Warning'}
            </span>
            <span className="text-[12px] text-txt-tertiary">
              {formatWarningDate(warning.warning_date)}
            </span>
          </div>

          {/* Warning description */}
          <p className="text-[14px] text-txt-primary leading-[1.5]">
            {warning.description}
          </p>

          {/* Acknowledged indicator */}
          {isAcknowledged && (
            <p className="mt-1.5 text-[12px] text-status-success">
              Acknowledged
              {warning.acknowledged_by && ` by ${warning.acknowledged_by}`}
              {warning.acknowledged_at && ` — ${formatAcknowledgedAt(warning.acknowledged_at)}`}
            </p>
          )}

          {/* Error state */}
          {ackError && (
            <p className="mt-1.5 text-[12px] text-status-critical">{ackError}</p>
          )}
        </div>

        {/* Acknowledge button — only shown when not yet acknowledged and user has permission */}
        {!isAcknowledged && canAcknowledge && (
          <GhostButton
            onClick={handleAcknowledge}
            disabled={isLoading || acknowledging}
            className={cn(
              'text-[12px] min-h-8 px-3 py-1.5 flex-shrink-0',
              isViolation
                ? 'text-status-critical border-status-critical/40 hover:bg-status-critical/10'
                : 'text-status-warning border-status-warning/40 hover:bg-status-warning/10'
            )}
          >
            {acknowledging ? 'Acknowledging...' : 'Acknowledge'}
          </GhostButton>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// WARNINGS SECTION
// ============================================================================

/**
 * WarningsSection — Shows STCW compliance violations with acknowledge action.
 *
 * Per plan spec: STCW violations with acknowledge button.
 * - Critical (red): STCW violation — must be acknowledged
 * - Warning (amber): Close to threshold — informational
 *
 * Unacknowledged violations have a subtle red tint on the row.
 * Acknowledged violations show a green confirmation timestamp.
 *
 * Empty state: contextual message when the crew member has no violations.
 */
export function WarningsSection({
  warnings,
  onAcknowledge,
  canAcknowledge,
  isLoading,
  stickyTop,
}: WarningsSectionProps) {
  const unacknowledgedCount = warnings.filter((w) => !w.acknowledged_at).length;

  return (
    <SectionContainer
      title="STCW Warnings"
      count={warnings.length > 0 ? warnings.length : undefined}
      stickyTop={stickyTop}
    >
      {warnings.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No active warnings. Rest requirements are being met.
          </p>
        </div>
      ) : (
        <>
          {/* Summary banner when there are unacknowledged violations */}
          {unacknowledgedCount > 0 && (
            <div className="px-5 py-2.5 bg-status-critical/10 border-b border-status-critical/20">
              <p className="text-[13px] font-medium text-status-critical">
                {unacknowledgedCount} unacknowledged violation{unacknowledgedCount === 1 ? '' : 's'} — acknowledgment required for compliance record
              </p>
            </div>
          )}

          <div className="-mx-4">
            {warnings.map((warning) => (
              <WarningRow
                key={warning.id}
                warning={warning}
                onAcknowledge={onAcknowledge}
                canAcknowledge={canAcknowledge}
                isLoading={isLoading}
              />
            ))}
          </div>
        </>
      )}
    </SectionContainer>
  );
}

export default WarningsSection;
