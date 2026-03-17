'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { DocumentLensContent } from '@/components/lens/DocumentLensContent';

export default function DocumentDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="document"
      entityId={params.id as string}
      content={DocumentLensContent}
    />
  );
}
