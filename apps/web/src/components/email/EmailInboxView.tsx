/**
 * EmailInboxView Component
 *
 * Shows unlinked email threads and allows users to link them to objects.
 * This is the "Link to Work Order" feature the user requested.
 */

'use client';

import { useState } from 'react';
import { Mail, Link2, Loader2, AlertCircle, RefreshCw, ChevronLeft, ChevronRight, Inbox, CheckCircle } from 'lucide-react';
import { useInboxThreads, type EmailThread } from '@/hooks/useEmailData';
import { LinkEmailModal } from './LinkEmailModal';
import { Button } from '@/components/ui/button';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useSurfaceSafe } from '@/contexts/SurfaceContext';

interface EmailInboxViewProps {
  className?: string;
}

export function EmailInboxView({ className }: EmailInboxViewProps) {
  const surfaceContext = useSurfaceSafe();
  const [page, setPage] = useState(1);
  const [showLinked, setShowLinked] = useState(false);
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);

  const { data, isLoading, error, refetch } = useInboxThreads(page, showLinked);

  // Open email in full EmailSurface view via overlay
  // SINGLE-SURFACE: Uses SurfaceContext to show email overlay (no URL change)
  const handleOpenThread = (thread: EmailThread) => {
    if (surfaceContext) {
      surfaceContext.showEmail({ threadId: thread.id, folder: 'inbox' });
    }
  };

  const threads = data?.threads || [];
  const hasMore = data?.has_more || false;
  const total = data?.total || 0;

  const handleLinkClick = (thread: EmailThread) => {
    setSelectedThread(thread);
    setIsLinkModalOpen(true);
  };

  const handleModalClose = (open: boolean) => {
    setIsLinkModalOpen(open);
    if (!open) {
      setSelectedThread(null);
      // Refetch to update the list
      refetch();
    }
  };

  return (
    <div className={cn('space-y-4', className)} data-testid="email-inbox">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Inbox className="h-5 w-5 text-zinc-500" />
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200">
            Email Inbox
          </h2>
          <span className="text-[13px] text-zinc-500">
            {total} {showLinked ? 'total' : 'unlinked'} thread{total !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Toggle */}
          <button
            onClick={() => {
              setShowLinked(!showLinked);
              setPage(1);
            }}
            className={cn(
              'px-3 py-1.5 text-[13px] rounded-md transition-colors',
              showLinked
                ? 'bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300'
                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
            )}
          >
            {showLinked ? 'Showing All' : 'Showing Unlinked Only'}
          </button>

          {/* Refresh */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div>
              <p className="text-[14px] text-red-700 dark:text-red-400">
                {error instanceof Error ? error.message : 'Failed to load emails'}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-2 text-[13px] text-red-600 hover:text-red-700 underline"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && threads.length === 0 && (
        <div className="text-center py-12">
          <Mail className="h-12 w-12 text-zinc-300 mx-auto mb-4" />
          <h3 className="text-[16px] font-medium text-zinc-700 dark:text-zinc-300 mb-2">
            {showLinked ? 'No email threads' : 'All emails are linked!'}
          </h3>
          <p className="text-[14px] text-zinc-500 max-w-sm mx-auto">
            {showLinked
              ? 'Email threads will appear here after sync.'
              : 'All your email threads have been linked to objects. Great work!'}
          </p>
        </div>
      )}

      {/* Thread List */}
      {!isLoading && !error && threads.length > 0 && (
        <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg divide-y divide-zinc-100 dark:divide-zinc-800" data-testid="email-list">
          {threads.map((thread) => (
            <ThreadRow
              key={thread.id}
              thread={thread}
              onLinkClick={() => handleLinkClick(thread)}
              onOpenClick={() => handleOpenThread(thread)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && total > 0 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-[13px] text-zinc-500">
            Page {page} of {Math.ceil(total / (data?.page_size || 20))}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasMore}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Link Modal */}
      {selectedThread && (
        <LinkEmailModal
          open={isLinkModalOpen}
          onOpenChange={handleModalClose}
          threadId={selectedThread.id}
          threadSubject={selectedThread.latest_subject || undefined}
        />
      )}
    </div>
  );
}

// ============================================================================
// THREAD ROW SUB-COMPONENT
// ============================================================================

interface ThreadRowProps {
  thread: EmailThread;
  onLinkClick: () => void;
  onOpenClick: () => void;
}

function ThreadRow({ thread, onLinkClick, onOpenClick }: ThreadRowProps) {
  return (
    <div
      className="flex items-center gap-4 p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors cursor-pointer"
      data-testid="email-thread-item"
      onClick={onOpenClick}
    >
      {/* Email Icon */}
      <Mail className="h-5 w-5 text-zinc-400 flex-shrink-0" />

      {/* Thread Info */}
      <div className="flex-1 min-w-0">
        <h4 className="text-[14px] font-medium text-zinc-800 dark:text-zinc-200 truncate">
          {thread.latest_subject || '(No subject)'}
        </h4>
        <div className="flex items-center gap-3 mt-1 text-[12px] text-zinc-500">
          <span>{thread.message_count} message{thread.message_count !== 1 ? 's' : ''}</span>
          {thread.has_attachments && <span>Has attachments</span>}
          {thread.last_activity_at && (
            <span>{formatRelativeTime(thread.last_activity_at)}</span>
          )}
        </div>
      </div>

      {/* Link Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={(e) => {
          e.stopPropagation(); // Don't trigger row click
          onLinkClick();
        }}
        className="flex-shrink-0"
        data-testid="link-email-button"
      >
        <Link2 className="h-4 w-4 mr-1.5" />
        Link to...
      </Button>
    </div>
  );
}

export default EmailInboxView;
