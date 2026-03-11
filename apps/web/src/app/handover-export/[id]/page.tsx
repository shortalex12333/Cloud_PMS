'use client';

/**
 * Handover Export Detail Page - /handover-export/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~196 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function HandoverExportDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="handover_export"
      entityId={params.id as string}
      listRoute="/handover"
    />
  );
}
