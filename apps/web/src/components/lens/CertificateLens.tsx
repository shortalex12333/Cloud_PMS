'use client';

/**
 * CertificateLens - Full-screen entity lens for vessel and crew certificates.
 *
 * Per UI_SPEC.md and the WorkOrderLens reference pattern:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - LensTitleBlock: certificate name + status pill
 * - VitalSignsRow: 5 indicators (status, type, expiry, authority, linked entity)
 * - Section containers: Details, Linked Documents, Renewal History
 * - useCertificateActions hook for all 6 actions
 * - Role-based button visibility (hide, not disable)
 * - Glass transition via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * Supports both vessel and crew certificates via `certificateType` prop.
 *
 * FE-02-04: Certificate Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { useCertificateActions, useCertificatePermissions } from '@/hooks/useCertificateActions';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface CertificateDocument {
  id: string;
  name: string;
  file_type?: string;
  file_size?: number;
  url?: string;
  created_at: string;
}

export interface RenewalEntry {
  id: string;
  certificate_number?: string;
  issue_date: string;
  expiry_date: string;
  superseded_at: string;
  superseded_by?: string;
  notes?: string;
}

export interface CertificateData {
  id: string;
  /** Certificate name e.g. "STCW Basic Safety Training" */
  certificate_name: string;
  /** Certificate type/category name for display */
  certificate_type_name?: string;
  /** Human-readable certificate number — NEVER show raw UUID */
  certificate_number?: string;
  /** Status enum: valid | expiring_soon | expired | superseded */
  status: 'valid' | 'expiring_soon' | 'expired' | 'superseded';
  /** Issue date ISO string */
  issue_date: string;
  /** Expiry date ISO string */
  expiry_date: string;
  /** Issuing authority name */
  issuing_authority: string;
  /** Notes / remarks */
  notes?: string;
  /** For crew certificates: crew member ID */
  crew_member_id?: string;
  /** For crew certificates: crew member display name */
  crew_member_name?: string;
  /** For vessel certificates: vessel / yacht name */
  vessel_name?: string;
  /** Days until expiry (negative = already expired) */
  days_until_expiry?: number;
  /** Linked documents (scanned cert, supporting docs) */
  documents?: CertificateDocument[];
  /** Renewal / revision history */
  renewal_history?: RenewalEntry[];
}

