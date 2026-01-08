// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * AddWorklistTaskModal Component
 *
 * Modal for adding tasks to shipyard worklist during refit/maintenance
 * Supports task categorization, dependencies, and contractor assignment
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
import { Checkbox } from '@/components/ui/checkbox';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  ClipboardList,
  Loader2,
  Hammer,
  Calendar,
  Users,
  Link2,
  AlertCircle,
  Tag,
  Clock,
  DollarSign,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const addWorklistTaskSchema = z.object({
  worklist_id: z.string().min(1),
  title: z.string().min(3, 'Task title must be at least 3 characters'),
  description: z.string().optional(),
  category: z.enum([
    'hull',
    'mechanical',
    'electrical',
    'plumbing',
    'hvac',
    'interior',
    'exterior',
    'safety',
    'electronics',
    'other',
  ]),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  estimated_hours: z.number().min(0).optional(),
  estimated_cost: z.number().min(0).optional(),
  assigned_contractor: z.string().optional(),
  start_date: z.string().optional(),
  due_date: z.string().optional(),
  dependencies: z.array(z.string()).optional(),
  requires_parts: z.boolean(),
  requires_haulout: z.boolean(),
  notes: z.string().optional(),
});

type AddWorklistTaskFormData = z.infer<typeof addWorklistTaskSchema>;

interface ExistingTask {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
}

interface Contractor {
  id: string;
  name: string;
  specialty: string;
  available: boolean;
}

interface AddWorklistTaskModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    worklist_id: string;
    worklist_name: string;
    vessel_name: string;
    existing_tasks?: ExistingTask[];
    contractors?: Contractor[];
    refit_start_date?: string;
    refit_end_date?: string;
  };
  onSuccess?: () => void;
}

const CATEGORIES = [
  { value: 'hull', label: 'Hull & Structure', color: 'bg-slate-100 text-slate-700' },
  { value: 'mechanical', label: 'Mechanical', color: 'bg-orange-100 text-orange-700' },
  { value: 'electrical', label: 'Electrical', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'plumbing', label: 'Plumbing', color: 'bg-blue-100 text-blue-700' },
  { value: 'hvac', label: 'HVAC', color: 'bg-cyan-100 text-cyan-700' },
  { value: 'interior', label: 'Interior', color: 'bg-pink-100 text-pink-700' },
  { value: 'exterior', label: 'Exterior', color: 'bg-green-100 text-green-700' },
  { value: 'safety', label: 'Safety Systems', color: 'bg-red-100 text-red-700' },
  { value: 'electronics', label: 'Electronics', color: 'bg-purple-100 text-purple-700' },
  { value: 'other', label: 'Other', color: 'bg-zinc-100 text-zinc-700' },
];

const PRIORITIES = [
  { value: 'low', label: 'Low', color: 'text-zinc-500' },
  { value: 'medium', label: 'Medium', color: 'text-blue-500' },
  { value: 'high', label: 'High', color: 'text-amber-500' },
  { value: 'critical', label: 'Critical', color: 'text-red-500' },
];

