'use client';

/**
 * WarrantyLensContent - Inner content for Warranty lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

export interface WarrantyLensContentProps {
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

export function WarrantyLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: WarrantyLensContentProps) {
  // Map data
  const title = (data.title as string) || (data.name as string) || 'Warranty';
  const equipment_id = data.equipment_id as string | undefined;
  const equipment_name = data.equipment_name as string | undefined;
  const supplier = data.supplier as string | undefined;
  const start_date = data.start_date as string | undefined;
  const expiry_date = data.expiry_date as string | undefined;
  const status = (data.status as string) || 'active';
  const coverage = data.coverage as string | undefined;
  const terms = data.terms as string | undefined;

  const statusColor = mapStatusToColor(status, expiry_date);

  // Calculate days until expiry
  let expiryDisplay = '—';
  if (expiry_date) {
    const daysUntilExpiry = Math.floor((new Date(expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry < 0) {
      expiryDisplay = `Expired ${Math.abs(daysUntilExpiry)} days ago`;
    } else if (daysUntilExpiry === 0) {
      expiryDisplay = 'Expires today';
    } else {
      expiryDisplay = `${daysUntilExpiry} days remaining`;
    }
  }

  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Equipment', value: equipment_name ?? 'N/A', onClick: equipment_id && onNavigate ? () => onNavigate('equipment', equipment_id) : undefined },
    { label: 'Supplier', value: supplier ?? 'Unknown' },
    { label: 'Started', value: start_date ? formatRelativeTime(start_date) : '—' },
    { label: 'Expires', value: expiryDisplay, color: statusColor },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Warranty" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            subtitle={equipment_name}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {status === 'active' && (
          <div className="mt-4">
            <PrimaryButton onClick={() => console.log('[WarrantyLens] File claim:', id)} className="text-[13px] min-h-[36px] px-4 py-2">File Claim</PrimaryButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {coverage && (
          <div className="mt-6">
            <SectionContainer title="Coverage" stickyTop={56}>
              <p className="text-sm text-txt-primary whitespace-pre-wrap">{coverage}</p>
            </SectionContainer>
          </div>
        )}

        {terms && (
          <div className="mt-6">
            <SectionContainer title="Terms & Conditions" stickyTop={56}>
              <p className="text-sm text-txt-primary whitespace-pre-wrap">{terms}</p>
            </SectionContainer>
          </div>
        )}

        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {supplier && (
                <>
                  <dt className="text-txt-tertiary">Supplier</dt>
                  <dd className="text-txt-primary">{supplier}</dd>
                </>
              )}
              {start_date && (
                <>
                  <dt className="text-txt-tertiary">Start Date</dt>
                  <dd className="text-txt-primary">{new Date(start_date).toLocaleDateString()}</dd>
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
      </main>
    </div>
  );
}

export default WarrantyLensContent;
