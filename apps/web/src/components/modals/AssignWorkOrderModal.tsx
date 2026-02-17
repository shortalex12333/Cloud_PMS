/**
 * AssignWorkOrderModal Component
 *
 * Modal for assigning work orders to crew members
 * Role-restricted: chief_engineer, captain, manager
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
  UserPlus,
  Loader2,
  Wrench,
  Calendar,
  Clock,
  User,
  Users,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const assignWorkOrderSchema = z.object({
  work_order_id: z.string().min(1, 'Work order ID is required'),
  assigned_to: z.string().min(1, 'Please select an assignee'),
  due_date: z.string().optional(),
  priority_override: z.enum(['routine', 'important', 'critical']).optional(),
  assignment_notes: z.string().max(500, 'Notes too long').optional(),
  notify_assignee: z.boolean().optional(),
});

type AssignWorkOrderFormData = z.infer<typeof assignWorkOrderSchema>;

// Mock crew data - in production, fetched from API
const MOCK_CREW = [
  { id: 'ce-001', name: 'John Smith', role: 'Chief Engineer', available: true },
  { id: 'eng-002', name: 'Maria Garcia', role: '2nd Engineer', available: true },
  { id: 'eng-003', name: 'James Wilson', role: '3rd Engineer', available: false },
  { id: 'eto-001', name: 'Michael Chen', role: 'ETO', available: true },
  { id: 'deck-001', name: 'Robert Brown', role: 'Bosun', available: true },
];

interface AssignWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    work_order_id: string;
    work_order_title: string;
    equipment_name?: string;
    current_priority: 'routine' | 'important' | 'critical';
    current_assignee?: string;
    due_date?: string;
  };
  onSuccess?: () => void;
}

export function AssignWorkOrderModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AssignWorkOrderModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [crew, setCrew] = useState(MOCK_CREW);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<AssignWorkOrderFormData>({
    resolver: zodResolver(assignWorkOrderSchema) as any,
    defaultValues: {
      work_order_id: context.work_order_id,
      assigned_to: context.current_assignee || '',
      due_date: context.due_date || '',
      priority_override: undefined,
      assignment_notes: '',
      notify_assignee: true,
    },
  });

  const selectedAssignee = watch('assigned_to');
  const notifyAssignee = watch('notify_assignee');

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'important':
        return 'text-amber-700 bg-amber-50 border-amber-300';
      default:
        return 'text-celeste-text-secondary bg-celeste-bg-primary border-celeste-border';
    }
  };

  const onSubmit = async (data: AssignWorkOrderFormData) => {
    const response = await executeAction(
      'assign_work_order',
      {
        work_order_id: data.work_order_id,
        assigned_to: data.assigned_to,
        due_date: data.due_date,
        priority_override: data.priority_override,
        assignment_notes: data.assignment_notes,
        notify_assignee: data.notify_assignee,
      },
      {
        successMessage: 'Work order assigned successfully',
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

  const selectedCrewMember = crew.find(c => c.id === selectedAssignee);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-celeste-accent" />
            Assign Work Order
          </DialogTitle>
          <DialogDescription>
            Assign this work order to a crew member
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Work Order Context */}
          <div className="p-3 bg-celeste-accent-line border border-celeste-accent-line rounded-lg">
            <div className="flex items-start gap-3">
              <Wrench className="h-5 w-5 text-celeste-accent mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-celeste-accent">{context.work_order_title}</h3>
                {context.equipment_name && (
                  <p className="text-sm text-celeste-accent mt-0.5">Equipment: {context.equipment_name}</p>
                )}
                <div className="flex items-center gap-3 mt-2">
                  <span className={cn(
                    'text-xs px-2 py-0.5 rounded border',
                    getPriorityColor(context.current_priority)
                  )}>
                    {context.current_priority.toUpperCase()}
                  </span>
                  {context.due_date && (
                    <span className="text-xs text-celeste-accent flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Due: {context.due_date}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Role Restriction Notice */}
          <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <Shield className="h-4 w-4 text-amber-600" />
            <p className="text-xs text-amber-700">
              This action is restricted to Chief Engineer, Captain, or Manager roles
            </p>
          </div>

          {/* Assignee Selection */}
          <div className="space-y-2">
            <Label htmlFor="assigned_to">Assign To *</Label>
            <Select
              value={selectedAssignee}
              onValueChange={(value) => setValue('assigned_to', value)}
            >
              <SelectTrigger id="assigned_to" className={errors.assigned_to ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select crew member..." />
              </SelectTrigger>
              <SelectContent>
                {crew.map((member) => (
                  <SelectItem
                    key={member.id}
                    value={member.id}
                    disabled={!member.available}
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        'w-2 h-2 rounded-full',
                        member.available ? 'bg-emerald-500' : 'bg-celeste-text-muted'
                      )} />
                      <span>{member.name}</span>
                      <span className="text-celeste-text-muted">·</span>
                      <span className="text-celeste-text-disabled">{member.role}</span>
                      {!member.available && (
                        <span className="text-xs text-celeste-text-muted">(Unavailable)</span>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.assigned_to && (
              <p className="text-sm text-red-600">{errors.assigned_to.message}</p>
            )}
          </div>

          {/* Selected Assignee Info */}
          {selectedCrewMember && (
            <div className="flex items-center gap-3 p-3 bg-celeste-bg-primary rounded-lg">
              <div className="w-10 h-10 rounded-full bg-celeste-accent-subtle flex items-center justify-center">
                <User className="h-5 w-5 text-celeste-accent" />
              </div>
              <div>
                <p className="font-medium text-celeste-black">{selectedCrewMember.name}</p>
                <p className="text-sm text-celeste-text-disabled">{selectedCrewMember.role}</p>
              </div>
              {selectedCrewMember.available && (
                <span className="ml-auto text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  Available
                </span>
              )}
            </div>
          )}

          {/* Due Date Override */}
          <div className="space-y-2">
            <Label htmlFor="due_date">Due Date (Optional Override)</Label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-celeste-text-muted" />
              <input
                id="due_date"
                type="date"
                {...register('due_date')}
                className={cn(
                  'w-full pl-10 pr-4 py-2 border rounded-md',
                  'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted',
                  errors.due_date ? 'border-red-500' : 'border-celeste-border'
                )}
              />
            </div>
          </div>

          {/* Priority Override */}
          <div className="space-y-2">
            <Label htmlFor="priority_override">Priority Override (Optional)</Label>
            <Select
              onValueChange={(value) => setValue('priority_override', value as any)}
            >
              <SelectTrigger id="priority_override">
                <SelectValue placeholder="Keep current priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="routine">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-celeste-text-muted" />
                    Routine
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

          {/* Assignment Notes */}
          <div className="space-y-2">
            <Label htmlFor="assignment_notes">Assignment Notes (Optional)</Label>
            <Textarea
              id="assignment_notes"
              {...register('assignment_notes')}
              placeholder="Add any instructions or context for the assignee..."
              rows={3}
            />
            {errors.assignment_notes && (
              <p className="text-sm text-red-600">{errors.assignment_notes.message}</p>
            )}
          </div>

          {/* Notify Checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="notify_assignee"
              {...register('notify_assignee')}
              className="h-4 w-4 rounded border-celeste-border text-celeste-accent focus:ring-celeste-accent-muted"
            />
            <Label
              htmlFor="notify_assignee"
              className="text-sm font-normal cursor-pointer"
            >
              Send notification to assignee
            </Label>
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
            <Button type="submit" disabled={isLoading || !selectedAssignee}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Assigning...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Assign Work Order
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
