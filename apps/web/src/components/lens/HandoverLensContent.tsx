'use client';

/**
 * HandoverLensContent - Inner content for Handover lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

export interface HandoverLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected': return 'critical';
    case 'pending':
    case 'draft': return 'warning';
    case 'acknowledged':
    case 'completed': return 'success';
    default: return 'neutral';
  }
}

export function HandoverLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: HandoverLensContentProps) {
  // Map data
  const title = (data.title as string) || 'Handover Note';
  const department = (data.department as string) || 'General';
  const status = (data.status as string) || 'pending';
  const from_crew = data.from_crew as string | undefined;
  const to_crew = data.to_crew as string | undefined;
  const handover_time = data.handover_time as string | undefined;
  const content = data.content as string | undefined;
  const priority_items = (data.priority_items as string[]) || [];
  const acknowledged_at = data.acknowledged_at as string | undefined;

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Department', value: department },
    { label: 'From', value: from_crew ?? 'Unknown' },
    { label: 'To', value: to_crew ?? 'Pending' },
    { label: 'Time', value: handover_time ? formatRelativeTime(handover_time) : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Handover" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            subtitle={department}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {status === 'pending' && (
          <div className="mt-4">
            <PrimaryButton onClick={() => console.log('[HandoverLens] Acknowledge:', id)} className="text-[13px] min-h-9 px-4 py-2">Acknowledge Handover</PrimaryButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {priority_items.length > 0 && (
          <div className="mt-6">
            <SectionContainer title="Priority Items" stickyTop={56}>
              <ul className="space-y-2">
                {priority_items.map((item, index) => (
                  <li key={index} className="flex items-start gap-2 typo-body">
                    <span className="text-status-warning">•</span>
                    <span className="text-celeste-text-primary">{item}</span>
                  </li>
                ))}
              </ul>
            </SectionContainer>
          </div>
        )}

        <div className="mt-6">
          <SectionContainer title="Notes" stickyTop={56}>
            <p className="typo-body text-celeste-text-primary whitespace-pre-wrap">
              {content || 'No notes provided.'}
            </p>
          </SectionContainer>
        </div>

        {acknowledged_at && (
          <div className="mt-6">
            <SectionContainer title="Acknowledgement" stickyTop={56}>
              <p className="typo-body text-celeste-text-muted">
                Acknowledged {formatRelativeTime(acknowledged_at)}
                {to_crew && ` by ${to_crew}`}
              </p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}

export default HandoverLensContent;
