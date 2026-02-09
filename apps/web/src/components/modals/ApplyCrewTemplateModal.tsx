// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * ApplyCrewTemplateModal Component
 *
 * Modal for applying schedule templates to specific weeks
 * Bulk-creates hours of rest records from template patterns
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
  CalendarCheck,
  Loader2,
  Calendar,
  Layout,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const applyCrewTemplateSchema = z.object({
  week_start_date: z.string().min(1, 'Week start date is required').regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
  template_id: z.string().optional(),
});

type ApplyCrewTemplateFormData = z.infer<typeof applyCrewTemplateSchema>;

interface ApplyCrewTemplateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface Template {
  id: string;
  schedule_name: string;
  template_type: string;
  created_at: string;
}

export function ApplyCrewTemplateModal({
  open,
  onOpenChange,
  onSuccess,
}: ApplyCrewTemplateModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<ApplyCrewTemplateFormData>({
    resolver: zodResolver(applyCrewTemplateSchema),
    defaultValues: {
      week_start_date: getNextMonday(),
      template_id: undefined,
    },
  });

  const weekStartDate = watch('week_start_date');
  const selectedTemplateId = watch('template_id');

  // Load available templates when modal opens
  useEffect(() => {
    if (open) {
      loadTemplates();
    }
  }, [open]);

  const loadTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const response = await executeAction(
        'list_crew_templates',
        {},
        { silent: true }
      );

      if (response?.success && response.data?.templates) {
        setTemplates(response.data.templates);
        // Auto-select first template if available
        if (response.data.templates.length > 0) {
          setValue('template_id', response.data.templates[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const onSubmit = async (data: ApplyCrewTemplateFormData) => {
    const response = await executeAction(
      'apply_crew_template',
      {
        week_start_date: data.week_start_date,
        template_id: data.template_id,
      },
      {
        successMessage: `Schedule template applied to week of ${formatDate(data.week_start_date)}`,
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
    setTemplates([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarCheck className="h-5 w-5 text-blue-500" />
            Apply Schedule Template
          </DialogTitle>
          <DialogDescription>
            Apply a saved schedule template to a specific week
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {/* Info Box */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex gap-3">
            <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Bulk Schedule Creation</p>
              <p>
                This will create hours of rest records for all 7 days of the selected week
                based on the template pattern. Existing records will not be overwritten.
              </p>
            </div>
          </div>

          {/* Week Start Date */}
          <div className="space-y-2">
            <Label htmlFor="week_start_date" className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-gray-500" />
              Week Starting (Monday) *
            </Label>
            <Input
              id="week_start_date"
              type="date"
              {...register('week_start_date')}
              className={errors.week_start_date ? 'border-red-500' : ''}
            />
            {errors.week_start_date && (
              <p className="text-sm text-red-600">{errors.week_start_date.message}</p>
            )}
            {weekStartDate && !isMonday(weekStartDate) && (
              <div className="flex items-center gap-2 text-amber-600 text-sm">
                <AlertTriangle className="h-4 w-4" />
                <p>Warning: Selected date is not a Monday. Week will start from this date anyway.</p>
              </div>
            )}
          </div>

          {/* Template Selection */}
          <div className="space-y-2">
            <Label htmlFor="template_id" className="flex items-center gap-2">
              <Layout className="h-4 w-4 text-gray-500" />
              Schedule Template {templates.length > 0 && '(Optional)'}
            </Label>
            {loadingTemplates ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            ) : templates.length > 0 ? (
              <Select
                value={selectedTemplateId}
                onValueChange={(value) => setValue('template_id', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a template (or leave empty for default)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No template (default schedule)</SelectItem>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.schedule_name} ({template.template_type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
                <p className="text-sm text-gray-600">No templates available</p>
                <p className="text-xs text-gray-500 mt-1">
                  Create a template first, or leave empty to use default schedule
                </p>
              </div>
            )}
          </div>

          {/* Preview */}
          {weekStartDate && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-2">Schedule Preview</p>
              <div className="grid grid-cols-7 gap-1">
                {getWeekDates(weekStartDate).map((date, index) => (
                  <div
                    key={index}
                    className="text-center p-2 bg-white rounded text-xs"
                  >
                    <p className="font-semibold text-gray-700">
                      {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index]}
                    </p>
                    <p className="text-gray-500">{date.split('-')[2]}</p>
                  </div>
                ))}
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
              disabled={isLoading || !weekStartDate}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Applying...
                </>
              ) : (
                <>
                  <CalendarCheck className="h-4 w-4 mr-2" />
                  Apply Template
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Helper functions
function getNextMonday(): string {
  const today = new Date();
  const dayOfWeek = today.getDay();
  const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek) % 7;
  const nextMonday = new Date(today);
  nextMonday.setDate(today.getDate() + daysUntilMonday);
  return nextMonday.toISOString().split('T')[0];
}

function isMonday(dateStr: string): boolean {
  const date = new Date(dateStr);
  return date.getDay() === 1;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

function getWeekDates(startDate: string): string[] {
  const dates: string[] = [];
  const start = new Date(startDate);
  for (let i = 0; i < 7; i++) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    dates.push(date.toISOString().split('T')[0]);
  }
  return dates;
}
