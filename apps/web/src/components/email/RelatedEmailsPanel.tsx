/**
 * RelatedEmailsPanel Component
 *
 * Shows email threads linked to a context object (work order, equipment, etc.)
 *
 * Design principles:
 * - NOT an inbox - this is a "related evidence panel"
 * - Shows link confidence (why this thread is linked)
 * - Allows explicit user actions (accept/change/unlink)
 * - Fails gracefully when feature is disabled
 */

'use client';

import { useState } from 'react';
import { Mail, ChevronDown, ChevronRight, Link2, AlertCircle, Loader2, Settings, RefreshCw, AlertTriangle } from 'lucide-react';
import { useRelatedThreads, useEmailFeatureEnabled, useWatcherStatus, type EmailThread, type LinkConfidence } from '@/hooks/useEmailData';
import { useSurface } from '@/contexts/SurfaceContext';
import { EmailThreadViewer } from './EmailThreadViewer';
import { EmailLinkActions } from './EmailLinkActions';
import { LinkEmailModal } from './LinkEmailModal';
import { cn, formatRelativeTime } from '@/lib/utils';
import { openSettingsModal } from '@/lib/settingsModal';

interface RelatedEmailsPanelProps {
  objectType: string;
  objectId: string;
  className?: string;
}

export function RelatedEmailsPanel({ objectType, objectId, className }: RelatedEmailsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const [selectedThreadForLinking, setSelectedThreadForLinking] = useState<{id: string; subject: string} | null>(null);

  const { showEmail } = useSurface();
  const { enabled: featureEnabled } = useEmailFeatureEnabled();
  const { data: watcherStatus } = useWatcherStatus();
  const { data, isLoading, error, refetch } = useRelatedThreads(objectType, objectId);

  // Feature disabled state - fail closed with CTA
  if (!featureEnabled) {
    return (
      <div className={cn('celeste-card p-3', className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-400">
            <Mail className="h-4 w-4" />
            <span className="text-[13px]">Email integration is off</span>
          </div>
          <button
            onClick={openSettingsModal}
            className="inline-flex items-center gap-1 text-[12px] text-blue-500 hover:text-blue-600 transition-colors"
          >
            <Settings className="h-3 w-3" />
            Connect Outlook in Settings
          </button>
        </div>
      </div>
    );
  }

  // Not connected state - no watcher configured
  if (watcherStatus && !watcherStatus.is_connected) {
    return (
      <div className={cn('celeste-card p-3', className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-400">
            <Mail className="h-4 w-4" />
            <span className="text-[13px]">Outlook not connected</span>
          </div>
          <button
            onClick={openSettingsModal}
            className="inline-flex items-center gap-1 text-[12px] text-blue-500 hover:text-blue-600 transition-colors"
          >
            <Settings className="h-3 w-3" />
            Connect Outlook in Settings
          </button>
        </div>
      </div>
    );
  }

  const threads = data?.threads || [];
  const hasThreads = threads.length > 0;

  return (
    <div className={cn('celeste-card', className)}>
      {/* Header - Collapsible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-zinc-500" />
          <span className="text-[14px] font-medium text-zinc-700 dark:text-zinc-300">
            Related Emails
          </span>
          {hasThreads && (
            <span className="text-[12px] text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded">
              {threads.length}
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-zinc-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-zinc-400" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-zinc-100 dark:border-zinc-800">
          {/* Degraded Mode Warning */}
          {watcherStatus?.sync_status === 'degraded' && (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-100 dark:border-amber-800/50">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-amber-700 dark:text-amber-400">
                    Email sync degraded
                    {watcherStatus.last_sync_error && (
                      <span className="text-amber-600 dark:text-amber-500">
                        : {watcherStatus.last_sync_error}
                      </span>
                    )}
                  </p>
                  <button
                    onClick={openSettingsModal}
                    className="inline-flex items-center gap-1 mt-1 text-[12px] text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 transition-colors"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Reconnect in Settings
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-4 text-center">
              <AlertCircle className="h-5 w-5 text-amber-500 mx-auto mb-2" />
              <p className="text-[13px] text-zinc-500">
                {error instanceof Error ? error.message : 'Failed to load related emails'}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-2 text-[13px] text-blue-500 hover:text-blue-600"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && !hasThreads && (
            <div className="p-4 text-center">
              <Mail className="h-8 w-8 text-zinc-300 mx-auto mb-2" />
              <p className="text-[13px] text-zinc-500 mb-3">
                No related email threads yet.
              </p>
              <button
                onClick={() => showEmail({ folder: 'inbox' })}
                className="inline-flex items-center gap-1.5 text-[13px] text-blue-500 hover:text-blue-600"
              >
                <Link2 className="h-3.5 w-3.5" />
                Link emails from Inbox
              </button>
            </div>
          )}

          {/* Thread List */}
          {!isLoading && !error && hasThreads && (
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {threads.map((thread) => (
                <ThreadItem
                  key={thread.id}
                  thread={thread}
                  isSelected={selectedThreadId === thread.id}
                  onClick={() => setSelectedThreadId(
                    selectedThreadId === thread.id ? null : thread.id
                  )}
                  objectType={objectType}
                  objectId={objectId}
                />
              ))}

              {/* Link More CTA */}
              <div className="p-2">
                <button
                  onClick={() => showEmail({ folder: 'inbox' })}
                  className="w-full flex items-center justify-center gap-1.5 p-2 text-[13px] text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded transition-colors"
                >
                  <Link2 className="h-3.5 w-3.5" />
                  Link more from Inbox
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Thread Viewer (slides in below selected thread) */}
      {selectedThreadId && (
        <div className="border-t border-zinc-100 dark:border-zinc-800">
          <EmailThreadViewer
            threadId={selectedThreadId}
            onClose={() => setSelectedThreadId(null)}
          />
        </div>
      )}

      {/* Link Modal - Note: This modal now expects a threadId.
          For "link another thread", users should use the Email Inbox view
          where they can select an unlinked thread and link it. */}
      {selectedThreadForLinking && (
        <LinkEmailModal
          open={isLinkModalOpen}
          onOpenChange={setIsLinkModalOpen}
          threadId={selectedThreadForLinking.id}
          threadSubject={selectedThreadForLinking.subject}
        />
      )}
    </div>
  );
}

// ============================================================================
// THREAD ITEM SUB-COMPONENT
// ============================================================================

interface ThreadItemProps {
  thread: EmailThread;
  isSelected: boolean;
  onClick: () => void;
  objectType: string;
  objectId: string;
}

function ThreadItem({ thread, isSelected, onClick, objectType, objectId }: ThreadItemProps) {
  return (
    <div className="p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
      <button
        onClick={onClick}
        className="w-full text-left"
      >
        {/* Subject */}
        <div className="flex items-start justify-between gap-2 mb-1">
          <h4 className={cn(
            'text-[14px] font-medium truncate',
            isSelected ? 'text-blue-600' : 'text-zinc-800 dark:text-zinc-200'
          )}>
            {thread.latest_subject || '(No subject)'}
          </h4>
          <ConfidenceBadge confidence={thread.confidence} />
        </div>

        {/* Meta Row */}
        <div className="flex items-center gap-3 text-[12px] text-zinc-500">
          <span>{thread.message_count} message{thread.message_count !== 1 ? 's' : ''}</span>
          {thread.has_attachments && (
            <span className="text-zinc-400">Has attachments</span>
          )}
          {thread.last_activity_at && (
            <span>
              {formatRelativeTime(thread.last_activity_at)}
            </span>
          )}
        </div>
      </button>

      {/* Link Actions (only show if link_id exists) */}
      {thread.link_id && (
        <div className="mt-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <EmailLinkActions
            linkId={thread.link_id}
            threadId={thread.id}
            threadSubject={thread.latest_subject || undefined}
            confidence={thread.confidence}
            objectType={objectType}
            objectId={objectId}
          />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// CONFIDENCE BADGE SUB-COMPONENT
// ============================================================================

interface ConfidenceBadgeProps {
  confidence?: LinkConfidence;
}

function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (!confidence) return null;

  const styles = {
    deterministic: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
      label: 'Auto-linked',
    },
    user_confirmed: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
      label: 'Confirmed',
    },
    suggested: {
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      text: 'text-amber-700 dark:text-amber-400',
      label: 'Suggested',
    },
  };

  const style = styles[confidence] || styles.suggested;

  return (
    <span className={cn(
      'text-[11px] px-1.5 py-0.5 rounded font-medium flex-shrink-0',
      style.bg,
      style.text
    )}>
      {style.label}
    </span>
  );
}

export default RelatedEmailsPanel;
