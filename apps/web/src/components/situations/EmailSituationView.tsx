'use client';

/**
 * EmailSituationView
 *
 * Renders email thread as "evidence" within the situation framework.
 * Shows thread metadata, messages with fetch-on-click for original content,
 * and linked operational objects.
 *
 * Per doctrine: Email is evidence, not inbox. Content fetched on demand,
 * never stored locally.
 */

import React from 'react';
import { X, Mail, Link2, Loader2, AlertCircle } from 'lucide-react';
import type { SituationContext } from '@/types/situation';
import { EmailThreadViewer } from '@/components/email/EmailThreadViewer';
import { useThread } from '@/hooks/useEmailData';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

interface EmailSituationViewProps {
  situation: SituationContext;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function EmailSituationView({
  situation,
  onClose,
  onAction,
}: EmailSituationViewProps) {
  const threadId = situation.primary_entity_id;
  const { data: thread, isLoading, error } = useThread(threadId);

  // Handle loading state
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-white dark:bg-zinc-900 rounded-celeste-lg shadow-[0_25px_50px_-12px_rgba(0,0,0,0.4)] p-8">
          <Loader2 className="h-8 w-8 animate-spin text-purple-500 mx-auto" />
          <p className="mt-4 text-zinc-600 dark:text-zinc-400 text-center">
            Loading email thread...
          </p>
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-white dark:bg-zinc-900 rounded-celeste-lg shadow-[0_25px_50px_-12px_rgba(0,0,0,0.4)] p-8 max-w-md">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
          <p className="mt-4 text-zinc-800 dark:text-zinc-200 text-center font-medium">
            Failed to load email thread
          </p>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400 text-center typo-body">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <button
            onClick={onClose}
            className="mt-4 w-full py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors text-zinc-700 dark:text-zinc-300"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  if (!thread) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[8vh] pb-8 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-3xl mx-4">
        <div className="bg-white dark:bg-zinc-900 rounded-celeste-lg shadow-[0_25px_50px_-12px_rgba(0,0,0,0.4)] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-purple-50 dark:bg-purple-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500 rounded-lg">
                <Mail className="h-5 w-5 text-celeste-text-title" />
              </div>
              <div>
                <h2 className="typo-title font-semibold text-zinc-900 dark:text-zinc-100">
                  Email Thread
                </h2>
                <p className="typo-body text-zinc-500 dark:text-zinc-400">
                  {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
                  {thread.has_attachments && ' • Has attachments'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="btn-icon h-8 w-8"
            >
              <X className="w-[18px] h-[18px]" />
            </button>
          </div>

          {/* Thread Viewer */}
          <div className="max-h-[60vh] overflow-y-auto">
            <EmailThreadViewer threadId={threadId} />
          </div>

          {/* Linked Objects Section */}
          <LinkedObjectsSection threadId={threadId} onAction={onAction} />

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-[#171717]">
            <button
              onClick={onClose}
              className="px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// LINKED OBJECTS SUB-COMPONENT
// ============================================================================

interface LinkedObjectsSectionProps {
  threadId: string;
  onAction?: (action: string, payload: any) => void;
}

function LinkedObjectsSection({ threadId, onAction }: LinkedObjectsSectionProps) {
  // This would query email_links for objects linked to this thread
  // For now, show placeholder UI

  return (
    <div className="px-5 py-4 border-t border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center gap-2 mb-3">
        <Link2 className="h-4 w-4 text-zinc-400" />
        <span className="typo-body font-medium text-zinc-700 dark:text-zinc-300">
          Linked Objects
        </span>
      </div>

      {/* Placeholder - would show actual linked objects */}
      <div className="typo-body text-zinc-500 dark:text-zinc-400 italic">
        No linked objects yet. Email threads can be linked to work orders, equipment, and faults.
      </div>
    </div>
  );
}
