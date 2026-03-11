# Unified Route Architecture Specification

**Version:** 1.0
**Date:** 2026-03-03
**Status:** PROPOSED

---

## Executive Summary

### Problem Statement

The current codebase contains **12 fragmented route pages** totaling **~4,682 lines of duplicated code**. These route pages (`/faults/[id]`, `/work-orders/[id]`, etc.) replicate logic, UI patterns, and permission checks that already exist in the fully-functional `*LensContent` components.

Additionally, GAP-021 from the recent button hardening audit revealed that these fragmented routes had **26 unwired buttons** that required manual intervention to fix. The fundamental issue: two parallel implementations that must be kept in sync.

### Solution

Introduce a **RouteShell** wrapper component that renders existing `*LensContent` components in the context of fragmented routes. This eliminates code duplication while preserving:
- Feature flag gating (redirect when disabled)
- Route layout structure
- Navigation patterns specific to fragmented routes

### Impact Summary

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Route page LOC | ~4,682 | ~240 | **-95%** |
| Unwired button risk | High (26 found) | **Zero** | -100% |
| RBAC sources of truth | 3 (lens, route, hook) | **1** (lens_matrix.json) | -67% |
| Maintenance burden | 12 files to update | **1** component | -92% |

---

## 1. Current State (Mediocre)

### 1.1 Architecture Diagram

```
                      CURRENT STATE

     ┌─────────────────────────────────────────────────────┐
     │                  DUPLICATION                        │
     └─────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │ SPA Lens  │    │ Route     │    │ Permission│
    │ Components│    │ Pages     │    │ Hooks     │
    └───────────┘    └───────────┘    └───────────┘
          │                │                │
          │ 13 files       │ 12 files       │ 12 files
          │ ~6,500 LOC     │ ~4,682 LOC     │ ~4,200 LOC
          │                │                │
          │                │                │
          ▼                ▼                ▼
    ┌─────────────────────────────────────────────────────┐
    │  REDUNDANT IMPLEMENTATIONS                          │
    │  - Button logic duplicated                          │
    │  - Permission checks duplicated                     │
    │  - State management duplicated                      │
    │  - Modals duplicated                                │
    └─────────────────────────────────────────────────────┘
```

### 1.2 Fragmented Route Files (Line Counts)

| Route | File | LOC | Primary Issues |
|-------|------|-----|----------------|
| Faults | `/app/faults/[id]/page.tsx` | 405 | Duplicates FaultLensContent buttons |
| Work Orders | `/app/work-orders/[id]/page.tsx` | 601 | Duplicates WorkOrderLensContent modals |
| Equipment | `/app/equipment/[id]/page.tsx` | 426 | Duplicates EquipmentLensContent logic |
| Certificates | `/app/certificates/[id]/page.tsx` | 427 | Duplicates CertificateLensContent |
| Warranties | `/app/warranties/[id]/page.tsx` | 357 | Duplicates WarrantyLensContent |
| Hours of Rest | `/app/hours-of-rest/[id]/page.tsx` | 384 | Duplicates HoursOfRestLensContent |
| Receiving | `/app/receiving/[id]/page.tsx` | 383 | Duplicates ReceivingLensContent |
| Shopping List | `/app/shopping-list/[id]/page.tsx` | 389 | Duplicates ShoppingListLensContent |
| Inventory | `/app/inventory/[id]/page.tsx` | 245 | Duplicates PartsLensContent |
| Documents | `/app/documents/[id]/page.tsx` | 449 | Duplicates DocumentLensContent |
| Purchasing | `/app/purchasing/[id]/page.tsx` | 420 | Duplicates ShoppingListLensContent |
| Handover Export | `/app/handover-export/[id]/page.tsx` | 196 | Duplicates HandoverExportLensContent |
| **TOTAL** | — | **4,682** | — |

### 1.3 The 26 Unwired Buttons (GAP-021)

From the button hardening audit (2026-03-02), these buttons existed in route pages but had no functionality:

**Fault Routes (6):**
- `acknowledge-fault-btn` - onClick was empty
- `close-fault-btn` - onClick was empty
- `reopen-fault-btn` - onClick was empty
- `false-alarm-btn` - onClick was empty
- `add-note-btn` - onClick was empty
- `create-wo-button` - onClick was empty

