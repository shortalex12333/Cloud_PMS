'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { CertificateContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

interface Certificate {
  id: string;
  certificate_name?: string;
  certificate_number?: string;
  certificate_type?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: string;
  created_at: string;
  updated_at?: string;
}

function certAdapter(c: Certificate): EntityListResult {
  const status = c.status?.replace(/_/g, ' ') || 'Valid';
  const daysLeft = c.expiry_date ? Math.ceil((new Date(c.expiry_date).getTime() - Date.now()) / 86_400_000) : null;
  return {
    id: c.id,
    type: 'pms_vessel_certificates',
    title: c.certificate_name || c.certificate_number || 'Certificate',
    subtitle: `${c.certificate_type || ''} · ${c.issuing_authority || ''}`.replace(/^ · |· $/g, ''),
    entityRef: c.certificate_number || 'Certificate',
    status,
    statusVariant: c.status === 'expired' ? 'critical' : c.status === 'expiring_soon' ? 'warning' : 'open',
    severity: c.status === 'expired' ? 'critical' : c.status === 'expiring_soon' ? 'warning' : null,
    age: daysLeft !== null ? (daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : `${daysLeft}d`) : '\u2014',
  };
}

function LensContent() {
  return <div className={lensStyles.root}><CertificateContent /></div>;
}

function CertificatesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/certificates?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/certificates${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Certificate>
        domain="certificates"
        queryKey={['certificates']}
        table="v_certificates_enriched"
        columns="*"
        adapter={certAdapter}
        filterConfig={[]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No certificates recorded"
        sortBy="expiry_date"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="certificate" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function CertificatesPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <CertificatesPageContent />
    </React.Suspense>
  );
}
