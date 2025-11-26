// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * OrderPartModal Component
 *
 * Modal for ordering parts from suppliers
 * Shows current stock levels and calculates estimated cost
 * High-priority CREATE action for Phase 4
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
import { ShoppingCart, Package, AlertTriangle } from 'lucide-react';

// Validation schema
const orderPartSchema = z.object({
  part_id: z.string().min(1, 'Part ID is required'),
  quantity: z.coerce.number().min(1, 'Quantity must be at least 1'),
  supplier: z.string().min(1, 'Supplier is required'),
  expected_delivery: z.string().optional(),
  notes: z.string().optional(),
  urgency: z.enum(['normal', 'urgent', 'critical']).optional(),
});

type OrderPartFormData = z.infer<typeof orderPartSchema>;

interface OrderPartModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    part_id: string;
    part_name: string;
    part_number: string;
    current_stock: number;
    min_stock_level: number;
    unit_cost?: number;
    default_supplier?: string;
  };
  onSuccess?: (order_id: string) => void;
}

export function OrderPartModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: OrderPartModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<OrderPartFormData>({
    resolver: zodResolver(orderPartSchema),
    defaultValues: {
      part_id: context.part_id,
      quantity: Math.max(context.min_stock_level - context.current_stock, 1),
      supplier: context.default_supplier || '',
      expected_delivery: '',
      notes: '',
      urgency: 'normal',
    },
  });

  const quantity = watch('quantity');
  const urgency = watch('urgency');

  const estimatedCost = context.unit_cost ? (context.unit_cost * quantity).toFixed(2) : null;
  const isLowStock = context.current_stock < context.min_stock_level;
  const isOutOfStock = context.current_stock === 0;

  const onSubmit = async (data: OrderPartFormData) => {
    const response = await executeAction(
      'order_part',
      data,
      {
        successMessage: `Order created for ${data.quantity} units of ${context.part_name}`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess(response.data?.order_id);
      }
    }
  };

  const getUrgencyColor = (urg?: string) => {
    switch (urg) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'urgent':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-300';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-blue-600" />
            Order Part
          </DialogTitle>
          <DialogDescription>
            Create a purchase order for this part. The order will be submitted to the selected
            supplier.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Part Information */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-2">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-blue-900 flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  {context.part_name}
                </h3>
                <p className="text-sm text-blue-700">
                  P/N: {context.part_number}
                </p>
              </div>
            </div>

            {/* Stock Status */}
            <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-blue-200">
              <div>
                <p className="text-xs text-blue-600">Current Stock</p>
                <p className={`text-lg font-bold ${
                  isOutOfStock ? 'text-red-700' : isLowStock ? 'text-orange-700' : 'text-blue-900'
                }`}>
                  {context.current_stock}
                </p>
              </div>
              <div>
                <p className="text-xs text-blue-600">Min Level</p>
                <p className="text-lg font-bold text-blue-900">
                  {context.min_stock_level}
                </p>
              </div>
            </div>

            {/* Stock Warning */}
            {isOutOfStock && (
              <div className="flex items-center gap-2 p-2 bg-red-100 border border-red-300 rounded mt-2">
                <AlertTriangle className="h-4 w-4 text-red-700" />
                <p className="text-sm text-red-700 font-medium">
                  OUT OF STOCK - Order immediately
                </p>
              </div>
            )}
            {isLowStock && !isOutOfStock && (
              <div className="flex items-center gap-2 p-2 bg-orange-100 border border-orange-300 rounded mt-2">
                <AlertTriangle className="h-4 w-4 text-orange-700" />
                <p className="text-sm text-orange-700 font-medium">
                  LOW STOCK - Below minimum level
                </p>
              </div>
            )}
          </div>

          {/* Order Details */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Quantity */}
              <div className="space-y-2">
                <Label htmlFor="quantity">
                  Quantity to Order <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  {...register('quantity')}
                  className={errors.quantity ? 'border-red-500' : ''}
                />
                {errors.quantity && (
                  <p className="text-sm text-red-600">{errors.quantity.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Suggested: {Math.max(context.min_stock_level * 2 - context.current_stock, 1)} units
                </p>
              </div>

              {/* Estimated Cost */}
              {estimatedCost && (
                <div className="space-y-2">
                  <Label>Estimated Cost</Label>
                  <div className="h-10 px-3 py-2 rounded-md border border-gray-200 bg-gray-50">
                    <p className="text-lg font-semibold text-gray-900">
                      ${estimatedCost}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    ${context.unit_cost} × {quantity} units
                  </p>
                </div>
              )}
            </div>

            {/* Supplier */}
            <div className="space-y-2">
              <Label htmlFor="supplier">
                Supplier <span className="text-red-500">*</span>
              </Label>
              <Select
                value={watch('supplier')}
                onValueChange={(value) => setValue('supplier', value)}
              >
                <SelectTrigger className={errors.supplier ? 'border-red-500' : ''}>
                  <SelectValue placeholder="Select supplier..." />
                </SelectTrigger>
                <SelectContent>
                  {context.default_supplier && (
                    <SelectItem value={context.default_supplier}>
                      {context.default_supplier} (Default)
                    </SelectItem>
                  )}
                  <SelectItem value="Marine Parts Inc">Marine Parts Inc</SelectItem>
                  <SelectItem value="Nautical Supply Co">Nautical Supply Co</SelectItem>
                  <SelectItem value="Ocean Equipment Ltd">Ocean Equipment Ltd</SelectItem>
                  <SelectItem value="Other">Other Supplier</SelectItem>
                </SelectContent>
              </Select>
              {errors.supplier && (
                <p className="text-sm text-red-600">{errors.supplier.message}</p>
              )}
            </div>

            {/* Urgency */}
            <div className="space-y-2">
              <Label htmlFor="urgency">Order Urgency</Label>
              <Select
                value={urgency}
                onValueChange={(value) => setValue('urgency', value as any)}
              >
                <SelectTrigger className={getUrgencyColor(urgency)}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal - Standard delivery</SelectItem>
                  <SelectItem value="urgent">Urgent - Expedited shipping</SelectItem>
                  <SelectItem value="critical">Critical - Emergency order</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Expected Delivery */}
            <div className="space-y-2">
              <Label htmlFor="expected_delivery">Expected Delivery Date</Label>
              <Input
                id="expected_delivery"
                type="date"
                {...register('expected_delivery')}
              />
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Additional Notes</Label>
              <Textarea
                id="notes"
                {...register('notes')}
                placeholder="Any special instructions, shipping requirements, or additional details..."
                rows={3}
              />
            </div>
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
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Creating Order...' : 'Create Order'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
