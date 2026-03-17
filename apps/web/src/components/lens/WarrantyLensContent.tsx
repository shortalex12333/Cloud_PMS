'use client';

/**
 * WarrantyLensContent - Warranty detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /warranties/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { AttachmentsSection, RelatedEntitiesSection, type Attachment, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Status colour helper
// ---------------------------------------------------------------------------

function mapStatusToColor(status: string, expiryDate?: string): 'critical' | 'warning' | 'success' | 'neutral' {
  if (status === 'expired') return 'critical';
  if (status === 'expiring_soon') return 'warning';
  if (expiryDate) {
    const daysUntilExpiry = Math.floor((new Date(expiryDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry < 0) return 'critical';
    if (daysUntilExpiry < 30) return 'warning';
  }
  return 'success';
}

// ---------------------------------------------------------------------------
// WarrantyLensContent — zero props
// ---------------------------------------------------------------------------

export function WarrantyLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Map entity fields
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const title = ((entity?.title ?? entity?.name ?? payload.title ?? payload.name) as string | undefined) ?? 'Warranty';
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const supplier = (entity?.supplier ?? payload.supplier) as string | undefined;
  const start_date = (entity?.start_date ?? payload.start_date) as string | undefined;
  const expiry_date = (entity?.expiry_date ?? payload.expiry_date) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'active';
  const coverage = (entity?.coverage ?? payload.coverage) as string | undefined;
  const terms = (entity?.terms ?? payload.terms) as string | undefined;
  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const fileClaimAction = getAction('file_warranty_claim');
  const addAttachmentAction = getAction('add_warranty_attachment');

  // ---------------------------------------------------------------------------
  // Derived display values
  // ---------------------------------------------------------------------------
  const statusColor = mapStatusToColor(status, expiry_date);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  let expiryDisplay = '—';
  if (expiry_date) {
    const daysUntilExpiry = Math.floor((new Date(expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (daysUntilExpiry < 0) {
      expiryDisplay = `Expired ${Math.abs(daysUntilExpiry)} days ago`;
    } else if (daysUntilExpiry === 0) {
      expiryDisplay = 'Expires today';
    } else {
      expiryDisplay = `${daysUntilExpiry} days remaining`;
    }
  }

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    {
      label: 'Equipment',
      value: equipment_name ?? 'N/A',
      onClick: equipment_id
        ? () => router.push(getEntityRoute('equipment', equipment_id))
        : undefined,
    },
    { label: 'Supplier', value: supplier ?? 'Unknown' },
    { label: 'Started', value: start_date ? formatRelativeTime(start_date) : '—' },
    { label: 'Expires', value: expiryDisplay, color: statusColor },
  ];

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <>
      {/* No LensHeader — EntityLensPage's RouteLayout owns back/close navigation for this entity */}
      <div className="mt-6">
        <LensTitleBlock
          title={title}
          subtitle={equipment_name}
          status={{ label: statusLabel, color: statusColor }}
        />
      </div>

      <div className="mt-3">
        <VitalSignsRow signs={vitalSigns} />
      </div>

      {/* File Claim action — gated by action availability, not status string */}
      {fileClaimAction !== null && (
        <div className="mt-4">
          <GhostButton
            onClick={() =>
              executeAction('file_warranty_claim', {
                equipment_id: equipment_id ?? '',
                description: 'Warranty claim',
              })
            }
            disabled={fileClaimAction?.disabled ?? isLoading}
            title={fileClaimAction?.disabled_reason ?? undefined}
            className="text-[13px] min-h-9 px-4 py-2"
          >
            File Claim
          </GhostButton>
        </div>
      )}

      <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

      {coverage && (
        <div className="mt-6">
          <SectionContainer title="Coverage" stickyTop={56}>
            <p className="typo-body text-celeste-text-primary whitespace-pre-wrap">{coverage}</p>
          </SectionContainer>
        </div>
      )}

      {terms && (
        <div className="mt-6">
          <SectionContainer title="Terms & Conditions" stickyTop={56}>
            <p className="typo-body text-celeste-text-primary whitespace-pre-wrap">{terms}</p>
          </SectionContainer>
        </div>
      )}

      <div className="mt-6">
        <SectionContainer title="Details" stickyTop={56}>
          <dl className="grid grid-cols-2 gap-4 typo-body">
            {supplier && (
              <>
                <dt className="text-celeste-text-muted">Supplier</dt>
                <dd className="text-celeste-text-primary">{supplier}</dd>
              </>
            )}
            {start_date && (
              <>
                <dt className="text-celeste-text-muted">Start Date</dt>
                <dd className="text-celeste-text-primary">{new Date(start_date).toLocaleDateString()}</dd>
              </>
            )}
            {expiry_date && (
              <>
                <dt className="text-celeste-text-muted">Expiry Date</dt>
                <dd className="text-celeste-text-primary">{new Date(expiry_date).toLocaleDateString()}</dd>
              </>
            )}
          </dl>
        </SectionContainer>
      </div>

      {/* Attachments — shown whenever there are attachments; canAddFile driven by action gate */}
      {attachments.length > 0 && (
        <div className="mt-6">
          <AttachmentsSection
            attachments={attachments}
            onAddFile={() => {}}
            canAddFile={addAttachmentAction !== null}
            stickyTop={56}
          />
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
