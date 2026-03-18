'use client';

import { use } from 'react';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HandoverContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><HandoverContent /></div>;
}

export default function HandoverExportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <EntityLensPage
      entityType="handover_export"
      entityId={id}
      content={LensContent}
    />
  );
}
