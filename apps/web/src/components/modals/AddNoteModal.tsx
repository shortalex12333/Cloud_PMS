// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * AddNoteModal Component
 *
 * Generic modal for adding notes to any entity type
 * Supports: fault, work_order, equipment, checklist
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
import {
  StickyNote,
  Loader2,
  AlertCircle,
  Wrench,
  Cog,
  ClipboardList,
  PlusCircle,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const addNoteSchema = z.object({
  entity_type: z.enum(['fault', 'work_order', 'equipment', 'checklist']),
  entity_id: z.string().min(1, 'Entity ID is required'),
  note_text: z.string().min(1, 'Note content is required').max(2000, 'Note too long'),
  importance: z.enum(['normal', 'important', 'critical']).optional(),
  add_to_handover: z.boolean().optional(),
});

type AddNoteFormData = z.infer<typeof addNoteSchema>;

type EntityType = 'fault' | 'work_order' | 'equipment' | 'checklist';

interface AddNoteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    entity_type: EntityType;
    entity_id: string;
    entity_title: string;
    entity_subtitle?: string;
  };
  onSuccess?: () => void;
}

const ENTITY_CONFIG: Record<EntityType, { icon: React.ElementType; color: string; label: string }> = {
  fault: { icon: AlertCircle, color: 'text-red-500 bg-red-50 border-red-200', label: 'Fault' },
  work_order: { icon: Wrench, color: 'text-celeste-accent bg-celeste-accent-line border-celeste-accent-line', label: 'Work Order' },
  equipment: { icon: Cog, color: 'text-violet-500 bg-violet-50 border-violet-200', label: 'Equipment' },
  checklist: { icon: ClipboardList, color: 'text-emerald-500 bg-emerald-50 border-emerald-200', label: 'Checklist' },
};

export function AddNoteModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AddNoteModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [charCount, setCharCount] = useState(0);

  const config = ENTITY_CONFIG[context.entity_type];
  const EntityIcon = config.icon;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<AddNoteFormData>({
    resolver: zodResolver(addNoteSchema),
    defaultValues: {
      entity_type: context.entity_type,
      entity_id: context.entity_id,
      note_text: '',
      importance: 'normal',
      add_to_handover: false,
    },
  });

  const noteText = watch('note_text');
  const addToHandover = watch('add_to_handover');

  const onSubmit = async (data: AddNoteFormData) => {
    const actionName = `add_${context.entity_type}_note` as const;

    // Build context with the correct ID field name for the entity type
    const actionContext: Record<string, any> = {
      entity_type: data.entity_type,
      entity_id: data.entity_id,
    };

    // Map entity_id to the specific field name expected by the backend
    if (data.entity_type === 'work_order') {
      actionContext.work_order_id = data.entity_id;
    } else if (data.entity_type === 'fault') {
      actionContext.fault_id = data.entity_id;
    } else if (data.entity_type === 'equipment') {
      actionContext.equipment_id = data.entity_id;
    }

    // Build parameters object - these go into payload
    const parameters: Record<string, any> = {
      note_text: data.note_text,
      importance: data.importance,
      add_to_handover: data.add_to_handover,
    };

    // Include entity ID in parameters (backend expects it in payload)
    if (data.entity_type === 'work_order') {
      parameters.work_order_id = data.entity_id;
    } else if (data.entity_type === 'fault') {
      parameters.fault_id = data.entity_id;
    } else if (data.entity_type === 'equipment') {
      parameters.equipment_id = data.entity_id;
    } else if (data.entity_type === 'checklist') {
      parameters.checklist_item_id = data.entity_id;
    }

    const response = await executeAction(
      actionName,
      {
        ...actionContext,
        // Pass form data as parameters so it goes into payload
        parameters,
      },
      {
        successMessage: 'Note added successfully',
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
            <StickyNote className="h-5 w-5 text-amber-500" />
            Add Note
          </DialogTitle>
          <DialogDescription>
            Add a note or observation to this {config.label.toLowerCase()}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Entity Context */}
          <div className={cn('p-3 rounded-lg border', config.color)}>
            <div className="flex items-center gap-3">
              <EntityIcon className="h-5 w-5" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-celeste-black truncate">{context.entity_title}</p>
                {context.entity_subtitle && (
                  <p className="text-sm text-celeste-text-secondary truncate">{context.entity_subtitle}</p>
                )}
              </div>
            </div>
          </div>

          {/* Note Content */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="note_text">Note Content *</Label>
              <span className={cn(
                'text-xs',
                charCount > 1800 ? 'text-amber-600' : 'text-celeste-text-muted'
              )}>
                {charCount}/2000
              </span>
            </div>
            <Textarea
              id="note_text"
              {...register('note_text', {
                onChange: (e) => setCharCount(e.target.value.length),
              })}
              placeholder="Enter your observation, finding, or note..."
              rows={5}
              className={errors.note_text ? 'border-red-500' : ''}
            />
            {errors.note_text && (
              <p className="text-sm text-red-600">{errors.note_text.message}</p>
            )}
          </div>

          {/* Importance Level */}
          <div className="space-y-2">
            <Label htmlFor="importance">Importance Level</Label>
            <Select
              defaultValue="normal"
              onValueChange={(value) => setValue('importance', value as any)}
            >
              <SelectTrigger id="importance">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="normal">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-celeste-text-muted" />
                    Normal
                  </span>
                </SelectItem>
                <SelectItem value="important">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    Important
                  </span>
                </SelectItem>
                <SelectItem value="critical">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                    Critical
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Add to Handover */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="add_to_handover"
              checked={addToHandover}
              onCheckedChange={(checked) => setValue('add_to_handover', !!checked)}
            />
            <Label
              htmlFor="add_to_handover"
              className="text-sm font-normal cursor-pointer flex items-center gap-2"
            >
              <Users className="h-4 w-4 text-amber-500" />
              Include in next handover
            </Label>
          </div>
          {addToHandover && (
            <p className="text-xs text-amber-600 ml-6">
              This note will be added to the active handover draft
            </p>
          )}

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
            <Button type="submit" disabled={isLoading || !noteText?.trim()}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <PlusCircle className="h-4 w-4 mr-2" />
                  Add Note
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
