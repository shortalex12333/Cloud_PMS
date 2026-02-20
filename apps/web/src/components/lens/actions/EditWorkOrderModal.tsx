'use client';

/**
 * EditWorkOrderModal — Work Order Lens action modal
 *
 * Updates editable work order fields via update_work_order action.
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

export interface WorkOrderEditData {
  title?: string;
  description?: string;
  priority?: string;
  due_date?: string;
  type?: string;
}

export interface EditWorkOrderModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (changes: WorkOrderEditData) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Current work order data for pre-filling */
  currentData?: {
    title?: string;
    description?: string;
    priority?: string;
    due_date?: string;
    type?: string;
  };
}

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'routine', label: 'Routine' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

const TYPE_OPTIONS = [
  { value: 'scheduled', label: 'Scheduled Maintenance' },
  { value: 'unscheduled', label: 'Unscheduled Repair' },
  { value: 'inspection', label: 'Inspection' },
  { value: 'corrective', label: 'Corrective Action' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EditWorkOrderModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  currentData,
}: EditWorkOrderModalProps) {
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [priority, setPriority] = React.useState('');
  const [dueDate, setDueDate] = React.useState('');
  const [type, setType] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const titleRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open && currentData) {
      setTitle(currentData.title || '');
      setDescription(currentData.description || '');
      setPriority(currentData.priority || 'medium');
      setDueDate(currentData.due_date ? currentData.due_date.split('T')[0] : '');
      setType(currentData.type || 'scheduled');
      setTimeout(() => titleRef.current?.focus(), 50);
    }
  }, [open, currentData]);

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

    // Build changes object with only modified fields
    const changes: WorkOrderEditData = {};
    if (title !== currentData?.title) changes.title = title;
    if (description !== currentData?.description) changes.description = description;
    if (priority !== currentData?.priority) changes.priority = priority;
    if (dueDate !== (currentData?.due_date?.split('T')[0] || '')) changes.due_date = dueDate || undefined;
    if (type !== currentData?.type) changes.type = type;

    if (Object.keys(changes).length === 0) {
      setToast({ type: 'error', message: 'No changes made' });
      return;
    }

    const result = await onSubmit(changes);
    if (result.success) {
      setToast({ type: 'success', message: 'Work order updated' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to update work order' });
    }
  };

  const inputClasses = cn(
    'w-full',
    'bg-surface-primary border border-surface-border rounded-md',
    'px-3 py-2',
    'text-body text-txt-primary placeholder:text-txt-tertiary',
    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
    'transition-colors duration-fast'
  );

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
        aria-labelledby="edit-wo-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-lg mx-4',
          'max-h-[90vh] overflow-y-auto'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="edit-wo-title"
            className="text-heading text-txt-primary"
          >
            Edit Work Order
          </h2>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Title */}
            <div>
              <label
                htmlFor="wo-title"
                className="block text-label text-txt-primary mb-2"
              >
                Title
              </label>
              <input
                ref={titleRef}
                id="wo-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Work order title"
                className={inputClasses}
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="wo-description"
                className="block text-label text-txt-primary mb-2"
              >
                Description
              </label>
              <textarea
                id="wo-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                placeholder="Describe the work to be done..."
                className={cn(inputClasses, 'resize-y')}
              />
            </div>

            {/* Priority and Type row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="wo-priority"
                  className="block text-label text-txt-primary mb-2"
                >
                  Priority
                </label>
                <select
                  id="wo-priority"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className={inputClasses}
                >
                  {PRIORITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="wo-type"
                  className="block text-label text-txt-primary mb-2"
                >
                  Type
                </label>
                <select
                  id="wo-type"
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className={inputClasses}
                >
                  {TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Due Date */}
            <div>
              <label
                htmlFor="wo-due-date"
                className="block text-label text-txt-primary mb-2"
              >
                Due Date
              </label>
              <input
                id="wo-due-date"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className={inputClasses}
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
              disabled={isLoading || !title.trim()}
              aria-busy={isLoading}
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
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

