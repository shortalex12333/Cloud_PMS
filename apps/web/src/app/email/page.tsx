'use client';

/**
 * /email — Dedicated email page using EmailInboxView.
 * Replaces legacy RouteLayout with Spotlight-grade UX.
 * Thread clicks navigate to /email?thread={id} for detail view.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { EmailInboxView } from '@/components/email/EmailInboxView';

function EmailPageContent() {
  const router = useRouter();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--surface-base)' }}>
      {/* Topbar */}
      <div style={{
        height: 44, display: 'flex', alignItems: 'center', padding: '0 16px',
        borderBottom: '1px solid var(--border-sub)', background: 'var(--surface)', gap: 12,
      }}>
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.12em',
          textTransform: 'uppercase', color: 'var(--mark)',
        }}>Celeste</span>
        <div style={{ flex: 1 }} />
      </div>

      {/* Content — centered, max-width matching search panel */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px 20px 64px' }}>
        {/* Back nav */}
        <button
          onClick={() => router.push('/')}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 12, color: 'var(--txt3)', cursor: 'pointer',
            marginBottom: 20, background: 'none', border: 'none',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <ChevronLeft size={14} /> Back to search
        </button>

        {/* Email inbox in a card container */}
        <div style={{
          background: 'var(--surface)',
          borderTop: '1px solid rgba(255,255,255,0.09)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          borderRadius: 8, overflow: 'hidden',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.60), 0 28px 80px rgba(0,0,0,0.80)',
        }}>
          <EmailInboxView className="p-4" />
        </div>
      </div>
    </div>
  );
}

export default function EmailPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{
          height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--surface-base)',
        }}>
          <div style={{
            width: 20, height: 20, border: '2px solid var(--border-sub)',
            borderTopColor: 'var(--mark)', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      }
    >
      <EmailPageContent />
    </React.Suspense>
  );
}
