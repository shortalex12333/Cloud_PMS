'use client';

/**
 * RejectClaimModal — Warranty Lens action modal (HOD+)
 *
 * Rejects a submitted warranty claim with a required reason.
 * HOD+ only — transitions status submitted → rejected.
 * Role gate enforced at API level; button hidden via useWarrantyPermissions.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RejectClaimModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Claim display title (claim number + title) */
  claimTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RejectClaimModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  claimTitle,
}: RejectClaimModalProps) {
  const [reason, setReason] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const reasonRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    if (open) {
      setReason('');
      setTimeout(() => reasonRef.current?.focus(), 50);
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
    if (!reason.trim()) return;
    const result = await onSubmit(reason.trim());
    if (result.success) {
      setToast({ type: 'success', message: 'Warranty claim rejected' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to reject claim' });
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
        aria-labelledby="reject-claim-title"
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
            id="reject-claim-title"
            className="text-[16px] font-semibold text-txt-primary leading-[1.4]"
          >
            Reject Warranty Claim
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
            <p className="text-[14px] text-txt-primary leading-[1.6]">
              Reject this warranty claim. A rejection reason is required and will be
              recorded in the audit history.
            </p>

            {/* Rejection reason (required) */}
            <div>
              <label
                htmlFor="rejection-reason"
                className="block text-[13px] font-medium text-txt-primary mb-2"
              >
                Rejection reason <span className="text-status-critical">*</span>
              </label>
              <textarea
                id="rejection-reason"
                ref={reasonRef}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                required
                placeholder="Explain why this claim is being rejected..."
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-[14px] text-txt-primary placeholder:text-txt-tertiary',
                  'leading-[1.6] resize-y',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-fast'
                )}
              />
            </div>
          </div>

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <button
              type="submit"
              disabled={isLoading || !reason.trim()}
              aria-busy={isLoading}
              className={cn(
                'px-4 py-2 min-h-9 rounded-md text-[13px] font-semibold',
                'text-txt-inverse bg-status-critical',
                'hover:opacity-90 transition-opacity duration-fast',
                'focus:outline-none focus:ring-2 focus:ring-status-critical focus:ring-offset-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? 'Rejecting...' : 'Reject Claim'}
            </button>
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

export default RejectClaimModal;
