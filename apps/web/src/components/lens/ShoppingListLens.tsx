'use client';

/**
 * ShoppingListLens - Full-screen entity lens for shopping lists.
 *
 * Per CLAUDE.md and UI_SPEC.md — mirrors WorkOrderLens structure exactly:
 * - Fixed LensHeader (56px): back button, "Shopping List" overline, close button
 * - LensTitleBlock: list title + status pill
 * - VitalSignsRow: 5 indicators (status, items count, requester, approver, created)
 * - Sections: ItemsSection, ApprovalHistorySection (stickyTop={56})
 * - Per-item approval workflow: HOD+ can approve/reject each item individually
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * Status colour mappers are local to this lens (domain-specific logic).
 *
 * FE-03-05: Shopping List Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';

// Sections
import { ItemsSection } from './shopping-sections/ItemsSection';
import { ApprovalHistorySection } from './shopping-sections/ApprovalHistorySection';

// Action modals (reuse existing modals from /components/modals/)
import { CreateShoppingListItemModal } from '@/components/modals/CreateShoppingListItemModal';
import { ApproveShoppingListItemModal } from '@/components/modals/ApproveShoppingListItemModal';
import { RejectShoppingListItemModal } from '@/components/modals/RejectShoppingListItemModal';

// Action hook + permissions
import { useShoppingListActions, useShoppingListPermissions } from '@/hooks/useShoppingListActions';

// Shared UI
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// Re-export ShoppingListItemData so pages can use it
export type { ShoppingListItemData } from '@/components/cards/ShoppingListCard';
import type { ShoppingListItemData } from '@/components/cards/ShoppingListCard';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface ShoppingListLensData {
  id: string;
  /** Human-readable title e.g. "Monthly Engine Room Restock" */
  title?: string;
  /** Status: pending | approved | rejected | ordered */
  status: string;
  /** Crew member who created the shopping list */
  requester_name?: string;
  requester_id?: string;
  /** HOD who approved/rejected the list, or null if pending */
  approver_name?: string;
  approver_id?: string;
  /** ISO timestamp of record creation */
  created_at: string;
  /** ISO timestamp of most recent approval action */
  approved_at?: string;
  /** List items (per-item approval workflow) */
  items?: ShoppingListItemData[];
  /** Audit log entries for the shopping list */
  history?: ShoppingListAuditEntry[];
}

export interface ShoppingListAuditEntry {
  id: string;
  action: string;
  actor_name?: string;
  actor_id?: string;
  timestamp: string;
  details?: string;
  /** Item name affected (for per-item actions) */
  item_name?: string;
}

export interface ShoppingListLensProps {
  /** The shopping list data to render */
  shoppingList: ShoppingListLensData;
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
// Colour mapping helpers
// ---------------------------------------------------------------------------

/**
 * Map shopping list status string to StatusPill color level.
 * Per UI_SPEC.md status colour mapping.
 */
function mapStatusToColor(
  status: string
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected':
      return 'critical';
    case 'pending':
      return 'warning';
    case 'approved':
      return 'success';
    case 'ordered':
      return 'success';
    default:
      return 'neutral';
  }
}

/**
 * Format a shopping list status enum to human-readable label.
 */
function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: 'Pending Review',
    approved: 'Approved',
    rejected: 'Rejected',
    ordered: 'Ordered',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Approve/Reject modal context type
// ---------------------------------------------------------------------------

interface ItemActionContext {
  shopping_list_item_id: string;
  part_name: string;
  quantity_requested: number;
  unit?: string;
  urgency?: 'low' | 'normal' | 'high' | 'critical';
  requester_name?: string;
}

// ---------------------------------------------------------------------------
// ShoppingListLens component
// ---------------------------------------------------------------------------

