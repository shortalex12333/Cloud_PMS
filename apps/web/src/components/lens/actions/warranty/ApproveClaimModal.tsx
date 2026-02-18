'use client';

/**
 * ApproveClaimModal — Warranty Lens action modal (HOD+)
 *
 * Approves a submitted warranty claim with optional amount adjustment and notes.
 * HOD+ only — transitions status submitted → approved.
 * Role gate enforced at API level; button hidden via useWarrantyPermissions.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApproveClaimModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (approvedAmount?: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Claim display title (claim number + title) */
  claimTitle?: string;
  /** Original claimed amount for reference */
  claimedAmount?: number;
  /** Currency code e.g. "USD" */
  currency?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ApproveClaimModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  claimTitle,
  claimedAmount,
  currency = 'USD',
}: ApproveClaimModalProps) {
  const [approvedAmount, setApprovedAmount] = React.useState<string>(
    claimedAmount !== undefined ? claimedAmount.toFixed(2) : ''
  );
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    if (open) {
      setApprovedAmount(claimedAmount !== undefined ? claimedAmount.toFixed(2) : '');
      setNotes('');
      setTimeout(() => confirmRef.current?.focus(), 50);
    }
  }, [open, claimedAmount]);

  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedAmount = approvedAmount ? parseFloat(approvedAmount) : undefined;
    const result = await onSubmit(parsedAmount, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: 'Warranty claim approved' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to approve claim' });
    }
  };

  const parsedValue = parseFloat(approvedAmount);
  const amountDiffers =
    claimedAmount !== undefined &&
    !isNaN(parsedValue) &&
    parsedValue !== claimedAmount;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[var(--z-modal-backdrop)] bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="approve-claim-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-[var(--z-modal)]',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-lg',
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="approve-claim-title"
            className="text-[16px] font-semibold text-txt-primary leading-[1.4]"
          >
            Approve Warranty Claim
          </h2>
          {claimTitle && (
            <p className="mt-1 text-[13px] text-txt-secondary leading-[1.4] truncate">
              {claimTitle}
            </p>
          )}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Approved amount */}
            <div>
              <label
                htmlFor="approved-amount"
                className="block text-[13px] font-medium text-txt-primary mb-2"
              >
                Approved amount ({currency})
              </label>
              {claimedAmount !== undefined && (
                <p className="text-[12px] text-txt-tertiary mb-1.5">
                  Claimed: {currency} {claimedAmount.toFixed(2)}
                </p>
              )}
              <input
                id="approved-amount"
                type="number"
                step="0.01"
                min="0"
                value={approvedAmount}
                onChange={(e) => setApprovedAmount(e.target.value)}
                placeholder="0.00"
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-[14px] text-txt-primary placeholder:text-txt-tertiary',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-150'
                )}
              />
              {amountDiffers && (
                <p className="mt-1 text-[12px] text-status-warning">
                  Amount differs from claimed {currency} {claimedAmount!.toFixed(2)}
                </p>
              )}
            </div>

            {/* Approval notes */}
            <div>
              <label
                htmlFor="approval-notes"
                className="block text-[13px] font-medium text-txt-primary mb-2"
              >
                Approval notes (optional)
              </label>
              <textarea
                id="approval-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Add any notes about this approval decision..."
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-[14px] text-txt-primary placeholder:text-txt-tertiary',
                  'leading-[1.6] resize-y',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-150'
                )}
              />
            </div>
          </div>

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              ref={confirmRef}
              type="submit"
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {isLoading ? 'Approving...' : 'Approve Claim'}
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onDismiss={() => setToast(null)}
        />
      )}
    </>
  );
}

export default ApproveClaimModal;
