'use client';

/**
 * Document Detail Page - /documents/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~450 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-DOC-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function DocumentDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="document"
      entityId={params.id as string}
      listRoute="/documents"
    />
  );
}
