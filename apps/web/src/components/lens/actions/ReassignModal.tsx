'use client';

/**
 * ReassignModal — Work Order Lens action modal
 *
 * Reassigns the work order to a different crew member via assign_work_order.
 * For HOD+ roles; uses design system tokens exclusively.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CrewMember {
  id: string;
  display_name: string;
  role?: string;
}

export interface ReassignModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with new assignee ID on confirm */
  onSubmit: (assigneeId: string) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Available crew members to reassign to */
  crew?: CrewMember[];
  /** Current assignee ID (to pre-exclude) */
  currentAssigneeId?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReassignModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  crew = [],
  currentAssigneeId,
}: ReassignModalProps) {
  const [selectedId, setSelectedId] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const selectRef = React.useRef<HTMLSelectElement>(null);

  React.useEffect(() => {
    if (open) {
      setSelectedId('');
      setTimeout(() => selectRef.current?.focus(), 50);
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

  const availableCrew = crew.filter((m) => m.id !== currentAssigneeId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    const result = await onSubmit(selectedId);
    if (result.success) {
      setToast({ type: 'success', message: 'Work order reassigned' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Reassignment failed' });
    }
  };

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
        aria-labelledby="reassign-title"
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
            id="reassign-title"
            className="text-[16px] font-semibold text-txt-primary leading-[1.4]"
          >
            Reassign Work Order
          </h2>
          <p className="mt-1 text-[13px] text-txt-secondary leading-[1.4]">
            Select a crew member to take ownership.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4">
            <label
              htmlFor="reassign-select"
              className="block text-[13px] font-medium text-txt-primary mb-2"
            >
              Assign to
            </label>

            {availableCrew.length === 0 ? (
              <p className="text-[14px] text-txt-secondary">
                No other crew members available.
              </p>
            ) : (
              <select
                ref={selectRef}
                id="reassign-select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-[14px] text-txt-primary',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-150'
                )}
              >
                <option value="">Select crew member...</option>
                {availableCrew.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.display_name}
                    {member.role && ` — ${member.role}`}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={!selectedId || isLoading || availableCrew.length === 0}
              aria-busy={isLoading}
            >
              {isLoading ? 'Reassigning...' : 'Reassign'}
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

export default ReassignModal;
