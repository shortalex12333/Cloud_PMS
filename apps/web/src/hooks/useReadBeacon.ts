'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export function useReadBeacon(
  entityType: string,
  entityId: string | undefined,
  entityName?: string,
  metadata?: Record<string, unknown>
) {
  const { session } = useAuth();
  const token = session?.access_token;

  React.useEffect(() => {
    if (!entityId || !token) return;
    fetch(`${API_BASE}/v1/ledger/read-event`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        entity_name: entityName ?? '',
        metadata: metadata ?? {},
      }),
    }).catch(() => { /* intentionally silent */ });
  }, [entityType, entityId, entityName, token]);
}
