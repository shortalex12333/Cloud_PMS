/**
 * WarrantyCard Component
 *
 * Full-screen entity view for warranty claims with:
 * - Status badges (draft, submitted, approved, rejected, etc.)
 * - Claim type indicators (repair, replacement, refund)
 * - Equipment/fault references
 * - Vendor/manufacturer information
 * - Financial summary (claimed vs approved amounts)
 * - Documents section (certificates, claims, correspondence)
 * - Audit history timeline
 * - Tokenized styling (no hardcoded values)
 */

'use client';

import { useCallback } from 'react';
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
import {
  WarrantyDocumentsSection,
  type WarrantyDocument,
  type WarrantyDocumentType,
} from '@/components/lens/sections/warranty';

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
    // Documents (certificates, claims, correspondence)
    documents?: WarrantyDocument[];
  };
  actions?: MicroAction[];
  /** Permission: can this user add documents to the claim? */
  canAddDocument?: boolean;
  /** Callback when a document is clicked - opens Document lens */
  onDocumentClick?: (documentId: string) => void;
  /** Callback to open Add Document modal */
  onAddDocument?: () => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getStatusStyles(status: string) {
  switch (status) {
    case 'approved':
      return {
        bg: 'bg-status-success-bg',
        text: 'text-status-success',
        icon: <CheckCircle2 className="h-5 w-5 text-status-success" />,
        label: 'Approved',
      };
    case 'submitted':
      return {
        bg: 'bg-brand-muted',
        text: 'text-brand-interactive',
        icon: <Send className="h-5 w-5 text-brand-interactive" />,
        label: 'Submitted',
      };
    case 'under_review':
      return {
        bg: 'bg-status-warning-bg',
        text: 'text-status-warning',
        icon: <Clock className="h-5 w-5 text-status-warning" />,
        label: 'Under Review',
      };
    case 'rejected':
      return {
        bg: 'bg-status-critical-bg',
        text: 'text-status-critical',
        icon: <XCircle className="h-5 w-5 text-status-critical" />,
        label: 'Rejected',
      };
    case 'closed':
      return {
        bg: 'bg-txt-tertiary/10',
        text: 'text-txt-tertiary',
        icon: <FileText className="h-5 w-5 text-txt-tertiary" />,
        label: 'Closed',
      };
    default: // draft
      return {
        bg: 'bg-txt-tertiary/10',
        text: 'text-txt-secondary',
        icon: <FileWarning className="h-5 w-5 text-txt-secondary" />,
        label: 'Draft',
      };
  }
}

