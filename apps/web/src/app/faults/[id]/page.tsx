'use client';

/**
 * Fault Detail Page - /faults/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~405 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-F-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function FaultDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="fault"
      entityId={params.id as string}
      listRoute="/faults"
    />
  );
}
