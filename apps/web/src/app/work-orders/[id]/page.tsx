'use client';

/**
 * Work Order Detail Page - /work-orders/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~601 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-WO-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function WorkOrderDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="work_order"
      entityId={params.id as string}
      listRoute="/work-orders"
    />
  );
}
