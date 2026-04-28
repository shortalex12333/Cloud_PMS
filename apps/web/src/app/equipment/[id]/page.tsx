'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { EquipmentContent } from '@/components/lens/entity';
import lensStyles from '@/components/lens/lens.module.css';

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
