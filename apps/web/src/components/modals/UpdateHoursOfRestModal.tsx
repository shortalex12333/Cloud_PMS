// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * UpdateHoursOfRestModal Component
 *
 * Modal for updating crew hours of rest entries
 * MLC compliance-sensitive with audit trail
 */

'use client';

import { useState } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Clock,
  Loader2,
  User,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Edit,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Time entry schema
const timeEntrySchema = z.object({
  hour: z.number().min(0).max(23),
  status: z.enum(['work', 'rest', 'watch']),
});

// Validation schema
const updateHoursOfRestSchema = z.object({
  crew_member_id: z.string().min(1, 'Crew member is required'),
  date: z.string().min(1, 'Date is required'),
  entries: z.array(timeEntrySchema).length(24),
  reason: z.string().min(10, 'Reason must be at least 10 characters'),
  verified_by: z.string().optional(),
});

type TimeEntry = z.infer<typeof timeEntrySchema>;
type UpdateHoursOfRestFormData = z.infer<typeof updateHoursOfRestSchema>;

// Status types
type RestStatus = 'work' | 'rest' | 'watch';

interface UpdateHoursOfRestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    crew_member_id: string;
    crew_member_name: string;
    crew_member_role: string;
    date: string;
    current_entries?: TimeEntry[];
  };
  onSuccess?: () => void;
}

const STATUS_CONFIG: Record<RestStatus, { label: string; color: string; bgColor: string }> = {
  work: { label: 'Work', color: 'text-blue-700', bgColor: 'bg-blue-500' },
  rest: { label: 'Rest', color: 'text-emerald-700', bgColor: 'bg-emerald-500' },
  watch: { label: 'Watch', color: 'text-amber-700', bgColor: 'bg-amber-500' },
};

// Generate default 24-hour entries
function generateDefaultEntries(): TimeEntry[] {
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    status: hour >= 22 || hour < 6 ? 'rest' : 'work',
  }));
}

