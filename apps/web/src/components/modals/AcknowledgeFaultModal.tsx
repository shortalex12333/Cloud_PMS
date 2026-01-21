/**
 * AcknowledgeFaultModal Component
 *
 * Simple confirmation modal for acknowledging a fault.
 * Acknowledging means "I see this fault and take responsibility".
 *
 * IMPORTANT: Uses actionClient (not useActionHandler) to call the correct
 * backend endpoint: POST /v1/actions/execute
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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { executeAction, ActionExecutionError } from '@/lib/actionClient';
import { useAuth } from '@/hooks/useAuth';
import { CheckCircle2, Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AcknowledgeFaultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    fault_id: string;
    fault_title: string;
    severity: string;
  };
  onSuccess?: () => void;
}

export function AcknowledgeFaultModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AcknowledgeFaultModalProps) {
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();

  const handleAcknowledge = async () => {
    if (!user?.yachtId) {
      setError('User yacht not found');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      // Call the correct backend endpoint: POST /v1/actions/execute
      // Payload format: { action, context, payload }
      const result = await executeAction(
        'acknowledge_fault',
        { yacht_id: user.yachtId },
        { fault_id: context.fault_id, note: note || undefined }
      );

      if (result?.status === 'success') {
        onSuccess?.();
        onOpenChange(false);
        setNote('');
      } else {
        setError(result?.message || 'Failed to acknowledge fault');
      }
    } catch (e) {
      if (e instanceof ActionExecutionError) {
        setError(e.message);
      } else {
        setError(e instanceof Error ? e.message : 'Failed to acknowledge fault');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500';
      case 'high':
        return 'text-orange-500';
      case 'medium':
        return 'text-yellow-500';
      default:
        return 'text-blue-500';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            Acknowledge Fault
          </DialogTitle>
          <DialogDescription>
            Acknowledging this fault means you&apos;ve seen it and are taking responsibility.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Fault Info */}
          <div className="rounded-lg bg-zinc-50 dark:bg-zinc-800/50 p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className={cn('h-5 w-5 mt-0.5', getSeverityColor(context.severity))} />
              <div>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">
                  {context.fault_title}
                </p>
                <p className="text-sm text-zinc-500 capitalize">
                  {context.severity} severity
                </p>
              </div>
            </div>
          </div>

          {/* Optional Note */}
          <div className="space-y-2">
            <Label htmlFor="note">Add a note (optional)</Label>
            <Textarea
              id="note"
              placeholder="Any initial observations or planned actions..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAcknowledge}
            disabled={isLoading}
            className="bg-green-600 hover:bg-green-700"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Acknowledging...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Acknowledge
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
