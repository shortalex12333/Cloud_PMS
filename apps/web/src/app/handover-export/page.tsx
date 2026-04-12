'use client';

/**
 * Handover — Queue + Draft tabs
 *
 * Tab 1 — Queue: auto-detected items ready to add to next handover.
 *   Calls GET /v1/handover/queue via HandoverQueueView.
 *   Shows open faults, overdue WOs, low stock parts, pending orders.
 *
 * Tab 2 — Draft: items already added (handover_items, not yet exported).
 *   Reuses HandoverDraftPanel with variant='page' for in-page rendering.
 *   Includes Export button that navigates to /handover-export/[id] on success.
 *
 * The /handover-export/[id] lens for completed exports is untouched.
 */

import * as React from 'react';
import { HandoverQueueView } from '@/components/handover/HandoverQueueView';
import { HandoverDraftPanel } from '@/components/handover/HandoverDraftPanel';

type Tab = 'queue' | 'draft';

export default function HandoverExportPage() {
  const [activeTab, setActiveTab] = React.useState<Tab>('queue');

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
      background: 'var(--surface-base)',
    }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        padding: '10px 16px 0',
        borderBottom: '1px solid var(--border-sub)',
        flexShrink: 0,
        background: 'var(--surface)',
      }}>
        {(['queue', 'draft'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? 'var(--txt)' : 'var(--txt3)',
              background: 'none',
              border: 'none',
              borderBottom: `2px solid ${activeTab === tab ? 'var(--mark)' : 'transparent'}`,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              marginBottom: -1,
              textTransform: 'capitalize',
              transition: 'color 80ms, border-color 80ms',
              letterSpacing: '0.01em',
            }}
          >
            {tab === 'queue' ? 'Queue' : 'Draft Items'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* Queue tab */}
        <div style={{
          position: 'absolute', inset: 0,
          overflowY: 'auto',
          visibility: activeTab === 'queue' ? 'visible' : 'hidden',
          pointerEvents: activeTab === 'queue' ? 'auto' : 'none',
        }}>
          <HandoverQueueView />
        </div>

        {/* Draft tab */}
        <div style={{
          position: 'absolute', inset: 0,
          overflow: 'hidden',
          visibility: activeTab === 'draft' ? 'visible' : 'hidden',
          pointerEvents: activeTab === 'draft' ? 'auto' : 'none',
        }}>
          <HandoverDraftPanel
            isOpen={activeTab === 'draft'}
            onClose={() => setActiveTab('queue')}
            variant="page"
          />
        </div>
      </div>
    </div>
  );
}
