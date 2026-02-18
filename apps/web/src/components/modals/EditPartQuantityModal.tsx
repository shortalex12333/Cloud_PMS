/**
 * EditPartQuantityModal Component
 *
 * Modal for adjusting part stock quantities with audit logging
 * Supports various adjustment types and requires justification
 * Phase 4 - Priority 2: Audit-Sensitive EDIT Modals
 */

'use client';

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import { Package, AlertTriangle, FileText } from 'lucide-react';

// Validation schema
const editPartQuantitySchema = z.object({
  part_id: z.string().min(1, 'Part ID is required'),
  old_quantity: z.coerce.number(),
  new_quantity: z.coerce.number().min(0, 'Quantity cannot be negative'),
  adjustment_type: z.enum(['addition', 'correction', 'write_off', 'return']),
  adjustment_reason: z.string().min(10, 'Reason must be at least 10 characters'),
});

type EditPartQuantityFormData = z.infer<typeof editPartQuantitySchema>;

interface EditPartQuantityModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    part_id: string;
    part_name: string;
    part_number: string;
    current_quantity: number;
    min_stock_level: number;
  };
  onSuccess?: () => void;
}

export function EditPartQuantityModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditPartQuantityModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<EditPartQuantityFormData>({
    resolver: zodResolver(editPartQuantitySchema) as any,
    defaultValues: {
      part_id: context.part_id,
      old_quantity: context.current_quantity,
      new_quantity: context.current_quantity,
      adjustment_type: 'correction',
      adjustment_reason: '',
    },
  });

  const newQuantity = watch('new_quantity');
  const adjustmentType = watch('adjustment_type');

  const difference = newQuantity - context.current_quantity;
  const absoluteDifference = Math.abs(difference);
  const isIncrease = difference > 0;
  const isDecrease = difference < 0;
  const noChange = difference === 0;

  const willBeLowStock = newQuantity < context.min_stock_level;
  const willBeOutOfStock = newQuantity === 0;

  const onSubmit = async (data: EditPartQuantityFormData) => {
    const response = await executeAction(
      'edit_part_quantity',
      data,
      {
        successMessage: `Stock quantity updated: ${context.part_name} (${context.current_quantity} → ${data.new_quantity})`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess();
      }
    }
  };

  const getAdjustmentTypeLabel = (type: string) => {
    switch (type) {
      case 'addition':
        return 'Addition - Received new stock';
      case 'correction':
        return 'Correction - Fix inventory error';
      case 'write_off':
        return 'Write-off - Damaged/expired/lost';
      case 'return':
        return 'Return - Returned to supplier';
      default:
        return type;
    }
  };

  const getChangeColor = () => {
    if (isIncrease) return 'text-green-700';
    if (isDecrease) return 'text-orange-700';
    return 'text-celeste-text-secondary';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-celeste-accent" />
            Adjust Stock Quantity
          </DialogTitle>
          <DialogDescription>
            Adjust inventory quantity for this part. All changes are logged for audit purposes.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Part Information */}
          <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg space-y-2">
            <h3 className="font-semibold text-celeste-accent flex items-center gap-2">
              <Package className="h-4 w-4" />
              {context.part_name}
            </h3>
            <p className="text-sm text-celeste-accent">P/N: {context.part_number}</p>
            <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-celeste-accent-line">
              <div>
                <p className="text-xs text-celeste-accent">Min Stock Level</p>
                <p className="text-lg font-bold text-celeste-accent">{context.min_stock_level}</p>
              </div>
              <div>
                <p className="text-xs text-celeste-accent">Current Stock</p>
                <p className="text-lg font-bold text-celeste-accent">{context.current_quantity}</p>
              </div>
            </div>
          </div>

          {/* Adjustment Type */}
          <div className="space-y-2">
            <Label htmlFor="adjustment_type">
              Adjustment Type <span className="text-red-500">*</span>
            </Label>
            <Select
              value={adjustmentType}
              onValueChange={(value) => setValue('adjustment_type', value as any)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="addition">{getAdjustmentTypeLabel('addition')}</SelectItem>
                <SelectItem value="correction">{getAdjustmentTypeLabel('correction')}</SelectItem>
                <SelectItem value="write_off">{getAdjustmentTypeLabel('write_off')}</SelectItem>
                <SelectItem value="return">{getAdjustmentTypeLabel('return')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Quantities */}
          <div className="grid grid-cols-2 gap-4">
            {/* Current Quantity (Read-Only) */}
            <div className="space-y-2">
              <Label htmlFor="old_quantity">Current Quantity</Label>
              <Input
                id="old_quantity"
                type="number"
                {...register('old_quantity')}
                readOnly
                className="bg-celeste-bg-secondary cursor-not-allowed"
              />
            </div>

            {/* New Quantity */}
            <div className="space-y-2">
              <Label htmlFor="new_quantity">
                New Quantity <span className="text-red-500">*</span>
              </Label>
              <Input
                id="new_quantity"
                type="number"
                min="0"
                {...register('new_quantity')}
                className={errors.new_quantity ? 'border-red-500' : ''}
              />
              {errors.new_quantity && (
                <p className="text-sm text-red-600">{errors.new_quantity.message}</p>
              )}
            </div>
          </div>

          {/* Change Summary */}
          {!noChange && (
            <div className={`p-4 border rounded-lg ${
              willBeOutOfStock
                ? 'bg-red-50 border-red-300'
                : willBeLowStock
                ? 'bg-orange-50 border-orange-300'
                : 'bg-celeste-accent-subtle border-celeste-accent-line'
            }`}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Change:</span>
                  <span className={`text-lg font-bold ${getChangeColor()}`}>
                    {isIncrease && '+'}
                    {difference} units
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">New Stock:</span>
                  <span className={`text-lg font-bold ${getChangeColor()}`}>
                    {newQuantity} units
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Stock Warnings */}
          {!noChange && (
            <>
              {willBeOutOfStock && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-red-900">Stock will be depleted</p>
                    <p className="text-sm text-red-700">
                      This adjustment will result in zero stock. Consider ordering more immediately.
                    </p>
                  </div>
                </div>
              )}
              {willBeLowStock && !willBeOutOfStock && (
                <div className="flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-orange-900">Stock will be low</p>
                    <p className="text-sm text-orange-700">
                      New stock ({newQuantity}) will be below minimum level ({context.min_stock_level}).
                      Consider reordering soon.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Reason (REQUIRED) */}
          <div className="space-y-2">
            <Label htmlFor="adjustment_reason">
              Reason for Adjustment <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="adjustment_reason"
              {...register('adjustment_reason')}
              placeholder="Provide a detailed explanation for this stock adjustment. Include what caused the discrepancy and any relevant details..."
              rows={4}
              className={errors.adjustment_reason ? 'border-red-500' : ''}
            />
            {errors.adjustment_reason && (
              <p className="text-sm text-red-600">{errors.adjustment_reason.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              This reason will be permanently recorded in the audit log with MEDIUM severity.
            </p>
          </div>

          {/* Audit Notice */}
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-sm text-yellow-800">
              📋 This adjustment will create an audit log entry with details of the quantity change,
              adjustment type, and your justification.
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || noChange}>
              {isLoading ? 'Updating...' : 'Save Adjustment'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
