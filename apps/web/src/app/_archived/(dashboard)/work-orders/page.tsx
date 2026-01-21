// @ts-nocheck - Phase 3: Requires shadcn/ui components
/**
 * WorkOrdersListPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side WorkOrdersList component.
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import WorkOrdersList from './WorkOrdersList';

// Force dynamic rendering (required for useSearchParams)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function WorkOrdersLoading() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function WorkOrdersPage() {
  return (
    <Suspense fallback={<WorkOrdersLoading />}>
      <WorkOrdersList />
    </Suspense>
  );
}
