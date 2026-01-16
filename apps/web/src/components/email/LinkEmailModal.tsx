/**
 * LinkEmailModal Component
 *
 * Allows users to manually link an email thread to an object.
 *
 * V1 approach: Simple thread ID paste input
 * (No inbox browsing - that would make this an email client)
 */

'use client';

import { useState } from 'react';
import { Link2, Loader2, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useChangeLink } from '@/hooks/useEmailData';

interface LinkEmailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  objectType: string;
  objectId: string;
  existingLinkId?: string; // For change mode
}

export function LinkEmailModal({
  open,
  onOpenChange,
  objectType,
  objectId,
  existingLinkId,
}: LinkEmailModalProps) {
  const [threadId, setThreadId] = useState('');
  const [error, setError] = useState<string | null>(null);

  const changeLinkMutation = useChangeLink();

  const isChangeMode = !!existingLinkId;

  const handleSubmit = async () => {
    if (!threadId.trim()) {
      setError('Please enter a thread ID');
      return;
    }

    // Basic UUID validation
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(threadId.trim())) {
      setError('Invalid thread ID format. Please enter a valid UUID.');
      return;
    }

    setError(null);

    try {
      if (isChangeMode) {
        await changeLinkMutation.mutateAsync({
          linkId: existingLinkId!,
          newObjectType: objectType,
          newObjectId: objectId,
        });
      } else {
        // For new links, we'd call a create link endpoint
        // For V1, this is a placeholder - links are created by sync process
        setError('Manual link creation not yet available. Links are created during email sync.');
        return;
      }

      // Success
      setThreadId('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to link thread');
    }
  };

  const handleClose = () => {
    setThreadId('');
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            {isChangeMode ? 'Change Email Link' : 'Link Email Thread'}
          </DialogTitle>
          <DialogDescription>
            {isChangeMode
              ? 'Enter the thread ID to link to this work order instead.'
              : 'Enter the thread ID of the email conversation you want to link to this work order.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {/* Thread ID Input */}
          <div>
            <label
              htmlFor="thread-id"
              className="text-[13px] font-medium text-zinc-700 dark:text-zinc-300"
            >
              Thread ID
            </label>
            <input
              id="thread-id"
              type="text"
              value={threadId}
              onChange={(e) => setThreadId(e.target.value)}
              placeholder="e.g., 31e2879d-c279-416b-ac5c-20f116a63148"
              className="mt-1 w-full px-3 py-2 text-[14px] border border-zinc-200 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-[12px] text-zinc-500">
              You can find thread IDs in the email sync logs or database.
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-3 flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
              <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-[13px] text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Info Note */}
          <div className="mt-4 p-3 bg-zinc-100 dark:bg-zinc-800 rounded-md">
            <p className="text-[12px] text-zinc-600 dark:text-zinc-400">
              <strong>Note:</strong> Email threads are automatically discovered during sync.
              This manual linking option is for special cases where automatic detection
              didn&apos;t catch a relevant thread.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={changeLinkMutation.isPending}
          >
            {changeLinkMutation.isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            {isChangeMode ? 'Change Link' : 'Link Thread'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default LinkEmailModal;
