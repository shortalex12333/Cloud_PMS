// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * LinkPartsToWorkOrderModal Component
 *
 * Modal for linking multiple parts to work orders
 * Tracks required quantities and optionally reserves parts
 * Phase 4 - LINKING Selection Modal
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
  Package,
  Search,
  Wrench,
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  X,
} from 'lucide-react';

// Validation schema for individual part
const partLinkSchema = z.object({
  part_id: z.string().min(1, 'Part ID is required'),
  quantity_required: z.coerce.number().min(1, 'Quantity must be at least 1'),
  notes: z.string().optional(),
});

// Validation schema
const linkPartsToWorkOrderSchema = z.object({
  work_order_id: z.string().min(1, 'Work order ID is required'),
  parts: z.array(partLinkSchema).min(1, 'At least one part must be selected'),
  reserve_parts: z.boolean().optional(),
});

type LinkPartsToWorkOrderFormData = z.infer<typeof linkPartsToWorkOrderSchema>;
type PartLink = z.infer<typeof partLinkSchema>;

// Mock part data (in production, this would come from API)
type Part = {
  id: string;
  part_name: string;
  part_number: string;
  stock_quantity: number;
  min_stock_level: number;
  location: string;
  unit_cost?: number;
};

interface LinkPartsToWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    work_order_id: string;
    work_order_title: string;
    work_order_type?: string;
  };
  onSuccess?: () => void;
}

export function LinkPartsToWorkOrderModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: LinkPartsToWorkOrderModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [searchQuery, setSearchQuery] = useState('');
  const [showPartSelector, setShowPartSelector] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    control,
  } = useForm<LinkPartsToWorkOrderFormData>({
    resolver: zodResolver(linkPartsToWorkOrderSchema),
    defaultValues: {
      work_order_id: context.work_order_id,
      parts: [],
      reserve_parts: false,
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'parts',
  });

  const reserveParts = watch('reserve_parts');
  const selectedParts = watch('parts') || [];

  // Mock parts data - in production, fetch from API
  const mockParts: Part[] = [
    {
      id: 'p1',
      part_name: 'Oil Filter',
      part_number: 'OF-12345',
      stock_quantity: 12,
      min_stock_level: 5,
      location: 'Engine Room - Storage A',
      unit_cost: 45.0,
    },
    {
      id: 'p2',
      part_name: 'Air Filter',
      part_number: 'AF-67890',
      stock_quantity: 8,
      min_stock_level: 3,
      location: 'Engine Room - Storage A',
      unit_cost: 32.5,
    },
    {
      id: 'p3',
      part_name: 'Fuel Filter',
      part_number: 'FF-11111',
      stock_quantity: 2,
      min_stock_level: 4,
      location: 'Engine Room - Storage B',
      unit_cost: 65.0,
    },
    {
      id: 'p4',
      part_name: 'Engine Oil - 5W-30',
      part_number: 'OIL-22222',
      stock_quantity: 0,
      min_stock_level: 2,
      location: 'Engine Room - Storage C',
      unit_cost: 28.0,
    },
    {
      id: 'p5',
      part_name: 'Spark Plug',
      part_number: 'SP-33333',
      stock_quantity: 24,
      min_stock_level: 10,
      location: 'Engine Room - Storage A',
      unit_cost: 12.5,
    },
  ];

  // Filter parts by search query
  const filteredParts = mockParts.filter(
    (part) =>
      part.part_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      part.part_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      part.location.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Get parts that are already selected
  const selectedPartIds = selectedParts.map((p) => p.part_id);

  const addPart = (part: Part) => {
    if (selectedPartIds.includes(part.id)) {
      return; // Already added
    }
    append({
      part_id: part.id,
      quantity_required: 1,
      notes: '',
    });
    setShowPartSelector(false);
    setSearchQuery('');
  };

  const getPartDetails = (partId: string): Part | undefined => {
    return mockParts.find((p) => p.id === partId);
  };

  const onSubmit = async (data: LinkPartsToWorkOrderFormData) => {
    // Add parts one at a time (backend expects single part per call)
    const firstPart = data.parts[0];
    if (!firstPart) return;

    const response = await executeAction(
      'add_parts_to_work_order',
      {
        work_order_id: data.work_order_id,
        part_id: firstPart.part_id,
        quantity: firstPart.quantity_required,
        notes: firstPart.notes,
      },
      {
        successMessage: `Linked part to work order`,
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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-celeste-accent" />
            Link Parts to Work Order
          </DialogTitle>
          <DialogDescription>
            Select parts required for this work order and specify quantities
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Work Order Information */}
          <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg">
            <div className="flex items-start gap-3">
              <Wrench className="h-5 w-5 text-celeste-accent mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-celeste-accent">{context.work_order_title}</h3>
                <p className="text-sm text-celeste-accent mt-1">
                  Work Order ID: {context.work_order_id.slice(0, 8)}
                  {context.work_order_type && (
                    <span className="ml-2">
                      • Type: {context.work_order_type}
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Selected Parts List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>
                Selected Parts ({fields.length})
                {fields.length === 0 && <span className="text-red-500"> *</span>}
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowPartSelector(!showPartSelector)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Part
              </Button>
            </div>

            {errors.parts && (
              <p className="text-sm text-red-600">{errors.parts.message as string}</p>
            )}

            {/* Part Selector (shown when Add Part is clicked) */}
            {showPartSelector && (
              <div className="p-4 border border-celeste-accent-line bg-celeste-accent-subtle rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-celeste-accent">Search Parts</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowPartSelector(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-celeste-text-muted" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by name, part number, or location..."
                    className="pl-9"
                  />
                </div>

                <div className="border border-celeste-border rounded-lg max-h-60 overflow-y-auto bg-white">
                  {filteredParts.length === 0 ? (
                    <div className="p-4 text-center text-celeste-text-disabled">
                      <p className="text-sm">No parts found</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-celeste-border">
                      {filteredParts.map((part) => {
                        const isSelected = selectedPartIds.includes(part.id);
                        const isLowStock = part.stock_quantity < part.min_stock_level;
                        const isOutOfStock = part.stock_quantity === 0;

                        return (
                          <div
                            key={part.id}
                            className={`p-3 cursor-pointer hover:bg-celeste-bg-primary transition-colors ${
                              isSelected ? 'opacity-50 cursor-not-allowed' : ''
                            }`}
                            onClick={() => !isSelected && addPart(part)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-3 flex-1">
                                <Package className="h-5 w-5 text-celeste-text-secondary mt-1" />
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-medium text-celeste-black">{part.part_name}</h4>
                                  <p className="text-sm text-celeste-text-secondary">P/N: {part.part_number}</p>
                                  <div className="flex items-center gap-3 mt-1">
                                    <p
                                      className={`text-sm font-medium ${
                                        isOutOfStock
                                          ? 'text-red-700'
                                          : isLowStock
                                          ? 'text-orange-700'
                                          : 'text-green-700'
                                      }`}
                                    >
                                      Stock: {part.stock_quantity}
                                    </p>
                                    <p className="text-xs text-celeste-text-disabled">{part.location}</p>
                                  </div>
                                </div>
                              </div>
                              {isSelected && (
                                <CheckCircle2 className="h-5 w-5 text-green-600" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Selected Parts with Quantities */}
            {fields.length === 0 ? (
              <div className="p-8 text-center text-celeste-text-disabled border border-dashed border-celeste-border rounded-lg">
                <Package className="h-12 w-12 mx-auto mb-2 text-celeste-border" />
                <p className="text-sm">No parts selected yet</p>
                <p className="text-xs text-celeste-text-muted mt-1">Click "Add Part" to select parts</p>
              </div>
            ) : (
              <div className="space-y-2">
                {fields.map((field, index) => {
                  const part = getPartDetails(watch(`parts.${index}.part_id`));
                  if (!part) return null;

                  const quantityRequired = watch(`parts.${index}.quantity_required`) || 0;
                  const exceedsStock = quantityRequired > part.stock_quantity;
                  const willBeLowStock =
                    part.stock_quantity - quantityRequired < part.min_stock_level;

                  return (
                    <div
                      key={field.id}
                      className="p-3 border border-celeste-border rounded-lg bg-celeste-bg-primary space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <Package className="h-5 w-5 text-celeste-text-secondary mt-1" />
                          <div className="flex-1">
                            <h4 className="font-medium text-celeste-black">{part.part_name}</h4>
                            <p className="text-sm text-celeste-text-secondary">P/N: {part.part_number}</p>
                            <p className="text-xs text-celeste-text-disabled mt-1">{part.location}</p>
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => remove(index)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">Available Stock</Label>
                          <div className="h-9 px-3 py-2 rounded-md border bg-white">
                            <p
                              className={`text-sm font-semibold ${
                                part.stock_quantity === 0
                                  ? 'text-red-700'
                                  : part.stock_quantity < part.min_stock_level
                                  ? 'text-orange-700'
                                  : 'text-green-700'
                              }`}
                            >
                              {part.stock_quantity}
                            </p>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs">Qty Required *</Label>
                          <Input
                            type="number"
                            min="1"
                            {...register(`parts.${index}.quantity_required`)}
                            className={`h-9 ${exceedsStock ? 'border-red-500' : ''}`}
                          />
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs">Remaining</Label>
                          <div className="h-9 px-3 py-2 rounded-md border bg-white">
                            <p
                              className={`text-sm font-semibold ${
                                exceedsStock || part.stock_quantity - quantityRequired < 0
                                  ? 'text-red-700'
                                  : willBeLowStock
                                  ? 'text-orange-700'
                                  : 'text-celeste-text-secondary'
                              }`}
                            >
                              {Math.max(0, part.stock_quantity - quantityRequired)}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Warnings */}
                      {exceedsStock && (
                        <div className="flex items-start gap-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                          <AlertTriangle className="h-4 w-4 text-red-700 mt-0.5" />
                          <p>
                            Quantity exceeds available stock. Only {part.stock_quantity} available.
                          </p>
                        </div>
                      )}
                      {!exceedsStock && willBeLowStock && (
                        <div className="flex items-start gap-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs text-orange-800">
                          <AlertTriangle className="h-4 w-4 text-orange-700 mt-0.5" />
                          <p>Using this quantity will bring stock below minimum level.</p>
                        </div>
                      )}

                      {/* Notes */}
                      <div className="space-y-1">
                        <Label className="text-xs">Notes (Optional)</Label>
                        <Textarea
                          {...register(`parts.${index}.notes`)}
                          placeholder="Any specific notes for this part..."
                          rows={2}
                          className="text-sm"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Reserve Parts Option */}
          {fields.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="reserve_parts"
                  checked={reserveParts}
                  onCheckedChange={(checked) => setValue('reserve_parts', !!checked)}
                />
                <Label
                  htmlFor="reserve_parts"
                  className="text-sm font-normal cursor-pointer"
                >
                  Reserve these parts (reduce available quantity)
                </Label>
              </div>
              {reserveParts && (
                <p className="text-xs text-orange-600 ml-6">
                  ⚠️ Parts will be reserved and unavailable for other work orders until used or
                  unreserved
                </p>
              )}
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
            <Button type="submit" disabled={isLoading || fields.length === 0}>
              {isLoading ? 'Linking...' : `Link ${fields.length} Part${fields.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
