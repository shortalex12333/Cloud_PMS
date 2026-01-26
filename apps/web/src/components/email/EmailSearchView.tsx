'use client';

/**
 * EmailSearchView Component - Outlook-Style Three-Column Layout
 *
 * Dark-themed email search interface with:
 * - Left panel: Thread list with sender info
 * - Center panel: Selected message body (full HTML render)
 * - Right panel: Attachments for selected message
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Search,
  X,
  Mail,
  Paperclip,
  ChevronRight,
  Loader2,
  ArrowLeft,
  Inbox,
  Send,
  Download,
  AlertCircle,
  User,
  RefreshCw,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import {
  useInboxThreads,
  useEmailSearch,
  useThread,
  useMessageContent,
  useThreadLinks,
  useEmailBackfill,
  downloadAndSaveAttachment,
  useWatcherStatus,
  useOutlookConnection,
  type EmailThread,
  type EmailMessage,
  type MessageContent as MessageContentType,
  type EmailSearchResult,
} from '@/hooks/useEmailData';
import { cn, formatRelativeTime } from '@/lib/utils';

// ============================================================================
// ROLLING PLACEHOLDER SUGGESTIONS
// ============================================================================

const PLACEHOLDER_SUGGESTIONS = [
  'Search by subject...',
  'Find invoice emails',
  'Quote from supplier',
  'Service report attached',
  'Work order confirmation',
  'Parts delivery update',
];

// ============================================================================
// TYPES
// ============================================================================

interface EmailSearchViewProps {
  className?: string;
}

type DirectionFilter = 'all' | 'inbound' | 'outbound';

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function EmailSearchView({ className }: EmailSearchViewProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('all');
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch threads with search and direction filter
  const { data, isLoading, error, refetch } = useInboxThreads(
    page,
    true,
    debouncedQuery,
    directionFilter === 'all' ? undefined : directionFilter
  );

  // Fetch watcher status for sync indicator
  const { data: watcherStatus } = useWatcherStatus();

  // Outlook connection status for auth recovery
  const { data: outlookStatus, initiateReconnect, isLoading: outlookLoading } = useOutlookConnection();
  const [reconnecting, setReconnecting] = useState(false);

  const threads = data?.threads || [];
  const total = data?.total || 0;
  const hasMore = data?.has_more || false;

  // Handle Outlook reconnect
  const handleReconnect = useCallback(async () => {
    setReconnecting(true);
    const authUrl = await initiateReconnect();
    if (authUrl) {
      window.location.href = authUrl;
    } else {
      setReconnecting(false);
    }
  }, [initiateReconnect]);

  // Determine if we need to show reconnect banner
  const needsReconnect = !outlookLoading && outlookStatus && (!outlookStatus.isConnected || outlookStatus.isExpired);

  // Semantic search (uses /email/search endpoint when query present)
  const {
    data: searchData,
    isLoading: searchLoading,
    error: searchError,
  } = useEmailSearch(debouncedQuery, {
    direction: directionFilter === 'all' ? undefined : directionFilter,
    limit: 20,
  });

  // Use search results when searching, inbox otherwise
  const isSearching = debouncedQuery.length >= 2;
  const displayThreads = isSearching
    ? (searchData?.results || []).map((r) => ({
        id: r.thread_id,
        provider_conversation_id: '',
        latest_subject: r.subject,
        message_count: 1,
        has_attachments: r.has_attachments,
        source: '',
        first_message_at: null,
        last_activity_at: r.sent_at,
      }))
    : threads;
  const displayLoading = isSearching ? searchLoading : isLoading;
  const displayError = isSearching ? searchError : error;

  // Backfill hook for import
  const {
    status: backfillStatus,
    isRunning: isBackfilling,
    triggerBackfill,
    isTriggering,
  } = useEmailBackfill();

  // Get selected thread details
  const { data: selectedThread, isLoading: threadLoading } = useThread(selectedThreadId);

  // Get selected message content
  const { data: selectedContent, isLoading: contentLoading } = useMessageContent(selectedMessageId);

  // Get links for selected thread (for "See related" vs "Link to")
  const { data: threadLinksData } = useThreadLinks(selectedThreadId, 0.6);
  const hasRelatedLinks = (threadLinksData?.count || 0) > 0;

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Focus input on mount
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  // Rolling placeholder animation
  useEffect(() => {
    if (searchQuery) return;

    const interval = setInterval(() => {
      setIsAnimating(true);
      setTimeout(() => {
        setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_SUGGESTIONS.length);
        setIsAnimating(false);
      }, 200);
    }, 3000);

    return () => clearInterval(interval);
  }, [searchQuery]);

  // Auto-trigger backfill if inbox is empty (and not already running)
  const backfillTriggeredRef = useRef(false);
  useEffect(() => {
    if (
      !isLoading &&
      !isSearching &&
      threads.length === 0 &&
      !isBackfilling &&
      !backfillTriggeredRef.current &&
      outlookStatus?.isConnected
    ) {
      backfillTriggeredRef.current = true;
      console.log('[EmailSearchView] Auto-triggering backfill for empty inbox');
      triggerBackfill();
    }
  }, [isLoading, isSearching, threads.length, isBackfilling, outlookStatus?.isConnected, triggerBackfill]);

  // Auto-select first message when thread loads
  useEffect(() => {
    if (selectedThread?.messages?.length && !selectedMessageId) {
      setSelectedMessageId(selectedThread.messages[0].provider_message_id);
    }
  }, [selectedThread, selectedMessageId]);

  const handleClear = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    inputRef.current?.focus();
  }, []);

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleThreadClick = useCallback((threadId: string) => {
    setSelectedThreadId(threadId);
    setSelectedMessageId(null); // Will be auto-set when thread loads
  }, []);

  const handleMessageClick = useCallback((providerMessageId: string) => {
    setSelectedMessageId(providerMessageId);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (searchQuery) {
          handleClear();
        } else {
          router.back();
        }
      }
    },
    [searchQuery, handleClear, router]
  );

  // Get attachments for selected message
  const selectedAttachments = selectedContent?.attachments || [];

  return (
    <div className={cn('h-screen flex flex-col bg-[#1c1c1e] font-body', className)}>
      {/* Outlook Reconnect Banner */}
      {needsReconnect && (
        <div className="bg-[#3a2a1a] border-b border-[#ff9f0a]/30 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-[#ff9f0a]" />
              <div>
                <p className="text-[14px] font-medium text-white">
                  {outlookStatus?.isExpired ? 'Outlook session expired' : 'Outlook not connected'}
                </p>
                <p className="text-[12px] text-[#98989f]">
                  Reconnect to sync and search your emails
                </p>
              </div>
            </div>
            <button
              onClick={handleReconnect}
              disabled={reconnecting}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-colors',
                reconnecting
                  ? 'bg-[#48484a] text-[#98989f] cursor-not-allowed'
                  : 'bg-[#ff9f0a] text-black hover:bg-[#ffb340]'
              )}
            >
              {reconnecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Reconnect Outlook
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Header - Search Bar */}
      <div className="sticky top-0 z-10 bg-[#1c1c1e]/95 backdrop-blur-md border-b border-[#3d3d3f]/30 px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Back button */}
          <button
            onClick={handleBack}
            className="p-2 -ml-2 rounded-lg text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          {/* Search with scope indicator */}
          <div className="flex-1 flex items-center gap-3">
            <div className="px-2 py-0.5 bg-[#0a84ff]/20 border border-[#0a84ff]/30 rounded text-[11px] text-[#0a84ff] font-medium whitespace-nowrap">
              Email Scope
            </div>

            <div className="flex-1 spotlight-panel ring-1 ring-[#0a84ff]/30">
              <div className="flex items-center gap-3 px-4 h-[44px]">
                <Search className="flex-shrink-0 w-5 h-5 text-[#0a84ff]" strokeWidth={1.8} />

                <div className="flex-1 h-full relative">
                  <input
                    ref={inputRef}
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className={cn(
                      'w-full h-full',
                      'bg-transparent border-none outline-none',
                      'text-[15px] text-white',
                      'font-normal tracking-[-0.01em]',
                      'caret-white',
                      'relative z-10'
                    )}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                  />
                  {!searchQuery && (
                    <div className="absolute inset-0 flex items-center pointer-events-none overflow-hidden">
                      <span
                        className={cn(
                          'text-[15px] text-[#98989f] font-normal tracking-[-0.01em]',
                          'transition-all duration-[400ms] ease-out',
                          isAnimating ? 'opacity-0 -translate-y-3' : 'opacity-100 translate-y-0'
                        )}
                      >
                        {PLACEHOLDER_SUGGESTIONS[placeholderIndex]}
                      </span>
                    </div>
                  )}
                </div>

                {searchQuery && (
                  <button
                    onClick={handleClear}
                    className="flex items-center justify-center w-4 h-4 rounded-full bg-[#636366] hover:bg-[#8e8e93] transition-colors"
                    aria-label="Clear"
                  >
                    <X className="w-2.5 h-2.5 text-[#1c1c1e]" strokeWidth={3} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Sync status */}
          <SyncStatusBadge status={watcherStatus} onRefresh={refetch} />
        </div>

        {/* Filters row */}
        <div className="flex items-center gap-3 mt-3 pl-10">
          {/* Direction chips */}
          <div className="flex items-center gap-2">
            <DirectionChip
              icon={<Mail className="w-3.5 h-3.5" />}
              label="All"
              active={directionFilter === 'all'}
              onClick={() => {
                setDirectionFilter('all');
                setPage(1);
              }}
            />
            <DirectionChip
              icon={<Inbox className="w-3.5 h-3.5" />}
              label="Inbox"
              active={directionFilter === 'inbound'}
              onClick={() => {
                setDirectionFilter('inbound');
                setPage(1);
              }}
            />
            <DirectionChip
              icon={<Send className="w-3.5 h-3.5" />}
              label="Sent"
              active={directionFilter === 'outbound'}
              onClick={() => {
                setDirectionFilter('outbound');
                setPage(1);
              }}
            />
          </div>

          <div className="w-px h-5 bg-[#3d3d3f]" />

          {/* Operator chips */}
          <div className="flex items-center gap-2">
            <OperatorChip
              label="from:"
              onClick={() => setSearchQuery((q) => q + (q && !q.endsWith(' ') ? ' ' : '') + 'from:')}
            />
            <OperatorChip
              label="to:"
              onClick={() => setSearchQuery((q) => q + (q && !q.endsWith(' ') ? ' ' : '') + 'to:')}
            />
            <OperatorChip
              label="subject:"
              onClick={() => setSearchQuery((q) => q + (q && !q.endsWith(' ') ? ' ' : '') + 'subject:')}
            />
            <OperatorChip
              label="has:attachment"
              active={searchQuery.includes('has:attachment')}
              onClick={() => {
                if (searchQuery.includes('has:attachment')) {
                  setSearchQuery((q) => q.replace(/has:attachment\s*/g, '').trim());
                } else {
                  setSearchQuery((q) => q + (q && !q.endsWith(' ') ? ' ' : '') + 'has:attachment');
                }
              }}
            />
          </div>

          {/* Thread count */}
          {total > 0 && (
            <span className="ml-auto text-[12px] text-[#636366]">
              {total} thread{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Three-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Thread List */}
        <div className="w-80 flex-shrink-0 border-r border-[#3d3d3f]/30 overflow-y-auto">
          {/* Backfill progress indicator */}
          {isBackfilling && (
            <div className="p-3 border-b border-[#3d3d3f]/30 bg-[#2c2c2e]">
              <div className="flex items-center gap-2 text-[12px] text-[#98989f]">
                <Loader2 className="w-4 h-4 animate-spin text-[#0a84ff]" />
                <span>Importing emails...</span>
                {(backfillStatus?.progress ?? 0) > 0 && (
                  <span className="ml-auto">{backfillStatus?.progress ?? 0}%</span>
                )}
              </div>
              {(backfillStatus?.totalEmails ?? 0) > 0 && (
                <div className="mt-1 h-1 bg-[#3d3d3f] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#0a84ff] transition-all duration-300"
                    style={{ width: `${backfillStatus?.progress ?? 0}%` }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Import All CTA (always visible unless backfilling) */}
          {!isBackfilling && outlookStatus?.isConnected && (
            <div className="p-3 border-b border-[#3d3d3f]/30">
              <button
                onClick={() => triggerBackfill()}
                disabled={isTriggering}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[#2c2c2e] hover:bg-[#3a3a3c] text-[12px] text-[#98989f] transition-colors"
              >
                <Download className="w-4 h-4" />
                {isTriggering ? 'Starting import...' : 'Import all emails'}
              </button>
            </div>
          )}

          {displayLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-[#98989f]" />
            </div>
          )}

          {displayError && (
            <div className="py-8 text-center px-4">
              <p className="text-[13px] text-[#ff453a]">
                {displayError instanceof Error ? displayError.message : 'Failed to load emails'}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-2 text-[13px] text-[#0a84ff] hover:text-[#409cff]"
              >
                Try again
              </button>
            </div>
          )}

          {!displayLoading && !displayError && displayThreads.length === 0 && (
            <div className="py-12 text-center px-4">
              <Mail className="h-10 w-10 text-[#48484a] mx-auto mb-3" />
              <p className="text-[13px] text-[#98989f]">
                {debouncedQuery ? 'No emails match your search' : 'No email threads found'}
              </p>
            </div>
          )}

          {!displayLoading && !displayError && displayThreads.length > 0 && (
            <>
              {displayThreads.map((thread) => (
                <ThreadListItem
                  key={thread.id}
                  thread={thread as EmailThread}
                  isSelected={selectedThreadId === thread.id}
                  onClick={() => handleThreadClick(thread.id)}
                />
              ))}

              {/* Pagination (only for inbox, not search) */}
              {!isSearching && (page > 1 || hasMore) && (
                <div className="flex items-center justify-center gap-4 py-4 border-t border-[#3d3d3f]/30">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className={cn(
                      'px-3 py-1.5 rounded text-[12px] transition-colors',
                      page === 1
                        ? 'text-[#48484a] cursor-not-allowed'
                        : 'text-[#0a84ff] hover:bg-white/5'
                    )}
                  >
                    Prev
                  </button>
                  <span className="text-[11px] text-[#636366]">Page {page}</span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!hasMore}
                    className={cn(
                      'px-3 py-1.5 rounded text-[12px] transition-colors',
                      !hasMore
                        ? 'text-[#48484a] cursor-not-allowed'
                        : 'text-[#0a84ff] hover:bg-white/5'
                    )}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Center Panel - Message Content */}
        <div className="flex-1 overflow-y-auto">
          {!selectedThreadId && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Mail className="h-12 w-12 text-[#48484a] mx-auto mb-3" />
                <p className="text-[14px] text-[#98989f]">Select an email to view</p>
              </div>
            </div>
          )}

          {selectedThreadId && threadLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-[#98989f]" />
            </div>
          )}

          {selectedThread && (
            <MessagePanel
              thread={selectedThread}
              selectedMessageId={selectedMessageId}
              onMessageSelect={handleMessageClick}
              content={selectedContent}
              contentLoading={contentLoading}
              relatedLinksCount={threadLinksData?.count || 0}
              hasRelatedLinks={hasRelatedLinks}
            />
          )}
        </div>

        {/* Right Panel - Attachments */}
        <div className="w-64 flex-shrink-0 border-l border-[#3d3d3f]/30 overflow-y-auto">
          <AttachmentsPanel
            attachments={selectedAttachments}
            providerMessageId={selectedMessageId}
          />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// THREAD LIST ITEM
// ============================================================================

interface ThreadListItemProps {
  thread: EmailThread;
  isSelected: boolean;
  onClick: () => void;
}

function ThreadListItem({ thread, isSelected, onClick }: ThreadListItemProps) {
  // Generate avatar initials from subject
  const initials = useMemo(() => {
    const subject = thread.latest_subject || 'E';
    return subject.charAt(0).toUpperCase();
  }, [thread.latest_subject]);

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-start gap-3 p-3 text-left transition-colors',
        isSelected ? 'bg-[#0a84ff]/20' : 'hover:bg-[#2c2c2e]'
      )}
    >
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-[#3a3a3c] flex items-center justify-center flex-shrink-0">
        <span className="text-[14px] font-medium text-[#98989f]">{initials}</span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <h3
          className={cn(
            'text-[14px] font-medium truncate',
            isSelected ? 'text-[#0a84ff]' : 'text-white'
          )}
        >
          {thread.latest_subject || '(No subject)'}
        </h3>

        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[11px] text-[#636366]">
            {thread.message_count} msg{thread.message_count !== 1 ? 's' : ''}
          </span>
          {thread.has_attachments && <Paperclip className="w-3 h-3 text-[#636366]" />}
        </div>

        {thread.last_activity_at && (
          <span className="text-[11px] text-[#48484a] block mt-0.5">
            {formatRelativeTime(thread.last_activity_at)}
          </span>
        )}
      </div>

      <ChevronRight className="w-4 h-4 text-[#48484a] flex-shrink-0 mt-1" />
    </button>
  );
}

// ============================================================================
// MESSAGE PANEL (Center)
// ============================================================================

interface MessagePanelProps {
  thread: {
    latest_subject: string | null;
    message_count: number;
    has_attachments: boolean;
    messages: EmailMessage[];
  };
  selectedMessageId: string | null;
  onMessageSelect: (providerMessageId: string) => void;
  content: MessageContentType | null | undefined;
  contentLoading: boolean;
  relatedLinksCount: number;
  hasRelatedLinks: boolean;
}

function MessagePanel({
  thread,
  selectedMessageId,
  onMessageSelect,
  content,
  contentLoading,
  relatedLinksCount,
  hasRelatedLinks,
}: MessagePanelProps) {
  const [showLinkModal, setShowLinkModal] = useState(false);

  return (
    <div className="h-full flex flex-col">
      {/* Thread header */}
      <div className="p-4 border-b border-[#3d3d3f]/30">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-[16px] font-semibold text-white">
              {thread.latest_subject || '(No subject)'}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-[12px] text-[#636366]">
              <span>
                {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
              </span>
              {thread.has_attachments && (
                <span className="flex items-center gap-1">
                  <Paperclip className="w-3 h-3" />
                  Has attachments
                </span>
              )}
            </div>
          </div>

          {/* "See related" vs "Link to" conditional button */}
          <div className="flex-shrink-0">
            {hasRelatedLinks ? (
              <button
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#30d158]/20 text-[#30d158] text-[12px] font-medium hover:bg-[#30d158]/30 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
                See related ({relatedLinksCount})
              </button>
            ) : (
              <button
                onClick={() => setShowLinkModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0a84ff]/20 text-[#0a84ff] text-[12px] font-medium hover:bg-[#0a84ff]/30 transition-colors"
              >
                <Mail className="w-4 h-4" />
                Link to...
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Message tabs */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#3d3d3f]/30 overflow-x-auto">
        {thread.messages.map((msg, index) => (
          <button
            key={msg.id}
            onClick={() => onMessageSelect(msg.provider_message_id)}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded text-[12px] whitespace-nowrap transition-colors',
              selectedMessageId === msg.provider_message_id
                ? 'bg-[#0a84ff] text-white'
                : 'bg-[#2c2c2e] text-[#98989f] hover:bg-[#3a3a3c]'
            )}
          >
            <div
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                msg.direction === 'inbound' ? 'bg-blue-400' : 'bg-green-400'
              )}
            />
            <span className="truncate max-w-[100px]">{msg.from_display_name || `Message ${index + 1}`}</span>
          </button>
        ))}
      </div>

      {/* Message content */}
      <div className="flex-1 overflow-y-auto p-4">
        {contentLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-[#98989f]" />
            <span className="ml-2 text-[13px] text-[#98989f]">Loading email...</span>
          </div>
        )}

        {!contentLoading && content && (
          <div className="space-y-4">
            {/* From/To details */}
            <div className="space-y-1 text-[12px] text-[#98989f] pb-4 border-b border-[#3d3d3f]/30">
              {content.from_address?.emailAddress && (
                <div>
                  <span className="text-[#636366]">From: </span>
                  <span className="text-white">
                    {content.from_address.emailAddress.name || content.from_address.emailAddress.address}
                  </span>
                  {content.from_address.emailAddress.name && (
                    <span className="text-[#636366]">
                      {' '}
                      &lt;{content.from_address.emailAddress.address}&gt;
                    </span>
                  )}
                </div>
              )}
              {content.to_recipients?.length > 0 && (
                <div>
                  <span className="text-[#636366]">To: </span>
                  <span className="text-white">
                    {content.to_recipients
                      .map((r) => r.emailAddress?.name || r.emailAddress?.address)
                      .join(', ')}
                  </span>
                </div>
              )}
              {content.cc_recipients?.length > 0 && (
                <div>
                  <span className="text-[#636366]">Cc: </span>
                  <span className="text-white">
                    {content.cc_recipients
                      .map((r) => r.emailAddress?.name || r.emailAddress?.address)
                      .join(', ')}
                  </span>
                </div>
              )}
              {content.sent_at && (
                <div>
                  <span className="text-[#636366]">Date: </span>
                  <span className="text-white">
                    {new Date(content.sent_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {/* Email body - Full HTML render */}
            <div className="email-body">
              {content.body?.contentType === 'html' ? (
                <div
                  className="prose prose-invert prose-sm max-w-none text-[14px] leading-relaxed
                    [&_a]:text-[#0a84ff] [&_a]:no-underline [&_a:hover]:underline
                    [&_img]:max-w-full [&_img]:h-auto
                    [&_table]:border-collapse [&_td]:border [&_td]:border-[#3d3d3f] [&_td]:p-2
                    [&_th]:border [&_th]:border-[#3d3d3f] [&_th]:p-2 [&_th]:bg-[#2c2c2e]"
                  dangerouslySetInnerHTML={{ __html: content.body.content }}
                />
              ) : (
                <pre className="text-[14px] text-white whitespace-pre-wrap font-sans leading-relaxed">
                  {content.body?.content || content.body_preview || '(No content)'}
                </pre>
              )}
            </div>
          </div>
        )}

        {!contentLoading && !content && selectedMessageId && (
          <div className="text-center py-8">
            <p className="text-[13px] text-[#ff453a]">Failed to load message content</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// ATTACHMENTS PANEL (Right)
// ============================================================================

interface AttachmentsPanelProps {
  attachments: Array<{
    id: string;
    name: string;
    contentType?: string;
    size?: number;
  }>;
  providerMessageId: string | null;
}

function AttachmentsPanel({ attachments, providerMessageId }: AttachmentsPanelProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-[#3d3d3f]/30">
        <h3 className="text-[13px] font-medium text-[#98989f]">
          Attachments {attachments.length > 0 && `(${attachments.length})`}
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {attachments.length === 0 ? (
          <div className="text-center py-8">
            <Paperclip className="h-8 w-8 text-[#48484a] mx-auto mb-2" />
            <p className="text-[12px] text-[#636366]">No attachments</p>
          </div>
        ) : (
          <div className="space-y-2">
            {attachments.map((att) => (
              <AttachmentItem
                key={att.id}
                attachment={att}
                providerMessageId={providerMessageId!}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// ATTACHMENT ITEM
// ============================================================================

interface AttachmentItemProps {
  attachment: {
    id: string;
    name: string;
    contentType?: string;
    size?: number;
  };
  providerMessageId: string;
}

function AttachmentItem({ attachment, providerMessageId }: AttachmentItemProps) {
  const [status, setStatus] = React.useState<'idle' | 'downloading' | 'error'>('idle');
  const [error, setError] = React.useState<string | null>(null);

  const handleDownload = async () => {
    setStatus('downloading');
    setError(null);

    const result = await downloadAndSaveAttachment(
      providerMessageId,
      attachment.id,
      attachment.name
    );

    if (result.success) {
      setStatus('idle');
    } else {
      setStatus('error');
      setError(result.error.message);
    }
  };

  return (
    <div className="flex flex-col">
      <button
        onClick={handleDownload}
        disabled={status === 'downloading'}
        className={cn(
          'flex items-center gap-2 p-3 rounded-lg transition-colors text-left',
          status === 'error'
            ? 'bg-[#3a1a1a] border border-[#ff453a]/30'
            : 'bg-[#2c2c2e] hover:bg-[#3a3a3c]'
        )}
      >
        {status === 'downloading' ? (
          <Loader2 className="w-4 h-4 text-[#98989f] animate-spin flex-shrink-0" />
        ) : status === 'error' ? (
          <AlertCircle className="w-4 h-4 text-[#ff453a] flex-shrink-0" />
        ) : (
          <Download className="w-4 h-4 text-[#0a84ff] flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <span
            className={cn(
              'text-[13px] block truncate',
              status === 'error' ? 'text-[#ff453a]' : 'text-white'
            )}
          >
            {attachment.name}
          </span>
          {attachment.size && status !== 'error' && (
            <span className="text-[11px] text-[#636366]">{formatFileSize(attachment.size)}</span>
          )}
        </div>
      </button>
      {error && <p className="text-[11px] text-[#ff453a] mt-1 px-1">{error}</p>}
    </div>
  );
}

// ============================================================================
// SYNC STATUS BADGE
// ============================================================================

interface SyncStatusBadgeProps {
  status: {
    sync_status?: 'active' | 'degraded' | 'error';
    last_sync_at?: string | null;
    is_connected?: boolean;
  } | null | undefined;
  onRefresh: () => void;
}

function SyncStatusBadge({ status, onRefresh }: SyncStatusBadgeProps) {
  const lastSyncText = useMemo(() => {
    if (!status?.last_sync_at) return null;
    return formatRelativeTime(status.last_sync_at);
  }, [status?.last_sync_at]);

  if (!status?.is_connected) {
    return (
      <button
        onClick={onRefresh}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#3a1a1a] border border-[#ff453a]/30 text-[12px] text-[#ff453a]"
      >
        <AlertCircle className="w-3.5 h-3.5" />
        Not connected
      </button>
    );
  }

  return (
    <button
      onClick={onRefresh}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#2c2c2e] text-[12px] text-[#98989f] hover:bg-[#3a3a3c] transition-colors"
    >
      <RefreshCw className="w-3.5 h-3.5" />
      {lastSyncText ? `Synced ${lastSyncText}` : 'Sync'}
    </button>
  );
}

// ============================================================================
// UTILITY COMPONENTS
// ============================================================================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DirectionChipProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}

function DirectionChip({ icon, label, active, onClick }: DirectionChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors',
        active ? 'bg-[#0a84ff] text-white' : 'bg-[#3a3a3c] text-[#98989f] hover:bg-[#48484a]'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

interface OperatorChipProps {
  label: string;
  active?: boolean;
  onClick: () => void;
}

function OperatorChip({ label, active, onClick }: OperatorChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-2 py-1 rounded text-[11px] font-mono transition-colors',
        active
          ? 'bg-[#30d158]/20 text-[#30d158] border border-[#30d158]/30'
          : 'bg-[#2c2c2e] text-[#98989f] hover:bg-[#3a3a3c] border border-[#3d3d3f]/30'
      )}
    >
      {label}
    </button>
  );
}
