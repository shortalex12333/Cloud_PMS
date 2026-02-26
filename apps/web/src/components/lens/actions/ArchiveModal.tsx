'use client';

/**
 * ArchiveModal — Work Order Lens action modal
 *
 * Archives (soft-deletes) a work order via archive_work_order action.
 * Requires a deletion reason AND signature (PIN + TOTP).
 * Captain and manager only.
 * Uses design system tokens exclusively.
 *
 * Spec reference: work_order_lens_v2_PHASE_4_ACTIONS.md - Action 6
 * Signature payload must include: signer_id, signed_at, device_id, action_hash
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Signature payload structure per spec */
export interface SignaturePayload {
  signer_id: string;
  signed_at: string;
  device_id: string;
  action_hash: string;
  [key: string]: unknown;
}

export interface ArchiveModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with reason and signature on confirm */
  onSubmit: (reason: string, signature: SignaturePayload) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Work order display title for confirmation copy */
  workOrderTitle?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Generate a device identifier for the current browser session.
 * Uses a combination of user agent and timestamp to create a pseudo-unique ID.
 * Persists in sessionStorage for consistency during the session.
 */
function getDeviceId(): string {
  if (typeof window === 'undefined') return 'server';

  const stored = sessionStorage.getItem('celeste_device_id');
  if (stored) return stored;

  // Generate a new device ID based on browser fingerprint + random
  const ua = navigator.userAgent || 'unknown';
  const random = Math.random().toString(36).substring(2, 15);
  const deviceId = `web-${btoa(ua).substring(0, 12)}-${random}`;

  sessionStorage.setItem('celeste_device_id', deviceId);
  return deviceId;
}

/**
 * Generate SHA-256 hash of the action payload for audit trail.
 */
async function generateActionHash(payload: Record<string, unknown>): Promise<string> {
  const data = JSON.stringify(payload);
  const encoder = new TextEncoder();
  const buffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
  const hashArray = Array.from(new Uint8Array(buffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
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
  const { user } = useAuth();
  const [reason, setReason] = React.useState('');
  const [pin, setPin] = React.useState('');
  const [totp, setTotp] = React.useState('');
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [signatureError, setSignatureError] = React.useState<string | null>(null);
  const reasonRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    if (open) {
      setReason('');
      setPin('');
      setTotp('');
      setSignatureError(null);
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
    setSignatureError(null);

    const trimmedReason = reason.trim();
    const trimmedPin = pin.trim();
    const trimmedTotp = totp.trim();

    // Validate all required fields
    if (!trimmedReason) {
      setSignatureError('Deletion reason is required');
      return;
    }
    if (!trimmedPin) {
      setSignatureError('PIN is required for signature');
      return;
    }
    if (trimmedPin.length < 4) {
      setSignatureError('PIN must be at least 4 digits');
      return;
    }
    if (!trimmedTotp) {
      setSignatureError('TOTP code is required for signature');
      return;
    }
    if (trimmedTotp.length !== 6) {
      setSignatureError('TOTP code must be 6 digits');
      return;
    }

    // Build the signature payload
    try {
      const actionPayload = {
        action: 'archive_work_order',
        work_order_title: workOrderTitle,
        deletion_reason: trimmedReason,
        pin_hash: trimmedPin, // In production, this would be hashed
        totp: trimmedTotp,
      };

      const signature: SignaturePayload = {
        signer_id: user?.id ?? 'unknown',
        signed_at: new Date().toISOString(),
        device_id: getDeviceId(),
        action_hash: await generateActionHash(actionPayload),
      };

      const result = await onSubmit(trimmedReason, signature);
      if (result.success) {
        setToast({ type: 'success', message: 'Work order archived' });
        setTimeout(onClose, 800);
      } else {
        setToast({ type: 'error', message: result.error ?? 'Archive failed' });
      }
    } catch {
      setSignatureError('Failed to generate signature');
    }
  };

  // Cannot submit without reason AND signature (PIN + TOTP)
  const canSubmit =
    reason.trim().length > 0 &&
    pin.trim().length >= 4 &&
    totp.trim().length === 6 &&
    !isLoading;

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
          'rounded-lg shadow-modal',
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

            {/* Signature section */}
            <div className="border-t border-surface-border pt-4">
              <div className="flex items-center gap-2 mb-3">
                <svg
                  className="w-4 h-4 text-status-warning"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
                  />
                </svg>
                <span className="text-label text-txt-primary font-medium">
                  Digital Signature Required
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* PIN input */}
                <div>
                  <label
                    htmlFor="archive-pin"
                    className="block text-label text-txt-secondary mb-1.5"
                  >
                    PIN <span className="text-status-critical">*</span>
                  </label>
                  <input
                    type="password"
                    id="archive-pin"
                    value={pin}
                    onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="****"
                    autoComplete="off"
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary placeholder:text-txt-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast',
                      'tracking-widest text-center'
                    )}
                  />
                </div>

                {/* TOTP input */}
                <div>
                  <label
                    htmlFor="archive-totp"
                    className="block text-label text-txt-secondary mb-1.5"
                  >
                    TOTP Code <span className="text-status-critical">*</span>
                  </label>
                  <input
                    type="text"
                    id="archive-totp"
                    value={totp}
                    onChange={(e) => setTotp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary placeholder:text-txt-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast',
                      'tracking-widest text-center font-mono'
                    )}
                  />
                </div>
              </div>

              <p className="mt-2 text-[11px] text-txt-tertiary">
                Enter your PIN and 6-digit authenticator code to sign this action.
              </p>
            </div>

            {/* Signature error */}
            {signatureError && (
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-2',
                  'bg-status-critical/10 border border-status-critical/30 rounded-md',
                  'text-label text-status-critical'
                )}
                role="alert"
              >
                <svg
                  className="w-4 h-4 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                  />
                </svg>
                {signatureError}
              </div>
            )}
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
              {isLoading ? 'Signing & Archiving...' : 'Sign & Archive'}
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

