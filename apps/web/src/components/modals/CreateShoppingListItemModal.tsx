/**
 * CreateShoppingListItemModal Component
 *
 * Modal for creating new shopping list items.
 * Part of SHOP-03 requirement - Shopping List Lens v1.
 *
 * Features:
 * - Form fields: part_name, quantity_requested, urgency, source_type, source_notes
 * - Optional: link to existing part_id with search/select
 * - react-hook-form + zod validation
 */

'use client';

import { useState, useEffect } from 'react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import {
  ShoppingCart,
  Loader2,
  Package,
  AlertTriangle,
  Search,
  X,
  PlusCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// VALIDATION SCHEMA
// ============================================================================

const createShoppingListItemSchema = z.object({
  part_name: z
    .string()
    .min(1, 'Part name is required')
    .max(200, 'Part name too long'),
  part_number: z.string().optional(),
  manufacturer: z.string().optional(),
  quantity_requested: z.coerce
    .number()
    .positive('Quantity must be greater than 0'),
  unit: z.string().optional(),
  urgency: z.enum(['low', 'normal', 'high', 'critical']),
  source_type: z.enum([
    'inventory_low',
    'inventory_oos',
    'work_order_usage',
    'receiving_missing',
    'receiving_damaged',
    'manual_add',
  ]),
  source_notes: z.string().max(1000, 'Notes too long').optional(),
  part_id: z.string().uuid().optional().nullable(),
  source_work_order_id: z.string().uuid().optional().nullable(),
  estimated_unit_price: z.coerce.number().nonnegative().optional().nullable(),
  preferred_supplier: z.string().optional(),
});

type CreateShoppingListItemFormData = z.infer<typeof createShoppingListItemSchema>;

// ============================================================================
// TYPES
// ============================================================================

interface PartSuggestion {
  id: string;
  part_name: string;
  part_number?: string;
  manufacturer?: string;
  stock_quantity?: number;
  location?: string;
}

interface CreateShoppingListItemModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    work_order_id?: string;
    work_order_title?: string;
    part_id?: string;
    part_name?: string;
    suggested_quantity?: number;
    source_type?: CreateShoppingListItemFormData['source_type'];
  };
  onSuccess?: () => void;
}

// ============================================================================
// SOURCE TYPE OPTIONS
// ============================================================================

const SOURCE_TYPE_OPTIONS = [
  {
    value: 'manual_add',
    label: 'Manual Request',
    description: 'Manually added item',
  },
  {
    value: 'inventory_low',
    label: 'Low Stock',
    description: 'Stock below minimum level',
  },
  {
    value: 'inventory_oos',
    label: 'Out of Stock',
    description: 'Stock depleted',
  },
  {
    value: 'work_order_usage',
    label: 'Work Order',
    description: 'Required for work order',
  },
  {
    value: 'receiving_missing',
    label: 'Missing from Delivery',
    description: 'Item not in delivery',
  },
  {
    value: 'receiving_damaged',
    label: 'Damaged on Arrival',
    description: 'Item damaged in transit',
  },
] as const;

