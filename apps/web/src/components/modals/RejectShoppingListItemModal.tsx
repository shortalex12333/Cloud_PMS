/**
 * RejectShoppingListItemModal Component
 *
 * HOD-only modal for rejecting shopping list items.
 * Part of SHOP-03 requirement - Shopping List Lens v1.
 *
 * Features:
 * - rejection_reason (required)
 * - rejection_notes (optional)
 * - No signature required (per spec)
 * - react-hook-form + zod validation
 */

'use client';

import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  XCircle,
  ShoppingCart,
  Package,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// VALIDATION SCHEMA
// ============================================================================

const rejectShoppingListItemSchema = z.object({
  rejection_reason: z
    .string()
    .min(1, 'Rejection reason is required'),
  rejection_notes: z.string().max(1000, 'Notes too long').optional(),
});

type RejectShoppingListItemFormData = z.infer<typeof rejectShoppingListItemSchema>;

// ============================================================================
// TYPES
// ============================================================================

interface RejectShoppingListItemModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    shopping_list_item_id: string;
    part_name: string;
    quantity_requested: number;
    unit?: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
    requester_name?: string;
  };
  onSuccess?: () => void;
}

// ============================================================================
// REJECTION REASONS
// ============================================================================

const REJECTION_REASONS = [
  {
    value: 'not_needed',
    label: 'Not Needed',
    description: 'Item is not required at this time',
  },
  {
    value: 'budget_constraints',
    label: 'Budget Constraints',
    description: 'Insufficient budget allocation',
  },
  {
    value: 'duplicate_request',
    label: 'Duplicate Request',
    description: 'Already requested or on order',
  },
  {
    value: 'wrong_specification',
    label: 'Wrong Specification',
    description: 'Incorrect part specifications',
  },
  {
    value: 'alternative_available',
    label: 'Alternative Available',
    description: 'A suitable alternative exists',
  },
  {
    value: 'insufficient_justification',
    label: 'Insufficient Justification',
    description: 'Need more details or justification',
  },
  {
    value: 'vendor_issue',
    label: 'Vendor Issue',
    description: 'Supplier not approved or unavailable',
  },
  {
    value: 'other',
    label: 'Other',
    description: 'See notes for details',
  },
] as const;

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

export function RejectShoppingListItemModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: RejectShoppingListItemModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors },
  } = useForm<RejectShoppingListItemFormData>({
    resolver: zodResolver(rejectShoppingListItemSchema) as any,
    defaultValues: {
      rejection_reason: '',
      rejection_notes: '',
    },
  });

  const rejectionReason = watch('rejection_reason');

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      reset({
        rejection_reason: '',
        rejection_notes: '',
      });
    }
  }, [open, reset]);

  const onSubmit = async (data: RejectShoppingListItemFormData) => {
    const response = await executeAction(
      'reject_shopping_list_item' as any,
      {
        shopping_list_item_id: context.shopping_list_item_id,
        parameters: {
          rejection_reason: data.rejection_reason,
          rejection_notes: data.rejection_notes || undefined,
        },
      },
      {
        successMessage: `${context.part_name} has been rejected`,
        refreshData: true,
      }
    );

    if (response?.success) {
      reset();
      onOpenChange(false);
      onSuccess?.();
    }
  };

  const handleClose = () => {
    reset();
    onOpenChange(false);
  };

  // Get selected reason details for display
  const selectedReason = REJECTION_REASONS.find(r => r.value === rejectionReason);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-600" />
            Reject Shopping List Item
          </DialogTitle>
          <DialogDescription>
            Provide a reason for rejecting this request
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Item Summary */}
          <div className="p-4 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <ShoppingCart className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-red-900">
                  {context.part_name}
                </p>
                <div className="flex items-center gap-2 mt-1 typo-body text-red-700">
                  <Package className="h-4 w-4" />
                  <span>
                    Requested: {context.quantity_requested} {context.unit || 'units'}
                  </span>
                </div>
                {context.requester_name && (
                  <p className="typo-meta text-red-600 mt-1">
                    Requested by {context.requester_name}
                  </p>
                )}
              </div>
            </div>

            {/* Urgency Badge */}
            {context.urgency && context.urgency !== 'normal' && (
              <div
                className={cn(
                  'inline-flex items-center gap-1.5 mt-3 px-2 py-1 rounded-full typo-meta font-medium border',
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

          {/* Rejection Reason (Required) */}
          <div className="space-y-2">
            <Label htmlFor="rejection_reason">
              Rejection Reason *
            </Label>
            <Controller
              name="rejection_reason"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger
                    id="rejection_reason"
                    className={errors.rejection_reason ? 'border-red-500' : ''}
                  >
                    <SelectValue placeholder="Select a reason..." />
                  </SelectTrigger>
                  <SelectContent>
                    {REJECTION_REASONS.map((reason) => (
                      <SelectItem key={reason.value} value={reason.value}>
                        <div className="flex flex-col">
                          <span className="font-medium">{reason.label}</span>
                          <span className="typo-meta text-txt-tertiary">
                            {reason.description}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.rejection_reason && (
              <p className="typo-body text-red-600">
                {errors.rejection_reason.message}
              </p>
            )}
            {selectedReason && (
              <p className="typo-meta text-txt-tertiary">
                {selectedReason.description}
              </p>
            )}
          </div>

          {/* Rejection Notes (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="rejection_notes">
              Additional Notes {rejectionReason === 'other' ? '*' : '(optional)'}
            </Label>
            <Textarea
              id="rejection_notes"
              {...register('rejection_notes')}
              placeholder={
                rejectionReason === 'other'
                  ? 'Please explain the reason for rejection...'
                  : 'Add any additional details or guidance for the requester...'
              }
              rows={3}
              className={
                rejectionReason === 'other' && !watch('rejection_notes')
                  ? 'border-amber-400'
                  : ''
              }
            />
            {rejectionReason === 'other' && !watch('rejection_notes') && (
              <p className="typo-meta text-amber-600">
                Please provide details when selecting "Other"
              </p>
            )}
            {errors.rejection_notes && (
              <p className="typo-body text-red-600">
                {errors.rejection_notes.message}
              </p>
            )}
          </div>

          {/* Warning Box */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5" />
              <div className="typo-body text-amber-700">
                <p className="font-medium">This action cannot be undone</p>
                <p className="typo-meta mt-1">
                  The requester will be notified of the rejection and reason provided.
                </p>
              </div>
            </div>
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
              disabled={isLoading || !rejectionReason}
              className="bg-red-600 hover:bg-red-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Rejecting...
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Reject Request
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default RejectShoppingListItemModal;
