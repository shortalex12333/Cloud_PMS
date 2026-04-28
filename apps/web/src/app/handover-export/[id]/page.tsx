'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HandoverContent } from '@/components/lens/entity';
import lensStyles from '@/components/lens/lens.module.css';

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
