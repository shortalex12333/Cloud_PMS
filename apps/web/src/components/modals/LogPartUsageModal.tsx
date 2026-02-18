/**
 * LogPartUsageModal Component
 *
 * Modal for logging part consumption/usage
 * Links parts to work orders and updates stock levels
 * High-priority CREATE action for Phase 4
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import { Package, AlertCircle, CheckCircle2 } from 'lucide-react';

// Validation schema
const logPartUsageSchema = z.object({
  part_id: z.string().min(1, 'Part ID is required'),
  work_order_id: z.string().min(1, 'Work order must be selected'),
  quantity_used: z.coerce.number().min(1, 'Quantity must be at least 1'),
  notes: z.string().optional(),
});

type LogPartUsageFormData = z.infer<typeof logPartUsageSchema>;

interface LogPartUsageModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    part_id: string;
    part_name: string;
    part_number: string;
    current_stock: number;
    min_stock_level: number;
    work_order_id?: string;
    work_order_title?: string;
  };
  onSuccess?: () => void;
}

export function LogPartUsageModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: LogPartUsageModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [showStockWarning, setShowStockWarning] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<LogPartUsageFormData>({
    resolver: zodResolver(logPartUsageSchema) as any,
    defaultValues: {
      part_id: context.part_id,
      work_order_id: context.work_order_id || '',
      quantity_used: 1,
      notes: '',
    },
  });

  const quantityUsed = watch('quantity_used');

  const remainingStock = context.current_stock - quantityUsed;
  const willBeLowStock = remainingStock < context.min_stock_level;
  const willBeOutOfStock = remainingStock <= 0;
  const exceedsStock = quantityUsed > context.current_stock;

  const onSubmit = async (data: LogPartUsageFormData) => {
    // Validate stock availability
    if (exceedsStock) {
      setShowStockWarning(true);
      return;
    }

    const response = await executeAction(
      'log_part_usage',
      data,
      {
        successMessage: `Part usage logged: ${data.quantity_used} × ${context.part_name}`,
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-celeste-accent" />
            Log Part Usage
          </DialogTitle>
          <DialogDescription>
            Record the consumption of parts for maintenance work. Stock levels will be
            updated automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Part Information */}
          <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg space-y-2">
            <h3 className="font-semibold text-celeste-accent flex items-center gap-2">
              <Package className="h-4 w-4" />
              {context.part_name}
            </h3>
            <p className="text-sm text-celeste-accent">
              P/N: {context.part_number}
            </p>

            {/* Current Stock */}
            <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-celeste-accent-line">
              <div>
                <p className="text-xs text-celeste-accent">Available</p>
                <p className="text-lg font-bold text-celeste-accent">
                  {context.current_stock}
                </p>
              </div>
              <div>
                <p className="text-xs text-celeste-accent">Min Level</p>
                <p className="text-lg font-bold text-celeste-accent">
                  {context.min_stock_level}
                </p>
              </div>
              <div>
                <p className="text-xs text-celeste-accent">After Usage</p>
                <p className={`text-lg font-bold ${
                  willBeOutOfStock
                    ? 'text-red-700'
                    : willBeLowStock
                    ? 'text-orange-700'
                    : 'text-green-700'
                }`}>
                  {Math.max(remainingStock, 0)}
                </p>
              </div>
            </div>
          </div>

          {/* Work Order (if pre-selected) */}
          {context.work_order_title && (
            <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-md">
              <p className="text-sm font-medium text-celeste-black">
                Work Order: {context.work_order_title}
              </p>
            </div>
          )}

          {/* Usage Details */}
          <div className="space-y-4">
            {/* Work Order Selection */}
            {!context.work_order_id && (
              <div className="space-y-2">
                <Label htmlFor="work_order_id">
                  Work Order <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={watch('work_order_id')}
                  onValueChange={(value) => setValue('work_order_id', value)}
                >
                  <SelectTrigger className={errors.work_order_id ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Select work order..." />
                  </SelectTrigger>
                  <SelectContent>
                    {/* These would come from an API call in production */}
                    <SelectItem value="wo-001">WO-001: Engine Maintenance</SelectItem>
                    <SelectItem value="wo-002">WO-002: HVAC Repair</SelectItem>
                    <SelectItem value="wo-003">WO-003: Electrical Issue</SelectItem>
                    <SelectItem value="general">General Maintenance (No WO)</SelectItem>
                  </SelectContent>
                </Select>
                {errors.work_order_id && (
                  <p className="text-sm text-red-600">{errors.work_order_id.message}</p>
                )}
              </div>
            )}

            {/* Quantity Used */}
            <div className="space-y-2">
              <Label htmlFor="quantity_used">
                Quantity Used <span className="text-red-500">*</span>
              </Label>
              <Input
                id="quantity_used"
                type="number"
                min="1"
                max={context.current_stock}
                {...register('quantity_used')}
                className={errors.quantity_used || exceedsStock ? 'border-red-500' : ''}
              />
              {errors.quantity_used && (
                <p className="text-sm text-red-600">{errors.quantity_used.message}</p>
              )}
              {exceedsStock && (
                <p className="text-sm text-red-600">
                  ⚠️ Quantity exceeds available stock ({context.current_stock} available)
                </p>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                {...register('notes')}
                placeholder="Optional: Details about the usage, reason, or any observations..."
                rows={3}
              />
            </div>
          </div>

          {/* Stock Warnings */}
          {!exceedsStock && quantityUsed > 0 && (
            <>
              {willBeOutOfStock && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-red-900">Stock will be depleted</p>
                    <p className="text-sm text-red-700">
                      This usage will result in zero stock. Consider ordering more immediately.
                    </p>
                  </div>
                </div>
              )}
              {willBeLowStock && !willBeOutOfStock && (
                <div className="flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-orange-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-orange-900">Stock will be low</p>
                    <p className="text-sm text-orange-700">
                      Remaining stock ({remainingStock}) will be below minimum level ({context.min_stock_level}).
                      Consider reordering soon.
                    </p>
                  </div>
                </div>
              )}
              {!willBeLowStock && (
                <div className="flex items-start gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-green-900">Stock levels OK</p>
                    <p className="text-sm text-green-700">
                      Remaining stock ({remainingStock}) will be above minimum level.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Exceeded Stock Warning Modal State */}
          {showStockWarning && (
            <div className="p-4 bg-red-100 border-2 border-red-500 rounded-lg">
              <p className="font-semibold text-red-900">Cannot proceed with this quantity</p>
              <p className="text-sm text-red-700 mt-1">
                The requested quantity ({quantityUsed}) exceeds available stock ({context.current_stock}).
                Please adjust the quantity or check inventory.
              </p>
            </div>
          )}

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
            <Button
              type="submit"
              disabled={isLoading || exceedsStock}
            >
              {isLoading ? 'Logging Usage...' : 'Log Usage'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
