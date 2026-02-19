'use client';

/**
 * MarkCompleteModal — Work Order Lens action modal
 *
 * Closes/completes a work order via close_work_order action.
 * Shows a confirmation prompt with optional completion notes.
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

export interface MarkCompleteModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (completionNotes?: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Work order display title (WO number + title) */
  workOrderTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MarkCompleteModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  workOrderTitle,
}: MarkCompleteModalProps) {
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    if (open) {
      setNotes('');
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
    const result = await onSubmit(notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: 'Work order marked as complete' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to complete work order' });
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
        aria-labelledby="mark-complete-title"
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
            id="mark-complete-title"
            className="text-heading text-txt-primary"
          >
            Mark as Complete
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
            {/* Confirmation text */}
            <p className="text-body text-txt-primary">
              Confirm you want to mark this work order as complete. This action creates an
              audit log entry and transitions the status to <strong>Closed</strong>.
            </p>

            {/* Optional completion notes */}
            <div>
              <label
                htmlFor="completion-notes"
                className="block text-label text-txt-primary mb-2"
              >
                Completion notes (optional)
              </label>
              <textarea
                id="completion-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Describe work completed, parts used, any follow-up needed..."
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
              ref={confirmRef}
              type="submit"
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {isLoading ? 'Completing...' : 'Mark Complete'}
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

export default MarkCompleteModal;
