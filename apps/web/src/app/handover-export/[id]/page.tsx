'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { HandoverContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><HandoverContent /></div>;
}

export default function HandoverExportPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="handover_export"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
