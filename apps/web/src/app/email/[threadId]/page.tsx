'use client';

/**
 * /email/[threadId] — Deep link to a single email thread.
 * For shared URLs and mobile. Uses shared ThreadDetail component.
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { ThreadDetail } from '@/components/email/EmailShared';
import { useAuth } from '@/hooks/useAuth';

function EmailThreadDeepLink() {
  const router = useRouter();
  const params = useParams();
  const threadId = params.threadId as string;
  const { user } = useAuth();

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: 'var(--surface-base)', fontFamily: 'var(--font-sans)', fontSize: 13, lineHeight: 1.5 }}>
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

      <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 20px 64px' }}>
        <button
          onClick={() => router.push('/email')}
          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--txt3)', cursor: 'pointer', marginBottom: 20, background: 'none', border: 'none', fontFamily: 'var(--font-sans)' }}
        >
          <ChevronLeft size={14} /> Back to inbox
        </button>

        <div style={{
          background: 'var(--surface)',
          borderTop: '1px solid rgba(255,255,255,0.09)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          borderRadius: 8, overflow: 'hidden',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.60), 0 28px 80px rgba(0,0,0,0.55)',
        }}>
          <ThreadDetail threadId={threadId} />
        </div>
      </div>
    </div>
  );
}

export default function EmailThreadDetailPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-base)' }}>
          <div style={{ width: 20, height: 20, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      }
    >
      <EmailThreadDeepLink />
    </React.Suspense>
  );
}
