/**
 * Shopping List Actions Hook
 *
 * Provides action handlers for shopping list operations:
 * - create_shopping_list_item (All crew)
 * - approve_shopping_list_item (HoD only)
 * - reject_shopping_list_item (HoD only)
 * - promote_candidate_to_part (Engineers only)
 * - view_item_history (All crew)
 * - link_to_work_order (All crew - navigation)
 */

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isEngineer } from '@/contexts/AuthContext';
import { executeAction } from '@/lib/actionClient';
import type { CreateShoppingListItemPayload } from '../types';

export interface UseShoppingListActionsOptions {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export function useShoppingListActions(options: UseShoppingListActionsOptions = {}) {
  const { user } = useAuth();
  const router = useRouter();
  const { onSuccess, onError } = options;

  // Role checks
  const canApproveReject = isHOD(user);
  const canPromoteToPart = isEngineer(user);
  const canCreateItem = !!user; // All crew can create items

  // Action: Create Shopping List Item (All crew)
  const createItem = useCallback(
    async (payload: CreateShoppingListItemPayload) => {
      if (!user?.yachtId) {
        const error = new Error('No yacht context available');
        onError?.(error);
        throw error;
      }

      try {
        const result = await executeAction(
          'create_shopping_list_item',
          { yacht_id: user.yachtId },
          {
            ...payload,
            source_type: payload.source_type || 'manual_add',
          }
        );
        onSuccess?.();
        return result;
      } catch (error) {
        console.error('[useShoppingListActions] Create item failed:', error);
        onError?.(error as Error);
        throw error;
      }
    },
    [user?.yachtId, onSuccess, onError]
  );

  // Action: Approve Shopping List Item (HoD only)
  const approveItem = useCallback(
    async (itemId: string, quantityApproved?: number, approvalNotes?: string) => {
      if (!user?.yachtId || !canApproveReject) {
        const error = new Error('Not authorized to approve items');
        onError?.(error);
        throw error;
      }

      try {
        const result = await executeAction(
          'approve_shopping_list_item',
          { yacht_id: user.yachtId, shopping_list_item_id: itemId },
          {
            ...(quantityApproved !== undefined && { quantity_approved: quantityApproved }),
            ...(approvalNotes && { approval_notes: approvalNotes }),
          }
        );
        onSuccess?.();
        return result;
      } catch (error) {
        console.error('[useShoppingListActions] Approve item failed:', error);
        onError?.(error as Error);
        throw error;
      }
    },
    [user?.yachtId, canApproveReject, onSuccess, onError]
  );

  // Action: Reject Shopping List Item (HoD only)
  const rejectItem = useCallback(
    async (itemId: string, rejectionReason: string, rejectionNotes?: string) => {
      if (!user?.yachtId || !canApproveReject) {
        const error = new Error('Not authorized to reject items');
        onError?.(error);
        throw error;
      }

      try {
        const result = await executeAction(
          'reject_shopping_list_item',
          { yacht_id: user.yachtId, shopping_list_item_id: itemId },
          {
            rejection_reason: rejectionReason,
            ...(rejectionNotes && { rejection_notes: rejectionNotes }),
          }
        );
        onSuccess?.();
        return result;
      } catch (error) {
        console.error('[useShoppingListActions] Reject item failed:', error);
        onError?.(error as Error);
        throw error;
      }
    },
    [user?.yachtId, canApproveReject, onSuccess, onError]
  );

  // Action: Promote Candidate to Part (Engineers only)
  const promoteToPart = useCallback(
    async (itemId: string) => {
      if (!user?.yachtId || !canPromoteToPart) {
        const error = new Error('Not authorized to promote items to parts');
        onError?.(error);
        throw error;
      }

      try {
        const result = await executeAction(
          'promote_candidate_to_part',
          { yacht_id: user.yachtId, shopping_list_item_id: itemId },
          {}
        );
        onSuccess?.();
        return result;
      } catch (error) {
        console.error('[useShoppingListActions] Promote to part failed:', error);
        onError?.(error as Error);
        throw error;
      }
    },
    [user?.yachtId, canPromoteToPart, onSuccess, onError]
  );

  // Action: Link to Work Order (Navigation - All crew)
  const linkToWorkOrder = useCallback(
    (workOrderId: string) => {
      if (!workOrderId) {
        console.warn('[useShoppingListActions] No work order ID provided');
        return;
      }
      router.push(`/work-orders?id=${workOrderId}`);
    },
    [router]
  );

  return {
    // Actions
    createItem,
    approveItem,
    rejectItem,
    promoteToPart,
    linkToWorkOrder,

    // Role permissions
    canCreateItem,
    canApproveReject,
    canPromoteToPart,
  };
}
