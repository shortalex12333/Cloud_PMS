// @ts-nocheck - Phase 4: Type compatibility with action payload
/**
 * CreateWorkOrderModal Component
 *
 * Modal for creating a new work order
 * - Pre-fills from context (equipment_id, fault_id)
 * - Form validation with Zod
 * - Calls create_work_order action via useWorkOrderActions
 */

'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useWorkOrderActions } from '@/hooks/useActionHandler';
import { toast } from 'sonner';

// Validation schema
const workOrderSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  priority: z.enum(['low', 'medium', 'high', 'urgent']),
  equipment_id: z.string().optional(),
  fault_id: z.string().optional(),
  assigned_to: z.string().optional(),
});

type WorkOrderFormData = z.infer<typeof workOrderSchema>;

interface CreateWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-fill context from parent (e.g., fault card, equipment card) */
  context?: {
    equipment_id?: string;
    equipment_name?: string;
    fault_id?: string;
    fault_description?: string;
    suggested_title?: string;
  };
  /** Called after successful creation */
  onSuccess?: (workOrderId: string) => void;
}

export function CreateWorkOrderModal({
  open,
  onOpenChange,
  context = {},
  onSuccess,
}: CreateWorkOrderModalProps) {
  const { createWorkOrder, isLoading } = useWorkOrderActions();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<WorkOrderFormData>({
    resolver: zodResolver(workOrderSchema),
    defaultValues: {
      title: context.suggested_title || '',
      description: context.fault_description || '',
      priority: 'medium',
      equipment_id: context.equipment_id || '',
      fault_id: context.fault_id || '',
    },
  });

  const priority = watch('priority');

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      reset({
        title: context.suggested_title || '',
        description: context.fault_description || '',
        priority: 'medium',
        equipment_id: context.equipment_id || '',
        fault_id: context.fault_id || '',
      });
    }
  }, [open, context, reset]);

  const onSubmit = async (data: WorkOrderFormData) => {
    try {
      // yacht_id is injected by useActionHandler via context
      const response = await createWorkOrder(data);

      if (response?.success) {
        toast.success('Work order created successfully', {
          description: `Work order "${data.title}" has been created.`,
        });
        onOpenChange(false);
        if (onSuccess && response.data?.work_order_id) {
          onSuccess(response.data.work_order_id);
        }
      }
    } catch (error) {
      toast.error('Failed to create work order', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Work Order</DialogTitle>
          <DialogDescription>
            {context.equipment_name
              ? `Creating work order for ${context.equipment_name}`
              : 'Fill in the details below to create a new work order.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Title <span className="text-destructive">*</span>
            </Label>
            <Input
              id="title"
              placeholder="e.g., Replace hydraulic pump"
              {...register('title')}
              disabled={isLoading}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Description <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="description"
              placeholder="Describe the work to be done..."
              rows={4}
              {...register('description')}
              disabled={isLoading}
            />
            {errors.description && (
              <p className="text-sm text-destructive">
                {errors.description.message}
              </p>
            )}
          </div>

          {/* Priority */}
          <div className="space-y-2">
            <Label htmlFor="priority">
              Priority <span className="text-destructive">*</span>
            </Label>
            <Select
              value={priority}
              onValueChange={(value) =>
                setValue('priority', value as WorkOrderFormData['priority'])
              }
              disabled={isLoading}
            >
              <SelectTrigger id="priority">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
            {errors.priority && (
              <p className="text-sm text-destructive">
                {errors.priority.message}
              </p>
            )}
          </div>

          {/* Equipment (read-only if pre-filled) */}
          {context.equipment_name && (
            <div className="space-y-2">
              <Label>Equipment</Label>
              <Input
                value={context.equipment_name}
                disabled
                className="bg-muted"
              />
            </div>
          )}

          {/* Assigned To (optional for now - will be populated from DB later) */}
          <div className="space-y-2">
            <Label htmlFor="assigned_to">Assigned To (optional)</Label>
            <Input
              id="assigned_to"
              placeholder="Leave blank to assign later"
              {...register('assigned_to')}
              disabled={isLoading}
            />
          </div>

          <DialogFooter>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Creating...' : 'Create Work Order'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