export interface CertificateLensProps {
  /** The certificate data to render */
  certificate: CertificateData;
  /** Whether this is a vessel or crew certificate — drives entity link display */
  certificateType: 'vessel' | 'crew';
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Colour mapping helpers (domain-specific, local to this lens)
// ---------------------------------------------------------------------------

/**
 * Map certificate status to StatusPill color level.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'expired':
      return 'critical';
    case 'expiring_soon':
      return 'warning';
    case 'valid':
      return 'success';
    case 'superseded':
    default:
      return 'neutral';
  }
}

/**
 * Format status enum to human-readable label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    valid: 'Valid',
    expiring_soon: 'Expiring Soon',
    expired: 'Expired',
    superseded: 'Superseded',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Compute expiry display text and color for the VitalSignsRow.
 *
 * - Expired → "Expired 5 days ago" in critical (red)
 * - Expiring within 30 days → "Expires Jan 23, 2026" in warning (amber)
 * - Valid → "Expires Jan 23, 2026" in success (green)
 */
function getExpiryVitalSign(
  expiryDate: string,
  daysUntilExpiry?: number
): { value: string; color: 'critical' | 'warning' | 'success' | 'neutral' } {
  const expiry = new Date(expiryDate);
  const formattedDate = expiry.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  if (daysUntilExpiry === undefined) {
    return { value: `Expires ${formattedDate}`, color: 'neutral' };
  }

  if (daysUntilExpiry < 0) {
    const daysAgo = Math.abs(daysUntilExpiry);
    return {
      value: `Expired ${daysAgo} day${daysAgo === 1 ? '' : 's'} ago`,
      color: 'critical',
    };
  }

  if (daysUntilExpiry <= 30) {
    return {
      value: `Expires ${formattedDate}`,
      color: 'warning',
    };
  }

  return {
    value: `Expires ${formattedDate}`,
    color: 'success',
  };
}

/**
 * Format a date ISO string for display: "Jan 23, 2026"
 */
function formatDisplayDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Section: Details
// ---------------------------------------------------------------------------

interface DetailsSectionProps {
  certificate: CertificateData;
  stickyTop?: number;
}

function DetailsSection({ certificate, stickyTop = 56 }: DetailsSectionProps) {
  const rows: Array<{ label: string; value: string }> = [
    ...(certificate.certificate_number
      ? [{ label: 'Certificate No.', value: certificate.certificate_number }]
      : []),
    { label: 'Issue Date', value: formatDisplayDate(certificate.issue_date) },
    { label: 'Expiry Date', value: formatDisplayDate(certificate.expiry_date) },
    { label: 'Issuing Authority', value: certificate.issuing_authority },
    ...(certificate.notes ? [{ label: 'Notes', value: certificate.notes }] : []),
  ];

  return (
    <SectionContainer title="Details" stickyTop={stickyTop}>
      {rows.length === 0 ? (
        <p className="text-[14px] text-txt-secondary py-4">No details available.</p>
      ) : (
        <dl className="flex flex-col gap-3 py-2">
          {rows.map(({ label, value }) => (
            <div key={label} className="flex flex-col gap-0.5">
              <dt className="text-[12px] font-medium uppercase tracking-wider text-txt-tertiary">
                {label}
              </dt>
              <dd className="text-[14px] text-txt-primary">{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </SectionContainer>
  );
}

// ---------------------------------------------------------------------------
// Section: Linked Documents
// ---------------------------------------------------------------------------

interface LinkedDocumentsSectionProps {
  documents: CertificateDocument[];
  onLinkDocument?: () => void;
  canLinkDocument?: boolean;
  stickyTop?: number;
}

function LinkedDocumentsSection({
  documents,
  onLinkDocument,
  canLinkDocument = false,
  stickyTop = 56,
}: LinkedDocumentsSectionProps) {
  const countBadge = documents.length > 0 ? documents.length : undefined;

  return (
    <SectionContainer
      title="Linked Documents"
      count={countBadge}
      action={
        canLinkDocument && onLinkDocument
          ? { label: 'Link Document', onClick: onLinkDocument }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-10 h-10 rounded-[var(--radius-md)] bg-surface-secondary flex items-center justify-center mb-3">
            {/* File icon */}
            <svg
              className="w-5 h-5 text-txt-tertiary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <p className="text-[14px] font-medium text-txt-secondary mb-1">No documents linked</p>
          <p className="text-[13px] text-txt-tertiary">
            Link the scanned certificate and supporting documents.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2 py-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5',
                'bg-surface-secondary rounded-[var(--radius-sm)]',
                'border border-surface-border'
              )}
            >
              {/* Doc type icon */}
              <div className="w-9 h-9 rounded-[var(--radius-sm)] bg-surface-primary flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-4 h-4 text-txt-tertiary"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium text-txt-primary truncate">{doc.name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {doc.file_type && (
                    <span className="text-[12px] text-txt-tertiary uppercase">{doc.file_type}</span>
                  )}
                  {doc.file_type && (
                    <span className="text-txt-tertiary text-[12px]">&middot;</span>
                  )}
                  <span className="text-[12px] text-txt-tertiary">
                    {formatDisplayDate(doc.created_at)}
                  </span>
                </div>
              </div>

              {/* Chevron */}
              <svg
                className="w-4 h-4 text-txt-tertiary flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

// ---------------------------------------------------------------------------
// Section: Renewal History
// ---------------------------------------------------------------------------

interface RenewalHistorySectionProps {
  history: RenewalEntry[];
  stickyTop?: number;
}

function RenewalHistorySection({ history, stickyTop = 56 }: RenewalHistorySectionProps) {
  const countBadge = history.length > 0 ? history.length : undefined;

  return (
    <SectionContainer title="Renewal History" count={countBadge} stickyTop={stickyTop}>
      {history.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-10 h-10 rounded-[var(--radius-md)] bg-surface-secondary flex items-center justify-center mb-3">
            {/* Refresh icon */}
            <svg
              className="w-5 h-5 text-txt-tertiary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </div>
          <p className="text-[14px] font-medium text-txt-secondary mb-1">No renewal history</p>
          <p className="text-[13px] text-txt-tertiary">
            Previous certificate versions will appear here when superseded.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 py-2">
          {history.map((entry, index) => (
            <div
              key={entry.id}
              className={cn(
                'flex flex-col gap-1.5 px-3 py-3',
                'bg-surface-secondary rounded-[var(--radius-sm)]',
                'border border-surface-border'
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[13px] font-medium text-txt-primary">
                  {entry.certificate_number ? `No. ${entry.certificate_number}` : `Version ${history.length - index}`}
                </span>
                <span className="text-[12px] text-txt-tertiary">
                  Superseded {formatDisplayDate(entry.superseded_at)}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-[12px] text-txt-tertiary">Issued: </span>
                  <span className="text-[12px] text-txt-secondary">{formatDisplayDate(entry.issue_date)}</span>
                </div>
                <div>
                  <span className="text-[12px] text-txt-tertiary">Expired: </span>
                  <span className="text-[12px] text-txt-secondary">{formatDisplayDate(entry.expiry_date)}</span>
                </div>
              </div>
              {entry.notes && (
                <p className="text-[13px] text-txt-secondary mt-0.5 line-clamp-2">{entry.notes}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

// ---------------------------------------------------------------------------
// CertificateLens component
// ---------------------------------------------------------------------------

/**
 * CertificateLens — Full-screen entity lens for vessel and crew certificates.
 *
 * Usage:
 * ```tsx
 * <CertificateLens
 *   certificate={data}
 *   certificateType="vessel"
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const CertificateLens = React.forwardRef<HTMLDivElement, CertificateLensProps>(
  (
    { certificate, certificateType, onBack, onClose, className, onRefresh },
    ref
  ) => {
    // Glass transition: lens mounts as closed then opens on first render
    const [isOpen, setIsOpen] = React.useState(false);

    // Actions and permissions
    const actions = useCertificateActions(certificate.id);
    const perms = useCertificatePermissions();

    useEffect(() => {
      // Trigger glass enter animation on mount
      setIsOpen(true);
    }, []);

    // Derived display values
    const statusColor = mapStatusToColor(certificate.status);
    const statusLabel = formatStatusLabel(certificate.status);

    // Expiry vital sign with warning/critical color
    const expiryVitalSign = getExpiryVitalSign(
      certificate.expiry_date,
      certificate.days_until_expiry
    );

    // Linked entity display — vessel name or crew member name
    const linkedEntityLabel = certificateType === 'crew'
      ? (certificate.crew_member_name ?? 'Unknown Crew Member')
      : (certificate.vessel_name ?? 'Vessel');

    const linkedEntityHref = certificateType === 'crew' && certificate.crew_member_id
      ? `/crew/${certificate.crew_member_id}`
      : undefined;

    // Build the 5 vital signs per plan spec
    const certVitalSigns: VitalSign[] = [
      {
        label: 'Status',
        value: statusLabel,
        color: statusColor,
      },
      {
        label: 'Type',
        value: certificate.certificate_type_name ?? (certificateType === 'crew' ? 'Crew Certificate' : 'Vessel Certificate'),
      },
      {
        label: 'Expiry',
        value: expiryVitalSign.value,
        color: expiryVitalSign.color,
      },
      {
        label: 'Authority',
        value: certificate.issuing_authority,
      },
      {
        label: certificateType === 'crew' ? 'Crew Member' : 'Vessel',
        value: linkedEntityLabel,
        href: linkedEntityHref,
      },
    ];

    // Section data (safe fallbacks)
    const documents = certificate.documents ?? [];
    const renewalHistory = certificate.renewal_history ?? [];

    // Handle close with exit animation
    const handleClose = React.useCallback(() => {
      setIsOpen(false);
      if (onClose) {
        setTimeout(onClose, 210); // Wait for exit animation (200ms + buffer)
      }
    }, [onClose]);

    const handleBack = React.useCallback(() => {
      if (onBack) {
        onBack();
      } else {
        handleClose();
      }
    }, [onBack, handleClose]);

    const handleLinkDocument = React.useCallback(async () => {
      const result = await actions.linkDocument('');
      if (result.success) onRefresh?.();
    }, [actions, onRefresh]);

    const handleSupersede = React.useCallback(async () => {
      const result = await actions.supersedeCertificate({});
      if (result.success) onRefresh?.();
    }, [actions, onRefresh]);

    return (
      <LensContainer
        ref={ref}
        isOpen={isOpen}
        onClose={handleClose}
        className={className}
      >
        {/* Fixed navigation header — 56px, at z-header */}
        <LensHeader
          entityType={certificateType === 'crew' ? 'Crew Certificate' : 'Vessel Certificate'}
          title={certificate.certificate_name}
          onBack={handleBack}
          onClose={handleClose}
        />

        {/* Main content — padded top to clear fixed header (56px = h-14) */}
        <main
          className={cn(
            // Clear the fixed header
            'pt-14',
            // Lens body padding: 40px desktop, responsive
            'px-10 md:px-6 sm:px-4',
            // Max content width: 800px centered per spec
            'max-w-[800px] mx-auto',
            // Bottom breathing room
            'pb-12'
          )}
        >
          {/* -------------------------------------------------------------------
              Title block: certificate name + status pill
              Gap from header: 24px (--space-6)
              ------------------------------------------------------------------- */}
          <div className="mt-6">
            <LensTitleBlock
              title={certificate.certificate_name}
              subtitle={certificate.certificate_number ? `Certificate No. ${certificate.certificate_number}` : undefined}
              status={{
                label: statusLabel,
                color: statusColor,
              }}
            />
          </div>

          {/* -------------------------------------------------------------------
              Vital Signs Row — 5 indicators
              Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
              ------------------------------------------------------------------- */}
          <div className="mt-3">
            <VitalSignsRow signs={certVitalSigns} />
          </div>

          {/* -------------------------------------------------------------------
              Header action buttons
              Visible only if user has relevant permissions — hidden, not disabled
              ------------------------------------------------------------------- */}
          {(perms.canCreate || perms.canUpdate || perms.canSupersede) && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              {perms.canCreate && (
                <PrimaryButton
                  onClick={() => actions.createCertificate({})}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Create Certificate
                </PrimaryButton>
              )}
              {perms.canUpdate && (
                <GhostButton
                  onClick={() => actions.updateCertificate({})}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2"
                >
                  Update
                </GhostButton>
              )}
              {perms.canSupersede && (
                <GhostButton
                  onClick={handleSupersede}
                  disabled={actions.isLoading}
                  className="text-[13px] min-h-[36px] px-4 py-2 text-status-warning hover:text-status-warning"
                >
                  Supersede
                </GhostButton>
              )}
            </div>
          )}

          {/* Section divider */}
          <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

          {/* -------------------------------------------------------------------
              Details Section
              stickyTop={56}: sticky headers clear the 56px fixed LensHeader
              ------------------------------------------------------------------- */}
          <div className="mt-6">
            <DetailsSection certificate={certificate} stickyTop={56} />
          </div>

          {/* -------------------------------------------------------------------
              Linked Documents Section
              ------------------------------------------------------------------- */}
          <div className="mt-6">
            <LinkedDocumentsSection
              documents={documents}
              onLinkDocument={handleLinkDocument}
              canLinkDocument={perms.canLinkDocument}
              stickyTop={56}
            />
          </div>

          {/* -------------------------------------------------------------------
              Renewal History Section
              ------------------------------------------------------------------- */}
          <div className="mt-6">
            <RenewalHistorySection history={renewalHistory} stickyTop={56} />
          </div>
        </main>
      </LensContainer>
    );
  }
);

CertificateLens.displayName = 'CertificateLens';

export default CertificateLens;