const URGENCY_OPTIONS = [
  { value: 'low', label: 'Low', color: 'text-gray-600' },
  { value: 'normal', label: 'Normal', color: 'text-blue-600' },
  { value: 'high', label: 'High', color: 'text-orange-600' },
  { value: 'critical', label: 'Critical', color: 'text-red-600' },
] as const;

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function CreateShoppingListItemModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: CreateShoppingListItemModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const { user } = useAuth();
  const [linkExistingPart, setLinkExistingPart] = useState(false);
  const [partSearch, setPartSearch] = useState('');
  const [partSuggestions, setPartSuggestions] = useState<PartSuggestion[]>([]);
  const [selectedPart, setSelectedPart] = useState<PartSuggestion | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<CreateShoppingListItemFormData>({
    resolver: zodResolver(createShoppingListItemSchema) as any,
    defaultValues: {
      part_name: context?.part_name || '',
      quantity_requested: context?.suggested_quantity || 1,
      urgency: 'normal',
      source_type: context?.source_type || 'manual_add',
      source_notes: '',
      part_id: context?.part_id || null,
      source_work_order_id: context?.work_order_id || null,
    },
  });

  // Reset form when modal opens/closes
  useEffect(() => {
    if (open) {
      reset({
        part_name: context?.part_name || '',
        quantity_requested: context?.suggested_quantity || 1,
        urgency: 'normal',
        source_type: context?.source_type || 'manual_add',
        source_notes: '',
        part_id: context?.part_id || null,
        source_work_order_id: context?.work_order_id || null,
      });
      setSelectedPart(null);
      setLinkExistingPart(!!context?.part_id);
      setPartSearch('');
    }
  }, [open, context, reset]);

  // Search parts via Supabase pms_parts table
  useEffect(() => {
    if (!partSearch || partSearch.length < 2 || !user?.yachtId) {
      setPartSuggestions([]);
      return;
    }

    const searchTimeout = setTimeout(async () => {
      setIsSearching(true);
      try {
        const searchTerm = partSearch.toLowerCase().trim();
        const { data: parts, error } = await supabase
          .from('pms_parts')
          .select('part_id, part_name, part_number, manufacturer, on_hand, location')
          .eq('yacht_id', user.yachtId)
          .or(`part_name.ilike.%${searchTerm}%,part_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%`)
          .limit(10);

        if (error) {
          console.error('[CreateShoppingListItemModal] Parts search error:', error);
          setPartSuggestions([]);
        } else if (parts) {
          // Map database fields to PartSuggestion interface
          const suggestions: PartSuggestion[] = parts.map((part: any) => ({
            id: part.part_id,
            part_name: part.part_name || `Part ${part.part_number}`,
            part_number: part.part_number,
            manufacturer: part.manufacturer,
            stock_quantity: part.on_hand || 0,
            location: part.location,
          }));
          setPartSuggestions(suggestions);
        }
      } catch (err) {
        console.error('[CreateShoppingListItemModal] Parts search failed:', err);
        setPartSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(searchTimeout);
  }, [partSearch, user?.yachtId]);

  const onSubmit = async (data: CreateShoppingListItemFormData) => {
    // Build parameters for the action
    const parameters: Record<string, any> = {
      part_name: data.part_name,
      quantity_requested: data.quantity_requested,
      urgency: data.urgency,
      source_type: data.source_type,
      source_notes: data.source_notes || undefined,
      part_number: data.part_number || undefined,
      manufacturer: data.manufacturer || undefined,
      unit: data.unit || undefined,
      preferred_supplier: data.preferred_supplier || undefined,
      estimated_unit_price: data.estimated_unit_price || undefined,
    };

    // Include linked part if selected
    if (selectedPart) {
      parameters.part_id = selectedPart.id;
    } else if (data.part_id) {
      parameters.part_id = data.part_id;
    }

    // Include source work order if provided
    if (data.source_work_order_id) {
      parameters.source_work_order_id = data.source_work_order_id;
    }

    const response = await executeAction(
      'create_shopping_list_item' as any,
      {
        parameters,
      },
      {
        successMessage: 'Item added to shopping list',
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
    setSelectedPart(null);
    setLinkExistingPart(false);
    setPartSearch('');
    onOpenChange(false);
  };

  const handleSelectPart = (part: PartSuggestion) => {
    setSelectedPart(part);
    setValue('part_name', part.part_name);
    setValue('part_number', part.part_number || '');
    setValue('manufacturer', part.manufacturer || '');
    setPartSearch('');
    setPartSuggestions([]);
  };

  const handleClearSelectedPart = () => {
    setSelectedPart(null);
    setValue('part_id', null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-brand-interactive" />
            Add to Shopping List
          </DialogTitle>
          <DialogDescription>
            Request a part or item to be ordered
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Work Order Context (if provided) */}
          {context?.work_order_id && context?.work_order_title && (
            <div className="p-3 rounded-lg border border-surface-border bg-surface-elevated">
              <p className="typo-meta text-txt-tertiary uppercase tracking-wide mb-1">
                Linked Work Order
              </p>
              <p className="typo-body font-medium text-txt-primary">
                {context.work_order_title}
              </p>
            </div>
          )}

          {/* Link Existing Part Toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="link_existing"
              checked={linkExistingPart}
              onCheckedChange={(checked) => {
                setLinkExistingPart(!!checked);
                if (!checked) {
                  handleClearSelectedPart();
                }
              }}
            />
            <Label
              htmlFor="link_existing"
              className="typo-body font-normal cursor-pointer flex items-center gap-2"
            >
              <Package className="h-4 w-4 text-txt-tertiary" />
              Link to existing part in catalog
            </Label>
          </div>

          {/* Part Search (when linking existing) */}
          {linkExistingPart && (
            <div className="space-y-2">
              <Label htmlFor="part_search">Search Parts</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-tertiary" />
                <Input
                  id="part_search"
                  placeholder="Search by name or part number..."
                  value={partSearch}
                  onChange={(e) => setPartSearch(e.target.value)}
                  className="pl-9"
                />
                {isSearching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-txt-tertiary" />
                )}
              </div>

              {/* Part Suggestions */}
              {partSuggestions.length > 0 && (
                <div className="border rounded-lg divide-y max-h-48 overflow-y-auto">
                  {partSuggestions.map((part) => (
                    <button
                      key={part.id}
                      type="button"
                      onClick={() => handleSelectPart(part)}
                      className="w-full p-2 text-left hover:bg-surface-elevated transition-colors"
                    >
                      <p className="font-medium typo-body">{part.part_name}</p>
                      <p className="typo-meta text-txt-tertiary">
                        {[
                          part.part_number && `P/N: ${part.part_number}`,
                          part.manufacturer,
                          part.stock_quantity !== undefined && `Stock: ${part.stock_quantity}`,
                          part.location && `Loc: ${part.location}`,
                        ]
                          .filter(Boolean)
                          .join(' | ')}
                      </p>
                    </button>
                  ))}
                </div>
              )}

              {/* No results message */}
              {partSearch.length >= 2 && !isSearching && partSuggestions.length === 0 && (
                <p className="typo-meta text-txt-tertiary py-2 text-center">
                  No parts found matching "{partSearch}"
                </p>
              )}

              {/* Selected Part */}
              {selectedPart && (
                <div className="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded-lg">
                  <Package className="h-4 w-4 text-green-600" />
                  <div className="flex-1">
                    <p className="typo-body font-medium text-green-700">
                      {selectedPart.part_name}
                    </p>
                    {selectedPart.part_number && (
                      <p className="typo-meta text-green-600">
                        P/N: {selectedPart.part_number}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleClearSelectedPart}
                    className="p-1 hover:bg-green-100 rounded"
                  >
                    <X className="h-4 w-4 text-green-600" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Part Name */}
          <div className="space-y-2">
            <Label htmlFor="part_name">Part Name *</Label>
            <Input
              id="part_name"
              {...register('part_name')}
              placeholder="Enter part name"
              disabled={!!selectedPart}
              className={errors.part_name ? 'border-red-500' : ''}
            />
            {errors.part_name && (
              <p className="typo-body text-red-600">{errors.part_name.message}</p>
            )}
          </div>

          {/* Part Number & Manufacturer */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="part_number">Part Number</Label>
              <Input
                id="part_number"
                {...register('part_number')}
                placeholder="P/N"
                disabled={!!selectedPart}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="manufacturer">Manufacturer</Label>
              <Input
                id="manufacturer"
                {...register('manufacturer')}
                placeholder="Brand/Manufacturer"
                disabled={!!selectedPart}
              />
            </div>
          </div>

          {/* Quantity & Unit */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="quantity_requested">Quantity *</Label>
              <Input
                id="quantity_requested"
                type="number"
                step="0.01"
                min="0.01"
                {...register('quantity_requested')}
                className={errors.quantity_requested ? 'border-red-500' : ''}
              />
              {errors.quantity_requested && (
                <p className="typo-body text-red-600">
                  {errors.quantity_requested.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="unit">Unit</Label>
              <Input
                id="unit"
                {...register('unit')}
                placeholder="pcs, liters, meters..."
              />
            </div>
          </div>

          {/* Urgency */}
          <div className="space-y-2">
            <Label htmlFor="urgency">Urgency</Label>
            <Controller
              name="urgency"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="urgency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {URGENCY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <span className={cn('flex items-center gap-2', option.color)}>
                          <span
                            className={cn(
                              'w-2 h-2 rounded-full',
                              option.value === 'critical' && 'bg-red-500',
                              option.value === 'high' && 'bg-orange-500',
                              option.value === 'normal' && 'bg-blue-500',
                              option.value === 'low' && 'bg-gray-500'
                            )}
                          />
                          {option.label}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          {/* Source Type */}
          <div className="space-y-2">
            <Label htmlFor="source_type">Request Reason *</Label>
            <Controller
              name="source_type"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="source_type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCE_TYPE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div>
                          <span className="font-medium">{option.label}</span>
                          <span className="text-txt-tertiary ml-2 typo-meta">
                            {option.description}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          {/* Source Notes */}
          <div className="space-y-2">
            <Label htmlFor="source_notes">Notes (optional)</Label>
            <Textarea
              id="source_notes"
              {...register('source_notes')}
              placeholder="Additional details, specifications, or justification..."
              rows={3}
            />
            {errors.source_notes && (
              <p className="typo-body text-red-600">{errors.source_notes.message}</p>
            )}
          </div>

          {/* Preferred Supplier */}
          <div className="space-y-2">
            <Label htmlFor="preferred_supplier">Preferred Supplier (optional)</Label>
            <Input
              id="preferred_supplier"
              {...register('preferred_supplier')}
              placeholder="Supplier name"
            />
          </div>

          {/* Estimated Unit Price */}
          <div className="space-y-2">
            <Label htmlFor="estimated_unit_price">Estimated Unit Price (optional)</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-txt-tertiary">
                $
              </span>
              <Input
                id="estimated_unit_price"
                type="number"
                step="0.01"
                min="0"
                {...register('estimated_unit_price')}
                className="pl-7"
                placeholder="0.00"
              />
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
            <Button type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <PlusCircle className="h-4 w-4 mr-2" />
                  Add to List
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default CreateShoppingListItemModal;
