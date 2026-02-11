// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * LogDeliveryReceivedModal Component
 *
 * Modal for logging received deliveries and updating inventory
 * Updates stock levels automatically
 */

'use client';

import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
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
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  PackageCheck,
  Loader2,
  Package,
  Truck,
  Calendar,
  CheckCircle,
  AlertTriangle,
  Camera,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Item schema
const deliveryItemSchema = z.object({
  part_id: z.string(),
  part_name: z.string(),
  part_number: z.string(),
  ordered_qty: z.number(),
  received_qty: z.number().min(0),
  condition: z.enum(['good', 'damaged', 'wrong_item']),
  location: z.string().optional(),
  notes: z.string().optional(),
});

// Validation schema
const logDeliveryReceivedSchema = z.object({
  purchase_order_id: z.string().min(1),
  delivery_date: z.string().min(1, 'Delivery date is required'),
  carrier: z.string().optional(),
  tracking_number: z.string().optional(),
  items: z.array(deliveryItemSchema),
  received_by: z.string().min(1, 'Receiver name is required'),
  notes: z.string().optional(),
  update_inventory: z.boolean(),
});

type DeliveryItem = z.infer<typeof deliveryItemSchema>;
type LogDeliveryReceivedFormData = z.infer<typeof logDeliveryReceivedSchema>;

interface LogDeliveryReceivedModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    purchase_order_id: string;
    purchase_order_number: string;
    supplier_name: string;
    expected_items: DeliveryItem[];
    expected_date?: string;
  };
  onSuccess?: () => void;
}

