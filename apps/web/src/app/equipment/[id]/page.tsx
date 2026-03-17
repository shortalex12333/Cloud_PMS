'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { EquipmentLensContent } from '@/components/lens/EquipmentLensContent';

export default function EquipmentDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="equipment"
      entityId={params.id as string}
      content={EquipmentLensContent}
    />
  );
}
