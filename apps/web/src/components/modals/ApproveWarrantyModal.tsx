/**
 * ApproveWarrantyModal Component
 *
 * Modal for approving warranty claims with signature confirmation
 * Uses SignaturePrompt for ownership transfer before executing approve action
 * Phase 13-06 - Gap Remediation: CLEAN-04 + WARR approval flow
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
import { useActionHandler } from '@/hooks/useActionHandler';
import { useAuth } from '@/hooks/useAuth';
import SignaturePrompt from '@/components/celeste/SignaturePrompt';
import { CheckCircle, DollarSign, FileWarning } from 'lucide-react';
import type { DiffItem } from '@/components/celeste/MutationPreview';

const approveSchema = z.object({
  approved_amount: z.coerce.number().min(0).optional(),
  notes: z.string().optional(),
});

type ApproveFormData = z.infer<typeof approveSchema>;

interface ApproveWarrantyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    claim_id: string;
    claim_number: string;
    claim_title: string;
    claimed_amount?: number;
    currency: string;
  };
  onSuccess?: () => void;
}

export function ApproveWarrantyModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: ApproveWarrantyModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const { user } = useAuth();
  const [showSignature, setShowSignature] = useState(false);
  const [formData, setFormData] = useState<ApproveFormData | null>(null);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<ApproveFormData>({
    resolver: zodResolver(approveSchema) as any,
    defaultValues: {
      approved_amount: context.claimed_amount,
      notes: '',
    },
  });

  const approvedAmount = watch('approved_amount');

  // Build diffs for signature preview (using before/after per DiffItem interface)
  const diffs: DiffItem[] = [
    {
      field: 'Claim',
      before: context.claim_number,
      after: 'Approved',
    },
    {
      field: 'Amount',
      before: `${context.currency} ${context.claimed_amount?.toFixed(2) || '0.00'} (claimed)`,
      after: `${context.currency} ${(formData?.approved_amount || approvedAmount || 0).toFixed(2)} (approved)`,
    },
    {
      field: 'Status',
      before: 'Submitted',
      after: 'Approved',
    },
  ];

  const onSubmit = (data: ApproveFormData) => {
    setFormData(data);
    setShowSignature(true);
  };

  const handleSign = async () => {
    if (!formData) return;

    const response = await executeAction(
      'approve_warranty_claim' as any,
      {
        claim_id: context.claim_id,
        approved_amount: formData.approved_amount,
        notes: formData.notes,
        signature: {
          signed_by: user?.id,
          signed_at: new Date().toISOString(),
          signature_type: 'approve',
        },
      },
      {
        successMessage: `Warranty claim ${context.claim_number} approved`,
        refreshData: true,
      }
    );

    if (response?.success) {
      setShowSignature(false);
      onOpenChange(false);
      onSuccess?.();
    }
  };

  const handleCancel = () => {
    setShowSignature(false);
    setFormData(null);
  };

  // Show signature prompt when form is submitted
  if (showSignature) {
    return (
      <SignaturePrompt
        diffs={diffs}
        userName={user?.email || 'User'}
        onSign={handleSign}
        onCancel={handleCancel}
        isCommitting={isLoading}
      />
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            Approve Warranty Claim
          </DialogTitle>
          <DialogDescription>
            Review and approve this warranty claim
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-4">
          {/* Claim Summary */}
          <div className="p-4 bg-celeste-bg-secondary rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <FileWarning className="h-5 w-5 text-celeste-accent" />
              <span className="font-semibold">{context.claim_number}</span>
            </div>
            <p className="typo-body text-celeste-text-secondary">
              {context.claim_title}
            </p>
          </div>

          {/* Approved Amount */}
          <div className="space-y-2">
            <Label htmlFor="approved_amount">
              Approved Amount ({context.currency})
            </Label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-celeste-text-muted" />
              <Input
                id="approved_amount"
                type="number"
                step="0.01"
                className="pl-9"
                {...register('approved_amount')}
              />
            </div>
            {context.claimed_amount && approvedAmount !== context.claimed_amount && (
              <p className="typo-meta text-amber-600">
                Different from claimed: {context.currency} {context.claimed_amount.toFixed(2)}
              </p>
            )}
            {errors.approved_amount && (
              <p className="typo-meta text-red-600">{errors.approved_amount.message}</p>
            )}
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Approval Notes (optional)</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Add any notes about this approval..."
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              <CheckCircle className="h-4 w-4 mr-2" />
              Approve & Sign
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
