'use client';

/**
 * Inventory Action Modals
 *
 * Modal components for inventory actions that require user input.
 * Replaces hardcoded values with proper form inputs and validation.
 *
 * Actions covered:
 * - ConsumePartModal: Record stock consumption
 * - ReceivePartModal: Add incoming stock
 * - TransferPartModal: Move stock between locations
 * - AdjustStockModal: Manual stock level correction
 * - WriteOffPartModal: Write off damaged/expired stock
 * - AddToShoppingListModal: Add part to procurement list
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BaseModalProps {
  open: boolean;
  onClose: () => void;
  isLoading?: boolean;
  partName?: string;
  currentQuantity?: number;
  currentLocation?: string;
  unitOfMeasure?: string;
}

export interface ConsumePartModalProps extends BaseModalProps {
  onSubmit: (quantity: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
}

export interface ReceivePartModalProps extends BaseModalProps {
  onSubmit: (quantity: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
}

export interface TransferPartModalProps extends BaseModalProps {
  onSubmit: (quantity: number, targetLocation: string, notes?: string) => Promise<{ success: boolean; error?: string }>;
  availableLocations?: string[];
}

export interface AdjustStockModalProps extends BaseModalProps {
  onSubmit: (newQuantity: number, reason: string) => Promise<{ success: boolean; error?: string }>;
}

export interface WriteOffPartModalProps extends BaseModalProps {
  onSubmit: (quantity: number, reason: string) => Promise<{ success: boolean; error?: string }>;
}

export interface AddToShoppingListModalProps extends BaseModalProps {
  onSubmit: (quantity: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
}

// ---------------------------------------------------------------------------
// Common styles
// ---------------------------------------------------------------------------

const inputClasses = cn(
  'w-full',
  'bg-surface-primary border border-surface-border rounded-md',
  'px-3 py-2',
  'text-body text-txt-primary placeholder:text-txt-tertiary',
  'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
  'transition-colors duration-fast'
);

const textareaClasses = cn(
  inputClasses,
  'resize-y min-h-[60px]'
);

const selectClasses = cn(
  inputClasses,
  'appearance-none cursor-pointer'
);

const labelClasses = 'block text-label text-txt-primary mb-2';

const modalPanelClasses = cn(
  'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
  'z-modal',
  'bg-surface-elevated border border-surface-border',
  'rounded-lg shadow-modal',
  'w-full max-w-md mx-4'
);

// ---------------------------------------------------------------------------
// Common write-off/adjustment reasons
// ---------------------------------------------------------------------------

const WRITE_OFF_REASONS = [
  'Damaged',
  'Expired',
  'Lost',
  'Defective',
  'Obsolete',
  'Quality issue',
  'Other',
] as const;

// ---------------------------------------------------------------------------
// ConsumePartModal
// ---------------------------------------------------------------------------

export function ConsumePartModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  currentQuantity = 0,
  unitOfMeasure,
}: ConsumePartModalProps) {
  const [quantity, setQuantity] = React.useState('1');
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setQuantity('1');
      setNotes('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
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
    setValidationError(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setValidationError('Please enter a valid positive quantity');
      return;
    }
    if (qty > currentQuantity) {
      setValidationError(`Cannot consume more than available stock (${currentQuantity})`);
      return;
    }

    const result = await onSubmit(qty, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: `${qty} ${unitOfMeasure || 'units'} consumed successfully` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to consume stock' });
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="consume-part-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="consume-part-title" className="text-heading text-txt-primary">
            Use Part
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
          <p className="mt-1 text-meta text-txt-tertiary">
            Available: {currentQuantity} {unitOfMeasure || 'units'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="consume-quantity" className={labelClasses}>
                Quantity to use <span className="text-status-critical">*</span>
              </label>
              <input
                ref={quantityRef}
                id="consume-quantity"
                type="number"
                min="1"
                max={currentQuantity}
                step="1"
                value={quantity}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  setValidationError(null);
                }}
                placeholder="Enter quantity"
                className={inputClasses}
                required
              />
            </div>

            <div>
              <label htmlFor="consume-notes" className={labelClasses}>
                Usage notes (optional)
              </label>
              <textarea
                id="consume-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="What was this used for?"
                className={textareaClasses}
              />
            </div>

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton type="submit" disabled={isLoading || !quantity} loading={isLoading}>
              Use Part
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// ReceivePartModal
// ---------------------------------------------------------------------------

export function ReceivePartModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  currentQuantity = 0,
  unitOfMeasure,
}: ReceivePartModalProps) {
  const [quantity, setQuantity] = React.useState('1');
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setQuantity('1');
      setNotes('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
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
    setValidationError(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setValidationError('Please enter a valid positive quantity');
      return;
    }

    const result = await onSubmit(qty, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: `${qty} ${unitOfMeasure || 'units'} received successfully` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to receive stock' });
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="receive-part-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="receive-part-title" className="text-heading text-txt-primary">
            Receive Stock
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
          <p className="mt-1 text-meta text-txt-tertiary">
            Current stock: {currentQuantity} {unitOfMeasure || 'units'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="receive-quantity" className={labelClasses}>
                Quantity received <span className="text-status-critical">*</span>
              </label>
              <input
                ref={quantityRef}
                id="receive-quantity"
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  setValidationError(null);
                }}
                placeholder="Enter quantity"
                className={inputClasses}
                required
              />
            </div>

            <div>
              <label htmlFor="receive-notes" className={labelClasses}>
                Receiving notes (optional)
              </label>
              <textarea
                id="receive-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="PO number, supplier info, condition notes..."
                className={textareaClasses}
              />
            </div>

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton type="submit" disabled={isLoading || !quantity} loading={isLoading}>
              Receive Stock
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// TransferPartModal
// ---------------------------------------------------------------------------

export function TransferPartModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  currentQuantity = 0,
  currentLocation,
  unitOfMeasure,
  availableLocations = [],
}: TransferPartModalProps) {
  const [quantity, setQuantity] = React.useState('1');
  const [targetLocation, setTargetLocation] = React.useState('');
  const [customLocation, setCustomLocation] = React.useState('');
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  const showCustomLocationInput = targetLocation === '__custom__' || availableLocations.length === 0;

  React.useEffect(() => {
    if (open) {
      setQuantity('1');
      setTargetLocation('');
      setCustomLocation('');
      setNotes('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
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
    setValidationError(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setValidationError('Please enter a valid positive quantity');
      return;
    }
    if (qty > currentQuantity) {
      setValidationError(`Cannot transfer more than available stock (${currentQuantity})`);
      return;
    }

    const finalLocation = showCustomLocationInput ? customLocation.trim() : targetLocation;
    if (!finalLocation) {
      setValidationError('Please specify a target location');
      return;
    }

    if (finalLocation === currentLocation) {
      setValidationError('Target location must be different from current location');
      return;
    }

    const result = await onSubmit(qty, finalLocation, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: `${qty} ${unitOfMeasure || 'units'} transferred to ${finalLocation}` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to transfer stock' });
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="transfer-part-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="transfer-part-title" className="text-heading text-txt-primary">
            Transfer Stock
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
          <p className="mt-1 text-meta text-txt-tertiary">
            Available: {currentQuantity} {unitOfMeasure || 'units'}
            {currentLocation && ` at ${currentLocation}`}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="transfer-quantity" className={labelClasses}>
                Quantity to transfer <span className="text-status-critical">*</span>
              </label>
              <input
                ref={quantityRef}
                id="transfer-quantity"
                type="number"
                min="1"
                max={currentQuantity}
                step="1"
                value={quantity}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  setValidationError(null);
                }}
                placeholder="Enter quantity"
                className={inputClasses}
                required
              />
            </div>

            {availableLocations.length > 0 ? (
              <div>
                <label htmlFor="transfer-location" className={labelClasses}>
                  Target location <span className="text-status-critical">*</span>
                </label>
                <select
                  id="transfer-location"
                  value={targetLocation}
                  onChange={(e) => {
                    setTargetLocation(e.target.value);
                    setValidationError(null);
                  }}
                  className={selectClasses}
                  required
                >
                  <option value="">Select location...</option>
                  {availableLocations
                    .filter(loc => loc !== currentLocation)
                    .map((loc) => (
                      <option key={loc} value={loc}>
                        {loc}
                      </option>
                    ))}
                  <option value="__custom__">Other (enter manually)</option>
                </select>
              </div>
            ) : null}

            {showCustomLocationInput && (
              <div>
                <label htmlFor="transfer-custom-location" className={labelClasses}>
                  {availableLocations.length > 0 ? 'Enter location' : 'Target location'} <span className="text-status-critical">*</span>
                </label>
                <input
                  id="transfer-custom-location"
                  type="text"
                  value={customLocation}
                  onChange={(e) => {
                    setCustomLocation(e.target.value);
                    setValidationError(null);
                  }}
                  placeholder="Enter target location"
                  className={inputClasses}
                  required
                />
              </div>
            )}

            <div>
              <label htmlFor="transfer-notes" className={labelClasses}>
                Transfer notes (optional)
              </label>
              <textarea
                id="transfer-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Reason for transfer..."
                className={textareaClasses}
              />
            </div>

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={isLoading || !quantity || (!targetLocation && !customLocation)}
              loading={isLoading}
            >
              Transfer Stock
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// AdjustStockModal
// ---------------------------------------------------------------------------

export function AdjustStockModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  currentQuantity = 0,
  unitOfMeasure,
}: AdjustStockModalProps) {
  const [newQuantity, setNewQuantity] = React.useState('');
  const [reason, setReason] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setNewQuantity(currentQuantity.toString());
      setReason('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
    }
  }, [open, currentQuantity]);

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
    setValidationError(null);

    const qty = parseInt(newQuantity, 10);
    if (isNaN(qty) || qty < 0) {
      setValidationError('Please enter a valid quantity (0 or greater)');
      return;
    }

    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setValidationError('Please provide a reason for the adjustment');
      return;
    }

    if (trimmedReason.length < 5) {
      setValidationError('Reason must be at least 5 characters');
      return;
    }

    const result = await onSubmit(qty, trimmedReason);
    if (result.success) {
      const diff = qty - currentQuantity;
      const diffStr = diff >= 0 ? `+${diff}` : `${diff}`;
      setToast({ type: 'success', message: `Stock adjusted (${diffStr} ${unitOfMeasure || 'units'})` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to adjust stock' });
    }
  };

  const quantityDiff = parseInt(newQuantity, 10) - currentQuantity;
  const showDiff = !isNaN(quantityDiff) && quantityDiff !== 0;

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="adjust-stock-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="adjust-stock-title" className="text-heading text-txt-primary">
            Adjust Stock
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
          <p className="mt-1 text-meta text-txt-tertiary">
            Current stock: {currentQuantity} {unitOfMeasure || 'units'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="adjust-quantity" className={labelClasses}>
                New quantity <span className="text-status-critical">*</span>
              </label>
              <div className="relative">
                <input
                  ref={quantityRef}
                  id="adjust-quantity"
                  type="number"
                  min="0"
                  step="1"
                  value={newQuantity}
                  onChange={(e) => {
                    setNewQuantity(e.target.value);
                    setValidationError(null);
                  }}
                  placeholder="Enter new quantity"
                  className={inputClasses}
                  required
                />
                {showDiff && (
                  <span
                    className={cn(
                      'absolute right-3 top-1/2 -translate-y-1/2 text-meta font-medium',
                      quantityDiff > 0 ? 'text-status-success' : 'text-status-critical'
                    )}
                  >
                    {quantityDiff > 0 ? '+' : ''}{quantityDiff}
                  </span>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="adjust-reason" className={labelClasses}>
                Reason for adjustment <span className="text-status-critical">*</span>
              </label>
              <textarea
                id="adjust-reason"
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  setValidationError(null);
                }}
                rows={2}
                placeholder="Explain why this adjustment is needed (e.g., inventory count correction, system sync error)..."
                className={textareaClasses}
                required
              />
            </div>

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={isLoading || !newQuantity || !reason.trim()}
              loading={isLoading}
            >
              Adjust Stock
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// WriteOffPartModal
// ---------------------------------------------------------------------------

export function WriteOffPartModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  currentQuantity = 0,
  unitOfMeasure,
}: WriteOffPartModalProps) {
  const [quantity, setQuantity] = React.useState('1');
  const [reasonType, setReasonType] = React.useState<string>('');
  const [customReason, setCustomReason] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  const showCustomReason = reasonType === 'Other';

  React.useEffect(() => {
    if (open) {
      setQuantity('1');
      setReasonType('');
      setCustomReason('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
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
    setValidationError(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setValidationError('Please enter a valid positive quantity');
      return;
    }
    if (qty > currentQuantity) {
      setValidationError(`Cannot write off more than available stock (${currentQuantity})`);
      return;
    }

    if (!reasonType) {
      setValidationError('Please select a reason for write-off');
      return;
    }

    let finalReason = reasonType;
    if (showCustomReason) {
      const trimmedCustom = customReason.trim();
      if (!trimmedCustom) {
        setValidationError('Please provide details for the write-off reason');
        return;
      }
      finalReason = trimmedCustom;
    }

    const result = await onSubmit(qty, finalReason);
    if (result.success) {
      setToast({ type: 'success', message: `${qty} ${unitOfMeasure || 'units'} written off` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to write off stock' });
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="writeoff-part-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="writeoff-part-title" className="text-heading text-txt-primary">
            Write Off Stock
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
          <p className="mt-1 text-meta text-txt-tertiary">
            Available: {currentQuantity} {unitOfMeasure || 'units'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="writeoff-quantity" className={labelClasses}>
                Quantity to write off <span className="text-status-critical">*</span>
              </label>
              <input
                ref={quantityRef}
                id="writeoff-quantity"
                type="number"
                min="1"
                max={currentQuantity}
                step="1"
                value={quantity}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  setValidationError(null);
                }}
                placeholder="Enter quantity"
                className={inputClasses}
                required
              />
            </div>

            <div>
              <label htmlFor="writeoff-reason" className={labelClasses}>
                Reason for write-off <span className="text-status-critical">*</span>
              </label>
              <select
                id="writeoff-reason"
                value={reasonType}
                onChange={(e) => {
                  setReasonType(e.target.value);
                  setValidationError(null);
                }}
                className={selectClasses}
                required
              >
                <option value="">Select reason...</option>
                {WRITE_OFF_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {reason}
                  </option>
                ))}
              </select>
            </div>

            {showCustomReason && (
              <div>
                <label htmlFor="writeoff-custom-reason" className={labelClasses}>
                  Please specify <span className="text-status-critical">*</span>
                </label>
                <textarea
                  id="writeoff-custom-reason"
                  value={customReason}
                  onChange={(e) => {
                    setCustomReason(e.target.value);
                    setValidationError(null);
                  }}
                  rows={2}
                  placeholder="Describe the reason for write-off..."
                  className={textareaClasses}
                  required
                />
              </div>
            )}

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={isLoading || !quantity || !reasonType || (showCustomReason && !customReason.trim())}
              loading={isLoading}
            >
              Write Off
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// AddToShoppingListModal
// ---------------------------------------------------------------------------

export function AddToShoppingListModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  partName,
  unitOfMeasure,
}: AddToShoppingListModalProps) {
  const [quantity, setQuantity] = React.useState('1');
  const [notes, setNotes] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const quantityRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setQuantity('1');
      setNotes('');
      setValidationError(null);
      setTimeout(() => quantityRef.current?.focus(), 50);
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
    setValidationError(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setValidationError('Please enter a valid positive quantity');
      return;
    }

    const result = await onSubmit(qty, notes.trim() || undefined);
    if (result.success) {
      setToast({ type: 'success', message: `${qty} ${unitOfMeasure || 'units'} added to shopping list` });
      setTimeout(onClose, 800);
    } else {
      setToast({ type: 'error', message: result.error ?? 'Failed to add to shopping list' });
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="shopping-list-title"
        className={modalPanelClasses}
      >
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="shopping-list-title" className="text-heading text-txt-primary">
            Add to Shopping List
          </h2>
          {partName && (
            <p className="mt-1 text-label text-txt-secondary truncate">{partName}</p>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            <div>
              <label htmlFor="shopping-quantity" className={labelClasses}>
                Quantity to order <span className="text-status-critical">*</span>
              </label>
              <input
                ref={quantityRef}
                id="shopping-quantity"
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(e) => {
                  setQuantity(e.target.value);
                  setValidationError(null);
                }}
                placeholder="Enter quantity"
                className={inputClasses}
                required
              />
            </div>

            <div>
              <label htmlFor="shopping-notes" className={labelClasses}>
                Order notes (optional)
              </label>
              <textarea
                id="shopping-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Urgency, preferred supplier, specifications..."
                className={textareaClasses}
              />
            </div>

            {validationError && (
              <p className="text-meta text-status-critical">{validationError}</p>
            )}
          </div>

          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton type="submit" disabled={isLoading || !quantity} loading={isLoading}>
              Add to List
            </PrimaryButton>
          </div>
        </form>
      </div>

      {toast && (
        <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />
      )}
    </>
  );
}
