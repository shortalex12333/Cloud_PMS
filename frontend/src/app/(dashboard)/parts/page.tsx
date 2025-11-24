// @ts-nocheck - Phase 3: Requires shadcn/ui components
/**
 * PartsListPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side PartsList component.
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import PartsList from './PartsList';

// Force dynamic rendering (required for useSearchParams)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function PartsLoading() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function PartsPage() {
  return (
    <Suspense fallback={<PartsLoading />}>
      <PartsList />
    </Suspense>
  );
}
