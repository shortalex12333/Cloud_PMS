# Show Related — Frontend Implementation Spec

> **Audience:** New engineer assigned to build the Show Related feature end-to-end.
> **Read first:** `docs/SHOW_RELATED_BACKEND.md` — covers the API contract, response shapes,
> security model, and all known gaps. This document covers the frontend only.
> **Do not read:** `context_nav/related_expansion.py`, `RelatedPanel.tsx`, `AddRelatedModal.tsx` —
> these are legacy and will be removed. The new implementation does not use them.

---

## 1. What Already Exists — Do Not Rebuild

| File | Status | Notes |
|------|--------|-------|
| `src/components/context-nav/RelatedPanel.tsx` | **LEGACY — do not use** | Wired to `NavigationContext` and the dead `related_expansion.py` backend |
| `src/components/context-nav/AddRelatedModal.tsx` | **LEGACY — do not use** | Calls `addUserRelation` from old api-client, wrong auth pattern |
| `src/components/lens/sections/RelatedEntitiesSection.tsx` | **Active — keep as-is** | Inline display of entities embedded in entity-detail response. Not the same feature. |
| `src/components/layout/RouteLayout.tsx` | **Active — use this** | Has `primaryPanel` prop: 480px right-side panel, slide-in animation, close button, already wired |
| `src/hooks/useAuth.ts` | **Active — use this** | Provides `session.access_token` for Bearer auth |

The existing `RelatedEntitiesSection` shows entities that the entity-detail endpoint returns
directly embedded in its JSON response. The Show Related feature is different: it calls a
**separate endpoint** (`GET /v1/related`) which runs FK traversal and explicit-link lookup
specifically for this purpose. Both can coexist; they serve different UX needs.

---

## 2. Feature Description

A **Show Related** button appears in the top-right corner of every `[id]` lens page
(e.g. `/work-orders/[id]`, `/faults/[id]`). Clicking it slides open a 480px right-hand
panel — via `RouteLayout.primaryPanel` — that renders the full related-entity graph for
the current record.

The panel shows:
- Related entities grouped by domain (equipment, faults, previous work orders, parts, manuals, attachments)
- Each item is a clickable link that navigates to that entity's lens page
- An "Add Related" button at the bottom (HOD/manager role only) that allows explicit manual linking

The button and panel are entirely self-contained — no global state, no context provider.

---

## 3. Files to Create

```
apps/web/src/
  hooks/
    useRelated.ts                         ← API hook (the core)
  components/lens/
    ShowRelatedButton.tsx                 ← Button for topNavContent
    RelatedDrawer.tsx                     ← Panel content
    AddRelatedItemModal.tsx               ← Modal for POST /v1/related/add (HOD only)
```

Four existing lens pages need a ~15-line modification each:
```
apps/web/src/app/
  work-orders/[id]/page.tsx              ← Add button + panel wiring
  faults/[id]/page.tsx                   ← Add button + panel wiring
  equipment/[id]/page.tsx                ← Add button + panel wiring
  inventory/[id]/page.tsx                ← Add button + panel wiring
```

---

## 4. The `useRelated` Hook

**File:** `src/hooks/useRelated.ts`

This is the most important piece. Wire it to TanStack Query (already in the project).

