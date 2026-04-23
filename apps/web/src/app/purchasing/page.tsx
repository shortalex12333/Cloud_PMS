'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { PurchaseOrderContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

interface PurchaseOrder {
  id: string;
  po_number?: string;
  status?: string;
  supplier_id?: string;
  supplier_name?: string;
  ordered_at?: string;
  received_at?: string;
  currency?: string;
  total_amount?: number;
  description?: string;
  created_at: string;
  updated_at?: string;
}

function poStatusVariant(status?: string): EntityListResult['statusVariant'] {
  switch (status) {
    case 'received': return 'signed';
    case 'cancelled': return 'cancelled';
    case 'ordered':
    case 'approved':
    case 'partially_received': return 'in_progress';
    default: return 'open';
  }
}

function poAdapter(po: PurchaseOrder): EntityListResult {
  const status = po.status?.replace(/_/g, ' ') || 'Draft';
  const supplier = po.supplier_name ? ` \u00b7 ${po.supplier_name}` : '';
  const amount = po.total_amount
    ? ` \u00b7 ${po.currency === 'EUR' ? '\u20ac' : po.currency === 'GBP' ? '\u00a3' : '$'}${po.total_amount.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
    : '';
  return {
    id: po.id,
    type: 'pms_purchase_orders',
    title: po.po_number || 'PO',
    subtitle: `${status}${supplier}${amount}`,
    entityRef: po.po_number || 'PO',
    status,
    statusVariant: poStatusVariant(po.status),
    severity: null,
    age: po.ordered_at ? formatAge(po.ordered_at) : (po.created_at ? formatAge(po.created_at) : '\u2014'),
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
  return <div className={lensStyles.root}><PurchaseOrderContent /></div>;
}

function PurchasingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/purchasing?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/purchasing${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<PurchaseOrder>
        domain="purchasing"
        queryKey={['purchasing']}
        table="pms_purchase_orders"
        columns="id, po_number, status, supplier_id, ordered_at, received_at, currency, created_at, updated_at"
        adapter={poAdapter}
        filterConfig={[]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No purchase orders recorded"
        sortBy="created_at"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="purchase_order" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function PurchasingPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <PurchasingPageContent />
    </React.Suspense>
  );
}
