# FIX ROOT CAUSES - Priority Order

Claude identified 4 root causes. Fix in this order:

---

## PRIORITY 1: Validation Errors (28 failures) - EASIEST WIN

**Problem:** Handlers return 500 (crash) instead of 400 (validation error)

**Fix:** Add try/catch with proper error responses

**Files to fix:**
```
/apps/web/src/lib/microactions/handlers/*.ts
```

**Pattern:**
```typescript
// BEFORE (crashes with 500):
export async function someHandler(context: ActionContext) {
  const { entity_id } = context;
  // If entity_id is missing, this crashes
  const result = await supabase.from('table').select().eq('id', entity_id);
}

// AFTER (returns 400):
export async function someHandler(context: ActionContext): Promise<ActionResult> {
  try {
    const { entity_id } = context;

    // Validate required fields
    if (!entity_id) {
      return {
        success: false,
        error: 'entity_id is required',
        status: 400
      };
    }

    const result = await supabase.from('table').select().eq('id', entity_id);
    return { success: true, data: result.data };

  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      status: 500
    };
  }
}
```

**Time to fix:** ~30 minutes (add validation to all handlers)

---

## PRIORITY 2: Auth Resume Tests (12 failures) - FRONTEND BUG

**Problem:** Sessions don't persist after page reload

**Files to investigate:**
```
/apps/web/src/contexts/AuthContext.tsx
/apps/web/src/lib/supabaseClient.ts
```

**Likely issue:**
- Session token not being stored in localStorage/cookies
- Or session refresh not working on page load

**Check:**
```typescript
// In AuthContext.tsx, verify session persistence
useEffect(() => {
  supabase.auth.getSession().then(({ data: { session } }) => {
    // Is this returning null after reload?
  });
}, []);
```

**Time to fix:** ~1 hour (debug session flow)

---

## PRIORITY 3: Cluster 02 Tests (18 failures) - SCHEMA MISMATCH

**Problem:** Tests expect tables that don't exist. Code uses metadata JSON fields.

**Two options:**

### Option A: Update tests to match current implementation
```typescript
// Test expects:
const { data } = await supabase.from('work_order_checklists').select();

// Reality: checklist is in work_order.metadata.checklist
const { data } = await supabase.from('pms_work_orders').select('metadata');
const checklist = data?.metadata?.checklist;
```

### Option B: Create the missing tables (proper solution)
```sql
-- If spec says these tables should exist, create them
CREATE TABLE work_order_checklists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  work_order_id UUID REFERENCES pms_work_orders(id),
  items JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Decision:** Check the spec (COMPLETE_ACTION_EXECUTION_CATALOG.md) - does it say dedicated tables or metadata?

---

## PRIORITY 4: Contract Test (3 failures) - CONFIG ISSUE

**Problem:** tenant_key_alias format doesn't match test expectation

**Files:**
```
/tests/e2e/contracts/ (find the contract test)
/supabase/ (check what get_my_bootstrap returns)
```

**Fix:** Either update test expectation OR fix the RPC to return correct format

---

## EXECUTION ORDER

```
1. Fix validation (add try/catch to handlers) → Run tests → 28 failures fixed
2. Fix auth resume (debug session persistence) → Run tests → 12 more fixed
3. Fix cluster 02 (update tests OR create tables) → Run tests → 18 more fixed
4. Fix contract test (format mismatch) → Run tests → 3 more fixed

Total: ~61 failures → 0 failures
```

---

## PROMPT FOR CLAUDE

```
You identified 4 root causes. Fix them in order:

1. FIRST: Validation errors (28 failures)
   - Add try/catch to all handlers in /apps/web/src/lib/microactions/handlers/
   - Return 400 for validation errors, not 500
   - Run: npx playwright test tests/e2e/microactions/vigorous_test_matrix.spec.ts

2. SECOND: Auth resume (12 failures)
   - Debug /apps/web/src/contexts/AuthContext.tsx
   - Find why session doesn't persist after reload
   - Run: npx playwright test tests/e2e/auth/

3. THIRD: Cluster 02 (18 failures)
   - Check if tests expect tables or metadata
   - Update tests OR create missing tables
   - Run: npx playwright test tests/e2e/microactions/cluster_02_do_maintenance.spec.ts

4. FOURTH: Contract test (3 failures)
   - Fix tenant_key_alias format
   - Run: npx playwright test --project=contracts

After each fix, run that specific test suite to verify.
When ALL pass locally, push and verify GitHub is green.
```
