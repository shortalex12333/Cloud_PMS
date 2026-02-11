/**
 * EditWorkOrderDetailsModal Component
 *
 * Modal for editing work order details with audit logging
 * Shows change diff and validates status
 * Phase 4 - Priority 2: Audit-Sensitive EDIT Modals
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
import { Edit, AlertCircle, FileText } from 'lucide-react';

// Validation schema
const editWorkOrderSchema = z.object({
  work_order_id: z.string().min(1, 'Work order ID is required'),
  title: z.string().min(5, 'Title must be at least 5 characters').optional(),
  description: z.string().min(10, 'Description must be at least 10 characters').optional(),
  priority: z.enum(['routine', 'important', 'critical']).optional(),
  due_date: z.string().optional(),
  assigned_to: z.string().optional(),
});

type EditWorkOrderFormData = z.infer<typeof editWorkOrderSchema>;

interface EditWorkOrderDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    work_order_id: string;
    current_title: string;
    current_description: string;
    current_priority: 'routine' | 'important' | 'critical';
    current_due_date?: string;
    current_assigned_to?: string;
    current_assigned_to_name?: string;
    status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  };
  onSuccess?: () => void;
}

export function EditWorkOrderDetailsModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditWorkOrderDetailsModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [showChanges, setShowChanges] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<EditWorkOrderFormData>({
    resolver: zodResolver(editWorkOrderSchema),
    defaultValues: {
      work_order_id: context.work_order_id,
      title: context.current_title,
      description: context.current_description,
      priority: context.current_priority,
      due_date: context.current_due_date || '',
      assigned_to: context.current_assigned_to || '',
    },
  });

  const title = watch('title');
  const description = watch('description');
  const priority = watch('priority');
  const dueDate = watch('due_date');
  const assignedTo = watch('assigned_to');

  const isCompleted = context.status === 'completed';
  const isCancelled = context.status === 'cancelled';
  const cannotEdit = isCompleted || isCancelled;

  // Check what changed
  const changes = {
    title: title !== context.current_title,
    description: description !== context.current_description,
    priority: priority !== context.current_priority,
    due_date: dueDate !== (context.current_due_date || ''),
    assigned_to: assignedTo !== (context.current_assigned_to || ''),
  };

  const hasChanges = Object.values(changes).some(Boolean);

  const onSubmit = async (data: EditWorkOrderFormData) => {
    if (cannotEdit) {
      return;
    }

    // Only send changed fields
    const changedFields: Record<string, any> = {};
    if (changes.title) changedFields.title = data.title;
    if (changes.description) changedFields.description = data.description;
    if (changes.priority) changedFields.priority = data.priority;
    if (changes.due_date) changedFields.due_date = data.due_date;
    if (changes.assigned_to) changedFields.assigned_to = data.assigned_to;

    const response = await executeAction(
      'edit_work_order_details',
      {
        work_order_id: data.work_order_id,
        changes: changedFields,
      },
      {
        successMessage: 'Work order updated successfully (audit log created)',
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

  const getPriorityColor = (prio: string) => {
    switch (prio) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'important':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      case 'routine':
        return 'text-celeste-accent bg-celeste-accent-subtle border-celeste-accent-line';
      default:
        return 'text-celeste-text-secondary bg-celeste-bg-primary border-celeste-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit className="h-5 w-5 text-celeste-accent" />
            Edit Work Order Details
          </DialogTitle>
          <DialogDescription>
            Modify work order information. All changes are logged for audit purposes.
          </DialogDescription>
        </DialogHeader>

        {/* Cannot Edit Warning */}
        {cannotEdit && (
          <div className="p-4 bg-red-50 border border-red-300 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-700 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900">Cannot Edit Work Order</p>
                <p className="text-sm text-red-800 mt-1">
                  This work order is {context.status}. {isCompleted ? 'Completed' : 'Cancelled'}{' '}
                  work orders cannot be modified.
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              {...register('title')}
              disabled={cannotEdit}
              className={errors.title ? 'border-red-500' : ''}
            />
            {errors.title && (
              <p className="text-sm text-red-600">{errors.title.message}</p>
            )}
            {changes.title && (
              <p className="text-xs text-orange-600">
                Changed from: "{context.current_title}"
              </p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Description <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              {...register('description')}
              rows={5}
              disabled={cannotEdit}
              className={errors.description ? 'border-red-500' : ''}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
            {changes.description && (
              <p className="text-xs text-orange-600">Description has been modified</p>
            )}
          </div>

          {/* Priority */}
          <div className="space-y-2">
            <Label htmlFor="priority">Priority</Label>
            <Select
              value={priority}
              onValueChange={(value) => setValue('priority', value as any)}
              disabled={cannotEdit}
            >
              <SelectTrigger className={getPriorityColor(priority || 'routine')}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="routine">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-celeste-accent" />
                    Routine - Standard maintenance
                  </span>
                </SelectItem>
                <SelectItem value="important">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-orange-500" />
                    Important - Requires attention
                  </span>
                </SelectItem>
                <SelectItem value="critical">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-red-500" />
                    Critical - Urgent repair needed
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
            {changes.priority && (
              <p className="text-xs text-orange-600">
                Changed from: {context.current_priority}
              </p>
            )}
          </div>

          {/* Due Date */}
          <div className="space-y-2">
            <Label htmlFor="due_date">Due Date</Label>
            <Input
              id="due_date"
              type="date"
              {...register('due_date')}
              disabled={cannotEdit}
            />
            {changes.due_date && (
              <p className="text-xs text-orange-600">
                Due date has been modified
              </p>
            )}
          </div>

          {/* Assigned To */}
          <div className="space-y-2">
            <Label htmlFor="assigned_to">Assigned To</Label>
            <Select
              value={assignedTo}
              onValueChange={(value) => setValue('assigned_to', value)}
              disabled={cannotEdit}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select crew member..." />
              </SelectTrigger>
              <SelectContent>
                {context.current_assigned_to && (
                  <SelectItem value={context.current_assigned_to}>
                    {context.current_assigned_to_name || context.current_assigned_to} (Current)
                  </SelectItem>
                )}
                <SelectItem value="user-001">Chief Engineer</SelectItem>
                <SelectItem value="user-002">First Engineer</SelectItem>
                <SelectItem value="user-003">Deck Engineer</SelectItem>
                <SelectItem value="unassigned">Unassigned</SelectItem>
              </SelectContent>
            </Select>
            {changes.assigned_to && (
              <p className="text-xs text-orange-600">
                Assignment has been changed
              </p>
            )}
          </div>

          {/* Change Summary */}
          {hasChanges && !cannotEdit && (
            <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg">
              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-celeste-accent mt-0.5" />
                <div>
                  <p className="font-semibold text-celeste-accent">Changes Detected</p>
                  <p className="text-sm text-celeste-accent mt-1">
                    {Object.values(changes).filter(Boolean).length} field(s) will be updated.
                    An audit log will be created with MEDIUM severity.
                  </p>
                  <Button
                    type="button"
                    variant="link"
                    size="sm"
                    onClick={() => setShowChanges(!showChanges)}
                    className="p-0 h-auto text-celeste-accent"
                  >
                    {showChanges ? 'Hide' : 'Show'} changes
                  </Button>
                  {showChanges && (
                    <ul className="mt-2 text-sm text-celeste-accent space-y-1">
                      {changes.title && <li>• Title changed</li>}
                      {changes.description && <li>• Description changed</li>}
                      {changes.priority && <li>• Priority changed</li>}
                      {changes.due_date && <li>• Due date changed</li>}
                      {changes.assigned_to && <li>• Assignment changed</li>}
                    </ul>
                  )}
                </div>
              </div>
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
              disabled={isLoading || !hasChanges || cannotEdit}
            >
              {isLoading ? 'Updating...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