**Work Order Routes (5):**
- `start-work-btn` - onClick was empty
- `mark-complete-btn` - onClick was empty
- `edit-wo-btn` - onClick was empty
- `add-hours-btn` - onClick was empty
- `add-note-btn` - onClick was empty

**Equipment Routes (3):**
- `update-status-btn` - onClick was empty
- `log-running-hours-btn` - onClick was empty
- `add-note-btn` - onClick was empty

**Certificate Routes (3):**
- `supersede-btn` - onClick was empty
- `delete-btn` - onClick was empty
- `update-btn` - onClick was empty

**Warranty Routes (3):**
- `file-claim-btn` - onClick was empty
- `approve-claim-btn` - onClick was empty
- `extend-btn` - onClick was empty

**Document Routes (2):**
- `copy-link-btn` - onClick was empty
- `delete-btn` - onClick was empty

**Other Routes (4):**
- Shopping list: `mark-ordered-btn`, `approve-btn`
- Receiving: `accept-btn`, `reject-btn`

---

## 2. Target State (Elegant)

### 2.1 Architecture Diagram

```
                      TARGET STATE

     ┌─────────────────────────────────────────────────────┐
     │            SINGLE SOURCE OF TRUTH                   │
     └─────────────────────────────────────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────────────┐
    │         LAYER 1: LensContent Components             │
    │                                                     │
    │  FaultLensContent.tsx         (431 LOC)             │
    │  WorkOrderLensContent.tsx     (489 LOC)             │
    │  EquipmentLensContent.tsx     (~400 LOC)            │
    │  CertificateLensContent.tsx   (~380 LOC)            │
    │  WarrantyLensContent.tsx      (~350 LOC)            │
    │  ... (13 total lens components)                     │
    │                                                     │
    │  Single implementation of:                          │
    │  - Action buttons                                   │
    │  - Permission gates                                 │
    │  - Modal state management                           │
    │  - Form validation                                  │
    └─────────────────────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │  LAYER 2a: SPA Lens   │    │  LAYER 2b: Route      │
    │  (ContextPanel)       │    │  (RouteShell)         │
    └───────────────────────┘    └───────────────────────┘
          │                                 │
          │ LensRenderer.tsx                │ RouteShell.tsx
          │ (~154 LOC)                      │ (~100 LOC)
          │                                 │
          │ Renders lens in panel           │ Renders lens at route
          │ Navigation via stack            │ Navigation via router
          │ Close returns to search         │ Close returns to list
          │                                 │
          └────────────────┬────────────────┘
                           ▼
    ┌─────────────────────────────────────────────────────┐
    │         LAYER 3: Permission System                  │
    │                                                     │
    │  lens_matrix.json (single source of truth)          │
    │  └─▶ usePermissions hook (reads matrix)             │
    │      └─▶ can(actionId) function                     │
    │                                                     │
    │  All permission logic derived from matrix:          │
    │  - role_restricted arrays                           │
    │  - requires_signature flags                         │
    │  - requires_confirmation flags                      │
    └─────────────────────────────────────────────────────┘
```

### 2.2 Key Principles

1. **LensContent is the source of truth** for all UI logic, buttons, and state
2. **RouteShell is a thin wrapper** that provides route-specific context
3. **usePermissions reads from lens_matrix.json** for all RBAC decisions
4. **Zero duplication** between SPA and fragmented route rendering

---

## 3. Component Specifications

### 3.1 RouteShell Component

**File:** `/apps/web/src/components/lens/RouteShell.tsx`

#### TypeScript Interface

```typescript
/**
 * RouteShell - Renders LensContent components within fragmented route context.
 *
 * This component bridges the gap between:
 * - Route-based navigation (Next.js App Router)
 * - LensContent components (designed for ContextPanel)
 *
 * Key responsibilities:
 * 1. Feature flag gating (redirect when disabled)
 * 2. Data fetching via react-query
 * 3. Route-specific navigation callbacks
 * 4. RouteLayout wrapper
 */

export interface RouteShellProps {
  /** Entity type (maps to LensRenderer case) */
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
```

#### Behavior Specification

| Behavior | Description |
|----------|-------------|
| Feature Flag Check | If `isFragmentedRoutesEnabled()` returns false, redirect to `legacyRedirect` or `/app?entity={type}&id={id}` |
| Data Fetching | Use `useQuery` to fetch entity from `/v1/entity/{type}/{id}` |
| Navigation: Back | Navigate to `listRoute` (e.g., `/faults`) |
| Navigation: Close | Navigate to `listRoute` |
| Navigation: Cross-entity | Use router.push to fragmented route (e.g., `/equipment/{id}`) |
| Loading State | Render spinner with "Loading {entityType}..." |
| Error State | Render error message with retry button |
| Not Found State | Render 404 message with back-to-list button |

