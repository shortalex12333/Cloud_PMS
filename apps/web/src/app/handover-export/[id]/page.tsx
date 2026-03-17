'use client';

import { use } from 'react';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HandoverExportLensContent } from '@/components/lens/HandoverExportLensContent';

export default function HandoverExportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <EntityLensPage
      entityType="handover_export"
      entityId={id}
      content={HandoverExportLensContent}
    />
  );
}
