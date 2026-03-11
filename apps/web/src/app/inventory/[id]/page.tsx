'use client';

/**
 * Inventory Detail Page - /inventory/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~245 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-INV-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function InventoryDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="inventory"
      entityId={params.id as string}
      listRoute="/inventory"
    />
  );
}
