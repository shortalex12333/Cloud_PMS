'use client';

/**
 * Hours of Rest Detail Page - /hours-of-rest/[id]
 *
 * Tier 1 fragmented route for viewing a single hours of rest record.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-HOR-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';

// Feature flag guard
function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      // Redirect to legacy route with entity params
      const id = params.id as string;
      router.replace(`/app?entity=hours_of_rest&id=${id}`);
    }
  }, [router, params]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-txt-primary/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fetch hours of rest detail
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

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading hours of rest record...</p>
      </div>
    </div>
  );
}

// Error state
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-status-critical/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-status-critical">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Failed to Load</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

// Not found state
function NotFoundState() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Record Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This hours of rest record may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/hours-of-rest')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Hours of Rest
      </button>
    </div>
  );
}

// Hours of rest detail content
function HoursOfRestContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const crewMemberName = (data?.crew_member_name || 'Crew Member') as string;
  const crewMemberId = data?.crew_member_id as string;
  const date = data?.date as string;
  const status = (data?.status || '') as string;
  const compliant = data?.compliant as boolean;
  const workHours = data?.work_hours as number;
  const restHours = data?.rest_hours as number;
  const notes = data?.notes as string;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-tertiary font-mono">
          {date ? new Date(date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : ''}
        </p>
        <h1 className="text-2xl font-semibold text-txt-primary">{crewMemberName}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
          <StatusPill status={getComplianceColor(compliant)} label={compliant ? 'Compliant' : 'Non-Compliant'} />
        </div>
      </div>

      {/* Hours Summary */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-surface-elevated rounded-lg">
        <div className="space-y-1">
          <p className="text-xs text-txt-tertiary uppercase tracking-wider">Work Hours</p>
          <p className="text-2xl font-semibold text-txt-primary">{workHours}h</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-txt-tertiary uppercase tracking-wider">Rest Hours</p>
          <p className="text-2xl font-semibold text-txt-primary">{restHours}h</p>
        </div>
      </div>

      {/* Compliance Details */}
      <div className="space-y-2">
        <h2 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Compliance Status</h2>
        <div className={`p-4 rounded-lg ${compliant ? 'bg-status-success/10' : 'bg-status-critical/10'}`}>
          <div className="flex items-center gap-3">
            {compliant ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-success">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                <path d="M22 4L12 14.01l-3-3" />
              </svg>
            ) : (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-critical">
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            )}
            <div>
              <p className={`font-medium ${compliant ? 'text-status-success' : 'text-status-critical'}`}>
                {compliant ? 'Meets Requirements' : 'Does Not Meet Requirements'}
              </p>
              <p className="text-sm text-txt-secondary">
                {compliant
                  ? 'This record meets maritime work/rest hour regulations.'
                  : 'This record does not meet maritime work/rest hour regulations and requires review.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        {crewMemberId && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Crew Member</p>
            <button
              onClick={() => onNavigate('crew', crewMemberId)}
              className="text-sm text-accent-primary hover:text-accent-primary-hover transition-colors"
              data-testid="crew-link"
              data-navigate="crew"
            >
              {crewMemberName}
            </button>
          </div>
        )}
        {date && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Date</p>
            <p className="text-sm text-txt-secondary">{new Date(date).toLocaleDateString()}</p>
          </div>
        )}
      </div>

      {/* Notes */}
      {notes && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Notes</h2>
          <p className="text-txt-secondary">{notes}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border-subtle">
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
          Edit Record
        </button>
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
          Export Report
        </button>
      </div>
    </div>
  );
}

// Main page content
function HoursOfRestDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const recordId = params.id as string;

  // Fetch hours of rest record
  const {
    data: record,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['hours-of-rest-detail', recordId],
    queryFn: () => fetchHoursOfRestDetail(recordId, token || ''),
    enabled: !!recordId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/hours-of-rest');
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle cross-entity navigation
  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) => {
      if (isFragmentedRoutesEnabled()) {
        switch (entityType) {
          case 'crew':
            router.push(`/crew/${entityId}`);
            break;
          default:
            router.push(`/app?entity=${entityType}&id=${entityId}`);
        }
      } else {
        router.push(`/app?entity=${entityType}&id=${entityId}`);
      }
    },
    [router]
  );

  // Derive display values
  const payload = record?.payload as Record<string, unknown> | undefined;
  const crewMemberName = (record?.crew_member_name || payload?.crew_member_name || 'Crew Member') as string;
  const date = (record?.date || payload?.date) as string | undefined;

  // Render content based on state
  let content: React.ReactNode;

  if (isLoading) {
    content = <LoadingState />;
  } else if (error) {
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    if (errorMessage.includes('404')) {
      content = <NotFoundState />;
    } else {
      content = <ErrorState message={errorMessage} onRetry={handleRefresh} />;
    }
  } else if (!record) {
    content = <NotFoundState />;
  } else {
    content = (
      <HoursOfRestContent
        data={record}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <main role="main" data-testid="hours-of-rest-detail">
    <RouteLayout
      pageTitle={date ? `${crewMemberName} - ${new Date(date).toLocaleDateString()}` : crewMemberName}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
            aria-label="Back"
            data-testid="back-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <div>
            <p className="text-xs text-txt-tertiary uppercase tracking-wider">Hours of Rest</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {date ? `${crewMemberName} - ${new Date(date).toLocaleDateString()}` : crewMemberName}
            </h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
    </main>
  );
}

// Export with feature flag guard
export default function HoursOfRestDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <HoursOfRestDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
