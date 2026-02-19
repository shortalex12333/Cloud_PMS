/**
 * AddPartModal Component
 *
 * Modal for adding new parts to inventory
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
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import { Package } from 'lucide-react';

// Validation schema
const addPartSchema = z.object({
  part_name: z.string().min(3, 'Part name must be at least 3 characters'),
  part_number: z.string().min(3, 'Part number is required'),
  stock_quantity: z.coerce.number().min(0, 'Quantity must be positive'),
  min_stock_level: z.coerce.number().min(0, 'Min stock must be positive'),
  location: z.string().min(1, 'Location is required'),
  deck: z.string().optional(),
  room: z.string().optional(),
  storage: z.string().optional(),
  unit_cost: z.coerce.number().min(0, 'Cost must be positive').optional(),
  supplier: z.string().optional(),
  category: z.string().optional(),
});

type AddPartFormData = z.infer<typeof addPartSchema>;

interface AddPartModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    suggested_name?: string;
    suggested_part_number?: string;
  };
  onSuccess?: (part_id: string) => void;
}

export function AddPartModal({
  open,
  onOpenChange,
  context = {},
  onSuccess,
}: AddPartModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<AddPartFormData>({
    resolver: zodResolver(addPartSchema) as any,
    defaultValues: {
      part_name: context.suggested_name || '',
      part_number: context.suggested_part_number || '',
      stock_quantity: 0,
      min_stock_level: 1,
      location: '',
      deck: '',
      room: '',
      storage: '',
      unit_cost: 0,
      supplier: '',
      category: '',
    },
  });

  const stockQuantity = watch('stock_quantity');
  const minStockLevel = watch('min_stock_level');

  const onSubmit = async (data: AddPartFormData) => {
    const response = await executeAction(
      'add_part',
      data,
      {
        successMessage: 'Part added to inventory successfully',
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess(response.data?.part_id);
      }
    }
  };

  const isLowStock = stockQuantity < minStockLevel;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-celeste-accent" />
            Add Part to Inventory
          </DialogTitle>
          <DialogDescription>
            Add a new spare part or consumable to the inventory system. Ensure all details
            are accurate for proper tracking.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Part Information */}
          <div className="space-y-4">
            <h3 className="typo-body font-semibold text-celeste-black">Part Information</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Part Name */}
              <div className="space-y-2">
                <Label htmlFor="part_name">
                  Part Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="part_name"
                  {...register('part_name')}
                  placeholder="e.g., Oil Filter"
                  className={errors.part_name ? 'border-red-500' : ''}
                />
                {errors.part_name && (
                  <p className="typo-body text-red-600">{errors.part_name.message}</p>
                )}
              </div>

              {/* Part Number */}
              <div className="space-y-2">
                <Label htmlFor="part_number">
                  Part Number <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="part_number"
                  {...register('part_number')}
                  placeholder="e.g., OF-12345"
                  className={errors.part_number ? 'border-red-500' : ''}
                />
                {errors.part_number && (
                  <p className="typo-body text-red-600">{errors.part_number.message}</p>
                )}
              </div>
            </div>

            {/* Category */}
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select onValueChange={(value) => setValue('category', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="engine">Engine Parts</SelectItem>
                  <SelectItem value="electrical">Electrical</SelectItem>
                  <SelectItem value="plumbing">Plumbing</SelectItem>
                  <SelectItem value="hvac">HVAC</SelectItem>
                  <SelectItem value="safety">Safety Equipment</SelectItem>
                  <SelectItem value="consumables">Consumables</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Stock Levels */}
          <div className="space-y-4">
            <h3 className="typo-body font-semibold text-celeste-black">Stock Levels</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Initial Stock Quantity */}
              <div className="space-y-2">
                <Label htmlFor="stock_quantity">
                  Initial Quantity <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="stock_quantity"
                  type="number"
                  min="0"
                  {...register('stock_quantity')}
                  className={errors.stock_quantity ? 'border-red-500' : ''}
                />
                {errors.stock_quantity && (
                  <p className="typo-body text-red-600">{errors.stock_quantity.message}</p>
                )}
              </div>

              {/* Minimum Stock Level */}
              <div className="space-y-2">
                <Label htmlFor="min_stock_level">
                  Min Stock Level <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="min_stock_level"
                  type="number"
                  min="0"
                  {...register('min_stock_level')}
                  className={errors.min_stock_level ? 'border-red-500' : ''}
                />
                {errors.min_stock_level && (
                  <p className="typo-body text-red-600">{errors.min_stock_level.message}</p>
                )}
                <p className="typo-meta text-muted-foreground">
                  Alert threshold for reordering
                </p>
              </div>
            </div>

            {/* Low Stock Warning */}
            {isLowStock && stockQuantity >= 0 && minStockLevel > 0 && (
              <div className="p-3 bg-orange-50 border border-orange-200 rounded-md">
                <p className="typo-body text-orange-800">
                  ⚠️ Initial stock is below minimum level. Consider ordering more.
                </p>
              </div>
            )}
          </div>

          {/* Location */}
          <div className="space-y-4">
            <h3 className="typo-body font-semibold text-celeste-black">Location</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* General Location */}
              <div className="col-span-2 space-y-2">
                <Label htmlFor="location">
                  General Location <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="location"
                  {...register('location')}
                  placeholder="e.g., Engine Room Storage"
                  className={errors.location ? 'border-red-500' : ''}
                />
                {errors.location && (
                  <p className="typo-body text-red-600">{errors.location.message}</p>
                )}
              </div>

              {/* Deck */}
              <div className="space-y-2">
                <Label htmlFor="deck">Deck</Label>
                <Input
                  id="deck"
                  {...register('deck')}
                  placeholder="e.g., Main Deck"
                />
              </div>

              {/* Room */}
              <div className="space-y-2">
                <Label htmlFor="room">Room</Label>
                <Input
                  id="room"
                  {...register('room')}
                  placeholder="e.g., Storage A"
                />
              </div>

              {/* Storage */}
              <div className="col-span-2 space-y-2">
                <Label htmlFor="storage">Specific Storage</Label>
                <Input
                  id="storage"
                  {...register('storage')}
                  placeholder="e.g., Cabinet 3, Shelf B"
                />
              </div>
            </div>
          </div>

          {/* Supplier & Cost */}
          <div className="space-y-4">
            <h3 className="typo-body font-semibold text-celeste-black">Supplier & Cost</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Unit Cost */}
              <div className="space-y-2">
                <Label htmlFor="unit_cost">Unit Cost (USD)</Label>
                <Input
                  id="unit_cost"
                  type="number"
                  min="0"
                  step="0.01"
                  {...register('unit_cost')}
                  placeholder="0.00"
                />
              </div>

              {/* Supplier */}
              <div className="space-y-2">
                <Label htmlFor="supplier">Supplier</Label>
                <Input
                  id="supplier"
                  {...register('supplier')}
                  placeholder="e.g., Marine Parts Inc."
                />
              </div>
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
              {isLoading ? 'Adding Part...' : 'Add to Inventory'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