/**
 * ShoppingListLens — Full-screen entity lens for shopping lists.
 *
 * Usage:
 * ```tsx
 * <ShoppingListLens
 *   shoppingList={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const ShoppingListLens = React.forwardRef<
  HTMLDivElement,
  ShoppingListLensProps
>(({ shoppingList, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility — create item
  const [createItemOpen, setCreateItemOpen] = React.useState(false);

  // Per-item approval/rejection modals
  const [approveContext, setApproveContext] = React.useState<ItemActionContext | null>(null);
  const [rejectContext, setRejectContext] = React.useState<ItemActionContext | null>(null);

  // Actions and permissions
  const actions = useShoppingListActions(shoppingList.id);
  const perms = useShoppingListPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // Derived display values
  const displayTitle = shoppingList.title ?? 'Shopping List';
  const statusColor = mapStatusToColor(shoppingList.status);
  const statusLabel = formatStatusLabel(shoppingList.status);

  // Item counts
  const items = shoppingList.items ?? [];
  const totalItems = items.length;
  const pendingItems = items.filter(
    (i) => i.status === 'candidate' || i.status === 'under_review'
  ).length;
  const approvedItems = items.filter((i) => i.status === 'approved').length;

  // Build the 5 vital signs as per plan spec
  const vitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: statusLabel,
      color: statusColor,
    },
    {
      label: 'Items',
      value: totalItems === 1 ? '1 item' : `${totalItems} items`,
    },
    {
      label: 'Requester',
      value: shoppingList.requester_name ?? 'Unknown',
    },
    {
      label: 'Approver',
      value: shoppingList.approver_name ?? 'Pending',
    },
    {
      label: 'Created',
      value: shoppingList.created_at
        ? formatRelativeTime(shoppingList.created_at)
        : '—',
    },
  ];

  // History entries
  const history = shoppingList.history ?? [];

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

  // Per-item approve handler — opens modal with context
  const handleApproveItem = React.useCallback((item: ShoppingListItemData) => {
    setApproveContext({
      shopping_list_item_id: item.id,
      part_name: item.part_name,
      quantity_requested: item.quantity_requested,
      unit: item.unit,
      urgency: item.urgency,
      requester_name: item.created_by_name,
    });
  }, []);

  // Per-item reject handler — opens modal with context
  const handleRejectItem = React.useCallback((item: ShoppingListItemData) => {
    setRejectContext({
      shopping_list_item_id: item.id,
      part_name: item.part_name,
      quantity_requested: item.quantity_requested,
      unit: item.unit,
      urgency: item.urgency,
      requester_name: item.created_by_name,
    });
  }, []);

  // Mark ordered — fires action for each approved item
  const handleMarkOrdered = React.useCallback(async () => {
    const approvedIds = items
      .filter((i) => i.status === 'approved')
      .map((i) => i.id);

    for (const itemId of approvedIds) {
      await actions.markOrdered(itemId);
    }
    onRefresh?.();
  }, [items, actions, onRefresh]);

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Shopping List"
        title={displayTitle}
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
        {/* ---------------------------------------------------------------
            Title block: title + status pill
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            status={{
              label: statusLabel,
              color: statusColor,
            }}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Header action buttons
            - Crew can add items (canCreateItem)
            - HOD+ can mark ordered if there are approved items
            Hidden, not disabled, per UI_SPEC.md
            --------------------------------------------------------------- */}
        {(perms.canCreateItem || (perms.canMarkOrdered && approvedItems > 0)) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {perms.canCreateItem && (
              <PrimaryButton
                onClick={() => setCreateItemOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Add Item
              </PrimaryButton>
            )}
            {perms.canMarkOrdered && approvedItems > 0 && (
              <GhostButton
                onClick={handleMarkOrdered}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Mark {approvedItems} Approved {approvedItems === 1 ? 'Item' : 'Items'} as Ordered
              </GhostButton>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px per spec
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Items Section — per-item approve/reject for HOD+
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <ItemsSection
            items={items}
            isHoD={perms.canApproveItem}
            onApproveItem={handleApproveItem}
            onRejectItem={handleRejectItem}
            onAddItem={perms.canCreateItem ? () => setCreateItemOpen(true) : undefined}
            pendingCount={pendingItems}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Approval History Section — read-only audit log
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <ApprovalHistorySection history={history} stickyTop={56} />
        </div>
      </main>

      {/* ---------------------------------------------------------------
          Action Modals — rendered at lens root for correct z-index stacking
          --------------------------------------------------------------- */}

      <CreateShoppingListItemModal
        open={createItemOpen}
        onOpenChange={setCreateItemOpen}
        onSuccess={() => {
          setCreateItemOpen(false);
          onRefresh?.();
        }}
      />

      {approveContext && (
        <ApproveShoppingListItemModal
          open={!!approveContext}
          onOpenChange={(open) => { if (!open) setApproveContext(null); }}
          context={approveContext}
          onSuccess={() => {
            setApproveContext(null);
            onRefresh?.();
          }}
        />
      )}

      {rejectContext && (
        <RejectShoppingListItemModal
          open={!!rejectContext}
          onOpenChange={(open) => { if (!open) setRejectContext(null); }}
          context={rejectContext}
          onSuccess={() => {
            setRejectContext(null);
            onRefresh?.();
          }}
        />
      )}
    </LensContainer>
  );
});

ShoppingListLens.displayName = 'ShoppingListLens';

export default ShoppingListLens;
