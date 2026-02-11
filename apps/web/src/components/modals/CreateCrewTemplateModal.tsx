// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * CreateCrewTemplateModal Component
 *
 * Modal for creating crew schedule templates
 * Watch schedules, rotation patterns, and standard rest/work cycles
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Layout,
  Loader2,
  Clock,
  Copy,
  Plus,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Rest period schema
const restPeriodSchema = z.object({
  start: z.string().regex(/^\d{2}:\d{2}$/, 'Time must be in HH:MM format'),
  end: z.string().regex(/^\d{2}:\d{2}$/, 'Time must be in HH:MM format'),
  hours: z.number().min(0).max(24),
});

// Day template schema
const dayTemplateSchema = z.object({
  rest_periods: z.array(restPeriodSchema),
  total_rest_hours: z.number().min(0).max(24),
});

// Validation schema
const createCrewTemplateSchema = z.object({
  schedule_name: z.string().min(3, 'Name must be at least 3 characters'),
  template_type: z.enum(['standard', 'watch', 'port', 'sea']),
  days: z.record(z.string(), dayTemplateSchema),
});

type RestPeriod = z.infer<typeof restPeriodSchema>;
type DayTemplate = z.infer<typeof dayTemplateSchema>;
type CreateCrewTemplateFormData = z.infer<typeof createCrewTemplateSchema>;

interface CreateCrewTemplateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const TEMPLATE_PRESETS = {
  standard: {
    name: 'Standard Day Work',
    rest_periods: [
      { start: '18:00', end: '08:00', hours: 14 },
    ],
    total_rest_hours: 14,
  },
  watch_4on_8off: {
    name: '4 on / 8 off Watch',
    rest_periods: [
      { start: '00:00', end: '04:00', hours: 4 },
      { start: '12:00', end: '20:00', hours: 8 },
    ],
    total_rest_hours: 12,
  },
  watch_6on_6off: {
    name: '6 on / 6 off Watch',
    rest_periods: [
      { start: '06:00', end: '12:00', hours: 6 },
      { start: '18:00', end: '00:00', hours: 6 },
    ],
    total_rest_hours: 12,
  },
};