#### Implementation

```typescript
'use client';

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { LensRenderer } from './LensRenderer';

export interface RouteShellProps {
  entityType: string;
  entityId: string;
  legacyRedirect?: string;
  listRoute: string;
  pageTitle?: string;
}

// Map entity type to API endpoint
const ENTITY_ENDPOINTS: Record<string, string> = {
  work_order: 'work_order',
  fault: 'fault',
  equipment: 'equipment',
  part: 'part',
  inventory: 'part',
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

// Map entity type to human-readable label
const ENTITY_LABELS: Record<string, string> = {
  work_order: 'Work Order',
  fault: 'Fault',
  equipment: 'Equipment',
  part: 'Part',
  inventory: 'Part',
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

// Map entity type to fragmented route path
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

async function fetchEntity(
  type: string,
  id: string,
  token: string
): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const endpoint = ENTITY_ENDPOINTS[type] || type;
  const response = await fetch(`${baseUrl}/v1/entity/${endpoint}/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${type}: ${response.status}`);
  }

  return response.json();
}

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

  // Feature flag guard
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

  // Early return for feature flag
  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  // Derive title
  const label = ENTITY_LABELS[entityType] || entityType;
  const title =
    pageTitle ||
    (entityData?.title as string) ||
    (entityData?.name as string) ||
    label;

  // Render content based on state
  let content: React.ReactNode;

  if (isLoading) {
    content = (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          <p className="text-sm text-white/60">Loading {label.toLowerCase()}...</p>
        </div>
      </div>
    );
  } else if (error) {
    const errorMessage = error instanceof Error ? error.message : 'An error occurred';
    const is404 = errorMessage.includes('404');

    content = is404 ? (
      <div className="flex flex-col items-center justify-center h-full text-center px-6">
        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
            <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">{label} Not Found</h3>
        <p className="text-sm text-white/60 max-w-sm mb-4">
          This {label.toLowerCase()} may have been deleted or you may not have access.
        </p>
        <button
          onClick={handleBack}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
        >
          Back to {label}s
        </button>
      </div>
    ) : (
      <div className="flex flex-col items-center justify-center h-full text-center px-6">
        <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-400">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
        <p className="text-sm text-white/60 max-w-sm mb-4">{errorMessage}</p>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  } else if (!entityData) {
    content = null;
  } else {
    // Render the LensContent via LensRenderer
    // Override navigation callbacks for route context
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
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60">
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

/**
 * LensRendererWithRouteCallbacks - Wraps LensRenderer to inject route-specific callbacks
 *
 * This is necessary because LensRenderer's default callbacks use NavigationContext,
 * but route pages need to use Next.js router directly.
 */
function LensRendererWithRouteCallbacks({
  entityType,
  entityId,
  entityData,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: {
  entityType: string;
  entityId: string;
  entityData: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate: (type: string, id: string) => void;
  onRefresh: () => void;
}) {
  // Import lens components dynamically based on entityType
  // This allows the same routing logic as LensRenderer but with overridden callbacks

  const commonProps = {
    id: entityId,
    data: entityData,
    onBack,
    onClose,
    onNavigate,
    onRefresh,
  };

  // Reuse the same switch logic as LensRenderer
  // (This could be refactored to share the mapping)
  switch (entityType) {
    case 'work_order':
      // @ts-expect-error - Dynamic import handled at build time
      return <WorkOrderLensContent {...commonProps} />;
    case 'fault':
      // @ts-expect-error - Dynamic import handled at build time
      return <FaultLensContent {...commonProps} />;
    // ... etc for all entity types
    default:
      return (
        <div className="p-6 text-celeste-text-muted">
          <p>Unknown entity type: {entityType}</p>
        </div>
      );
  }
}

// Import all lens components at module level
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
```

### 3.2 Fragmented Route Pages (After Refactor)

#### Before: `/app/faults/[id]/page.tsx` (405 lines)

