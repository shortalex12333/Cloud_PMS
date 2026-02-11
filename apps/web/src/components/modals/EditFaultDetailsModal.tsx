/**
 * EditFaultDetailsModal Component
 *
 * Modal for editing fault details with status validation
 * Prevents reopening closed faults without reason
 * Phase 4 - Priority 2: Audit-Sensitive EDIT Modals
 */

'use client';

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
import { AlertCircle, AlertTriangle } from 'lucide-react';

// Validation schema
const editFaultSchema = z.object({
  fault_id: z.string().min(1, 'Fault ID is required'),
  title: z.string().min(5, 'Title must be at least 5 characters').optional(),
  description: z.string().min(20, 'Description must be at least 20 characters').optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  status: z.enum(['open', 'in_progress', 'resolved', 'closed']).optional(),
  reopening_reason: z.string().optional(),
});

type EditFaultFormData = z.infer<typeof editFaultSchema>;

interface EditFaultDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    fault_id: string;
    current_title: string;
    current_description: string;
    current_severity: 'low' | 'medium' | 'high' | 'critical';
    current_status: 'open' | 'in_progress' | 'resolved' | 'closed';
  };
  onSuccess?: () => void;
}

export function EditFaultDetailsModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditFaultDetailsModalProps) {
  const { executeAction, isLoading } = useActionHandler();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<EditFaultFormData>({
    resolver: zodResolver(editFaultSchema),
    defaultValues: {
      fault_id: context.fault_id,
      title: context.current_title,
      description: context.current_description,
      severity: context.current_severity,
      status: context.current_status,
      reopening_reason: '',
    },
  });

  const title = watch('title');
  const description = watch('description');
  const severity = watch('severity');
  const status = watch('status');
  const reopeningReason = watch('reopening_reason');

  // Check what changed
  const changes = {
    title: title !== context.current_title,
    description: description !== context.current_description,
    severity: severity !== context.current_severity,
    status: status !== context.current_status,
  };

  const hasChanges = Object.values(changes).some(Boolean);

  // Check if reopening a closed fault
  const isReopening =
    context.current_status === 'closed' &&
    status !== 'closed' &&
    changes.status;

  const isSeverityIncreasing =
    changes.severity &&
    getSeverityLevel(severity) > getSeverityLevel(context.current_severity);

  const isSeverityDecreasing =
    changes.severity &&
    getSeverityLevel(severity) < getSeverityLevel(context.current_severity);

  const onSubmit = async (data: EditFaultFormData) => {
    // Validate reopening reason
    if (isReopening && (!data.reopening_reason || data.reopening_reason.length < 15)) {
      alert('You must provide a detailed reason (min 15 characters) to reopen a closed fault.');
      return;
    }

    // Only send changed fields
    const changedFields: Record<string, any> = {};
    if (changes.title) changedFields.title = data.title;
    if (changes.description) changedFields.description = data.description;
    if (changes.severity) changedFields.severity = data.severity;
    if (changes.status) changedFields.status = data.status;

    const response = await executeAction(
      'edit_fault_details',
      {
        fault_id: data.fault_id,
        changes: changedFields,
        reopening_reason: isReopening ? data.reopening_reason : undefined,
      },
      {
        successMessage: 'Fault details updated successfully',
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-600" />
            Edit Fault Details
          </DialogTitle>
          <DialogDescription>
            Modify fault information. Reopening closed faults requires a detailed reason.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Reopening Warning */}
          {isReopening && (
            <div className="p-4 bg-red-50 border border-red-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-700 mt-0.5" />
                <div>
                  <p className="font-semibold text-red-900">Reopening Closed Fault</p>
                  <p className="text-sm text-red-800 mt-1">
                    You are reopening a fault that was previously closed. You MUST provide a
                    detailed reason below (minimum 15 characters).
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Severity Increase Warning */}
          {isSeverityIncreasing && (
            <div className="p-4 bg-orange-50 border border-orange-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-orange-700 mt-0.5" />
                <div>
                  <p className="font-semibold text-orange-900">Severity Increase</p>
                  <p className="text-sm text-orange-800 mt-1">
                    You are increasing the severity from{' '}
                    <span className="font-bold uppercase">{context.current_severity}</span> to{' '}
                    <span className="font-bold uppercase">{severity}</span>. This may trigger
                    additional notifications.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Fault Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              {...register('title')}
              className={errors.title ? 'border-red-500' : ''}
            />
            {errors.title && (
              <p className="text-sm text-red-600">{errors.title.message}</p>
            )}
            {changes.title && (
              <p className="text-xs text-orange-600">
                Changed from: "{context.current_title}"
              </p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Description <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              {...register('description')}
              rows={5}
              className={errors.description ? 'border-red-500' : ''}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
            {changes.description && (
              <p className="text-xs text-orange-600">Description has been modified</p>
            )}
          </div>

          {/* Severity */}
          <div className="space-y-2">
            <Label htmlFor="severity">Severity</Label>
            <Select value={severity} onValueChange={(value) => setValue('severity', value as any)}>
              <SelectTrigger className={getSeverityColor(severity)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low - Minor issue, no immediate action needed</SelectItem>
                <SelectItem value="medium">
                  Medium - Moderate issue, address soon
                </SelectItem>
                <SelectItem value="high">High - Serious issue, priority action</SelectItem>
                <SelectItem value="critical">
                  Critical - Emergency, immediate action required
                </SelectItem>
              </SelectContent>
            </Select>
            {changes.severity && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Previous:</span>
                <span className={`font-medium ${getSeverityTextColor(context.current_severity)}`}>
                  {context.current_severity.toUpperCase()}
                </span>
                <span className="text-muted-foreground">→</span>
                <span className={`font-medium ${getSeverityTextColor(severity)}`}>
                  {severity?.toUpperCase()}
                </span>
                {isSeverityIncreasing && <span className="text-red-600">⬆ INCREASED</span>}
                {isSeverityDecreasing && <span className="text-green-600">⬇ DECREASED</span>}
              </div>
            )}
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(value) => setValue('status', value as any)}>
              <SelectTrigger className={getStatusColor(status)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Open - Reported, not yet assigned</SelectItem>
                <SelectItem value="in_progress">
                  In Progress - Currently being worked on
                </SelectItem>
                <SelectItem value="resolved">Resolved - Fixed, awaiting verification</SelectItem>
                <SelectItem value="closed">Closed - Verified and complete</SelectItem>
              </SelectContent>
            </Select>
            {changes.status && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Previous:</span>
                <span className={`font-medium ${getStatusTextColor(context.current_status)}`}>
                  {context.current_status.toUpperCase().replace('_', ' ')}
                </span>
                <span className="text-muted-foreground">→</span>
                <span className={`font-medium ${getStatusTextColor(status)}`}>
                  {status?.toUpperCase().replace('_', ' ')}
                </span>
              </div>
            )}
          </div>

          {/* Reopening Reason (only shown when reopening closed fault) */}
          {isReopening && (
            <div className="space-y-2">
              <Label htmlFor="reopening_reason">
                Reason for Reopening <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="reopening_reason"
                {...register('reopening_reason')}
                placeholder="Explain in detail why this closed fault needs to be reopened (minimum 15 characters)..."
                rows={4}
                className="border-red-300"
              />
              {reopeningReason && reopeningReason.length < 15 && (
                <p className="text-sm text-red-600">
                  Reason must be at least 15 characters ({reopeningReason.length}/15)
                </p>
              )}
            </div>
          )}

          {/* Change Summary */}
          {hasChanges && (
            <div
              className={`p-4 border rounded-lg ${
                isReopening
                  ? 'bg-red-50 border-red-300'
                  : isSeverityIncreasing
                  ? 'bg-orange-50 border-orange-300'
                  : 'bg-blue-50 border-blue-300'
              }`}
            >
              <p
                className={`text-sm font-medium ${
                  isReopening
                    ? 'text-red-900'
                    : isSeverityIncreasing
                    ? 'text-orange-900'
                    : 'text-blue-900'
                }`}
              >
                {Object.values(changes).filter(Boolean).length} field(s) will be updated.
                {isReopening
                  ? ' HIGH severity audit log will be created (fault reopening).'
                  : ' MEDIUM severity audit log will be created.'}
              </p>
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
              disabled={isLoading || !hasChanges}
              variant={isReopening ? 'destructive' : 'default'}
            >
              {isLoading ? 'Updating...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Helper functions
function getSeverityLevel(severity?: string): number {
  switch (severity) {
    case 'low':
      return 1;
    case 'medium':
      return 2;
    case 'high':
      return 3;
    case 'critical':
      return 4;
    default:
      return 0;
  }
}

function getSeverityColor(severity?: string): string {
  switch (severity) {
    case 'low':
      return 'border-celeste-border bg-celeste-bg-primary';
    case 'medium':
      return 'border-yellow-300 bg-yellow-50';
    case 'high':
      return 'border-orange-300 bg-orange-50';
    case 'critical':
      return 'border-red-300 bg-red-50';
    default:
      return '';
  }
}

function getSeverityTextColor(severity?: string): string {
  switch (severity) {
    case 'low':
      return 'text-celeste-text-secondary';
    case 'medium':
      return 'text-yellow-700';
    case 'high':
      return 'text-orange-700';
    case 'critical':
      return 'text-red-700';
    default:
      return '';
  }
}

function getStatusColor(status?: string): string {
  switch (status) {
    case 'open':
      return 'border-blue-300 bg-blue-50';
    case 'in_progress':
      return 'border-yellow-300 bg-yellow-50';
    case 'resolved':
      return 'border-green-300 bg-green-50';
    case 'closed':
      return 'border-celeste-border bg-celeste-bg-primary';
    default:
      return '';
  }
}

function getStatusTextColor(status?: string): string {
  switch (status) {
    case 'open':
      return 'text-blue-700';
    case 'in_progress':
      return 'text-yellow-700';
    case 'resolved':
      return 'text-green-700';
    case 'closed':
      return 'text-celeste-text-secondary';
    default:
      return '';
  }
}
