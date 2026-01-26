'use client';

/**
 * EmailSearchView Component
 *
 * Dark-themed email search interface with Spotlight-inspired design.
 * Features:
 * - Search bar at top with rolling placeholder
 * - Email thread list below
 * - Click-on-demand email content rendering
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Mail, Paperclip, ChevronLeft, Loader2, ArrowLeft, Inbox, Send } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useInboxThreads, useThread, useMessageContent, type EmailThread } from '@/hooks/useEmailData';
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

// ============================================================================
// COMPONENT
// ============================================================================

type DirectionFilter = 'all' | 'inbound' | 'outbound';

export default function EmailSearchView({ className }: EmailSearchViewProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
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

  const threads = data?.threads || [];
  const total = data?.total || 0;
  const hasMore = data?.has_more || false;

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1); // Reset to first page on new search
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

  const handleClear = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    inputRef.current?.focus();
  }, []);

  const handleBack = useCallback(() => {
    if (selectedThread) {
      setSelectedThread(null);
    } else {
      router.back();
    }
  }, [selectedThread, router]);

  const handleThreadClick = useCallback((thread: EmailThread) => {
    setSelectedThread(thread);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (selectedThread) {
        setSelectedThread(null);
      } else if (searchQuery) {
        handleClear();
      } else {
        router.back();
      }
    }
  }, [selectedThread, searchQuery, handleClear, router]);

  return (
    <div className={cn('min-h-screen bg-[#1c1c1e] font-body', className)}>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#1c1c1e]/95 backdrop-blur-md border-b border-[#3d3d3f]/30">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Back button and title */}
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={handleBack}
              className="p-2 -ml-2 rounded-lg text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-semibold text-white">
              {selectedThread ? 'Email Thread' : 'Email Search'}
            </h1>
            {!selectedThread && total > 0 && (
              <span className="text-[13px] text-[#98989f]">
                {total} thread{total !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Search bar - only show when not viewing thread */}
          {!selectedThread && (
            <>
            {/* Email scope indicator */}
            <div className="flex items-center gap-2 mb-2">
              <div className="px-2 py-0.5 bg-[#0a84ff]/20 border border-[#0a84ff]/30 rounded text-[11px] text-[#0a84ff] font-medium">
                Email Scope
              </div>
            </div>
            <div className="spotlight-panel ring-1 ring-[#0a84ff]/30">
              <div className="flex items-center gap-3 px-4 h-[50px]">
                <Search
                  className="flex-shrink-0 w-5 h-5 text-[#0a84ff]"
                  strokeWidth={1.8}
                />

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
                      'text-[17px] text-white',
                      'font-normal tracking-[-0.01em]',
                      'caret-white',
                      'relative z-10'
                    )}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                  />
                  {/* Animated rolling placeholder */}
                  {!searchQuery && (
                    <div className="absolute inset-0 flex items-center pointer-events-none overflow-hidden">
                      <span
                        className={cn(
                          'text-[17px] text-[#98989f] font-normal tracking-[-0.01em]',
                          'transition-all duration-[400ms] ease-out',
                          isAnimating
                            ? 'opacity-0 -translate-y-3'
                            : 'opacity-100 translate-y-0'
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

            {/* Direction Filter Chips */}
            <div className="flex items-center gap-2 mt-3">
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
            </>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="max-w-3xl mx-auto px-4 py-4">
        {/* Loading State */}
        {isLoading && !selectedThread && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-[#98989f]" />
          </div>
        )}

        {/* Error State */}
        {error && !selectedThread && (
          <div className="py-12 text-center">
            <p className="text-[15px] text-[#ff453a]">
              {error instanceof Error ? error.message : 'Failed to load emails'}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-2 text-[14px] text-[#0a84ff] hover:text-[#409cff]"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && !selectedThread && threads.length === 0 && (
          <div className="py-12 text-center">
            <Mail className="h-12 w-12 text-[#48484a] mx-auto mb-4" />
            <p className="text-[15px] text-[#98989f]">
              {debouncedQuery ? 'No emails match your search' : 'No email threads found'}
            </p>
          </div>
        )}

        {/* Thread List */}
        {!isLoading && !error && !selectedThread && threads.length > 0 && (
          <div className="space-y-1">
            {threads.map((thread) => (
              <ThreadRow
                key={thread.id}
                thread={thread}
                onClick={() => handleThreadClick(thread)}
              />
            ))}

            {/* Pagination */}
            {(page > 1 || hasMore) && (
              <div className="flex items-center justify-center gap-4 pt-6">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className={cn(
                    'px-4 py-2 rounded-lg text-[14px] transition-colors',
                    page === 1
                      ? 'text-[#48484a] cursor-not-allowed'
                      : 'text-[#0a84ff] hover:bg-white/5'
                  )}
                >
                  Previous
                </button>
                <span className="text-[13px] text-[#98989f]">Page {page}</span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasMore}
                  className={cn(
                    'px-4 py-2 rounded-lg text-[14px] transition-colors',
                    !hasMore
                      ? 'text-[#48484a] cursor-not-allowed'
                      : 'text-[#0a84ff] hover:bg-white/5'
                  )}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}

        {/* Thread Detail View */}
        {selectedThread && (
          <ThreadDetailView
            threadId={selectedThread.id}
            subject={selectedThread.latest_subject}
            onBack={() => setSelectedThread(null)}
          />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// THREAD ROW SUB-COMPONENT
// ============================================================================

interface ThreadRowProps {
  thread: EmailThread;
  onClick: () => void;
}

function ThreadRow({ thread, onClick }: ThreadRowProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-start gap-3 p-4 rounded-xl',
        'bg-[#2c2c2e] hover:bg-[#3a3a3c] transition-colors',
        'text-left'
      )}
    >
      <Mail className="w-5 h-5 text-[#98989f] mt-0.5 flex-shrink-0" />

      <div className="flex-1 min-w-0">
        <h3 className="text-[15px] font-medium text-white truncate">
          {thread.latest_subject || '(No subject)'}
        </h3>

        <div className="flex items-center gap-3 mt-1 text-[12px] text-[#98989f]">
          <span>{thread.message_count} message{thread.message_count !== 1 ? 's' : ''}</span>
          {thread.has_attachments && (
            <span className="flex items-center gap-1">
              <Paperclip className="w-3 h-3" />
              Attachments
            </span>
          )}
          {thread.last_activity_at && (
            <span>{formatRelativeTime(thread.last_activity_at)}</span>
          )}
        </div>
      </div>

      <ChevronLeft className="w-5 h-5 text-[#48484a] rotate-180 flex-shrink-0" />
    </button>
  );
}

// ============================================================================
// THREAD DETAIL VIEW SUB-COMPONENT
// ============================================================================

interface ThreadDetailViewProps {
  threadId: string;
  subject: string | null;
  onBack: () => void;
}

function ThreadDetailView({ threadId, subject, onBack }: ThreadDetailViewProps) {
  const { data: thread, isLoading, error } = useThread(threadId);
  const [expandedMessageId, setExpandedMessageId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-[#98989f]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-[15px] text-[#ff453a]">
          {error instanceof Error ? error.message : 'Failed to load thread'}
        </p>
      </div>
    );
  }

  if (!thread) return null;

  return (
    <div className="space-y-4">
      {/* Thread Header */}
      <div className="p-4 rounded-xl bg-[#2c2c2e]">
        <h2 className="text-[17px] font-semibold text-white mb-2">
          {subject || '(No subject)'}
        </h2>
        <div className="flex items-center gap-4 text-[13px] text-[#98989f]">
          <span>{thread.message_count} message{thread.message_count !== 1 ? 's' : ''}</span>
          {thread.has_attachments && (
            <span className="flex items-center gap-1">
              <Paperclip className="w-3.5 h-3.5" />
              Has attachments
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="space-y-2">
        {(thread.messages || []).map((message) => (
          <MessageRow
            key={message.id}
            message={message}
            isExpanded={expandedMessageId === message.provider_message_id}
            onToggle={() =>
              setExpandedMessageId(
                expandedMessageId === message.provider_message_id
                  ? null
                  : message.provider_message_id
              )
            }
          />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// MESSAGE ROW SUB-COMPONENT (Click-on-demand)
// ============================================================================

interface MessageRowProps {
  message: {
    id: string;
    provider_message_id: string;
    direction: 'inbound' | 'outbound';
    from_display_name: string | null;
    subject: string | null;
    sent_at: string | null;
    has_attachments: boolean;
  };
  isExpanded: boolean;
  onToggle: () => void;
}

function MessageRow({ message, isExpanded, onToggle }: MessageRowProps) {
  return (
    <div className="rounded-xl bg-[#2c2c2e] overflow-hidden">
      {/* Message Header - Always visible */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center gap-3 p-4 text-left',
          'hover:bg-[#3a3a3c] transition-colors'
        )}
      >
        <div
          className={cn(
            'w-2 h-2 rounded-full flex-shrink-0',
            message.direction === 'inbound' ? 'bg-[#0a84ff]' : 'bg-[#30d158]'
          )}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-medium text-white truncate">
              {message.from_display_name || 'Unknown'}
            </span>
            <span className="text-[12px] text-[#48484a]">
              {message.direction === 'inbound' ? 'received' : 'sent'}
            </span>
          </div>
          {message.sent_at && (
            <span className="text-[12px] text-[#98989f]">
              {formatRelativeTime(message.sent_at)}
            </span>
          )}
        </div>

        {message.has_attachments && (
          <Paperclip className="w-4 h-4 text-[#98989f]" />
        )}

        <ChevronLeft
          className={cn(
            'w-4 h-4 text-[#48484a] transition-transform',
            isExpanded ? 'rotate-90' : '-rotate-90'
          )}
        />
      </button>

      {/* Message Content - Click to load */}
      {isExpanded && (
        <MessageContent providerMessageId={message.provider_message_id} />
      )}
    </div>
  );
}

// ============================================================================
// MESSAGE CONTENT SUB-COMPONENT (Fetch on demand)
// ============================================================================

interface MessageContentProps {
  providerMessageId: string;
}

function MessageContent({ providerMessageId }: MessageContentProps) {
  const { data: content, isLoading, error } = useMessageContent(providerMessageId);

  if (isLoading) {
    return (
      <div className="px-4 pb-4">
        <div className="flex items-center justify-center py-8 border-t border-[#3d3d3f]">
          <Loader2 className="h-5 w-5 animate-spin text-[#98989f]" />
          <span className="ml-2 text-[13px] text-[#98989f]">Loading email content...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 pb-4">
        <div className="py-4 border-t border-[#3d3d3f] text-center">
          <p className="text-[13px] text-[#ff453a]">
            {error instanceof Error ? error.message : 'Failed to load content'}
          </p>
        </div>
      </div>
    );
  }

  if (!content) return null;

  return (
    <div className="px-4 pb-4 border-t border-[#3d3d3f]">
      {/* From/To Details */}
      <div className="py-3 space-y-1 text-[12px] text-[#98989f] border-b border-[#3d3d3f]">
        {content.from_address?.emailAddress && (
          <div>
            <span className="text-[#636366]">From: </span>
            <span className="text-white">
              {content.from_address.emailAddress.name || content.from_address.emailAddress.address}
            </span>
            {content.from_address.emailAddress.name && (
              <span className="text-[#636366]"> &lt;{content.from_address.emailAddress.address}&gt;</span>
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
      </div>

      {/* Email Body */}
      <div className="py-4">
        {content.body?.contentType === 'html' ? (
          <div
            className="prose prose-invert prose-sm max-w-none text-[14px] leading-relaxed"
            dangerouslySetInnerHTML={{ __html: content.body.content }}
          />
        ) : (
          <pre className="text-[14px] text-white whitespace-pre-wrap font-sans leading-relaxed">
            {content.body?.content || content.body_preview || '(No content)'}
          </pre>
        )}
      </div>

      {/* Attachments */}
      {content.attachments && content.attachments.length > 0 && (
        <div className="pt-3 border-t border-[#3d3d3f]">
          <h4 className="text-[12px] font-medium text-[#98989f] mb-2">
            Attachments ({content.attachments.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {content.attachments.map((att: any, i: number) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#3a3a3c]"
              >
                <Paperclip className="w-3.5 h-3.5 text-[#98989f]" />
                <span className="text-[13px] text-white truncate max-w-[200px]">
                  {att.name}
                </span>
                {att.size && (
                  <span className="text-[11px] text-[#636366]">
                    {formatFileSize(att.size)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ============================================================================
// DIRECTION FILTER CHIP
// ============================================================================

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
        'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium transition-colors',
        active
          ? 'bg-[#0a84ff] text-white'
          : 'bg-[#3a3a3c] text-[#98989f] hover:bg-[#48484a]'
      )}
    >
      {icon}
      {label}
    </button>
  );
}
