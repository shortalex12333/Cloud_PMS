'use client';

/**
 * AddHoursModal — Work Order Lens action modal
 *
 * Logs hours worked on a work order via add_wo_hours action.
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

export interface AddHoursModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (hours: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Work order display title */
  workOrderTitle?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AddHoursModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  workOrderTitle,
}: AddHoursModalProps) {
  const [hours, setHours] = React.useState('');
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const hoursRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setHours('');
      setNotes('');
      setTimeout(() => hoursRef.current?.focus(), 50);
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
    const hoursNum = parseFloat(hours);
    if (isNaN(hoursNum) || hoursNum <= 0) {
      setToast({ type: 'error', message: 'Please enter a valid number of hours' });
      return;
    }
    const result = await onSubmit(hoursNum, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: `${hoursNum} hours logged successfully` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to log hours' });
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
        aria-labelledby="add-hours-title"
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
            id="add-hours-title"
            className="text-heading text-txt-primary"
          >
            Log Hours
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
            {/* Hours input */}
            <div>
              <label
                htmlFor="hours-input"
                className="block text-label text-txt-primary mb-2"
              >
                Hours worked
              </label>
              <input
                ref={hoursRef}
                id="hours-input"
                type="number"
                step="0.25"
                min="0.25"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="e.g., 2.5"
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-body text-txt-primary placeholder:text-txt-tertiary',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-fast'
                )}
              />
            </div>

            {/* Notes input */}
            <div>
              <label
                htmlFor="hours-notes"
                className="block text-label text-txt-primary mb-2"
              >
                Notes (optional)
              </label>
              <textarea
                id="hours-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Describe work performed..."
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
              disabled={isLoading || !hours}
              aria-busy={isLoading}
            >
              {isLoading ? 'Logging...' : 'Log Hours'}
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

