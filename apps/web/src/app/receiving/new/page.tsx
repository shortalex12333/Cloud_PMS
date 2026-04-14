'use client';

/**
 * /receiving/new — Dedicated page for logging a new receiving.
 * Replaces the modal-behind-UI ReceivingDocumentUpload pattern.
 * Full-page stepped flow: Select Type → Upload → Review → Save.
 */

import React, { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { ReceivingDocumentUpload } from '@/components/receiving/ReceivingDocumentUpload';
import { useAuth } from '@/hooks/useAuth';
import { getEntityRoute } from '@/lib/entityRoutes';
import { toast } from 'sonner';

export default function NewReceivingPage() {
  const router = useRouter();
  const { user } = useAuth();

  const handleComplete = useCallback((receivingId: string, documentId: string, extractedData: any) => {
    toast.success('Receiving logged', {
      description: extractedData?.supplier_name || 'Document uploaded successfully',
    });
    router.push(getEntityRoute('receiving', receivingId));
  }, [router]);

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: 'var(--surface-base)' }}>
      {/* Topbar */}
      <div style={{
        height: 44, display: 'flex', alignItems: 'center', padding: '0 16px',
        borderBottom: '1px solid var(--border-sub)', background: 'var(--surface)', gap: 12,
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--mark)' }}>Celeste</span>
        <span style={{ fontSize: 12, color: 'var(--txt3)', borderLeft: '1px solid var(--border-sub)', paddingLeft: 12 }}>
          {user?.yachtName || 'Vessel'}
        </span>
        <div style={{ flex: 1 }} />
      </div>

      {/* Content */}
      <div style={{ maxWidth: 560, margin: '0 auto', padding: '32px 20px 64px' }}>
        {/* Back nav */}
        <button
          onClick={() => router.back()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 12, color: 'var(--txt3)', cursor: 'pointer',
            marginBottom: 24, background: 'none', border: 'none',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <ChevronLeft size={14} /> Back to search
        </button>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--txt)', letterSpacing: '-0.01em' }}>Log Receiving</h1>
          <p style={{ fontSize: 13, color: 'var(--txt3)', marginTop: 4, lineHeight: 1.5 }}>
            Upload or photograph a delivery document. We&apos;ll extract vendor, items, and quantities automatically.
          </p>
        </div>

        {/* Receiving Upload Component (existing, reused) */}
        <div style={{
          background: 'var(--surface)',
          borderTop: '1px solid rgba(255,255,255,0.09)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          borderRadius: 8, overflow: 'hidden', padding: 20,
        }}>
          <ReceivingDocumentUpload onComplete={handleComplete} />
        </div>
      </div>
    </div>
  );
}