export function CreateCrewTemplateModal({
  open,
  onOpenChange,
  onSuccess,
}: CreateCrewTemplateModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [selectedPreset, setSelectedPreset] = useState<keyof typeof TEMPLATE_PRESETS>('standard');
  const [dayTemplates, setDayTemplates] = useState<Record<string, DayTemplate>>({
    mon: TEMPLATE_PRESETS.standard,
    tue: TEMPLATE_PRESETS.standard,
    wed: TEMPLATE_PRESETS.standard,
    thu: TEMPLATE_PRESETS.standard,
    fri: TEMPLATE_PRESETS.standard,
    sat: TEMPLATE_PRESETS.standard,
    sun: TEMPLATE_PRESETS.standard,
  });
  const [editingDay, setEditingDay] = useState<string | null>('mon');

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<CreateCrewTemplateFormData>({
    resolver: zodResolver(createCrewTemplateSchema),
    defaultValues: {
      schedule_name: '',
      template_type: 'standard',
      days: dayTemplates,
    },
  });

  const scheduleName = watch('schedule_name');

  const applyPresetToDay = (day: string, preset: keyof typeof TEMPLATE_PRESETS) => {
    setDayTemplates((prev) => ({
      ...prev,
      [day]: TEMPLATE_PRESETS[preset],
    }));
  };

  const applyPresetToAll = (preset: keyof typeof TEMPLATE_PRESETS) => {
    const template = TEMPLATE_PRESETS[preset];
    setDayTemplates({
      mon: template,
      tue: template,
      wed: template,
      thu: template,
      fri: template,
      sat: template,
      sun: template,
    });
  };

  const onSubmit = async (data: CreateCrewTemplateFormData) => {
    const response = await executeAction(
      'create_crew_template',
      {
        schedule_name: data.schedule_name,
        schedule_template: {
          type: data.template_type,
          days: dayTemplates,
        },
      },
      {
        successMessage: `Schedule template "${data.schedule_name}" created`,
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
    setDayTemplates({
      mon: TEMPLATE_PRESETS.standard,
      tue: TEMPLATE_PRESETS.standard,
      wed: TEMPLATE_PRESETS.standard,
      thu: TEMPLATE_PRESETS.standard,
      fri: TEMPLATE_PRESETS.standard,
      sat: TEMPLATE_PRESETS.standard,
      sun: TEMPLATE_PRESETS.standard,
    });
    setEditingDay('mon');
    onOpenChange(false);
  };

  const daysOfWeek = [
    { key: 'mon', label: 'Monday' },
    { key: 'tue', label: 'Tuesday' },
    { key: 'wed', label: 'Wednesday' },
    { key: 'thu', label: 'Thursday' },
    { key: 'fri', label: 'Friday' },
    { key: 'sat', label: 'Saturday' },
    { key: 'sun', label: 'Sunday' },
  ];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layout className="h-5 w-5 text-celeste-accent" />
            Create Schedule Template
          </DialogTitle>
          <DialogDescription>
            Define a reusable schedule pattern for crew members
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Template Name */}
          <div className="space-y-2">
            <Label htmlFor="schedule_name">Template Name *</Label>
            <Input
              id="schedule_name"
              {...register('schedule_name')}
              placeholder="e.g., Standard Day Work, 4/8 Watch Rotation"
              className={errors.schedule_name ? 'border-red-500' : ''}
            />
            {errors.schedule_name && (
              <p className="text-sm text-red-600">{errors.schedule_name.message}</p>
            )}
          </div>

          {/* Template Type */}
          <div className="space-y-2">
            <Label htmlFor="template_type">Schedule Type</Label>
            <Select
              value={watch('template_type')}
              onValueChange={(value: any) => setValue('template_type', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard">Standard (Day Work)</SelectItem>
                <SelectItem value="watch">Watch System</SelectItem>
                <SelectItem value="port">Port Schedule</SelectItem>
                <SelectItem value="sea">At Sea Schedule</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Preset Selector */}
          <div className="space-y-2">
            <Label>Apply Preset</Label>
            <div className="flex gap-2 flex-wrap">
              {Object.entries(TEMPLATE_PRESETS).map(([key, preset]) => (
                <Button
                  key={key}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSelectedPreset(key as any);
                    applyPresetToAll(key as any);
                  }}
                  className={selectedPreset === key ? 'bg-celeste-accent-line border-celeste-accent' : ''}
                >
                  <Copy className="h-3 w-3 mr-1" />
                  {preset.name}
                </Button>
              ))}
            </div>
            <p className="text-xs text-celeste-text-disabled">Apply a preset to all days, then customize as needed</p>
          </div>

          {/* Days Grid */}
          <div className="space-y-2">
            <Label>Weekly Schedule</Label>
            <div className="grid grid-cols-7 gap-2">
              {daysOfWeek.map((day) => {
                const template = dayTemplates[day.key];
                const isEditing = editingDay === day.key;
                return (
                  <button
                    key={day.key}
                    type="button"
                    onClick={() => setEditingDay(day.key)}
                    className={cn(
                      'p-3 rounded-lg border-2 transition-all text-left',
                      isEditing
                        ? 'border-celeste-accent bg-celeste-accent-line ring-2 ring-celeste-accent-muted ring-offset-1'
                        : 'border-celeste-border hover:border-celeste-border'
                    )}
                  >
                    <p className={cn(
                      'text-xs font-semibold mb-1',
                      isEditing ? 'text-celeste-accent' : 'text-celeste-text-secondary'
                    )}>
                      {day.label.slice(0, 3)}
                    </p>
                    <div className={cn(
                      'text-lg font-bold',
                      template.total_rest_hours >= 10
                        ? 'text-emerald-600'
                        : 'text-red-600'
                    )}>
                      {template.total_rest_hours}h
                    </div>
                    <p className="text-xs text-celeste-text-disabled">
                      {template.rest_periods.length} period{template.rest_periods.length !== 1 ? 's' : ''}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Day Editor */}
          {editingDay && (
            <div className="p-4 border-2 border-celeste-accent-line rounded-lg bg-celeste-accent-line">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-celeste-black">
                  Editing: {daysOfWeek.find(d => d.key === editingDay)?.label}
                </h4>
                <div className="flex gap-1">
                  {Object.entries(TEMPLATE_PRESETS).map(([key, preset]) => (
                    <Button
                      key={key}
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => applyPresetToDay(editingDay, key as any)}
                      title={`Apply ${preset.name}`}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                {dayTemplates[editingDay].rest_periods.map((period, index) => (
                  <div key={index} className="flex items-center gap-2 bg-white p-2 rounded">
                    <Clock className="h-4 w-4 text-celeste-text-muted" />
                    <span className="text-sm font-medium">{period.start}</span>
                    <span className="text-celeste-text-muted">→</span>
                    <span className="text-sm font-medium">{period.end}</span>
                    <span className="text-sm text-celeste-text-secondary">({period.hours}h)</span>
                  </div>
                ))}
                <div className="pt-2">
                  <p className="text-sm font-semibold text-celeste-text-secondary">
                    Total Rest: {dayTemplates[editingDay].total_rest_hours} hours
                    {dayTemplates[editingDay].total_rest_hours < 10 && (
                      <span className="ml-2 text-red-600 text-xs">⚠️ Below MLC minimum</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
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
            <Button
              type="submit"
              disabled={isLoading || !scheduleName}
              className="bg-celeste-accent hover:bg-celeste-accent-hover"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Template
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
