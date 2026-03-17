'use client';

/**
 * CertificateLensContent - Certificate detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /certificates/{id}.
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
import { PrimaryButton } from '@/components/ui/PrimaryButton';
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
// CertificateLensContent — zero props
// ---------------------------------------------------------------------------

export function CertificateLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Map entity fields
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const name = ((entity?.name ?? entity?.title ?? payload.name) as string | undefined) ?? 'Certificate';
  const certificate_type = ((entity?.certificate_type ?? payload.certificate_type) as string | undefined) ?? 'General';
  const issuing_authority = (entity?.issuing_authority ?? payload.issuing_authority) as string | undefined;
  const issue_date = (entity?.issue_date ?? payload.issue_date) as string | undefined;
  const expiry_date = (entity?.expiry_date ?? payload.expiry_date) as string | undefined;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'valid';
  const certificate_number = (entity?.certificate_number ?? payload.certificate_number) as string | undefined;
  const notes = (entity?.notes ?? payload.notes) as string | undefined;
  const document_url = (entity?.document_url ?? payload.document_url) as string | undefined;
  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  // ---------------------------------------------------------------------------
  // Action gates — ALL stored as named consts, never inlined in JSX
  // ---------------------------------------------------------------------------
  const renewAction = getAction('renew_certificate');
  const uploadDocAction = getAction('link_document_to_certificate');
  const setReminderAction = getAction('certificate.set_reminder');

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
      expiryDisplay = `${daysUntilExpiry} days`;
    }
  }

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Type', value: certificate_type },
    { label: 'Authority', value: issuing_authority ?? 'Unknown' },
    { label: 'Issued', value: issue_date ? formatRelativeTime(issue_date) : '—' },
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
          title={name}
          subtitle={certificate_number ? `#${certificate_number}` : undefined}
          status={{ label: statusLabel, color: statusColor }}
        />
      </div>

      <div className="mt-3">
        <VitalSignsRow signs={vitalSigns} />
      </div>

      {/* Expiry warning banners */}
      {status === 'expiring_soon' && expiry_date && (
        <div className="mt-4 p-4 bg-status-warning/10 border border-status-warning/20 rounded-lg">
          <div className="flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-warning flex-shrink-0 mt-0.5">
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-status-warning">Certificate Expiring Soon</p>
              <p className="text-xs text-celeste-text-muted mt-1">
                This certificate will expire on {new Date(expiry_date).toLocaleDateString()}. Please arrange for renewal.
              </p>
            </div>
          </div>
        </div>
      )}

      {status === 'expired' && expiry_date && (
        <div className="mt-4 p-4 bg-status-critical/10 border border-status-critical/20 rounded-lg">
          <div className="flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-critical flex-shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <div>
              <p className="text-sm font-medium text-status-critical">Certificate Expired</p>
              <p className="text-xs text-celeste-text-muted mt-1">
                This certificate expired on {new Date(expiry_date).toLocaleDateString()}. Immediate action is required.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {renewAction !== null && (
        <div className="mt-4">
          <PrimaryButton
            onClick={() => executeAction('renew_certificate', { status: 'renewal_pending' })}
            disabled={renewAction?.disabled ?? isLoading}
            title={renewAction?.disabled_reason ?? undefined}
            className="text-[13px] min-h-9 px-4 py-2"
          >
            Renew Certificate
          </PrimaryButton>
        </div>
      )}

      {document_url && (
        <div className={renewAction !== null ? 'mt-2' : 'mt-4'}>
          {/* document_url is a browser navigation link, not a server action — field-driven by design */}
          <GhostButton
            onClick={() => window.open(document_url, '_blank')}
            className="text-[13px] min-h-9 px-4 py-2"
          >
            View Certificate Document
          </GhostButton>
        </div>
      )}

      {uploadDocAction !== null && (
        <div className="mt-2">
          <GhostButton
            onClick={() => executeAction('link_document_to_certificate', {})}
            disabled={uploadDocAction?.disabled ?? isLoading}
            title={uploadDocAction?.disabled_reason ?? undefined}
            className="text-[13px] min-h-9 px-4 py-2"
          >
            Upload Document
          </GhostButton>
        </div>
      )}

      {setReminderAction !== null && (
        <div className="mt-2">
          <GhostButton
            onClick={() => executeAction('certificate.set_reminder', { expiry_date, reminder_days_before: 30 })}
            disabled={setReminderAction?.disabled ?? isLoading}
            title={setReminderAction?.disabled_reason ?? undefined}
            className="text-[13px] min-h-9 px-4 py-2"
          >
            Set Reminder
          </GhostButton>
        </div>
      )}

      <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

      {/* Details */}
      <div className="mt-6">
        <SectionContainer title="Details" stickyTop={56}>
          <dl className="grid grid-cols-2 gap-4 typo-body">
            {certificate_number && (
              <>
                <dt className="text-celeste-text-muted">Certificate Number</dt>
                <dd className="text-celeste-text-primary">{certificate_number}</dd>
              </>
            )}
            <dt className="text-celeste-text-muted">Type</dt>
            <dd className="text-celeste-text-primary">{certificate_type}</dd>
            {issuing_authority && (
              <>
                <dt className="text-celeste-text-muted">Issuing Authority</dt>
                <dd className="text-celeste-text-primary">{issuing_authority}</dd>
              </>
            )}
            {issue_date && (
              <>
                <dt className="text-celeste-text-muted">Issue Date</dt>
                <dd className="text-celeste-text-primary">{new Date(issue_date).toLocaleDateString()}</dd>
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

      {/* Notes */}
      {notes && (
        <div className="mt-6">
          <SectionContainer title="Notes" stickyTop={56}>
            <p className="typo-body text-celeste-text-primary">{notes}</p>
          </SectionContainer>
        </div>
      )}

      {/* Attachments */}
      {attachments.length > 0 && (
        <div className="mt-6">
          <AttachmentsSection
            attachments={attachments}
            onAddFile={() => {}}
            canAddFile={uploadDocAction !== null}
            stickyTop={56}
          />
        </div>
      )}

      {/* Related entities */}
      {related_entities.length > 0 && (
        <div className="mt-6">
          <RelatedEntitiesSection entities={related_entities} onNavigate={handleNavigate} stickyTop={56} />
        </div>
      )}
    </>
  );
}
