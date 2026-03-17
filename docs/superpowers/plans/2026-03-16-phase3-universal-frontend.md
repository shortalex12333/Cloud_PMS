# Phase 3: Universal Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 10 per-entity action hooks and gut 12 entity `[id]/page.tsx` files by building `useEntityLens` + `EntityLensContext` + `EntityLensPage`, eliminating all frontend role arrays and the `canPerformAction()` function — role filtering is now solely owned by the Phase 2 backend `available_actions` response.

**Architecture:** A universal `useEntityLens(entityType, entityId)` hook fetches the entity GET endpoint (which now returns `available_actions` per Phase 2) and owns execution via `executeAction`. An `EntityLensContext` distributes entity data + execution throughout the component tree. An `EntityLensPage` shell handles loading/error states, the lifecycle action bar, and signature interception — entity-specific `*LensContent` components plug into it as a `content` prop and read from context. Migration is incremental: work_order first (most complex), then one entity per PR, old hook deleted in the same commit as its replacement.

**Tech Stack:** Next.js 14 App Router, React 18, TanStack React Query (already installed but NOT used by new hook — direct fetch with useState is the pattern used by existing pages), vitest (unit tests), TypeScript, Tailwind CSS.

---

## File Map

### New files (create)
| File | Responsibility |
|------|----------------|
| `apps/web/src/types/entity.ts` | `EntityType`, `AvailableAction`, `ActionResult` — the API contract types |
| `apps/web/src/contexts/EntityLensContext.tsx` | Context shape, `EntityLensProvider`, `useEntityLensContext()` |
| `apps/web/src/hooks/useEntityLens.ts` | Universal fetch + execute hook |
| `apps/web/src/components/lens/EntityLensPage.tsx` | Shared shell: loading/error states, action bar, signature interception |
| `apps/web/src/hooks/__tests__/useEntityLens.test.ts` | Unit tests for the hook |
| `apps/web/src/contexts/__tests__/EntityLensContext.test.tsx` | Unit tests for context |

### Modified files
| File | Change |
|------|--------|
| `apps/web/src/types/actions.ts` | Gut from 1244 → ~70 lines: delete `ACTION_REGISTRY`, `canPerformAction`, `MicroAction`, `role_restricted`. Keep `ACTION_DISPLAY` map + `getActionDisplay()`. |
| `apps/web/src/components/lens/EntityLensPage.tsx` | Task 5 Step 3: replace inline `getActionDisplay` stub with real import from `@/types/actions`. |

### Per-entity migration (one PR each)
For each entity: gut `[id]/page.tsx` to ~15 lines, rewrite `*LensContent` to read from `useEntityLensContext()`, delete old hook.

| Order | Entity | LensContent | Page | Hook deleted |
|-------|--------|-------------|------|--------------|
| 1 | work_order | `WorkOrderLensContent.tsx` | `work-orders/[id]/page.tsx` | `useWorkOrderActions.ts` |
| 2 | fault | `FaultLensContent.tsx` | `faults/[id]/page.tsx` | `useFaultActions.ts` |
| 3 | equipment | `EquipmentLensContent.tsx` | `equipment/[id]/page.tsx` | `useEquipmentActions.ts` |
| 4 | part | `PartsLensContent.tsx` | `inventory/[id]/page.tsx` | `usePartActions.ts` |
| 5 | receiving | `ReceivingLensContent.tsx` | `receiving/[id]/page.tsx` | `useReceivingActions.ts` |
| 6 | certificate | `CertificateLensContent.tsx` | `certificates/[id]/page.tsx` | (no hook) |
| 7 | document | `DocumentLensContent.tsx` | `documents/[id]/page.tsx` | `useDocumentActions.ts` |
| 8 | shopping_list | `ShoppingListLensContent.tsx` | `shopping-list/[id]/page.tsx` | (no hook) |
| 9 | warranty | `WarrantyLensContent.tsx` | `warranties/[id]/page.tsx` | (no hook) |
| 10 | hours_of_rest | `HoursOfRestLensContent.tsx` | `hours-of-rest/[id]/page.tsx` | `useHoursOfRestActions.ts` |
| 11 | purchase_order | `PurchaseOrderLensContent.tsx` | `purchasing/[id]/page.tsx` | (no hook) |
| 12 | handover_export | `HandoverExportLensContent.tsx` | `handover-export/[id]/page.tsx` | `useHandoverActions.ts` |

### Final cleanup (Task 18)
Delete `useEntityActions.ts` and `useActionHandler.ts` — both depend on `canPerformAction` and `ACTION_REGISTRY` which are gone after Task 5.

---

## Chunk 1: Infrastructure

### Task 1: API contract types in `types/entity.ts`

**Files:**
- Create: `apps/web/src/types/entity.ts`

- [ ] **Step 1: Create the file with EntityType, AvailableAction, ActionResult**

```typescript
// apps/web/src/types/entity.ts

export type EntityType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'receiving'
  | 'certificate'
  | 'document'
  | 'shopping_list'
  | 'warranty'
  | 'hours_of_rest'
  | 'purchase_order'
  | 'handover_export';

/**
 * One action entry from the backend GET /v1/entity/{type}/{id} response.
 * Backend populates: action_id, label, variant, disabled, disabled_reason,
 * requires_signature, prefill, required_fields, optional_fields.
 * Frontend role filtering has been moved to the backend (Phase 2).
 * If an action is absent from this array, the current user has no permission.
 */
export interface AvailableAction {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'SIGNED';
  disabled: boolean;
  disabled_reason: string | null;
  requires_signature: boolean;
  prefill: Record<string, unknown>;
  required_fields: string[];
  optional_fields: string[];
}

/**
 * Response shape from POST /api/v1/actions/execute (Next.js proxy → backend).
 */
export interface ActionResult {
  success: boolean;
  data?: Record<string, unknown>;
  message?: string;
  error?: string;
  code?: string;
  execution_id?: string;
}
```

- [ ] **Step 2: Verify TypeScript accepts the file**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only pre-existing errors unrelated to this file).

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/types/entity.ts
git commit -m "feat(frontend): add EntityType, AvailableAction, ActionResult types"
```

---

### Task 2: EntityLensContext

**Files:**
- Create: `apps/web/src/contexts/EntityLensContext.tsx`
- Create: `apps/web/src/contexts/__tests__/EntityLensContext.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/contexts/__tests__/EntityLensContext.test.tsx
import { describe, it, expect } from 'vitest';
import { render, renderHook } from '@testing-library/react';
import * as React from 'react';
import { EntityLensProvider, useEntityLensContext } from '../EntityLensContext';
import type { EntityLensContextValue } from '../EntityLensContext';

const makeValue = (overrides: Partial<EntityLensContextValue> = {}): EntityLensContextValue => ({
  entityType: 'work_order',
  entityId: 'test-id',
  entity: null,
  availableActions: [],
  isLoading: false,
  error: null,
  executeAction: async () => ({ success: true }),
  refetch: () => {},
  getAction: () => null,
  ...overrides,
});

