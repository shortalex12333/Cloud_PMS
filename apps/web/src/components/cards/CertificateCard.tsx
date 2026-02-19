/**
 * CertificateCard Component
 *
 * Full-screen entity view for vessel and crew certificates:
 * - Certificate details (type, dates, authority)
 * - Expiry status indicator with countdown
 * - Linked documents section
 * - Audit history
 * - Tokenized styling (no hardcoded values)
 */

'use client';

import {
  FileCheck,
  Calendar,
  Building2,
  User,
  AlertTriangle,
  FileText,
  History,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Archive,
  RefreshCw,
  Link,
} from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

interface CertificateDocument {
  id: string;
  name: string;
  file_type?: string;
  created_at: string;
}

interface CertificateAuditEntry {
  id: string;
  action: string;
  old_values?: Record<string, unknown>;
  new_values?: Record<string, unknown>;
  user_id?: string;
  created_at: string;
}

interface CertificateCardProps {
  certificate: {
    id: string;
    certificate_type: 'vessel' | 'crew';
    certificate_name: string;
    certificate_number?: string;
    issue_date: string;
    expiry_date: string;
    issuing_authority: string;
    status: 'valid' | 'expiring_soon' | 'expired' | 'superseded';
    // For crew certificates
    crew_member_id?: string;
    crew_member_name?: string;
    // Enriched data
    documents?: CertificateDocument[];
    audit_history?: CertificateAuditEntry[];
    documents_count?: number;
    days_until_expiry?: number;
  };
  actions?: MicroAction[];
}

// ============================================================================
// EMPTY STATE CTA COMPONENT
// ============================================================================

interface EmptyStateCTAProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function EmptyStateCTA({ icon, title, description }: EmptyStateCTAProps) {
  return (
    <div className="flex flex-col items-center justify-center py-ds-6 px-ds-4 text-center">
      <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-ds-3">
        {icon}
      </div>
      <p className="text-txt-primary font-medium mb-ds-1">
        {title}
      </p>
      <p className="text-txt-tertiary typo-meta">
        {description}
      </p>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function CertificateCard({ certificate, actions = [] }: CertificateCardProps) {
  // Get status styling
  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'valid':
        return {
          pillClass: 'status-pill status-pill-success',
          icon: <CheckCircle2 className="h-5 w-5" />,
          label: 'Valid',
        };
      case 'expiring_soon':
        return {
          pillClass: 'status-pill status-pill-warning',
          icon: <AlertTriangle className="h-5 w-5" />,
          label: 'Expiring Soon',
        };
      case 'expired':
        return {
          pillClass: 'status-pill status-pill-critical',
          icon: <XCircle className="h-5 w-5" />,
          label: 'Expired',
        };
      case 'superseded':
        return {
          pillClass: 'status-pill status-pill-neutral',
          icon: <Archive className="h-5 w-5" />,
          label: 'Superseded',
        };
      default:
        return {
          pillClass: 'status-pill status-pill-neutral',
          icon: <FileCheck className="h-5 w-5" />,
          label: 'Unknown',
        };
    }
  };

  // Get certificate type styling
  const getTypeStyles = (type: string) => {
    switch (type) {
      case 'vessel':
        return { bg: 'bg-brand-muted', text: 'text-brand-interactive', label: 'Vessel' };
      case 'crew':
        return { bg: 'bg-txt-secondary/10', text: 'text-txt-secondary', label: 'Crew' };
      default:
        return { bg: 'bg-txt-tertiary/10', text: 'text-txt-tertiary', label: type };
    }
  };

  // Get expiry countdown styling
  const getExpiryCountdownStyles = (daysUntilExpiry: number | undefined) => {
    if (daysUntilExpiry === undefined) return null;

    if (daysUntilExpiry < 0) {
      return {
        color: 'text-status-critical',
        bg: 'bg-status-critical-bg',
        text: `Expired ${Math.abs(daysUntilExpiry)} days ago`,
      };
    } else if (daysUntilExpiry <= 30) {
      return {
        color: 'text-status-critical',
        bg: 'bg-status-critical-bg',
        text: `${daysUntilExpiry} days remaining`,
      };
    } else if (daysUntilExpiry <= 90) {
      return {
        color: 'text-status-warning',
        bg: 'bg-status-warning-bg',
        text: `${daysUntilExpiry} days remaining`,
      };
    } else {
      return {
        color: 'text-status-success',
        bg: 'bg-status-success-bg',
        text: `${daysUntilExpiry} days remaining`,
      };
    }
  };

