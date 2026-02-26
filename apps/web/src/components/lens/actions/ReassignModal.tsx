'use client';

/**
 * ReassignModal — Work Order Lens action modal
 *
 * Reassigns the work order to a different crew member via reassign_work_order.
 * REQUIRES SIGNATURE per spec: Action 5 in work_order_lens_v2_PHASE_4_ACTIONS.md
 * Allowed roles: captain, chief_officer, chief_engineer, eto, chief_steward, purser
 *
 * Signature payload includes: signer_id, signed_at, device_id, action_hash
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

export interface CrewMember {
  id: string;
  display_name: string;
  role?: string;
}

export interface SignaturePayload {
  signer_id: string;
  signed_at: string;
  device_id: string;
  action_hash: string;
  [key: string]: unknown;
}

export interface ReassignModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with new assignee ID, reason, and signature on confirm */
  onSubmit: (
    assigneeId: string,
    reason: string,
    signature: SignaturePayload
  ) => Promise<{ success: boolean; error?: string }>;
  isLoading?: boolean;
  /** Available crew members to reassign to */
  crew?: CrewMember[];
  /** Current assignee ID (to pre-exclude) */
  currentAssigneeId?: string;
  /** Work order ID for action hash */
  workOrderId?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Generate a unique device ID for this browser session
 * Uses localStorage to persist across sessions
 */
function getDeviceId(): string {
  if (typeof window === 'undefined') return 'server';
  let deviceId = localStorage.getItem('celeste_device_id');
  if (!deviceId) {
    deviceId = `web-${crypto.randomUUID()}`;
    localStorage.setItem('celeste_device_id', deviceId);
  }
  return deviceId;
}

/**
 * Generate SHA-256 hash of action payload for signature integrity
 */
async function generateActionHash(payload: Record<string, unknown>): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(JSON.stringify(payload));
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
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
  workOrderId,
}: ReassignModalProps) {
  const { user } = useAuth();
  const [selectedId, setSelectedId] = React.useState('');
  const [reason, setReason] = React.useState('');
  const [pin, setPin] = React.useState('');
  const [totp, setTotp] = React.useState('');
  const [signatureError, setSignatureError] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const selectRef = React.useRef<HTMLSelectElement>(null);

  React.useEffect(() => {
    if (open) {
      setSelectedId('');
      setReason('');
      setPin('');
      setTotp('');
      setSignatureError(null);
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

  // Signature validation: both PIN and TOTP required
  const isSignatureValid = pin.length >= 4 && totp.length === 6;
  const canSubmit = selectedId && reason.trim().length > 0 && isSignatureValid && !isLoading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !reason.trim()) return;

    // Validate signature fields
    if (!isSignatureValid) {
      setSignatureError('PIN (4+ digits) and TOTP (6 digits) are required to sign this action');
      return;
    }

    // Build signature payload per spec
    const actionPayload = {
      work_order_id: workOrderId,
      assignee_id: selectedId,
      reason: reason.trim(),
      pin_hash: pin, // In production, this would be hashed
      totp_code: totp,
    };

    const actionHash = await generateActionHash(actionPayload);

    const signature: SignaturePayload = {
      signer_id: user?.id ?? '',
      signed_at: new Date().toISOString(),
      device_id: getDeviceId(),
      action_hash: actionHash,
    };

    const result = await onSubmit(selectedId, reason.trim(), signature);
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
        className="fixed inset-0 z-sidebar bg-black/60"
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
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-md mx-4'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="reassign-title"
            className="text-heading text-txt-primary"
          >
            Reassign Work Order
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            Select a crew member to take ownership.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Assignee selection */}
            <div>
              <label
                htmlFor="reassign-select"
                className="block text-label text-txt-primary mb-2"
              >
                Assign to <span className="text-status-critical">*</span>
              </label>

              {availableCrew.length === 0 ? (
                <p className="text-body text-txt-secondary">
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
                    'text-body text-txt-primary',
                    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                    'transition-colors duration-fast'
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

            {/* Reason for reassignment */}
            <div>
              <label
                htmlFor="reassign-reason"
                className="block text-label text-txt-primary mb-2"
              >
                Reason for reassignment <span className="text-status-critical">*</span>
              </label>
              <textarea
                id="reassign-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                placeholder="e.g., Workload balancing, specialist skills required..."
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
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                  />
                </svg>
                <span className="text-label text-txt-primary font-medium">
                  Signature Required
                </span>
              </div>
              <p className="text-label text-txt-secondary mb-3">
                This action requires your signature for audit compliance.
              </p>

              <div className="grid grid-cols-2 gap-3">
                {/* PIN field */}
                <div>
                  <label
                    htmlFor="reassign-pin"
                    className="block text-label text-txt-primary mb-1"
                  >
                    PIN <span className="text-status-critical">*</span>
                  </label>
                  <input
                    type="password"
                    id="reassign-pin"
                    value={pin}
                    onChange={(e) => {
                      setPin(e.target.value.replace(/\D/g, ''));
                      setSignatureError(null);
                    }}
                    maxLength={8}
                    placeholder="4+ digits"
                    autoComplete="off"
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary placeholder:text-txt-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast',
                      signatureError && 'border-status-critical'
                    )}
                  />
                </div>

                {/* TOTP field */}
                <div>
                  <label
                    htmlFor="reassign-totp"
                    className="block text-label text-txt-primary mb-1"
                  >
                    TOTP Code <span className="text-status-critical">*</span>
                  </label>
                  <input
                    type="text"
                    id="reassign-totp"
                    value={totp}
                    onChange={(e) => {
                      setTotp(e.target.value.replace(/\D/g, '').slice(0, 6));
                      setSignatureError(null);
                    }}
                    maxLength={6}
                    placeholder="6 digits"
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary placeholder:text-txt-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast',
                      signatureError && 'border-status-critical'
                    )}
                  />
                </div>
              </div>

              {/* Signature error */}
              {signatureError && (
                <p className="mt-2 text-label text-status-critical">
                  {signatureError}
                </p>
              )}
            </div>
          </div>

          {/* Footer buttons */}
          <div className="px-6 pb-6 flex justify-end gap-3">
            <GhostButton type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={!canSubmit || availableCrew.length === 0}
              aria-busy={isLoading}
            >
              {isLoading ? 'Reassigning...' : 'Sign & Reassign'}
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

