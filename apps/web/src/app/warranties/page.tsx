'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { WarrantyContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

interface Warranty {
  id: string;
  claim_number?: string;
  title?: string;
  status?: string;
  warranty_expiry?: string;
  vendor_name?: string;
  claimed_amount?: number;
  currency?: string;
  created_at: string;
  updated_at?: string;
}

function warrantyAdapter(w: Warranty): EntityListResult {
  const status = w.status?.replace(/_/g, ' ') || 'Active';
  return {
    id: w.id,
    type: 'pms_warranty_claims',
    title: w.title || w.claim_number || 'Warranty',
    subtitle: `${status}${w.vendor_name ? ` \u00b7 ${w.vendor_name}` : ''}`,
    entityRef: w.claim_number || 'Warranty',
    status,
    statusVariant: w.status === 'expired' ? 'critical' : w.status === 'expiring_soon' ? 'warning' : 'open',
    severity: w.status === 'expired' ? 'critical' : w.status === 'expiring_soon' ? 'warning' : null,
    age: w.warranty_expiry ? formatAge(w.warranty_expiry) : '\u2014',
  };
}

function formatAge(d: string): string {
  const days = Math.floor((Date.now() - new Date(d).getTime()) / 86_400_000);
  if (days < 1) return '<1d';
  if (days < 7) return `${days}d`;
  const date = new Date(d);
  return `${date.getDate()} ${date.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function LensContent() {
  return <div className={lensStyles.root}><WarrantyContent /></div>;
}

function WarrantiesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/warranties?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/warranties${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Warranty>
        domain="warranties"
        queryKey={['warranties']}
        table="v_warranty_enriched"
        columns="id, claim_number, title, status, warranty_expiry, vendor_name, claimed_amount, currency, created_at, updated_at"
        adapter={warrantyAdapter}
        filterConfig={[]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No warranty records"
        sortBy="created_at"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="warranty" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function WarrantiesPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <WarrantiesPageContent />
    </React.Suspense>
  );
}
