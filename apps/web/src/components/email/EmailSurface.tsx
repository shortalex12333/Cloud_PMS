'use client';

/**
 * EmailSurface - Signal Stream Interface
 *
 * Design Philosophy:
 * - Search is the product, not the inbox
 * - Linked context first, email body secondary
 * - No inbox clone - operational signal stream
 * - Break inbox addiction while maintaining trust
 *
 * Version: 2026-02-13-v2 (Spotlight-grade Redesign)
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Search,
  X,
  Paperclip,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertCircle,
  FileText,
  Wrench,
  Package,
  AlertTriangle,
  ExternalLink,
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
  useMarkThreadRead,
  type EmailThread,
  type EmailMessage,
  type MessageContent as MessageContentType,
  type ThreadLink,
} from '@/hooks/useEmailData';
import DocumentViewerOverlay from '@/components/viewer/DocumentViewerOverlay';
import { LinkEmailModal } from '@/components/email/LinkEmailModal';
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';
import { cn } from '@/lib/utils';
import DOMPurify from 'isomorphic-dompurify';

// ============================================================================
// CONSTANTS & CONFIG
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

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  work_order: <Wrench className="w-4 h-4" />,
  equipment: <Package className="w-4 h-4" />,
  fault: <AlertTriangle className="w-4 h-4" />,
  part: <Package className="w-4 h-4" />,
  handover: <FileText className="w-4 h-4" />,
};

type FilterState = 'all' | 'linked' | 'unlinked';

// ============================================================================
// UTILITIES
// ============================================================================

function sanitizeHtml(html: string): string {
  if (!html) return '';
  let clean = DOMPurify.sanitize(html, SANITIZE_CONFIG);
  clean = clean.replace(/<a\s+([^>]*?)>/gi, '<a $1 target="_blank" rel="noopener noreferrer">');
  clean = clean.replace(/<img\s+([^>]*?)src=["'](?!(cid:|data:image))/gi, '<img $1data-blocked-src="');
  return clean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getTimeGroup(dateStr: string | null): 'today' | 'yesterday' | 'last_week' | 'older' {
  if (!dateStr) return 'older';
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays <= 7) return 'last_week';
  return 'older';
}

function getInitials(name: string | null): string {
  if (!name) return '??';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

// ============================================================================
// TYPES
// ============================================================================

interface EmailSurfaceProps {
  className?: string;
  initialThreadId?: string;
  onClose?: () => void;
}

interface GroupedThreads {
  today: EmailThread[];
  yesterday: EmailThread[];
  last_week: EmailThread[];
  older: EmailThread[];
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
  const [filter, setFilter] = useState<FilterState>('all');
  const [page, setPage] = useState(1);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(initialThreadId || null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showCreateWOModal, setShowCreateWOModal] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Data hooks
  const { data, isLoading, error, refetch } = useInboxThreads(page, true, debouncedQuery);
  const { data: watcherStatus } = useWatcherStatus();
  const { data: outlookStatus, initiateReconnect, isLoading: outlookLoading } = useOutlookConnection();
  const { mutate: markAsRead } = useMarkThreadRead();
  const [reconnecting, setReconnecting] = useState(false);

  const threads = data?.threads || [];
  const hasMore = data?.has_more || false;

  const { data: searchData, isLoading: searchLoading } = useEmailSearch(debouncedQuery, { limit: 50 });

  const isSearching = debouncedQuery.length >= 2;

  // Transform search results to thread format
  const displayThreads = useMemo(() => {
    const rawThreads = isSearching
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
          confidence: undefined, // Search results don't have link info
          body_preview: r.preview_text,
        }))
      : threads;

    // Apply filter
    if (filter === 'linked') {
      return rawThreads.filter((t) => t.confidence);
    } else if (filter === 'unlinked') {
      return rawThreads.filter((t) => !t.confidence);
    }
    return rawThreads;
  }, [isSearching, searchData, threads, filter]);

  const displayLoading = isSearching ? searchLoading : isLoading;

  // Group threads by time
  const groupedThreads = useMemo((): GroupedThreads => {
    const groups: GroupedThreads = { today: [], yesterday: [], last_week: [], older: [] };
    displayThreads.forEach((thread) => {
      const group = getTimeGroup(thread.last_activity_at);
      groups[group].push(thread as EmailThread);
    });
    return groups;
  }, [displayThreads]);

  // Flat list for keyboard navigation
  const flatThreadList = useMemo(() => {
    return [
      ...groupedThreads.today,
      ...groupedThreads.yesterday,
      ...groupedThreads.last_week,
      ...groupedThreads.older,
    ];
  }, [groupedThreads]);

  // Selected thread data
  const { data: selectedThread, isLoading: threadLoading } = useThread(selectedThreadId);
  const { data: selectedContent, isLoading: contentLoading } = useMessageContent(selectedMessageId);
  const { data: threadLinksData } = useThreadLinks(selectedThreadId, 0.5);

  const prefetchThread = usePrefetchThread();

  const needsReconnect = !outlookLoading && outlookStatus && (!outlookStatus.isConnected || outlookStatus.isExpired);
  const isDegraded = watcherStatus?.sync_status === 'degraded' || watcherStatus?.sync_status === 'error';

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Auto-select first message when thread loads
  useEffect(() => {
    if (selectedThread?.messages?.length && !selectedMessageId) {
      setSelectedMessageId(selectedThread.messages[0].provider_message_id);
    }
  }, [selectedThread, selectedMessageId]);

  // Handlers
  const handleReconnect = useCallback(async () => {
    setReconnecting(true);
    const authUrl = await initiateReconnect();
    if (authUrl) {
      window.location.href = authUrl;
    } else {
      setReconnecting(false);
    }
  }, [initiateReconnect]);

  const handleThreadSelect = useCallback((threadId: string, index: number) => {
    setSelectedThreadId(threadId);
    setSelectedMessageId(null);
    setSelectedIndex(index);
    // Mark thread as read when selected
    markAsRead(threadId);
  }, [markAsRead]);

  const handleThreadHover = useCallback((threadId: string) => {
    if (threadId !== selectedThreadId) {
      prefetchThread(threadId);
    }
  }, [selectedThreadId, prefetchThread]);

  const handleClearSearch = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    searchInputRef.current?.focus();
  }, []);

  // Keyboard navigation (Spotlight-style)
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const newIndex = Math.min(selectedIndex + 1, flatThreadList.length - 1);
      if (flatThreadList[newIndex]) {
        handleThreadSelect(flatThreadList[newIndex].id, newIndex);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const newIndex = Math.max(selectedIndex - 1, 0);
      if (flatThreadList[newIndex]) {
        handleThreadSelect(flatThreadList[newIndex].id, newIndex);
      }
    } else if (e.key === 'Enter' && selectedThreadId) {
      // Could open full view or trigger primary action
    } else if (e.key === 'Escape') {
      if (searchQuery) {
        handleClearSearch();
      } else if (onClose) {
        onClose();
      }
    }
  }, [selectedIndex, flatThreadList, selectedThreadId, searchQuery, handleClearSearch, onClose, handleThreadSelect]);

  const selectedAttachments = selectedContent?.attachments || [];

  return (
    <div
      data-testid="email-surface"
      className={cn('h-screen flex flex-col bg-celeste-black-deep font-body', className)}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Connection warnings */}
      {needsReconnect && (
        <div className="bg-restricted-red/10 border-b border-restricted-red/30 px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-restricted-red" />
              <span className="text-[12px] text-celeste-text-secondary">
                {outlookStatus?.isExpired ? 'Session expired' : 'Not connected'}
              </span>
            </div>
            <button
              onClick={handleReconnect}
              disabled={reconnecting}
              className="text-[11px] text-restricted-red hover:underline"
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
            <span className="text-[12px] text-celeste-text-secondary">Sync paused</span>
          </div>
        </div>
      )}

      {/* TOP BAR: Search dominant */}
      <div className="px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-4">
          <h1 className="text-[14px] font-semibold text-celeste-text-title tracking-wide">Email</h1>

          {/* Search - dominant control */}
          <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg bg-celeste-black-base border border-white/10 focus-within:border-celeste-accent/50">
            <Search className="w-4 h-4 text-celeste-text-secondary" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search email..."
              className="flex-1 bg-transparent text-[13px] text-celeste-text-title placeholder:text-celeste-text-secondary/60 outline-none"
            />
            {searchQuery && (
              <button onClick={handleClearSearch} className="text-celeste-text-secondary hover:text-celeste-text-title">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filter */}
          <div className="flex items-center gap-1 text-[11px]">
            <button
              onClick={() => setFilter('all')}
              className={cn(
                'px-2 py-1 rounded transition-colors',
                filter === 'all' ? 'bg-white/10 text-celeste-text-title' : 'text-celeste-text-secondary hover:text-celeste-text-title'
              )}
            >
              All
            </button>
            <button
              onClick={() => setFilter('linked')}
              className={cn(
                'px-2 py-1 rounded transition-colors',
                filter === 'linked' ? 'bg-white/10 text-celeste-text-title' : 'text-celeste-text-secondary hover:text-celeste-text-title'
              )}
            >
              Linked
            </button>
            <button
              onClick={() => setFilter('unlinked')}
              className={cn(
                'px-2 py-1 rounded transition-colors',
                filter === 'unlinked' ? 'bg-white/10 text-celeste-text-title' : 'text-celeste-text-secondary hover:text-celeste-text-title'
              )}
            >
              Unlinked
            </button>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="btn-icon h-8 w-8"
            >
              <X className="w-[18px] h-[18px]" />
            </button>
          )}
        </div>
      </div>

      {/* MAIN CONTENT: Results | Context */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT: Results */}
        <div ref={listRef} className="w-[400px] flex-shrink-0 border-r border-white/10 overflow-y-auto">
          {displayLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-celeste-text-secondary" />
            </div>
          )}

          {error && (
            <div className="py-8 text-center px-4">
              <p className="text-[12px] text-restricted-red">Failed to load</p>
              <button onClick={() => refetch()} className="text-[12px] text-celeste-accent mt-2 hover:underline">
                Retry
              </button>
            </div>
          )}

          {!displayLoading && !error && displayThreads.length === 0 && (
            <div className="py-12 text-center px-4">
              <p className="text-[13px] text-celeste-text-secondary">
                {debouncedQuery ? 'No results found' : 'No emails'}
              </p>
            </div>
          )}

          {!displayLoading && !error && displayThreads.length > 0 && (
            <>
              <ResultsSection
                title="TODAY"
                threads={groupedThreads.today}
                selectedId={selectedThreadId}
                startIndex={0}
                onSelect={handleThreadSelect}
                onHover={handleThreadHover}
              />
              <ResultsSection
                title="YESTERDAY"
                threads={groupedThreads.yesterday}
                selectedId={selectedThreadId}
                startIndex={groupedThreads.today.length}
                onSelect={handleThreadSelect}
                onHover={handleThreadHover}
              />
              <ResultsSection
                title="LAST WEEK"
                threads={groupedThreads.last_week}
                selectedId={selectedThreadId}
                startIndex={groupedThreads.today.length + groupedThreads.yesterday.length}
                onSelect={handleThreadSelect}
                onHover={handleThreadHover}
              />
              <ResultsSection
                title="OLDER"
                threads={groupedThreads.older}
                selectedId={selectedThreadId}
                startIndex={groupedThreads.today.length + groupedThreads.yesterday.length + groupedThreads.last_week.length}
                onSelect={handleThreadSelect}
                onHover={handleThreadHover}
              />

              {!isSearching && hasMore && (
                <div className="px-4 py-3 border-t border-white/10">
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    className="text-[12px] text-celeste-accent hover:underline"
                  >
                    Load more
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* RIGHT: Context + Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden bg-celeste-black-base">
          {!selectedThreadId && (
            <div className="h-full flex items-center justify-center">
              <p className="text-[13px] text-celeste-text-secondary">
                Select an email to view context
              </p>
            </div>
          )}

          {selectedThreadId && threadLoading && (
            <div className="h-full flex items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-celeste-text-secondary" />
            </div>
          )}

          {selectedThread && selectedThreadId && (
            <ContextPane
              thread={selectedThread}
              content={selectedContent}
              contentLoading={contentLoading}
              linkedItems={threadLinksData?.links || []}
              attachments={selectedAttachments}
              onLinkEmail={() => setShowLinkModal(true)}
              onCreateWorkOrder={() => setShowCreateWOModal(true)}
            />
          )}

          {/* Link Email Modal */}
          {selectedThreadId && (
            <LinkEmailModal
              open={showLinkModal}
              onOpenChange={setShowLinkModal}
              threadId={selectedThreadId}
              threadSubject={selectedThread?.latest_subject || undefined}
            />
          )}

          {/* Create Work Order Modal */}
          <CreateWorkOrderModal
            open={showCreateWOModal}
            onOpenChange={setShowCreateWOModal}
            context={{
              suggested_title: selectedThread?.latest_subject || undefined,
            }}
          />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// RESULTS SECTION (grouped)
// ============================================================================

interface ResultsSectionProps {
  title: string;
  threads: EmailThread[];
  selectedId: string | null;
  startIndex: number;
  onSelect: (id: string, index: number) => void;
  onHover: (id: string) => void;
}

function ResultsSection({ title, threads, selectedId, startIndex, onSelect, onHover }: ResultsSectionProps) {
  if (threads.length === 0) return null;

  return (
    <div>
      <div className="px-4 py-2 sticky top-0 bg-celeste-black-deep z-10">
        <h2 className="text-[11px] font-semibold text-celeste-text-secondary uppercase tracking-wider">
          {title}
        </h2>
      </div>
      {threads.map((thread, i) => (
        <EmailRow
          key={thread.id}
          thread={thread}
          isSelected={selectedId === thread.id}
          onClick={() => onSelect(thread.id, startIndex + i)}
          onHover={() => onHover(thread.id)}
        />
      ))}
    </div>
  );
}

// ============================================================================
// EMAIL ROW
// ============================================================================

interface EmailRowProps {
  thread: EmailThread & { from_display_name?: string | null; body_preview?: string };
  isSelected: boolean;
  onClick: () => void;
  onHover: () => void;
}

function EmailRow({ thread, isSelected, onClick, onHover }: EmailRowProps) {
  const sender = thread.from_display_name || 'Unknown';
  const subject = thread.latest_subject || '(No subject)';
  const snippet = (thread as any).body_preview || '';
  const isLinked = !!thread.confidence;
  // Use actual is_read state from thread data (defaults to unread if not set)
  const isUnread = thread.is_read === false || thread.is_read === undefined;

  return (
    <button
      data-testid="email-row"
      onClick={onClick}
      onMouseEnter={onHover}
      className={cn(
        'w-full flex items-start gap-3 px-4 py-3 text-left transition-colors',
        isSelected
          ? 'bg-celeste-accent/20'
          : 'hover:bg-white/5',
        isUnread && 'border-l-2 border-l-celeste-accent',
        !isUnread && 'border-l-2 border-l-transparent'
      )}
    >
      {/* Avatar */}
      <div className="w-9 h-9 rounded-full bg-celeste-accent/30 flex items-center justify-center flex-shrink-0">
        <span className="text-[12px] font-medium text-celeste-accent">
          {getInitials(sender)}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={cn(
            'text-[13px] truncate',
            isUnread ? 'font-semibold text-celeste-text-title' : 'font-normal text-celeste-text-title/80'
          )}>
            {sender}
          </span>
          {/* Linked indicator */}
          {isLinked && (
            <span className="w-2 h-2 rounded-full bg-celeste-accent flex-shrink-0" />
          )}
        </div>
        <p className={cn(
          'text-[12px] truncate mt-0.5',
          isUnread ? 'font-medium text-celeste-text-title/90' : 'font-normal text-celeste-text-title/70'
        )}>
          {subject}
        </p>
        {snippet && (
          <p className="text-[11px] text-celeste-text-secondary truncate mt-0.5">
            {snippet}
          </p>
        )}
      </div>

      {/* Attachment indicator */}
      {thread.has_attachments && (
        <Paperclip className="w-3.5 h-3.5 text-celeste-text-secondary flex-shrink-0 mt-1" />
      )}
    </button>
  );
}

// ============================================================================
// CONTEXT PANE
// ============================================================================

interface ContextPaneProps {
  thread: {
    latest_subject: string | null;
    message_count: number;
    has_attachments: boolean;
    messages: EmailMessage[];
  };
  content: MessageContentType | null | undefined;
  contentLoading: boolean;
  linkedItems: ThreadLink[];
  attachments: Array<{
    id: string;
    name: string;
    contentType?: string;
    size?: number;
  }>;
  onLinkEmail: () => void;
  onCreateWorkOrder: () => void;
}

function ContextPane({
  thread,
  content,
  contentLoading,
  linkedItems,
  attachments,
  onLinkEmail,
  onCreateWorkOrder,
}: ContextPaneProps) {
  const [showBody, setShowBody] = useState(false);
  const [showAttachments, setShowAttachments] = useState(false);
  const [viewer, setViewer] = useState<{
    open: boolean;
    fileName: string;
    contentType: string;
    blobUrl: string;
  }>({ open: false, fileName: '', contentType: '', blobUrl: '' });

  const firstMessage = thread.messages?.[0];
  const providerMessageId = firstMessage?.provider_message_id;

  const handleViewAttachment = useCallback(async (att: { id: string; name: string }) => {
    if (!providerMessageId) return;

    try {
      const result = await fetchAttachmentBlob(providerMessageId, att.id, true);
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
  }, [providerMessageId, viewer.blobUrl]);

  const handleCloseViewer = useCallback(() => {
    if (viewer.blobUrl) URL.revokeObjectURL(viewer.blobUrl);
    setViewer({ open: false, fileName: '', contentType: '', blobUrl: '' });
  }, [viewer.blobUrl]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        {/* LINKED SECTION - Always first */}
        <div className="px-6 py-4 border-b border-white/10">
          <h3 className="text-[11px] font-semibold text-celeste-text-secondary uppercase tracking-wider mb-3">
            Linked
          </h3>

          {linkedItems.length > 0 ? (
            <div className="space-y-2">
              {linkedItems.map((item) => (
                <LinkedItemRow key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="py-4">
              <p className="text-[13px] text-celeste-text-secondary mb-4">No links yet.</p>
              <div className="flex gap-2">
                <button
                  onClick={onLinkEmail}
                  className="px-4 py-2 rounded bg-celeste-accent text-white text-[12px] font-medium hover:bg-celeste-accent/90 transition-colors"
                >
                  Link...
                </button>
                <button
                  onClick={onCreateWorkOrder}
                  className="px-4 py-2 rounded bg-white/10 text-celeste-text-title text-[12px] font-medium hover:bg-white/15 transition-colors"
                >
                  Create Work Order
                </button>
              </div>
            </div>
          )}
        </div>

        {/* EMAIL VIEWER SECTION */}
        <div className="px-6 py-4">
          <h3 className="text-[11px] font-semibold text-celeste-text-secondary uppercase tracking-wider mb-3">
            Email
          </h3>

          {contentLoading && (
            <div className="py-8 flex justify-center">
              <Loader2 className="h-4 w-4 animate-spin text-celeste-text-secondary" />
            </div>
          )}

          {!contentLoading && content && (
            <>
              {/* Compact header */}
              <div className="mb-4">
                <h4 className="text-[14px] font-medium text-celeste-text-title mb-2">
                  {content.subject || thread.latest_subject || '(No subject)'}
                </h4>
                <div className="space-y-1 text-[12px]">
                  {content.from_address?.emailAddress && (
                    <div className="flex gap-2">
                      <span className="text-celeste-text-secondary w-12">From</span>
                      <span className="text-celeste-text-title">
                        {content.from_address.emailAddress.name || content.from_address.emailAddress.address}
                      </span>
                    </div>
                  )}
                  {content.to_recipients?.length > 0 && (
                    <div className="flex gap-2">
                      <span className="text-celeste-text-secondary w-12">To</span>
                      <span className="text-celeste-text-title/80 truncate">
                        {content.to_recipients.map((r) => r.emailAddress?.address).join(', ')}
                      </span>
                    </div>
                  )}
                  {content.sent_at && (
                    <div className="flex gap-2">
                      <span className="text-celeste-text-secondary w-12">Date</span>
                      <span className="text-celeste-text-title/80">
                        {new Date(content.sent_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-4 mb-4 pb-4 border-b border-white/10">
                <button className="text-[12px] text-celeste-text-title/80 hover:text-celeste-text-title transition-colors">
                  Reply
                </button>
                <button className="text-[12px] text-celeste-text-title/80 hover:text-celeste-text-title transition-colors">
                  Reply All
                </button>
                <button className="text-[12px] text-celeste-text-title/80 hover:text-celeste-text-title transition-colors">
                  Forward
                </button>
                <button className="text-[12px] text-celeste-text-secondary hover:text-celeste-text-title transition-colors flex items-center gap-1">
                  <ExternalLink className="w-3 h-3" />
                  Open in Outlook
                </button>
              </div>

              {/* Body toggle */}
              <button
                onClick={() => setShowBody(!showBody)}
                className="flex items-center gap-2 text-[12px] text-celeste-text-secondary hover:text-celeste-text-title transition-colors mb-3"
              >
                {showBody ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                {showBody ? 'Hide body' : 'Show body'}
              </button>

              {showBody && (
                <div className="text-[13px] text-celeste-text-title/90 leading-relaxed mb-4">
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
              )}

              {/* Attachments */}
              {attachments.length > 0 && (
                <div>
                  <button
                    onClick={() => setShowAttachments(!showAttachments)}
                    className="flex items-center gap-2 text-[12px] text-celeste-text-secondary hover:text-celeste-text-title transition-colors"
                  >
                    {showAttachments ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    Attachments ({attachments.length})
                  </button>

                  {showAttachments && (
                    <div className="mt-2 space-y-1">
                      {attachments.map((att) => (
                        <button
                          key={att.id}
                          onClick={() => handleViewAttachment(att)}
                          className="w-full flex items-center gap-2 px-3 py-2 rounded bg-white/5 hover:bg-white/10 transition-colors text-left"
                        >
                          <FileText className="w-4 h-4 text-celeste-text-secondary flex-shrink-0" />
                          <span className="text-[12px] text-celeste-text-title truncate flex-1">
                            {att.name}
                          </span>
                          {att.size && (
                            <span className="text-[11px] text-celeste-text-secondary">
                              {formatFileSize(att.size)}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {!contentLoading && !content && (
            <p className="text-[12px] text-celeste-text-secondary">
              Unable to load email content
            </p>
          )}
        </div>
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
// LINKED ITEM ROW
// ============================================================================

function LinkedItemRow({ item }: { item: ThreadLink }) {
  const icon = ENTITY_ICONS[item.object_type] || <FileText className="w-4 h-4" />;
  const typeLabel = item.object_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded bg-white/5 hover:bg-white/10 transition-colors text-left group">
      <div className="p-2 rounded bg-celeste-accent/20 text-celeste-accent">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-[13px] font-medium text-celeste-text-title">
          {typeLabel}
        </span>
        {item.suggested_reason && (
          <p className="text-[11px] text-celeste-text-secondary truncate">
            {item.suggested_reason}
          </p>
        )}
      </div>
      <ChevronRight className="w-4 h-4 text-celeste-text-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  );
}
