'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderLensContent } from '@/components/lens/WorkOrderLensContent';

export default function WorkOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="work_order"
      entityId={params.id as string}
      content={WorkOrderLensContent}
    />
  );
}
