'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { FaultContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><FaultContent /></div>;
}

export default function FaultDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="fault"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
