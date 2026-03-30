'use client';

/**
 * Warranties List Page - /warranties
 *
 * No warranty table exists in Supabase yet. This page renders a
 * factual empty state until the table is created.
 */

import * as React from 'react';
import { Shield } from 'lucide-react';

export default function WarrantiesPage() {
  return (
    <div
      data-testid="empty-state"
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
      <Shield style={{ width: 28, height: 28, marginBottom: 4 }} />
      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt3)' }}>
        No warranty records
      </span>
    </div>
  );
}
