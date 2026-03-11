'use client';

/**
 * Equipment Detail Page - /equipment/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~426 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-EQ-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function EquipmentDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="equipment"
      entityId={params.id as string}
      listRoute="/equipment"
    />
  );
}
