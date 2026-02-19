'use client';

/**
 * SubmitClaimModal — Warranty Lens action modal
 *
 * Submits a draft warranty claim for approval.
 * Requires confirmation — transitions status draft → submitted.
 * Available to all crew who can edit the claim.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SubmitClaimModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Claim display title (claim number + title) */
  claimTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SubmitClaimModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  claimTitle,
}: SubmitClaimModalProps) {
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    if (open) {
      setTimeout(() => confirmRef.current?.focus(), 50);
    }
  }, [open]);

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
    const result = await onSubmit();
    if (result.success) {
      setToast({ type: 'success', message: 'Claim submitted for approval' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to submit claim' });
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="submit-claim-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="submit-claim-title"
            className="text-[16px] font-semibold text-txt-primary leading-[1.4]"
          >
            Submit Claim for Approval
          </h2>
          {claimTitle && (
            <p className="mt-1 text-[13px] text-txt-secondary leading-[1.4] truncate">
              {claimTitle}
            </p>
          )}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4">
            <p className="text-[14px] text-txt-primary leading-[1.6]">
              Submit this warranty claim for HOD review and approval. Once submitted,
              the claim cannot be edited without approval.
            </p>
            <p className="mt-3 text-[13px] text-txt-secondary leading-[1.5]">
              Status will change from <strong>Draft</strong> to <strong>Submitted</strong>.
            </p>
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
              {isLoading ? 'Submitting...' : 'Submit Claim'}
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

export default SubmitClaimModal;
