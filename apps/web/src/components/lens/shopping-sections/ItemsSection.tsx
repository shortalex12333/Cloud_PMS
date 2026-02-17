'use client';

/**
 * ItemsSection - Shopping list items with per-item approval actions.
 *
 * Used inside ShoppingListLens.
 *
 * Features:
 * - Renders each ShoppingListItemData with ShoppingListCard
 * - Part link rendered inside card (EntityLink to /parts/[id]) when part_id exists
 * - HOD+ sees Approve / Reject buttons per pending item
 * - "Add Item" CTA shown for users with canCreateItem permission
 * - Empty state handled gracefully
 *
 * FE-03-05: Shopping List Lens Rebuild
 */

import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { ShoppingListCard } from '@/components/cards/ShoppingListCard';
import type { ShoppingListItemData } from '@/components/cards/ShoppingListCard';
import { GhostButton } from '@/components/ui/GhostButton';
import { ShoppingCart } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface ItemsSectionProps {
  items: ShoppingListItemData[];
  /** Whether the current user is a HOD (can approve/reject) */
  isHoD: boolean;
  /** Called when HOD clicks Approve on a specific item */
  onApproveItem?: (item: ShoppingListItemData) => void;
  /** Called when HOD clicks Reject on a specific item */
  onRejectItem?: (item: ShoppingListItemData) => void;
  /** Called when user clicks "Add Item" (only shown if provided) */
  onAddItem?: () => void;
  /** Count of pending items — shown in section badge */
  pendingCount?: number;
  /** Top offset for sticky header (56 when inside lens) */
  stickyTop?: number;
}

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * ItemsSection — Displays shopping list items with per-item approval actions.
 *
 * Delegates rendering to ShoppingListCard which already handles:
 * - Part link (EntityLink to /parts/[id]) when part_id is set
 * - Approval/rejection UI based on isHoD prop
 * - Status pills, urgency badges, candidate part badges
 */
export function ItemsSection({
  items,
  isHoD,
  onApproveItem,
  onRejectItem,
  onAddItem,
  pendingCount = 0,
  stickyTop = 0,
}: ItemsSectionProps) {
  // Section action button — "Add Item" for crew
  const sectionAction =
    onAddItem != null
      ? { label: 'Add Item', onClick: onAddItem }
      : undefined;

  // Section count badge: show pending count when reviewing, total otherwise
  const badgeCount = items.length > 0 ? items.length : undefined;

  return (
    <SectionContainer
      title="Items"
      count={badgeCount}
      action={sectionAction}
      stickyTop={stickyTop}
    >
      {items.length === 0 ? (
        /* Empty state */
        <div className="py-10 flex flex-col items-center gap-2 text-txt-secondary">
          <ShoppingCart
            className="w-8 h-8 opacity-30"
            aria-hidden="true"
          />
          <p className="text-[14px]">No items yet</p>
          {onAddItem && (
            <GhostButton
              onClick={onAddItem}
              className="mt-2 text-[13px]"
            >
              Add the first item
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Pending review banner for HOD */}
          {isHoD && pendingCount > 0 && (
            <div
              role="status"
              aria-live="polite"
              className="px-3 py-2 rounded-[var(--radius-sm)] bg-status-warning/10 border border-status-warning/30 text-[13px] text-status-warning"
            >
              {pendingCount} {pendingCount === 1 ? 'item requires' : 'items require'} your review
            </div>
          )}

          {/* Item cards */}
          {items.map((item) => (
            <ShoppingListCard
              key={item.id}
              item={item}
              isHoD={isHoD}
              onApprove={
                onApproveItem ? () => onApproveItem(item) : undefined
              }
              onReject={
                onRejectItem ? () => onRejectItem(item) : undefined
              }
            />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}
