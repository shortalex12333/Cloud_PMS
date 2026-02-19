'use client';

/**
 * FaultLensContent - Inner content for Fault lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';

export interface FaultLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapSeverityToColor(severity: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity) {
    case 'critical': return 'critical';
    case 'high': return 'warning';
    case 'medium': return 'neutral';
    case 'low':
    default: return 'neutral';
  }
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'open':
    case 'unresolved': return 'warning';
    case 'resolved':
    case 'closed': return 'success';
    default: return 'neutral';
  }
}

export function FaultLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
}: FaultLensContentProps) {
  // Modal state
  const [showCreateWO, setShowCreateWO] = useState(false);

  // Map data
  const title = (data.title as string) || 'Fault';
  const description = data.description as string | undefined;
  const severity = (data.severity as string) || 'medium';
  const status = (data.status as string) || 'open';
  const equipment_id = data.equipment_id as string | undefined;
  const equipment_name = data.equipment_name as string | undefined;
  const reported_by = data.reported_by as string | undefined;
  const reported_at = data.reported_at as string | undefined;
  const resolved_at = data.resolved_at as string | undefined;

  const severityColor = mapSeverityToColor(severity);
  const statusColor = mapStatusToColor(status);

  const vitalSigns: VitalSign[] = [
    { label: 'Severity', value: severity.charAt(0).toUpperCase() + severity.slice(1), color: severityColor },
    { label: 'Status', value: status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), color: statusColor },
    { label: 'Equipment', value: equipment_name ?? 'Unknown', onClick: equipment_id && onNavigate ? () => onNavigate('equipment', equipment_id) : undefined },
    { label: 'Reporter', value: reported_by ?? 'Unknown' },
    { label: 'Reported', value: reported_at ? formatRelativeTime(reported_at) : '—' },
  ];

  const handleCreateWorkOrder = () => {
    setShowCreateWO(true);
  };

  return (
    <>
      <div className="flex flex-col h-full">
        <LensHeader entityType="Fault" title={title} onBack={onBack} onClose={onClose} />

        <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
          <div className="mt-6">
            <LensTitleBlock
              title={title}
              subtitle={description}
              status={{ label: severity.charAt(0).toUpperCase() + severity.slice(1), color: severityColor }}
            />
          </div>

          <div className="mt-3">
            <VitalSignsRow signs={vitalSigns} />
          </div>

          {status === 'open' && (
            <div className="mt-4">
              <PrimaryButton
                onClick={handleCreateWorkOrder}
                className="text-[13px] min-h-9 px-4 py-2"
              >
                Create Work Order
              </PrimaryButton>
            </div>
          )}

          <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

          <div className="mt-6">
            <SectionContainer title="Description" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">
                {description || 'No description provided.'}
              </p>
            </SectionContainer>
          </div>

          {resolved_at && (
            <div className="mt-6">
              <SectionContainer title="Resolution" stickyTop={56}>
                <p className="typo-body text-celeste-text-muted">
                  Resolved {formatRelativeTime(resolved_at)}
                </p>
              </SectionContainer>
            </div>
          )}
        </main>
      </div>

      {/* Create Work Order Modal */}
      <CreateWorkOrderModal
        open={showCreateWO}
        onOpenChange={setShowCreateWO}
        context={{
          equipment_id: equipment_id,
          equipment_name: equipment_name,
          fault_id: id,
          fault_description: description,
          suggested_title: `Fix: ${title}`,
        }}
        onSuccess={(workOrderId) => {
          console.log('[FaultLens] Work order created:', workOrderId);
        }}
      />
    </>
  );
}

export default FaultLensContent;
