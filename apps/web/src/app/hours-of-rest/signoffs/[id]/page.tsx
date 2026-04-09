'use client';

/**
 * Sign-off Detail Page — /hours-of-rest/signoffs/[id]
 *
 * Direct-link route for a single monthly sign-off. This is used when someone
 * navigates directly (e.g., from a bookmarked URL, ledger event click, or
 * search result). It renders the same HoRSignoffContent lens as the list page
 * overlay, but as a full-page view via EntityLensPage.
 *
 * EntityLensPage handles:
 *   - Fetching entity data from GET /v1/entity/hours_of_rest_signoff/{id}
 *   - Glass header with back button, related panel, theme toggle
 *   - Signature interception (ActionPopup for requires_signature actions)
 *   - Loading/error/not-found states
 *
 * If this page shows "Not Found", check that the generic entity resolver in the
 * backend knows how to route entityType='hours_of_rest_signoff' to the correct
 * handler (get_monthly_signoff in hours_of_rest_handlers.py).
 */

import * as React from 'react';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { HoRSignoffContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><HoRSignoffContent /></div>;
}

export default function SignoffDetailPage() {
  const params = useParams();
  const id = params.id as string;

  return (
    <React.Suspense
      fallback={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--surface-base)' }}>
          <div style={{ width: 32, height: 32, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      }
    >
      <EntityLensPage
        entityType="hours_of_rest_signoff"
        entityId={id}
        content={LensContent}
        pageTitle="Monthly Sign-Off"
      />
    </React.Suspense>
  );
}
