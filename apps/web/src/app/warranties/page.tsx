'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { WarrantyContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';
import { useAuth } from '@/hooks/useAuth';

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
  const statusVariant: EntityListResult['statusVariant'] =
    w.status === 'rejected'     ? 'critical' :
    w.status === 'submitted' || w.status === 'under_review' ? 'warning' :
    w.status === 'approved'     ? 'open' :
    w.status === 'closed'       ? 'neutral' :
    'open'; // draft

  return {
    id: w.id,
    type: 'pms_warranty_claims',
    title: w.title || w.claim_number || 'Warranty Claim',
    subtitle: `${w.status?.replace(/_/g, ' ') ?? 'Draft'}${w.vendor_name ? ` \u00b7 ${w.vendor_name}` : ''}`,
    entityRef: w.claim_number || '—',
    status: w.status?.replace(/_/g, ' ') ?? 'Draft',
    statusVariant,
    severity: w.status === 'rejected' ? 'critical' : w.status === 'submitted' ? 'warning' : null,
    age: w.created_at ? formatAge(w.created_at) : '—',
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
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const selectedId = searchParams.get('id');

  const [newClaimOpen, setNewClaimOpen] = React.useState(false);
  const [newClaimTitle, setNewClaimTitle] = React.useState('');
  const [newClaimVendor, setNewClaimVendor] = React.useState('');
  const [newClaimLoading, setNewClaimLoading] = React.useState(false);
  const [newClaimError, setNewClaimError] = React.useState<string | null>(null);

  const handleFileNewClaim = React.useCallback(async () => {
    if (!newClaimTitle.trim()) { setNewClaimError('Title is required'); return; }
    setNewClaimLoading(true);
    setNewClaimError(null);
    try {
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session?.access_token}` },
        body: JSON.stringify({
          action: 'file_warranty_claim',
          context: {},
          payload: { title: newClaimTitle.trim(), vendor_name: newClaimVendor.trim() },
        }),
      });
      const result = await res.json();
      if (result.success === false) { setNewClaimError(result.message ?? result.error ?? 'Failed to create claim'); return; }
      setNewClaimOpen(false);
      setNewClaimTitle('');
      setNewClaimVendor('');
      queryClient.invalidateQueries({ queryKey: ['warranties'] });
    } catch (e) {
      setNewClaimError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setNewClaimLoading(false);
    }
  }, [newClaimTitle, newClaimVendor, session, queryClient]);

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
    <div className="h-full bg-surface-base" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '12px 20px 0', flexShrink: 0 }}>
        <button
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 600,
            borderRadius: '6px',
            background: 'var(--mark)',
            color: 'var(--mark-fg, #000)',
            border: 'none',
            cursor: 'pointer',
          }}
          onClick={() => setNewClaimOpen(true)}
        >
          File New Claim
        </button>
      </div>

      {newClaimOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div role="dialog" aria-modal="true" aria-label="File New Warranty Claim" style={{ background: 'var(--surface)', borderRadius: '8px', padding: '24px', width: '440px', maxWidth: 'calc(100vw - 32px)', border: '1px solid var(--border-sub)' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--txt)', marginBottom: '16px' }}>File New Warranty Claim</div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--txt2)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Claim Title *</label>
              <input
                value={newClaimTitle}
                onChange={e => setNewClaimTitle(e.target.value)}
                name="title"
                placeholder="e.g. Main Engine Pump — Seal Failure"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '5px', border: '1px solid var(--border-sub)', background: 'var(--surface-el)', color: 'var(--txt)', fontSize: '13px', fontFamily: 'var(--font-sans)', boxSizing: 'border-box' }}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--txt2)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Vendor / Supplier</label>
              <input
                value={newClaimVendor}
                onChange={e => setNewClaimVendor(e.target.value)}
                placeholder="e.g. Caterpillar Marine"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '5px', border: '1px solid var(--border-sub)', background: 'var(--surface-el)', color: 'var(--txt)', fontSize: '13px', fontFamily: 'var(--font-sans)', boxSizing: 'border-box' }}
              />
            </div>
            {newClaimError && <div style={{ fontSize: '12px', color: '#ef4444', marginBottom: '12px' }}>{newClaimError}</div>}
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button onClick={() => { setNewClaimOpen(false); setNewClaimError(null); }} style={{ padding: '8px 16px', borderRadius: '5px', border: '1px solid var(--border-sub)', background: 'transparent', color: 'var(--txt2)', fontSize: '13px', cursor: 'pointer' }}>Cancel</button>
              <button type="submit" onClick={handleFileNewClaim} disabled={newClaimLoading} style={{ padding: '8px 16px', borderRadius: '5px', border: 'none', background: 'var(--mark)', color: 'var(--mark-fg, #000)', fontSize: '13px', fontWeight: 600, cursor: newClaimLoading ? 'not-allowed' : 'pointer', opacity: newClaimLoading ? 0.7 : 1 }}>
                {newClaimLoading ? 'Filing…' : 'File Claim'}
              </button>
            </div>
          </div>
        </div>
      )}
      <div style={{ flex: 1, overflow: 'hidden' }}>
      <FilteredEntityList<Warranty>
        domain="warranties"
        queryKey={['warranties']}
        table="v_warranty_enriched"
        columns="id, claim_number, title, status, warranty_expiry, vendor_name, claimed_amount, currency, created_at, updated_at"
        adapter={warrantyAdapter}
        filterConfig={[
          {
            key: 'status',
            label: 'Status',
            type: 'select' as const,
            options: [
              { value: 'draft',        label: 'Draft' },
              { value: 'submitted',    label: 'Submitted' },
              { value: 'under_review', label: 'Under Review' },
              { value: 'approved',     label: 'Approved' },
              { value: 'rejected',     label: 'Rejected' },
              { value: 'closed',       label: 'Closed' },
            ],
            category: 'status-priority' as const,
          },
        ]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No warranty records"
        sortBy="created_at"
      />
      </div>

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
