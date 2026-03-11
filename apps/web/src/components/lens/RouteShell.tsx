'use client';

/**
 * RouteShell — Phase 16.2 Unified Route Architecture
 *
 * Thin wrapper component that renders LensContent components within fragmented route context.
 * Eliminates ~4,682 lines of duplicated code across 12 route pages.
 *
 * Key responsibilities:
 * 1. Feature flag gating (redirect when disabled)
 * 2. Data fetching via react-query
 * 3. Route-specific navigation callbacks
 * 4. Loading/error/not-found states
 * 5. Delegation to existing LensContent components
 *
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';

// LensContent components — same imports as LensRenderer.tsx
import { WorkOrderLensContent } from './WorkOrderLensContent';
import { FaultLensContent } from './FaultLensContent';
import { EquipmentLensContent } from './EquipmentLensContent';
import { PartsLensContent } from './PartsLensContent';
import { ReceivingLensContent } from './ReceivingLensContent';
import { CertificateLensContent } from './CertificateLensContent';
import { HandoverLensContent } from './HandoverLensContent';
import { HandoverExportLensContent } from './HandoverExportLensContent';
import { HoursOfRestLensContent } from './HoursOfRestLensContent';
import { WarrantyLensContent } from './WarrantyLensContent';
import { ShoppingListLensContent } from './ShoppingListLensContent';
import { DocumentLensContent } from './DocumentLensContent';
import { WorklistLensContent } from './WorklistLensContent';

// =============================================================================
// Types
// =============================================================================

export type EntityType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'inventory'
  | 'receiving'
  | 'certificate'
  | 'handover'
  | 'handover_export'
  | 'hours_of_rest'
  | 'warranty'
  | 'shopping_list'
  | 'document'
  | 'worklist';

export interface RouteShellProps {
  /** Entity type (maps to LensContent component) */
  entityType: EntityType;
  /** Entity ID from route params */
  entityId: string;
  /** Route to redirect to when feature flag is disabled */
  legacyRedirect?: string;
  /** Route to navigate to for list view (back button) */
  listRoute: string;
  /** Optional: Override the page title */
  pageTitle?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Map entity type to API endpoint path */
const ENTITY_ENDPOINTS: Record<string, string> = {
  work_order: 'work_order',
  fault: 'fault',
  equipment: 'equipment',
  part: 'part',
  inventory: 'part', // inventory uses part endpoint
  receiving: 'receiving',
  certificate: 'certificate',
  handover: 'handover',
  handover_export: 'handover_export',
  hours_of_rest: 'hours_of_rest',
  warranty: 'warranty',
  shopping_list: 'shopping_list',
  document: 'document',
  worklist: 'worklist',
};

/** Map entity type to human-readable label */
const ENTITY_LABELS: Record<string, string> = {
  work_order: 'Work Order',
  fault: 'Fault',
  equipment: 'Equipment',
  part: 'Part',
  inventory: 'Inventory',
  receiving: 'Receiving',
  certificate: 'Certificate',
  handover: 'Handover',
  handover_export: 'Handover Export',
  hours_of_rest: 'Hours of Rest',
  warranty: 'Warranty',
  shopping_list: 'Shopping List',
  document: 'Document',
  worklist: 'Worklist',
};

/** Map entity type to fragmented route path */
const ENTITY_ROUTES: Record<string, string> = {
  work_order: 'work-orders',
  fault: 'faults',
  equipment: 'equipment',
  part: 'inventory',
  inventory: 'inventory',
  receiving: 'receiving',
  certificate: 'certificates',
  handover: 'handover',
  handover_export: 'handover-export',
  hours_of_rest: 'hours-of-rest',
  warranty: 'warranties',
  shopping_list: 'shopping-list',
  document: 'documents',
  worklist: 'worklist',
};

// =============================================================================
// Data Fetching
// =============================================================================

async function fetchEntity(
  type: string,
  id: string,
  token: string
): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const endpoint = ENTITY_ENDPOINTS[type] || type;

  const response = await fetch(`${baseUrl}/v1/entity/${endpoint}/${id}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${type}: ${response.status}`);
  }

  return response.json();
}

// =============================================================================
// State Components
// =============================================================================

function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading {label.toLowerCase()}...</p>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-red-400"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

function NotFoundState({ label, onBack }: { label: string; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-white/40"
        >
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">{label} Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">
        This {label.toLowerCase()} may have been deleted or you may not have access.
      </p>
      <button
        onClick={onBack}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Back to {label}s
      </button>
    </div>
  );
}

// =============================================================================
// LensRenderer with Route Callbacks
// =============================================================================

