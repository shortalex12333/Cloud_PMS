/**
 * ApproveShoppingListItemModal Component
 *
 * HOD-only modal for approving shopping list items.
 * Part of SHOP-03 requirement - Shopping List Lens v1.
 *
 * Features:
 * - quantity_approved (defaults to quantity_requested)
 * - approval_notes (optional)
 * - Signature required via SignaturePrompt
 * - react-hook-form + zod validation
 */

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useActionHandler } from '@/hooks/useActionHandler';
import { useAuth } from '@/hooks/useAuth';
import SignaturePrompt from '@/components/celeste/SignaturePrompt';
import {
  CheckCircle,
  ShoppingCart,
  Package,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DiffItem } from '@/components/celeste/MutationPreview';

// ============================================================================
// VALIDATION SCHEMA
// ============================================================================

const approveShoppingListItemSchema = z.object({
  quantity_approved: z.coerce
    .number()
    .positive('Quantity must be greater than 0'),
  approval_notes: z.string().max(1000, 'Notes too long').optional(),
});

type ApproveShoppingListItemFormData = z.infer<typeof approveShoppingListItemSchema>;

// ============================================================================
// TYPES
// ============================================================================

interface ApproveShoppingListItemModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    shopping_list_item_id: string;
    part_name: string;
    quantity_requested: number;
    unit?: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
    source_type?: string;
    requester_name?: string;
  };
  onSuccess?: () => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getUrgencyLabel(urgency?: string): string {
  const labels: Record<string, string> = {
    low: 'Low',
    normal: 'Normal',
    high: 'High',
    critical: 'Critical',
  };
  return labels[urgency || 'normal'] || 'Normal';
}

function getUrgencyColor(urgency?: string): string {
  const colors: Record<string, string> = {
    low: 'text-gray-600 bg-gray-50 border-gray-200',
    normal: 'text-blue-600 bg-blue-50 border-blue-200',
    high: 'text-orange-600 bg-orange-50 border-orange-200',
    critical: 'text-red-600 bg-red-50 border-red-200',
  };
  return colors[urgency || 'normal'] || colors.normal;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ApproveShoppingListItemModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: ApproveShoppingListItemModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const { user } = useAuth();
  const [showSignature, setShowSignature] = useState(false);
  const [formData, setFormData] = useState<ApproveShoppingListItemFormData | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<ApproveShoppingListItemFormData>({
    resolver: zodResolver(approveShoppingListItemSchema) as any,
    defaultValues: {
      quantity_approved: context.quantity_requested,
      approval_notes: '',
    },
  });

  const quantityApproved = watch('quantity_approved');

  // Build diffs for signature preview
  const diffs: DiffItem[] = [
    {
      field: 'Item',
      before: context.part_name,
      after: 'Approved',
    },
    {
      field: 'Quantity',
      before: `${context.quantity_requested} ${context.unit || 'units'} (requested)`,
      after: `${formData?.quantity_approved || quantityApproved || context.quantity_requested} ${context.unit || 'units'} (approved)`,
    },
    {
      field: 'Status',
      before: 'Pending Review',
      after: 'Approved',
    },
  ];

  const onSubmit = (data: ApproveShoppingListItemFormData) => {
    setFormData(data);
    setShowSignature(true);
  };

  const handleSign = async () => {
    if (!formData) return;

    const response = await executeAction(
      'approve_shopping_list_item' as any,
      {
        shopping_list_item_id: context.shopping_list_item_id,
        parameters: {
          quantity_approved: formData.quantity_approved,
          approval_notes: formData.approval_notes || undefined,
          signature: {
            signed_by: user?.id,
            signed_at: new Date().toISOString(),
            signature_type: 'approve',
          },
        },
      },
      {
        successMessage: `${context.part_name} approved for ordering`,
        refreshData: true,
      }
    );

    if (response?.success) {
      setShowSignature(false);
      reset();
      onOpenChange(false);
      onSuccess?.();
    }
  };

  const handleCancel = () => {
    setShowSignature(false);
    setFormData(null);
  };

  const handleClose = () => {
    reset();
    setFormData(null);
    setShowSignature(false);
    onOpenChange(false);
  };

  // Show signature prompt when form is submitted
  if (showSignature) {
    return (
      <SignaturePrompt
        diffs={diffs}
        userName={user?.email || 'User'}
        onSign={handleSign}
        onCancel={handleCancel}
        isCommitting={isLoading}
      />
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            Approve Shopping List Item
          </DialogTitle>
          <DialogDescription>
            Review and approve this item for ordering
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Item Summary */}
          <div className="p-4 bg-[var(--celeste-bg-secondary)] rounded-lg border border-[var(--celeste-border)]">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-[var(--celeste-accent)]/10 rounded-lg">
                <ShoppingCart className="h-5 w-5 text-[var(--celeste-accent)]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-[var(--celeste-text-primary)]">
                  {context.part_name}
                </p>
                <div className="flex items-center gap-2 mt-1 text-sm text-[var(--celeste-text-secondary)]">
                  <Package className="h-4 w-4" />
                  <span>
                    Requested: {context.quantity_requested} {context.unit || 'units'}
                  </span>
                </div>
                {context.requester_name && (
                  <p className="text-xs text-[var(--celeste-text-muted)] mt-1">
                    Requested by {context.requester_name}
                  </p>
                )}
              </div>
            </div>

            {/* Urgency Badge */}
            {context.urgency && context.urgency !== 'normal' && (
              <div
                className={cn(
                  'inline-flex items-center gap-1.5 mt-3 px-2 py-1 rounded-full text-xs font-medium border',
                  getUrgencyColor(context.urgency)
                )}
              >
                {context.urgency === 'critical' && (
                  <AlertTriangle className="h-3 w-3" />
                )}
                {getUrgencyLabel(context.urgency)} Priority
              </div>
            )}
          </div>

          {/* Quantity Approved */}
          <div className="space-y-2">
            <Label htmlFor="quantity_approved">
              Quantity to Approve *
            </Label>
            <div className="flex items-center gap-2">
              <Input
                id="quantity_approved"
                type="number"
                step="0.01"
                min="0.01"
                {...register('quantity_approved')}
                className={cn(
                  'flex-1',
                  errors.quantity_approved ? 'border-red-500' : ''
                )}
              />
              {context.unit && (
                <span className="text-sm text-[var(--celeste-text-muted)] min-w-[60px]">
                  {context.unit}
                </span>
              )}
            </div>
            {quantityApproved !== context.quantity_requested && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Different from requested quantity ({context.quantity_requested})
              </p>
            )}
            {errors.quantity_approved && (
              <p className="text-sm text-red-600">
                {errors.quantity_approved.message}
              </p>
            )}
          </div>

          {/* Approval Notes */}
          <div className="space-y-2">
            <Label htmlFor="approval_notes">
              Approval Notes (optional)
            </Label>
            <Textarea
              id="approval_notes"
              {...register('approval_notes')}
              placeholder="Add any notes about this approval..."
              rows={3}
            />
            {errors.approval_notes && (
              <p className="text-sm text-red-600">
                {errors.approval_notes.message}
              </p>
            )}
          </div>

          {/* Info Box */}
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-700">
              <strong>Note:</strong> Approving this item will allow it to be
              ordered from suppliers. Your signature will be recorded for audit
              purposes.
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Approve & Sign
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default ApproveShoppingListItemModal;
