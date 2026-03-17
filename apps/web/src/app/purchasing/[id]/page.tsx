'use client';

/**
 * Purchase Order Detail Page - /purchasing/[id]
 *
 * Fragmented route for viewing a single purchase order.
 * All data-fetching, action dispatch, and error handling are handled
 * by EntityLensPage + useEntityLens.
 */

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { PurchaseOrderLensContent } from '@/components/lens/PurchaseOrderLensContent';

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="purchase_order"
      entityId={params.id as string}
      content={PurchaseOrderLensContent}
    />
  );
}
