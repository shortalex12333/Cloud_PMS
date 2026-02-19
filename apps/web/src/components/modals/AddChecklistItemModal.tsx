/**
 * AddChecklistItemModal Component
 *
 * Modal for adding checklist items to a work order
 */

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
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
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  ClipboardList,
  Loader2,
  Wrench,
  PlusCircle,
} from 'lucide-react';

interface FormData {
  title: string;
  description: string;
}

interface AddChecklistItemModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    work_order_id: string;
    work_order_title: string;
    yacht_id?: string;
  };
  onSuccess?: () => void;
}

export function AddChecklistItemModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AddChecklistItemModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      title: '',
      description: '',
    },
  });

  const title = watch('title');

  const onSubmit = async (data: FormData) => {
    const response = await executeAction(
      'add_checklist_item',
      {
        entity_type: 'work_order',
        entity_id: context.work_order_id,
        work_order_id: context.work_order_id,
        // Pass form data as parameters so it goes into payload
        // Include work_order_id in parameters (backend expects it in payload)
        parameters: {
          work_order_id: context.work_order_id,
          title: data.title.trim(),
          description: data.description?.trim() || undefined,
        },
      },
      {
        successMessage: 'Checklist item added successfully',
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-brand-interactive" />
            Add Checklist Item
          </DialogTitle>
          <DialogDescription>
            Add a new checklist item to track progress on this work order
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Work Order Context */}
          <div className="p-3 rounded-lg border bg-brand-muted border-brand-interactive/20">
            <div className="flex items-center gap-3">
              <Wrench className="h-5 w-5 text-brand-interactive" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-txt-primary truncate">
                  {context.work_order_title}
                </p>
                <p className="typo-body text-txt-tertiary truncate">
                  ID: {context.work_order_id.slice(0, 8)}...
                </p>
              </div>
            </div>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Checklist Item Title *</Label>
            <Input
              id="title"
              {...register('title', { required: 'Title is required' })}
              placeholder="e.g., Inspect oil level"
              className={errors.title ? 'border-red-500' : ''}
            />
            {errors.title && (
              <p className="typo-body text-red-600">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Additional details or instructions..."
              rows={3}
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
            <Button type="submit" disabled={isLoading || !title?.trim()}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <PlusCircle className="h-4 w-4 mr-2" />
                  Add Item
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