```typescript
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';

// ─── Types (mirrors backend RelatedItem + RelatedGroup shapes) ────────────────

export interface RelatedItem {
  entity_type: string;     // "work_order" | "equipment" | "fault" | "part" | "manual" | "attachment" | "handover"
  entity_id: string;       // UUID
  label: string;           // display name — always present
  subtitle?: string | null; // secondary info (e.g. WO number, equipment name)
  weight: number;          // 100 | 90 | 80 | 70 — already sorted by backend
  link_type: string;       // "fk" (FK-derived) | "related" | "reference" | "evidence" | "manual" (explicit)
}

export interface RelatedGroup {
  group_key: string;       // "equipment" | "faults" | "previous_work" | "parts" | "manuals" | "attachments" | "handovers"
  items: RelatedItem[];
}

export interface RelatedResponse {
  entity_type: string;
  entity_id: string;
  groups: RelatedGroup[];
}

// ─── Fetch function ───────────────────────────────────────────────────────────

async function fetchRelated(
  entityType: string,
  entityId: string,
  token: string
): Promise<RelatedResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const url = new URL(`${baseUrl}/v1/related`);
  url.searchParams.set('entity_type', entityType);
  url.searchParams.set('entity_id', entityId);

  const response = await fetch(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`GET /v1/related failed: ${response.status}`);
  }

  return response.json();
}

// ─── Add relation (HOD/manager only) ─────────────────────────────────────────

interface AddRelatedPayload {
  from_entity_type: string;
  from_entity_id: string;
  to_entity_type: string;
  to_entity_id: string;
  link_type: 'related' | 'reference' | 'evidence' | 'manual'; // NOT "explicit" — that's a backend bug (GAP-01)
  notes?: string;
}

async function postAddRelated(
  payload: AddRelatedPayload,
  token: string
): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/related/add`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`POST /v1/related/add failed: ${response.status} — ${err}`);
  }
}

// ─── Hook: read related entities ─────────────────────────────────────────────

export function useRelated(entityType: string, entityId: string) {
  const { session } = useAuth();
  const token = session?.access_token;

  return useQuery<RelatedResponse>({
    queryKey: ['related', entityType, entityId],
    queryFn: () => fetchRelated(entityType, entityId, token!),
    enabled: !!token && !!entityId && SUPPORTED_ENTITY_TYPES.includes(entityType),
    staleTime: 60_000,   // 60s — related data changes infrequently
    retry: 1,
  });
}

// ─── Hook: add explicit relation ──────────────────────────────────────────────

export function useAddRelated(entityType: string, entityId: string) {
  const { session } = useAuth();
  const token = session?.access_token;
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AddRelatedPayload) => postAddRelated(payload, token!),
    onSuccess: () => {
      // Invalidate so the panel refreshes immediately
      queryClient.invalidateQueries({ queryKey: ['related', entityType, entityId] });
    },
  });
}

// ─── Constants ────────────────────────────────────────────────────────────────

// Entity types the backend supports. Pages for other entity types should not
// show the Show Related button until the backend adds FK traversal.
// See SHOW_RELATED_BACKEND.md §11 GAP-03 for details.
export const SUPPORTED_ENTITY_TYPES = ['work_order', 'fault', 'equipment', 'part'] as const;

// Fixed display order for groups — do not reorder dynamically
export const GROUP_DISPLAY_ORDER = [
  'equipment',
  'faults',
  'previous_work',
  'parts',
  'manuals',
  'attachments',
  'handovers',
] as const;

// Human-readable labels for each group key
export const GROUP_LABELS: Record<string, string> = {
  equipment:     'Equipment',
  faults:        'Faults',
  previous_work: 'Previous Work Orders',
  parts:         'Parts',
  manuals:       'Manuals',
  attachments:   'Attachments',
  handovers:     'Handovers',
};
```

**Critical:** Do not disable the query just because `data` might be empty. An empty `groups: []`
is a valid response (entity exists but has no relations yet). The panel should render an
"No related items found" empty state rather than never fetching.

---

## 5. Entity Type Mapping

Each lens page must tell `useRelated` the correct backend entity type string.

| Lens Page | URL Pattern | `entityType` to pass |
|-----------|-------------|----------------------|
| Work Orders | `/work-orders/[id]` | `"work_order"` |
| Faults | `/faults/[id]` | `"fault"` |
| Equipment | `/equipment/[id]` | `"equipment"` |
| Inventory | `/inventory/[id]` | `"part"` |

**Pages not yet supported** — do NOT show the button on these until the backend adds
FK traversal (see `SHOW_RELATED_BACKEND.md` §11 GAP-03):

| Lens Page | Reason |
|-----------|--------|
| `/documents/[id]` | `attachment` has no FK traversal in `related_handlers.py` |
| `/certificates/[id]` | `certificate` not in `VALID_ENTITY_TYPES` at all |
| `/shopping-list/[id]` | not in `VALID_ENTITY_TYPES` |
| `/receiving/[id]` | not in `VALID_ENTITY_TYPES` |
| `/purchasing/[id]` | not in `VALID_ENTITY_TYPES` |
| `/hours-of-rest/[id]` | not in `VALID_ENTITY_TYPES` |
| `/warranties/[id]` | not in `VALID_ENTITY_TYPES` |

When the backend team adds traversal for a new entity type, add that entity to
`SUPPORTED_ENTITY_TYPES` in `useRelated.ts` and wire the corresponding lens page.

---

## 6. The `ShowRelatedButton` Component

**File:** `src/components/lens/ShowRelatedButton.tsx`

Small self-contained button. Goes into `topNavContent` on the right side of the `TopNav`.

```typescript
'use client';

