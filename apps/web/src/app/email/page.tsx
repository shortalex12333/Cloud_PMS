'use client';

/**
 * Email List Page - /email
 *
 * Tier 2 fragmented route for email.
 * Displays email threads with search and filtering.
 *
 * @see REQUIREMENTS_TABLE.md - T2-EM-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useInboxThreads, useEmailSearch, type EmailThread } from '@/hooks/useEmailData';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  React.useEffect(() => { if (!isFragmentedRoutesEnabled()) router.replace('/app?openEmail=true'); }, [router]);
  if (!isFragmentedRoutesEnabled()) return <div className="h-screen flex items-center justify-center bg-surface-base"><p className="text-txt-secondary">Redirecting...</p></div>;
  return <>{children}</>;
}

type FilterState = 'all' | 'linked' | 'unlinked';

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

function getTimeGroupLabel(group: string): string {
  switch (group) {
    case 'today': return 'Today';
    case 'yesterday': return 'Yesterday';
    case 'last_week': return 'Last 7 Days';
    case 'older': return 'Older';
    default: return group;
  }
}

function ThreadRow({ thread, isSelected, onClick }: { thread: EmailThread; isSelected: boolean; onClick: () => void }) {
  const hasLink = !!thread.link_id;
  const isUnread = !thread.is_read;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-surface-border',
        'hover:bg-surface-hover transition-colors focus:outline-none focus:bg-surface-hover',
        isSelected && 'bg-surface-active',
        isUnread && 'bg-surface-elevated/50'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {isUnread && <span className="w-2 h-2 rounded-full bg-brand-primary flex-shrink-0" />}
            {hasLink ? (
              <StatusPill status="success" label="Linked" />
            ) : (
              <StatusPill status="neutral" label="Unlinked" />
            )}
            {thread.has_attachments && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-tertiary">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
              </svg>
            )}
          </div>
          <h3 className={cn('text-sm text-txt-primary truncate', isUnread && 'font-semibold')}>
            {thread.latest_subject || '(No subject)'}
          </h3>
          <p className="text-xs text-txt-tertiary mt-1">
            {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="text-xs text-txt-tertiary whitespace-nowrap">
          {thread.last_activity_at ? new Date(thread.last_activity_at).toLocaleDateString() : ''}
        </div>
      </div>
    </button>
  );
}

function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">
        {hasSearch ? 'No Results' : 'No Emails'}
      </h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        {hasSearch
          ? 'Try adjusting your search terms or filters.'
          : 'Email threads will appear here once synced from Outlook.'}
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-surface-border border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading emails...</p>
      </div>
    </div>
  );
}

function EmailPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedThreadId = searchParams.get('thread');

  const [searchQuery, setSearchQuery] = React.useState('');
  const [debouncedQuery, setDebouncedQuery] = React.useState('');
  const [filter, setFilter] = React.useState<FilterState>('all');
  const [page, setPage] = React.useState(1);

  // Debounce search
  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Use search when query is present, otherwise use inbox
  const useSearch = debouncedQuery.length >= 2;
  const linked = filter === 'linked' ? true : filter === 'unlinked' ? false : false;

  const { data: inboxData, isLoading: isLoadingInbox, error: inboxError } = useInboxThreads(
    page,
    filter === 'linked',
    useSearch ? '' : debouncedQuery,
    undefined
  );

  const { data: searchData, isLoading: isLoadingSearch } = useEmailSearch(
    debouncedQuery,
    { limit: 50 }
  );

  const isLoading = useSearch ? isLoadingSearch : isLoadingInbox;

  // Get threads from appropriate source
  const threads = React.useMemo(() => {
    if (useSearch && searchData?.results) {
      // Convert search results to thread-like format
      return searchData.results.map(r => ({
        id: r.thread_id,
        provider_conversation_id: r.thread_id,
        latest_subject: r.subject,
        message_count: 1,
        has_attachments: r.has_attachments,
        source: 'search',
        first_message_at: r.sent_at,
        last_activity_at: r.sent_at,
        is_read: true,
      } as EmailThread));
    }
    return inboxData?.threads || [];
  }, [useSearch, searchData, inboxData]);

  // Group threads by time
  const groupedThreads = React.useMemo(() => {
    const groups: Record<string, EmailThread[]> = {
      today: [],
      yesterday: [],
      last_week: [],
      older: [],
    };
    threads.forEach(thread => {
      const group = getTimeGroup(thread.last_activity_at);
      groups[group].push(thread);
    });
    return groups;
  }, [threads]);

  const handleSelect = React.useCallback((threadId: string) => {
    router.push(`/email?thread=${threadId}`, { scroll: false });
  }, [router]);

  const handleViewThread = React.useCallback((threadId: string) => {
    router.push(`/email/${threadId}`);
  }, [router]);

  const handleCloseDetail = React.useCallback(() => {
    router.push('/email', { scroll: false });
  }, [router]);

  const listContent = React.useMemo(() => {
    if (isLoading) return <LoadingState />;
    if (inboxError) return <div className="flex items-center justify-center h-full"><p className="text-status-critical">Failed to load emails</p></div>;
    if (threads.length === 0) return <EmptyState hasSearch={useSearch} />;

    return (
      <div>
        {(['today', 'yesterday', 'last_week', 'older'] as const).map(group => {
          const groupThreads = groupedThreads[group];
          if (groupThreads.length === 0) return null;
          return (
            <div key={group}>
              <div className="px-6 py-2 bg-surface-elevated border-b border-surface-border">
                <span className="text-xs font-medium text-txt-tertiary uppercase tracking-wider">
                  {getTimeGroupLabel(group)}
                </span>
              </div>
              {groupThreads.map(thread => (
                <ThreadRow
                  key={thread.id}
                  thread={thread}
                  isSelected={thread.id === selectedThreadId}
                  onClick={() => handleSelect(thread.id)}
                />
              ))}
            </div>
          );
        })}
        {inboxData?.has_more && (
          <div className="p-4 text-center">
            <button
              onClick={() => setPage(p => p + 1)}
              className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
            >
              Load More
            </button>
          </div>
        )}
      </div>
    );
  }, [threads, groupedThreads, isLoading, inboxError, useSearch, selectedThreadId, handleSelect, inboxData?.has_more]);

  return (
    <RouteLayout
      pageTitle="Email"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4 flex-1">
          <h1 className="text-lg font-semibold text-txt-primary">Email</h1>
          <div className="flex-1 max-w-md">
            <div className="relative">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3 top-1/2 -translate-y-1/2 text-txt-tertiary">
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              <input
                type="text"
                placeholder="Search emails... (from:, to:, has:attachment)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-surface-elevated border border-surface-border rounded-lg text-sm text-txt-primary placeholder:text-txt-tertiary focus:outline-none focus:border-brand-primary"
              />
            </div>
          </div>
          <div className="flex gap-1">
            {(['all', 'linked', 'unlinked'] as const).map(f => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1); }}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  filter === f
                    ? 'bg-brand-primary text-white'
                    : 'bg-surface-elevated text-txt-secondary hover:bg-surface-hover'
                )}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      }
      primaryPanel={selectedThreadId ? {
        visible: true,
        title: threads.find(t => t.id === selectedThreadId)?.latest_subject || 'Email Thread',
        children: (
          <div className="p-4 space-y-4">
            <p className="text-sm text-txt-secondary">Thread selected. Click below to view full thread.</p>
            <button
              onClick={() => handleViewThread(selectedThreadId)}
              className="px-4 py-2 bg-brand-primary hover:bg-brand-primary/90 rounded-lg text-sm text-white transition-colors"
            >
              View Full Thread
            </button>
          </div>
        ),
      } : undefined}
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

export default function EmailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <EmailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
