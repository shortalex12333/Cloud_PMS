'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HoursOfRestLensContent } from '@/components/lens/HoursOfRestLensContent';

export default function HoursOfRestDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="hours_of_rest"
      entityId={params.id as string}
      content={HoursOfRestLensContent}
    />
  );
}
