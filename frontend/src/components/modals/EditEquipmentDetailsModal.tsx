/**
 * EditEquipmentDetailsModal Component
 *
 * Modal for editing equipment details with change tracking
 * Highlights critical field changes (serial numbers)
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
import { Label } from '@/components/ui/label';
import { useActionHandler } from '@/hooks/useActionHandler';
import { Settings, AlertTriangle } from 'lucide-react';

// Validation schema
const editEquipmentSchema = z.object({
  equipment_id: z.string().min(1, 'Equipment ID is required'),
  name: z.string().min(3, 'Name must be at least 3 characters').optional(),
  model: z.string().optional(),
  serial_number: z.string().optional(),
  location: z.string().optional(),
  manufacturer: z.string().optional(),
});

type EditEquipmentFormData = z.infer<typeof editEquipmentSchema>;

interface EditEquipmentDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    equipment_id: string;
    current_name: string;
    current_model?: string;
    current_serial_number?: string;
    current_location?: string;
    current_manufacturer?: string;
  };
  onSuccess?: () => void;
}

export function EditEquipmentDetailsModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditEquipmentDetailsModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<EditEquipmentFormData>({
    resolver: zodResolver(editEquipmentSchema),
    defaultValues: {
      equipment_id: context.equipment_id,
      name: context.current_name,
      model: context.current_model || '',
      serial_number: context.current_serial_number || '',
      location: context.current_location || '',
      manufacturer: context.current_manufacturer || '',
    },
  });

  const name = watch('name');
  const model = watch('model');
  const serialNumber = watch('serial_number');
  const location = watch('location');
  const manufacturer = watch('manufacturer');

  // Check what changed
  const changes = {
    name: name !== context.current_name,
    model: model !== (context.current_model || ''),
    serial_number: serialNumber !== (context.current_serial_number || ''),
    location: location !== (context.current_location || ''),
    manufacturer: manufacturer !== (context.current_manufacturer || ''),
  };

  const hasChanges = Object.values(changes).some(Boolean);
  const criticalChange = changes.serial_number;

  const onSubmit = async (data: EditEquipmentFormData) => {
    // Only send changed fields
    const changedFields: Record<string, any> = {};
    if (changes.name) changedFields.name = data.name;
    if (changes.model) changedFields.model = data.model;
    if (changes.serial_number) changedFields.serial_number = data.serial_number;
    if (changes.location) changedFields.location = data.location;
    if (changes.manufacturer) changedFields.manufacturer = data.manufacturer;

    const response = await executeAction(
      'edit_equipment_details',
      {
        equipment_id: data.equipment_id,
        changes: changedFields,
      },
      {
        successMessage: 'Equipment details updated successfully',
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
            <Settings className="h-5 w-5 text-blue-600" />
            Edit Equipment Details
          </DialogTitle>
          <DialogDescription>
            Modify equipment information. Changes to serial numbers create HIGH severity audit logs.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Critical Change Warning */}
          {criticalChange && (
            <div className="p-4 bg-red-50 border border-red-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-700 mt-0.5" />
                <div>
                  <p className="font-semibold text-red-900">Critical Field Change</p>
                  <p className="text-sm text-red-800 mt-1">
                    You are changing the serial number. This is a critical change that will create
                    a HIGH severity audit log and may require additional verification.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Equipment Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="name"
              {...register('name')}
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name.message}</p>
            )}
            {changes.name && (
              <p className="text-xs text-orange-600">
                Changed from: &quot;{context.current_name}&quot;
              </p>
            )}
          </div>

          {/* Model */}
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Input
              id="model"
              {...register('model')}
              placeholder="e.g., M-2000X"
            />
            {changes.model && (
              <p className="text-xs text-orange-600">Model has been modified</p>
            )}
          </div>

          {/* Serial Number - Critical Field */}
          <div className="space-y-2">
            <Label htmlFor="serial_number" className="flex items-center gap-2">
              Serial Number
              {context.current_serial_number && (
                <span className="text-xs text-orange-600">(Critical Field)</span>
              )}
            </Label>
            <Input
              id="serial_number"
              {...register('serial_number')}
              placeholder="e.g., SN-123456"
              className={criticalChange ? 'border-orange-500' : ''}
            />
            {criticalChange && (
              <p className="text-xs text-red-600 font-medium">
                ⚠️ Changed from: &quot;{context.current_serial_number || 'empty'}&quot; → Requires HIGH severity audit
              </p>
            )}
          </div>

          {/* Location */}
          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              {...register('location')}
              placeholder="e.g., Engine Room, Main Deck"
            />
            {changes.location && (
              <p className="text-xs text-orange-600">Location has been modified</p>
            )}
          </div>

          {/* Manufacturer */}
          <div className="space-y-2">
            <Label htmlFor="manufacturer">Manufacturer</Label>
            <Input
              id="manufacturer"
              {...register('manufacturer')}
              placeholder="e.g., Caterpillar, Rolls-Royce"
            />
            {changes.manufacturer && (
              <p className="text-xs text-orange-600">Manufacturer has been modified</p>
            )}
          </div>

          {/* Change Summary */}
          {hasChanges && (
            <div className={`p-4 border rounded-lg ${
              criticalChange
                ? 'bg-red-50 border-red-300'
                : 'bg-blue-50 border-blue-300'
            }`}>
              <p className={`text-sm font-medium ${
                criticalChange ? 'text-red-900' : 'text-blue-900'
              }`}>
                {Object.values(changes).filter(Boolean).length} field(s) will be updated.
                {criticalChange
                  ? ' HIGH severity audit log will be created.'
                  : ' LOW severity audit log will be created.'}
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
              disabled={isLoading || !hasChanges}
              variant={criticalChange ? 'destructive' : 'default'}
            >
              {isLoading ? 'Updating...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
