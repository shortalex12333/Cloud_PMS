// @ts-nocheck - Phase 4: Zod v4/hookform resolver compatibility
/**
 * ComplianceWarningModal Component
 *
 * Modal for viewing and managing compliance warnings
 * MLC 2006 violations - acknowledge (crew) or dismiss (HOD+)
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
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  AlertTriangle,
  Loader2,
  Calendar,
  User,
  CheckCircle2,
  ShieldCheck,
  Clock,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema for dismissing (HOD+ only)
const dismissWarningSchema = z.object({
  warning_id: z.string().min(1, 'Warning ID is required'),
  hod_justification: z.string().min(20, 'Justification must be at least 20 characters'),
  dismissed_by_role: z.string().min(1, 'Role is required'),
});

type DismissWarningFormData = z.infer<typeof dismissWarningSchema>;

interface ComplianceWarningModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  warning: {
    id: string;
    user_id: string;
    user_name?: string;
    record_date: string;
    violation_type: string;
    total_rest_hours: number;
    description: string;
    status: 'active' | 'acknowledged' | 'dismissed';
    acknowledged_at?: string;
    dismissed_at?: string;
    dismissed_by?: string;
    hod_justification?: string;
  };
  mode: 'view' | 'acknowledge' | 'dismiss';
  userRole: string;
  onSuccess?: () => void;
}

const VIOLATION_TYPES = {
  insufficient_rest: {
    label: 'Insufficient Rest',
    description: 'Less than 10 hours rest in 24-hour period',
    severity: 'high',
  },
  insufficient_continuous: {
    label: 'Insufficient Continuous Rest',
    description: 'Less than 6 hours continuous rest',
    severity: 'high',
  },
  excessive_work: {
    label: 'Excessive Work Hours',
    description: 'More than 14 hours work in 24-hour period',
    severity: 'medium',
  },
  weekly_limit: {
    label: 'Weekly Rest Limit',
    description: 'Less than 77 hours rest in 7-day period',
    severity: 'high',
  },
};

export function ComplianceWarningModal({
  open,
  onOpenChange,
  warning,
  mode,
  userRole,
  onSuccess,
}: ComplianceWarningModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [acknowledging, setAcknowledging] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<DismissWarningFormData>({
    resolver: zodResolver(dismissWarningSchema),
    defaultValues: {
      warning_id: warning.id,
      hod_justification: '',
      dismissed_by_role: userRole,
    },
  });

  const handleAcknowledge = async () => {
    setAcknowledging(true);
    try {
      const response = await executeAction(
        'acknowledge_warning',
        {
          warning_id: warning.id,
        },
        {
          successMessage: 'Warning acknowledged',
          refreshData: true,
        }
      );

      if (response?.success) {
        onOpenChange(false);
        onSuccess?.();
      }
    } catch (error) {
      console.error('Failed to acknowledge warning:', error);
    } finally {
      setAcknowledging(false);
    }
  };

  const onSubmitDismiss = async (data: DismissWarningFormData) => {
    const response = await executeAction(
      'dismiss_warning',
      {
        warning_id: data.warning_id,
        hod_justification: data.hod_justification,
        dismissed_by_role: data.dismissed_by_role,
      },
      {
        successMessage: 'Warning dismissed',
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

  const violationType = VIOLATION_TYPES[warning.violation_type as keyof typeof VIOLATION_TYPES] || {
    label: warning.violation_type,
    description: 'Compliance violation',
    severity: 'medium',
  };

  const isHODPlus = ['chief_engineer', 'chief_officer', 'chief_steward', 'eto', 'purser', 'captain', 'manager'].includes(userRole);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Compliance Warning
          </DialogTitle>
          <DialogDescription>
            MLC 2006 Hours of Rest Violation
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {/* Warning Status */}
          <div className={cn(
            'p-4 rounded-lg border flex items-center gap-3',
            warning.status === 'active'
              ? 'bg-red-50 border-red-200'
              : warning.status === 'acknowledged'
              ? 'bg-amber-50 border-amber-200'
              : 'bg-celeste-bg-primary border-celeste-border'
          )}>
            {warning.status === 'active' ? (
              <AlertTriangle className="h-6 w-6 text-red-600" />
            ) : warning.status === 'acknowledged' ? (
              <Clock className="h-6 w-6 text-amber-600" />
            ) : (
              <CheckCircle2 className="h-6 w-6 text-celeste-text-secondary" />
            )}
            <div className="flex-1">
              <p className={cn(
                'font-semibold text-lg capitalize',
                warning.status === 'active'
                  ? 'text-red-800'
                  : warning.status === 'acknowledged'
                  ? 'text-amber-800'
                  : 'text-celeste-bg-tertiary'
              )}>
                {warning.status} Warning
              </p>
              <p className={cn(
                'text-sm',
                warning.status === 'active'
                  ? 'text-red-700'
                  : warning.status === 'acknowledged'
                  ? 'text-amber-700'
                  : 'text-celeste-text-secondary'
              )}>
                {violationType.label}
              </p>
            </div>
          </div>

          {/* Violation Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
              <div className="flex items-center gap-2 text-celeste-text-secondary mb-1">
                <Calendar className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">Date</span>
              </div>
              <p className="text-lg font-semibold text-celeste-black">
                {new Date(warning.record_date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>
            <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
              <div className="flex items-center gap-2 text-celeste-text-secondary mb-1">
                <User className="h-4 w-4" />
                <span className="text-xs font-medium uppercase">Crew Member</span>
              </div>
              <p className="text-lg font-semibold text-celeste-black">
                {warning.user_name || 'Unknown'}
              </p>
            </div>
          </div>

          {/* Rest Hours */}
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-3">
              <Clock className="h-6 w-6 text-amber-600" />
              <div>
                <p className="font-semibold text-amber-900">
                  {warning.total_rest_hours} hours of rest recorded
                </p>
                <p className="text-sm text-amber-700">
                  {violationType.description}
                </p>
              </div>
            </div>
          </div>

          {/* Description */}
          {warning.description && (
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-celeste-text-disabled" />
                Details
              </Label>
              <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
                <p className="text-sm text-celeste-text-secondary">{warning.description}</p>
              </div>
            </div>
          )}

          {/* Acknowledged Status */}
          {warning.status === 'acknowledged' && warning.acknowledged_at && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-amber-900">Acknowledged by crew member</p>
                <p className="text-xs text-amber-700">
                  {new Date(warning.acknowledged_at).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Dismissed Status */}
          {warning.status === 'dismissed' && warning.dismissed_at && (
            <div className="space-y-3">
              <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-celeste-text-secondary" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-celeste-black">
                    Dismissed by {warning.dismissed_by || 'HOD'}
                  </p>
                  <p className="text-xs text-celeste-text-secondary">
                    {new Date(warning.dismissed_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {warning.hod_justification && (
                <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg">
                  <p className="text-xs font-medium text-celeste-text-secondary mb-1 uppercase">Justification</p>
                  <p className="text-sm text-celeste-text-secondary">{warning.hod_justification}</p>
                </div>
              )}
            </div>
          )}

          {/* Acknowledge Action (CREW) */}
          {mode === 'acknowledge' && warning.status === 'active' && (
            <div className="pt-4 border-t">
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg mb-4">
                <p className="text-sm text-blue-800">
                  By acknowledging this warning, you confirm that you are aware of the
                  MLC compliance violation. This does not resolve the warning - only HOD or
                  Captain can dismiss it.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClose}
                  disabled={acknowledging}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleAcknowledge}
                  disabled={acknowledging}
                  className="bg-amber-600 hover:bg-amber-700"
                >
                  {acknowledging ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Acknowledging...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Acknowledge Warning
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Dismiss Action (HOD+ only) */}
          {mode === 'dismiss' && isHODPlus && warning.status !== 'dismissed' && (
            <form onSubmit={handleSubmit(onSubmitDismiss)} className="space-y-4 pt-4 border-t">
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4" />
                  <span className="font-medium">HOD Authority Required</span>
                </p>
                <p className="text-sm text-amber-700 mt-1">
                  Dismissing a warning requires a detailed justification. This action is
                  recorded in the audit log with your signature.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="hod_justification">Justification for Dismissal *</Label>
                <Textarea
                  id="hod_justification"
                  {...register('hod_justification')}
                  placeholder="Explain why this warning should be dismissed (e.g., operational necessity, emergency situation, documented exception)..."
                  rows={4}
                  className={errors.hod_justification ? 'border-red-500' : ''}
                />
                {errors.hod_justification && (
                  <p className="text-sm text-red-600">{errors.hod_justification.message}</p>
                )}
                <p className="text-xs text-celeste-text-disabled">
                  Minimum 20 characters. This is an audit-sensitive field.
                </p>
              </div>

              <div className="flex justify-end gap-2">
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
                  disabled={isLoading}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Dismissing...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-4 w-4 mr-2" />
                      Dismiss Warning
                    </>
                  )}
                </Button>
              </div>
            </form>
          )}

          {/* View Mode Actions */}
          {mode === 'view' && (
            <div className="flex justify-end pt-4 border-t">
              <Button onClick={handleClose} variant="outline">
                Close
              </Button>
            </div>
          )}

          {/* Insufficient Permissions */}
          {mode === 'dismiss' && !isHODPlus && (
            <div className="p-3 bg-celeste-bg-primary border border-celeste-border rounded-lg text-center">
              <ShieldCheck className="h-8 w-8 text-celeste-text-muted mx-auto mb-2" />
              <p className="text-sm text-celeste-text-secondary">
                Only HOD, Captain, or Manager can dismiss warnings
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
