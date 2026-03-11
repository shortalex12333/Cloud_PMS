'use client';

/**
 * Warranty Detail Page - /warranties/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~357 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-WAR-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function WarrantyDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="warranty"
      entityId={params.id as string}
      listRoute="/warranties"
    />
  );
}
