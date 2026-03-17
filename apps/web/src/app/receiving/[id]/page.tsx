'use client';

/**
 * Receiving Detail Page - /receiving/[id]
 *
 * Tier 1 fragmented route for viewing a single receiving record.
 * Delegates all loading, error handling, and action management to EntityLensPage.
 *
 * @see REQUIREMENTS_TABLE.md - T1-RCV-02
 */

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { ReceivingLensContent } from '@/components/lens/ReceivingLensContent';

export default function ReceivingDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="receiving"
      entityId={params.id as string}
      content={ReceivingLensContent}
    />
  );
}
