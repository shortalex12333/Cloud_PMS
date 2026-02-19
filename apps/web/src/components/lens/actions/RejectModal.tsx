'use client';

/**
 * RejectModal — Receiving Lens rejection flow (FE-03-01)
 *
 * Full rejection workflow per CLAUDE.md:
 * 1. Reason dropdown (standard reasons + "Other")
 * 2. If "Other" selected, show free-text input
 * 3. Rejection requires signature (SignaturePrompt)
 * 4. Optional email notification note (displayed only)
 * 5. After reject, status changes to "rejected"
 *
 * Uses design system tokens exclusively.
 * SignaturePrompt renders as full overlay replacing modal per spec.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';
import SignaturePrompt from '@/components/celeste/SignaturePrompt';
import type { DiffItem } from '@/components/celeste/MutationPreview';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Standard rejection reasons per CLAUDE.md spec
// ---------------------------------------------------------------------------

const REJECTION_REASONS = [
  { value: 'damaged_goods', label: 'Goods received damaged' },
  { value: 'wrong_items', label: 'Wrong items delivered' },
  { value: 'quantity_mismatch', label: 'Quantity does not match PO' },
  { value: 'quality_not_met', label: 'Quality standards not met' },
  { value: 'late_delivery', label: 'Delivery unacceptably late' },
  { value: 'missing_documentation', label: 'Missing required documentation' },
  { value: 'other', label: 'Other (specify below)' },
] as const;

type RejectionReasonValue = typeof REJECTION_REASONS[number]['value'];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RejectModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with (reason, customReason?, signature?) */
  onSubmit: (
    reason: string,
    customReason?: string,
    signature?: Record<string, unknown>
  ) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Display title of the entity being rejected */
  entityTitle?: string;
  /** Entity type label (e.g. "receiving") */
  entityType?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RejectModal({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  entityTitle,
  entityType = 'receiving',
}: RejectModalProps) {
  const { user } = useAuth();

  // Form state
  const [selectedReason, setSelectedReason] = React.useState<RejectionReasonValue | ''>('');
  const [customReason, setCustomReason] = React.useState('');

  // Signature flow: when user clicks "Reject", show SignaturePrompt
  const [showSignature, setShowSignature] = React.useState(false);

  // Toast state
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Focus the reason dropdown on open
  const reasonRef = React.useRef<HTMLSelectElement>(null);

  React.useEffect(() => {
    if (open) {
      setSelectedReason('');
      setCustomReason('');
      setShowSignature(false);
      setTimeout(() => reasonRef.current?.focus(), 50);
    }
  }, [open]);

  // Escape key closes the modal (unless signature is shown — let it handle its own escape)
  React.useEffect(() => {
    if (!open || showSignature) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose, showSignature]);

  if (!open) return null;

  const isOtherSelected = selectedReason === 'other';
  const hasValidReason =
    selectedReason !== '' &&
    (!isOtherSelected || customReason.trim().length > 0);

  const reasonLabel =
    REJECTION_REASONS.find((r) => r.value === selectedReason)?.label ?? selectedReason;

  // The display reason shown in signature preview
  const displayReason = isOtherSelected
    ? customReason.trim()
    : reasonLabel;

  // Build mutation diffs for SignaturePrompt preview
  const diffs: DiffItem[] = [
    {
      field: 'Status',
      before: 'pending',
      after: 'rejected',
    },
    {
      field: 'Rejection reason',
      before: '—',
      after: displayReason,
    },
  ];

  // Step 1: User clicks "Reject" → validate → show signature
  const handleProceedToSign = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasValidReason) return;
    setShowSignature(true);
  };

  // Step 2: User signs → submit action
  const handleSign = async () => {
    const signature: Record<string, unknown> = {
      signed_by: user?.id ?? 'unknown',
      signed_by_name: user?.displayName ?? user?.email ?? 'Unknown user',
      signed_at: new Date().toISOString(),
      reason: selectedReason,
      custom_reason: isOtherSelected ? customReason.trim() : undefined,
    };

    const result = await onSubmit(
      selectedReason,
      isOtherSelected ? customReason.trim() : undefined,
      signature
    );

    if (result.success) {
      setToast({ type: 'success', message: `${entityType === 'receiving' ? 'Receiving record' : 'Record'} rejected` });
      setShowSignature(false);
      setTimeout(onClose, 800);
    } else {
      setShowSignature(false);
      setToast({ type: 'error', message: result.error ?? 'Failed to reject record' });
    }
  };

  // User cancels from signature prompt → go back to form
  const handleCancelSign = () => {
    setShowSignature(false);
  };

  return (
    <>
      {/* If signature step, show SignaturePrompt overlay instead of modal */}
      {showSignature ? (
        <SignaturePrompt
          diffs={diffs}
          userName={user?.displayName ?? user?.email ?? 'Unknown user'}
          onSign={handleSign}
          onCancel={handleCancelSign}
          isCommitting={isLoading}
        />
      ) : (
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
            aria-labelledby="reject-modal-title"
            className={cn(
              'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
              'z-modal',
              'bg-surface-elevated border border-surface-border',
              'rounded-[16px] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.4)]',
              'w-full max-w-md mx-4'
            )}
          >
            {/* Header */}
            <div className="px-6 pt-6 pb-4 border-b border-surface-border">
              <h2
                id="reject-modal-title"
                className="text-heading text-txt-primary"
              >
                Reject Receiving Record
              </h2>
              {entityTitle && (
                <p className="mt-1 text-label text-txt-secondary truncate">
                  {entityTitle}
                </p>
              )}
            </div>

            {/* Form */}
            <form onSubmit={handleProceedToSign}>
              <div className="px-6 py-4 space-y-4">
                {/* Reason dropdown */}
                <div>
                  <label
                    htmlFor="rejection-reason"
                    className="block text-label text-txt-primary mb-2"
                  >
                    Reason for rejection
                    <span className="text-status-critical ml-1" aria-hidden="true">*</span>
                  </label>
                  <select
                    id="rejection-reason"
                    ref={reasonRef}
                    value={selectedReason}
                    onChange={(e) => setSelectedReason(e.target.value as RejectionReasonValue | '')}
                    required
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-[10px]',
                      'px-3 py-2 pr-8',
                      'text-body text-txt-primary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast',
                      'appearance-none',
                      // Placeholder color when empty
                      selectedReason === '' && 'text-txt-tertiary'
                    )}
                  >
                    <option value="" disabled>
                      Select a reason...
                    </option>
                    {REJECTION_REASONS.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* "Other" free-text input — shown when "Other" selected */}
                {isOtherSelected && (
                  <div>
                    <label
                      htmlFor="custom-rejection-reason"
                      className="block text-label text-txt-primary mb-2"
                    >
                      Please describe the reason
                      <span className="text-status-critical ml-1" aria-hidden="true">*</span>
                    </label>
                    <textarea
                      id="custom-rejection-reason"
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      rows={3}
                      placeholder="Describe the specific issue requiring rejection..."
                      required
                      autoFocus
                      className={cn(
                        'w-full',
                        'bg-surface-primary border border-surface-border rounded-[10px]',
                        'px-3 py-2',
                        'text-body text-txt-primary placeholder:text-txt-tertiary',
                        'resize-y',
                        'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                        'transition-colors duration-fast'
                      )}
                    />
                  </div>
                )}

                {/* Signature notice */}
                <div className="flex items-start gap-2 px-3 py-2.5 rounded-md bg-surface-secondary border border-surface-border">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="w-4 h-4 text-txt-tertiary flex-shrink-0 mt-0.5"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 16v-4M12 8h.01" />
                  </svg>
                  <p className="text-caption text-txt-secondary">
                    Rejection requires your digital signature. You will be asked to sign on the next screen.
                    This action is recorded in the audit log and cannot be undone.
                  </p>
                </div>
              </div>

              {/* Footer buttons */}
              <div className="px-6 pb-6 flex justify-end gap-3">
                <GhostButton type="button" onClick={onClose} disabled={isLoading}>
                  Cancel
                </GhostButton>
                <PrimaryButton
                  type="submit"
                  disabled={isLoading || !hasValidReason}
                  aria-busy={isLoading}
                  className="bg-status-critical hover:bg-status-critical/90 focus-visible:ring-status-critical"
                >
                  {isLoading ? 'Rejecting...' : 'Reject'}
                </PrimaryButton>
              </div>
            </form>
          </div>
        </>
      )}

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

export default RejectModal;
