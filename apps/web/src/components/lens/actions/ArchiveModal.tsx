'use client';

/**
 * ArchiveModal — Work Order Lens action modal
 *
 * Archives (soft-deletes) a work order via archive_work_order action.
 * Requires a deletion reason. Captain and manager only.
 * Uses design system tokens exclusively.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ArchiveModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with reason string on confirm */
  onSubmit: (reason: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Work order display title for confirmation copy */
  workOrderTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ArchiveModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  workOrderTitle,
}: ArchiveModalProps) {
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
    const trimmed = reason.trim();
    if (!trimmed) return;
    const result = await onSubmit(trimmed);
    if (result.success) {
      setToast({ type: 'success', message: 'Work order archived' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Archive failed' });
    }
  };

  const canSubmit = reason.trim().length > 0 && !isLoading;

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
        aria-labelledby="archive-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-lg',
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="archive-title"
            className="text-heading text-txt-primary"
          >
            Archive Work Order
          </h2>
          {workOrderTitle && (
            <p className="mt-1 text-label text-txt-secondary truncate">
              {workOrderTitle}
            </p>
          )}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Warning */}
            <div
              className={cn(
                'flex items-start gap-3 px-4 py-3',
                'bg-surface-primary border border-surface-border rounded-md'
              )}
            >
              {/* Warning icon */}
              <svg
                className="w-5 h-5 text-status-warning flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p className="text-label text-txt-primary">
                Archiving removes this work order from active views. The record is preserved
                in the audit log. This action requires a reason.
              </p>
            </div>

            {/* Reason input */}
            <div>
              <label
                htmlFor="archive-reason"
                className="block text-label text-txt-primary mb-2"
              >
                Reason for archiving <span className="text-status-critical">*</span>
              </label>
              <textarea
                ref={reasonRef}
                id="archive-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                placeholder="e.g., Duplicate of WO-2026-018, incorrect equipment..."
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-body text-txt-primary placeholder:text-txt-tertiary',
                  'resize-y',
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
            <PrimaryButton
              type="submit"
              disabled={!canSubmit}
              aria-busy={isLoading}
              className="bg-status-critical hover:bg-status-critical/90"
            >
              {isLoading ? 'Archiving...' : 'Archive'}
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

export default ArchiveModal;
