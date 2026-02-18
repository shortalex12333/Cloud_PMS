'use client';

import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { toast } from 'sonner';

interface FinishButtonProps {
  mode: 'edit' | 'review';
  hasUserSignature: boolean;
  hasHodSignature: boolean;
  onSubmit: () => Promise<void>;
  onCountersign: () => Promise<void>;
  isLoading: boolean;
}

export function FinishButton({
  mode,
  hasUserSignature,
  hasHodSignature,
  onSubmit,
  onCountersign,
  isLoading
}: FinishButtonProps) {
  const isEditMode = mode === 'edit';
  const isReviewMode = mode === 'review';

  const handleClick = async () => {
    if (isEditMode) {
      if (!hasUserSignature) {
        toast.error('You must sign the handover before submitting');
        // Scroll to signature section
        document.getElementById('signature-required-message')?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
        return;
      }
      await onSubmit();
    } else if (isReviewMode) {
      if (!hasHodSignature) {
        toast.error('You must countersign before approving');
        return;
      }
      await onCountersign();
    }
  };

  const buttonLabel = isEditMode
    ? 'Finish and Submit'
    : 'Approve and Countersign';

  const isDisabled = isEditMode
    ? !hasUserSignature
    : !hasHodSignature;

  return (
    <PrimaryButton
      onClick={handleClick}
      disabled={isDisabled || isLoading}
      loading={isLoading}
    >
      {isLoading ? 'Processing...' : buttonLabel}
    </PrimaryButton>
  );
}
