'use client';

/**
 * /email — Split-pane email view.
 * Left: thread list (320px). Right: thread detail.
 * URL state via ?thread={id} for deep links.
 * Matches email-split.html prototype.
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Mail, RefreshCw } from 'lucide-react';
import { useInboxThreads } from '@/hooks/useEmailData';
import { useAuth } from '@/hooks/useAuth';
import { ThreadRow, ThreadDetail, EmptyDetail } from '@/components/email/EmailShared';

type FilterState = 'all' | 'unlinked' | 'linked';

function getTimeGroup(dateStr: string | null): string {
  if (!dateStr) return 'older';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return 'today';
  if (diff === 1) return 'yesterday';
  if (diff <= 7) return 'last_7_days';
  return 'older';
}

const GROUP_LABELS: Record<string, string> = {
  today: 'Today', yesterday: 'Yesterday', last_7_days: 'Last 7 Days', older: 'Older',
};

function EmailSplitContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedThreadId = searchParams.get('thread');
  const { user } = useAuth();

  const [filter, setFilter] = React.useState<FilterState>('all');
  const [page, setPage] = React.useState(1);

  const linked = filter === 'linked';
  const { data, isLoading, refetch } = useInboxThreads(page, linked);
  const threads = data?.threads || [];
  const total = data?.total || 0;

  // Group threads by time
  const grouped = React.useMemo(() => {
    const groups: Record<string, typeof threads> = { today: [], yesterday: [], last_7_days: [], older: [] };
    const filtered = filter === 'unlinked' ? threads.filter(t => !t.link_id) : threads;
    filtered.forEach(t => {
      const g = getTimeGroup(t.last_activity_at);
      groups[g].push(t);
    });
    return groups;
  }, [threads, filter]);

  const handleSelectThread = React.useCallback((threadId: string) => {
    router.push(`/email?thread=${threadId}`, { scroll: false });
  }, [router]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)', fontSize: 13, lineHeight: 1.5, WebkitFontSmoothing: 'antialiased', background: 'var(--surface-base)', color: 'var(--txt)' }}>

      {/* Topbar — matches elegant.html */}
      <header style={{
        height: 40, flexShrink: 0, display: 'flex', alignItems: 'center', padding: '0 20px', gap: 8,
        borderBottom: '1px solid var(--border-faint)', background: 'rgba(12,11,10,0.70)',
        backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
      }}>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#4A9EC0' }}>Celeste</div>
        <div style={{ width: 1, height: 12, background: 'var(--border-sub)', margin: '0 4px' }} />
        <div style={{ fontSize: 11, color: 'var(--txt3)' }}><em style={{ fontStyle: 'normal', color: 'rgba(74,158,192,0.80)' }}>{user?.yachtName || 'SY Vessel'}</em></div>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--txt-ghost)', background: 'var(--surface-el)', border: '1px solid var(--border-sub)', borderRadius: 3, padding: '2px 7px' }}>{user?.role || 'Crew'}</div>
      </header>

      {/* Split layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ═══ LEFT PANE ═══ */}
        <div style={{ width: 320, flexShrink: 0, borderRight: '1px solid var(--border-sub)', display: 'flex', flexDirection: 'column', background: 'var(--surface)' }}>

          {/* List header */}
          <div style={{ display: 'flex', alignItems: 'center', padding: '10px 14px', borderBottom: '1px solid var(--border-sub)', gap: 6, flexShrink: 0 }}>
            <div style={{ width: 22, height: 22, borderRadius: 5, background: 'var(--teal-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Mail size={11} color="var(--mark)" />
            </div>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--txt)' }}>Email</span>
            <span style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>{total}</span>
            <div style={{ flex: 1 }} />
            <button onClick={() => refetch()} style={{ width: 22, height: 22, borderRadius: 4, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)' }}>
              <RefreshCw size={11} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: 2, padding: '6px 14px', borderBottom: '1px solid var(--border-faint)', flexShrink: 0 }}>
            {(['all', 'unlinked', 'linked'] as FilterState[]).map(f => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1); }}
                style={{
                  padding: '3px 8px', borderRadius: 3, fontSize: 10, fontWeight: 600,
                  cursor: 'pointer', border: 'none',
                  color: filter === f ? 'var(--mark)' : 'var(--txt3)',
                  background: filter === f ? 'var(--teal-bg)' : 'none',
                  fontFamily: 'var(--font-sans)', textTransform: 'uppercase', letterSpacing: '0.04em',
                }}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Thread list */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {isLoading && threads.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48 }}>
                <div style={{ width: 20, height: 20, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              </div>
            ) : threads.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
                <Mail size={32} style={{ color: 'var(--txt-ghost)', marginBottom: 8 }} />
                <div style={{ fontSize: 12, color: 'var(--txt3)' }}>No email threads</div>
              </div>
            ) : (
              (['today', 'yesterday', 'last_7_days', 'older'] as const).map(group => {
                const items = grouped[group];
                if (!items || items.length === 0) return null;
                return (
                  <div key={group}>
                    <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--txt-ghost)', padding: '8px 14px 3px' }}>
                      {GROUP_LABELS[group]}
                    </div>
                    {items.map(thread => (
                      <ThreadRow
                        key={thread.id}
                        thread={thread}
                        isSelected={thread.id === selectedThreadId}
                        onClick={() => handleSelectThread(thread.id)}
                      />
                    ))}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ═══ RIGHT PANE ═══ */}
        <div style={{ flex: 1, overflowY: 'auto', background: 'var(--surface-base)' }}>
          {selectedThreadId ? (
            <ThreadDetail threadId={selectedThreadId} />
          ) : (
            <EmptyDetail />
          )}
        </div>

      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function EmailPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-base)' }}>
          <div style={{ width: 20, height: 20, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      }
    >
      <EmailSplitContent />
    </React.Suspense>
  );
}
