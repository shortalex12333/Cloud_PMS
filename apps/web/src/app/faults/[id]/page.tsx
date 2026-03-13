'use client';

/**
 * Fault Detail Page - /faults/[id]
 *
 * Tier 1 fragmented route for viewing a single fault.
 *
 * @see REQUIREMENTS_TABLE.md - T1-F-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { useAuth } from '@/hooks/useAuth';
import { useFaultActions } from '@/hooks/useFaultActions';
import { StatusPill } from '@/components/ui/StatusPill';
import { AttachmentsSection, RelatedEntitiesSection, HistorySection } from '@/components/lens/sections';
import { type Attachment, type RelatedEntity } from '@/components/lens/sections';
import { getEntityRoute } from '@/lib/featureFlags';
import { useEntityLedger } from '@/hooks/useEntityLedger';
import { useReadBeacon } from '@/hooks/useReadBeacon';

async function fetchFaultDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/fault/${id}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch fault: ${response.status}`);
  return response.json();
}

function getSeverityColor(severity: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity?.toLowerCase()) {
    case 'critical': case 'high': return 'critical';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'neutral';
  }
}

function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'open': case 'reported': return 'critical';
    case 'in_progress': case 'investigating': return 'warning';
    case 'resolved': case 'closed': return 'success';
    default: return 'neutral';
  }
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading fault...</p>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-400">
          <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">{message}</p>
      <button onClick={onRetry} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Try Again</button>
    </div>
  );
}

function NotFoundState() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Fault Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">This fault may have been deleted or you may not have access.</p>
      <button onClick={() => router.push('/faults')} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Back to Faults</button>
    </div>
  );
}

function FaultContent({ data, onNavigate, onRefresh }: { data: Record<string, unknown>; onNavigate: (type: string, id: string) => void; onRefresh?: () => void }) {
  const title = (data?.title || 'Fault') as string;
  const severity = (data?.severity || '') as string;
  const status = (data?.status || '') as string;
  const description = data?.description as string;
  const equipmentId = data?.equipment_id as string;
  const equipmentName = data?.equipment_name as string;
  const reportedBy = data?.reported_by_name as string;
  const reportedAt = data?.reported_at as string;
  const attachments = (data?.attachments as Attachment[]) || [];
  const related_entities = (data?.related_entities as RelatedEntity[]) || [];

  const faultId = data?.id as string;
  const { session } = useAuth();
  const { isLoading, acknowledgeFault, closeFault, reopenFault, markFalseAlarm } = useFaultActions(faultId);
  const { data: history = [] } = useEntityLedger('fault', faultId);
  useReadBeacon('fault', faultId);
  const [creatingWO, setCreatingWO] = React.useState(false);

  const handleAcknowledge = React.useCallback(async () => {
    const result = await acknowledgeFault();
    if (result.success) onRefresh?.();
  }, [acknowledgeFault, onRefresh]);

  const handleClose = React.useCallback(async () => {
    const result = await closeFault();
    if (result.success) onRefresh?.();
  }, [closeFault, onRefresh]);

  const handleMarkFalseAlarm = React.useCallback(async () => {
    const result = await markFalseAlarm();
    if (result.success) onRefresh?.();
  }, [markFalseAlarm, onRefresh]);

  const handleReopen = React.useCallback(async () => {
    const result = await reopenFault();
    if (result.success) onRefresh?.();
  }, [reopenFault, onRefresh]);

  const handleCreateWorkOrder = React.useCallback(async () => {
    if (!session?.access_token) return;
    setCreatingWO(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
      const response = await fetch(`${baseUrl}/v1/actions/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          action: 'create_work_order_from_fault',
          context: {},
          payload: { fault_id: data.id as string },
        }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error((json as { error?: string; detail?: string }).error || (json as { error?: string; detail?: string }).detail || `${response.status}`);
      onRefresh?.();
    } catch (err) {
      console.error('[FaultContent] create_work_order_from_fault failed:', err);
    } finally {
      setCreatingWO(false);
    }
  }, [session, data.id, onRefresh]);

  const statusLower = status.toLowerCase();

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-white">{title}</h1>
        <div className="flex gap-2">
          <StatusPill status={getSeverityColor(severity)} label={severity} />
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      {description && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Description</h2>
          <p className="text-white/80">{description}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {equipmentId && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Equipment</p>
            <button onClick={() => onNavigate('equipment', equipmentId)} className="text-sm text-blue-400 hover:text-blue-300 transition-colors" data-testid="equipment-link">
              {equipmentName || equipmentId}
            </button>
          </div>
        )}
        {reportedBy && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Reported By</p>
            <p className="text-sm text-white/80">{reportedBy}</p>
          </div>
        )}
        {reportedAt && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Reported</p>
            <p className="text-sm text-white/80">{new Date(reportedAt).toLocaleDateString()}</p>
          </div>
        )}
      </div>

      {/* Attachments */}
      {attachments.length > 0 && (
        <AttachmentsSection attachments={attachments} onAddFile={() => {}} canAddFile={false} />
      )}

      {/* Related Entities */}
      {related_entities.length > 0 && (
        <RelatedEntitiesSection entities={related_entities} onNavigate={(type, id) => onNavigate(type, id)} />
      )}

      {history.length > 0 && (
        <HistorySection history={history} />
      )}

      <div className="flex gap-3 pt-4 border-t border-white/10 flex-wrap">
        {(statusLower === 'open' || statusLower === 'reported') && (
          <button
            onClick={handleAcknowledge}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
          >
            {isLoading && <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
            Acknowledge
          </button>
        )}
        {(statusLower === 'investigating' || statusLower === 'acknowledged' || statusLower === 'diagnosed') && (
          <>
            <button
              onClick={handleClose}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
            >
              {isLoading && <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
              Close Fault
            </button>
            <button
              onClick={handleMarkFalseAlarm}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
            >
              {isLoading && <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
              Mark False Alarm
            </button>
          </>
        )}
        {(statusLower === 'closed' || statusLower === 'false_alarm') && (
          <button
            onClick={handleReopen}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
          >
            {isLoading && <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
            Reopen
          </button>
        )}
        <button
          onClick={handleCreateWorkOrder}
          disabled={creatingWO}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
        >
          {creatingWO && <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />}
          {creatingWO ? 'Creating...' : 'Create Work Order'}
        </button>
      </div>
    </div>
  );
}

function FaultDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;
  const faultId = params.id as string;

  const { data: fault, isLoading, error, refetch } = useQuery({
    queryKey: ['fault', faultId],
    queryFn: () => fetchFaultDetail(faultId, token || ''),
    enabled: !!faultId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleRefresh = React.useCallback(() => refetch(), [refetch]);
  const handleNavigate = React.useCallback((entityType: string, entityId: string) => {
    router.push(getEntityRoute(entityType as any, entityId));
  }, [router]);

  const title = (fault?.title || 'Fault') as string;

  let content: React.ReactNode;
  if (isLoading) content = <LoadingState />;
  else if (error) {
    const msg = error instanceof Error ? error.message : 'An error occurred';
    content = msg.includes('404') ? <NotFoundState /> : <ErrorState message={msg} onRetry={handleRefresh} />;
  }
  else if (!fault) content = <NotFoundState />;
  else content = <FaultContent data={fault} onNavigate={handleNavigate} onRefresh={handleRefresh} />;

  return (
    <RouteLayout
      pageTitle={title}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back" data-testid="back-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <div>
            <p className="text-xs text-white/40 uppercase tracking-wider">Fault</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">{title}</h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

export default function FaultDetailPage() {
  return (
    <React.Suspense fallback={<LoadingState />}>
      <FaultDetailPageContent />
    </React.Suspense>
  );
}