import * as React from 'react';

interface ShowRelatedButtonProps {
  onClick: () => void;
  isOpen: boolean;
  count?: number;   // total related items — shown as badge when > 0
  isLoading?: boolean;
}

export function ShowRelatedButton({ onClick, isOpen, count, isLoading }: ShowRelatedButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={isOpen ? 'Close related panel' : 'Show related'}
      aria-expanded={isOpen}
      data-testid="show-related-button"
      className={[
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
        isOpen
          ? 'bg-surface-elevated text-txt-primary'
          : 'hover:bg-surface-hover text-txt-secondary hover:text-txt-primary',
      ].join(' ')}
    >
      {/* Network/link icon */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
      </svg>
      <span>Related</span>
      {!isLoading && count != null && count > 0 && (
        <span className="px-1.5 py-0.5 bg-accent-primary/20 text-accent-primary rounded text-xs font-medium">
          {count}
        </span>
      )}
      {isLoading && (
        <span className="w-3 h-3 border border-txt-tertiary border-t-txt-secondary rounded-full animate-spin" />
      )}
    </button>
  );
}
```

The button is placed in `topNavContent` on the **right side** of the `TopNav`. The `TopNav`
uses `justify-between` — the existing back-button + title lives on the left. Add a `<div>`
on the right to hold the `ShowRelatedButton`.

---

## 7. The `RelatedDrawer` Component

**File:** `src/components/lens/RelatedDrawer.tsx`

This is the content for `RouteLayout.primaryPanel.children`. It receives the data from
`useRelated` and renders it. Keep this component "dumb" — all data fetching happens in
the parent page via `useRelated`.

```typescript
'use client';

import * as React from 'react';
import { GROUP_DISPLAY_ORDER, GROUP_LABELS } from '@/hooks/useRelated';
import type { RelatedGroup, RelatedItem } from '@/hooks/useRelated';

interface RelatedDrawerProps {
  groups: RelatedGroup[];
  isLoading: boolean;
  error?: Error | null;
  onNavigate: (entityType: string, entityId: string) => void;
  /** Render add-related button (HOD/manager only — caller decides visibility) */
  onAddRelated?: () => void;
}