  const status = getStatusStyles(certificate.status);
  const certType = getTypeStyles(certificate.certificate_type);
  const expiryCountdown = getExpiryCountdownStyles(certificate.days_until_expiry);

  const documents = certificate.documents || [];
  const auditHistory = certificate.audit_history || [];

  const actionContext = {
    certificate_id: certificate.id,
    certificate_type: certificate.certificate_type,
    crew_member_id: certificate.crew_member_id,
  };

  return (
    <div className="flex flex-col gap-ds-6">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        {/* Status & Type Row */}
        <div className="flex items-center gap-ds-2 mb-ds-4">
          <span className={status.pillClass}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center px-ds-3 py-ds-1 rounded-sm typo-meta font-medium',
            certType.bg, certType.text
          )}>
            {certType.label}
          </span>
        </div>

        {/* Certificate Name */}
        <h1 className="text-2xl font-semibold text-txt-primary mb-ds-2">
          {certificate.certificate_name}
        </h1>

        {/* Certificate Number */}
        {certificate.certificate_number && (
          <p className="text-txt-secondary mb-ds-4">
            Certificate No: {certificate.certificate_number}
          </p>
        )}

        {/* Expiry Countdown Indicator */}
        {expiryCountdown && (
          <div className={cn(
            'inline-flex items-center gap-ds-2 px-ds-3 py-ds-2 rounded-sm mb-ds-4',
            expiryCountdown.bg
          )}>
            <Clock className={cn('h-4 w-4', expiryCountdown.color)} />
            <span className={cn('typo-meta font-medium', expiryCountdown.color)}>
              {expiryCountdown.text}
            </span>
          </div>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-ds-4 pt-ds-4 border-t border-surface-border">
          {/* Certificate Type */}
          <div>
            <p className="text-txt-tertiary typo-meta uppercase tracking-wide mb-1">Type</p>
            <div className="flex items-center gap-ds-1">
              <FileCheck className="h-4 w-4 text-txt-secondary" />
              <span className="text-txt-primary capitalize">{certificate.certificate_type}</span>
            </div>
          </div>

          {/* Issue Date */}
          <div>
            <p className="text-txt-tertiary typo-meta uppercase tracking-wide mb-1">Issue Date</p>
            <div className="flex items-center gap-ds-1">
              <Calendar className="h-4 w-4 text-txt-secondary" />
              <span className="text-txt-primary">{formatDate(certificate.issue_date)}</span>
            </div>
          </div>

          {/* Expiry Date */}
          <div>
            <p className="text-txt-tertiary typo-meta uppercase tracking-wide mb-1">Expiry Date</p>
            <div className="flex items-center gap-ds-1">
              <Calendar className="h-4 w-4 text-txt-secondary" />
              <span className={cn(
                certificate.status === 'expired' ? 'text-status-critical' :
                certificate.status === 'expiring_soon' ? 'text-status-warning' :
                'text-txt-primary'
              )}>
                {formatDate(certificate.expiry_date)}
              </span>
            </div>
          </div>

          {/* Issuing Authority */}
          <div>
            <p className="text-txt-tertiary typo-meta uppercase tracking-wide mb-1">Issuing Authority</p>
            <div className="flex items-center gap-ds-1">
              <Building2 className="h-4 w-4 text-txt-secondary" />
              <span className="text-txt-primary">{certificate.issuing_authority}</span>
            </div>
          </div>
        </div>

        {/* Crew Member Name (for crew certificates) */}
        {certificate.certificate_type === 'crew' && certificate.crew_member_name && (
          <div className="mt-ds-4 pt-ds-4 border-t border-surface-border">
            <p className="text-txt-tertiary typo-meta uppercase tracking-wide mb-1">Crew Member</p>
            <div className="flex items-center gap-ds-2">
              <User className="h-4 w-4 text-txt-secondary" />
              <span className="text-txt-primary font-medium">{certificate.crew_member_name}</span>
            </div>
          </div>
        )}

        {/* Primary Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-ds-2 mt-ds-4 pt-ds-4 border-t border-surface-border">
            {actions.slice(0, 4).map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={actionContext}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
            {actions.length > 4 && (
              <button className="h-9 px-ds-2 typo-meta text-txt-tertiary hover:text-txt-primary transition-colors">
                <ChevronRight className="h-[18px] w-[18px]" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          DOCUMENTS SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center justify-between mb-ds-3">
          <div className="flex items-center gap-ds-2">
            <FileText className="h-5 w-5 text-txt-secondary" />
            <h3 className="text-txt-primary font-semibold">Linked Documents</h3>
            {documents.length > 0 && (
              <span className="text-txt-tertiary typo-meta">({documents.length})</span>
            )}
          </div>
        </div>

        {documents.length === 0 ? (
          <EmptyStateCTA
            icon={<FileText className="h-6 w-6 text-txt-tertiary" />}
            title="No documents linked"
            description="Link scanned certificate documents for reference and audit trail."
          />
        ) : (
          <div className="space-y-ds-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-ds-3 bg-surface-elevated rounded-sm border border-surface-border"
              >
                <div className="flex items-center gap-ds-3">
                  <div className="w-8 h-8 rounded-sm bg-surface-hover flex items-center justify-center">
                    <FileText className="h-4 w-4 text-txt-tertiary" />
                  </div>
                  <div>
                    <p className="text-txt-primary font-medium typo-meta">
                      {doc.name}
                    </p>
                    <div className="flex items-center gap-ds-2 typo-meta text-txt-tertiary">
                      {doc.file_type && <span>{doc.file_type.toUpperCase()}</span>}
                      {doc.file_type && doc.created_at && <span>-</span>}
                      {doc.created_at && <span>{formatDate(doc.created_at)}</span>}
                    </div>
                  </div>
                </div>
                <Link className="h-4 w-4 text-txt-tertiary" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================
          AUDIT HISTORY SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <History className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">Activity</h3>
          {auditHistory.length > 0 && (
            <span className="text-txt-tertiary typo-meta">({auditHistory.length})</span>
          )}
        </div>

        {auditHistory.length === 0 ? (
          <div className="text-center py-ds-6">
            <History className="h-8 w-8 text-txt-tertiary mx-auto mb-ds-2" />
            <p className="text-txt-tertiary">No activity yet</p>
          </div>
        ) : (
          <div className="space-y-ds-3">
            {auditHistory.slice(0, 10).map((entry) => {
              // Convert action to human-readable label
              const actionLabels: Record<string, string> = {
                'create_certificate': 'Certificate created',
                'update_certificate': 'Certificate updated',
                'renew_certificate': 'Certificate renewed',
                'supersede_certificate': 'Certificate superseded',
                'link_document': 'Document linked',
                'upload_document': 'Document uploaded',
                'expire_certificate': 'Certificate expired',
              };
              const label = actionLabels[entry.action] || entry.action.replace(/_/g, ' ');

              // Extract summary from new_values
              let summary = '';
              if (entry.new_values) {
                if (entry.new_values.certificate_name) {
                  summary = String(entry.new_values.certificate_name);
                } else if (entry.new_values.document_name) {
                  summary = String(entry.new_values.document_name);
                } else if (entry.new_values.expiry_date) {
                  summary = `New expiry: ${formatDate(String(entry.new_values.expiry_date))}`;
                }
              }

              return (
                <div
                  key={entry.id}
                  className="p-ds-3 bg-surface-elevated rounded-sm border border-surface-border"
                >
                  <div className="flex items-start justify-between gap-ds-2">
                    <p className="text-txt-primary font-medium typo-meta">
                      {label}
                    </p>
                    <span className="typo-meta text-txt-tertiary whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  {summary && (
                    <p className="typo-meta text-txt-secondary mt-1 line-clamp-2">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
            {auditHistory.length > 10 && (
              <p className="typo-meta text-txt-tertiary text-center pt-2">
                +{auditHistory.length - 10} more activities
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
