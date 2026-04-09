'use client';

/**
 * Receiving Detail Page - /receiving/[id]
 *
 * Tier 1 fragmented route for viewing a single receiving record.
 * Delegates all loading, error handling, and action management to EntityLensPage.
 *
 * @see REQUIREMENTS_TABLE.md - T1-RCV-02
 */

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { ReceivingContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><ReceivingContent /></div>;
}

export default function ReceivingDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="receiving"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
