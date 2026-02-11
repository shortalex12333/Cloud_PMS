'use client';

/**
 * EmailSurface - Correspondence Interface
 *
 * AUTHORITATIVE SPEC IMPLEMENTATION:
 * - Email is evidence moving through the system, not a workspace
 * - Email list shows entity-first (linked work order/equipment/fault)
 * - No auto-open, no Inbox/Sent tabs, no unread counts
 * - Mutations FORBIDDEN - view only
 * - Subordinate visual styling
 *
 * Version: 2026-02-10-v1 (Correspondence Overhaul)
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  X,
  Paperclip,
  ChevronRight,
  Loader2,
  AlertCircle,
  FileText,
  Wrench,
  Package,
  AlertTriangle,
  Filter,
  MoreHorizontal,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import {
  useInboxThreads,
  useEmailSearch,
  useThread,
  useMessageContent,
  useThreadLinks,
  fetchAttachmentBlob,
  useWatcherStatus,
  useOutlookConnection,
  usePrefetchThread,
  type EmailThread,
  type EmailMessage,
  type MessageContent as MessageContentType,
  type ThreadLink,
} from '@/hooks/useEmailData';
import DocumentViewerOverlay from '@/components/viewer/DocumentViewerOverlay';
import { cn } from '@/lib/utils';
import DOMPurify from 'isomorphic-dompurify';

// ============================================================================
// HTML SANITIZATION CONFIG
// ============================================================================

const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'div', 'span', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'b', 'i', 'u', 's', 'strong', 'em', 'mark', 'small', 'sub', 'sup',
    'a',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
    'blockquote', 'pre', 'code',
    'img',
  ],
  ALLOWED_ATTR: [
    'class', 'id', 'style',
    'href', 'target', 'rel',
    'src', 'alt', 'width', 'height',
    'colspan', 'rowspan', 'scope',
  ],
  ADD_ATTR: ['target', 'rel'],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['script', 'style', 'iframe', 'frame', 'object', 'embed', 'form', 'input', 'button'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
};

function sanitizeHtml(html: string): string {
  if (!html) return '';
  let clean = DOMPurify.sanitize(html, SANITIZE_CONFIG);
  clean = clean.replace(/<a\s+([^>]*?)>/gi, '<a $1 target="_blank" rel="noopener noreferrer">');
  clean = clean.replace(/<img\s+([^>]*?)src=["'](?!(cid:|data:image))/gi, '<img $1data-blocked-src="');
  return clean;
}

// ============================================================================
// TYPES
// ============================================================================

interface EmailSurfaceProps {
  className?: string;
  initialThreadId?: string;
  onClose?: () => void;
}

type SystemState = 'attached' | 'referenced' | 'archived' | 'unlinked';

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  work_order: <Wrench className="w-3 h-3" />,
  equipment: <Package className="w-3 h-3" />,
  fault: <AlertTriangle className="w-3 h-3" />,
  part: <Package className="w-3 h-3" />,
  handover: <FileText className="w-3 h-3" />,
};

// ============================================================================
// UTILITY: Format timestamp
// ============================================================================

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  }

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function EmailSurface({
  className,
  initialThreadId,
  onClose,
}: EmailSurfaceProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(initialThreadId || null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isOverlayMode = !!onClose;

  const { data, isLoading, error, refetch } = useInboxThreads(page, true, debouncedQuery);
  const { data: watcherStatus } = useWatcherStatus();
  const { data: outlookStatus, initiateReconnect, isLoading: outlookLoading } = useOutlookConnection();
  const [reconnecting, setReconnecting] = useState(false);

  const threads = data?.threads || [];
  const hasMore = data?.has_more || false;

  const handleReconnect = useCallback(async () => {
    setReconnecting(true);
    const authUrl = await initiateReconnect();
    if (authUrl) {
      window.location.href = authUrl;
    } else {
      setReconnecting(false);
    }
  }, [initiateReconnect]);

  const needsReconnect = !outlookLoading && outlookStatus && (!outlookStatus.isConnected || outlookStatus.isExpired);
  const isDegraded = watcherStatus?.sync_status === 'degraded' || watcherStatus?.sync_status === 'error';

  const { data: searchData, isLoading: searchLoading, error: searchError } = useEmailSearch(debouncedQuery, { limit: 20 });

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
        from_display_name: r.from_display_name,
      }))
    : threads;
  const displayLoading = isSearching ? searchLoading : isLoading;
  const displayError = isSearching ? searchError : error;

  const { data: selectedThread, isLoading: threadLoading } = useThread(selectedThreadId);
  const { data: selectedContent, isLoading: contentLoading } = useMessageContent(selectedMessageId);
  const { data: threadLinksData } = useThreadLinks(selectedThreadId, 0.5);

  const prefetchThread = usePrefetchThread();

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleClear = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    inputRef.current?.focus();
  }, []);

  const handleBack = useCallback(() => {
    if (onClose) {
      onClose();
    } else {
      router.back();
    }
  }, [router, onClose]);

  const handleThreadClick = useCallback((threadId: string) => {
    setSelectedThreadId(threadId);
    setSelectedMessageId(null);
  }, []);

  const handleThreadHover = useCallback((threadId: string) => {
    if (threadId !== selectedThreadId) {
      prefetchThread(threadId);
    }
  }, [selectedThreadId, prefetchThread]);

  const handleMessageClick = useCallback((providerMessageId: string) => {
    setSelectedMessageId(providerMessageId);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (searchQuery) {
          handleClear();
        } else if (onClose) {
          onClose();
        } else {
          router.back();
        }
      }
    },
    [searchQuery, handleClear, router, onClose]
  );

  const selectedAttachments = selectedContent?.attachments || [];

  return (
    <div
      data-testid="email-surface"
      className={cn('h-screen flex flex-col bg-[#1c1c1e] font-body', className)}
    >
      {needsReconnect && (
        <div className="bg-orange-500/10 border-b border-orange-500/30 px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-orange-500" />
              <span className="text-[12px] text-gray-400">
                {outlookStatus?.isExpired ? 'Session expired' : 'Not connected'}
              </span>
            </div>
            <button
              onClick={handleReconnect}
              disabled={reconnecting}
              className="text-[11px] text-orange-500 hover:underline"
            >
              {reconnecting ? 'Connecting...' : 'Reconnect'}
            </button>
          </div>
        </div>
      )}

      {!needsReconnect && isDegraded && (
        <div className="bg-orange-500/10 border-b border-orange-500/30 px-4 py-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-orange-500" />
            <span className="text-[12px] text-gray-400">Sync paused</span>
          </div>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT: Correspondence List */}
        <div className="w-[340px] flex-shrink-0 border-r border-white/10 flex flex-col">
          <div className="px-4 py-3 border-b border-white/10">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {isOverlayMode && (
                  <button
                    onClick={handleBack}
                    className="p-1.5 -ml-1.5 rounded text-gray-500 hover:text-gray-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                <h1 className="text-[14px] font-medium text-gray-300">
                  Correspondence
                </h1>
              </div>
              <button className="p-1.5 rounded text-gray-500 hover:text-gray-400 transition-colors">
                <MoreHorizontal className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-white/5 border border-white/10">
              <Filter className="w-3.5 h-3.5 text-gray-500" />
              <input
                ref={inputRef}
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Filter..."
                className="flex-1 bg-transparent text-[12px] text-gray-300 placeholder:text-gray-500 outline-none"
              />
              {searchQuery && (
                <button onClick={handleClear} className="text-gray-500 hover:text-gray-400">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {displayLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
              </div>
            )}

            {displayError && (
              <div className="py-6 text-center px-4">
                <p className="text-[11px] text-red-400">Failed to load</p>
                <button onClick={() => refetch()} className="text-[11px] text-celeste-accent mt-1">
                  Retry
                </button>
              </div>
            )}

            {!displayLoading && !displayError && displayThreads.length === 0 && (
              <div className="py-8 text-center px-4">
                <p className="text-[11px] text-gray-500">
                  {debouncedQuery ? 'No matches' : 'No correspondence'}
                </p>
              </div>
            )}

            {!displayLoading && !displayError && displayThreads.length > 0 && (
              <>
                {displayThreads.map((thread) => (
                  <CorrespondenceRow
                    key={thread.id}
                    thread={thread as EmailThread}
                    isSelected={selectedThreadId === thread.id}
                    onClick={() => handleThreadClick(thread.id)}
                    onHover={() => handleThreadHover(thread.id)}
                  />
                ))}

                {!isSearching && (page > 1 || hasMore) && (
                  <div className="flex items-center justify-between px-4 py-2 border-t border-white/10">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="text-[10px] text-gray-500 disabled:opacity-30"
                    >
                      ← Prev
                    </button>
                    <span className="text-[10px] text-gray-500">{page}</span>
                    <button
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!hasMore}
                      className="text-[10px] text-gray-500 disabled:opacity-30"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* RIGHT: Inspector Panel */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedThreadId && (
            <div className="h-full flex items-center justify-center">
              <p className="text-[13px] text-gray-500">
                Select a message to inspect correspondence.
              </p>
            </div>
          )}

          {selectedThreadId && threadLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
            </div>
          )}

          {selectedThread && selectedThreadId && (
            <InspectorPanel
              thread={selectedThread}
              selectedMessageId={selectedMessageId}
              onMessageSelect={handleMessageClick}
              content={selectedContent}
              contentLoading={contentLoading}
              linkedItems={threadLinksData?.links || []}
              attachments={selectedAttachments}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// CORRESPONDENCE ROW
// ============================================================================

interface CorrespondenceRowProps {
  thread: EmailThread & { from_display_name?: string | null };
  isSelected: boolean;
  onClick: () => void;
  onHover?: () => void;
}

function CorrespondenceRow({ thread, isSelected, onClick, onHover }: CorrespondenceRowProps) {
  const systemState: SystemState = thread.confidence
    ? thread.confidence === 'deterministic' ? 'attached' : 'referenced'
    : 'unlinked';

  const entityTitle = thread.latest_subject || '(No subject)';
  const sender = thread.from_display_name || '';

  return (
    <button
      data-testid="thread-row"
      onClick={onClick}
      onMouseEnter={onHover}
      className={cn(
        'w-full flex items-start gap-3 px-4 py-3 text-left transition-colors border-l-2',
        isSelected
          ? 'bg-celeste-accent-subtle border-l-celeste-accent'
          : 'hover:bg-white/5 border-l-transparent'
      )}
    >
      <div className="mt-1.5">
        <div className={cn(
          'w-1.5 h-1.5 rounded-full',
          isSelected ? 'bg-celeste-accent' : 'bg-gray-600'
        )} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h3 className={cn(
            'text-[13px] font-medium leading-tight truncate',
            isSelected ? 'text-white' : 'text-gray-300'
          )}>
            {entityTitle}
          </h3>
          <span className="text-[10px] text-gray-500 whitespace-nowrap">
            {formatTime(thread.last_activity_at)}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-1">
          <SystemStateBadge state={systemState} />
          {thread.has_attachments && (
            <div className="flex items-center gap-1 text-gray-500">
              <Paperclip className="w-2.5 h-2.5" />
              <span className="text-[10px]">{thread.message_count}</span>
            </div>
          )}
        </div>

        {sender && (
          <p className="text-[11px] text-gray-500 mt-1 truncate">
            {sender}
          </p>
        )}
      </div>

      {thread.message_count > 1 && (
        <div className="flex items-center gap-0.5 text-gray-500">
          <span className="text-[10px]">‹</span>
          <span className="text-[10px]">{thread.message_count}</span>
        </div>
      )}
    </button>
  );
}

// ============================================================================
// SYSTEM STATE BADGE
// ============================================================================

function SystemStateBadge({ state }: { state: SystemState }) {
  const config = {
    attached: { label: 'Attached', className: 'bg-green-500/20 text-green-400' },
    referenced: { label: 'Referenced', className: 'bg-celeste-accent-subtle text-celeste-accent' },
    archived: { label: 'Archived', className: 'bg-gray-500/20 text-gray-400' },
    unlinked: { label: '', className: '' },
  };

  const { label, className: badgeClass } = config[state];
  if (!label) return null;

  return (
    <span className={cn('px-1.5 py-0.5 rounded text-[9px] font-medium', badgeClass)}>
      {label}
    </span>
  );
}

// ============================================================================
// INSPECTOR PANEL
// ============================================================================

interface InspectorPanelProps {
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
  linkedItems: ThreadLink[];
  attachments: Array<{
    id: string;
    name: string;
    contentType?: string;
    size?: number;
  }>;
}

function InspectorPanel({
  thread,
  selectedMessageId,
  onMessageSelect,
  content,
  contentLoading,
  linkedItems,
  attachments,
}: InspectorPanelProps) {
  const [viewer, setViewer] = useState<{
    open: boolean;
    fileName: string;
    contentType: string;
    blobUrl: string;
  }>({ open: false, fileName: '', contentType: '', blobUrl: '' });

  const primaryLinkedEntity = useMemo(() => {
    if (!linkedItems.length) return null;
    const deterministic = linkedItems.find((l) => l.confidence_level === 'deterministic');
    if (deterministic) return deterministic;
    return linkedItems.sort((a, b) => b.confidence - a.confidence)[0];
  }, [linkedItems]);

  const panelTitle = primaryLinkedEntity
    ? `${primaryLinkedEntity.object_type.replace('_', ' ').toUpperCase()}: ${primaryLinkedEntity.object_id.slice(0, 8)}...`
    : thread.latest_subject || '(No subject)';

  const handleViewAttachment = useCallback(async (att: { id: string; name: string }) => {
    if (!selectedMessageId) return;

    try {
      const result = await fetchAttachmentBlob(selectedMessageId, att.id, true);
      if (viewer.blobUrl) URL.revokeObjectURL(viewer.blobUrl);

      setViewer({
        open: true,
        fileName: result.fileName,
        contentType: result.contentType,
        blobUrl: URL.createObjectURL(result.blob),
      });
    } catch (err) {
      console.error('Failed to load attachment:', err);
    }
  }, [selectedMessageId, viewer.blobUrl]);

  const handleCloseViewer = useCallback(() => {
    if (viewer.blobUrl) URL.revokeObjectURL(viewer.blobUrl);
    setViewer({ open: false, fileName: '', contentType: '', blobUrl: '' });
  }, [viewer.blobUrl]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-white/10 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-[15px] font-medium text-white truncate">
            {panelTitle}
          </h2>
        </div>
        <button className="p-1.5 rounded text-gray-500 hover:text-gray-400">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {thread.messages.length > 1 && (
          <div className="px-6 py-2 border-b border-white/10 flex gap-1 overflow-x-auto">
            {thread.messages.map((msg, i) => (
              <button
                key={msg.id}
                onClick={() => onMessageSelect(msg.provider_message_id)}
                className={cn(
                  'px-2.5 py-1 rounded text-[11px] whitespace-nowrap transition-colors',
                  selectedMessageId === msg.provider_message_id
                    ? 'bg-celeste-accent-subtle text-celeste-accent'
                    : 'text-gray-500 hover:text-gray-400'
                )}
              >
                <span className={cn(
                  'inline-block w-1.5 h-1.5 rounded-full mr-1.5',
                  msg.direction === 'inbound' ? 'bg-celeste-accent' : 'bg-green-500'
                )} />
                {msg.from_display_name || `Message ${i + 1}`}
              </button>
            ))}
          </div>
        )}

        {contentLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
          </div>
        )}

        {!contentLoading && content && (
          <div className="px-6 py-4">
            <div className="space-y-0.5 text-[11px] text-gray-500 mb-4 pb-4 border-b border-white/5">
              {content.from_address?.emailAddress && (
                <div>
                  <span>From: </span>
                  <span className="text-gray-400">
                    {content.from_address.emailAddress.name || content.from_address.emailAddress.address}
                  </span>
                </div>
              )}
              {content.to_recipients?.length > 0 && (
                <div>
                  <span>To: </span>
                  <span className="text-gray-400">
                    {content.to_recipients.map((r) => r.emailAddress?.address).join(', ')}
                  </span>
                </div>
              )}
              {content.sent_at && (
                <div>
                  <span>Date: </span>
                  <span className="text-gray-400">
                    {new Date(content.sent_at).toLocaleDateString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              )}
              {content.subject && (
                <div>
                  <span>Subject: </span>
                  <span className="text-gray-400">{content.subject}</span>
                </div>
              )}
            </div>

            <div className="text-[13px] text-gray-300 leading-relaxed">
              {content.body?.contentType === 'html' ? (
                <div
                  className="prose prose-invert prose-sm max-w-none
                    [&_a]:text-celeste-accent [&_a]:no-underline [&_a:hover]:underline
                    [&_img]:max-w-full [&_img]:h-auto [&_img[data-blocked-src]]:hidden
                    [&_table]:border-collapse [&_td]:border [&_td]:border-white/10 [&_td]:p-2"
                  dangerouslySetInnerHTML={{ __html: sanitizeHtml(content.body.content) }}
                />
              ) : (
                <pre className="whitespace-pre-wrap font-sans">
                  {content.body?.content || content.body_preview || '(No content)'}
                </pre>
              )}
            </div>

            {attachments.length > 0 && (
              <div className="mt-6 pt-4 border-t border-white/5">
                <h4 className="text-[11px] font-medium text-gray-500 mb-2">
                  Attachments
                </h4>
                <div className="space-y-1">
                  {attachments.map((att) => (
                    <button
                      key={att.id}
                      onClick={() => handleViewAttachment(att)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded bg-white/5 hover:bg-white/10 transition-colors text-left"
                    >
                      <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                      <span className="text-[12px] text-gray-300 truncate flex-1">
                        {att.name}
                      </span>
                      {att.size && (
                        <span className="text-[10px] text-gray-500">
                          ({formatFileSize(att.size)})
                        </span>
                      )}
                      <Paperclip className="w-3 h-3 text-gray-500" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {linkedItems.length > 0 && (
              <div className="mt-6 pt-4 border-t border-white/5">
                <h4 className="text-[11px] font-medium text-gray-500 mb-2">
                  Linked Items
                </h4>
                <div className="space-y-1">
                  {linkedItems.map((item) => (
                    <LinkedItemCard key={item.id} item={item} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!contentLoading && !content && selectedMessageId && (
          <div className="px-6 py-8 text-center">
            <p className="text-[11px] text-gray-500">
              Failed to load message
            </p>
          </div>
        )}

        {!selectedMessageId && thread.messages.length > 0 && (
          <div className="px-6 py-8 text-center">
            <p className="text-[11px] text-gray-500">
              Select a message to view
            </p>
            <button
              onClick={() => onMessageSelect(thread.messages[0].provider_message_id)}
              className="mt-2 text-[11px] text-celeste-accent hover:underline"
            >
              View first message
            </button>
          </div>
        )}
      </div>

      <DocumentViewerOverlay
        open={viewer.open}
        onClose={handleCloseViewer}
        fileName={viewer.fileName}
        contentType={viewer.contentType}
        blobUrl={viewer.blobUrl}
        allowDownload={false}
      />
    </div>
  );
}

// ============================================================================
// LINKED ITEM CARD
// ============================================================================

function LinkedItemCard({ item }: { item: ThreadLink }) {
  const icon = ENTITY_ICONS[item.object_type] || <FileText className="w-3 h-3" />;
  const typeLabel = item.object_type.replace('_', ' ');

  const statusClass = item.confidence_level === 'deterministic'
    ? 'text-green-400'
    : item.confidence_level === 'suggested'
      ? 'text-celeste-accent'
      : 'text-gray-400';

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded bg-white/5 group">
      <div className="p-1.5 rounded bg-white/5 text-gray-500">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium text-gray-300 truncate">
            {item.object_id.slice(0, 8)}...
          </span>
          <span className={cn('text-[9px] uppercase', statusClass)}>
            {item.confidence_level === 'deterministic' ? 'In Progress' : typeLabel}
          </span>
        </div>
        {item.suggested_reason && (
          <p className="text-[10px] text-gray-500 truncate">
            {item.suggested_reason}
          </p>
        )}
      </div>
      <ChevronRight className="w-4 h-4 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
