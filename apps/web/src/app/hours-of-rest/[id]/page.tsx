'use client';

/**
 * Hours of Rest Detail Page - /hours-of-rest/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~384 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-HOR-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function HoursOfRestDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="hours_of_rest"
      entityId={params.id as string}
      listRoute="/hours-of-rest"
    />
  );
}
