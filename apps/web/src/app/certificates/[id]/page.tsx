'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { CertificateContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><CertificateContent /></div>;
}

export default function CertificateDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="certificate"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