```typescript
// 400+ lines of duplicated logic:
// - FeatureFlagGuard
// - fetchFaultDetail
// - getSeverityColor / getStatusColor
// - LoadingState / ErrorState / NotFoundState
// - FaultContent with all buttons and handlers
// - useFaultActions / useFaultPermissions
// - Modal state management
// - etc.
```

#### After: `/app/faults/[id]/page.tsx` (20 lines)

```typescript
'use client';

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function FaultDetailPage() {
  const params = useParams();
  const faultId = params.id as string;

  return (
    <RouteShell
      entityType="fault"
      entityId={faultId}
      listRoute="/faults"
    />
  );
}
```

#### Template for All Routes

```typescript
'use client';

import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function ${EntityType}DetailPage() {
  const params = useParams();
  const entityId = params.id as string;

  return (
    <RouteShell
      entityType="${entityType}"
      entityId={entityId}
      listRoute="/${listRoute}"
    />
  );
}
```

### 3.3 usePermissions Hook

**File:** `/apps/web/src/hooks/usePermissions.ts`

#### Current State: Hardcoded Role Arrays

Each `use*Permissions` hook (12 total) contains hardcoded role arrays:

```typescript
// useFaultPermissions.ts (current)
const FAULT_RESTRICTED_ROLES = ['chief_engineer', 'captain', 'manager'];

export function useFaultPermissions(): FaultPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canAcknowledge: FAULT_RESTRICTED_ROLES.includes(role),
    canClose: FAULT_RESTRICTED_ROLES.includes(role),
    // ... 10 more hardcoded checks
  };
}
```

#### Target State: Single Source of Truth

```typescript
'use client';

/**
 * usePermissions - Unified permission hook reading from lens_matrix.json
 *
 * Single source of truth for all RBAC decisions.
 * Reads role_restricted arrays from the lens matrix and returns
 * a `can(actionId)` function for permission checks.
 *
 * @param lensType - The lens type (e.g., 'fault', 'work_order')
 */

import { useMemo } from 'react';
import { useAuth } from '@/hooks/useAuth';
import lensMatrix from '@/../.planning/agents/lens-matrix/lens_matrix.json';

// All crew roles (can perform any non-restricted action)
const ALL_CREW_ROLES = [
  'crew', 'deckhand', 'steward', 'chef', 'eto', 'engineer',
  'chief_engineer', 'chief_officer', 'captain', 'manager'
];

export interface PermissionResult {
  /** Check if user can perform a specific action */
  can: (actionId: string) => boolean;

  /** Get all actions user can perform */
  allowedActions: string[];

  /** Check if action requires signature */
  requiresSignature: (actionId: string) => boolean;

  /** Check if action requires confirmation */
  requiresConfirmation: (actionId: string) => boolean;
}

export function usePermissions(lensType: string): PermissionResult {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return useMemo(() => {
    // Get lens configuration from matrix
    const lens = (lensMatrix.lenses as Record<string, unknown>)[lensType] as {
      mutate_actions: Record<string, {
        action_id: string;
        role_restricted: string[];
        requires_signature?: boolean;
        requires_confirmation?: boolean;
      }>;
    } | undefined;

    if (!lens?.mutate_actions) {
      return {
        can: () => false,
        allowedActions: [],
        requiresSignature: () => false,
        requiresConfirmation: () => false,
      };
    }

    const actions = lens.mutate_actions;

    // Check if user can perform action
    const can = (actionId: string): boolean => {
      const action = actions[actionId];
      if (!action) return false;

      // Empty role_restricted means all crew can perform
      if (!action.role_restricted || action.role_restricted.length === 0) {
        return ALL_CREW_ROLES.includes(role);
      }

      // Otherwise, check if user role is in restricted list
      return action.role_restricted.includes(role);
    };

    // Get all actions user can perform
    const allowedActions = Object.keys(actions).filter(can);

    // Check if action requires signature
    const requiresSignature = (actionId: string): boolean => {
      return actions[actionId]?.requires_signature ?? false;
    };

    // Check if action requires confirmation
    const requiresConfirmation = (actionId: string): boolean => {
      return actions[actionId]?.requires_confirmation ?? false;
    };

    return {
      can,
      allowedActions,
      requiresSignature,
      requiresConfirmation,
    };
  }, [lensType, role]);
}

/**
 * Legacy compatibility wrapper - useFaultPermissions
 *
 * Maps to the unified usePermissions hook.
 * Can be deprecated once all consumers migrate.
 */
export function useFaultPermissions() {
  const perms = usePermissions('fault');

  return {
    canReport: perms.can('report_fault'),
    canAcknowledge: perms.can('acknowledge_fault'),
    canClose: perms.can('close_fault'),
    canUpdate: perms.can('update_fault'),
    canReopen: perms.can('reopen_fault'),
    canCreateWorkOrder: perms.can('create_work_order_from_fault'),
    canMarkFalseAlarm: perms.can('mark_fault_false_alarm'),
    canDiagnose: perms.can('diagnose_fault'),
    canAddNote: perms.can('add_fault_note'),
    canAddPhoto: perms.can('add_fault_photo'),
    canShowManual: ALL_CREW_ROLES.includes(useAuth().user?.role ?? ''),
  };
}

// Similar wrappers for other entity types...
```

