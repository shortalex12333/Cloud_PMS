# Action Prefill Hardening Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix shell bar silent API failures for actions with unresolved required fields, and extend ActionModal to use backend prefill when available.

**Architecture:** Three targeted changes. No new files. No new UI components. Content components already handle complex (user-input) actions inline — the shell bar should only show one-click-safe actions.

**Tech Stack:** TypeScript, React, Next.js.

---

## Context

### Two sources of prefill

| Source | Where used | What it resolves |
|--------|-----------|-----------------|
| `AvailableAction.prefill` (backend vlookup) | Entity lens — `useEntityLens.executeAction` merges it | Entity IDs, entity-derived values (title from equipment name, etc.) |
| `query` (spotlight search text) | `ActionModal` initializer | Narrative fields: title, description, note_text, text, comment etc. |

### Shell bar gap — silent failures

`EntityLensPage` shell bar calls `safeExecute(action.action_id)` with no payload. `useEntityLens.executeAction` merges `action.prefill`, but some shell bar actions have required fields NOT covered by prefill:

| Action | Required but not in prefill | Result |
|--------|---------------------------|--------|
| `archive_work_order` | `deletion_reason`, `signature` | Backend 422 |
| `reassign_work_order` | `assignee_id`, `reason` | Backend 422 |
| `report_fault` | `title`, `description` | Backend 422 |
| `decommission_equipment` | `reason` | Backend 422 |
| `create_work_order_for_equipment` | `type`, `priority` | Backend 422 |

Content components already have inline forms for all these actions. The fix: filter the shell bar to only show actions where all required fields are either backend-auto (yacht_id, signature, idempotency_key) or resolved by prefill.

### ActionModal prefill gap

`ActionModal` formData initializer seeds from `query` but ignores `action.prefill`. When ActionModal is opened with an `AvailableAction` (entity context, prefill resolved), entity-derived values won't appear. Fix: layer `action.prefill` on top of query seed (entity data takes priority — it's more precise than free text).

---

## File structure

| File | Change |
|------|--------|
| `apps/web/src/components/lens/EntityLensPage.tsx` | Add `hasUnresolvedFields` filter to shell bar |
| `apps/web/src/lib/actionClient.ts` | Add `prefill?: Record<string, unknown>` to `ActionSuggestion` |
| `apps/web/src/components/actions/ActionModal.tsx` | Layer `action.prefill` seed in formData initializer |

---

## Task 1: Filter shell bar to one-click-safe actions

**Files:**
- Modify: `apps/web/src/components/lens/EntityLensPage.tsx`

**Goal:** Only show shell bar button if all required fields are either BACKEND_AUTO or in `action.prefill`.

### Steps

- [ ] **Read the file** — specifically lines 191-195 (shellActions filter) and the imports section.

- [ ] **Add BACKEND_AUTO constant and hasUnresolvedFields helper** after the `SHELL_CLUSTERS` definition (around line 20):

```tsx
// Fields handled automatically — never require user input in the form
const BACKEND_AUTO = new Set(['yacht_id', 'signature', 'idempotency_key']);

/**
 * Returns true if the action has required fields that are not covered by
 * BACKEND_AUTO or action.prefill — meaning a form is needed to execute it.
 * Such actions must NOT appear in the shell bar (content component handles them inline).
 */
function hasUnresolvedFields(action: AvailableAction): boolean {
  return action.required_fields.some(
    (f) => !BACKEND_AUTO.has(f) && !(f in action.prefill)
  );
}
```

- [ ] **Update the shellActions filter** (around line 192):

Current:
```tsx
  const shellActions = lens.availableActions.filter((a) => {
    const { cluster } = getActionDisplay(a.action_id);
    return SHELL_CLUSTERS.has(cluster);
  });
```

New:
```tsx
  const shellActions = lens.availableActions.filter((a) => {
    const { cluster } = getActionDisplay(a.action_id);
    return SHELL_CLUSTERS.has(cluster) && !hasUnresolvedFields(a);
  });
```

