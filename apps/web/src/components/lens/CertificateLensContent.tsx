'use client';

/**
 * CertificateLensContent - Inner content for Certificate lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { toast } from 'sonner';
import {
  useCertificateActions,
  useCertificatePermissions,
  type CertificateType,
} from '@/hooks/useCertificateActions';

export interface CertificateLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStatusToColor(status: string, expiryDate?: string): 'critical' | 'warning' | 'success' | 'neutral' {
  if (status === 'expired') return 'critical';
  if (status === 'expiring_soon') return 'warning';
  if (expiryDate) {
    const daysUntilExpiry = Math.floor((new Date(expiryDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry < 0) return 'critical';
    if (daysUntilExpiry < 30) return 'warning';
  }
  return 'success';
}

/**
 * Determine certificate type from data object.
 * Vessel certificates have vessel_id, crew certificates have crew_member_id.
 */
function determineCertificateType(data: Record<string, unknown>): CertificateType {
  if (data.crew_member_id || data.crewMemberId) {
    return 'crew';
  }
  // Default to vessel if vessel_id present or no crew identifier
  return 'vessel';
}

export function CertificateLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: CertificateLensContentProps) {
  // Determine certificate type for proper API routing
  const certType = determineCertificateType(data);

  // Hook up certificate actions and permissions
  const { renewCertificate, linkDocument, isLoading, error } = useCertificateActions(id, certType);
  const { canRenew, canLink } = useCertificatePermissions();

  // State for renewal dialog
  const [showRenewalInput, setShowRenewalInput] = useState(false);
  const [newExpiryDate, setNewExpiryDate] = useState('');

  // Map data
  const name = (data.name as string) || (data.title as string) || 'Certificate';
  const certificate_type = (data.certificate_type as string) || (data.type as string) || 'General';
  const issuing_authority = data.issuing_authority as string | undefined;
  const issue_date = data.issue_date as string | undefined;
  const expiry_date = data.expiry_date as string | undefined;
  const status = (data.status as string) || 'valid';
  const certificate_number = data.certificate_number as string | undefined;
  const notes = data.notes as string | undefined;

  const statusColor = mapStatusToColor(status, expiry_date);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // Calculate days until expiry
  let expiryDisplay = '—';
  if (expiry_date) {
    const daysUntilExpiry = Math.floor((new Date(expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry < 0) {
      expiryDisplay = `Expired ${Math.abs(daysUntilExpiry)} days ago`;
    } else if (daysUntilExpiry === 0) {
      expiryDisplay = 'Expires today';
    } else {
      expiryDisplay = `${daysUntilExpiry} days`;
    }
  }

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Type', value: certificate_type },
    { label: 'Authority', value: issuing_authority ?? 'Unknown' },
    { label: 'Issued', value: issue_date ? formatRelativeTime(issue_date) : '—' },
    { label: 'Expires', value: expiryDisplay, color: statusColor },
  ];

  /**
   * Handle certificate renewal submission.
   */
  const handleRenewCertificate = async () => {
    if (!newExpiryDate) {
      toast.error('Please select a new expiry date');
      return;
    }

    const result = await renewCertificate({ new_expiry_date: newExpiryDate });

    if (result.success) {
      toast.success('Certificate renewed successfully');
      setShowRenewalInput(false);
      setNewExpiryDate('');
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to renew certificate');
    }
  };

  /**
   * Toggle renewal input visibility.
   */
  const handleRenewClick = () => {
    if (showRenewalInput) {
      // If already showing, submit
      handleRenewCertificate();
    } else {
      // Show the date input
      setShowRenewalInput(true);
      // Pre-populate with a date 1 year from now
      const oneYearFromNow = new Date();
      oneYearFromNow.setFullYear(oneYearFromNow.getFullYear() + 1);
      setNewExpiryDate(oneYearFromNow.toISOString().split('T')[0]);
    }
  };

  /**
   * Cancel renewal flow.
   */
  const handleCancelRenewal = () => {
    setShowRenewalInput(false);
    setNewExpiryDate('');
  };

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Certificate" title={name} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={name}
            subtitle={certificate_number ? `#${certificate_number}` : undefined}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Renewal action - only shown if status is not success and user has permission */}
        {statusColor !== 'success' && canRenew && (
          <div className="mt-4 flex flex-col gap-3">
            {showRenewalInput && (
              <div className="flex items-center gap-3">
                <label htmlFor="new-expiry-date" className="text-celeste-text-muted text-sm">
                  New expiry date:
                </label>
                <input
                  id="new-expiry-date"
                  type="date"
                  value={newExpiryDate}
                  onChange={(e) => setNewExpiryDate(e.target.value)}
                  className="px-3 py-1.5 text-sm border border-surface-border rounded-md bg-surface-background text-celeste-text-primary focus:outline-none focus:ring-2 focus:ring-celeste-brand"
                  disabled={isLoading}
                />
              </div>
            )}
            <div className="flex items-center gap-2">
              <PrimaryButton
                onClick={handleRenewClick}
                disabled={isLoading}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                {isLoading ? 'Renewing...' : showRenewalInput ? 'Confirm Renewal' : 'Renew Certificate'}
              </PrimaryButton>
              {showRenewalInput && (
                <button
                  type="button"
                  onClick={handleCancelRenewal}
                  disabled={isLoading}
                  className="text-sm text-celeste-text-muted hover:text-celeste-text-primary transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 typo-body">
              {certificate_number && (
                <>
                  <dt className="text-celeste-text-muted">Certificate Number</dt>
                  <dd className="text-celeste-text-primary">{certificate_number}</dd>
                </>
              )}
              <dt className="text-celeste-text-muted">Type</dt>
              <dd className="text-celeste-text-primary">{certificate_type}</dd>
              {issuing_authority && (
                <>
                  <dt className="text-celeste-text-muted">Issuing Authority</dt>
                  <dd className="text-celeste-text-primary">{issuing_authority}</dd>
                </>
              )}
              {issue_date && (
                <>
                  <dt className="text-celeste-text-muted">Issue Date</dt>
                  <dd className="text-celeste-text-primary">{new Date(issue_date).toLocaleDateString()}</dd>
                </>
              )}
              {expiry_date && (
                <>
                  <dt className="text-celeste-text-muted">Expiry Date</dt>
                  <dd className="text-celeste-text-primary">{new Date(expiry_date).toLocaleDateString()}</dd>
                </>
              )}
            </dl>
          </SectionContainer>
        </div>

        {notes && (
          <div className="mt-6">
            <SectionContainer title="Notes" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">{notes}</p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}
