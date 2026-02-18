/**
 * CompleteWorkOrderModal Component
 *
 * Modal for completing work orders with required completion data
 * Tracks actual time, parts used, completion notes, and quality checks
 * Phase 4 - Special Utility Modal
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  CheckCircle,
  Clock,
  Wrench,
  AlertTriangle,
  FileText,
  Camera,
  Package,
} from 'lucide-react';

// Validation schema
const completeWorkOrderSchema = z.object({
  work_order_id: z.string().min(1, 'Work order ID is required'),
  completion_notes: z.string().min(20, 'Completion notes must be at least 20 characters'),
  actual_hours: z.coerce.number().min(0, 'Actual hours must be positive'),
  outcome: z.enum(['completed', 'partially_completed', 'deferred']),
  quality_check_passed: z.boolean(),
  parts_used_documented: z.boolean(),
  follow_up_required: z.boolean().optional(),
  follow_up_notes: z.string().optional(),
  attachments_added: z.boolean().optional(),
});

type CompleteWorkOrderFormData = z.infer<typeof completeWorkOrderSchema>;

interface CompleteWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    work_order_id: string;
    work_order_title: string;
    estimated_hours?: number;
    assigned_to?: string;
    created_date: string;
    priority?: string;
  };
  onSuccess?: () => void;
}

export function CompleteWorkOrderModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: CompleteWorkOrderModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [showFollowUp, setShowFollowUp] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<CompleteWorkOrderFormData>({
    resolver: zodResolver(completeWorkOrderSchema) as any,
    defaultValues: {
      work_order_id: context.work_order_id,
      completion_notes: '',
      actual_hours: context.estimated_hours || 0,
      outcome: 'completed',
      quality_check_passed: false,
      parts_used_documented: false,
      follow_up_required: false,
      follow_up_notes: '',
      attachments_added: false,
    },
  });

  const actualHours = watch('actual_hours') || 0;
  const outcome = watch('outcome');
  const qualityCheckPassed = watch('quality_check_passed');
  const partsUsedDocumented = watch('parts_used_documented');
  const followUpRequired = watch('follow_up_required');

  const hoursDifference = context.estimated_hours
    ? actualHours - context.estimated_hours
    : 0;
  const isOverEstimate = hoursDifference > 0;
  const isSignificantVariance =
    context.estimated_hours && Math.abs(hoursDifference) > context.estimated_hours * 0.2;

  const canComplete =
    outcome === 'completed'
      ? qualityCheckPassed && partsUsedDocumented
      : true;

  const onSubmit = async (data: CompleteWorkOrderFormData) => {
    if (!canComplete && outcome === 'completed') {
      alert(
        'To mark as completed, you must confirm quality check passed and parts are documented.'
      );
      return;
    }

    const response = await executeAction(
      'complete_work_order',
      {
        work_order_id: data.work_order_id,
        completion_notes: data.completion_notes,
        actual_hours: data.actual_hours,
        outcome: data.outcome,
        quality_check_passed: data.quality_check_passed,
        parts_used_documented: data.parts_used_documented,
        follow_up_required: data.follow_up_required,
        follow_up_notes: data.follow_up_notes,
        completed_at: new Date().toISOString(),
      },
      {
        successMessage: `Work order ${
          data.outcome === 'completed' ? 'completed' : data.outcome.replace('_', ' ')
        } successfully`,
        refreshData: true,
      }
    );

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) {
        onSuccess();
      }
    }
  };

  const getOutcomeColor = (outcomeValue?: string) => {
    switch (outcomeValue) {
      case 'completed':
        return 'border-green-300 bg-green-50';
      case 'partially_completed':
        return 'border-yellow-300 bg-yellow-50';
      case 'deferred':
        return 'border-orange-300 bg-orange-50';
      default:
        return '';
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'critical':
        return 'text-red-700 bg-red-50 border-red-300';
      case 'high':
        return 'text-orange-700 bg-orange-50 border-orange-300';
      case 'medium':
        return 'text-yellow-700 bg-yellow-50 border-yellow-300';
      default:
        return 'text-txt-secondary bg-surface-primary border-surface-border';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            Complete Work Order
          </DialogTitle>
          <DialogDescription>
            Document completion details and close out this work order
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Work Order Context */}
          <div className="p-4 bg-brand-interactive/10 border border-brand-interactive/20 rounded-lg">
            <div className="flex items-start gap-3">
              <Wrench className="h-5 w-5 text-brand-interactive mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-brand-interactive">{context.work_order_title}</h3>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-sm text-brand-interactive">
                  <p>
                    <span className="font-medium">ID:</span> {context.work_order_id.slice(0, 8)}
                  </p>
                  {context.assigned_to && (
                    <p>
                      <span className="font-medium">Assigned:</span> {context.assigned_to}
                    </p>
                  )}
                  <p>
                    <span className="font-medium">Created:</span>{' '}
                    {new Date(context.created_date).toLocaleDateString()}
                  </p>
                  {context.estimated_hours && (
                    <p>
                      <span className="font-medium">Est. Hours:</span> {context.estimated_hours}
                    </p>
                  )}
                  {context.priority && (
                    <div className="col-span-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded border ${getPriorityColor(
                          context.priority
                        )}`}
                      >
                        {context.priority.toUpperCase()} PRIORITY
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Outcome Selection */}
          <div className="space-y-2">
            <Label htmlFor="outcome">
              Completion Outcome <span className="text-red-500">*</span>
            </Label>
            <Select value={outcome} onValueChange={(value) => setValue('outcome', value as any)}>
              <SelectTrigger className={getOutcomeColor(outcome)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="completed">
                  Completed - Work fully finished and verified
                </SelectItem>
                <SelectItem value="partially_completed">
                  Partially Completed - Some work remains
                </SelectItem>
                <SelectItem value="deferred">Deferred - Postponed to later date</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Actual Hours */}
          <div className="space-y-2">
            <Label htmlFor="actual_hours">
              Actual Hours Worked <span className="text-red-500">*</span>
            </Label>
            <Input
              id="actual_hours"
              type="number"
              min="0"
              step="0.5"
              {...register('actual_hours')}
              className={errors.actual_hours ? 'border-red-500' : ''}
            />
            {errors.actual_hours && (
              <p className="text-sm text-red-600">{errors.actual_hours.message}</p>
            )}

            {/* Time Variance Warning */}
            {context.estimated_hours && actualHours > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-txt-tertiary" />
                <span className="text-txt-secondary">
                  Estimated: {context.estimated_hours}h | Actual: {actualHours}h
                </span>
                <span
                  className={`font-medium ${
                    isOverEstimate ? 'text-orange-700' : 'text-green-700'
                  }`}
                >
                  {isOverEstimate ? '+' : ''}
                  {hoursDifference.toFixed(1)}h ({isOverEstimate ? 'over' : 'under'})
                </span>
              </div>
            )}

            {isSignificantVariance && (
              <div className="flex items-start gap-2 p-3 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800">
                <AlertTriangle className="h-4 w-4 text-orange-700 mt-0.5" />
                <p>
                  Significant variance from estimate (&gt;20%). Please explain in completion notes.
                </p>
              </div>
            )}
          </div>

          {/* Completion Notes */}
          <div className="space-y-2">
            <Label htmlFor="completion_notes">
              Completion Notes <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="completion_notes"
              {...register('completion_notes')}
              placeholder="Describe the work performed, any issues encountered, and final status..."
              rows={5}
              className={errors.completion_notes ? 'border-red-500' : ''}
            />
            {errors.completion_notes && (
              <p className="text-sm text-red-600">{errors.completion_notes.message}</p>
            )}
            {isSignificantVariance && (
              <p className="text-xs text-orange-600">
                ⚠️ Make sure to explain why actual time differed significantly from estimate
              </p>
            )}
          </div>

          {/* Quality & Documentation Checklist */}
          <div className="space-y-3 p-4 border border-surface-border rounded-lg bg-surface-primary">
            <h3 className="font-semibold text-txt-primary flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Required Checks
            </h3>

            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <Checkbox
                  id="quality_check_passed"
                  checked={qualityCheckPassed}
                  onCheckedChange={(checked) => setValue('quality_check_passed', !!checked)}
                />
                <Label
                  htmlFor="quality_check_passed"
                  className="text-sm font-normal cursor-pointer"
                >
                  Quality check passed - work meets standards
                  {outcome === 'completed' && (
                    <span className="text-red-500 ml-1">*</span>
                  )}
                </Label>
              </div>

              <div className="flex items-start gap-2">
                <Checkbox
                  id="parts_used_documented"
                  checked={partsUsedDocumented}
                  onCheckedChange={(checked) => setValue('parts_used_documented', !!checked)}
                />
                <Label
                  htmlFor="parts_used_documented"
                  className="text-sm font-normal cursor-pointer flex items-center gap-1"
                >
                  <Package className="h-3 w-3" />
                  All parts used have been logged
                  {outcome === 'completed' && (
                    <span className="text-red-500 ml-1">*</span>
                  )}
                </Label>
              </div>

              <div className="flex items-start gap-2">
                <Checkbox
                  id="attachments_added"
                  checked={watch('attachments_added')}
                  onCheckedChange={(checked) => setValue('attachments_added', !!checked)}
                />
                <Label
                  htmlFor="attachments_added"
                  className="text-sm font-normal cursor-pointer flex items-center gap-1"
                >
                  <Camera className="h-3 w-3" />
                  Photos or documents attached (if applicable)
                </Label>
              </div>
            </div>

            {outcome === 'completed' && !canComplete && (
              <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                ⚠️ To mark as completed, quality check and parts documentation are required
              </div>
            )}
          </div>

          {/* Follow-up Required */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Checkbox
                id="follow_up_required"
                checked={followUpRequired}
                onCheckedChange={(checked) => {
                  setValue('follow_up_required', !!checked);
                  setShowFollowUp(!!checked);
                }}
              />
              <Label htmlFor="follow_up_required" className="text-sm font-normal cursor-pointer">
                Follow-up work or monitoring required
              </Label>
            </div>

            {showFollowUp && (
              <div className="ml-6 space-y-2">
                <Label htmlFor="follow_up_notes" className="text-sm">
                  Follow-up Details
                </Label>
                <Textarea
                  id="follow_up_notes"
                  {...register('follow_up_notes')}
                  placeholder="Describe what follow-up is needed and when..."
                  rows={3}
                  className="text-sm"
                />
              </div>
            )}
          </div>

          {/* Completion Warning for Partially Completed/Deferred */}
          {(outcome === 'partially_completed' || outcome === 'deferred') && (
            <div className="p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-700 mt-0.5" />
                <div>
                  <p className="font-semibold text-yellow-900">
                    {outcome === 'partially_completed'
                      ? 'Partial Completion'
                      : 'Work Deferred'}
                  </p>
                  <p className="text-sm text-yellow-800 mt-1">
                    {outcome === 'partially_completed'
                      ? 'A new work order will be created for the remaining work. Make sure to document what was completed and what remains.'
                      : 'This work order will be closed and can be reopened later. Document the reason for deferral in completion notes.'}
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
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || (outcome === 'completed' && !canComplete)}
              variant={outcome === 'completed' ? 'default' : 'secondary'}
            >
              {isLoading ? (
                'Processing...'
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {outcome === 'completed'
                    ? 'Complete Work Order'
                    : outcome === 'partially_completed'
                    ? 'Mark Partially Complete'
                    : 'Defer Work Order'}
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