---

## 4. File Structure

### Before

```
apps/web/src/
├── app/
│   ├── faults/[id]/page.tsx          # 405 LOC (duplicated)
│   ├── work-orders/[id]/page.tsx     # 601 LOC (duplicated)
│   ├── equipment/[id]/page.tsx       # 426 LOC (duplicated)
│   ├── certificates/[id]/page.tsx    # 427 LOC (duplicated)
│   ├── warranties/[id]/page.tsx      # 357 LOC (duplicated)
│   ├── hours-of-rest/[id]/page.tsx   # 384 LOC (duplicated)
│   ├── receiving/[id]/page.tsx       # 383 LOC (duplicated)
│   ├── shopping-list/[id]/page.tsx   # 389 LOC (duplicated)
│   ├── inventory/[id]/page.tsx       # 245 LOC (duplicated)
│   ├── documents/[id]/page.tsx       # 449 LOC (duplicated)
│   ├── purchasing/[id]/page.tsx      # 420 LOC (duplicated)
│   └── handover-export/[id]/page.tsx # 196 LOC (duplicated)
│
├── components/lens/
│   ├── FaultLensContent.tsx          # 431 LOC (source of truth)
│   ├── WorkOrderLensContent.tsx      # 489 LOC (source of truth)
│   └── ...
│
└── hooks/
    ├── useFaultActions.ts            # Actions + hardcoded permissions
    ├── useWorkOrderActions.ts        # Actions + hardcoded permissions
    └── ...
```

### After

```
apps/web/src/
├── app/
│   ├── faults/[id]/page.tsx          # ~20 LOC (RouteShell wrapper)
│   ├── work-orders/[id]/page.tsx     # ~20 LOC (RouteShell wrapper)
│   ├── equipment/[id]/page.tsx       # ~20 LOC (RouteShell wrapper)
│   ├── certificates/[id]/page.tsx    # ~20 LOC (RouteShell wrapper)
│   ├── warranties/[id]/page.tsx      # ~20 LOC (RouteShell wrapper)
│   ├── hours-of-rest/[id]/page.tsx   # ~20 LOC (RouteShell wrapper)
│   ├── receiving/[id]/page.tsx       # ~20 LOC (RouteShell wrapper)
│   ├── shopping-list/[id]/page.tsx   # ~20 LOC (RouteShell wrapper)
│   ├── inventory/[id]/page.tsx       # ~20 LOC (RouteShell wrapper)
│   ├── documents/[id]/page.tsx       # ~20 LOC (RouteShell wrapper)
│   ├── purchasing/[id]/page.tsx      # ~20 LOC (RouteShell wrapper)
│   └── handover-export/[id]/page.tsx # ~20 LOC (RouteShell wrapper)
│
├── components/lens/
│   ├── RouteShell.tsx                # ~150 LOC (NEW - route wrapper)
│   ├── LensRenderer.tsx              # ~154 LOC (unchanged)
│   ├── FaultLensContent.tsx          # 431 LOC (unchanged - source of truth)
│   ├── WorkOrderLensContent.tsx      # 489 LOC (unchanged - source of truth)
│   └── ...
│
└── hooks/
    ├── usePermissions.ts             # ~100 LOC (NEW - unified)
    ├── useFaultActions.ts            # Actions only (permissions moved)
    ├── useWorkOrderActions.ts        # Actions only (permissions moved)
    └── ...
```

---

## 5. Migration Checklist

### Phase 1: Foundation (Day 1)

- [ ] Create `/components/lens/RouteShell.tsx`
- [ ] Create `/hooks/usePermissions.ts`
- [ ] Create TypeScript types for lens matrix schema
- [ ] Add unit tests for usePermissions

