---
wave: 2
depends_on: [FE-01-01, FE-01-02]
files_modified:
  - apps/web/src/components/lens/WorkOrderLens.tsx
  - apps/web/src/components/lens/actions/*.tsx
  - apps/web/src/hooks/useWorkOrderActions.ts
autonomous: true
requirements: [WO-03, WO-04]
---

# Plan FE-01-03: Work Order Actions (All 20)

## Objective

Wire all 20 Work Order actions from backend to frontend. Each action must be accessible from the UI and trigger the correct API call via the action registry.

## Pre-work

<task id="0">
Query the action registry to get all Work Order actions:

```bash
grep -A5 "work_order" apps/api/registry.py | head -60
```

Or via Supabase if registry is in DB. List all action names, required roles, and whether signature is required.
</task>

## Tasks

<task id="1">
Create `useWorkOrderActions.ts` hook:

```tsx
export function useWorkOrderActions(workOrderId: string) {
  const { mutateAsync: executeAction } = useMutation({
    mutationFn: async ({ action, payload }: { action: string; payload?: Record<string, any> }) => {
      return api.post('/action', {
        entity_type: 'work_order',
        entity_id: workOrderId,
        action,
        payload
      });
    }
  });

  return {
    addNote: (content: string) => executeAction({ action: 'add_note', payload: { content } }),
    addPart: (partId: string, qty: number) => executeAction({ action: 'add_part', payload: { part_id: partId, quantity: qty } }),
    markComplete: () => executeAction({ action: 'mark_complete' }),
    reopen: () => executeAction({ action: 'reopen' }),
    reassign: (userId: string) => executeAction({ action: 'reassign', payload: { assigned_to: userId } }),
    archive: () => executeAction({ action: 'archive' }),
    // ... all 20 actions
  };
}
```
</task>

<task id="2">
Create action button components in `apps/web/src/components/lens/actions/`:

- `AddNoteModal.tsx` - Text input, submit
- `AddPartModal.tsx` - Part selector, quantity input
- `MarkCompleteModal.tsx` - Confirmation + optional signature
- `ReassignModal.tsx` - User selector
- `ArchiveModal.tsx` - Confirmation

Each modal:
- Uses design tokens (surface-elevated, radius-lg)
- Has cancel and confirm buttons
- Shows loading state during submission
- Handles errors with Toast
</task>

<task id="3">
Wire action buttons to sections:

| Section | Actions |
|---------|---------|
| Header | Mark Complete, Reopen, Archive |
| Notes | Add Note |
| Parts | Add Part, Remove Part |
| Attachments | Add Attachment, Remove Attachment |
| (Global) | Reassign, Create from Fault, Link Equipment |

Each button:
- Uses GhostButton or PrimaryButton from design system
- Respects user role (hide if not permitted)
- Opens corresponding modal
</task>

<task id="4">
Implement role-based visibility:

```tsx
const { userRole } = useAuth();
const canMarkComplete = ['captain', 'chief_engineer', 'chief_officer'].includes(userRole);
const canArchive = ['captain', 'manager'].includes(userRole);
```

Hide buttons user cannot use. Don't disable—hide entirely.
</task>

<task id="5">
Test all actions fire correctly:

```bash
# API test for each action
curl -X POST https://api.celeste7.ai/action \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"entity_type":"work_order","entity_id":"...","action":"add_note","payload":{"content":"Test"}}'
```

Verify:
- 200 response
- Ledger entry created
- UI refreshes with new data
</task>

## Verification

```bash
# All 20 actions have UI triggers
grep -rn "executeAction\|mutateAsync" apps/web/src/components/lens/WorkOrderLens.tsx apps/web/src/components/lens/actions/

# Build passes
cd apps/web && npm run build
```

## must_haves

- [ ] useWorkOrderActions hook with all 20 actions
- [ ] Add Note modal works and creates ledger entry
- [ ] Add Part modal works with part selector
- [ ] Mark Complete requires signature for certain roles
- [ ] Role-based button visibility (hide, not disable)
- [ ] All actions trigger correct API endpoint
- [ ] Build passes
