/**
 * ShoppingListCard Component
 *
 * Displays shopping list item information with status, urgency, and actions.
 * Part of SHOP-03 requirement - Shopping List Lens v1.
 *
 * Features:
 * - Display: part_name, quantity_requested, status (with StatusPill), urgency, source_type
 * - Show approval info when approved
 * - Show rejection info when rejected
 * - Action buttons based on user role (HoD approval/rejection, Engineer promotion)
 */

'use client';

import { useState } from 'react';
import {
  ShoppingCart,
  Package,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  FileText,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { StatusPill } from '@/components/ui/StatusPill';
import { EntityLink } from '@/components/ui/EntityLink';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

export interface ShoppingListItemData {
  id: string;
  part_name: string;
  part_number?: string;
  manufacturer?: string;
  quantity_requested: number;
  quantity_approved?: number;
  unit?: string;
  status: 'candidate' | 'under_review' | 'approved' | 'ordered' | 'partially_fulfilled' | 'fulfilled' | 'installed' | 'rejected';
  urgency?: 'low' | 'normal' | 'high' | 'critical';
  source_type: 'inventory_low' | 'inventory_oos' | 'work_order_usage' | 'receiving_missing' | 'receiving_damaged' | 'manual_add';
  source_notes?: string;
  // Linked entities
  part_id?: string;
  is_candidate_part?: boolean;
  candidate_promoted_to_part_id?: string;
  source_work_order_id?: string;
  source_receiving_id?: string;
  // Timestamps and users
  created_at: string;
  created_by?: string;
  created_by_name?: string;
  approved_at?: string;
  approved_by?: string;
  approved_by_name?: string;
  approval_notes?: string;
  rejected_at?: string;
  rejected_by?: string;
  rejected_by_name?: string;
  rejection_reason?: string;
  rejection_notes?: string;
  promoted_at?: string;
  promoted_by?: string;
  promoted_by_name?: string;
}

interface ShoppingListCardProps {
  item: ShoppingListItemData;
  actions?: MicroAction[];
  userRole?: string;
  isHoD?: boolean;
  isEngineer?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onPromote?: () => void;
  onViewHistory?: () => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Map shopping list status to StatusPill color
 */
function mapStatusToColor(
  status: ShoppingListItemData['status'],
  isRejected?: boolean
): 'critical' | 'warning' | 'success' | 'neutral' {
  if (isRejected) return 'critical';

  switch (status) {
    case 'rejected':
      return 'critical';
    case 'candidate':
    case 'under_review':
      return 'warning';
    case 'approved':
    case 'ordered':
    case 'partially_fulfilled':
      return 'neutral';
    case 'fulfilled':
    case 'installed':
      return 'success';
    default:
      return 'neutral';
  }
}

/**
 * Map urgency to display config
 */
function getUrgencyConfig(urgency?: ShoppingListItemData['urgency']): {
  label: string;
  pillClass: string;
  icon?: React.ReactNode;
} {
  switch (urgency) {
    case 'critical':
      return {
        label: 'Critical',
        pillClass: 'status-pill status-pill-critical',
        icon: <AlertTriangle className="h-3 w-3" />,
      };
    case 'high':
      return {
        label: 'High',
        pillClass: 'status-pill status-pill-warning',
      };
    case 'normal':
      return {
        label: 'Normal',
        pillClass: 'status-pill status-pill-neutral',
      };
    case 'low':
    default:
      return {
        label: 'Low',
        pillClass: 'status-pill status-pill-neutral',
      };
  }
}

/**
 * Map source type to human-readable label
 */
function getSourceTypeLabel(sourceType: ShoppingListItemData['source_type']): string {
  const labels: Record<ShoppingListItemData['source_type'], string> = {
    inventory_low: 'Low Stock',
    inventory_oos: 'Out of Stock',
    work_order_usage: 'Work Order',
    receiving_missing: 'Missing from Delivery',
    receiving_damaged: 'Damaged on Arrival',
    manual_add: 'Manual Request',
  };
  return labels[sourceType] || sourceType.replace(/_/g, ' ');
}

/**
 * Format status for display
 */
function formatStatusLabel(status: ShoppingListItemData['status'], isRejected?: boolean): string {
  if (isRejected) return 'Rejected';

  const labels: Record<ShoppingListItemData['status'], string> = {
    candidate: 'Pending Review',
    under_review: 'Under Review',
    approved: 'Approved',
    ordered: 'Ordered',
    partially_fulfilled: 'Partial',
    fulfilled: 'Fulfilled',
    installed: 'Installed',
    rejected: 'Rejected',
  };
  return labels[status] || status.replace(/_/g, ' ');
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ShoppingListCard({
  item,
  actions = [],
  userRole,
  isHoD = false,
  isEngineer = false,
  onApprove,
  onReject,
  onPromote,
  onViewHistory,
}: ShoppingListCardProps) {
  const isRejected = !!item.rejected_at;
  const isApproved = item.status === 'approved' && !isRejected;
  const isPending = (item.status === 'candidate' || item.status === 'under_review') && !isRejected;
  const canBePromoted = item.is_candidate_part && !item.candidate_promoted_to_part_id && isEngineer;

  const statusColor = mapStatusToColor(item.status, isRejected);
  const statusLabel = formatStatusLabel(item.status, isRejected);
  const urgencyConfig = getUrgencyConfig(item.urgency);
  const sourceLabel = getSourceTypeLabel(item.source_type);

  const actionContext = {
    shopping_list_item_id: item.id,
    part_id: item.part_id,
  };

  return (
    <div
      className={cn(
        'bg-surface-primary rounded-md p-ds-4 border',
        isRejected
          ? 'border-red-200 bg-red-50/30'
          : 'border-surface-border',
        'transition-colors'
      )}
      data-testid="shopping-list-card"
      data-entity-type="shopping_list_item"
      data-entity-id={item.id}
    >
      <div className="flex items-start gap-ds-3">
        {/* Icon */}
        <div
          className={cn(
            'mt-0.5 p-2 rounded-lg',
            isRejected
              ? 'bg-red-100 text-red-600'
              : isApproved
              ? 'bg-green-100 text-green-600'
              : 'bg-brand-muted text-brand-interactive'
          )}
        >
          {isRejected ? (
            <XCircle className="h-5 w-5" />
          ) : isApproved ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : (
            <ShoppingCart className="h-5 w-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header Row: Part Name + Status */}
          <div className="flex items-center gap-ds-2 mb-ds-2 flex-wrap">
            <h3 className="font-semibold text-txt-primary truncate">
              {item.part_name}
            </h3>
            <StatusPill
              status={statusColor}
              label={statusLabel}
              showDot={isPending}
            />
            {item.urgency && item.urgency !== 'normal' && (
              <span className={urgencyConfig.pillClass}>
                {urgencyConfig.icon}
                {urgencyConfig.label}
              </span>
            )}
          </div>

          {/* Part Details */}
          <div className="space-y-ds-1 mb-ds-3">
            {/* Part Number & Manufacturer */}
            {(item.part_number || item.manufacturer) && (
              <p className="typo-body text-txt-secondary">
                {item.part_number && (
                  <span className="font-medium">P/N: {item.part_number}</span>
                )}
                {item.part_number && item.manufacturer && ' | '}
                {item.manufacturer && <span>{item.manufacturer}</span>}
              </p>
            )}

            {/* Quantity */}
            <div className="flex items-center gap-ds-4 typo-body">
              <span className="text-txt-primary">
                <span className="font-medium">Requested:</span>{' '}
                <span className="text-brand-interactive font-semibold">
                  {item.quantity_requested}
                </span>
                {item.unit && (
                  <span className="text-txt-tertiary ml-1">
                    {item.unit}
                  </span>
                )}
              </span>
              {item.quantity_approved !== undefined && item.quantity_approved !== null && (
                <span className="text-txt-primary">
                  <span className="font-medium">Approved:</span>{' '}
                  <span className="text-green-600 font-semibold">
                    {item.quantity_approved}
                  </span>
                  {item.unit && (
                    <span className="text-txt-tertiary ml-1">
                      {item.unit}
                    </span>
                  )}
                </span>
              )}
            </div>

            {/* Source Type */}
            <div className="flex items-center gap-ds-2 typo-meta text-txt-tertiary">
              <FileText className="h-3.5 w-3.5" />
              <span>Source: {sourceLabel}</span>
              {item.source_work_order_id && (
                <>
                  <span>|</span>
                  <EntityLink
                    entityType="work_order"
                    entityId={item.source_work_order_id}
                    label="View Work Order"
                    className="typo-meta"
                  />
                </>
              )}
            </div>

            {/* Candidate Part Badge */}
            {item.is_candidate_part && !item.candidate_promoted_to_part_id && (
              <div className="flex items-center gap-ds-1 typo-meta text-amber-600">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Candidate part (not in catalog)</span>
              </div>
            )}

            {/* Linked Part */}
            {item.part_id && !item.is_candidate_part && (
              <div className="flex items-center gap-ds-2 typo-meta">
                <Package className="h-3.5 w-3.5 text-txt-tertiary" />
                <EntityLink
                  entityType="part"
                  entityId={item.part_id}
                  label="View Part"
                  className="typo-meta"
                />
              </div>
            )}

            {/* Source Notes */}
            {item.source_notes && (
              <p className="typo-body text-txt-secondary italic mt-1">
                "{item.source_notes}"
              </p>
            )}
          </div>

          {/* Approval Info */}
          {isApproved && item.approved_at && (
            <div className="p-ds-3 bg-green-50 rounded-md border border-green-200 mb-ds-3">
              <div className="flex items-center gap-ds-2 typo-body text-green-700">
                <CheckCircle2 className="h-4 w-4" />
                <span className="font-medium">Approved</span>
                {item.approved_by_name && (
                  <>
                    <span>by</span>
                    <span className="font-medium">{item.approved_by_name}</span>
                  </>
                )}
                <span className="text-green-600">
                  {formatDate(item.approved_at)}
                </span>
              </div>
              {item.approval_notes && (
                <p className="typo-body text-green-600 mt-1 pl-6">
                  {item.approval_notes}
                </p>
              )}
            </div>
          )}

          {/* Rejection Info */}
          {isRejected && item.rejected_at && (
            <div className="p-ds-3 bg-red-50 rounded-md border border-red-200 mb-ds-3">
              <div className="flex items-center gap-ds-2 typo-body text-red-700">
                <XCircle className="h-4 w-4" />
                <span className="font-medium">Rejected</span>
                {item.rejected_by_name && (
                  <>
                    <span>by</span>
                    <span className="font-medium">{item.rejected_by_name}</span>
                  </>
                )}
                <span className="text-red-600">
                  {formatDate(item.rejected_at)}
                </span>
              </div>
              {item.rejection_reason && (
                <p className="typo-body text-red-700 mt-1 pl-6 font-medium">
                  Reason: {item.rejection_reason}
                </p>
              )}
              {item.rejection_notes && (
                <p className="typo-body text-red-600 mt-1 pl-6">
                  {item.rejection_notes}
                </p>
              )}
            </div>
          )}

          {/* Metadata Row */}
          <div className="flex items-center gap-ds-4 typo-meta text-txt-tertiary mb-ds-3">
            {item.created_by_name && (
              <div className="flex items-center gap-1">
                <User className="h-3.5 w-3.5" />
                <span>{item.created_by_name}</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              <span>{formatDate(item.created_at)}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-ds-2">
            {/* HoD Actions: Approve/Reject (only for pending items) */}
            {isHoD && isPending && (
              <>
                {onApprove && (
                  <button
                    onClick={onApprove}
                    className="btn-primary"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Approve
                  </button>
                )}
                {onReject && (
                  <button
                    onClick={onReject}
                    className="btn-danger"
                  >
                    <XCircle className="h-4 w-4" />
                    Reject
                  </button>
                )}
              </>
            )}

            {/* Engineer Action: Promote to Part Catalog */}
            {canBePromoted && onPromote && (
              <button
                onClick={onPromote}
                className="btn-primary"
              >
                <Sparkles className="h-4 w-4" />
                Add to Catalog
              </button>
            )}

            {/* View History */}
            {onViewHistory && (
              <button
                onClick={onViewHistory}
                className="btn-ghost"
              >
                <Clock className="h-4 w-4" />
                History
              </button>
            )}

            {/* Backend-provided actions */}
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={actionContext}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ShoppingListCard;
