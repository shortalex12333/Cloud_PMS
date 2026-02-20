'use client';

/**
 * AddNoteModal — Work Order Lens action modal
 *
 * Adds a text note to the work order via add_wo_note action.
 * Uses design system tokens exclusively (surface-elevated, radius-lg).
 * Shows loading state during submission, handles errors via Toast.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AddNoteModalProps {
  /** Whether the modal is visible */
  open: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Called with the note text when user submits */
  onSubmit: (noteText: string) => Promise<{ success: boolean; error?: string }>;
  /** Whether the parent action is currently loading */
  isLoading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * AddNoteModal
 *
 * Modal overlay for adding a work order note.
 * Cancel clears the textarea; Escape key dismisses.
 */
export function AddNoteModal({ open, onClose, onSubmit, isLoading = false }: AddNoteModalProps) {
  const [text, setText] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Focus textarea when modal opens
  React.useEffect(() => {
    if (open) {
      setText('');
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [open]);

  // Dismiss on Escape
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
    const trimmed = text.trim();
    if (!trimmed) return;

    const result = await onSubmit(trimmed);
    if (result.success) {
      setToast({ type: 'success', message: 'Note added successfully' });
      setText('');
      // Close after short delay so user sees success
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to add note' });
    }
  };

  const handleCancel = () => {
    setText('');
    onClose();
  };

  const charCount = text.length;
  const isOverLimit = charCount > 2000;
  const canSubmit = text.trim().length > 0 && !isOverLimit && !isLoading;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={handleCancel}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-note-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          // Surface tokens
          'bg-surface-elevated border border-surface-border',
          // Shape - modal gets shadow per spec
          'rounded-lg shadow-modal',
          // Width
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="add-note-title"
            className="text-heading text-txt-primary"
          >
            Add Note
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            Document progress, findings, or observations.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4">
            <label
              htmlFor="note-text"
              className="block text-label text-txt-primary mb-2"
            >
              Note content
            </label>
            <textarea
              ref={textareaRef}
              id="note-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              placeholder="Enter your observation, finding, or note..."
              className={cn(
                'w-full',
                'bg-surface-primary border rounded-md',
                'px-3 py-2',
                'text-body text-txt-primary placeholder:text-txt-tertiary',
                'leading-[1.6]',
                'resize-y',
                'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                'transition-colors duration-fast',
                isOverLimit
                  ? 'border-status-critical'
                  : 'border-surface-border hover:border-surface-border-focus'
              )}
            />
            {/* Character count */}
            <div className="flex justify-end mt-1">
              <span
                className={cn(
                  'text-caption',
                  isOverLimit ? 'text-status-critical' : 'text-txt-tertiary'
                )}
              >
                {charCount}/2000
              </span>
            </div>
          </div>

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
            >
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={!canSubmit}
              aria-busy={isLoading}
            >
              {isLoading ? 'Adding...' : 'Add Note'}
            </PrimaryButton>
          </div>
        </form>
      </div>

      {/* Toast notification */}
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

