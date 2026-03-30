'use client';

/**
 * Handover Export — List view placeholder
 *
 * Minimal placeholder until the full handover list view is built.
 * The handover detail page at /handover-export/[id] already exists.
 */

import * as React from 'react';
import { FileSignature } from 'lucide-react';

export default function HandoverExportPage() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        gap: 8,
        color: 'var(--txt-ghost)',
      }}
    >
      <FileSignature style={{ width: 28, height: 28, marginBottom: 4 }} />
      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt3)' }}>
        Handover Records
      </span>
      <span style={{ fontSize: 11, color: 'var(--txt-ghost)' }}>
        Select a handover from the search results to view details
      </span>
    </div>
  );
}