describe('useEntityLensContext', () => {
  it('throws when used outside EntityLensProvider', () => {
    expect(() => {
      renderHook(() => useEntityLensContext());
    }).toThrow('useEntityLensContext must be used inside EntityLensProvider');
  });

  it('returns the provided value when inside EntityLensProvider', () => {
    const value = makeValue({ entityId: 'abc-123' });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.entityId).toBe('abc-123');
  });

  it('getAction returns null for an action_id not in availableActions', () => {
    const value = makeValue({
      availableActions: [
        { action_id: 'close_work_order', label: 'Close', variant: 'MUTATE', disabled: false, disabled_reason: null, requires_signature: false, prefill: {}, required_fields: [], optional_fields: [] },
      ],
    });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.getAction('nonexistent_action')).toBeNull();
  });

  it('getAction returns the action when it exists in availableActions', () => {
    const action = {
      action_id: 'close_work_order',
      label: 'Close',
      variant: 'MUTATE' as const,
      disabled: false,
      disabled_reason: null,
      requires_signature: false,
      prefill: {},
      required_fields: [],
      optional_fields: [],
    };
    const value = makeValue({ availableActions: [action] });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.getAction('close_work_order')).toEqual(action);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd apps/web && npx vitest run src/contexts/__tests__/EntityLensContext.test.tsx
```

Expected: FAIL — `EntityLensContext` module not found.

- [ ] **Step 3: Implement EntityLensContext.tsx**

```typescript
// apps/web/src/contexts/EntityLensContext.tsx
'use client';

import * as React from 'react';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

export interface EntityLensContextValue {
  entityType: EntityType;
  entityId: string;
  entity: Record<string, unknown> | null;
  availableActions: AvailableAction[];
  isLoading: boolean;
  error: string | null;
  executeAction: (actionId: string, payload?: Record<string, unknown>) => Promise<ActionResult>;
  refetch: () => void;
  /**
   * Returns the AvailableAction entry for this actionId, or null if the backend
   * omitted it (meaning the current role has no permission).
   * null = don't render the button at all.
   * { disabled: true } = render the button greyed out with disabled_reason tooltip.
   */
  getAction: (actionId: string) => AvailableAction | null;
}

const EntityLensContext = React.createContext<EntityLensContextValue | null>(null);

export function EntityLensProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: EntityLensContextValue;
}) {
  return <EntityLensContext.Provider value={value}>{children}</EntityLensContext.Provider>;
}

export function useEntityLensContext(): EntityLensContextValue {
  const ctx = React.useContext(EntityLensContext);
  if (!ctx) {
    throw new Error('useEntityLensContext must be used inside EntityLensProvider');
  }
  return ctx;
}
```

- [ ] **Step 4: Run to verify tests pass**

```bash
cd apps/web && npx vitest run src/contexts/__tests__/EntityLensContext.test.tsx
```

Expected: 4 PASS.

- [ ] **Step 5: Typecheck**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/contexts/EntityLensContext.tsx apps/web/src/contexts/__tests__/EntityLensContext.test.tsx
git commit -m "feat(frontend): add EntityLensContext with provider and useEntityLensContext hook"
```

---

### Task 3: useEntityLens hook

**Files:**
- Create: `apps/web/src/hooks/useEntityLens.ts`
- Create: `apps/web/src/hooks/__tests__/useEntityLens.test.ts`

**Context for implementer:** The existing entity pages (e.g. `apps/web/src/app/work-orders/[id]/page.tsx`) fetch the entity directly using:
```typescript
const res = await fetch(`${NEXT_PUBLIC_API_URL}/v1/entity/${entityType}/${id}`, {
  headers: { Authorization: `Bearer ${token}` },
});
```
The Phase 2 backend now returns `available_actions` in that response. `useEntityLens` consolidates this fetch + the `executeAction` call into one hook.

Action execution uses the Next.js proxy at `/api/v1/actions/execute` (see `apps/web/src/app/api/v1/actions/execute/route.ts`) which forwards to the backend.

The `useAuth` hook (at `apps/web/src/hooks/useAuth.ts`) returns `{ session, user }` where `session.access_token` is the Bearer token.

- [ ] **Step 1: Write failing tests**

```typescript
// apps/web/src/hooks/__tests__/useEntityLens.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useEntityLens } from '../useEntityLens';

// Mock useAuth
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ session: { access_token: 'test-token' }, user: { id: 'u1' } }),
}));

const mockAction = {
  action_id: 'close_work_order',
  label: 'Close',
  variant: 'MUTATE' as const,
  disabled: false,
  disabled_reason: null,
  requires_signature: false,
  prefill: { work_order_id: 'wo-1' },
  required_fields: ['work_order_id'],
  optional_fields: [],
};

const mockEntity = {
  id: 'wo-1',
  title: 'Test WO',
  status: 'open',
  available_actions: [mockAction],
};

describe('useEntityLens', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('fetches entity and populates entity + availableActions', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entity).toEqual({ id: 'wo-1', title: 'Test WO', status: 'open' });
    expect(result.current.availableActions).toHaveLength(1);
    expect(result.current.availableActions[0].action_id).toBe('close_work_order');
  });

  it('sets error when fetch fails', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'bad-id'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe('404');
    expect(result.current.entity).toBeNull();
  });

  it('executeAction merges prefill into payload before POSTing', async () => {
    // First call: entity fetch
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })
      // Second call: executeAction
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      // Third call: refetch after success
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', { completion_notes: 'done' });
    });

    // Check the second fetch call (index 1) is the execute call
    const executeCalls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const executeCall = executeCalls[1];
    const body = JSON.parse(executeCall[1].body);
    // prefill has work_order_id: 'wo-1', payload should include it
    expect(body.payload.work_order_id).toBe('wo-1');
    expect(body.payload.completion_notes).toBe('done');
  });

  it('executeAction triggers refetch on success', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...mockEntity, status: 'closed', available_actions: [] }) });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', {});
    });

    // After executeAction + refetch, available_actions should be empty (state changed)
    expect(result.current.availableActions).toHaveLength(0);
  });

  it('executeAction does NOT refetch when the execute POST fails', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })  // initial fetch
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ success: false, error: 'Validation failed' }) });  // execute fails

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', {});
    });

    // Only 2 fetch calls: initial fetch + failed execute. No refetch.
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(2);
    // Available actions unchanged (no refetch happened)
    expect(result.current.availableActions).toHaveLength(1);
  });

  it('getAction returns null for an action_id not in availableActions', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.getAction('nonexistent')).toBeNull();
  });

  it('getAction returns the action when it exists', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.getAction('close_work_order')).toEqual(mockAction);
  });
});
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd apps/web && npx vitest run src/hooks/__tests__/useEntityLens.test.ts
```

Expected: FAIL — `useEntityLens` module not found.

- [ ] **Step 3: Implement useEntityLens.ts**