- [ ] **TypeScript check:**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler" | grep "EntityLensPage" | head -10
```

Expected: no errors.

- [ ] **Verify logic with known actions:**

`start_work_order` required: `[yacht_id, work_order_id]` — prefill has `work_order_id`, yacht_id is BACKEND_AUTO → `hasUnresolvedFields` = false → shown ✅
`archive_work_order` required: `[yacht_id, work_order_id, deletion_reason, signature]` — prefill has `work_order_id`, yacht_id/signature BACKEND_AUTO, but `deletion_reason` not in prefill → `hasUnresolvedFields` = true → hidden ✅

- [ ] **Commit:**
```bash
git add apps/web/src/components/lens/EntityLensPage.tsx
git commit -m "fix: filter shell bar to one-click-safe actions only (prevent silent API failures)"
```

---

## Task 2: Add `prefill` to `ActionSuggestion` type

**Files:**
- Modify: `apps/web/src/lib/actionClient.ts`

**Goal:** `ActionSuggestion` (spotlight type) gains optional `prefill` field so `ActionModal` can use it generically when entity prefill is eventually available in this path.

### Steps

- [ ] **Read the `ActionSuggestion` interface** (lines 30-44).

- [ ] **Add `prefill?: Record<string, unknown>` field:**

Current:
```tsx
export interface ActionSuggestion {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'SIGNED';
  allowed_roles: string[];
  required_fields: string[];
  domain: string | null;
  match_score: number;
  storage_options?: {
    bucket: string;
    path_preview: string;
    writable_prefixes: string[];
    confirmation_required: boolean;
  };
}
```

New (add `prefill` before `storage_options`):
```tsx
export interface ActionSuggestion {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'SIGNED';
  allowed_roles: string[];
  required_fields: string[];
  domain: string | null;
  match_score: number;
  prefill?: Record<string, unknown>;
  storage_options?: {
    bucket: string;
    path_preview: string;
    writable_prefixes: string[];
    confirmation_required: boolean;
  };
}
```

- [ ] **TypeScript check:**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler" | head -10
```

Expected: no errors.

- [ ] **Commit:**
```bash
git add apps/web/src/lib/actionClient.ts
git commit -m "feat: add optional prefill field to ActionSuggestion interface"
```

---

## Task 3: Layer `action.prefill` into `ActionModal` formData seed

**Files:**
- Modify: `apps/web/src/components/actions/ActionModal.tsx`

**Goal:** When `action.prefill` contains values (entity-resolved), use them in formData. Entity data takes priority over query text — it's more precise.

Order of priority (highest to lowest):
1. `action.prefill` values (backend-resolved entity data)
2. `query` text for narrative fields NOT already covered by prefill

### Steps

- [ ] **Read the `useState` initializer** (lines 76-91).

Current:
```tsx
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const trimmedQuery = query?.trim() ?? '';
    if (!trimmedQuery) return {};
    const seed: Record<string, string> = {};
    const isNarrativeField = (name: string) =>
      inferFieldType(name) === 'textarea' ||
      name === 'title' ||
      name === 'content' ||
      name === 'summary' ||
      name === 'text' ||
      name === 'comment' ||
      name === 'hod_justification';
    for (const field of action.required_fields) {
      if (isNarrativeField(field)) {
        seed[field] = trimmedQuery;
      }
    }
    return seed;
  });
```

New — query seeds first, then prefill overwrites (entity data is more precise than free text):
```tsx
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const seed: Record<string, string> = {};

    // Layer 1: query text for narrative fields (best-effort from search intent)
    const trimmedQuery = query?.trim() ?? '';
    if (trimmedQuery) {
      const isNarrativeField = (name: string) =>
        inferFieldType(name) === 'textarea' ||
        name === 'title' ||
        name === 'content' ||
        name === 'summary' ||
        name === 'text' ||
        name === 'comment' ||
        name === 'hod_justification';
      for (const field of action.required_fields) {
        if (isNarrativeField(field)) {
          seed[field] = trimmedQuery;
        }
      }
    }

    // Layer 2: backend prefill overwrites query seed (entity-resolved values are precise)
    if (action.prefill) {
      for (const [field, value] of Object.entries(action.prefill)) {
        if (value != null && value !== '') {
          seed[field] = typeof value === 'string' ? value : String(value);
        }
      }
    }

    return seed;
  });
```

- [ ] **TypeScript check:**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler" | grep "ActionModal" | head -10
```

Expected: no errors. `action.prefill` is now `Record<string, unknown> | undefined` from the updated `ActionSuggestion` type — the `if (action.prefill)` guard handles the undefined case.

- [ ] **Commit:**
```bash
git add apps/web/src/components/actions/ActionModal.tsx
git commit -m "feat: layer backend prefill over query seed in ActionModal formData (entity data takes priority)"
```

---

## Verification

After all 3 tasks:

**Shell bar:**
1. On a Work Order page → shell bar shows `Start`, `Close`, `Cancel` buttons ✅
2. Shell bar does NOT show `Archive` (needs deletion_reason) or `Reassign` (needs assignee_id) ✅ — those appear only in the content component's inline form
3. Clicking a shell bar button executes immediately without error ✅

**ActionModal prefill priority:**
1. Spotlight: search "Engine overheating", click "Add Fault" → title pre-filled with query text ✅
2. (Future path) Entity lens opens ActionModal with equipment entity → title field shows equipment canonical_label (from prefill), overriding any query text ✅

**TypeScript:**
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler"
```
Expected: no errors.
