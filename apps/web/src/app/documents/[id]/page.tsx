'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { DocumentContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><DocumentContent /></div>;
}

export default function DocumentDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="document"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
