// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * AddToHandoverQuickModal Component
 *
 * Single-item, immediate capture modal for adding entities to shift handover.
 * Pre-fills form with entity context, user only needs to add their note.
 *
 * Phase 1 - Quick Handover Capture
 * Spec: cluster_05_HANDOVER_COMMUNICATION
 */

'use client';

import { useState, useEffect } from 'react';
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
import {
  FileText,
  AlertCircle,
  Wrench,
  Package,
  Settings,
  File,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema matching backend contract
const addToHandoverQuickSchema = z.object({
  entity_type: z.enum(['fault', 'work_order', 'equipment', 'document_chunk', 'part']),
  entity_id: z.string().uuid(),
  title: z.string().min(1, 'Title required'),
  category: z.enum([
    'ongoing_fault',
    'work_in_progress',
    'important_info',
    'equipment_status',
    'general',
  ]),
  summary_text: z
    .string()
    .min(10, 'Add your note (minimum 10 characters)')
    .max(2000, 'Note too long (maximum 2000 characters)'),
  priority: z.enum(['low', 'normal', 'high', 'urgent']),
});

type AddToHandoverQuickFormData = z.infer<typeof addToHandoverQuickSchema>;

interface AddToHandoverQuickModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entityType: 'fault' | 'work_order' | 'equipment' | 'document_chunk' | 'part';
  entityId: string;
  onSuccess?: () => void;
}

const ENTITY_ICONS = {
  fault: AlertCircle,
  work_order: Wrench,
  equipment: Settings,
  document_chunk: File,
  part: Package,
};

const CATEGORY_LABELS = {
  ongoing_fault: 'Ongoing Fault',
  work_in_progress: 'Work in Progress',
  important_info: 'Important Info',
  equipment_status: 'Equipment Status',
  general: 'General',
};

const PRIORITY_LABELS = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
};

export function AddToHandoverQuickModal({
  open,
  onOpenChange,
  entityType,
  entityId,
  onSuccess,
}: AddToHandoverQuickModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [prefillLoading, setPrefillLoading] = useState(false);
  const [prefillError, setPrefillError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<AddToHandoverQuickFormData>({
    resolver: zodResolver(addToHandoverQuickSchema),
    defaultValues: {
      entity_type: entityType,
      entity_id: entityId,
      title: '',
      category: 'general',
      summary_text: '',
      priority: 'normal',
    },
  });

  const EntityIcon = ENTITY_ICONS[entityType] || FileText;

  // Fetch prefill data when modal opens
  useEffect(() => {
    if (!open || !entityType || !entityId) return;

    const fetchPrefillData = async () => {
      setPrefillLoading(true);
      setPrefillError(null);

      try {
        // Call prefill endpoint
        const response = await fetch(
          `/v1/actions/add_to_handover/prefill?entity_type=${entityType}&entity_id=${entityId}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to load handover details');
        }

        const data = await response.json();

        if (data.status === 'success' && data.prefill_data) {
          const prefill = data.prefill_data;

          // Set form values from prefill
          setValue('title', prefill.title || '');
          setValue('category', prefill.category || 'general');
          setValue('priority', prefill.priority || 'normal');
          setValue(
            'summary_text',
            prefill.summary_text
              ? `${prefill.summary_text}\n\n[Your note here]`
              : '[Your note here]'
          );
        } else {
          setPrefillError(data.message || 'Failed to load context');
        }
      } catch (error) {
        console.error('Prefill error:', error);
        setPrefillError('Failed to load entity context');
      } finally {
        setPrefillLoading(false);
      }
    };

    fetchPrefillData();
  }, [open, entityType, entityId, setValue]);

  const onSubmit = async (data: AddToHandoverQuickFormData) => {
    const response = await executeAction(
      'add_to_handover',
      {
        entity_type: data.entity_type,
        entity_id: data.entity_id,
        summary_text: data.summary_text,
        category: data.category,
        priority: data.priority,
      },
      {
        successMessage: 'Added to handover',
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
    setPrefillError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Add to Handover
          </DialogTitle>
          <DialogDescription>
            Add this item to shift handover with your note
          </DialogDescription>
        </DialogHeader>

        {prefillLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-sm text-gray-600">Loading context...</span>
          </div>
        ) : prefillError ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="h-5 w-5" />
              <span className="font-medium">{prefillError}</span>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Entity Type Indicator */}
            <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
              <EntityIcon className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900 capitalize">
                {entityType.replace('_', ' ')}
              </span>
            </div>

            {/* Title (editable) */}
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                {...register('title')}
                placeholder="Handover item title"
              />
              {errors.title && (
                <p className="text-sm text-red-600">{errors.title.message}</p>
              )}
            </div>

            {/* Category */}
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select
                value={watch('category')}
                onValueChange={(value) => setValue('category', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.category && (
                <p className="text-sm text-red-600">{errors.category.message}</p>
              )}
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={watch('priority')}
                onValueChange={(value) => setValue('priority', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'h-2 w-2 rounded-full',
                            value === 'urgent' && 'bg-red-500',
                            value === 'high' && 'bg-orange-500',
                            value === 'normal' && 'bg-blue-500',
                            value === 'low' && 'bg-gray-400'
                          )}
                        />
                        {label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.priority && (
                <p className="text-sm text-red-600">{errors.priority.message}</p>
              )}
            </div>

            {/* Details / Note */}
            <div className="space-y-2">
              <Label htmlFor="summary_text">
                Details / Your Note
                <span className="text-xs text-gray-500 ml-2">
                  (Add your observation or instructions below)
                </span>
              </Label>
              <Textarea
                id="summary_text"
                {...register('summary_text')}
                placeholder="Pre-filled context will appear here. Add your note below."
                rows={8}
                className="font-mono text-sm"
              />
              <div className="flex justify-between items-center">
                <div>
                  {errors.summary_text && (
                    <p className="text-sm text-red-600">{errors.summary_text.message}</p>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {watch('summary_text')?.length || 0} / 2000 characters
                </span>
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
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Add to Handover
                  </>
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