### Phase 2: Refactor Permission Hooks (Day 2)

- [ ] Migrate `useFaultPermissions` to use `usePermissions`
- [ ] Migrate `useWorkOrderPermissions` to use `usePermissions`
- [ ] Migrate `useEquipmentPermissions` to use `usePermissions`
- [ ] Migrate `useCertificatePermissions` to use `usePermissions`
- [ ] Migrate `useWarrantyPermissions` to use `usePermissions`
- [ ] Migrate `useHoursOfRestPermissions` to use `usePermissions`
- [ ] Migrate `useReceivingPermissions` to use `usePermissions`
- [ ] Migrate `useShoppingListPermissions` to use `usePermissions`
- [ ] Migrate `usePartsPermissions` to use `usePermissions`
- [ ] Migrate `useDocumentPermissions` to use `usePermissions`
- [ ] Migrate `useHandoverPermissions` to use `usePermissions`
- [ ] Migrate `useWorklistPermissions` to use `usePermissions`

### Phase 3: Replace Route Pages (Day 3)

- [ ] Replace `/app/faults/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/work-orders/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/equipment/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/certificates/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/warranties/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/hours-of-rest/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/receiving/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/shopping-list/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/inventory/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/documents/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/purchasing/[id]/page.tsx` with RouteShell
- [ ] Replace `/app/handover-export/[id]/page.tsx` with RouteShell

### Phase 4: Validation (Day 4)

- [ ] Run TypeScript compiler (`npm run build`)
- [ ] Run E2E tests with feature flag OFF (redirects work)
- [ ] Run E2E tests with feature flag ON (all buttons work)
- [ ] Verify lens_matrix.json changes propagate to UI
- [ ] Run button audit script to verify zero unwired buttons
- [ ] Performance test: no regression in load times

---

## 6. Acceptance Criteria

| Criterion | Verification Method |
|-----------|---------------------|
| TypeScript compiles | `npm run build` succeeds with no errors |
| Feature flag OFF | Routes redirect to `/app?entity=...&id=...` |
| Feature flag ON | Routes render full lens UI with working buttons |
| All buttons wired | Run button audit script, expect 0 unwired |
| lens_matrix.json changes | Add role to action, verify button appears |
| No regression | E2E test pass rate >= 95% |
| LOC reduction | Route pages total < 300 LOC |

---

## 7. Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Route page total LOC | ~4,682 | ~240 | **-95%** |
| Unwired buttons | 26 | 0 | **-100%** |
| RBAC sources of truth | 3 | 1 | **-67%** |
| Files to update for new action | 3 | 1 | **-67%** |
| Permission hook LOC | ~4,200 | ~300 | **-93%** |
| Maintenance burden | HIGH | LOW | Qualitative |

---

## 8. Risk Mitigation

### Risk 1: Breaking LensContent Components

**Mitigation:** LensContent components are **unchanged**. RouteShell only wraps them with route-specific callbacks. The existing SPA lens rendering via ContextPanel continues to work.

### Risk 2: Feature Flag Regression

**Mitigation:** RouteShell includes the same feature flag check as existing pages. If disabled, it redirects to the legacy route. No change in behavior.

### Risk 3: Navigation Behavior Changes

**Mitigation:** RouteShell explicitly handles navigation:
- `onBack` -> `router.push(listRoute)`
- `onClose` -> `router.push(listRoute)`
- `onNavigate` -> `router.push(/${entityRoute}/${id})`

This matches the current route page behavior exactly.

### Risk 4: Permission Logic Differs

**Mitigation:** The new `usePermissions` hook reads from the **same lens_matrix.json** that the backend uses. This ensures frontend and backend permission logic are always in sync.

### Risk 5: E2E Test Failures

**Mitigation:**
- All existing `data-testid` attributes are preserved (they're in LensContent)
- Navigation patterns match existing behavior
- Feature flag gating is identical

---

## 9. References

- `lens_matrix.json`: `/.planning/agents/lens-matrix/lens_matrix.json`
- LensRenderer: `/apps/web/src/components/lens/LensRenderer.tsx`
- Button Hardening Audit: `/docs/ON_GOING_WORK/BACKEND/LENSES/GAPS.md`
- Feature Flags: `/apps/web/src/lib/featureFlags.ts`

---

*Specification complete. Ready for implementation upon approval.*
