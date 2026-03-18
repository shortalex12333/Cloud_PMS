# Action Form Query Pre-fill Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-populate `ActionModal` form fields with the original spotlight search query so users don't have to retype their intent when executing a suggested action.

**Architecture:** Three files, no new abstractions. The query flows as a prop: `SpotlightSearch` → `SuggestedActions` → `ActionModal`. `ActionModal` seeds `formData` initial state with the query for "narrative" fields (text/textarea whose names suggest user-authored content, not IDs or numbers). The entity lens path (EntityLensPage shell bar) already handles backend-resolved `prefill` inside `useEntityLens.executeAction` — no changes needed there.

**Tech Stack:** React `useState` lazy initializer, TypeScript prop widening.

---

## Context

### Two action invocation paths — only spotlight is affected

| Path | Prefill source | Status |
|------|---------------|--------|
| Entity lens shell bar (`EntityLensPage`) | Backend `AvailableAction.prefill` dict merged in `useEntityLens.executeAction` | ✅ Already done |
| Spotlight (`SuggestedActions → ActionModal`) | `query` text from search input | ❌ Not implemented |

`ActionModal` is only consumed by `SuggestedActions`. The `InventoryActionModals` file is unrelated.

### File locations

| File | Role |
|------|------|
| `apps/web/src/components/actions/ActionModal.tsx` | Renders form, seeds `formData` |
| `apps/web/src/components/SuggestedActions.tsx` | Passes `query` prop through |
| `apps/web/src/components/spotlight/SpotlightSearch.tsx` | Callsite — already has `query` state |

### Narrative field detection

Only pre-seed fields where the user's query text makes semantic sense:
- `inferFieldType(field) === 'textarea'` — catches `reason`, `note_text`, `description`, `notes`
- `field === 'title'` — the most common single-line narrative field
- `field === 'content'` or `field === 'summary'` — other common free-text fields

Do NOT seed `date`, `select`, or fields with numeric intent (`quantity`, `price`, anything with `_id`).

Define a helper `isNarrativeField(name: string): boolean` inline at the top of the seed logic.

---

## Task 1: Seed `formData` from `query` in `ActionModal`

**Files:**
- Modify: `apps/web/src/components/actions/ActionModal.tsx`

### Steps

- [ ] **Read the file** before editing.

Already read: line 74 is `const [formData, setFormData] = useState<Record<string, string>>({});`

- [ ] **Add `query?: string` to `ActionModalProps`**

Change lines 19–25 from:
```tsx
interface ActionModalProps {
  action: ActionSuggestion;
  yachtId: string | null;
  entityId?: string;
  onClose: () => void;
  onSuccess: () => void;
}
```
To:
```tsx
interface ActionModalProps {
  action: ActionSuggestion;
  yachtId: string | null;
  entityId?: string;
  query?: string;
  onClose: () => void;
  onSuccess: () => void;
}
```

- [ ] **Add `query` to destructured props** (line 67–73):

Change:
```tsx
export default function ActionModal({
  action,
  yachtId,
  entityId,
  onClose,
  onSuccess,
}: ActionModalProps) {
```
To:
```tsx
export default function ActionModal({
  action,
  yachtId,
  entityId,
  query,
  onClose,
  onSuccess,
}: ActionModalProps) {
```

- [ ] **Change `useState` initializer on line 74** to seed narrative fields from query:

Change:
```tsx
const [formData, setFormData] = useState<Record<string, string>>({});
```
To:
```tsx
const [formData, setFormData] = useState<Record<string, string>>(() => {
  const trimmedQuery = query?.trim() ?? '';
  if (!trimmedQuery) return {};
  const seed: Record<string, string> = {};
  const isNarrativeField = (name: string) =>
    inferFieldType(name) === 'textarea' ||
    name === 'title' ||
    name === 'content' ||
    name === 'summary';
  for (const field of action.required_fields) {
    if (isNarrativeField(field)) {
      seed[field] = trimmedQuery;
    }
  }
  return seed;
});
```