export function LogDeliveryReceivedModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: LogDeliveryReceivedModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<LogDeliveryReceivedFormData>({
    resolver: zodResolver(logDeliveryReceivedSchema),
    defaultValues: {
      purchase_order_id: context.purchase_order_id,
      delivery_date: new Date().toISOString().split('T')[0],
      carrier: '',
      tracking_number: '',
      items: context.expected_items.map(item => ({
        ...item,
        received_qty: item.ordered_qty,
        condition: 'good',
      })),
      received_by: '',
      notes: '',
      update_inventory: true,
    },
  });

  const { fields } = useFieldArray({
    control,
    name: 'items',
  });

  const items = watch('items');
  const updateInventory = watch('update_inventory');

  // Calculate summary
  const summary = {
    total: items.length,
    complete: items.filter(i => i.received_qty === i.ordered_qty && i.condition === 'good').length,
    partial: items.filter(i => i.received_qty > 0 && i.received_qty < i.ordered_qty).length,
    issues: items.filter(i => i.condition !== 'good' || i.received_qty === 0).length,
  };

  const isComplete = summary.complete === summary.total;

  const updateItemQty = (index: number, qty: number) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], received_qty: qty };
    setValue('items', newItems);
  };

  const updateItemCondition = (index: number, condition: 'good' | 'damaged' | 'wrong_item') => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], condition };
    setValue('items', newItems);
  };

  const receiveAll = () => {
    const newItems = items.map(item => ({
      ...item,
      received_qty: item.ordered_qty,
      condition: 'good' as const,
    }));
    setValue('items', newItems);
  };

  const onSubmit = async (data: LogDeliveryReceivedFormData) => {
    const response = await executeAction(
      'log_delivery_received',
      {
        purchase_order_id: data.purchase_order_id,
        delivery_date: data.delivery_date,
        carrier: data.carrier,
        tracking_number: data.tracking_number,
        items: data.items,
        received_by: data.received_by,
        notes: data.notes,
        update_inventory: data.update_inventory,
        is_complete: isComplete,
      },
      {
        successMessage: 'Delivery logged successfully',
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

  const getConditionBadge = (condition: string) => {
    switch (condition) {
      case 'good':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'damaged':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'wrong_item':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      default:
        return 'bg-celeste-bg-secondary text-celeste-text-secondary border-celeste-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <PackageCheck className="h-5 w-5 text-emerald-500" />
            Log Delivery Received
          </DialogTitle>
          <DialogDescription>
            Record received items and update inventory
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Order Info */}
          <div className="p-3 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Truck className="h-5 w-5 text-celeste-accent" />
                <div>
                  <p className="font-medium text-celeste-accent">
                    PO #{context.purchase_order_number}
                  </p>
                  <p className="text-sm text-celeste-accent">{context.supplier_name}</p>
                </div>
              </div>
              {context.expected_date && (
                <div className="text-right text-sm text-celeste-accent">
                  <p>Expected: {context.expected_date}</p>
                </div>
              )}
            </div>
          </div>

          {/* Delivery Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="delivery_date">Delivery Date *</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-celeste-text-muted" />
                <Input
                  id="delivery_date"
                  type="date"
                  {...register('delivery_date')}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="received_by">Received By *</Label>
              <Input
                id="received_by"
                {...register('received_by')}
                placeholder="Your name"
                className={errors.received_by ? 'border-red-500' : ''}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="carrier">Carrier</Label>
              <Input
                id="carrier"
                {...register('carrier')}
                placeholder="e.g., DHL, FedEx"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tracking_number">Tracking Number</Label>
              <Input
                id="tracking_number"
                {...register('tracking_number')}
                placeholder="Tracking reference"
              />
            </div>
          </div>

          {/* Items List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Items ({fields.length})</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={receiveAll}
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Receive All
              </Button>
            </div>

            <div className="border rounded-lg divide-y max-h-72 overflow-y-auto">
              {fields.map((field, index) => {
                const item = items[index];
                const isFullyReceived = item.received_qty === item.ordered_qty;

                return (
                  <div
                    key={field.id}
                    className={cn(
                      'p-3',
                      item.condition !== 'good' && 'bg-amber-50'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <Package className={cn(
                        'h-5 w-5 mt-0.5',
                        isFullyReceived && item.condition === 'good'
                          ? 'text-emerald-500'
                          : 'text-celeste-text-muted'
                      )} />

                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-celeste-black text-sm">
                          {item.part_name}
                        </p>
                        <p className="text-xs text-celeste-text-disabled">
                          P/N: {item.part_number}
                        </p>

                        <div className="mt-2 flex items-center gap-3">
                          {/* Quantity Input */}
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-celeste-text-disabled">Qty:</span>
                            <Input
                              type="number"
                              min={0}
                              max={item.ordered_qty}
                              value={item.received_qty}
                              onChange={(e) => updateItemQty(index, parseInt(e.target.value) || 0)}
                              className="w-16 h-8 text-sm"
                            />
                            <span className="text-xs text-celeste-text-disabled">/ {item.ordered_qty}</span>
                          </div>

                          {/* Condition Select */}
                          <select
                            value={item.condition}
                            onChange={(e) => updateItemCondition(index, e.target.value as any)}
                            className={cn(
                              'text-xs px-2 py-1 rounded border',
                              getConditionBadge(item.condition)
                            )}
                          >
                            <option value="good">Good</option>
                            <option value="damaged">Damaged</option>
                            <option value="wrong_item">Wrong Item</option>
                          </select>
                        </div>
                      </div>

                      {isFullyReceived && item.condition === 'good' ? (
                        <CheckCircle className="h-5 w-5 text-emerald-500" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-emerald-50 rounded-lg text-center">
              <p className="text-xl font-bold text-emerald-700">{summary.complete}</p>
              <p className="text-xs text-emerald-600">Complete</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg text-center">
              <p className="text-xl font-bold text-amber-700">{summary.partial}</p>
              <p className="text-xs text-amber-600">Partial</p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg text-center">
              <p className="text-xl font-bold text-red-700">{summary.issues}</p>
              <p className="text-xs text-red-600">Issues</p>
            </div>
          </div>

          {/* Update Inventory Option */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="update_inventory"
              checked={updateInventory}
              onCheckedChange={(checked) => setValue('update_inventory', !!checked)}
            />
            <Label
              htmlFor="update_inventory"
              className="text-sm font-normal cursor-pointer flex items-center gap-2"
            >
              <Package className="h-4 w-4 text-emerald-500" />
              Automatically update inventory stock levels
            </Label>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Delivery Notes</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Any observations about the delivery..."
              rows={2}
            />
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
            <Button type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Logging...
                </>
              ) : (
                <>
                  <PackageCheck className="h-4 w-4 mr-2" />
                  Log Delivery
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
