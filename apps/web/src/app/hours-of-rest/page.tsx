'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HoursOfRestContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

interface HoRRecord {
  id: string;
  crew_member_name?: string;
  record_date?: string;
  total_rest_hours?: number;
  total_work_hours?: number;
  is_compliant?: boolean;
  status?: string;
  created_at: string;
  updated_at?: string;
}

function horAdapter(r: HoRRecord): EntityListResult {
  const status = r.is_compliant === false ? 'Non-Compliant' : r.status?.replace(/_/g, ' ') || 'Compliant';
  const date = r.record_date ? new Date(r.record_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
  return {
    id: r.id,
    type: 'pms_hours_of_rest',
    title: r.crew_member_name || 'Rest Record',
    subtitle: `${date} · ${r.total_work_hours ?? 0}h work · ${r.total_rest_hours ?? 0}h rest`,
    entityRef: r.record_date ? new Date(r.record_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) : '',
    status,
    statusVariant: r.is_compliant === false ? 'critical' : r.status === 'pending' ? 'pending' : 'signed',
    severity: r.is_compliant === false ? 'critical' : null,
    age: r.record_date ? formatAge(r.record_date) : '\u2014',
  };
}

function formatAge(d: string): string {
  const days = Math.floor((Date.now() - new Date(d).getTime()) / 86_400_000);
  if (days < 1) return 'Today';
  if (days === 1) return '1d';
  if (days < 7) return `${days}d`;
  const date = new Date(d);
  return `${date.getDate()} ${date.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function LensContent() {
  return <div className={lensStyles.root}><HoursOfRestContent /></div>;
}

function HoRPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/hours-of-rest?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/hours-of-rest${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<HoRRecord>
        domain="hours-of-rest"
        queryKey={['hours-of-rest']}
        table="v_hours_of_rest_enriched"
        columns="*"
        adapter={horAdapter}
        filterConfig={[]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No rest records"
        sortBy="record_date"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="hours_of_rest" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function HoursOfRestPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <HoRPageContent />
    </React.Suspense>
  );
}
