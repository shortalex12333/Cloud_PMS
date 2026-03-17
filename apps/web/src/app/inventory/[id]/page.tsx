'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { PartsLensContent } from '@/components/lens/PartsLensContent';

export default function InventoryDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="part"
      entityId={params.id as string}
      content={PartsLensContent}
    />
  );
}
