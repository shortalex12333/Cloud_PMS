'use client';

/**
 * Certificate Detail Page - /certificates/[id]
 *
 * Phase 16.2: Unified Route Architecture
 * Replaced ~400 LOC with RouteShell wrapper (~20 LOC)
 *
 * @see REQUIREMENTS_TABLE.md - T1-CERT-02
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function CertificateDetailPage() {
  const params = useParams();

  return (
    <RouteShell
      entityType="certificate"
      entityId={params.id as string}
      listRoute="/certificates"
    />
  );
}
