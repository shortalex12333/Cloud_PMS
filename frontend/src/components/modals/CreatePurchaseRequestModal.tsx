/**
 * CreatePurchaseRequestModal Component
 *
 * Modal for creating purchase requests with multiple line items
 * Supports parts and equipment purchases with budget tracking
 * Phase 4 - Additional CREATE Modal
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import { ShoppingCart, Plus, Trash2, DollarSign, AlertCircle } from 'lucide-react';

// Line item schema
const lineItemSchema = z.object({
  item_type: z.enum(['part', 'equipment']),
  item_id: z.string().optional(),
  item_name: z.string().min(3, 'Item name must be at least 3 characters'),
  quantity: z.coerce.number().min(1, 'Quantity must be at least 1'),
  estimated_unit_cost: z.coerce.number().min(0, 'Cost must be positive'),
});

// Validation schema
const createPurchaseRequestSchema = z.object({
  justification: z.string().min(20, 'Justification must be at least 20 characters'),
  urgency: z.enum(['normal', 'urgent', 'critical']),
  budget_code: z.string().min(1, 'Budget code is required'),
  line_items: z.array(lineItemSchema).min(1, 'At least one item is required'),
});

type CreatePurchaseRequestFormData = z.infer<typeof createPurchaseRequestSchema>;
type LineItem = z.infer<typeof lineItemSchema>;

interface CreatePurchaseRequestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    pre_fill_item?: {
      item_type: 'part' | 'equipment';
      item_id?: string;
      item_name: string;
      estimated_cost?: number;
    };
  };
  onSuccess?: (request_id: string) => void;
}

export function CreatePurchaseRequestModal({
  open,
  onOpenChange,
  context = {},
  onSuccess,
}: CreatePurchaseRequestModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    control,
  } = useForm<CreatePurchaseRequestFormData>({
    resolver: zodResolver(createPurchaseRequestSchema),
    defaultValues: {
      justification: '',
      urgency: 'normal',
      budget_code: '',
      line_items: context.pre_fill_item
        ? [
            {
              item_type: context.pre_fill_item.item_type,
              item_id: context.pre_fill_item.item_id || '',
              item_name: context.pre_fill_item.item_name,
              quantity: 1,
              estimated_unit_cost: context.pre_fill_item.estimated_cost || 0,
            },
          ]
        : [
            {
              item_type: 'part',
              item_id: '',
              item_name: '',
              quantity: 1,
              estimated_unit_cost: 0,
            },
          ],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'line_items',
  });

  const lineItems = watch('line_items');
  const urgency = watch('urgency');

  // Calculate total cost
  const totalCost = lineItems.reduce((sum, item) => {
    return sum + (item.quantity || 0) * (item.estimated_unit_cost || 0);
  }, 0);

  const onSubmit = async (data: CreatePurchaseRequestFormData) => {
    const response = await executeAction(
      'create_purchase_request',
      data,
      {
        successMessage: `Purchase request created with ${data.line_items.length} item(s)`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess(response.data?.request_id);
      }
    }
  };

  const addLineItem = () => {
    append({
      item_type: 'part',
      item_id: '',
      item_name: '',
      quantity: 1,
      estimated_unit_cost: 0,
    });
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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-blue-600" />
            Create Purchase Request
          </DialogTitle>
          <DialogDescription>
            Submit a purchase request for approval. Add multiple items and provide justification
            for the purchase.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Request Details */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900">Request Details</h3>

            {/* Justification */}
            <div className="space-y-2">
              <Label htmlFor="justification">
                Business Justification <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="justification"
                {...register('justification')}
                placeholder="Explain why this purchase is necessary, how it benefits operations, and any urgency factors..."
                rows={4}
                className={errors.justification ? 'border-red-500' : ''}
              />
              {errors.justification && (
                <p className="text-sm text-red-600">{errors.justification.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Budget Code */}
              <div className="space-y-2">
                <Label htmlFor="budget_code">
                  Budget Code <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={watch('budget_code')}
                  onValueChange={(value) => setValue('budget_code', value)}
                >
                  <SelectTrigger className={errors.budget_code ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Select budget code..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MAINT-OPS">MAINT-OPS - Maintenance Operations</SelectItem>
                    <SelectItem value="PARTS-INV">PARTS-INV - Parts Inventory</SelectItem>
                    <SelectItem value="EQUIP-UPG">EQUIP-UPG - Equipment Upgrades</SelectItem>
                    <SelectItem value="EMERGENCY">EMERGENCY - Emergency Repairs</SelectItem>
                    <SelectItem value="SAFETY">SAFETY - Safety Equipment</SelectItem>
                    <SelectItem value="CONSUMABLES">CONSUMABLES - Consumables</SelectItem>
                  </SelectContent>
                </Select>
                {errors.budget_code && (
                  <p className="text-sm text-red-600">{errors.budget_code.message}</p>
                )}
              </div>

              {/* Urgency */}
              <div className="space-y-2">
                <Label htmlFor="urgency">Request Urgency</Label>
                <Select
                  value={urgency}
                  onValueChange={(value) => setValue('urgency', value as any)}
                >
                  <SelectTrigger className={getUrgencyColor(urgency)}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="normal">Normal - Standard procurement</SelectItem>
                    <SelectItem value="urgent">Urgent - Expedited approval needed</SelectItem>
                    <SelectItem value="critical">Critical - Emergency purchase</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Line Items ({fields.length})
              </h3>
              <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                <Plus className="h-4 w-4 mr-1" />
                Add Item
              </Button>
            </div>

            {errors.line_items && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{errors.line_items.message as string}</p>
              </div>
            )}

            <div className="space-y-3">
              {fields.map((field, index) => (
                <div
                  key={field.id}
                  className="p-4 border border-gray-200 rounded-lg space-y-3 bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Item #{index + 1}</span>
                    {fields.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => remove(index)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <div className="grid grid-cols-12 gap-3">
                    {/* Item Type */}
                    <div className="col-span-3 space-y-1">
                      <Label className="text-xs">Type</Label>
                      <Select
                        value={watch(`line_items.${index}.item_type`)}
                        onValueChange={(value) =>
                          setValue(`line_items.${index}.item_type`, value as any)
                        }
                      >
                        <SelectTrigger className="h-9">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="part">Part</SelectItem>
                          <SelectItem value="equipment">Equipment</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Item Name */}
                    <div className="col-span-5 space-y-1">
                      <Label className="text-xs">Item Name *</Label>
                      <Input
                        {...register(`line_items.${index}.item_name`)}
                        placeholder="e.g., Oil Filter"
                        className={`h-9 ${
                          errors.line_items?.[index]?.item_name ? 'border-red-500' : ''
                        }`}
                      />
                    </div>

                    {/* Quantity */}
                    <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Qty *</Label>
                      <Input
                        type="number"
                        min="1"
                        {...register(`line_items.${index}.quantity`)}
                        className={`h-9 ${
                          errors.line_items?.[index]?.quantity ? 'border-red-500' : ''
                        }`}
                      />
                    </div>

                    {/* Unit Cost */}
                    <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Unit Cost</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        {...register(`line_items.${index}.estimated_unit_cost`)}
                        placeholder="0.00"
                        className="h-9"
                      />
                    </div>
                  </div>

                  {/* Line Total */}
                  {lineItems[index] && (
                    <div className="flex justify-end">
                      <span className="text-sm text-gray-600">
                        Line Total:{' '}
                        <span className="font-semibold">
                          $
                          {(
                            (lineItems[index].quantity || 0) *
                            (lineItems[index].estimated_unit_cost || 0)
                          ).toFixed(2)}
                        </span>
                      </span>
                    </div>
                  )}

                  {/* Validation Errors for this item */}
                  {errors.line_items?.[index] && (
                    <div className="text-xs text-red-600">
                      {errors.line_items[index]?.item_name && (
                        <p>• {errors.line_items[index]?.item_name?.message}</p>
                      )}
                      {errors.line_items[index]?.quantity && (
                        <p>• {errors.line_items[index]?.quantity?.message}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Cost Summary */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-blue-700" />
                <span className="font-semibold text-blue-900">Estimated Total Cost</span>
              </div>
              <span className="text-2xl font-bold text-blue-900">${totalCost.toFixed(2)}</span>
            </div>
            <p className="text-xs text-blue-700 mt-2">
              {lineItems.length} item(s) • {lineItems.reduce((sum, item) => sum + (item.quantity || 0), 0)} total units
            </p>
            {totalCost > 5000 && (
              <div className="mt-3 p-2 bg-orange-50 border border-orange-200 rounded flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-orange-700 mt-0.5" />
                <p className="text-xs text-orange-800">
                  High-value request (&gt;$5,000) may require additional approval levels.
                </p>
              </div>
            )}
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
            <Button type="submit" disabled={isLoading || lineItems.length === 0}>
              {isLoading ? 'Submitting...' : 'Submit Request'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
