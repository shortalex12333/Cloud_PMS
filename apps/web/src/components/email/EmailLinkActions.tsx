/**
 * EmailLinkActions Component
 *
 * Actions for managing email-object links:
 * - Accept (for suggested links)
 * - Change link target
 * - Unlink
 *
 * All actions require explicit user confirmation.
 */

'use client';

import { useState } from 'react';
import { Check, RefreshCw, Unlink, Loader2, AlertCircle } from 'lucide-react';
import { useAcceptLink, useRemoveLink, type LinkConfidence } from '@/hooks/useEmailData';
import { LinkEmailModal } from './LinkEmailModal';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmailLinkActionsProps {
  linkId: string;
  threadId: string;
  threadSubject?: string;
  confidence?: LinkConfidence;
  objectType: string;
  objectId: string;
}

export function EmailLinkActions({
  linkId,
  threadId,
  threadSubject,
  confidence,
  objectType,
  objectId,
}: EmailLinkActionsProps) {
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [showUnlinkConfirm, setShowUnlinkConfirm] = useState(false);

  const acceptMutation = useAcceptLink();
  const removeMutation = useRemoveLink();

  const isSuggested = confidence === 'suggested';

  const handleAccept = async () => {
    try {
      await acceptMutation.mutateAsync(linkId);
    } catch (err) {
      // Error handled by mutation state
    }
  };

  const handleUnlink = async () => {
    try {
      await removeMutation.mutateAsync(linkId);
      setShowUnlinkConfirm(false);
    } catch (err) {
      // Error handled by mutation state
    }
  };

  return (
    <>
      <div className="flex items-center gap-1">
        {/* Accept Button (only for suggested links) */}
        {isSuggested && (
          <button
            onClick={handleAccept}
            disabled={acceptMutation.isPending}
            className={cn(
              'inline-flex items-center gap-1 px-2 py-1 typo-meta rounded transition-colors',
              'text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20',
              acceptMutation.isPending && 'opacity-50 cursor-not-allowed'
            )}
          >
            {acceptMutation.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Check className="h-3 w-3" />
            )}
            Accept
          </button>
        )}

        {/* Change Link Button */}
        <button
          onClick={() => setShowChangeModal(true)}
          className="inline-flex items-center gap-1 px-2 py-1 typo-meta rounded transition-colors text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
        >
          <RefreshCw className="h-3 w-3" />
          Change
        </button>

        {/* Unlink Button */}
        <button
          onClick={() => setShowUnlinkConfirm(true)}
          className="inline-flex items-center gap-1 px-2 py-1 typo-meta rounded transition-colors text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
        >
          <Unlink className="h-3 w-3" />
          Unlink
        </button>

        {/* Error indicator */}
        {(acceptMutation.isError || removeMutation.isError) && (
          <span className="text-red-500 typo-meta">
            <AlertCircle className="h-3 w-3 inline mr-0.5" />
            Failed
          </span>
        )}
      </div>

      {/* Change Link Modal */}
      <LinkEmailModal
        open={showChangeModal}
        onOpenChange={setShowChangeModal}
        threadId={threadId}
        threadSubject={threadSubject}
        existingLinkId={linkId}
      />

      {/* Unlink Confirmation Dialog */}
      <UnlinkConfirmDialog
        open={showUnlinkConfirm}
        onOpenChange={setShowUnlinkConfirm}
        onConfirm={handleUnlink}
        isLoading={removeMutation.isPending}
        error={removeMutation.error}
      />
    </>
  );
}

// ============================================================================
// UNLINK CONFIRM DIALOG SUB-COMPONENT
// ============================================================================

interface UnlinkConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isLoading: boolean;
  error: Error | null;
}

function UnlinkConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  isLoading,
  error,
}: UnlinkConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Unlink className="h-5 w-5 text-red-500" />
            Unlink Email Thread
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to unlink this email thread? The email will no longer
            appear in the related emails panel for this work order.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
            <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="typo-meta text-red-600 dark:text-red-400">
              {error.message || 'Failed to unlink thread'}
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Unlink
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default EmailLinkActions;
