/**
 * UpdateHoursOfRestModal Component - UPDATED FOR NEW SCHEMA
 *
 * Modal for logging daily hours of rest entries
 * MLC compliance-sensitive with audit trail
 *
 * NEW SCHEMA:
 * - record_date: ISO date string (e.g., "2026-02-09")
 * - rest_periods: Array of {start: "22:00", end: "06:00", hours: 8.0}
 * - total_rest_hours: Sum of all rest period hours
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
import { Label } from '@/components/ui/label';
import {
  Clock,
  Loader2,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Plus,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { upsertHoursOfRest } from '@/lib/microactions/handlers/hours_of_rest';

// Rest period schema
const restPeriodSchema = z.object({
  start: z.string().regex(/^\d{2}:\d{2}$/, 'Time must be in HH:MM format'),
  end: z.string().regex(/^\d{2}:\d{2}$/, 'Time must be in HH:MM format'),
  hours: z.number().min(0).max(24),
});

// Validation schema
const updateHoursOfRestSchema = z.object({
  record_date: z.string().min(1, 'Date is required'),
  rest_periods: z.array(restPeriodSchema).min(1, 'At least one rest period is required'),
  total_rest_hours: z.number().min(0).max(24),
});

type RestPeriod = z.infer<typeof restPeriodSchema>;
type UpdateHoursOfRestFormData = z.infer<typeof updateHoursOfRestSchema>;

interface UpdateHoursOfRestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    yacht_id: string;
    user_id: string;
    user_role: string;
  };
  defaultDate?: string;
  currentData?: {
    record_date: string;
    rest_periods: RestPeriod[];
    total_rest_hours: number;
  };
  onSuccess?: () => void;
}

// Common rest period presets
const REST_PRESETS = {
  standard: {
    label: 'Standard Night Rest (22:00-06:00)',
    periods: [{ start: '22:00', end: '06:00', hours: 8.0 }],
  },
  extended: {
    label: 'Extended Night Rest (20:00-08:00)',
    periods: [{ start: '20:00', end: '08:00', hours: 12.0 }],
  },
  split: {
    label: 'Split Rest (00:00-06:00 + 13:00-17:00)',
    periods: [
      { start: '00:00', end: '06:00', hours: 6.0 },
      { start: '13:00', end: '17:00', hours: 4.0 },
    ],
  },
  watch_4_8: {
    label: '4/8 Watch Rest (04:00-08:00 + 20:00-04:00)',
    periods: [
      { start: '04:00', end: '08:00', hours: 4.0 },
      { start: '20:00', end: '04:00', hours: 8.0 },
    ],
  },
};

export function UpdateHoursOfRestModal({
  open,
  onOpenChange,
  context,
  defaultDate,
  currentData,
  onSuccess,
}: UpdateHoursOfRestModalProps) {
  const [isLoading, setIsLoading] = useState(false);

  const defaultRestPeriods = currentData?.rest_periods || [{ start: '22:00', end: '06:00', hours: 8.0 }];
  const defaultTotalHours = currentData?.total_rest_hours || 8.0;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<UpdateHoursOfRestFormData>({
    resolver: zodResolver(updateHoursOfRestSchema) as any,
    defaultValues: {
      record_date: currentData?.record_date || defaultDate || new Date().toISOString().split('T')[0],
      rest_periods: defaultRestPeriods,
      total_rest_hours: defaultTotalHours,
    },
  });

  const restPeriods = watch('rest_periods');
  const totalRestHours = watch('total_rest_hours');
  const recordDate = watch('record_date');

  // Check MLC compliance (minimum 10 hours rest in 24 hours)
  const isCompliant = totalRestHours >= 10;

  const addRestPeriod = () => {
    setValue('rest_periods', [
      ...restPeriods,
      { start: '00:00', end: '00:00', hours: 0 },
    ]);
  };

  const removeRestPeriod = (index: number) => {
    const newPeriods = restPeriods.filter((_, i) => i !== index);
    setValue('rest_periods', newPeriods);
    recalculateTotalHours(newPeriods);
  };

  const updateRestPeriod = (index: number, field: keyof RestPeriod, value: string | number) => {
    const newPeriods = [...restPeriods];
    newPeriods[index] = { ...newPeriods[index], [field]: value };

    // Auto-calculate hours if start and end times are provided
    if (field === 'start' || field === 'end') {
      const period = newPeriods[index];
      if (period.start && period.end) {
        newPeriods[index].hours = calculateHours(period.start, period.end);
      }
    }

    setValue('rest_periods', newPeriods);
    recalculateTotalHours(newPeriods);
  };

  const recalculateTotalHours = (periods: RestPeriod[]) => {
    const total = periods.reduce((sum, period) => sum + period.hours, 0);
    setValue('total_rest_hours', Math.round(total * 10) / 10);
  };

  const applyPreset = (presetKey: keyof typeof REST_PRESETS) => {
    const preset = REST_PRESETS[presetKey];
    setValue('rest_periods', preset.periods);
    recalculateTotalHours(preset.periods);
  };

  const onSubmit = async (data: UpdateHoursOfRestFormData) => {
    setIsLoading(true);
    try {
      const result = await upsertHoursOfRest(context, {
        record_date: data.record_date,
        rest_periods: data.rest_periods,
        total_rest_hours: data.total_rest_hours,
      });

      if (result.success) {
        reset();
        onOpenChange(false);
        onSuccess?.();
      } else {
        console.error('Failed to save hours of rest:', result.error);
        alert(result.error?.message || 'Failed to save hours of rest');
      }
    } catch (error) {
      console.error('Error saving hours of rest:', error);
      alert('An error occurred while saving');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-celeste-accent" />
            Log Hours of Rest
          </DialogTitle>
          <DialogDescription>
            Record rest periods for MLC 2006 compliance
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
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
                'typo-body',
                isCompliant ? 'text-emerald-700' : 'text-red-700'
              )}>
                {totalRestHours} hours rest recorded. Minimum 10 hours required per 24-hour period.
              </p>
            </div>
          </div>

          {/* Record Date */}
          <div className="space-y-2">
            <Label htmlFor="record_date" className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-celeste-text-disabled" />
              Date *
            </Label>
            <Input
              id="record_date"
              type="date"
              {...register('record_date')}
              className={errors.record_date ? 'border-red-500' : ''}
            />
            {errors.record_date && (
              <p className="typo-body text-red-600">{errors.record_date.message}</p>
            )}
          </div>

          {/* Preset Buttons */}
          <div className="space-y-2">
            <Label>Quick Presets</Label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(REST_PRESETS).map(([key, preset]) => (
                <Button
                  key={key}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset(key as keyof typeof REST_PRESETS)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Rest Periods */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Rest Periods *</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addRestPeriod}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add Period
              </Button>
            </div>

            {errors.rest_periods && (
              <p className="typo-body text-red-600">{errors.rest_periods.message as string}</p>
            )}

            <div className="space-y-2">
              {restPeriods.map((period, index) => (
                <div key={index} className="flex items-center gap-2 p-3 bg-celeste-bg-primary rounded-lg">
                  <div className="flex-1 grid grid-cols-3 gap-2">
                    <div>
                      <Label className="typo-meta text-celeste-text-secondary">Start</Label>
                      <Input
                        type="time"
                        value={period.start}
                        onChange={(e) => updateRestPeriod(index, 'start', e.target.value)}
                        className="h-9"
                      />
                    </div>
                    <div>
                      <Label className="typo-meta text-celeste-text-secondary">End</Label>
                      <Input
                        type="time"
                        value={period.end}
                        onChange={(e) => updateRestPeriod(index, 'end', e.target.value)}
                        className="h-9"
                      />
                    </div>
                    <div>
                      <Label className="typo-meta text-celeste-text-secondary">Hours</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0"
                        max="24"
                        value={period.hours}
                        onChange={(e) => updateRestPeriod(index, 'hours', parseFloat(e.target.value) || 0)}
                        className="h-9"
                      />
                    </div>
                  </div>
                  {restPeriods.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeRestPeriod(index)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Total Rest Hours (auto-calculated) */}
          <div className="p-4 bg-celeste-accent-subtle border border-celeste-accent-line rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="typo-body font-medium text-celeste-accent">Total Rest Hours</p>
                <p className="typo-meta text-celeste-accent">Auto-calculated from rest periods</p>
              </div>
              <p className={cn(
                'text-3xl font-bold',
                isCompliant ? 'text-emerald-600' : 'text-red-600'
              )}>
                {totalRestHours}h
              </p>
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
            <Button
              type="submit"
              disabled={isLoading || restPeriods.length === 0}
              className={!isCompliant ? 'bg-amber-600 hover:bg-amber-700' : 'bg-celeste-accent hover:bg-celeste-accent-hover'}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Clock className="h-4 w-4 mr-2" />
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

// Helper function to calculate hours between two times
function calculateHours(start: string, end: string): number {
  const [startHour, startMin] = start.split(':').map(Number);
  const [endHour, endMin] = end.split(':').map(Number);

  let hours = endHour - startHour;
  let minutes = endMin - startMin;

  // Handle negative hours (crossing midnight)
  if (hours < 0) {
    hours += 24;
  }

  // Convert minutes to fractional hours
  const totalHours = hours + minutes / 60;

  return Math.round(totalHours * 10) / 10;
}
