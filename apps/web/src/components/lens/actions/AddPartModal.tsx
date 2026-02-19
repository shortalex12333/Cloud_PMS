'use client';

/**
 * AddPartModal — Work Order Lens action modal
 *
 * Adds a part to the work order via add_wo_part action.
 * Part selector: text input for part ID/name + quantity field.
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

export interface PartOption {
  id: string;
  name: string;
  part_number?: string;
  unit?: string;
  stock?: number;
}

export interface AddPartModalProps {
  /** Whether the modal is visible */
  open: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Called with part details when user submits */
  onSubmit: (partId: string, quantity: number, unit?: string) => Promise<{ success: boolean; error?: string }>;
  /** Whether the parent action is currently loading */
  isLoading?: boolean;
  /** Available parts for selection (from inventory) */
  parts?: PartOption[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * AddPartModal
 *
 * Modal for attaching a part from inventory to a work order.
 * Part selector shows name + part number. Quantity must be positive integer.
 */
export function AddPartModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  parts = [],
}: AddPartModalProps) {
  const [selectedPartId, setSelectedPartId] = React.useState('');
  const [quantity, setQuantity] = React.useState(1);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const searchRef = React.useRef<HTMLInputElement>(null);

  // Reset state when modal opens
  React.useEffect(() => {
    if (open) {
      setSelectedPartId('');
      setQuantity(1);
      setSearchQuery('');
      setTimeout(() => searchRef.current?.focus(), 50);
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

  // Filter parts by search query
  const filteredParts = parts.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      !q ||
      p.name.toLowerCase().includes(q) ||
      p.part_number?.toLowerCase().includes(q)
    );
  });

  const selectedPart = parts.find((p) => p.id === selectedPartId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPartId) return;
    if (quantity < 1) return;

    const result = await onSubmit(selectedPartId, quantity, selectedPart?.unit);
    if (result.success) {
      setToast({ type: 'success', message: 'Part added to work order' });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to add part' });
    }
  };

  const handleCancel = () => {
    setSelectedPartId('');
    setQuantity(1);
    setSearchQuery('');
    onClose();
  };

  const canSubmit = selectedPartId.length > 0 && quantity >= 1 && !isLoading;

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
        aria-labelledby="add-part-title"
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
            id="add-part-title"
            className="text-heading text-txt-primary"
          >
            Add Part
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            Select a part from inventory and specify the quantity used.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Part search / selector */}
            <div>
              <label
                htmlFor="part-search"
                className="block text-label text-txt-primary mb-2"
              >
                Part
              </label>
              <input
                ref={searchRef}
                id="part-search"
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  // Clear selection if query changes
                  if (selectedPartId) setSelectedPartId('');
                }}
                placeholder="Search by name or part number..."
                className={cn(
                  'w-full',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-body text-txt-primary placeholder:text-txt-tertiary',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-fast'
                )}
              />

              {/* Part list */}
              {searchQuery && filteredParts.length > 0 && !selectedPartId && (
                <div
                  className={cn(
                    'mt-1 max-h-[160px] overflow-y-auto',
                    'bg-surface-elevated border border-surface-border rounded-md',
                    'shadow-md'
                  )}
                >
                  {filteredParts.slice(0, 8).map((part) => (
                    <button
                      key={part.id}
                      type="button"
                      onClick={() => {
                        setSelectedPartId(part.id);
                        setSearchQuery(part.name);
                      }}
                      className={cn(
                        'w-full text-left px-3 py-2',
                        'hover:bg-surface-hover transition-colors duration-fast',
                        'border-b border-surface-border-subtle last:border-b-0'
                      )}
                    >
                      <span className="block text-body text-txt-primary">
                        {part.name}
                      </span>
                      {part.part_number && (
                        <span className="block text-caption text-txt-tertiary">
                          {part.part_number}
                          {part.stock !== undefined && ` — ${part.stock} in stock`}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* No results */}
              {searchQuery && filteredParts.length === 0 && !selectedPartId && (
                <p className="mt-2 text-label text-txt-tertiary">
                  No parts found. Check the Parts inventory.
                </p>
              )}

              {/* Selected indicator */}
              {selectedPartId && selectedPart && (
                <p className="mt-2 text-label text-status-success">
                  Selected: {selectedPart.name}
                  {selectedPart.part_number && ` (${selectedPart.part_number})`}
                </p>
              )}
            </div>

            {/* Quantity */}
            <div>
              <label
                htmlFor="part-quantity"
                className="block text-label text-txt-primary mb-2"
              >
                Quantity {selectedPart?.unit && `(${selectedPart.unit})`}
              </label>
              <input
                id="part-quantity"
                type="number"
                min={1}
                step={1}
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className={cn(
                  'w-24',
                  'bg-surface-primary border border-surface-border rounded-md',
                  'px-3 py-2',
                  'text-body text-txt-primary',
                  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                  'transition-colors duration-fast'
                )}
              />
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
              {isLoading ? 'Adding...' : 'Add Part'}
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

export default AddPartModal;
