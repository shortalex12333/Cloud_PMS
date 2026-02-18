'use client';

/**
 * CertificateLensContent - Inner content for Certificate lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

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

export function CertificateLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: CertificateLensContentProps) {
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

        {statusColor !== 'success' && (
          <div className="mt-4">
            <PrimaryButton onClick={() => console.log('[CertificateLens] Renew:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Renew Certificate</PrimaryButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {certificate_number && (
                <>
                  <dt className="text-txt-tertiary">Certificate Number</dt>
                  <dd className="text-txt-primary">{certificate_number}</dd>
                </>
              )}
              <dt className="text-txt-tertiary">Type</dt>
              <dd className="text-txt-primary">{certificate_type}</dd>
              {issuing_authority && (
                <>
                  <dt className="text-txt-tertiary">Issuing Authority</dt>
                  <dd className="text-txt-primary">{issuing_authority}</dd>
                </>
              )}
              {issue_date && (
                <>
                  <dt className="text-txt-tertiary">Issue Date</dt>
                  <dd className="text-txt-primary">{new Date(issue_date).toLocaleDateString()}</dd>
                </>
              )}
              {expiry_date && (
                <>
                  <dt className="text-txt-tertiary">Expiry Date</dt>
                  <dd className="text-txt-primary">{new Date(expiry_date).toLocaleDateString()}</dd>
                </>
              )}
            </dl>
          </SectionContainer>
        </div>

        {notes && (
          <div className="mt-6">
            <SectionContainer title="Notes" stickyTop={56}>
              <p className="text-sm text-txt-primary">{notes}</p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}

export default CertificateLensContent;
