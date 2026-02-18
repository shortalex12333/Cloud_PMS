'use client';

/**
 * HoursOfRestLensContent - Inner content for Hours of Rest lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';

export interface HoursOfRestLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapComplianceToColor(compliant: boolean): 'critical' | 'warning' | 'success' | 'neutral' {
  return compliant ? 'success' : 'critical';
}

export function HoursOfRestLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: HoursOfRestLensContentProps) {
  // Map data
  const crew_name = (data.crew_name as string) || 'Crew Member';
  const date = data.date as string | undefined;
  const total_rest_hours = (data.total_rest_hours as number) ?? 0;
  const total_work_hours = (data.total_work_hours as number) ?? 0;
  const is_compliant = (data.is_compliant as boolean) ?? true;
  const status = (data.status as string) || 'draft';
  const verified_by = data.verified_by as string | undefined;
  const verified_at = data.verified_at as string | undefined;

  // Rest periods from child table
  const rest_periods = (data.rest_periods as Array<{
    id: string;
    start_time: string;
    end_time: string;
    duration_hours: number;
  }>) || [];

  const complianceColor = mapComplianceToColor(is_compliant);
  const complianceLabel = is_compliant ? 'Compliant' : 'Non-Compliant';

  const vitalSigns: VitalSign[] = [
    { label: 'Compliance', value: complianceLabel, color: complianceColor },
    { label: 'Rest Hours', value: `${total_rest_hours.toFixed(1)}h` },
    { label: 'Work Hours', value: `${total_work_hours.toFixed(1)}h` },
    { label: 'Crew', value: crew_name },
    { label: 'Date', value: date ? new Date(date).toLocaleDateString() : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Hours of Rest" title={crew_name} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={crew_name}
            subtitle={date ? `Record for ${new Date(date).toLocaleDateString()}` : undefined}
            status={{ label: complianceLabel, color: complianceColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {status !== 'verified' && (
          <div className="mt-4 flex items-center gap-2">
            <PrimaryButton onClick={() => console.log('[HoursOfRestLens] Verify:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Verify Record</PrimaryButton>
            <GhostButton onClick={() => console.log('[HoursOfRestLens] Add rest period:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Add Rest Period</GhostButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title={`Rest Periods (${rest_periods.length})`} stickyTop={56}>
            {rest_periods.length === 0 ? (
              <p className="text-sm text-txt-tertiary">No rest periods recorded.</p>
            ) : (
              <ul className="space-y-3">
                {rest_periods.map((period, index) => (
                  <li key={period.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                    <span className="text-sm text-txt-primary">
                      {new Date(period.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(period.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className="text-sm text-txt-tertiary">
                      {period.duration_hours.toFixed(1)} hours
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </SectionContainer>
        </div>

        {verified_at && (
          <div className="mt-6">
            <SectionContainer title="Verification" stickyTop={56}>
              <p className="text-sm text-txt-tertiary">
                Verified {formatRelativeTime(verified_at)}
                {verified_by && ` by ${verified_by}`}
              </p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}

export default HoursOfRestLensContent;
