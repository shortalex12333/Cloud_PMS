'use client';

/**
 * Warranty Detail Page - /warranties/[id]
 *
 * Tier 1 fragmented route for viewing a single warranty.
 * Delegates all data fetching, loading states, and action orchestration
 * to EntityLensPage — this file is intentionally thin.
 *
 * @see REQUIREMENTS_TABLE.md - T1-WAR-02
 */

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WarrantyLensContent } from '@/components/lens/WarrantyLensContent';

export default function WarrantyDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="warranty"
      entityId={params.id as string}
      content={WarrantyLensContent}
    />
  );
}
