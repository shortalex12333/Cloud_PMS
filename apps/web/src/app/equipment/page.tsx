'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EquipmentLensContent } from '@/components/lens/EquipmentLensContent';
import { fetchEquipment, fetchEquipmentItem } from '@/features/equipment/api';
import { equipmentToListResult } from '@/features/equipment/adapter';
import type { Equipment } from '@/features/equipment/types';

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

function EquipmentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const selectedId = searchParams.get('id');
  const { session } = useAuth();
  const token = session?.access_token;

  // Fetch selected equipment data
  const { data: equipmentData, isLoading, error } = useQuery({
    queryKey: ['equipment', selectedId],
    queryFn: () => fetchEquipmentItem(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/equipment?id=${id}`, { scroll: false });
    },
    [router]
  );

  const handleCloseDetail = React.useCallback(() => {
    router.push('/equipment', { scroll: false });
  }, [router]);

  const handleRefresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['equipment'] });
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ['equipment', selectedId] });
    }
  }, [queryClient, selectedId]);

  // Render loading state for lens content
  const renderLensContent = () => {
    if (!selectedId) return null;

    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        </div>
      );
    }

    if (error || !equipmentData) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-red-400">Failed to load equipment</p>
        </div>
      );
    }

    return (
      <EquipmentLensContent
        id={selectedId}
        data={equipmentData as unknown as Record<string, unknown>}
        onBack={handleCloseDetail}
        onClose={handleCloseDetail}
        onRefresh={handleRefresh}
      />
    );
  };

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<Equipment>
        queryKey={['equipment']}
        fetchFn={fetchEquipment}
        adapter={equipmentToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No equipment found"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {renderLensContent()}
      </EntityDetailOverlay>
    </div>
  );
}

export default function EquipmentPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <EquipmentPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
