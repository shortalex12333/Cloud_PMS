/**
 * ScheduleMaintenanceModal Component
 *
 * Modal for scheduling equipment maintenance
 * Placeholder implementation - to be fully implemented in future phase
 */

'use client';

import React from 'react';
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
import { Calendar } from 'lucide-react';
import { toast } from 'sonner';

// Validation schema
const scheduleMaintenanceSchema = z.object({
  equipment_id: z.string().optional(),
  title: z.string().min(5, 'Title must be at least 5 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  maintenance_type: z.enum(['routine', 'preventive', 'inspection', 'overhaul']),
  scheduled_date: z.string().min(1, 'Scheduled date is required'),
  estimated_duration: z.string().optional(),
});

type ScheduleMaintenanceFormData = z.infer<typeof scheduleMaintenanceSchema>;

interface ScheduleMaintenanceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    equipment_id?: string;
    equipment_name?: string;
    suggested_date?: string;
  };
  onSuccess?: (maintenance_id: string) => void;
}

export function ScheduleMaintenanceModal({
  open,
  onOpenChange,
  context = {},
  onSuccess,
}: ScheduleMaintenanceModalProps) {
  const [isLoading, setIsLoading] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<ScheduleMaintenanceFormData>({
    resolver: zodResolver(scheduleMaintenanceSchema) as any,
    defaultValues: {
      equipment_id: context.equipment_id || '',
      title: '',
      description: '',
      maintenance_type: 'routine',
      scheduled_date: context.suggested_date || '',
      estimated_duration: '',
    },
  });

  const maintenanceType = watch('maintenance_type');

  const onSubmit = async (data: ScheduleMaintenanceFormData) => {
    setIsLoading(true);
    // TODO: Backend endpoint not yet implemented
    toast.info('Maintenance scheduling coming soon');
    setIsLoading(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600" />
            Schedule Maintenance
          </DialogTitle>
          <DialogDescription>
            Schedule maintenance for equipment. Set the date, type, and details for the maintenance task.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-4">
          {/* Equipment (if pre-selected) */}
          {context.equipment_name && (
            <div className="p-3 bg-celeste-accent-subtle border border-celeste-accent-line rounded-md">
              <p className="text-sm font-medium text-celeste-accent">
                Equipment: {context.equipment_name}
              </p>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Maintenance Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              {...register('title')}
              placeholder="e.g., Quarterly engine service"
              className={errors.title ? 'input-field-error' : ''}
            />
            {errors.title && (
              <p className="text-sm text-red-600">{errors.title.message}</p>
            )}
          </div>

          {/* Maintenance Type */}
          <div className="space-y-2">
            <Label htmlFor="maintenance_type">
              Maintenance Type <span className="text-red-500">*</span>
            </Label>
            <Select
              value={maintenanceType}
              onValueChange={(value) =>
                setValue('maintenance_type', value as any)
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="routine">Routine Maintenance</SelectItem>
                <SelectItem value="preventive">Preventive Maintenance</SelectItem>
                <SelectItem value="inspection">Inspection</SelectItem>
                <SelectItem value="overhaul">Overhaul</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Scheduled Date */}
          <div className="space-y-2">
            <Label htmlFor="scheduled_date">
              Scheduled Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="scheduled_date"
              type="date"
              {...register('scheduled_date')}
              className={errors.scheduled_date ? 'input-field-error' : ''}
            />
            {errors.scheduled_date && (
              <p className="text-sm text-red-600">{errors.scheduled_date.message}</p>
            )}
          </div>

          {/* Estimated Duration */}
          <div className="space-y-2">
            <Label htmlFor="estimated_duration">Estimated Duration</Label>
            <Input
              id="estimated_duration"
              {...register('estimated_duration')}
              placeholder="e.g., 4 hours"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Description <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Describe the maintenance tasks to be performed..."
              rows={4}
              className={errors.description ? 'input-field-error' : ''}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Scheduling...' : 'Schedule Maintenance'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
