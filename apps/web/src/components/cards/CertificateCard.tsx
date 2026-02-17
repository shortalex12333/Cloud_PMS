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
    <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-6)] px-[var(--celeste-spacing-4)] text-center">
      <div className="w-12 h-12 rounded-[var(--celeste-border-radius-md)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-3)]">
        {icon}
      </div>
      <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
        {title}
      </p>
      <p className="text-[var(--celeste-text-muted)] text-sm">
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
          bg: 'bg-[var(--celeste-green)]/10',
          text: 'text-[var(--celeste-green)]',
          icon: <CheckCircle2 className="h-5 w-5 text-[var(--celeste-green)]" />,
          label: 'Valid',
        };
      case 'expiring_soon':
        return {
          bg: 'bg-[var(--celeste-orange)]/10',
          text: 'text-[var(--celeste-orange)]',
          icon: <AlertTriangle className="h-5 w-5 text-[var(--celeste-orange)]" />,
          label: 'Expiring Soon',
        };
      case 'expired':
        return {
          bg: 'bg-[var(--celeste-warning)]/10',
          text: 'text-[var(--celeste-warning)]',
          icon: <XCircle className="h-5 w-5 text-[var(--celeste-warning)]" />,
          label: 'Expired',
        };
      case 'superseded':
        return {
          bg: 'bg-[var(--celeste-text-muted)]/10',
          text: 'text-[var(--celeste-text-muted)]',
          icon: <Archive className="h-5 w-5 text-[var(--celeste-text-muted)]" />,
          label: 'Superseded',
        };
      default:
        return {
          bg: 'bg-[var(--celeste-text-muted)]/10',
          text: 'text-[var(--celeste-text-muted)]',
          icon: <FileCheck className="h-5 w-5 text-[var(--celeste-text-muted)]" />,
          label: 'Unknown',
        };
    }
  };

  // Get certificate type styling
  const getTypeStyles = (type: string) => {
    switch (type) {
      case 'vessel':
        return { bg: 'bg-[var(--celeste-accent)]/10', text: 'text-[var(--celeste-accent)]', label: 'Vessel' };
      case 'crew':
        return { bg: 'bg-[var(--celeste-text-secondary)]/10', text: 'text-[var(--celeste-text-secondary)]', label: 'Crew' };
      default:
        return { bg: 'bg-[var(--celeste-text-muted)]/10', text: 'text-[var(--celeste-text-muted)]', label: type };
    }
  };

  // Get expiry countdown styling
  const getExpiryCountdownStyles = (daysUntilExpiry: number | undefined) => {
    if (daysUntilExpiry === undefined) return null;

    if (daysUntilExpiry < 0) {
      return {
        color: 'text-[var(--celeste-warning)]',
        bg: 'bg-[var(--celeste-warning)]/10',
        text: `Expired ${Math.abs(daysUntilExpiry)} days ago`,
      };
    } else if (daysUntilExpiry <= 30) {
      return {
        color: 'text-[var(--celeste-warning)]',
        bg: 'bg-[var(--celeste-warning)]/10',
        text: `${daysUntilExpiry} days remaining`,
      };
    } else if (daysUntilExpiry <= 90) {
      return {
        color: 'text-[var(--celeste-orange)]',
        bg: 'bg-[var(--celeste-orange)]/10',
        text: `${daysUntilExpiry} days remaining`,
      };
    } else {
      return {
        color: 'text-[var(--celeste-green)]',
        bg: 'bg-[var(--celeste-green)]/10',
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
    <div className="flex flex-col gap-[var(--celeste-spacing-6)]">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        {/* Status & Type Row */}
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-4)]">
          <span className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-1)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            certType.bg, certType.text
          )}>
            {certType.label}
          </span>
        </div>

        {/* Certificate Name */}
        <h1 className="text-2xl font-semibold text-[var(--celeste-text-title)] mb-[var(--celeste-spacing-2)]">
          {certificate.certificate_name}
        </h1>

        {/* Certificate Number */}
        {certificate.certificate_number && (
          <p className="text-[var(--celeste-text-secondary)] mb-[var(--celeste-spacing-4)]">
            Certificate No: {certificate.certificate_number}
          </p>
        )}

        {/* Expiry Countdown Indicator */}
        {expiryCountdown && (
          <div className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-2)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-2)] rounded-[var(--celeste-border-radius-sm)] mb-[var(--celeste-spacing-4)]',
            expiryCountdown.bg
          )}>
            <Clock className={cn('h-4 w-4', expiryCountdown.color)} />
            <span className={cn('text-sm font-medium', expiryCountdown.color)}>
              {expiryCountdown.text}
            </span>
          </div>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
          {/* Certificate Type */}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Type</p>
            <div className="flex items-center gap-[var(--celeste-spacing-1)]">
              <FileCheck className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className="text-[var(--celeste-text-primary)] capitalize">{certificate.certificate_type}</span>
            </div>
          </div>

          {/* Issue Date */}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Issue Date</p>
            <div className="flex items-center gap-[var(--celeste-spacing-1)]">
              <Calendar className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className="text-[var(--celeste-text-primary)]">{formatDate(certificate.issue_date)}</span>
            </div>
          </div>

          {/* Expiry Date */}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Expiry Date</p>
            <div className="flex items-center gap-[var(--celeste-spacing-1)]">
              <Calendar className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className={cn(
                certificate.status === 'expired' ? 'text-[var(--celeste-warning)]' :
                certificate.status === 'expiring_soon' ? 'text-[var(--celeste-orange)]' :
                'text-[var(--celeste-text-primary)]'
              )}>
                {formatDate(certificate.expiry_date)}
              </span>
            </div>
          </div>

          {/* Issuing Authority */}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Issuing Authority</p>
            <div className="flex items-center gap-[var(--celeste-spacing-1)]">
              <Building2 className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className="text-[var(--celeste-text-primary)]">{certificate.issuing_authority}</span>
            </div>
          </div>
        </div>

        {/* Crew Member Name (for crew certificates) */}
        {certificate.certificate_type === 'crew' && certificate.crew_member_name && (
          <div className="mt-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Crew Member</p>
            <div className="flex items-center gap-[var(--celeste-spacing-2)]">
              <User className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className="text-[var(--celeste-text-primary)] font-medium">{certificate.crew_member_name}</span>
            </div>
          </div>
        )}

        {/* Primary Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-[var(--celeste-spacing-2)] mt-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
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
              <button className="h-8 px-[var(--celeste-spacing-2)] text-sm text-[var(--celeste-text-muted)] hover:text-[var(--celeste-text-primary)] transition-colors">
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          DOCUMENTS SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <FileText className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Linked Documents</h3>
            {documents.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({documents.length})</span>
            )}
          </div>
        </div>

        {documents.length === 0 ? (
          <EmptyStateCTA
            icon={<FileText className="h-6 w-6 text-[var(--celeste-text-muted)]" />}
            title="No documents linked"
            description="Link scanned certificate documents for reference and audit trail."
          />
        ) : (
          <div className="space-y-[var(--celeste-spacing-2)]">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
              >
                <div className="flex items-center gap-[var(--celeste-spacing-3)]">
                  <div className="w-8 h-8 rounded-[var(--celeste-border-radius-sm)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center">
                    <FileText className="h-4 w-4 text-[var(--celeste-text-muted)]" />
                  </div>
                  <div>
                    <p className="text-[var(--celeste-text-primary)] font-medium text-sm">
                      {doc.name}
                    </p>
                    <div className="flex items-center gap-[var(--celeste-spacing-2)] text-xs text-[var(--celeste-text-muted)]">
                      {doc.file_type && <span>{doc.file_type.toUpperCase()}</span>}
                      {doc.file_type && doc.created_at && <span>-</span>}
                      {doc.created_at && <span>{formatDate(doc.created_at)}</span>}
                    </div>
                  </div>
                </div>
                <Link className="h-4 w-4 text-[var(--celeste-text-muted)]" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================
          AUDIT HISTORY SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <History className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">Activity</h3>
          {auditHistory.length > 0 && (
            <span className="text-[var(--celeste-text-muted)] text-sm">({auditHistory.length})</span>
          )}
        </div>

        {auditHistory.length === 0 ? (
          <div className="text-center py-[var(--celeste-spacing-6)]">
            <History className="h-8 w-8 text-[var(--celeste-text-muted)] mx-auto mb-[var(--celeste-spacing-2)]" />
            <p className="text-[var(--celeste-text-muted)]">No activity yet</p>
          </div>
        ) : (
          <div className="space-y-[var(--celeste-spacing-3)]">
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
                  className="p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
                >
                  <div className="flex items-start justify-between gap-[var(--celeste-spacing-2)]">
                    <p className="text-[var(--celeste-text-primary)] font-medium text-sm">
                      {label}
                    </p>
                    <span className="text-xs text-[var(--celeste-text-muted)] whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  {summary && (
                    <p className="text-sm text-[var(--celeste-text-secondary)] mt-1 line-clamp-2">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
            {auditHistory.length > 10 && (
              <p className="text-xs text-[var(--celeste-text-muted)] text-center pt-2">
                +{auditHistory.length - 10} more activities
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