export function RelatedDrawer({
  groups,
  isLoading,
  error,
  onNavigate,
  onAddRelated,
}: RelatedDrawerProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
          <p className="text-xs text-txt-tertiary">Loading related...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-status-critical mb-2">Failed to load related items</p>
        <p className="text-xs text-txt-tertiary">{error.message}</p>
      </div>
    );
  }

  // Flatten to count total items (for empty state)
  const totalItems = groups.reduce((sum, g) => sum + g.items.length, 0);

  if (totalItems === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-txt-secondary mb-4">No related items found.</p>
        {onAddRelated && (
          <button
            onClick={onAddRelated}
            className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
          >
            Add Related
          </button>
        )}
      </div>
    );
  }

  // Sort groups by fixed display order; groups not in the order list go last
  const orderedGroups = [...groups].sort((a, b) => {
    const ai = GROUP_DISPLAY_ORDER.indexOf(a.group_key as any);
    const bi = GROUP_DISPLAY_ORDER.indexOf(b.group_key as any);
    if (ai === -1 && bi === -1) return 0;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  return (
    <div className="p-4 space-y-6">
      {orderedGroups.map((group) => (
        <RelatedGroup key={group.group_key} group={group} onNavigate={onNavigate} />
      ))}

      {onAddRelated && (
        <div className="pt-4 border-t border-border-subtle">
          <button
            onClick={onAddRelated}
            className="w-full px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors text-left"
          >
            + Add Explicit Link
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Group section ────────────────────────────────────────────────────────────

function RelatedGroup({
  group,
  onNavigate,
}: {
  group: RelatedGroup;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const label = GROUP_LABELS[group.group_key] ?? group.group_key.replace(/_/g, ' ');

  return (
    <section>
      <h3 className="text-xs font-medium text-txt-tertiary uppercase tracking-wider mb-2">
        {label}
        <span className="ml-2 text-txt-muted font-normal">{group.items.length}</span>
      </h3>
      <ul className="space-y-1">
        {group.items.map((item) => (
          <RelatedItem key={item.entity_id} item={item} onNavigate={onNavigate} />
        ))}
      </ul>
    </section>
  );
}

// ─── Individual item row ──────────────────────────────────────────────────────

function RelatedItem({
  item,
  onNavigate,
}: {
  item: RelatedItem;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onNavigate(item.entity_type, item.entity_id)}
        data-testid={`related-item-${item.entity_type}-${item.entity_id}`}
        className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors group"
      >
        <span className="block text-sm text-txt-primary group-hover:text-accent-primary truncate">
          {item.label}
        </span>
        {item.subtitle && (
          <span className="block text-xs text-txt-tertiary truncate mt-0.5">
            {item.subtitle}
          </span>
        )}
      </button>
    </li>
  );
}
```

---

## 8. The `AddRelatedItemModal` Component

**File:** `src/components/lens/AddRelatedItemModal.tsx`

Shown only to HOD/managers (backend enforces this too — returns 403 otherwise).
The caller decides whether to show the "Add Related" button based on user role.

```typescript
'use client';

import * as React from 'react';
import { useAddRelated } from '@/hooks/useRelated';
import { SUPPORTED_ENTITY_TYPES } from '@/hooks/useRelated';

const LINK_TYPES = [
  { value: 'related',   label: 'Related' },
  { value: 'reference', label: 'Reference' },
  { value: 'evidence',  label: 'Evidence' },
  { value: 'manual',    label: 'Manual Link' },
  // NOTE: "explicit" is intentionally NOT in this list — it's a schema bug (GAP-01).
  // The backend VALID_LINK_TYPES does not include "explicit" despite it being the
  // schema default. Using it will return 400. Track fix in SHOW_RELATED_BACKEND.md.
] as const;

interface AddRelatedItemModalProps {
  fromEntityType: string;
  fromEntityId: string;
  onClose: () => void;
}

export function AddRelatedItemModal({
  fromEntityType,
  fromEntityId,
  onClose,
}: AddRelatedItemModalProps) {
  const [toEntityType, setToEntityType] = React.useState('');
  const [toEntityId, setToEntityId] = React.useState('');
  const [linkType, setLinkType] = React.useState<'related' | 'reference' | 'evidence' | 'manual'>('related');

  const { mutate, isPending, error } = useAddRelated(fromEntityType, fromEntityId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(
      {
        from_entity_type: fromEntityType,
        from_entity_id: fromEntityId,
        to_entity_type: toEntityType,
        to_entity_id: toEntityId,
        link_type: linkType,
      },
      { onSuccess: onClose }
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface-elevated rounded-xl p-6 max-w-md w-full mx-4 border border-border-subtle"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-txt-primary mb-4">Add Explicit Link</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Link to Entity Type
            </label>
            <select
              value={toEntityType}
              onChange={(e) => setToEntityType(e.target.value)}
              required
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary"
            >
              <option value="">Select type…</option>
              {SUPPORTED_ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Entity ID (UUID)
            </label>
            <input
              type="text"
              value={toEntityId}
              onChange={(e) => setToEntityId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              required
              pattern="[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary font-mono"
            />
          </div>

          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Link Type
            </label>
            <select
              value={linkType}
              onChange={(e) => setLinkType(e.target.value as typeof linkType)}
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary"
            >
              {LINK_TYPES.map((lt) => (
                <option key={lt.value} value={lt.value}>{lt.label}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-status-critical">{(error as Error).message}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="flex-1 px-4 py-2 bg-surface-base hover:bg-surface-hover border border-border-subtle rounded-lg text-sm text-txt-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !toEntityType || !toEntityId}
              className="flex-1 px-4 py-2 bg-accent-primary hover:bg-accent-primary-hover rounded-lg text-sm text-white font-medium transition-colors disabled:opacity-50"
            >
              {isPending ? 'Adding…' : 'Add Link'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

---

## 9. Wiring Into a Lens Page

**Pattern — shown for `work-orders/[id]/page.tsx`. Apply identically to faults, equipment, inventory.**

### 9a. Add state and hooks

In the `WorkOrderDetailPageContent` function (the component that wraps `RouteLayout`), add:

```typescript
import { useRelated, SUPPORTED_ENTITY_TYPES } from '@/hooks/useRelated';
import { ShowRelatedButton } from '@/components/lens/ShowRelatedButton';
import { RelatedDrawer } from '@/components/lens/RelatedDrawer';
import { AddRelatedItemModal } from '@/components/lens/AddRelatedItemModal';
import { isHOD } from '@/contexts/AuthContext';  // already in codebase

// Inside WorkOrderDetailPageContent:
const { user } = useAuth();           // already uses session — extend to include user
const [relatedOpen, setRelatedOpen] = React.useState(false);
const [showAddModal, setShowAddModal] = React.useState(false);
const canAddRelated = isHOD(user);    // HOD/manager only

const {
  data: relatedData,
  isLoading: relatedLoading,
  error: relatedError,
} = useRelated('work_order', workOrderId);

const totalRelated = relatedData?.groups.reduce((sum, g) => sum + g.items.length, 0) ?? 0;
```

### 9b. Modify `topNavContent`

The current `topNavContent` has a flex row with back-button + title on the left.
Add a right-side div:

```typescript
topNavContent={
  <div className="flex items-center justify-between w-full">
    {/* LEFT — existing back button + title */}
    <div className="flex items-center gap-4">
      <button onClick={handleBack} ...>
        {/* existing chevron SVG */}
      </button>
      <div>
        <p className="text-xs text-txt-tertiary uppercase tracking-wider">Work Orders</p>
        <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
          {title}
        </h1>
      </div>
    </div>

    {/* RIGHT — Show Related button */}
    <ShowRelatedButton
      onClick={() => setRelatedOpen((open) => !open)}
      isOpen={relatedOpen}
      count={totalRelated}
      isLoading={relatedLoading}
    />
  </div>
}
```

### 9c. Add `primaryPanel` prop to `RouteLayout`

```typescript
<RouteLayout
  pageTitle={title}
  showTopNav={true}
  topNavContent={/* ... */}
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
  {content}
</RouteLayout>
```

### 9d. Render `AddRelatedItemModal` outside `RouteLayout`

```typescript
return (
  <main role="main" data-testid="work-order-detail">
    <RouteLayout ...>
      {content}
    </RouteLayout>

    {showAddModal && (
      <AddRelatedItemModal
        fromEntityType="work_order"
        fromEntityId={workOrderId}
        onClose={() => setShowAddModal(false)}
      />
    )}
  </main>
);
```

### 9e. Entity type strings for each page

| Page file | `useRelated` first arg | `fromEntityType` in modal |
|-----------|------------------------|---------------------------|
| `work-orders/[id]/page.tsx` | `'work_order'` | `'work_order'` |
| `faults/[id]/page.tsx` | `'fault'` | `'fault'` |
| `equipment/[id]/page.tsx` | `'equipment'` | `'equipment'` |
| `inventory/[id]/page.tsx` | `'part'` | `'part'` |

---

## 10. Navigation from the Drawer

The `onNavigate` callback from each page's `handleNavigate` already routes correctly via
`getEntityRoute` from `@/lib/featureFlags`. Pass it directly:

```typescript
onNavigate={handleNavigate}
```

`getEntityRoute` maps `'work_order'` → `/work-orders/{id}`, `'fault'` → `/faults/{id}`, etc.
Verify this mapping covers all entity types the backend can return. If `'manual'`,
`'attachment'`, or `'handover'` are not yet in `getEntityRoute`, add them:

- `'manual'` → `/documents/{id}`
- `'attachment'` → `/documents/{id}`
- `'handover'` → `/handover-export/{id}` (if that's the right destination — confirm with product)

---

## 11. Role Check for "Add Related"

The `isHOD` function is already imported in `useReceivingActions.ts` and `useFaultActions.ts`.
Pattern:

```typescript
import { isHOD } from '@/contexts/AuthContext';
const canAddRelated = isHOD(user);
```

The backend will also return 403 if a non-HOD tries to POST `/v1/related/add`.
The frontend role check is a UX affordance only — the security is enforced server-side.

---

## 12. Known Gaps to Not Work Around

These are documented in `SHOW_RELATED_BACKEND.md §11`. Do not implement frontend workarounds.
The engineer should log these as follow-up tickets:

| Gap | What it means for frontend |
|-----|---------------------------|
| **GAP-01** `link_type: "explicit"` default | `AddRelatedItemModal` already avoids this — never set `link_type` to `"explicit"` |
| **GAP-02** FK lookup is one-directional | Backend will return A→B but not B→A from explicit links. Results may look sparse. Expected. |
| **GAP-04** Shadow logger disabled | Not relevant to frontend |
| **GAP-05** No pagination | If a group has 100 items, all 100 render. Add a "Show more" cap at 10 items per group with an expand toggle if the UX feels overwhelming |
| **GAP-06** Part/manual/attachment have no FK traversal | `useRelated` query is disabled for unsupported entity types. No button shown. |
| **GAP-07** `related_text` not used in search | Not relevant to frontend |
| **GAP-08** `handover` entity type string conflict | If backend returns `entity_type: "handover"` and `getEntityRoute` doesn't handle it, log it — do not silently swallow |

---

## 13. Testing Checklist

Before considering this done, verify each item manually or with a Playwright test:

### Button
- [ ] Button appears in top-right of `/work-orders/{id}` page
- [ ] Button does NOT appear on list pages (`/work-orders`)
- [ ] Button shows count badge when related items exist
- [ ] Button shows spinner while `useRelated` query is in flight
- [ ] Clicking button toggles panel open/closed
- [ ] `aria-expanded` attribute updates correctly

### Panel
- [ ] Panel slides in from right at 480px width (RouteLayout `primaryPanel` handles this)
- [ ] Panel shows loading spinner during first fetch
- [ ] Panel shows error state if API returns 500
- [ ] Panel shows empty state if `groups: []`
- [ ] Groups render in fixed order: Equipment → Faults → Previous Work → Parts → Manuals → Attachments → Handovers
- [ ] Clicking an item navigates to the correct lens page
- [ ] Close button (in panel header, provided by RouteLayout) dismisses the panel

### Role-gated "Add Related"
- [ ] "Add Related" button is visible when user is HOD/manager
- [ ] "Add Related" button is NOT visible when user is crew
- [ ] Submitting `AddRelatedItemModal` calls `POST /v1/related/add`
- [ ] After success, panel refreshes (TanStack Query invalidation)
- [ ] Submitting with `link_type: "explicit"` is impossible (not in dropdown)

### All four lens pages
- [ ] Work Orders `/work-orders/{id}` ✓
- [ ] Faults `/faults/{id}` ✓
- [ ] Equipment `/equipment/{id}` ✓
- [ ] Inventory `/inventory/{id}` ✓

---

## 14. Files Modified Summary

| File | Change |
|------|--------|
| `src/hooks/useRelated.ts` | **New** — query + mutation hooks |
| `src/components/lens/ShowRelatedButton.tsx` | **New** — button component |
| `src/components/lens/RelatedDrawer.tsx` | **New** — panel content |
| `src/components/lens/AddRelatedItemModal.tsx` | **New** — HOD-only modal |
| `src/app/work-orders/[id]/page.tsx` | **Modified** — add hooks, button, primaryPanel prop |
| `src/app/faults/[id]/page.tsx` | **Modified** — same pattern |
| `src/app/equipment/[id]/page.tsx` | **Modified** — same pattern |
| `src/app/inventory/[id]/page.tsx` | **Modified** — same pattern |

**Do not modify** `RelatedPanel.tsx`, `AddRelatedModal.tsx`, `RelatedEntitiesSection.tsx`,
or `RouteLayout.tsx`.
