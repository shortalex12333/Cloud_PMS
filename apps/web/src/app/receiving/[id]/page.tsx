'use client';

/**
 * Receiving Detail Page - /receiving/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~383 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-RCV-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function ReceivingDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="receiving"
      entityId={params.id as string}
      listRoute="/receiving"
    />
  );
}
