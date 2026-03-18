'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HoursOfRestContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><HoursOfRestContent /></div>;
}

export default function HoursOfRestDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="hours_of_rest"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
