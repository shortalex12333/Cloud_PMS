'use client';

/**
 * FileWarrantyClaimModal — Full-form modal to file a new warranty claim.
 *
 * Follows the AttachmentUploadModal structural pattern:
 *   - Plain React state (no react-hook-form)
 *   - CSS variables only — no hardcoded hex/rgba
 *   - Same backdrop + panel + header + footer layout
 *
 * Wired from AppShell.handlePrimaryAction when activeDomain === 'warranties'.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { useAuth } from '@/hooks/useAuth';
import { useQueryClient } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FileWarrantyClaimModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

// ---------------------------------------------------------------------------
// Shared input / label style helpers (CSS vars, no hardcoded colours)
// ---------------------------------------------------------------------------

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: '5px',
  border: '1px solid var(--surface-border)',
  background: 'var(--surface-primary)',
  color: 'var(--txt-primary)',
  fontSize: '13px',
  boxSizing: 'border-box',
  fontFamily: 'inherit',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '11px',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  color: 'var(--txt-secondary)',
  marginBottom: '4px',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FileWarrantyClaimModal({ open, onOpenChange }: FileWarrantyClaimModalProps) {
  const { session } = useAuth();
  const queryClient = useQueryClient();

  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [vendor, setVendor] = React.useState('');
  const [manufacturer, setManufacturer] = React.useState('');
  const [contactEmail, setContactEmail] = React.useState('');
  const [equipmentRef, setEquipmentRef] = React.useState('');
  const [workOrderRef, setWorkOrderRef] = React.useState('');
  const [warrantyExpiry, setWarrantyExpiry] = React.useState('');
  const [claimedAmount, setClaimedAmount] = React.useState('');
  const [currency, setCurrency] = React.useState('USD');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Reset on open
  React.useEffect(() => {
    if (open) {
      setTitle('');
      setDescription('');
      setVendor('');
      setManufacturer('');
      setContactEmail('');
      setEquipmentRef('');
      setWorkOrderRef('');
      setWarrantyExpiry('');
      setClaimedAmount('');
      setCurrency('USD');
      setLoading(false);
      setError(null);
    }
  }, [open]);

  // Dismiss on Escape
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onOpenChange]);

  if (!open) return null;

  const handleCancel = () => {
    onOpenChange(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Claim title is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(),
      };
      if (description.trim()) payload.description = description.trim();
      if (vendor.trim()) payload.vendor_name = vendor.trim();
      if (manufacturer.trim()) payload.manufacturer = manufacturer.trim();
      // Manufacturer contact email stored in metadata.manufacturer_email (not in description)
      if (contactEmail.trim()) payload.manufacturer_email = contactEmail.trim();
      if (equipmentRef.trim()) payload.equipment_id = equipmentRef.trim();
      if (workOrderRef.trim()) payload.work_order_id = workOrderRef.trim();
      if (warrantyExpiry) payload.warranty_expiry = warrantyExpiry;
      if (claimedAmount) {
        payload.claimed_amount = parseFloat(claimedAmount);
        payload.currency = currency;
      }

      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ action: 'file_warranty_claim', context: {}, payload }),
      });
      const result = await res.json();
      if (!result || result.success === false) {
        setError(result?.message ?? result?.error ?? 'Failed to file claim');
        return;
      }
      queryClient.invalidateQueries({ queryKey: ['warranties'] });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-sidebar"
        style={{ background: 'var(--overlay-bg)' }}
        onClick={handleCancel}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="file-warranty-claim-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-lg mx-4'
        )}
        style={{ maxHeight: '90vh', overflowY: 'auto' }}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2
            id="file-warranty-claim-title"
            className="text-heading text-txt-primary"
          >
            File Warranty Claim
          </h2>
          <p className="mt-1 text-label text-txt-secondary">
            Record a new warranty or defect claim against equipment or a supplier.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

            {/* Row 1: Claim Title (full width) */}
            <div>
              <label htmlFor="fwc-title" style={labelStyle}>
                Claim Title <span style={{ color: 'var(--status-critical)' }}>*</span>
              </label>
              <input
                id="fwc-title"
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Main Engine Pump — Seal Failure"
                disabled={loading}
                style={inputStyle}
              />
            </div>

            {/* Row 2: Description (full width) */}
            <div>
              <label htmlFor="fwc-description" style={labelStyle}>
                Description
              </label>
              <textarea
                id="fwc-description"
                rows={3}
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Describe the defect, damage, or failure..."
                disabled={loading}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>

            {/* Row 3: Vendor + Manufacturer (2-col) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label htmlFor="fwc-vendor" style={labelStyle}>
                  Vendor / Supplier
                </label>
                <input
                  id="fwc-vendor"
                  type="text"
                  value={vendor}
                  onChange={e => setVendor(e.target.value)}
                  placeholder="e.g. Caterpillar Marine"
                  disabled={loading}
                  style={inputStyle}
                />
              </div>
              <div>
                <label htmlFor="fwc-manufacturer" style={labelStyle}>
                  Manufacturer
                </label>
                <input
                  id="fwc-manufacturer"
                  type="text"
                  value={manufacturer}
                  onChange={e => setManufacturer(e.target.value)}
                  placeholder="e.g. MTU, Rolls-Royce Marine"
                  disabled={loading}
                  style={inputStyle}
                />
              </div>
            </div>

            {/* Row 4: Manufacturer Contact Email (full width) */}
            <div>
              <label htmlFor="fwc-contact-email" style={labelStyle}>
                Manufacturer Contact Email
              </label>
              <input
                id="fwc-contact-email"
                type="email"
                value={contactEmail}
                onChange={e => setContactEmail(e.target.value)}
                placeholder="warranty@manufacturer.com"
                disabled={loading}
                style={inputStyle}
              />
            </div>

            {/* Row 5: Equipment Ref + Linked Work Order (2-col) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label htmlFor="fwc-equipment-ref" style={labelStyle}>
                  Equipment Ref
                </label>
                <input
                  id="fwc-equipment-ref"
                  type="text"
                  value={equipmentRef}
                  onChange={e => setEquipmentRef(e.target.value)}
                  placeholder="Equipment UUID or reference"
                  disabled={loading}
                  style={inputStyle}
                />
              </div>
              <div>
                <label htmlFor="fwc-work-order-ref" style={labelStyle}>
                  Linked Work Order
                </label>
                <input
                  id="fwc-work-order-ref"
                  type="text"
                  value={workOrderRef}
                  onChange={e => setWorkOrderRef(e.target.value)}
                  placeholder="Work order UUID or reference"
                  disabled={loading}
                  style={inputStyle}
                />
              </div>
            </div>

            {/* Row 6: Warranty Expiry Date (full width) */}
            <div>
              <label htmlFor="fwc-warranty-expiry" style={labelStyle}>
                Warranty Expiry Date
              </label>
              <input
                id="fwc-warranty-expiry"
                type="date"
                value={warrantyExpiry}
                onChange={e => setWarrantyExpiry(e.target.value)}
                disabled={loading}
                style={inputStyle}
              />
            </div>

            {/* Row 7: Currency + Claimed Amount (2-col) */}
            <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '12px' }}>
              <div>
                <label htmlFor="fwc-currency" style={labelStyle}>
                  Currency
                </label>
                <select
                  id="fwc-currency"
                  value={currency}
                  onChange={e => setCurrency(e.target.value)}
                  disabled={loading}
                  style={inputStyle}
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="NOK">NOK</option>
                  <option value="AUD">AUD</option>
                  <option value="SGD">SGD</option>
                </select>
              </div>
              <div>
                <label htmlFor="fwc-claimed-amount" style={labelStyle}>
                  Claimed Amount
                </label>
                <input
                  id="fwc-claimed-amount"
                  type="number"
                  value={claimedAmount}
                  onChange={e => setClaimedAmount(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  min="0"
                  disabled={loading}
                  style={inputStyle}
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 pb-6" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {error && (
              <p
                className="text-caption"
                style={{ color: 'var(--status-critical)', margin: 0 }}
              >
                {error}
              </p>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <GhostButton type="button" onClick={handleCancel} disabled={loading}>
                Cancel
              </GhostButton>
              <PrimaryButton type="submit" disabled={loading} aria-busy={loading}>
                {loading ? 'Filing…' : 'File Claim'}
              </PrimaryButton>
            </div>
          </div>
        </form>
      </div>
    </>
  );
}
