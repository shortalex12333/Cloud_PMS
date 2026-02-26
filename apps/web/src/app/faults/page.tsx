'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { FaultLensContent } from '@/components/lens/FaultLensContent';
import { fetchFaults, fetchFault } from '@/features/faults/api';
import { faultToListResult } from '@/features/faults/adapter';
import type { Fault } from '@/features/faults/types';

function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      router.replace('/app');
    }
  }, [router]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

interface FaultDetailContentProps {
  id: string;
  onClose: () => void;
}

function FaultDetailContent({ id, onClose }: FaultDetailContentProps) {
  const { session } = useAuth();
  const token = session?.access_token;
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['fault', id],
    queryFn: () => fetchFault(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  const handleRefresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['fault', id] });
    queryClient.invalidateQueries({ queryKey: ['faults'] });
  }, [queryClient, id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-400">Failed to load fault</p>
      </div>
    );
  }

  return (
    <FaultLensContent
      id={id}
      data={data as unknown as Record<string, unknown>}
      onBack={onClose}
      onClose={onClose}
      onRefresh={handleRefresh}
    />
  );
}

function FaultsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const activeFilter = searchParams.get('filter');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams();
      params.set('id', id);
      if (activeFilter) params.set('filter', activeFilter);
      router.push(`/faults?${params.toString()}`, { scroll: false });
    },
    [router, activeFilter]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = activeFilter ? `?filter=${activeFilter}` : '';
    router.push(`/faults${params}`, { scroll: false });
  }, [router, activeFilter]);

  const handleClearFilter = React.useCallback(() => {
    router.push('/faults', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<Fault>
        queryKey={['faults']}
        fetchFn={fetchFaults}
        adapter={faultToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No faults found"
        filter={activeFilter}
        filterDomain="faults"
        onClearFilter={handleClearFilter}
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <FaultDetailContent id={selectedId} onClose={handleCloseDetail} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function FaultsPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <FaultsPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
