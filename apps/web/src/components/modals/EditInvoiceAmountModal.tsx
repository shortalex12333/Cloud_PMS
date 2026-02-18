/**
 * EditInvoiceAmountModal Component
 *
 * AUDIT-SENSITIVE modal for editing invoice amounts
 * Requires mandatory reason field and creates HIGH severity audit logs
 * Triggers email notifications for changes >$500 or >10%
 * Phase 4 - Priority 2: Audit-Sensitive EDIT Modals
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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useActionHandler } from '@/hooks/useActionHandler';
import { DollarSign, AlertTriangle, Shield } from 'lucide-react';

// Validation schema - REASON IS REQUIRED
const editInvoiceAmountSchema = z.object({
  purchase_id: z.string().min(1, 'Purchase ID is required'),
  invoice_id: z.string().min(1, 'Invoice ID is required'),
  old_amount: z.coerce.number(),
  new_amount: z.coerce.number().min(0, 'Amount must be positive'),
  reason: z.string().min(15, 'Reason must be at least 15 characters - explain the change in detail'),
});

type EditInvoiceAmountFormData = z.infer<typeof editInvoiceAmountSchema>;

interface EditInvoiceAmountModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    purchase_id: string;
    invoice_id: string;
    invoice_number: string;
    current_amount: number;
    supplier?: string;
  };
  onSuccess?: () => void;
}

export function EditInvoiceAmountModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: EditInvoiceAmountModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [showNotificationWarning, setShowNotificationWarning] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<EditInvoiceAmountFormData>({
    resolver: zodResolver(editInvoiceAmountSchema) as any,
    defaultValues: {
      purchase_id: context.purchase_id,
      invoice_id: context.invoice_id,
      old_amount: context.current_amount,
      new_amount: context.current_amount,
      reason: '',
    },
  });

  const newAmount = watch('new_amount');
  const oldAmount = context.current_amount;

  const difference = newAmount - oldAmount;
  const absoluteDifference = Math.abs(difference);
  const percentageChange = oldAmount !== 0 ? (difference / oldAmount) * 100 : 0;

  // Check if notification will be triggered
  const willTriggerNotification = absoluteDifference > 500 || Math.abs(percentageChange) > 10;

  useEffect(() => {
    setShowNotificationWarning(willTriggerNotification);
  }, [willTriggerNotification]);

  const onSubmit = async (data: EditInvoiceAmountFormData) => {
    const response = await executeAction(
      'edit_invoice_amount',
      data,
      {
        successMessage: 'Invoice amount updated (audit log created)',
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

  const getChangeColor = () => {
    if (difference > 0) return 'text-red-700';
    if (difference < 0) return 'text-green-700';
    return 'text-txt-secondary';
  };

  const getChangeSymbol = () => {
    if (difference > 0) return '+';
    return '';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-600" />
            Edit Invoice Amount
          </DialogTitle>
          <DialogDescription>
            This is an audit-sensitive operation. All changes are logged with HIGH severity
            and require a detailed justification.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
          {/* Invoice Information */}
          <div className="p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-700 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-900">Audit-Sensitive Edit</h3>
                <p className="text-sm text-yellow-800 mt-1">
                  This action creates a HIGH severity audit log and notifies management
                  if the change exceeds $500 or 10%.
                </p>
              </div>
            </div>
          </div>

          {/* Invoice Details */}
          <div className="p-4 bg-surface-primary border border-surface-border rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-txt-primary">
                  Invoice: {context.invoice_number}
                </p>
                {context.supplier && (
                  <p className="text-sm text-txt-secondary">
                    Supplier: {context.supplier}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Amount Changes */}
          <div className="space-y-4">
            {/* Current Amount (Read-Only) */}
            <div className="space-y-2">
              <Label htmlFor="old_amount">Current Amount</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-tertiary" />
                <Input
                  id="old_amount"
                  type="number"
                  step="0.01"
                  {...register('old_amount')}
                  readOnly
                  className="pl-8 bg-surface-elevated cursor-not-allowed"
                />
              </div>
            </div>

            {/* New Amount */}
            <div className="space-y-2">
              <Label htmlFor="new_amount">
                New Amount <span className="text-red-500">*</span>
              </Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-tertiary" />
                <Input
                  id="new_amount"
                  type="number"
                  step="0.01"
                  min="0"
                  {...register('new_amount')}
                  className={`pl-8 ${errors.new_amount ? 'border-red-500' : ''}`}
                />
              </div>
              {errors.new_amount && (
                <p className="text-sm text-red-600">{errors.new_amount.message}</p>
              )}
            </div>

            {/* Change Summary */}
            {difference !== 0 && (
              <div className={`p-4 border rounded-lg ${
                willTriggerNotification
                  ? 'bg-red-50 border-red-300'
                  : 'bg-brand-interactive/10 border-brand-interactive/20'
              }`}>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-txt-secondary">Change:</span>
                    <span className={`text-lg font-bold ${getChangeColor()}`}>
                      {getChangeSymbol()}${absoluteDifference.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-txt-secondary">Percentage:</span>
                    <span className={`text-lg font-bold ${getChangeColor()}`}>
                      {getChangeSymbol()}{Math.abs(percentageChange).toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Reason (REQUIRED) */}
          <div className="space-y-2">
            <Label htmlFor="reason" className="flex items-center gap-2">
              Reason for Change <span className="text-red-500">*</span>
              <span className="text-xs text-txt-tertiary">(Min 15 characters)</span>
            </Label>
            <Textarea
              id="reason"
              {...register('reason')}
              placeholder="Provide a detailed explanation for this invoice amount change. Include what caused the discrepancy and why this correction is necessary..."
              rows={5}
              className={errors.reason ? 'border-red-500' : ''}
            />
            {errors.reason && (
              <p className="text-sm text-red-600">{errors.reason.message}</p>
            )}
            <p className="text-xs text-txt-tertiary">
              This reason will be permanently recorded in the audit log and may be reviewed
              during audits.
            </p>
          </div>

          {/* Notification Warning */}
          {showNotificationWarning && (
            <div className="p-4 bg-orange-50 border border-orange-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-orange-700 mt-0.5" />
                <div>
                  <p className="font-semibold text-orange-900">
                    Management Notification Will Be Sent
                  </p>
                  <p className="text-sm text-orange-800 mt-1">
                    This change exceeds the notification threshold (${500} or 10%). An email
                    will be sent to management for review.
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
              disabled={isLoading || difference === 0}
              variant={willTriggerNotification ? 'destructive' : 'default'}
            >
              {isLoading
                ? 'Updating...'
                : willTriggerNotification
                ? 'Update & Notify Management'
                : 'Update Amount'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
