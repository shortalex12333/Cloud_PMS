import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import type { MonthlySignOff } from '../../types';

// ============================================================================
// TYPES
// ============================================================================

export interface MonthlySignOffSectionProps {
  /** The current month's sign-off record, or null if none exists yet */
  signoff: MonthlySignOff | null;
  /** Callback to sign off the current month */
  onSignOff: () => Promise<{ success: boolean; error?: string } | undefined>;
  /** Whether the current user can sign off */
  canSignOff: boolean;
  /** Whether an action is in flight */
  isLoading: boolean;
  /** Whether the sign-off confirmation UI is open */
  signOffOpen: boolean;
  /** Callback to open/close the sign-off confirmation */
  onSignOffOpenChange: (open: boolean) => void;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format "YYYY-MM" to display month name.
 * "2026-02" → "February 2026"
 */
function formatMonth(yearMonth: string): string {
  const [year, month] = yearMonth.split('-').map(Number);
  const date = new Date(year!, (month ?? 1) - 1, 1);
  return date.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

/**
 * Format ISO timestamp for signature display.
 */
function formatSignedAt(isoString: string): string {
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

/**
 * Map sign-off status to display label.
 */
function formatStatus(status: MonthlySignOff['status']): string {
  switch (status) {
    case 'complete':
      return 'Complete';
    case 'captain_signed':
      return 'Captain Signed';
    case 'hod_signed':
      return 'HOD Signed';
    case 'crew_signed':
      return 'Crew Signed';
    case 'pending':
    default:
      return 'Pending';
  }
}

// ============================================================================
// SIGNATURE ROW
// ============================================================================

interface SignatureRowProps {
  label: string;
  signedAt?: string;
}

function SignatureRow({ label, signedAt }: SignatureRowProps) {
  const isSigned = !!signedAt;

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-surface-border-subtle last:border-b-0">
      {/* Status indicator */}
      <span
        className={cn(
          'inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-bold flex-shrink-0',
          isSigned
            ? 'bg-status-success text-white'
            : 'bg-surface-raised text-txt-tertiary border border-surface-border'
        )}
        aria-label={isSigned ? 'Signed' : 'Unsigned'}
      >
        {isSigned ? '✓' : '○'}
      </span>

      {/* Role label */}
      <span className="text-[14px] font-medium text-txt-primary w-24 flex-shrink-0">
        {label}
      </span>

      {/* Signed at or pending */}
      {isSigned ? (
        <span className="text-[13px] text-txt-secondary">
          Signed {formatSignedAt(signedAt!)}
        </span>
      ) : (
        <span className="text-[13px] text-txt-tertiary italic">Awaiting signature</span>
      )}
    </div>
  );
}

// ============================================================================
// SIGN-OFF CONFIRMATION PANEL
// ============================================================================

interface SignOffConfirmProps {
  month: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

function SignOffConfirmPanel({ month, onConfirm, onCancel, isLoading }: SignOffConfirmProps) {
  return (
    <div
      className={cn(
        'mt-4 p-4 rounded-md',
        'bg-surface-raised border border-surface-border',
      )}
      role="dialog"
      aria-label="Sign off monthly hours of rest"
    >
      <h4 className="text-[14px] font-semibold text-txt-primary mb-1">
        Sign Off: {formatMonth(month)}
      </h4>
      <p className="text-[13px] text-txt-secondary mb-4 leading-[1.5]">
        By signing, you confirm that the hours of rest records for {formatMonth(month)} are
        accurate and comply with STCW requirements. This action creates a legally binding record
        and cannot be undone.
      </p>

      <div className="flex items-center gap-2">
        <PrimaryButton
          onClick={onConfirm}
          disabled={isLoading}
          className="text-[13px] min-h-9 px-4 py-2"
        >
          {isLoading ? 'Signing...' : 'Confirm Signature'}
        </PrimaryButton>
        <button
          onClick={onCancel}
          disabled={isLoading}
          className={cn(
            'text-[13px] px-4 py-2 rounded-md min-h-9',
            'text-txt-secondary hover:text-txt-primary',
            'hover:bg-surface-raised transition-colors duration-fast',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// MONTHLY SIGN-OFF SECTION
// ============================================================================

/**
 * MonthlySignOffSection — Shows sign-off status and signature flow for the month.
 *
 * Per plan spec: sign-off status, signature if required.
 * Shows three signature rows: Crew, HOD, Captain.
 * When sign-off is pending, a "Sign Off Month" button triggers the confirmation panel.
 * Confirmation panel shows the legal declaration before committing.
 *
 * Empty state: when no sign-off record exists for the period (before month ends or
 * before it has been created by HOD).
 */
export function MonthlySignOffSection({
  signoff,
  onSignOff,
  canSignOff,
  isLoading,
  signOffOpen,
  onSignOffOpenChange,
  stickyTop,
}: MonthlySignOffSectionProps) {
  if (!signoff) {
    return (
      <SectionContainer
        title="Monthly Sign-off"
        stickyTop={stickyTop}
      >
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No sign-off record for this period. Sign-off records are created by the HOD at month end.
          </p>
        </div>
      </SectionContainer>
    );
  }

  const statusLabel = formatStatus(signoff.status);
  const isComplete = signoff.status === 'complete';
  const monthLabel = formatMonth(signoff.month);

  return (
    <SectionContainer
      title="Monthly Sign-off"
      stickyTop={stickyTop}
    >
      {/* Month + status header */}
      <div className="px-5 py-3 border-b border-surface-border-subtle flex items-center justify-between">
        <div>
          <p className="text-[14px] font-semibold text-txt-primary">{monthLabel}</p>
          <p className="text-[12px] text-txt-tertiary capitalize">
            {signoff.department} department
          </p>
        </div>
        <span
          className={cn(
            'text-[12px] font-semibold px-2.5 py-1 rounded-full',
            isComplete
              ? 'bg-status-success/15 text-status-success'
              : 'bg-status-warning/15 text-status-warning'
          )}
        >
          {statusLabel}
        </span>
      </div>

      {/* Signature rows */}
      <div className="px-5 py-1">
        <SignatureRow label="Crew" signedAt={signoff.crew_signed_at} />
        <SignatureRow label="HOD" signedAt={signoff.hod_signed_at} />
        <SignatureRow label="Captain" signedAt={signoff.captain_signed_at} />
      </div>

      {/* Sign-off CTA — shown when pending and user has permission */}
      {canSignOff && !isComplete && (
        <div className="px-5 pb-4">
          {signOffOpen ? (
            <SignOffConfirmPanel
              month={signoff.month}
              onConfirm={onSignOff}
              onCancel={() => onSignOffOpenChange(false)}
              isLoading={isLoading}
            />
          ) : (
            <button
              onClick={() => onSignOffOpenChange(true)}
              disabled={isLoading}
              className={cn(
                'mt-3 text-[13px] font-medium text-brand-interactive',
                'hover:text-brand-hover transition-colors duration-fast',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-lg',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Sign off {monthLabel} →
            </button>
          )}
        </div>
      )}

      {/* Complete state — green confirmation */}
      {isComplete && (
        <div className="px-5 pb-4">
          <div className="mt-3 flex items-center gap-2 text-[13px] text-status-success">
            <span className="text-[16px]" aria-hidden="true">✓</span>
            <span>Sign-off complete — all required signatures received</span>
          </div>
        </div>
      )}
    </SectionContainer>
  );
}

export default MonthlySignOffSection;
