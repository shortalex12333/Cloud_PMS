'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { EquipmentContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><EquipmentContent /></div>;
}

export default function EquipmentDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="equipment"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
