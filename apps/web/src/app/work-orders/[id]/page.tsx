'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><WorkOrderContent /></div>;
}

export default function WorkOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="work_order"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
