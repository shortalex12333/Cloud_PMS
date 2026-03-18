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

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WarrantyContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><WarrantyContent /></div>;
}

export default function WarrantyDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="warranty"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