interface LensRendererWithRouteCallbacksProps {
  entityType: EntityType;
  entityId: string;
  entityData: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate: (type: string, id: string) => void;
  onRefresh: () => void;
}

/**
 * Internal component that maps entityType to LensContent with route-specific callbacks.
 * Same pattern as LensRenderer.tsx but with route navigation instead of panel navigation.
 */
function LensRendererWithRouteCallbacks({
  entityType,
  entityId,
  entityData,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: LensRendererWithRouteCallbacksProps) {
  // Common props passed to all LensContent components
  const commonProps = {
    id: entityId,
    data: entityData,
    onBack,
    onClose,
    onNavigate,
    onRefresh,
  };

  switch (entityType) {
    case 'work_order':
      return <WorkOrderLensContent {...commonProps} />;
    case 'fault':
      return <FaultLensContent {...commonProps} />;
    case 'equipment':
      return <EquipmentLensContent {...commonProps} />;
    case 'part':
    case 'inventory':
      return <PartsLensContent {...commonProps} entityType={entityType} />;
    case 'receiving':
      return <ReceivingLensContent {...commonProps} />;
    case 'certificate':
      return <CertificateLensContent {...commonProps} />;
    case 'handover':
      return <HandoverLensContent {...commonProps} />;
    case 'handover_export':
      return <HandoverExportLensContent {...commonProps} />;
    case 'hours_of_rest':
      return <HoursOfRestLensContent {...commonProps} />;
    case 'warranty':
      return <WarrantyLensContent {...commonProps} />;
    case 'shopping_list':
      return <ShoppingListLensContent {...commonProps} />;
    case 'document':
      return <DocumentLensContent {...commonProps} />;
    case 'worklist':
      return <WorklistLensContent {...commonProps} />;
    default:
      return (
        <div className="p-6 text-white/60">
          <p>Unknown entity type: {entityType}</p>
        </div>
      );
  }
}

// =============================================================================
// RouteShell Component
// =============================================================================

export function RouteShell({
  entityType,
  entityId,
  legacyRedirect,
  listRoute,
  pageTitle,
}: RouteShellProps) {
  const router = useRouter();
  const { session } = useAuth();
  const token = session?.access_token;

  // Feature flag guard — redirect if disabled
  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      const redirect = legacyRedirect || `/app?entity=${entityType}&id=${entityId}`;
      router.replace(redirect);
    }
  }, [router, entityType, entityId, legacyRedirect]);

  // Fetch entity data
  const {
    data: entityData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: [entityType, entityId],
    queryFn: () => fetchEntity(entityType, entityId, token || ''),
    enabled: !!entityId && !!token && isFragmentedRoutesEnabled(),
    staleTime: 30000,
    retry: 1,
  });

  // Navigation callbacks (route-specific)
  const handleBack = React.useCallback(() => {
    router.push(listRoute);
  }, [router, listRoute]);

  const handleClose = React.useCallback(() => {
    router.push(listRoute);
  }, [router, listRoute]);

  const handleNavigate = React.useCallback(
    (targetType: string, targetId: string) => {
      const route = ENTITY_ROUTES[targetType];
      if (route && isFragmentedRoutesEnabled()) {
        router.push(`/${route}/${targetId}`);
      } else {
        router.push(`/app?entity=${targetType}&id=${targetId}`);
      }
    },
    [router]
  );

  const handleRefresh = React.useCallback(() => {
    refetch();
  }, [refetch]);

  // Early return for feature flag disabled
  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  // Derive label and title
  const label = ENTITY_LABELS[entityType] || entityType;
  const title =
    pageTitle ||
    (entityData?.title as string) ||
    (entityData?.name as string) ||
    label;

  // Render content based on state
  let content: React.ReactNode;

  if (isLoading) {
    content = <LoadingState label={label} />;
  } else if (error) {
    const errorMessage = error instanceof Error ? error.message : 'An error occurred';
    const is404 = errorMessage.includes('404');

    content = is404 ? (
      <NotFoundState label={label} onBack={handleBack} />
    ) : (
      <ErrorState message={errorMessage} onRetry={handleRefresh} />
    );
  } else if (!entityData) {
    content = <NotFoundState label={label} onBack={handleBack} />;
  } else {
    content = (
      <LensRendererWithRouteCallbacks
        entityType={entityType}
        entityId={entityId}
        entityData={entityData}
        onBack={handleBack}
        onClose={handleClose}
        onNavigate={handleNavigate}
        onRefresh={handleRefresh}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={title}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            aria-label="Back"
            data-testid="back-button"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-white/60"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <div>
            <p className="text-xs text-white/40 uppercase tracking-wider">{label}</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">{title}</h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

export default RouteShell;
