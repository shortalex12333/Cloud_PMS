'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { FaultLensContent } from '@/components/lens/FaultLensContent';

export default function FaultDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="fault"
      entityId={params.id as string}
      content={FaultLensContent}
    />
  );
}