export function AddWorklistTaskModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AddWorklistTaskModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [selectedDependencies, setSelectedDependencies] = useState<string[]>([]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<AddWorklistTaskFormData>({
    resolver: zodResolver(addWorklistTaskSchema),
    defaultValues: {
      worklist_id: context.worklist_id,
      title: '',
      description: '',
      category: 'mechanical',
      priority: 'medium',
      estimated_hours: undefined,
      estimated_cost: undefined,
      assigned_contractor: '',
      start_date: context.refit_start_date || '',
      due_date: '',
      dependencies: [],
      requires_parts: false,
      requires_haulout: false,
      notes: '',
    },
  });

  const category = watch('category');
  const priority = watch('priority');
  const requiresParts = watch('requires_parts');
  const requiresHaulout = watch('requires_haulout');

  const toggleDependency = (taskId: string) => {
    const newDeps = selectedDependencies.includes(taskId)
      ? selectedDependencies.filter(id => id !== taskId)
      : [...selectedDependencies, taskId];
    setSelectedDependencies(newDeps);
    setValue('dependencies', newDeps);
  };

  const onSubmit = async (data: AddWorklistTaskFormData) => {
    const response = await executeAction(
      'add_worklist_task',
      {
        worklist_id: data.worklist_id,
        title: data.title,
        description: data.description,
        category: data.category,
        priority: data.priority,
        estimated_hours: data.estimated_hours,
        estimated_cost: data.estimated_cost,
        assigned_contractor: data.assigned_contractor,
        start_date: data.start_date,
        due_date: data.due_date,
        dependencies: data.dependencies,
        requires_parts: data.requires_parts,
        requires_haulout: data.requires_haulout,
        notes: data.notes,
      },
      {
        successMessage: 'Task added to worklist',
        refreshData: true,
      }
    );

    if (response?.success) {
      reset();
      setSelectedDependencies([]);
      onOpenChange(false);
      onSuccess?.();
    }
  };

  const handleClose = () => {
    reset();
    setSelectedDependencies([]);
    onOpenChange(false);
  };

  const existingTasks = context.existing_tasks || [];
  const contractors = context.contractors || [];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-indigo-500" />
            Add Worklist Task
          </DialogTitle>
          <DialogDescription>
            Add a new task to {context.worklist_name} for {context.vessel_name}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Task Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Task Title *</Label>
            <div className="relative">
              <Hammer className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                id="title"
                {...register('title')}
                placeholder="e.g., Replace prop shaft seals"
                className={cn('pl-10', errors.title && 'border-red-500')}
              />
            </div>
            {errors.title && (
              <p className="text-xs text-red-500">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Detailed description of the work required..."
              rows={2}
            />
          </div>

          {/* Category & Priority Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Category *</Label>
              <div className="grid grid-cols-2 gap-1.5 max-h-32 overflow-y-auto p-1">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => setValue('category', cat.value as any)}
                    className={cn(
                      'px-2 py-1.5 rounded-lg text-xs font-medium transition-all',
                      'border',
                      category === cat.value
                        ? cn(cat.color, 'border-current ring-1 ring-current')
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Priority *</Label>
              <div className="space-y-1.5">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setValue('priority', p.value as any)}
                    className={cn(
                      'w-full px-3 py-2 rounded-lg text-sm font-medium text-left transition-all',
                      'border',
                      priority === p.value
                        ? cn('bg-zinc-50 border-zinc-300', p.color)
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Estimates Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="estimated_hours">Estimated Hours</Label>
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="estimated_hours"
                  type="number"
                  min={0}
                  step={0.5}
                  {...register('estimated_hours', { valueAsNumber: true })}
                  placeholder="0"
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="estimated_cost">Estimated Cost ($)</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="estimated_cost"
                  type="number"
                  min={0}
                  step={100}
                  {...register('estimated_cost', { valueAsNumber: true })}
                  placeholder="0"
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          {/* Dates Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_date">Start Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="start_date"
                  type="date"
                  {...register('start_date')}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="due_date">Due Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="due_date"
                  type="date"
                  {...register('due_date')}
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          {/* Contractor Assignment */}
          {contractors.length > 0 && (
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Users className="h-4 w-4 text-gray-500" />
                Assign Contractor
              </Label>
              <select
                {...register('assigned_contractor')}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                <option value="">-- Select Contractor --</option>
                {contractors.map((c) => (
                  <option
                    key={c.id}
                    value={c.id}
                    disabled={!c.available}
                  >
                    {c.name} ({c.specialty}){!c.available && ' - Unavailable'}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Dependencies */}
          {existingTasks.length > 0 && (
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-gray-500" />
                Dependencies (must complete first)
              </Label>
              <div className="border rounded-lg p-2 max-h-32 overflow-y-auto space-y-1">
                {existingTasks
                  .filter(t => t.status !== 'completed')
                  .map((task) => (
                    <label
                      key={task.id}
                      className={cn(
                        'flex items-center gap-2 p-2 rounded cursor-pointer',
                        'hover:bg-gray-50 transition-colors',
                        selectedDependencies.includes(task.id) && 'bg-indigo-50'
                      )}
                    >
                      <Checkbox
                        checked={selectedDependencies.includes(task.id)}
                        onCheckedChange={() => toggleDependency(task.id)}
                      />
                      <span className="text-sm text-gray-700">{task.title}</span>
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded ml-auto',
                        task.status === 'pending' && 'bg-gray-100 text-gray-600',
                        task.status === 'in_progress' && 'bg-blue-100 text-blue-600'
                      )}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </label>
                  ))}
              </div>
            </div>
          )}

          {/* Special Requirements */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
            <p className="text-xs font-medium text-amber-800 flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" />
              Special Requirements
            </p>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={requiresParts}
                  onCheckedChange={(checked) => setValue('requires_parts', !!checked)}
                />
                <span className="text-sm text-amber-800">Requires Parts Order</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={requiresHaulout}
                  onCheckedChange={(checked) => setValue('requires_haulout', !!checked)}
                />
                <span className="text-sm text-amber-800">Requires Haul-out</span>
              </label>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Any additional information for the yard or crew..."
              rows={2}
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
            <Button type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <ClipboardList className="h-4 w-4 mr-2" />
                  Add Task
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