function getClaimTypeStyles(claimType: string) {
  switch (claimType) {
    case 'replacement':
      return {
        bg: 'bg-status-warning-bg',
        text: 'text-status-warning',
        icon: <RefreshCw className="h-4 w-4" />,
        label: 'Replacement',
      };
    case 'refund':
      return {
        bg: 'bg-status-success-bg',
        text: 'text-status-success',
        icon: <DollarSign className="h-4 w-4" />,
        label: 'Refund',
      };
    default: // repair
      return {
        bg: 'bg-brand-muted',
        text: 'text-brand-interactive',
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

export function WarrantyCard({
  warrantyClaim,
  actions = [],
  canAddDocument = false,
  onDocumentClick,
  onAddDocument,
}: WarrantyCardProps) {
  const status = getStatusStyles(warrantyClaim.status);
  const claimType = getClaimTypeStyles(warrantyClaim.claim_type);
  const auditHistory = warrantyClaim.audit_history || [];
  const documents = warrantyClaim.documents || [];

  const actionContext = {
    warranty_claim_id: warrantyClaim.id,
    claim_id: warrantyClaim.id,
    equipment_id: warrantyClaim.equipment_id,
    fault_id: warrantyClaim.fault_id,
  };

  // Handle add document action
  const handleAddDocument = useCallback(() => {
    onAddDocument?.();
  }, [onAddDocument]);

  // Handle document click - opens Document lens
  const handleDocumentClick = useCallback(
    (documentId: string) => {
      onDocumentClick?.(documentId);
    },
    [onDocumentClick]
  );

  return (
    <div className="flex flex-col gap-ds-6">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        {/* Status & Claim Type Row */}
        <div className="flex items-center gap-ds-2 mb-ds-4">
          <span className={cn(
            'inline-flex items-center gap-ds-1 px-ds-3 py-ds-1 rounded-sm text-celeste-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center gap-ds-1 px-ds-3 py-ds-1 rounded-sm text-celeste-sm font-medium',
            claimType.bg, claimType.text
          )}>
            {claimType.icon}
            {claimType.label}
          </span>
        </div>

        {/* Claim Number */}
        <div className="flex items-center gap-ds-2 mb-ds-2">
          <Hash className="h-4 w-4 text-txt-tertiary" />
          <span className="text-txt-tertiary text-celeste-sm font-mono">
            {warrantyClaim.claim_number}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-txt-primary mb-ds-2">
          {warrantyClaim.title}
        </h1>

        {/* Description */}
        {warrantyClaim.description && (
          <p className="text-txt-primary mb-ds-4">
            {warrantyClaim.description}
          </p>
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
              <button className="h-8 px-ds-2 text-celeste-sm text-txt-tertiary hover:text-txt-primary transition-colors">
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
        <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
          <div className="flex items-center gap-ds-2 mb-ds-3">
            <Package className="h-5 w-5 text-txt-secondary" />
            <h3 className="text-txt-primary font-semibold">
              Linked References
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-ds-4">
            {warrantyClaim.equipment_name && (
              <div className="p-ds-4 bg-surface-elevated rounded-sm border border-surface-border">
                <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                  Equipment
                </p>
                <p className="text-txt-primary font-medium">
                  {warrantyClaim.equipment_name}
                </p>
              </div>
            )}

            {warrantyClaim.fault_code && (
              <div className="p-ds-4 bg-surface-elevated rounded-sm border border-surface-border">
                <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                  Fault Reference
                </p>
                <div className="flex items-center gap-ds-2">
                  <AlertCircle className="h-4 w-4 text-status-warning" />
                  <span className="text-txt-primary font-mono">
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
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <Building2 className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">
            Vendor / Manufacturer
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-ds-4">
          {warrantyClaim.vendor_name && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Vendor
              </p>
              <span className="text-txt-primary">
                {warrantyClaim.vendor_name}
              </span>
            </div>
          )}

          {warrantyClaim.manufacturer && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Manufacturer
              </p>
              <span className="text-txt-primary">
                {warrantyClaim.manufacturer}
              </span>
            </div>
          )}

          {warrantyClaim.part_number && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Part Number
              </p>
              <span className="text-txt-primary font-mono">
                {warrantyClaim.part_number}
              </span>
            </div>
          )}

          {warrantyClaim.serial_number && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Serial Number
              </p>
              <span className="text-txt-primary font-mono">
                {warrantyClaim.serial_number}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          FINANCIAL SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <DollarSign className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">
            Financial Summary
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-ds-4">
          <div className="p-ds-4 bg-surface-elevated rounded-sm border border-surface-border">
            <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
              Claimed Amount
            </p>
            <p className="text-xl font-semibold text-txt-primary">
              {formatCurrency(warrantyClaim.claimed_amount, warrantyClaim.currency)}
            </p>
          </div>

          {warrantyClaim.status === 'approved' && (
            <div className="p-ds-4 bg-status-success/5 rounded-sm border border-status-success/20">
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Approved Amount
              </p>
              <p className="text-xl font-semibold text-status-success">
                {formatCurrency(warrantyClaim.approved_amount, warrantyClaim.currency)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          DOCUMENTS SECTION
          ================================================================ */}
      <WarrantyDocumentsSection
        documents={documents}
        onAddDocument={handleAddDocument}
        canAddDocument={canAddDocument}
        onDocumentClick={handleDocumentClick}
      />

      {/* ================================================================
          DATES SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <Calendar className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">
            Dates
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-ds-4">
          {warrantyClaim.purchase_date && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Purchase Date
              </p>
              <span className="text-txt-primary">
                {formatDate(warrantyClaim.purchase_date)}
              </span>
            </div>
          )}

          {warrantyClaim.warranty_expiry && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Warranty Expiry
              </p>
              <span className={cn(
                new Date(warrantyClaim.warranty_expiry) < new Date()
                  ? 'text-status-critical'
                  : 'text-txt-primary'
              )}>
                {formatDate(warrantyClaim.warranty_expiry)}
              </span>
            </div>
          )}

          {warrantyClaim.drafted_at && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Drafted
              </p>
              <span className="text-txt-primary">
                {formatDate(warrantyClaim.drafted_at)}
              </span>
            </div>
          )}

          {warrantyClaim.submitted_at && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Submitted
              </p>
              <span className="text-txt-primary">
                {formatDate(warrantyClaim.submitted_at)}
              </span>
            </div>
          )}

          {warrantyClaim.approved_at && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Approved
              </p>
              <span className="text-status-success">
                {formatDate(warrantyClaim.approved_at)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          WORKFLOW SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <User className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">
            Workflow
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-ds-4">
          {warrantyClaim.drafted_by && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Drafted By
              </p>
              <span className="text-txt-primary">
                {warrantyClaim.drafted_by}
              </span>
            </div>
          )}

          {warrantyClaim.submitted_by && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Submitted By
              </p>
              <span className="text-txt-primary">
                {warrantyClaim.submitted_by}
              </span>
            </div>
          )}

          {warrantyClaim.approved_by && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">
                Approved By
              </p>
              <span className="text-status-success">
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
        <div className="bg-status-critical/5 rounded-md p-ds-6 border border-status-critical/20">
          <div className="flex items-center gap-ds-2 mb-ds-3">
            <XCircle className="h-5 w-5 text-status-critical" />
            <h3 className="text-status-critical font-semibold">
              Rejection Reason
            </h3>
          </div>
          <p className="text-txt-primary">
            {warrantyClaim.rejection_reason}
          </p>
        </div>
      )}

      {/* ================================================================
          AUDIT HISTORY SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <History className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">Activity</h3>
          {auditHistory.length > 0 && (
            <span className="text-txt-tertiary text-celeste-sm">({auditHistory.length})</span>
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
                  className="p-ds-3 bg-surface-elevated rounded-sm border border-surface-border"
                >
                  <div className="flex items-start justify-between gap-ds-2">
                    <p className="text-txt-primary font-medium text-celeste-sm">
                      {label}
                    </p>
                    <span className="text-celeste-xs text-txt-tertiary whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  {summary && (
                    <p className="text-celeste-sm text-txt-secondary mt-1 line-clamp-2">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
            {auditHistory.length > 10 && (
              <p className="text-celeste-xs text-txt-tertiary text-center pt-2">
                +{auditHistory.length - 10} more activities
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
