'use client';

/**
 * Purchase Order Detail Page - /purchasing/[id]
 *
 * Fragmented route for viewing a single purchase order.
 * All data-fetching, action dispatch, and error handling are handled
 * by EntityLensPage + useEntityLens.
 */

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { PurchaseOrderContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><PurchaseOrderContent /></div>;
}

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="purchase_order"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