- [ ] **Manual test** (no automated test needed — the change is a `useState` initializer):

Open spotlight, type "Engine overheating issue", click an action with a `title` field (e.g. "Add Fault"). Confirm the Title input is pre-populated with "Engine overheating issue".

- [ ] **Commit**:
```bash
git add apps/web/src/components/actions/ActionModal.tsx
git commit -m "feat: seed ActionModal formData from spotlight query for narrative fields"
```

---

## Task 2: Thread `query` prop through `SuggestedActions`

**Files:**
- Modify: `apps/web/src/components/SuggestedActions.tsx`

### Steps

- [ ] **Read the file** before editing.

Already read: `SuggestedActionsProps` at lines 16–21, `<ActionModal>` at lines 84–89.

- [ ] **Add `query?: string` to `SuggestedActionsProps`**:

Change:
```tsx
interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  onActionComplete?: () => void;
  className?: string;
}
```
To:
```tsx
interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  query?: string;
  onActionComplete?: () => void;
  className?: string;
}
```

- [ ] **Add `query` to destructuring** (line 23–28):

Change:
```tsx
export default function SuggestedActions({
  actions,
  yachtId,
  onActionComplete,
  className,
}: SuggestedActionsProps) {
```
To:
```tsx
export default function SuggestedActions({
  actions,
  yachtId,
  query,
  onActionComplete,
  className,
}: SuggestedActionsProps) {
```

- [ ] **Pass `query` to `<ActionModal>`** (lines 84–89):

Change:
```tsx
      {selectedAction && (
        <ActionModal
          action={selectedAction}
          yachtId={yachtId}
          onClose={handleModalClose}
          onSuccess={handleActionSuccess}
        />
      )}
```
To:
```tsx
      {selectedAction && (
        <ActionModal
          action={selectedAction}
          yachtId={yachtId}
          query={query}
          onClose={handleModalClose}
          onSuccess={handleActionSuccess}
        />
      )}
```

- [ ] **Commit**:
```bash
git add apps/web/src/components/SuggestedActions.tsx
git commit -m "feat: thread query prop through SuggestedActions to ActionModal"
```

---

## Task 3: Pass `query` from `SpotlightSearch` to `SuggestedActions`

**Files:**
- Modify: `apps/web/src/components/spotlight/SpotlightSearch.tsx`

### Steps

- [ ] **Read the callsite** (lines 1016–1022) before editing.

Current (lines 1017–1021):
```tsx
          {hasQuery && actionSuggestions.length > 0 && (
            <SuggestedActions
              actions={actionSuggestions}
              yachtId={user?.yachtId ?? null}
              onActionComplete={refetch}
            />
          )}
```

- [ ] **Add `query={query}` prop**:

Change:
```tsx
            <SuggestedActions
              actions={actionSuggestions}
              yachtId={user?.yachtId ?? null}
              onActionComplete={refetch}
            />
```
To:
```tsx
            <SuggestedActions
              actions={actionSuggestions}
              yachtId={user?.yachtId ?? null}
              query={query}
              onActionComplete={refetch}
            />
```

- [ ] **TypeScript check** — verify no type errors:
```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -v "useActionHandler" | head -20
```
Expected: no new errors.

- [ ] **Commit**:
```bash
git add apps/web/src/components/spotlight/SpotlightSearch.tsx
git commit -m "feat: pass spotlight query to SuggestedActions for form pre-fill"
```

---

## Verification

After all 3 tasks:

1. Search "Engine overheating issue" in spotlight
2. Click "Add Fault" action button → modal opens with Title pre-filled: "Engine overheating issue" and Description pre-filled: "Engine overheating issue"
3. Search "Anchoring winch inspection" → click "Add Work Order" → Title pre-filled
4. Click a date field (e.g. "expiry_date") action → confirm date field is NOT pre-filled
5. Click a quantity/numeric field action → confirm numeric field is NOT pre-filled
6. Clear the search, click an action → confirm modal opens with empty fields (no stale query)
