'use client';

/**
 * HoursOfRestLensContent - Hours of Rest detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /hours-of-rest/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 *
 * create_monthly_signoff is a compliance cluster action and is rendered
 * automatically in EntityLensPage's shell action bar. Do NOT render it here.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { RelatedEntitiesSection, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Compliance colour helper
// ---------------------------------------------------------------------------

function mapComplianceToColor(compliant: boolean): 'critical' | 'warning' | 'success' | 'neutral' {
  return compliant ? 'success' : 'critical';
}

// ---------------------------------------------------------------------------
// HoursOfRestLensContent — zero props
// ---------------------------------------------------------------------------

export function HoursOfRestLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Named action const — null means server says not available for this role/state
  const upsertAction = getAction('upsert_hours_of_rest');

  // Map entity fields
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const crew_name = ((entity?.crew_name ?? payload.crew_name) as string | undefined) ?? 'Crew Member';
  const date = (entity?.date ?? payload.date) as string | undefined;
  const total_rest_hours = ((entity?.total_rest_hours ?? payload.total_rest_hours) as number | undefined) ?? 0;
  const total_work_hours = ((entity?.total_work_hours ?? payload.total_work_hours) as number | undefined) ?? 0;
  const is_compliant = ((entity?.is_compliant ?? payload.is_compliant) as boolean | undefined) ?? true;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const verified_by = (entity?.verified_by ?? payload.verified_by) as string | undefined;
  const verified_at = (entity?.verified_at ?? payload.verified_at) as string | undefined;
  const rest_periods = ((entity?.rest_periods ?? payload.rest_periods) as Array<{
    id?: string;
    start_time: string;
    end_time: string;
    duration_hours: number;
  }> | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  // Derived display values
  const complianceColor = mapComplianceToColor(is_compliant);
  const complianceLabel = is_compliant ? 'Compliant' : 'Non-Compliant';

  const vitalSigns: VitalSign[] = [
    { label: 'Compliance', value: complianceLabel, color: complianceColor },
    { label: 'Rest Hours', value: `${total_rest_hours.toFixed(1)}h` },
    { label: 'Work Hours', value: `${total_work_hours.toFixed(1)}h` },
    { label: 'Crew', value: crew_name },
    { label: 'Date', value: date ? new Date(date).toLocaleDateString() : '—' },
  ];

  void status; // status retained for future gate use; unused by display logic

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <>
      {/* No LensHeader — EntityLensPage's RouteLayout owns back/close navigation */}
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

      {upsertAction !== null && (
        <div className="mt-4 flex items-center gap-2">
          <GhostButton
            onClick={() => executeAction('upsert_hours_of_rest', {
              date: date ?? new Date().toISOString().split('T')[0],
              rest_periods: rest_periods.map(p => ({ hours: p.duration_hours })),
            })}
            disabled={upsertAction?.disabled ?? isLoading}
            title={upsertAction?.disabled_reason ?? undefined}
          >
            Update Record
          </GhostButton>
          <GhostButton
            onClick={() => executeAction('upsert_hours_of_rest', {
              date: date ?? new Date().toISOString().split('T')[0],
              rest_periods: [...rest_periods.map(p => ({ hours: p.duration_hours })), { hours: 0 }],
            })}
            disabled={upsertAction?.disabled ?? isLoading}
            title={upsertAction?.disabled_reason ?? undefined}
          >
            Add Rest Period
          </GhostButton>
        </div>
      )}

      <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

      <div className="mt-6">
        <SectionContainer title={`Rest Periods (${rest_periods.length})`} stickyTop={56}>
          {rest_periods.length === 0 ? (
            <p className="typo-body text-celeste-text-muted">No rest periods recorded.</p>
          ) : (
            <ul className="space-y-3">
              {rest_periods.map((period, index) => (
                <li key={period.id ?? index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                  <span className="typo-body text-celeste-text-primary">
                    {new Date(period.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(period.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="typo-body text-celeste-text-muted">
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
            <p className="typo-body text-celeste-text-muted">
              Verified {formatRelativeTime(verified_at)}
              {verified_by && ` by ${verified_by}`}
            </p>
          </SectionContainer>
        </div>
      )}

      {related_entities.length > 0 && (
        <div className="mt-6">
          <RelatedEntitiesSection entities={related_entities} onNavigate={handleNavigate} stickyTop={56} />
        </div>
      )}
    </>
  );
}