```typescript
// apps/web/src/hooks/useEntityLens.ts
'use client';

import { useCallback, useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export interface UseEntityLensResult {
  entity: Record<string, unknown> | null;
  availableActions: AvailableAction[];
  isLoading: boolean;
  error: string | null;
  executeAction: (actionId: string, payload?: Record<string, unknown>) => Promise<ActionResult>;
  refetch: () => void;
  getAction: (actionId: string) => AvailableAction | null;
}

export function useEntityLens(
  entityType: EntityType,
  entityId: string
): UseEntityLensResult {
  const { session } = useAuth();
  const token = session?.access_token ?? null;

  const [entity, setEntity] = useState<Record<string, unknown> | null>(null);
  const [availableActions, setAvailableActions] = useState<AvailableAction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEntity = useCallback(async () => {
    if (!entityId || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/v1/entity/${entityType}/${entityId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json() as Record<string, unknown> & { available_actions?: AvailableAction[] };
      const { available_actions = [], ...rest } = data;
      setEntity(rest);
      setAvailableActions(available_actions);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setIsLoading(false);
    }
  }, [entityType, entityId, token]);

  useEffect(() => {
    fetchEntity();
  }, [fetchEntity]);

  const executeAction = useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      if (!token) throw new Error('Not authenticated');
      // Merge prefill from the matching available_actions entry — backend provides
      // context-aware defaults (e.g. work_order_id, fault_id) so callers don't
      // need to know which fields are required.
      const actionMeta = availableActions.find((a) => a.action_id === actionId);
      const mergedPayload = { ...actionMeta?.prefill, ...payload };
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: actionId,
          context: { entity_id: entityId },
          payload: mergedPayload,
        }),
      });
      const result: ActionResult = await res.json();
      if (res.ok) {
        // Refetch: entity state and available_actions both change after a mutation
        await fetchEntity();
      }
      return result;
    },
    [token, entityId, availableActions, fetchEntity]
  );

  const getAction = useCallback(
    (actionId: string): AvailableAction | null =>
      availableActions.find((a) => a.action_id === actionId) ?? null,
    [availableActions]
  );

  return { entity, availableActions, isLoading, error, executeAction, refetch: fetchEntity, getAction };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/web && npx vitest run src/hooks/__tests__/useEntityLens.test.ts
```

Expected: 7 PASS.

- [ ] **Step 5: Typecheck**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/hooks/useEntityLens.ts apps/web/src/hooks/__tests__/useEntityLens.test.ts
git commit -m "feat(frontend): add useEntityLens hook — universal entity fetch + execute"
```

---

### Task 4: EntityLensPage shell component

**Files:**
- Create: `apps/web/src/components/lens/EntityLensPage.tsx`

**Context for implementer:**
- `RouteLayout` is imported from `@/components/layout` — used in all current entity pages. It accepts `pageTitle`, `showTopNav`, `topNavContent`, `primaryPanel`, and `onClosePrimaryPanel` props.
- `useRelatedPanel` is at `@/hooks/useRelatedPanel` — already universal.
- `useReadBeacon` is at `@/hooks/useReadBeacon` — marks entity as read.
- `ShowRelatedButton`, `RelatedDrawer`, `AddRelatedItemModal` are in `@/components/lens/`.
- `getEntityRoute` is at `@/lib/featureFlags` — maps `(entityType, entityId)` → route path.
- `getActionDisplay` (from Task 5) maps `actionId` → `{ icon, cluster }`. **Implement a local version inline in this file until Task 5 completes**, then replace the import. Local version: `const getActionDisplay = (id: string) => ({ icon: 'circle', cluster: 'entity' as const })`.
- Shell action bar: renders only actions whose `cluster` is `'lifecycle'` or `'entity'`. Other actions (notes, inventory, etc.) are rendered inline by `*LensContent` components via `useEntityLensContext()`.
- Signature interception: if `action.requires_signature` is true, the shell shows a PIN modal before calling `executeAction`. The full TOTP flow is a future phase — the modal in this task collects a PIN string and appends `{ pin }` to the payload.

- [ ] **Step 1: Create EntityLensPage.tsx**

```typescript
// apps/web/src/components/lens/EntityLensPage.tsx
'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { RouteLayout } from '@/components/layout';
import { useEntityLens } from '@/hooks/useEntityLens';
import { EntityLensProvider } from '@/contexts/EntityLensContext';
import { useRelatedPanel } from '@/hooks/useRelatedPanel';
import { useReadBeacon } from '@/hooks/useReadBeacon';
import { ShowRelatedButton } from './ShowRelatedButton';
import { RelatedDrawer } from './RelatedDrawer';
import { AddRelatedItemModal } from './AddRelatedItemModal';
import { getEntityRoute } from '@/lib/featureFlags';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

// ACTION_DISPLAY import — populated in Task 5. Until then, use the fallback.
// After Task 5: import { getActionDisplay } from '@/types/actions';
function getActionDisplay(actionId: string): { icon: string; cluster: string } {
  const DISPLAY: Record<string, { icon: string; cluster: string }> = {
    start_work_order:           { icon: 'play',          cluster: 'lifecycle' },
    close_work_order:           { icon: 'check',         cluster: 'lifecycle' },
    cancel_work_order:          { icon: 'x',             cluster: 'lifecycle' },
    reopen_work_order:          { icon: 'rotate-ccw',    cluster: 'lifecycle' },
    archive_work_order:         { icon: 'archive',       cluster: 'entity'    },
    reassign_work_order:        { icon: 'user',          cluster: 'entity'    },
    update_work_order:          { icon: 'edit',          cluster: 'entity'    },
    close_fault:                { icon: 'check',         cluster: 'lifecycle' },
    reopen_fault:               { icon: 'rotate-ccw',   cluster: 'lifecycle' },
    acknowledge_fault:          { icon: 'check-circle',  cluster: 'lifecycle' },
    mark_fault_false_alarm:     { icon: 'x-circle',     cluster: 'lifecycle' },
    report_fault:               { icon: 'alert',         cluster: 'entity'    },
    decommission_equipment:     { icon: 'trash',         cluster: 'lifecycle' },
    update_equipment_status:    { icon: 'edit',          cluster: 'entity'    },
    flag_equipment_attention:   { icon: 'flag',          cluster: 'entity'    },
    write_off_part:             { icon: 'trash',         cluster: 'lifecycle' },
    accept_receiving:           { icon: 'check',         cluster: 'lifecycle' },
    reject_receiving:           { icon: 'x',             cluster: 'lifecycle' },
    update_receiving:           { icon: 'edit',          cluster: 'entity'    },
    update_certificate:         { icon: 'edit',          cluster: 'entity'    },
    export_handover:            { icon: 'download',      cluster: 'entity'    },
    export_hours_of_rest:       { icon: 'download',      cluster: 'compliance'},
  };
  return DISPLAY[actionId] ?? { icon: 'circle', cluster: 'entity' };
}

// Clusters rendered in the shell action bar (not inline in content)
const SHELL_CLUSTERS = new Set(['lifecycle', 'entity', 'compliance']);

