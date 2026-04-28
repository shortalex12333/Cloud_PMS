'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { PartsInventoryContent } from '@/components/lens/entity';
import lensStyles from '@/components/lens/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><PartsInventoryContent /></div>;
}

export default function InventoryDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="part"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
