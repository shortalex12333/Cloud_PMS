'use client';

/**
 * Hours of Rest List Page - /hours-of-rest
 *
 * Tier 1 fragmented route for hours of rest records.
 * Displays a list of crew rest compliance records with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-HOR-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

// Feature flag guard - redirect if disabled
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
        <p className="text-txt-primary/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Hours of rest list item type
interface HoursOfRestListItem {
  id: string;
  crew_member_name: string;
  crew_member_id: string;
  date: string;
  work_hours: number;
  rest_hours: number;
  compliant: boolean;
  notes?: string;
  status: 'compliant' | 'non_compliant' | 'pending_review';
}

// Fetch hours of rest from API
async function fetchHoursOfRest(yachtId: string, token: string): Promise<HoursOfRestListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/hours-of-rest?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hours of rest: ${response.status}`);
  }

  const data = await response.json();
  return data.hours_of_rest || data.items || data || [];
}

// Fetch single hours of rest detail
async function fetchHoursOfRestDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/hours_of_rest/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hours of rest record: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'non_compliant':
      return 'critical';
    case 'pending_review':
      return 'warning';
    case 'compliant':
      return 'success';
    default:
      return 'neutral';
  }
}

// Compliance color mapping
function getComplianceColor(compliant: boolean): 'critical' | 'success' {
  return compliant ? 'success' : 'critical';
}

// Hours of Rest List Item Component
function HoursOfRestRow({
  item,
  isSelected,
  onClick,
}: {
  item: HoursOfRestListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-border-subtle',
        'hover:bg-surface-hover transition-colors',
        'focus:outline-none focus:bg-surface-hover',
        isSelected && 'bg-surface-selected'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
            <StatusPill status={getComplianceColor(item.compliant)} label={item.compliant ? 'Compliant' : 'Non-Compliant'} />
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.crew_member_name}</h3>
          <div className="flex items-center gap-4 mt-1">
            <p className="text-xs text-txt-secondary">
              Work: {item.work_hours}h | Rest: {item.rest_hours}h
            </p>
          </div>
        </div>
        <div className="text-xs text-txt-tertiary whitespace-nowrap">
          {new Date(item.date).toLocaleDateString()}
        </div>
      </div>
    </button>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Hours of Rest Records</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Record crew work and rest hours to track compliance with maritime regulations.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading hours of rest...</p>
      </div>
    </div>
  );
}

// Hours of rest detail content
function HoursOfRestDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const crewMemberName = (data?.crew_member_name || 'Crew Member') as string;
  const date = data?.date as string;
  const status = (data?.status || '') as string;
  const compliant = data?.compliant as boolean;
  const workHours = data?.work_hours as number;
  const restHours = data?.rest_hours as number;
  const notes = data?.notes as string;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
          aria-label="Back"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div>
          <p className="text-xs text-txt-tertiary">{date ? new Date(date).toLocaleDateString() : ''}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{crewMemberName}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        <StatusPill status={getComplianceColor(compliant)} label={compliant ? 'Compliant' : 'Non-Compliant'} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-txt-tertiary">Work Hours</p>
          <p className="text-sm text-txt-primary">{workHours}h</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-txt-tertiary">Rest Hours</p>
          <p className="text-sm text-txt-primary">{restHours}h</p>
        </div>
      </div>
      {notes && (
        <div className="space-y-1">
          <p className="text-xs text-txt-tertiary">Notes</p>
          <p className="text-sm text-txt-secondary">{notes}</p>
        </div>
      )}
    </div>
  );
}

// Main page component
function HoursOfRestPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch hours of rest list
  const {
    data: hoursOfRestRecords,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['hours-of-rest', user?.yachtId],
    queryFn: () => fetchHoursOfRest(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected hours of rest detail
  const {
    data: selectedRecord,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['hours-of-rest-detail', selectedId],
    queryFn: () => fetchHoursOfRestDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle record selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/hours-of-rest?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/hours-of-rest', { scroll: false });
  }, [router]);

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetchList();
    refetchDetail();
  }, [refetchList, refetchDetail]);

  // Render list content
  const listContent = React.useMemo(() => {
    if (isLoadingList) {
      return <LoadingState />;
    }

    if (listError) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-status-critical">Failed to load hours of rest records</p>
        </div>
      );
    }

    if (!hoursOfRestRecords || hoursOfRestRecords.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-border-subtle">
        {hoursOfRestRecords.map((record) => (
          <HoursOfRestRow
            key={record.id}
            item={record}
            isSelected={record.id === selectedId}
            onClick={() => handleSelect(record.id)}
          />
        ))}
      </div>
    );
  }, [hoursOfRestRecords, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Hours of Rest"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Hours of Rest</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedRecord?.crew_member_name as string || 'Hours of Rest',
              subtitle: selectedRecord?.date ? new Date(selectedRecord.date as string).toLocaleDateString() : undefined,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedRecord ? (
                <HoursOfRestDetailContent
                  data={selectedRecord}
                  onBack={handleBack}
                  onClose={handleCloseDetail}
                />
              ) : null,
            }
          : undefined
      }
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

// Export with feature flag guard
export default function HoursOfRestPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <HoursOfRestPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