// ---------------------------------------------------------------------------
// Signature modal (PIN collection only — TOTP is a future phase)
// ---------------------------------------------------------------------------
function SignatureModal({
  action,
  onConfirm,
  onCancel,
}: {
  action: AvailableAction;
  onConfirm: (credentials: { pin: string }) => void;
  onCancel: () => void;
}) {
  const [pin, setPin] = React.useState('');
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1a1a1f] border border-white/10 rounded-xl p-6 w-80 space-y-4">
        <h2 className="text-white font-semibold">Signature Required</h2>
        <p className="text-sm text-white/60">{action.label} requires authorization.</p>
        <input
          type="password"
          placeholder="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && pin && onConfirm({ pin })}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm"
          data-testid="signature-pin-input"
        />
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!pin}
            onClick={() => onConfirm({ pin })}
            className="flex-1 px-3 py-2 bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/30 rounded-lg text-sm text-teal-300 disabled:opacity-40 transition-colors"
            data-testid="signature-confirm-button"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading / error / not-found states (shared across all 12 entity pages)
// ---------------------------------------------------------------------------
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full min-h-64">
      <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 min-h-64">
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

function NotFoundState({ entityType, onBack }: { entityType: EntityType; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 min-h-64">
      <h3 className="text-lg font-medium text-white mb-2">Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">
        This {entityType.replace(/_/g, ' ')} may have been deleted or you may not have access.
      </p>
      <button
        onClick={onBack}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Go Back
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export interface EntityLensPageProps {
  entityType: EntityType;
  entityId: string;
  /** Entity-specific content component — reads from useEntityLensContext() directly */
  content: React.ComponentType;
  /** Optional fallback title if entity has no title/name field */
  pageTitle?: string;
}

export function EntityLensPage({
  entityType,
  entityId,
  content: Content,
  pageTitle,
}: EntityLensPageProps) {
  const router = useRouter();
  const lens = useEntityLens(entityType, entityId);

  const [pendingSignature, setPendingSignature] = React.useState<{
    action: AvailableAction;
    payload: Record<string, unknown>;
  } | null>(null);

  const {
    open: relatedOpen,
    setOpen: setRelatedOpen,
    showAddModal,
    setShowAddModal,
    canAdd: canAddRelated,
    data: relatedData,
    isLoading: relatedLoading,
    error: relatedError,
    totalRelated,
  } = useRelatedPanel(entityType, entityId);

  useReadBeacon(entityType, entityId);

  const handleNavigate = React.useCallback(
    (type: string, id: string) => {
      router.push(getEntityRoute(type as EntityType, id));
    },
    [router]
  );

  const handleBack = React.useCallback(() => router.back(), [router]);

  /**
   * safeExecute wraps lens.executeAction with signature interception.
   * If requires_signature is true, shows the PIN modal instead of executing.
   * After PIN entry, calls lens.executeAction with credentials merged in.
   * Content components call this via useEntityLensContext().executeAction.
   */
  const safeExecute = React.useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      const actionMeta = lens.getAction(actionId);
      if (actionMeta?.requires_signature) {
        setPendingSignature({ action: actionMeta, payload });
        return { success: false, message: 'Awaiting signature' };
      }
      return lens.executeAction(actionId, payload);
    },
    [lens]
  );

  // Shell action bar: lifecycle + entity cluster only
  const shellActions = lens.availableActions.filter((a) => {
    const { cluster } = getActionDisplay(a.action_id);
    return SHELL_CLUSTERS.has(cluster);
  });

  const contextValue = React.useMemo(
    () => ({
      entityType,
      entityId,
      entity: lens.entity,
      availableActions: lens.availableActions,
      isLoading: lens.isLoading,
      error: lens.error,
      executeAction: safeExecute,
      refetch: lens.refetch,
      getAction: lens.getAction,
    }),
    [entityType, entityId, lens, safeExecute]
  );

  const entityTitle = (
    lens.entity?.title ||
    lens.entity?.name ||
    lens.entity?.reference_number ||
    pageTitle ||
    entityType.replace(/_/g, ' ')
  ) as string;

  let bodyContent: React.ReactNode;

  if (lens.isLoading) {
    bodyContent = <LoadingState />;
  } else if (lens.error) {
    if (lens.error.includes('404')) {
      bodyContent = <NotFoundState entityType={entityType} onBack={handleBack} />;
    } else {
      bodyContent = <ErrorState message={lens.error} onRetry={lens.refetch} />;
    }
  } else if (!lens.entity) {
    bodyContent = <NotFoundState entityType={entityType} onBack={handleBack} />;
  } else {
    bodyContent = (
      <EntityLensProvider value={contextValue}>
        <div className="max-w-3xl mx-auto p-6 space-y-6">
          <Content />
          {/* Shell action bar — lifecycle and entity-level actions */}
          {shellActions.length > 0 && (
            <div
              className="flex gap-3 pt-4 border-t border-white/10 flex-wrap"
              data-testid="shell-action-bar"
            >
              {shellActions.map((action) => (
                <button
                  key={action.action_id}
                  disabled={action.disabled}
                  title={action.disabled_reason ?? undefined}
                  onClick={() => safeExecute(action.action_id)}
                  data-testid={`action-${action.action_id}`}
                  className="px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors flex items-center gap-2"
                >
                  {action.label}
                  {action.variant === 'SIGNED' && (
                    <span className="text-xs text-yellow-400" title="Requires signature">
                      ✎
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </EntityLensProvider>
    );
  }

  return (
    <main role="main" data-testid={`${entityType}-detail`}>
      <RouteLayout
        pageTitle={entityTitle}
        showTopNav={true}
        topNavContent={
          <div className="flex items-center justify-between w-full">
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
                <p className="text-xs text-white/40 uppercase tracking-wider">
                  {entityType.replace(/_/g, ' ')}
                </p>
                <h1 className="text-lg font-semibold text-white truncate max-w-md">
                  {entityTitle}
                </h1>
              </div>
            </div>
            <ShowRelatedButton
              onClick={() => setRelatedOpen((open) => !open)}
              isOpen={relatedOpen}
              count={totalRelated}
              isLoading={relatedLoading}
            />
          </div>
        }
        primaryPanel={{
          visible: relatedOpen,
          title: 'Related',
          subtitle: `${totalRelated} item${totalRelated !== 1 ? 's' : ''}`,
          children: (
            <RelatedDrawer
              groups={relatedData?.groups ?? []}
              isLoading={relatedLoading}
              error={relatedError ?? null}
              onNavigate={handleNavigate}
              onAddRelated={canAddRelated ? () => setShowAddModal(true) : undefined}
            />
          ),
        }}
        onClosePrimaryPanel={() => setRelatedOpen(false)}
      >
        {bodyContent}
      </RouteLayout>

      {showAddModal && (
        <AddRelatedItemModal
          fromEntityType={entityType}
          fromEntityId={entityId}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {pendingSignature && (
        <SignatureModal
          action={pendingSignature.action}
          onConfirm={async (credentials) => {
            await lens.executeAction(pendingSignature.action.action_id, {
              ...pendingSignature.payload,
              ...credentials,
            });
            setPendingSignature(null);
          }}
          onCancel={() => setPendingSignature(null)}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 2: Typecheck**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -30
```

Fix any type errors before proceeding.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/lens/EntityLensPage.tsx
git commit -m "feat(frontend): add EntityLensPage shell with action bar and signature interception"
```

---

### Task 5: Gut types/actions.ts to display-only

**Files:**
- Modify: `apps/web/src/types/actions.ts` (read the file first — it is 1244 lines)

**What dies:**
- `MicroAction` type union
- `ACTION_REGISTRY: Record<MicroAction, ActionMetadata>`
- `ActionMetadata` interface
- `canPerformAction(action, userRole)` function
- `requiresConfirmation()`, `requiresReason()`, `getActionMetadata()` helpers
- All `role_restricted` arrays

**What stays:** A ~70-line `ACTION_DISPLAY` map and `getActionDisplay()` helper. See exact content below.

**IMPORTANT:** After this task, `useActionHandler.ts` and `useEntityActions.ts` will have broken imports. That is expected — both files are deleted in Task 18. Do NOT fix those imports now. TypeScript errors from those two files are acceptable until Task 18.

- [ ] **Step 1: Find all consumers of the exports being deleted**

Run both checks. A file may import via a barrel/index re-export without referencing `@/types/actions` directly — the symbol check catches those.

```bash
# Module-path consumers (direct import)
cd apps/web && grep -r "from '@/types/actions'" src --include="*.ts" --include="*.tsx" | grep -v "useActionHandler\|useEntityActions\|useWorkOrderActions\|useFaultActions\|useEquipmentActions\|usePartActions\|useDocumentActions\|useReceivingActions\|useHoursOfRestActions\|useHandoverActions"

# Symbol-level consumers (catches barrel re-exports)
cd apps/web && grep -r "MicroAction\|ACTION_REGISTRY\|canPerformAction\|role_restricted\|getActionMetadata\|requiresConfirmation\|requiresReason" src --include="*.ts" --include="*.tsx" | grep -v "useActionHandler\|useEntityActions\|useWorkOrderActions\|useFaultActions\|useEquipmentActions\|usePartActions\|useDocumentActions\|useReceivingActions\|useHoursOfRestActions\|useHandoverActions"
```

Any files in either list (outside the hooks being deleted) will need updating after this task. Fix them before committing.

- [ ] **Step 2: Replace types/actions.ts with the display-only version**

```typescript
// apps/web/src/types/actions.ts
//
// DISPLAY METADATA ONLY — Phase 3
//
// The backend (Phase 2) now returns available_actions on every entity GET endpoint.
// Backend provides: action_id, label, variant, disabled, disabled_reason,
//                   requires_signature, prefill, required_fields, optional_fields.
// Frontend role filtering (canPerformAction, role_restricted) has been removed.
// This file owns only: icon (rendering concern) and cluster (placement: shell bar vs inline).

export type ActionCluster =
  | 'lifecycle'
  | 'entity'
  | 'notes'
  | 'inventory'
  | 'documents'
  | 'maintenance'
  | 'compliance';

export const ACTION_DISPLAY: Record<string, { icon: string; cluster: ActionCluster }> = {
  // Work Order — lifecycle (shell action bar)
  start_work_order:               { icon: 'play',          cluster: 'lifecycle'    },
  close_work_order:               { icon: 'check',         cluster: 'lifecycle'    },
  cancel_work_order:              { icon: 'x',             cluster: 'lifecycle'    },
  reopen_work_order:              { icon: 'rotate-ccw',    cluster: 'lifecycle'    },
  // Work Order — entity (shell action bar)
  archive_work_order:             { icon: 'archive',       cluster: 'entity'       },
  reassign_work_order:            { icon: 'user',          cluster: 'entity'       },
  update_work_order:              { icon: 'edit',          cluster: 'entity'       },
  // Work Order — inline content
  add_wo_note:                    { icon: 'message',       cluster: 'notes'        },
  add_wo_part:                    { icon: 'package',       cluster: 'inventory'    },
  add_wo_hours:                   { icon: 'clock',         cluster: 'notes'        },
  // Fault — lifecycle
  close_fault:                    { icon: 'check',         cluster: 'lifecycle'    },
  reopen_fault:                   { icon: 'rotate-ccw',   cluster: 'lifecycle'    },
  acknowledge_fault:              { icon: 'check-circle',  cluster: 'lifecycle'    },
  mark_fault_false_alarm:         { icon: 'x-circle',     cluster: 'lifecycle'    },
  // Fault — entity / inline
  report_fault:                   { icon: 'alert',         cluster: 'entity'       },
  create_work_order_from_fault:   { icon: 'clipboard',     cluster: 'entity'       },
  update_fault:                   { icon: 'edit',          cluster: 'entity'       },
  add_fault_note:                 { icon: 'message',       cluster: 'notes'        },
  add_fault_photo:                { icon: 'camera',        cluster: 'notes'        },
  // Equipment — lifecycle
  decommission_equipment:         { icon: 'trash',         cluster: 'lifecycle'    },
  // Equipment — entity / inline
  update_equipment_status:        { icon: 'edit',          cluster: 'entity'       },
  flag_equipment_attention:       { icon: 'flag',          cluster: 'entity'       },
  add_equipment_note:             { icon: 'message',       cluster: 'notes'        },
  create_work_order_for_equipment:{ icon: 'clipboard',     cluster: 'entity'       },
  // Parts / Inventory — lifecycle
  write_off_part:                 { icon: 'trash',         cluster: 'lifecycle'    },
  // Parts — inline
  log_part_usage:                 { icon: 'minus',         cluster: 'inventory'    },
  transfer_part:                  { icon: 'arrow-right',   cluster: 'inventory'    },
  adjust_stock_quantity:          { icon: 'edit',          cluster: 'inventory'    },
  add_to_shopping_list:           { icon: 'shopping-cart', cluster: 'inventory'    },
  // Receiving — lifecycle
  accept_receiving:               { icon: 'check',         cluster: 'lifecycle'    },
  reject_receiving:               { icon: 'x',             cluster: 'lifecycle'    },
  // Receiving — inline
  add_receiving_item:             { icon: 'plus',          cluster: 'inventory'    },
  update_receiving:               { icon: 'edit',          cluster: 'entity'       },
  // Certificate
  update_certificate:             { icon: 'edit',          cluster: 'entity'       },
  // Hours of rest
  update_hours_of_rest:           { icon: 'clock',         cluster: 'compliance'   },
  export_hours_of_rest:           { icon: 'download',      cluster: 'compliance'   },
  // Documents
  view_document:                  { icon: 'file',          cluster: 'documents'    },
  // Handover
  export_handover:                { icon: 'download',      cluster: 'entity'       },
  edit_handover_section:          { icon: 'edit',          cluster: 'notes'        },
};

/**
 * Returns display metadata with a safe fallback for unknown action IDs.
 * Unknown actions (new backend actions not yet added here) get a generic icon
 * and land in the shell action bar until someone adds the display entry.
 */
export function getActionDisplay(actionId: string): { icon: string; cluster: ActionCluster } {
  return ACTION_DISPLAY[actionId] ?? { icon: 'circle', cluster: 'entity' };
}
```

- [ ] **Step 3: Update EntityLensPage.tsx to use the real import**

Replace the inline `getActionDisplay` function in `EntityLensPage.tsx` with the import:

```typescript
import { getActionDisplay } from '@/types/actions';
```

Remove the local `getActionDisplay` function definition and the `DISPLAY` map inside it.

- [ ] **Step 4: Check for other consumers outside the hooks-being-deleted**

Re-run the grep from Step 1. Fix any non-hook consumers. If a file outside the 10 hooks uses `MicroAction` or `ACTION_REGISTRY`, replace the usage with `string` (for IDs) or `getActionDisplay` (for display info).

- [ ] **Step 5: Typecheck (expect errors in useActionHandler.ts and useEntityActions.ts — both deleted in Task 18)**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```

Expected: no errors outside the two files being deleted.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/types/actions.ts apps/web/src/components/lens/EntityLensPage.tsx
git commit -m "feat(frontend): gut types/actions.ts to ACTION_DISPLAY only — role filtering now backend-owned"
```

---

## Chunk 2: Entity Migrations

### Migration Pattern (read before starting Tasks 6–17)

Every entity migration follows the same three-step pattern. Read this once, then apply it for each entity.

**Step A: Rewrite the *LensContent component**

The `*LensContent` component currently imports a per-entity hook and a permissions hook:
```typescript
import { useWorkOrderActions, useWorkOrderPermissions } from '@/hooks/useWorkOrderActions';
```

Replace with context:
```typescript
import { useEntityLensContext } from '@/contexts/EntityLensContext';
```

Inside the component:
- Remove all props that came from the entity (the component now reads from context)
- Replace `const { addNote, closeWorkOrder } = useWorkOrderActions(id)` with `const { executeAction, getAction } = useEntityLensContext()`
- Replace permission checks `if (canClose)` with `const closeAction = getAction('close_work_order'); if (closeAction)` — if null, don't render the button
- Replace `disabled={!canClose}` with `disabled={closeAction?.disabled}`
- Replace `title="..."` tooltip text with `title={closeAction?.disabled_reason ?? undefined}`
- Replace `onRefresh?.()` after action success with nothing — `executeAction` triggers refetch automatically

The component signature changes from:
```typescript
export function WorkOrderLensContent({ id, data, onBack, onClose, onNavigate, onRefresh }: WorkOrderLensContentProps)
```
To:
```typescript
export function WorkOrderLensContent()
```
Navigation (onNavigate, onBack, onClose) is replaced by:
```typescript
const router = useRouter();
// onNavigate → router.push(getEntityRoute(entityType, entityId))
// onBack → router.back()
// onClose → router.push('/work-orders')  ← entity list route
```

**Step B: Gut the [id]/page.tsx**

Replace the entire page body with:
```typescript
'use client';
import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderLensContent } from '@/components/lens/WorkOrderLensContent';

export default function WorkOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="work_order"
      entityId={params.id as string}
      content={WorkOrderLensContent}
    />
  );
}
```

**Step C: Delete the old hook**

```bash
rm apps/web/src/hooks/useWorkOrderActions.ts
```

The hook is fully replaced. Delete in the same commit. Never leave both files alive together.

**Verification for each migration:**
```bash
# TypeScript must pass
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
# Expected: 0 errors from this entity's files

# E2E tests for this entity's shard must still pass
cd apps/web && npx playwright test e2e/shard-*-lens-actions/*ENTITY*actions*.spec.ts --reporter=list
```

---

### Task 6: Migrate work_order (proof of concept)

**Files:**
- Modify: `apps/web/src/components/lens/WorkOrderLensContent.tsx`
- Modify: `apps/web/src/app/work-orders/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useWorkOrderActions.ts`

**Context:** This is the most complex entity — state machine (draft→open→in_progress→closed), action modals, VitalSigns row, checklist, notes, parts, hours. If the universal pattern handles this one correctly, all others follow.

The current `WorkOrderLensContent.tsx` has props: `{ id, data, onBack, onClose, onNavigate, onRefresh }`. After migration it reads everything from `useEntityLensContext()`.

Current imports to remove:
```typescript
import { useWorkOrderActions, useWorkOrderPermissions } from '@/hooks/useWorkOrderActions';
```

- [ ] **Step 1: Read WorkOrderLensContent.tsx fully before touching it**

```bash
cd apps/web && wc -l src/components/lens/WorkOrderLensContent.tsx
```

Read the full file. Note every place `useWorkOrderPermissions` is used (permission checks) and every place `useWorkOrderActions` is used (action calls). Map each to the equivalent `getAction` / `executeAction` call.

- [ ] **Step 2: Rewrite WorkOrderLensContent.tsx following the Migration Pattern**

Key mappings for work_order:
| Old | New |
|-----|-----|
| `canClose` | `getAction('close_work_order')` |
| `canStart` | `getAction('start_work_order')` |
| `canCancel` | `getAction('cancel_work_order')` |
| `canAddNote` | `getAction('add_wo_note')` |
| `canAddPart` | `getAction('add_wo_part')` |
| `canAddHours` | `getAction('add_wo_hours')` |
| `canAssign` / `canArchive` | `getAction('reassign_work_order')` / `getAction('archive_work_order')` |
| `closeWorkOrder(notes)` | `executeAction('close_work_order', { completion_notes: notes })` |
| `addNote(text)` | `executeAction('add_wo_note', { note_text: text })` |
| `data.field` | `entity?.field` (from context) |

Remove `WorkOrderLensContentProps` — the component takes no props.

- [ ] **Step 3: Typecheck WorkOrderLensContent.tsx**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep "WorkOrderLensContent"
```

Expected: no errors on this file.

- [ ] **Step 4: Gut work-orders/[id]/page.tsx**

Replace entire file content with:
```typescript
'use client';

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderLensContent } from '@/components/lens/WorkOrderLensContent';

export default function WorkOrderDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="work_order"
      entityId={params.id as string}
      content={WorkOrderLensContent}
    />
  );
}
```

- [ ] **Step 5: Delete the old hook**

```bash
rm apps/web/src/hooks/useWorkOrderActions.ts
```

- [ ] **Step 6: Full typecheck**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```

Expected: 0 errors.

- [ ] **Step 7: Run unit tests**

```bash
cd apps/web && npx vitest run
```

Expected: all unit tests pass.

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/components/lens/WorkOrderLensContent.tsx
git add apps/web/src/app/work-orders/[id]/page.tsx
git rm apps/web/src/hooks/useWorkOrderActions.ts
git commit -m "feat(frontend): migrate work_order to useEntityLens — delete useWorkOrderActions"
```

---

### Task 7: Migrate fault

**Files:**
- Modify: `apps/web/src/components/lens/FaultLensContent.tsx`
- Modify: `apps/web/src/app/faults/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useFaultActions.ts`

Follow the Migration Pattern exactly. entityType = `'fault'`.

Fault-specific action mappings:
| Old permission/action | New |
|----------------------|-----|
| canClose / closeFault | `getAction('close_fault')` / `executeAction('close_fault', ...)` |
| canReopen / reopenFault | `getAction('reopen_fault')` / `executeAction('reopen_fault', ...)` |
| canAcknowledge | `getAction('acknowledge_fault')` |
| canAddNote / addFaultNote | `getAction('add_fault_note')` / `executeAction('add_fault_note', ...)` |
| canAddPhoto | `getAction('add_fault_photo')` |

Page shell:
```typescript
<EntityLensPage entityType="fault" entityId={params.id as string} content={FaultLensContent} />
```

Steps: read FaultLensContent → rewrite → typecheck → gut page → delete useFaultActions.ts → typecheck → commit.

```bash
git add apps/web/src/components/lens/FaultLensContent.tsx apps/web/src/app/faults/[id]/page.tsx
git rm apps/web/src/hooks/useFaultActions.ts
git commit -m "feat(frontend): migrate fault to useEntityLens — delete useFaultActions"
```

---

### Task 8: Migrate equipment

**Files:**
- Modify: `apps/web/src/components/lens/EquipmentLensContent.tsx`
- Modify: `apps/web/src/app/equipment/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useEquipmentActions.ts`

entityType = `'equipment'`. No state machine — flat entity. This validates the simple path.

Equipment action mappings:
| Old | New |
|-----|-----|
| canDecommission | `getAction('decommission_equipment')` |
| canFlag | `getAction('flag_equipment_attention')` |
| canUpdateStatus | `getAction('update_equipment_status')` |
| canAddNote | `getAction('add_equipment_note')` |

Page shell:
```typescript
<EntityLensPage entityType="equipment" entityId={params.id as string} content={EquipmentLensContent} />
```

Steps: read EquipmentLensContent → rewrite → typecheck → gut page → delete useEquipmentActions.ts → typecheck → commit.

```bash
git add apps/web/src/components/lens/EquipmentLensContent.tsx apps/web/src/app/equipment/[id]/page.tsx
git rm apps/web/src/hooks/useEquipmentActions.ts
git commit -m "feat(frontend): migrate equipment to useEntityLens — delete useEquipmentActions"
```

---

### Task 9: Migrate part (inventory)

**Files:**
- Modify: `apps/web/src/components/lens/PartsLensContent.tsx`
- Modify: `apps/web/src/app/inventory/[id]/page.tsx`
- Delete: `apps/web/src/hooks/usePartActions.ts`

entityType = `'part'`. This entity has SIGNED actions (`write_off_part`) — validates signature variant handling. The shell's `SignatureModal` intercepts `write_off_part` automatically because `requires_signature: true` comes from the backend.

Part action mappings:
| Old | New |
|-----|-----|
| canWriteOff | `getAction('write_off_part')` (will show signature modal when clicked) |
| canLogUsage | `getAction('log_part_usage')` |
| canTransfer | `getAction('transfer_part')` |
| canAddToShoppingList | `getAction('add_to_shopping_list')` |

Page shell:
```typescript
<EntityLensPage entityType="part" entityId={params.id as string} content={PartsLensContent} />
```

Steps: read PartsLensContent → rewrite → typecheck → gut page → delete usePartActions.ts → typecheck → commit.

```bash
git add apps/web/src/components/lens/PartsLensContent.tsx apps/web/src/app/inventory/[id]/page.tsx
git rm apps/web/src/hooks/usePartActions.ts
git commit -m "feat(frontend): migrate part/inventory to useEntityLens — delete usePartActions"
```

---

### Task 10: Migrate receiving

**Files:**
- Modify: `apps/web/src/components/lens/ReceivingLensContent.tsx`
- Modify: `apps/web/src/app/receiving/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useReceivingActions.ts`

entityType = `'receiving'`. Has terminal state gates — validates that accept/reject buttons show as disabled with reason when receiving is already closed.

Receiving action mappings:
| Old | New |
|-----|-----|
| canAccept | `getAction('accept_receiving')` |
| canReject | `getAction('reject_receiving')` |
| canAddItem | `getAction('add_receiving_item')` |

Page shell:
```typescript
<EntityLensPage entityType="receiving" entityId={params.id as string} content={ReceivingLensContent} />
```

Steps: read ReceivingLensContent → rewrite → typecheck → gut page → delete useReceivingActions.ts → typecheck → commit.

```bash
git add apps/web/src/components/lens/ReceivingLensContent.tsx apps/web/src/app/receiving/[id]/page.tsx
git rm apps/web/src/hooks/useReceivingActions.ts
git commit -m "feat(frontend): migrate receiving to useEntityLens — delete useReceivingActions"
```

---

### Task 11: Migrate certificate

**Files:**
- Modify: `apps/web/src/components/lens/CertificateLensContent.tsx`
- Modify: `apps/web/src/app/certificates/[id]/page.tsx`

entityType = `'certificate'`. No dedicated hook to delete. Flat entity — no state machine.

Page shell:
```typescript
<EntityLensPage entityType="certificate" entityId={params.id as string} content={CertificateLensContent} />
```

Steps: read CertificateLensContent → rewrite → gut page → then:

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
Expected: 0 errors from certificate files.

- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
Expected: all pass.

- [ ] **Commit**
```bash
git add apps/web/src/components/lens/CertificateLensContent.tsx apps/web/src/app/certificates/[id]/page.tsx
git commit -m "feat(frontend): migrate certificate to useEntityLens"
```

---

### Task 12: Migrate document

**Files:**
- Modify: `apps/web/src/components/lens/DocumentLensContent.tsx`
- Modify: `apps/web/src/app/documents/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useDocumentActions.ts`

entityType = `'document'`. Read-only entity (documents are viewed, not mutated through actions). Validates the READ variant path.

Page shell:
```typescript
<EntityLensPage entityType="document" entityId={params.id as string} content={DocumentLensContent} />
```

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
Expected: 0 errors from document files.

- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
Expected: all pass.

- [ ] **Commit**
```bash
git add apps/web/src/components/lens/DocumentLensContent.tsx apps/web/src/app/documents/[id]/page.tsx
git rm apps/web/src/hooks/useDocumentActions.ts
git commit -m "feat(frontend): migrate document to useEntityLens — delete useDocumentActions"
```

---

### Task 13: Migrate shopping_list

**Files:**
- Modify: `apps/web/src/components/lens/ShoppingListLensContent.tsx`
- Modify: `apps/web/src/app/shopping-list/[id]/page.tsx`

entityType = `'shopping_list'`. No dedicated hook. Flat entity.

Page shell:
```typescript
<EntityLensPage entityType="shopping_list" entityId={params.id as string} content={ShoppingListLensContent} />
```

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
- [ ] **Commit**
```bash
git add apps/web/src/components/lens/ShoppingListLensContent.tsx apps/web/src/app/shopping-list/[id]/page.tsx
git commit -m "feat(frontend): migrate shopping_list to useEntityLens"
```

---

### Task 14: Migrate warranty

**Files:**
- Modify: `apps/web/src/components/lens/WarrantyLensContent.tsx`
- Modify: `apps/web/src/app/warranties/[id]/page.tsx`

entityType = `'warranty'`. No dedicated hook. Flat entity.

Page shell:
```typescript
<EntityLensPage entityType="warranty" entityId={params.id as string} content={WarrantyLensContent} />
```

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
- [ ] **Commit**
```bash
git add apps/web/src/components/lens/WarrantyLensContent.tsx apps/web/src/app/warranties/[id]/page.tsx
git commit -m "feat(frontend): migrate warranty to useEntityLens"
```

---

### Task 15: Migrate hours_of_rest

**Files:**
- Modify: `apps/web/src/components/lens/HoursOfRestLensContent.tsx`
- Modify: `apps/web/src/app/hours-of-rest/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useHoursOfRestActions.ts`

entityType = `'hours_of_rest'`. Compliance entity — export action. Validates `'compliance'` cluster in the shell bar.

Page shell:
```typescript
<EntityLensPage entityType="hours_of_rest" entityId={params.id as string} content={HoursOfRestLensContent} />
```

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
- [ ] **Commit**
```bash
git add apps/web/src/components/lens/HoursOfRestLensContent.tsx apps/web/src/app/hours-of-rest/[id]/page.tsx
git rm apps/web/src/hooks/useHoursOfRestActions.ts
git commit -m "feat(frontend): migrate hours_of_rest to useEntityLens — delete useHoursOfRestActions"
```

---

### Task 16: Migrate purchase_order

**Files:**
- Modify: `apps/web/src/components/lens/PurchaseOrderLensContent.tsx`
- Modify: `apps/web/src/app/purchasing/[id]/page.tsx`

entityType = `'purchase_order'`. No dedicated hook. Note: Phase 2 `ENTITY_TYPE_TO_DOMAIN['purchase_order']` maps to `None` domain — `available_actions` returns `[]`. The shell action bar will be empty. This is correct behaviour — purchasing has no p0 actions yet.

Page shell:
```typescript
<EntityLensPage entityType="purchase_order" entityId={params.id as string} content={PurchaseOrderLensContent} />
```

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
- [ ] **Commit**
```bash
git add apps/web/src/components/lens/PurchaseOrderLensContent.tsx apps/web/src/app/purchasing/[id]/page.tsx
git commit -m "feat(frontend): migrate purchase_order to useEntityLens"
```

---

### Task 17: Migrate handover_export

**Files:**
- Modify: `apps/web/src/components/lens/HandoverExportLensContent.tsx`
- Modify: `apps/web/src/app/handover-export/[id]/page.tsx`
- Delete: `apps/web/src/hooks/useHandoverActions.ts`

entityType = `'handover_export'`. Note: Phase 2 `ENTITY_TYPE_TO_DOMAIN['handover_export']` maps to `None` domain — `available_actions` returns `[]`. The `HandoverExportLensContent` has its own signature canvas (`handover-export-sections/SignatureCanvas.tsx`) — this is the handover-specific sign-off flow, distinct from the p0 signature modal. Do NOT wire it through `safeExecute`. Keep the existing `SignatureCanvas` component usage as-is — it calls its own dedicated API route (`/api/handover-export/[id]/submit`), not the p0 action router.

Page shell:
```typescript
<EntityLensPage entityType="handover_export" entityId={params.id as string} content={HandoverExportLensContent} />
```

- [ ] **Verify SignatureCanvas is NOT wired through executeAction (spec requirement)**

The `HandoverExportLensContent` has its own signature flow via `SignatureCanvas` → `/api/handover-export/[id]/submit`. This must remain independent of the p0 action router. After migration, confirm zero calls to `executeAction` in this component for the signature path:

```bash
grep -n "safeExecute\|executeAction" apps/web/src/components/lens/HandoverExportLensContent.tsx
```

Expected: zero results, OR only calls for non-signature p0 actions (e.g. `export_handover`). Any line calling `executeAction` with a signature-related action name (countersign, submit, sign) is a bug — revert and fix.

- [ ] **Typecheck**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler\|useEntityActions"
```
- [ ] **Run unit tests**
```bash
cd apps/web && npx vitest run
```
- [ ] **Commit**
```bash
git add apps/web/src/components/lens/HandoverExportLensContent.tsx apps/web/src/app/handover-export/[id]/page.tsx
git rm apps/web/src/hooks/useHandoverActions.ts
git commit -m "feat(frontend): migrate handover_export to useEntityLens — delete useHandoverActions"
```

---

### Task 18: Final cleanup — delete useEntityActions.ts and useActionHandler.ts

**Files:**
- Delete: `apps/web/src/hooks/useEntityActions.ts`
- Delete: `apps/web/src/hooks/useActionHandler.ts`

Both files depend on `MicroAction`, `ACTION_REGISTRY`, and `canPerformAction` from `types/actions.ts` — all of which were deleted in Task 5. All per-entity hooks have been deleted in Tasks 6–17. These two files are now orphaned.

- [ ] **Step 1: Verify nothing still imports these hooks**

```bash
cd apps/web && grep -r "useEntityActions\|useActionHandler" src --include="*.ts" --include="*.tsx"
```

Expected: no results. If any file still imports them, fix that file first.

- [ ] **Step 2: Delete the files**

```bash
rm apps/web/src/hooks/useEntityActions.ts
rm apps/web/src/hooks/useActionHandler.ts
```

- [ ] **Step 3: Full typecheck — no exceptions this time**

```bash
cd apps/web && npx tsc --noEmit 2>&1
```

Expected: 0 errors. Any remaining errors must be fixed before committing.

- [ ] **Step 4: Run all unit tests**

```bash
cd apps/web && npx vitest run
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git rm apps/web/src/hooks/useEntityActions.ts
git rm apps/web/src/hooks/useActionHandler.ts
git commit -m "chore(frontend): delete useEntityActions and useActionHandler — replaced by useEntityLens + EntityLensContext"
```

---

## Verification Checklist

After Task 18, verify the complete Phase 3 result:

```bash
# 1. No frontend role arrays remain
cd apps/web && grep -r "HOD_ROLES\|CLOSE_ROLES\|role_restricted\|canPerformAction" src
# Expected: 0 results

# 2. No per-entity action hooks remain
cd apps/web && ls src/hooks/use*Actions.ts 2>/dev/null
# Expected: no files

# 3. TypeScript clean
cd apps/web && npx tsc --noEmit
# Expected: 0 errors

# 4. All unit tests pass
cd apps/web && npx vitest run
# Expected: all pass

# 5. All 12 pages now use EntityLensPage
cd apps/web && grep -l "EntityLensPage" src/app/*/\[id\]/page.tsx src/app/*/*/\[id\]/page.tsx 2>/dev/null | wc -l
# Expected: 12
```
