'use client';

/**
 * Equipment Detail Page - /equipment/[id]
 *
 * Tier 1 fragmented route for viewing a single equipment item.
 *
 * @see REQUIREMENTS_TABLE.md - T1-EQ-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { AttachmentsSection, RelatedEntitiesSection, HistorySection } from '@/components/lens/sections';
import { type Attachment, type RelatedEntity } from '@/components/lens/sections';
import { getEntityRoute } from '@/lib/featureFlags';
import { useEquipmentActions } from '@/hooks/useEquipmentActions';
import { useEntityLedger } from '@/hooks/useEntityLedger';
import { useReadBeacon } from '@/hooks/useReadBeacon';

async function fetchEquipmentDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/equipment/${id}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch equipment: ${response.status}`);
  return response.json();
}

function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'critical': case 'failed': case 'broken': return 'critical';
    case 'needs_maintenance': case 'degraded': return 'warning';
    case 'operational': case 'good': case 'active': return 'success';
    default: return 'neutral';
  }
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading equipment...</p>
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
      <h3 className="text-lg font-medium text-white mb-2">Equipment Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">This equipment may have been removed or you may not have access.</p>
      <button onClick={() => router.push('/equipment')} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Back to Equipment</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline modal: Report Fault
// ---------------------------------------------------------------------------

interface ReportFaultModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (title: string, description: string, severity: string) => void;
  isLoading: boolean;
}

function ReportFaultModal({ open, onClose, onSubmit, isLoading }: ReportFaultModalProps) {
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [severity, setSeverity] = React.useState('minor');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit(title.trim(), description.trim(), severity);
  };

  const handleClose = () => {
    setTitle('');
    setDescription('');
    setSeverity('minor');
    onClose();
  };

  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/60" onClick={handleClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-[#1a1a2e] border border-white/10 rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <h2 className="text-base font-semibold text-white">Report Fault</h2>
          <button onClick={handleClose} className="p-1 hover:bg-white/10 rounded transition-colors" aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Title <span className="text-red-400">*</span></label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Engine oil leak on port side"
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-white/30 transition-colors"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the fault in detail..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-white/30 transition-colors resize-none"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
            >
              <option value="cosmetic">Cosmetic</option>
              <option value="minor">Minor</option>
              <option value="major">Major</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={handleClose} disabled={isLoading} className="flex-1 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors disabled:opacity-50">
              Cancel
            </button>
            <button type="submit" disabled={isLoading || !title.trim()} className="flex-1 px-4 py-2 bg-red-500/80 hover:bg-red-500 rounded-lg text-sm text-white font-medium transition-colors disabled:opacity-50">
              {isLoading ? 'Submitting…' : 'Report Fault'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Inline modal: Create Work Order
// ---------------------------------------------------------------------------

interface CreateWorkOrderModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (title: string, description: string, priority: 'routine' | 'important' | 'critical') => void;
  isLoading: boolean;
}

function CreateWorkOrderModal({ open, onClose, onSubmit, isLoading }: CreateWorkOrderModalProps) {
  const [title, setTitle] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [priority, setPriority] = React.useState<'routine' | 'important' | 'critical'>('routine');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit(title.trim(), description.trim(), priority);
  };

  const handleClose = () => {
    setTitle('');
    setDescription('');
    setPriority('routine');
    onClose();
  };

  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/60" onClick={handleClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-[#1a1a2e] border border-white/10 rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <h2 className="text-base font-semibold text-white">Create Work Order</h2>
          <button onClick={handleClose} className="p-1 hover:bg-white/10 rounded transition-colors" aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Title <span className="text-red-400">*</span></label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Replace fuel filter"
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-white/30 transition-colors"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the work required..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-white/30 transition-colors resize-none"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-wider">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as 'routine' | 'important' | 'critical')}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
            >
              <option value="routine">Routine</option>
              <option value="important">Important</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={handleClose} disabled={isLoading} className="flex-1 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors disabled:opacity-50">
              Cancel
            </button>
            <button type="submit" disabled={isLoading || !title.trim()} className="flex-1 px-4 py-2 bg-blue-500/80 hover:bg-blue-500 rounded-lg text-sm text-white font-medium transition-colors disabled:opacity-50">
              {isLoading ? 'Creating…' : 'Create Work Order'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Equipment content
// ---------------------------------------------------------------------------

function EquipmentContent({ data, onNavigate, onRefresh }: { data: Record<string, unknown>; onNavigate: (type: string, id: string) => void; onRefresh?: () => void }) {
  const equipmentEntityId = data?.id as string;
  const { reportFault, createWorkOrderForEquipment, isLoading: actionsLoading } = useEquipmentActions(equipmentEntityId);
  const { data: history = [] } = useEntityLedger('equipment', equipmentEntityId);
  useReadBeacon('equipment', equipmentEntityId);
  const [showReportFaultModal, setShowReportFaultModal] = React.useState(false);
  const [showCreateWOModal, setShowCreateWOModal] = React.useState(false);

  const name = (data?.name || 'Equipment') as string;
  const equipmentType = (data?.equipment_type || '') as string;
  const status = (data?.status || '') as string;
  const manufacturer = data?.manufacturer as string;
  const model = data?.model as string;
  const serialNumber = data?.serial_number as string;
  const location = data?.location as string;
  const linkedWorkOrders = (data?.work_orders || []) as Array<{ id: string; wo_number: string; title: string }>;
  const linkedFaults = (data?.faults || []) as Array<{ id: string; title: string }>;
  const attachments = (data?.attachments as Attachment[]) || [];
  const related_entities = (data?.related_entities as RelatedEntity[]) || [];

  const handleReportFaultSubmit = async (title: string, description: string, severity: string) => {
    const result = await reportFault(data.id as string, { title, description, severity });
    if (result.success) {
      setShowReportFaultModal(false);
      onRefresh?.();
    }
  };

  const handleCreateWOSubmit = async (title: string, description: string, priority: 'routine' | 'important' | 'critical') => {
    const result = await createWorkOrderForEquipment(title, description, priority, 'corrective');
    if (result.success) {
      setShowCreateWOModal(false);
      onRefresh?.();
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <p className="text-xs text-white/40">{equipmentType}</p>
        <h1 className="text-2xl font-semibold text-white">{name}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {manufacturer && <div className="space-y-1"><p className="text-xs text-white/40">Manufacturer</p><p className="text-sm text-white/80">{manufacturer}</p></div>}
        {model && <div className="space-y-1"><p className="text-xs text-white/40">Model</p><p className="text-sm text-white/80">{model}</p></div>}
        {serialNumber && <div className="space-y-1"><p className="text-xs text-white/40">Serial Number</p><p className="text-sm text-white/80 font-mono">{serialNumber}</p></div>}
        {location && <div className="space-y-1"><p className="text-xs text-white/40">Location</p><p className="text-sm text-white/80">{location}</p></div>}
      </div>

      {linkedWorkOrders.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Linked Work Orders</h2>
          <div className="space-y-2">
            {linkedWorkOrders.map((wo) => (
              <button key={wo.id} onClick={() => onNavigate('work_order', wo.id)} className="w-full text-left p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <p className="text-xs text-white/40 font-mono">{wo.wo_number}</p>
                <p className="text-sm text-white/80">{wo.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {linkedFaults.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Linked Faults</h2>
          <div className="space-y-2">
            {linkedFaults.map((fault) => (
              <button key={fault.id} onClick={() => onNavigate('fault', fault.id)} className="w-full text-left p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <p className="text-sm text-white/80">{fault.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}

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

      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button
          onClick={() => setShowReportFaultModal(true)}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
        >
          Report Fault
        </button>
        <button
          onClick={() => setShowCreateWOModal(true)}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
        >
          Create Work Order
        </button>
      </div>

      <ReportFaultModal
        open={showReportFaultModal}
        onClose={() => setShowReportFaultModal(false)}
        onSubmit={handleReportFaultSubmit}
        isLoading={actionsLoading}
      />
      <CreateWorkOrderModal
        open={showCreateWOModal}
        onClose={() => setShowCreateWOModal(false)}
        onSubmit={handleCreateWOSubmit}
        isLoading={actionsLoading}
      />
    </div>
  );
}

function EquipmentDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const equipmentId = params.id as string;
  const token = session?.access_token;

  const { data: equipment, isLoading, error, refetch } = useQuery({
    queryKey: ['equipment-detail', equipmentId],
    queryFn: () => fetchEquipmentDetail(equipmentId, token || ''),
    enabled: !!equipmentId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleRefresh = React.useCallback(() => refetch(), [refetch]);
  const handleNavigate = React.useCallback((entityType: string, entityId: string) => {
    router.push(getEntityRoute(entityType as any, entityId));
  }, [router]);

  const name = (equipment?.name || 'Equipment') as string;
  const equipmentType = (equipment?.equipment_type || '') as string;

  let content: React.ReactNode;
  if (isLoading) content = <LoadingState />;
  else if (error) {
    const msg = error instanceof Error ? error.message : 'An error occurred';
    content = msg.includes('404') ? <NotFoundState /> : <ErrorState message={msg} onRetry={handleRefresh} />;
  }
  else if (!equipment) content = <NotFoundState />;
  else content = <EquipmentContent data={equipment} onNavigate={handleNavigate} onRefresh={handleRefresh} />;

  return (
    <RouteLayout
      pageTitle={name}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back" data-testid="back-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <div>
            <p className="text-xs text-white/40 uppercase tracking-wider">{equipmentType || 'Equipment'}</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">{name}</h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

export default function EquipmentDetailPage() {
  return (
    <React.Suspense fallback={<LoadingState />}>
      <EquipmentDetailPageContent />
    </React.Suspense>
  );
}
