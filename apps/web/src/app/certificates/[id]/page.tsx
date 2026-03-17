'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { CertificateLensContent } from '@/components/lens/CertificateLensContent';

export default function CertificateDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="certificate"
      entityId={params.id as string}
      content={CertificateLensContent}
    />
  );
}
