/**
 * WarrantyCard Component
 *
 * Full-screen entity view for warranty claims with:
 * - Status badges (draft, submitted, approved, rejected, etc.)
 * - Claim type indicators (repair, replacement, refund)
 * - Equipment/fault references
 * - Vendor/manufacturer information
 * - Financial summary (claimed vs approved amounts)
 * - Audit history timeline
 * - Tokenized styling (no hardcoded values)
 */

'use client';

import {
  FileWarning,
  CheckCircle2,
  XCircle,
  Clock,
  Wrench,
  RefreshCw,
  DollarSign,
  Building2,
  Package,
  AlertCircle,
  History,
  ChevronRight,
  Send,
  FileText,
  Calendar,
  Hash,
  User,
  Mail,
} from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

interface WarrantyAuditEntry {
  id: string;
  action: string;
  old_values?: Record<string, unknown>;
  new_values?: Record<string, unknown>;
  user_id?: string;
  created_at: string;
}

interface WarrantyCardProps {
  warrantyClaim: {
    id: string;
    claim_number: string;
    title: string;
    description: string;
    claim_type: 'repair' | 'replacement' | 'refund';
    status: 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'closed';
    // Equipment/Fault links
    equipment_id?: string;
    equipment_name?: string;
    fault_id?: string;
    fault_code?: string;
    // Vendor info
    vendor_id?: string;
    vendor_name?: string;
    manufacturer?: string;
    part_number?: string;
    serial_number?: string;
    // Dates
    purchase_date?: string;
    warranty_expiry?: string;
    created_at?: string;
    // Amounts
    claimed_amount?: number;
    approved_amount?: number;
    currency: string;
    // Workflow
    drafted_by?: string;
    drafted_at?: string;
    submitted_by?: string;
    submitted_at?: string;
    approved_by?: string;
    approved_at?: string;
    rejection_reason?: string;
    // Enriched data
    audit_history?: WarrantyAuditEntry[];
  };
  actions?: MicroAction[];
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getStatusStyles(status: string) {
  switch (status) {
    case 'approved':
      return {
        bg: 'bg-[var(--celeste-green)]/10',
        text: 'text-[var(--celeste-green)]',
        icon: <CheckCircle2 className="h-5 w-5 text-[var(--celeste-green)]" />,
        label: 'Approved',
      };
    case 'submitted':
      return {
        bg: 'bg-[var(--celeste-accent)]/10',
        text: 'text-[var(--celeste-accent)]',
        icon: <Send className="h-5 w-5 text-[var(--celeste-accent)]" />,
        label: 'Submitted',
      };
    case 'under_review':
      return {
        bg: 'bg-[var(--celeste-yellow)]/10',
        text: 'text-[var(--celeste-yellow)]',
        icon: <Clock className="h-5 w-5 text-[var(--celeste-yellow)]" />,
        label: 'Under Review',
      };
    case 'rejected':
      return {
        bg: 'bg-[var(--celeste-warning)]/10',
        text: 'text-[var(--celeste-warning)]',
        icon: <XCircle className="h-5 w-5 text-[var(--celeste-warning)]" />,
        label: 'Rejected',
      };
    case 'closed':
      return {
        bg: 'bg-[var(--celeste-text-muted)]/10',
        text: 'text-[var(--celeste-text-muted)]',
        icon: <FileText className="h-5 w-5 text-[var(--celeste-text-muted)]" />,
        label: 'Closed',
      };
    default: // draft
      return {
        bg: 'bg-[var(--celeste-text-muted)]/10',
        text: 'text-[var(--celeste-text-secondary)]',
        icon: <FileWarning className="h-5 w-5 text-[var(--celeste-text-secondary)]" />,
        label: 'Draft',
      };
  }
}

function getClaimTypeStyles(claimType: string) {
  switch (claimType) {
    case 'replacement':
      return {
        bg: 'bg-[var(--celeste-orange)]/10',
        text: 'text-[var(--celeste-orange)]',
        icon: <RefreshCw className="h-4 w-4" />,
        label: 'Replacement',
      };
    case 'refund':
      return {
        bg: 'bg-[var(--celeste-green)]/10',
        text: 'text-[var(--celeste-green)]',
        icon: <DollarSign className="h-4 w-4" />,
        label: 'Refund',
      };
    default: // repair
      return {
        bg: 'bg-[var(--celeste-accent)]/10',
        text: 'text-[var(--celeste-accent)]',
        icon: <Wrench className="h-4 w-4" />,
        label: 'Repair',
      };
  }
}

function formatCurrency(amount: number | undefined, currency: string): string {
  if (amount === undefined || amount === null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(amount);
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function WarrantyCard({ warrantyClaim, actions = [] }: WarrantyCardProps) {
  const status = getStatusStyles(warrantyClaim.status);
  const claimType = getClaimTypeStyles(warrantyClaim.claim_type);
  const auditHistory = warrantyClaim.audit_history || [];

  const actionContext = {
    warranty_claim_id: warrantyClaim.id,
    claim_id: warrantyClaim.id,
    equipment_id: warrantyClaim.equipment_id,
    fault_id: warrantyClaim.fault_id,
  };

  return (
    <div className="flex flex-col gap-[var(--celeste-spacing-6)]">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        {/* Status & Claim Type Row */}
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-4)]">
          <span className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-1)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-1)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            claimType.bg, claimType.text
          )}>
            {claimType.icon}
            {claimType.label}
          </span>
        </div>

        {/* Claim Number */}
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-2)]">
          <Hash className="h-4 w-4 text-[var(--celeste-text-muted)]" />
          <span className="text-[var(--celeste-text-muted)] text-sm font-mono">
            {warrantyClaim.claim_number}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-[var(--celeste-text-title)] mb-[var(--celeste-spacing-2)]">
          {warrantyClaim.title}
        </h1>

        {/* Description */}
        {warrantyClaim.description && (
          <p className="text-[var(--celeste-text-primary)] mb-[var(--celeste-spacing-4)]">
            {warrantyClaim.description}
          </p>
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
          EQUIPMENT & FAULT SECTION
          ================================================================ */}
      {(warrantyClaim.equipment_name || warrantyClaim.fault_code) && (
        <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
            <Package className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">
              Linked References
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-[var(--celeste-spacing-4)]">
            {warrantyClaim.equipment_name && (
              <div className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
                <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                  Equipment
                </p>
                <p className="text-[var(--celeste-text-primary)] font-medium">
                  {warrantyClaim.equipment_name}
                </p>
              </div>
            )}

            {warrantyClaim.fault_code && (
              <div className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
                <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                  Fault Reference
                </p>
                <div className="flex items-center gap-[var(--celeste-spacing-2)]">
                  <AlertCircle className="h-4 w-4 text-[var(--celeste-orange)]" />
                  <span className="text-[var(--celeste-text-primary)] font-mono">
                    {warrantyClaim.fault_code}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================================================================
          VENDOR / MANUFACTURER SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <Building2 className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">
            Vendor / Manufacturer
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-[var(--celeste-spacing-4)]">
          {warrantyClaim.vendor_name && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Vendor
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {warrantyClaim.vendor_name}
              </span>
            </div>
          )}

          {warrantyClaim.manufacturer && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Manufacturer
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {warrantyClaim.manufacturer}
              </span>
            </div>
          )}

          {warrantyClaim.part_number && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Part Number
              </p>
              <span className="text-[var(--celeste-text-primary)] font-mono">
                {warrantyClaim.part_number}
              </span>
            </div>
          )}

          {warrantyClaim.serial_number && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Serial Number
              </p>
              <span className="text-[var(--celeste-text-primary)] font-mono">
                {warrantyClaim.serial_number}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          FINANCIAL SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <DollarSign className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">
            Financial Summary
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-[var(--celeste-spacing-4)]">
          <div className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
              Claimed Amount
            </p>
            <p className="text-xl font-semibold text-[var(--celeste-text-title)]">
              {formatCurrency(warrantyClaim.claimed_amount, warrantyClaim.currency)}
            </p>
          </div>

          {warrantyClaim.status === 'approved' && (
            <div className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-green)]/5 rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-green)]/20">
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Approved Amount
              </p>
              <p className="text-xl font-semibold text-[var(--celeste-green)]">
                {formatCurrency(warrantyClaim.approved_amount, warrantyClaim.currency)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          DATES SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <Calendar className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">
            Dates
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-[var(--celeste-spacing-4)]">
          {warrantyClaim.purchase_date && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Purchase Date
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {formatDate(warrantyClaim.purchase_date)}
              </span>
            </div>
          )}

          {warrantyClaim.warranty_expiry && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Warranty Expiry
              </p>
              <span className={cn(
                new Date(warrantyClaim.warranty_expiry) < new Date()
                  ? 'text-[var(--celeste-warning)]'
                  : 'text-[var(--celeste-text-primary)]'
              )}>
                {formatDate(warrantyClaim.warranty_expiry)}
              </span>
            </div>
          )}

          {warrantyClaim.drafted_at && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Drafted
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {formatDate(warrantyClaim.drafted_at)}
              </span>
            </div>
          )}

          {warrantyClaim.submitted_at && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Submitted
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {formatDate(warrantyClaim.submitted_at)}
              </span>
            </div>
          )}

          {warrantyClaim.approved_at && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Approved
              </p>
              <span className="text-[var(--celeste-green)]">
                {formatDate(warrantyClaim.approved_at)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          WORKFLOW SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <User className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">
            Workflow
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-[var(--celeste-spacing-4)]">
          {warrantyClaim.drafted_by && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Drafted By
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {warrantyClaim.drafted_by}
              </span>
            </div>
          )}

          {warrantyClaim.submitted_by && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Submitted By
              </p>
              <span className="text-[var(--celeste-text-primary)]">
                {warrantyClaim.submitted_by}
              </span>
            </div>
          )}

          {warrantyClaim.approved_by && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">
                Approved By
              </p>
              <span className="text-[var(--celeste-green)]">
                {warrantyClaim.approved_by}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          REJECTION REASON (if rejected)
          ================================================================ */}
      {warrantyClaim.status === 'rejected' && warrantyClaim.rejection_reason && (
        <div className="bg-[var(--celeste-warning)]/5 rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-warning)]/20">
          <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
            <XCircle className="h-5 w-5 text-[var(--celeste-warning)]" />
            <h3 className="text-[var(--celeste-warning)] font-semibold">
              Rejection Reason
            </h3>
          </div>
          <p className="text-[var(--celeste-text-primary)]">
            {warrantyClaim.rejection_reason}
          </p>
        </div>
      )}

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
                'draft_warranty_claim': 'Claim drafted',
                'submit_warranty_claim': 'Claim submitted',
                'approve_warranty_claim': 'Claim approved',
                'reject_warranty_claim': 'Claim rejected',
                'compose_warranty_email': 'Email composed',
                'update_warranty_claim': 'Claim updated',
              };
              const label = actionLabels[entry.action] || entry.action.replace(/_/g, ' ');

              // Extract summary from new_values
              let summary = '';
              if (entry.new_values) {
                if (entry.new_values.status) {
                  summary = `Status changed to ${String(entry.new_values.status)}`;
                } else if (entry.new_values.rejection_reason) {
                  summary = `Reason: ${String(entry.new_values.rejection_reason).slice(0, 100)}`;
                } else if (entry.new_values.approved_amount) {
                  summary = `Approved: ${formatCurrency(entry.new_values.approved_amount as number, warrantyClaim.currency)}`;
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
