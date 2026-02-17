/**
 * FinalizeHandoverModal Component
 *
 * Modal for finalizing handovers with signature confirmation
 * Uses SignaturePrompt for ownership transfer before executing finalize action
 * Phase 13-06 - Gap Remediation: CLEAN-04 + HAND-02
 */

'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useActionHandler } from '@/hooks/useActionHandler';
import { useAuth } from '@/hooks/useAuth';
import SignaturePrompt from '@/components/celeste/SignaturePrompt';
import { CheckCircle, FileCheck, ClipboardList } from 'lucide-react';
import type { DiffItem } from '@/components/celeste/MutationPreview';

interface FinalizeHandoverModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    handover_id: string;
    handover_title: string;
    items_count: number;
    department?: string;
  };
  onSuccess?: () => void;
}

export function FinalizeHandoverModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: FinalizeHandoverModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const { user } = useAuth();
  const [showSignature, setShowSignature] = useState(false);

  // Build diffs for signature preview (using before/after per DiffItem interface)
  const diffs: DiffItem[] = [
    {
      field: 'Handover',
      before: context.handover_title,
      after: 'Finalized',
    },
    {
      field: 'Items',
      before: `${context.items_count} items`,
      after: 'Locked for handoff',
    },
    {
      field: 'Status',
      before: 'Draft',
      after: 'Finalized',
    },
  ];

  const handleFinalize = () => {
    setShowSignature(true);
  };

  const handleSign = async () => {
    const response = await executeAction(
      'finalize_handover',
      {
        handover_id: context.handover_id,
        signature: {
          signed_by: user?.id,
          signed_at: new Date().toISOString(),
          signature_type: 'finalize',
        },
      },
      {
        successMessage: 'Handover finalized successfully',
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
  };

  // Show signature prompt when user clicks Finalize & Sign
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
            <FileCheck className="h-5 w-5 text-green-600" />
            Finalize Handover
          </DialogTitle>
          <DialogDescription>
            Review and finalize this handover for signature
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Handover Summary */}
          <div className="p-4 bg-celeste-bg-secondary rounded-lg">
            <h3 className="font-semibold text-celeste-text-primary">
              {context.handover_title}
            </h3>
            <div className="mt-2 text-sm text-celeste-text-secondary">
              <div className="flex items-center gap-2">
                <ClipboardList className="h-4 w-4" />
                <span>{context.items_count} items to hand over</span>
              </div>
              {context.department && (
                <p className="mt-1">Department: {context.department}</p>
              )}
            </div>
          </div>

          {/* Warning */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
            Finalizing will lock this handover for signature. You will not be able to edit items after finalizing.
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button onClick={handleFinalize} disabled={isLoading}>
            <CheckCircle className="h-4 w-4 mr-2" />
            Finalize & Sign
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
