/**
 * EditHandoverSectionModal Component
 *
 * Modal for editing handover sections
 * Allows adding/removing items, reordering, and editing content
 */

'use client';

import { useState, useEffect } from 'react';
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
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Edit,
  Loader2,
  Users,
  Plus,
  Trash2,
  GripVertical,
  AlertCircle,
  Wrench,
  Package,
  FileText,
  CheckCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const handoverItemSchema = z.object({
  id: z.string(),
  type: z.enum(['fault', 'work_order', 'equipment', 'part', 'document', 'note']),
  title: z.string().min(1, 'Title is required'),
  summary: z.string(),
  importance: z.enum(['low', 'normal', 'high']),
});

const editHandoverSectionSchema = z.object({
  section_id: z.string().min(1),
  section_name: z.string().min(1, 'Section name is required'),
  items: z.array(handoverItemSchema),
  new_item_text: z.string().optional(),
});

type HandoverItem = z.infer<typeof handoverItemSchema>;
type EditHandoverSectionFormData = z.infer<typeof editHandoverSectionSchema>;

interface EditHandoverSectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    section_id: string;
    section_name: string;
    items: HandoverItem[];
    handover_date: string;
  };
  onSuccess?: () => void;
}

const ITEM_TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string }> = {
  fault: { icon: AlertCircle, color: 'text-red-500' },
  work_order: { icon: Wrench, color: 'text-celeste-accent' },
  equipment: { icon: Package, color: 'text-violet-500' },
  part: { icon: Package, color: 'text-emerald-500' },
  document: { icon: FileText, color: 'text-indigo-500' },
  note: { icon: FileText, color: 'text-amber-500' },
};

export function EditHandoverSectionModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditHandoverSectionModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [hasChanges, setHasChanges] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<EditHandoverSectionFormData>({
    resolver: zodResolver(editHandoverSectionSchema) as any,
    defaultValues: {
      section_id: context.section_id,
      section_name: context.section_name,
      items: context.items,
      new_item_text: '',
    },
  });

  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'items',
  });

  const newItemText = watch('new_item_text');

  const addManualNote = () => {
    if (!newItemText?.trim()) return;

    append({
      id: `new-${Date.now()}`,
      type: 'note',
      title: 'Note',
      summary: newItemText.trim(),
      importance: 'normal',
    });

    setValue('new_item_text', '');
    setHasChanges(true);
  };

  const handleRemoveItem = (index: number) => {
    remove(index);
    setHasChanges(true);
  };

  const handleImportanceChange = (index: number, importance: 'low' | 'normal' | 'high') => {
    const items = watch('items');
    items[index].importance = importance;
    setValue('items', items);
    setHasChanges(true);
  };

  const onSubmit = async (data: EditHandoverSectionFormData) => {
    const response = await executeAction(
      'edit_handover_section',
      {
        section_id: data.section_id,
        section_name: data.section_name,
        items: data.items.map(item => ({
          id: item.id,
          type: item.type,
          title: item.title,
          summary: item.summary,
          importance: item.importance,
        })),
      },
      {
        successMessage: 'Handover section updated',
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
    if (hasChanges) {
      if (confirm('You have unsaved changes. Discard them?')) {
        reset();
        setHasChanges(false);
        onOpenChange(false);
      }
    } else {
      reset();
      onOpenChange(false);
    }
  };

  const getImportanceBadge = (importance: string) => {
    switch (importance) {
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'normal':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      default:
        return 'bg-celeste-bg-secondary text-celeste-text-secondary border-celeste-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit className="h-5 w-5 text-amber-500" />
            Edit Handover Section
          </DialogTitle>
          <DialogDescription>
            Modify items in this section for the {context.handover_date} handover
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Section Name */}
          <div className="space-y-2">
            <Label htmlFor="section_name">Section Name</Label>
            <Input
              id="section_name"
              {...register('section_name')}
              className={errors.section_name ? 'border-red-500' : ''}
            />
            {errors.section_name && (
              <p className="typo-body text-red-600">{errors.section_name.message}</p>
            )}
          </div>

          {/* Items List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Items ({fields.length})</Label>
              {hasChanges && (
                <span className="typo-meta text-amber-600">Unsaved changes</span>
              )}
            </div>

            <div className="border rounded-lg divide-y">
              {fields.length === 0 ? (
                <div className="p-4 text-center text-celeste-text-disabled">
                  <Users className="h-8 w-8 mx-auto mb-2 text-celeste-border" />
                  <p className="typo-body">No items in this section</p>
                  <p className="typo-meta text-celeste-text-muted">Add items below</p>
                </div>
              ) : (
                fields.map((field, index) => {
                  const config = ITEM_TYPE_CONFIG[field.type] || ITEM_TYPE_CONFIG.note;
                  const Icon = config.icon;

                  return (
                    <div
                      key={field.id}
                      className="p-3 flex items-start gap-3 hover:bg-celeste-bg-primary transition-colors"
                    >
                      <div className="mt-1 cursor-grab text-celeste-border hover:text-celeste-text-disabled">
                        <GripVertical className="h-4 w-4" />
                      </div>

                      <Icon className={cn('h-5 w-5 mt-0.5', config.color)} />

                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-celeste-black typo-body">
                          {field.title}
                        </p>
                        <p className="typo-body text-celeste-text-secondary mt-0.5">
                          {field.summary}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <select
                            value={field.importance}
                            onChange={(e) => handleImportanceChange(index, e.target.value as any)}
                            className={cn(
                              'typo-meta px-2 py-0.5 rounded border appearance-none cursor-pointer',
                              getImportanceBadge(field.importance)
                            )}
                          >
                            <option value="low">Low</option>
                            <option value="normal">Normal</option>
                            <option value="high">High</option>
                          </select>
                          <span className="typo-meta text-celeste-text-muted">{field.type}</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveItem(index)}
                        className="p-1 text-celeste-text-muted hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Add Manual Note */}
          <div className="space-y-2">
            <Label>Add Note</Label>
            <div className="flex gap-2">
              <Input
                {...register('new_item_text')}
                placeholder="Type a note to add to this section..."
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addManualNote();
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addManualNote}
                disabled={!newItemText?.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
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
                  Saving...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