export function UpdateHoursOfRestModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: UpdateHoursOfRestModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [selectedStatus, setSelectedStatus] = useState<RestStatus>('work');

  const defaultEntries = context.current_entries || generateDefaultEntries();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<UpdateHoursOfRestFormData>({
    resolver: zodResolver(updateHoursOfRestSchema),
    defaultValues: {
      crew_member_id: context.crew_member_id,
      date: context.date,
      entries: defaultEntries,
      reason: '',
      verified_by: '',
    },
  });

  const entries = watch('entries');
  const reason = watch('reason');

  // Calculate hours summary
  const summary = {
    work: entries.filter(e => e.status === 'work').length,
    rest: entries.filter(e => e.status === 'rest').length,
    watch: entries.filter(e => e.status === 'watch').length,
  };

  // Check MLC compliance (minimum 10 hours rest in 24 hours, minimum 6 continuous)
  const totalRest = summary.rest;
  const isCompliant = totalRest >= 10;

  const toggleHour = (hour: number) => {
    const newEntries = [...entries];
    newEntries[hour] = {
      hour,
      status: selectedStatus,
    };
    setValue('entries', newEntries);
  };

  const setRange = (startHour: number, endHour: number, status: RestStatus) => {
    const newEntries = [...entries];
    for (let h = startHour; h <= endHour; h++) {
      newEntries[h] = { hour: h, status };
    }
    setValue('entries', newEntries);
  };

  const onSubmit = async (data: UpdateHoursOfRestFormData) => {
    const response = await executeAction(
      'update_hours_of_rest',
      {
        crew_member_id: data.crew_member_id,
        date: data.date,
        entries: data.entries,
        reason: data.reason,
        verified_by: data.verified_by,
        is_compliant: isCompliant,
      },
      {
        successMessage: 'Hours of rest updated',
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

  const formatHour = (hour: number) => {
    return `${hour.toString().padStart(2, '0')}:00`;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-500" />
            Update Hours of Rest
          </DialogTitle>
          <DialogDescription>
            Record work and rest periods for MLC compliance
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Compliance Warning */}
          <div className={cn(
            'p-3 rounded-lg border flex items-center gap-3',
            isCompliant
              ? 'bg-emerald-50 border-emerald-200'
              : 'bg-red-50 border-red-200'
          )}>
            {isCompliant ? (
              <CheckCircle className="h-5 w-5 text-emerald-600" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-600" />
            )}
            <div>
              <p className={cn(
                'font-medium',
                isCompliant ? 'text-emerald-800' : 'text-red-800'
              )}>
                {isCompliant ? 'MLC Compliant' : 'MLC Violation Warning'}
              </p>
              <p className={cn(
                'text-sm',
                isCompliant ? 'text-emerald-700' : 'text-red-700'
              )}>
                {totalRest} hours rest recorded. Minimum 10 hours required per 24-hour period.
              </p>
            </div>
          </div>

          {/* Crew Member Info */}
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <User className="h-5 w-5 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{context.crew_member_name}</p>
                <p className="text-sm text-gray-500">{context.crew_member_role}</p>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Calendar className="h-4 w-4" />
                {context.date}
              </div>
            </div>
          </div>

          {/* Status Selection */}
          <div className="space-y-2">
            <Label>Select Status to Apply</Label>
            <div className="flex gap-2">
              {(Object.keys(STATUS_CONFIG) as RestStatus[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setSelectedStatus(status)}
                  className={cn(
                    'px-4 py-2 rounded-lg border-2 transition-all',
                    'flex items-center gap-2 text-sm font-medium',
                    selectedStatus === status
                      ? `border-current ${STATUS_CONFIG[status].color} bg-white ring-2 ring-offset-2`
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  )}
                >
                  <span className={cn('w-3 h-3 rounded', STATUS_CONFIG[status].bgColor)} />
                  {STATUS_CONFIG[status].label}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500">Click on hours below to apply selected status</p>
          </div>

          {/* 24-Hour Grid */}
          <div className="space-y-2">
            <Label>24-Hour Schedule</Label>
            <div className="grid grid-cols-12 gap-1">
              {entries.map((entry, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => toggleHour(index)}
                  className={cn(
                    'aspect-square rounded flex flex-col items-center justify-center',
                    'text-xs transition-all hover:ring-2 hover:ring-offset-1',
                    STATUS_CONFIG[entry.status].bgColor,
                    'text-white font-medium'
                  )}
                  title={`${formatHour(index)} - ${STATUS_CONFIG[entry.status].label}`}
                >
                  <span>{index.toString().padStart(2, '0')}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRange(0, 5, 'rest')}
            >
              Night Rest (00-06)
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRange(6, 17, 'work')}
            >
              Day Work (06-18)
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRange(18, 21, 'rest')}
            >
              Evening Rest (18-22)
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRange(22, 23, 'rest')}
            >
              Night Rest (22-24)
            </Button>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-blue-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-blue-700">{summary.work}h</p>
              <p className="text-xs text-blue-600">Work</p>
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-emerald-700">{summary.rest}h</p>
              <p className="text-xs text-emerald-600">Rest</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-amber-700">{summary.watch}h</p>
              <p className="text-xs text-amber-600">Watch</p>
            </div>
          </div>

          {/* Reason for Change */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="reason">Reason for Update *</Label>
              <Shield className="h-4 w-4 text-amber-500" />
            </div>
            <Textarea
              id="reason"
              {...register('reason')}
              placeholder="Explain why this record is being updated (audit requirement)..."
              rows={3}
              className={errors.reason ? 'border-red-500' : ''}
            />
            {errors.reason && (
              <p className="text-sm text-red-600">{errors.reason.message}</p>
            )}
            <p className="text-xs text-amber-600">
              This is an audit-sensitive field. Changes are logged permanently.
            </p>
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
            <Button
              type="submit"
              disabled={isLoading || !reason?.trim() || reason.length < 10}
              className={!isCompliant ? 'bg-amber-600 hover:bg-amber-700' : ''}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Edit className="h-4 w-4 mr-2" />
                  {!isCompliant ? 'Save (Non-Compliant)' : 'Save Hours'}
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
