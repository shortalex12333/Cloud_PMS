'use client';

/**
 * Shopping List Detail Page - /shopping-list/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~389 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-SL-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function ShoppingListDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="shopping_list"
      entityId={params.id as string}
      listRoute="/shopping-list"
    />
  );
}
