'use client';

/**
 * ShoppingListLensContent - Inner content for Shopping List lens (no LensContainer).
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
import { toast } from 'sonner';
import { useShoppingListActions, useShoppingListPermissions } from '@/hooks/useShoppingListActions';

export interface ShoppingListLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

interface ShoppingListItem {
  id: string;
  part_name: string;
  quantity_requested: number;
  unit?: string;
  status: string;
  urgency?: 'low' | 'normal' | 'high' | 'critical';
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected': return 'critical';
    case 'pending': return 'warning';
    case 'approved':
    case 'ordered': return 'success';
    default: return 'neutral';
  }
}

/**
 * ItemActions - Action buttons for a single shopping list item.
 * Uses useShoppingListActions hook with the specific item ID.
 */
function ItemActions({
  item,
  canApprove,
  canReject,
  onRefresh,
}: {
  item: ShoppingListItem;
  canApprove: boolean;
  canReject: boolean;
  onRefresh?: () => void;
}) {
  const { approveItem, rejectItem, isLoading } = useShoppingListActions(item.id);
  const [actionInProgress, setActionInProgress] = React.useState<'approve' | 'reject' | null>(null);

  const handleApprove = async () => {
    setActionInProgress('approve');
    const result = await approveItem();
    if (result.success) {
      toast.success('Item approved');
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to approve item');
    }
    setActionInProgress(null);
  };

  const handleReject = async () => {
    setActionInProgress('reject');
    // TODO: Open modal to collect rejection reason
    const result = await rejectItem('Item rejected');
    if (result.success) {
      toast.success('Item rejected');
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to reject item');
    }
    setActionInProgress(null);
  };

  const isDisabled = isLoading || actionInProgress !== null;

  return (
    <div className="flex gap-1">
      {canApprove && (
        <button
          onClick={handleApprove}
          disabled={isDisabled}
          className={cn(
            'typo-meta px-2 py-1 bg-status-success/20 text-status-success rounded hover:bg-status-success/30',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {actionInProgress === 'approve' ? '...' : 'Approve'}
        </button>
      )}
      {canReject && (
        <button
          onClick={handleReject}
          disabled={isDisabled}
          className={cn(
            'typo-meta px-2 py-1 bg-status-critical/20 text-status-critical rounded hover:bg-status-critical/30',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {actionInProgress === 'reject' ? '...' : 'Reject'}
        </button>
      )}
    </div>
  );
}

export function ShoppingListLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: ShoppingListLensContentProps) {
  // Hooks for list-level actions (no item ID) and permissions
  const { createItem, markOrdered, isLoading } = useShoppingListActions();
  const { canCreate, canApprove, canReject, canMarkOrdered } = useShoppingListPermissions();

  // Track loading state per action type
  const [actionInProgress, setActionInProgress] = React.useState<string | null>(null);

  // Map data
  const title = (data.title as string) || 'Shopping List';
  const status = (data.status as string) || 'pending';
  const requester_name = data.requester_name as string | undefined;
  const approver_name = data.approver_name as string | undefined;
  const created_at = data.created_at as string | undefined;
  const approved_at = data.approved_at as string | undefined;

  // Items from child table
  const items = (data.items as ShoppingListItem[]) || [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // Calculate item counts
  const pendingItems = items.filter(i => i.status === 'candidate' || i.status === 'under_review').length;
  const approvedItems = items.filter(i => i.status === 'approved').length;

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Requester', value: requester_name ?? 'Unknown' },
    { label: 'Approver', value: approver_name ?? 'Pending' },
    { label: 'Created', value: created_at ? formatRelativeTime(created_at) : '—' },
  ];

  // Action handlers
  const handleAddItem = async () => {
    setActionInProgress('create');
    // TODO: Open modal to collect item details
    // For now, show placeholder - in production this would open a form modal
    const result = await createItem({
      description: 'New item',
      quantity: 1,
      unit: 'each',
      priority: 'normal',
    });
    if (result.success) {
      toast.success('Item added to shopping list');
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to add item');
    }
    setActionInProgress(null);
  };

  const handleMarkOrdered = async () => {
    setActionInProgress('order');
    // Mark all approved items as ordered
    const result = await markOrdered({});
    if (result.success) {
      toast.success(`${approvedItems} item${approvedItems === 1 ? '' : 's'} marked as ordered`);
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to mark items as ordered');
    }
    setActionInProgress(null);
  };

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Shopping List" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        <div className="mt-4 flex items-center gap-2 flex-wrap">
          {canCreate && (
            <PrimaryButton
              onClick={handleAddItem}
              disabled={isLoading || actionInProgress === 'create'}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              {actionInProgress === 'create' ? 'Adding...' : 'Add Item'}
            </PrimaryButton>
          )}
          {canMarkOrdered && approvedItems > 0 && (
            <GhostButton
              onClick={handleMarkOrdered}
              disabled={isLoading || actionInProgress === 'order'}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              {actionInProgress === 'order' ? 'Processing...' : `Mark ${approvedItems} as Ordered`}
            </GhostButton>
          )}
        </div>

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No items added yet.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => {
                  const urgencyColor = item.urgency === 'critical' ? 'text-status-critical' :
                                       item.urgency === 'high' ? 'text-status-warning' : 'text-celeste-text-muted';
                  const itemStatusColor = item.status === 'approved' ? 'text-status-success' :
                                          item.status === 'rejected' ? 'text-status-critical' : 'text-celeste-text-muted';
                  const showActions = (item.status === 'candidate' || item.status === 'under_review') && (canApprove || canReject);

                  return (
                    <li key={item.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                      <div>
                        <span className="typo-body text-celeste-text-primary">{item.part_name}</span>
                        <span className="ml-2 typo-body text-celeste-text-muted">
                          × {item.quantity_requested}{item.unit ? ` ${item.unit}` : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        {item.urgency && item.urgency !== 'normal' && (
                          <span className={cn('typo-meta uppercase', urgencyColor)}>{item.urgency}</span>
                        )}
                        <span className={cn('typo-meta uppercase', itemStatusColor)}>
                          {item.status.replace(/_/g, ' ')}
                        </span>
                        {showActions && (
                          <ItemActions
                            item={item}
                            canApprove={canApprove}
                            canReject={canReject}
                            onRefresh={onRefresh}
                          />
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionContainer>
        </div>

        {approved_at && (
          <div className="mt-6">
            <SectionContainer title="Approval" stickyTop={56}>
              <p className="typo-body text-celeste-text-muted">
                Approved {formatRelativeTime(approved_at)}
                {approver_name && ` by ${approver_name}`}
              </p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}
