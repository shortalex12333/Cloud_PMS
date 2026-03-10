# Lessons Learned - Celeste7 PMS

This file captures lessons from development and debugging sessions to prevent repeated mistakes.

---

## LESSON: Verify "Blocking" Issues Before Planning Fixes

**Date:** 2026-03-02
**Context:** GAP-001 was documented in GAPS.md as a critical blocker: "/v1/actions/prepare endpoint blocks prefill"
**Failure:** Initial assumption was that the endpoint didn't exist and needed to be implemented
**Root Cause:** The endpoint was already implemented at `p0_actions_routes.py:536` with proper imports at lines 51-60. The 422 error was a validation failure, not a missing endpoint (would be 404).
**Guard Added:** Always verify endpoint existence with actual HTTP request before marking as "blocking gap"
**Test Added:** Check that `/v1/actions/prepare` returns 422 (validation error) not 404 (not found)
**Reusable Pattern:** `curl -X POST http://localhost:8001/v1/actions/prepare` - 422 = exists, 404 = missing
**Tags:** api, endpoints, verification, gaps

---

## LESSON: Check Actual Test Results vs Documentation

**Date:** 2026-03-02
**Context:** Documentation mentioned "26 E2E test failures" as blocking
**Failure:** Prepared to debug 26 tests, wasted mental model on larger problem
**Root Cause:** `.last-run.json` showed only 4 failed tests. Old documentation not updated.
**Guard Added:** Always read `apps/web/test-results/.last-run.json` for actual failure count
**Test Added:** Before E2E debugging, run `cat .last-run.json | jq '.failedTests | length'`
**Reusable Pattern:** Trust JSON artifacts over human-written status docs for test counts
**Tags:** testing, e2e, documentation, verification

---

## LESSON: Placeholder console.log Buttons Are Silent Failures

**Date:** 2026-03-02
**Context:** 7 lens components had action buttons that only `console.log` on click
**Failure:** Users click buttons, nothing visible happens - appears broken
**Root Cause:** Development pattern of using console.log as placeholder, never replaced with real handlers
**Guard Added:** Grep for `console.log.*onClick` in lens components during QA
**Test Added:** Run `grep -r "onClick.*console.log" apps/web/src/components/lens/` - should return 0 results
**Reusable Pattern:** Replace placeholder logs with `toast.info("Feature coming soon")` as interim UX fix
**Tags:** ui, actions, placeholder, ux

---

## LESSON: ReadinessStates Props Must Be Passed Through Component Chain

**Date:** 2026-03-02
**Context:** SuggestedActions had `readinessStates` prop defined but never received data
**Failure:** Visual readiness indicators (green check, amber dot, red lock) not displaying
**Root Cause:** SpotlightSearch.tsx calls SuggestedActions but doesn't pass the readinessStates prop
**Guard Added:** When adding props to a component, grep for all callers and verify they pass the prop
**Test Added:** TypeScript strict mode would catch this if prop was required vs optional
**Reusable Pattern:** Make new props required initially, then relax to optional after verifying all callers
**Tags:** react, props, component-wiring, typescript

---

## LESSON: Parallel Agent Orchestration Dramatically Speeds Exploration

**Date:** 2026-03-02
**Context:** Needed to audit E2E tests, RLS policies, and action buttons simultaneously
**Failure:** N/A - this was a success pattern
**Root Cause:** Using three parallel agents (E2E, RLS, Actions) with Task tool completed in ~3 minutes what would take 15+ minutes sequentially
**Guard Added:** When auditing 3+ independent subsystems, spawn parallel agents
**Test Added:** N/A
**Reusable Pattern:** Use `run_in_background: true` for independent investigation tasks, collect with `TaskOutput`
**Tags:** orchestration, agents, performance, parallel

---

## LESSON: RLS Yacht Isolation Is Non-Negotiable

**Date:** 2026-03-02
**Context:** Audit revealed 81 RLS policies, all using `get_user_yacht_id()` for isolation
**Failure:** N/A - documenting the pattern for future reference
**Root Cause:** Multi-tenant yacht PMS requires absolute data isolation between yachts
**Guard Added:** Every new table MUST have RLS enabled with yacht_id check
**Test Added:**
```sql
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'pms_%' AND rowsecurity = false;
```
Should return 0 rows.
**Reusable Pattern:** `CREATE POLICY ... USING (yacht_id = public.get_user_yacht_id())`
**Tags:** security, rls, multi-tenant, yacht-isolation

---

## LESSON: Interim UX Fix Pattern for Placeholder Buttons

**Date:** 2026-03-02
**Context:** 14 lens component buttons had silent `console.log` placeholders - users clicked, nothing visible happened
**Failure:** N/A - this was a successful remediation pattern
**Root Cause:** Development pattern of using console.log as placeholder, never replaced with real handlers
**Guard Added:** When adding placeholder buttons, always use `toast.info("Feature coming soon")` instead of console.log
**Test Added:** `grep -r "console.log.*onClick" apps/web/src/components/lens/` should return 0 results
**Reusable Pattern:**
```typescript
// BAD - silent failure
<Button onClick={() => console.log('[Lens] Action:', id)}>Action</Button>

// GOOD - visible feedback
import { toast } from 'sonner';
<Button onClick={() => toast.info('Feature coming soon', { description: 'This feature is under development' })}>Action</Button>
```
**Tags:** ui, actions, placeholder, ux, sonner, toast

---

## Meta-Lesson: The Three Verification Gates

Before marking any "gap" or "blocker" as confirmed:

1. **HTTP Verification:** Does the endpoint respond? (200/201 = working, 4xx = exists but validation, 404 = actually missing)
2. **Code Verification:** Does the implementation exist in codebase? (grep, read file)
3. **Test Verification:** What do actual test artifacts say? (.last-run.json, coverage reports)

Trust artifacts over documentation. Verify before planning.

---

## LESSON: Action Hook Pattern for Lens Components

**Date:** 2026-03-02
**Context:** 7 lens components needed real action handlers instead of toast placeholders
**Failure:** N/A - documenting successful implementation pattern
**Root Cause:** Need to standardize how lens components trigger backend mutations
**Guard Added:** Every lens with action buttons MUST have a corresponding `useXxxActions.ts` hook
**Test Added:** Build must pass - hooks use TypeScript and executeAction
**Reusable Pattern:**
```typescript
// useXxxActions.ts pattern
export function useXxxActions(entityId: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doAction = useCallback(async (payload: ActionPayload) => {
    if (!user?.yachtId) return { success: false, error: 'No yacht context' };
    setIsLoading(true);
    setError(null);
    try {
      const result = await executeAction('action_name', {
        context: { yacht_id: user.yachtId, entity_id: entityId },
        payload,
      });
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setIsLoading(false);
    }
  }, [user?.yachtId, entityId]);

  return { doAction, isLoading, error };
}

// Companion permissions hook
export function useXxxPermissions() {
  const { user } = useAuth();
  return {
    canDoAction: ALLOWED_ROLES.includes(user?.role || ''),
  };
}
```
**Tags:** react, hooks, actions, patterns, architecture

---

## LESSON: Permission-Based UI Rendering (UI-Layer RLS)

**Date:** 2026-03-02
**Context:** Action buttons should only appear for users with appropriate roles
**Failure:** N/A - documenting successful pattern
**Root Cause:** Need to hide buttons users can't use (better UX than showing disabled/erroring)
**Guard Added:** Every action button must be wrapped in permission check
**Test Added:** Visual inspection per role
**Reusable Pattern:**
```typescript
const { canApprove, canReject } = useShoppingListPermissions();

// Only render if user has permission
{canApprove && (
  <Button onClick={handleApprove} disabled={isLoading}>
    {isLoading ? 'Approving...' : 'Approve'}
  </Button>
)}
```
**Tags:** react, permissions, ux, rls, roles

---

## LESSON: Sub-Component Pattern for Per-Item Actions in Lists

**Date:** 2026-03-02
**Context:** ShoppingListLensContent needed approve/reject buttons per item, but hooks must be called at component level
**Failure:** Initial approach tried to call hook dynamically per item (violates Rules of Hooks)
**Root Cause:** React hooks must be called unconditionally at component root, but list items need per-item context
**Guard Added:** When items in a list need individual action hooks, create a sub-component
**Test Added:** Build must pass (hook rules enforced by ESLint)
**Reusable Pattern:**
```typescript
// BAD - violates Rules of Hooks
items.map(item => {
  const { action } = useXxxActions(item.id); // ❌ Called in loop
  return <Button onClick={action}>Act</Button>
});

// GOOD - sub-component pattern
function ItemActions({ itemId }: { itemId: string }) {
  const { action, isLoading } = useXxxActions(itemId); // ✅ Called at component root
  return <Button onClick={action} disabled={isLoading}>Act</Button>;
}

items.map(item => <ItemActions key={item.id} itemId={item.id} />);
```
**Tags:** react, hooks, lists, patterns, architecture

---

## LESSON: Parallel Lens Wiring with 7 Agents

**Date:** 2026-03-02
**Context:** Needed to wire 7 lens components to their action hooks simultaneously
**Failure:** N/A - this was a success pattern
**Root Cause:** Each lens component wiring is independent, can be parallelized
**Guard Added:** For independent file modifications, spawn parallel agents
**Test Added:** TypeScript build catches any hook import/usage errors
**Reusable Pattern:**
```
// Spawn 7 agents in ONE message, all with run_in_background: true
Task(wire PartsLensContent)
Task(wire CertificateLensContent)
Task(wire ShoppingListLensContent)
Task(wire ReceivingLensContent)
Task(wire HandoverLensContent)
Task(wire HoursOfRestLensContent)
Task(wire WarrantyLensContent)

// Wait for completion notifications
// Run TypeScript build to verify all wiring correct
```
**Tags:** orchestration, agents, parallel, lens, performance

---

## LESSON: Parallel Agent Merge Conflicts on Same File

**Date:** 2026-03-02
**Context:** Wave 5 spawned 8 parallel agents, several of which modified useEquipmentActions.ts
**Failure:** 9 duplicate `restoreEquipment` function definitions appeared in the file
**Root Cause:** Multiple agents (archive, restore, decommission_replace) all added similar restore functionality at different file locations without coordination
**Guard Added:** When multiple agents will modify the SAME file, either:
  1. Assign ONE agent to do all modifications, OR
  2. Use sequential agents for same-file edits
**Test Added:** `grep -c "const restoreEquipment" useEquipmentActions.ts` should return 1
**Reusable Pattern:** Wave planning should identify file collision risks upfront
**Tags:** orchestration, parallel-agents, merge-conflicts, deduplication

---

## LESSON: Interface Property Name Mismatches Between Hook and Consumer

**Date:** 2026-03-02
**Context:** `PinTotpSignature` interface had `pin_hash`/`totp_code` but EquipmentLensContent used `pin`/`totp`
**Failure:** TypeScript build failed with "'pin' does not exist in type 'PinTotpSignature'"
**Root Cause:** Interface was defined with backend-focused names (hash, code) but component used user-input names (pin, totp)
**Guard Added:** When adding shared interfaces, verify ALL consumers use consistent property names
**Test Added:** TypeScript strict mode catches all property mismatches
**Reusable Pattern:**
```typescript
// Define interface where it's consumed, not where it's created
// OR use a shared types file with explicit documentation
export interface PinTotpSignature {
  pin: string;        // Raw user input, backend hashes if needed
  totp: string;       // 6-digit TOTP code
  signer_id: string;  // UUID of the signing user
  signed_at: string;  // ISO timestamp
}
```
**Tags:** typescript, interfaces, type-safety, naming

---

## LESSON: Action Hook Import Path Consistency

**Date:** 2026-03-02
**Context:** New useWorklistActions.ts used wrong import paths
**Failure:** Build failed: "Module '@/contexts/AuthContext' has no exported member 'useAuth'"
**Root Cause:** Agent used different import path than established pattern (`@/contexts/AuthContext` vs `@/hooks/useAuth`)
**Guard Added:** Before creating new hooks, grep existing hooks for import patterns
**Test Added:** `grep "import.*useAuth.*from" src/hooks/*.ts | head -3` to verify consistency
**Reusable Pattern:**
```typescript
// CORRECT imports for Celeste7 hooks:
import { useAuth } from '@/hooks/useAuth';
import { executeAction } from '@/lib/actionClient';
import type { ActionResult } from '@/lib/actionClient';
```
**Tags:** imports, consistency, hooks, patterns

---

## LESSON: Record<string, unknown> Type Compatibility

**Date:** 2026-03-02
**Context:** TypeScript error: "AddTaskParams is not assignable to Record<string, unknown>"
**Failure:** Build failed because interface lacks index signature
**Root Cause:** Defined interfaces don't implicitly satisfy `Record<string, unknown>` due to missing index signature
**Guard Added:** Use spread operator to convert typed params to Record
**Test Added:** TypeScript strict mode catches this
**Reusable Pattern:**
```typescript
// Option 1: Spread operator (preferred - keeps interface clean)
const action = useCallback(
  (params: MyParams) => execute('action_name', { ...params }),
  [execute]
);

// Option 2: Add index signature (allows unknown properties)
interface MyParams {
  known_field: string;
  [key: string]: unknown;
}
```
**Tags:** typescript, type-safety, generics, patterns

---

## LESSON: 46-Agent Parallel Sprint Verification Protocol

**Date:** 2026-03-02
**Context:** Action Wiring Sprint dispatched 46 parallel agents across 6 waves
**Failure:** N/A - documenting successful protocol
**Root Cause:** Massive parallel orchestration requires structured verification gates
**Guard Added:** After each wave, run TypeScript build before next wave
**Test Added:** `npm run build` must pass with 0 errors
**Reusable Pattern:**
```
Wave Execution Protocol:
1. Launch wave agents in ONE message (parallel)
2. Wait for ALL agents to complete (don't poll)
3. Run `npm run build` - fix ANY errors before next wave
4. Iterate until build green
5. Only then: proceed to next wave

Post-Sprint Verification:
- TypeScript build passes
- No new ESLint errors
- No duplicate function definitions
- All hooks have consistent import patterns
```
**Tags:** orchestration, sprint, verification, protocol, quality-gates

---

## LESSON: Supabase Auth Token localStorage Key Format

**Date:** 2026-03-02
**Context:** E2E tests getting 401 Unauthorized despite proper auth state loaded
**Failure:** `getAuthToken()` function searched for keys containing "supabase" but token key was `sb-qvzmkaamzaqxpzbewjxe-auth-token`
**Root Cause:** Supabase uses `sb-` prefix (abbreviation) not full word "supabase" in localStorage key names
**Guard Added:** Search for keys that `startsWith('sb-') || includes('supabase')` AND `includes('auth')`
**Test Added:** 48 action coverage tests now pass with correct token extraction
**Reusable Pattern:**
```typescript
// Correct Supabase auth token extraction
for (const key of Object.keys(localStorage)) {
  if ((key.startsWith('sb-') || key.includes('supabase')) && key.includes('auth')) {
    const data = JSON.parse(localStorage.getItem(key) || '{}');
    if (data.access_token) return data.access_token;
  }
}
```
**Tags:** supabase, auth, localStorage, e2e-testing, token-extraction

---

## LESSON: Playwright Tests Must Navigate Before Accessing localStorage

**Date:** 2026-03-02
**Context:** E2E tests failing with "SecurityError: Failed to read localStorage"
**Failure:** Test tried to access `localStorage` before navigating to the app domain
**Root Cause:** Browser security model blocks cross-origin localStorage access; Playwright starts at `about:blank`
**Guard Added:** Every test that calls `executeAction` must first call `await page.goto('/')`
**Test Added:** All 48 action coverage tests include navigation step
**Reusable Pattern:**
```typescript
test('action test', async ({ page, executeAction }) => {
  // CRITICAL: Navigate BEFORE any localStorage access
  await page.goto('/');

  const result = await executeAction(page, 'action_name', context, payload);
  expect(result.status).not.toBe(401);
});
```
**Tags:** playwright, e2e-testing, localStorage, browser-security, navigation

---

## LESSON: RouteShell Pattern for Route Page Deduplication

**Date:** 2026-03-03
**Context:** 13 fragmented route pages totaled ~5,081 LOC with massive duplication (feature flag guards, data fetching, loading/error states, navigation callbacks)
**Failure:** N/A - documenting successful elimination of 4,262 LOC
**Root Cause:** Each route page reimplemented the same ~400 LOC pattern instead of delegating to existing LensContent components
**Guard Added:** New route pages MUST use RouteShell wrapper instead of custom implementation
**Test Added:** TypeScript build catches RouteShell usage errors; LOC check: route pages should be <30 LOC
**Reusable Pattern:**
```typescript
// apps/web/src/app/{entity}/[id]/page.tsx - ~20 LOC
'use client';
import { useParams } from 'next/navigation';
import { RouteShell } from '@/components/lens/RouteShell';

export default function EntityDetailPage() {
  const params = useParams();
  return (
    <RouteShell
      entityType="entity_type"
      entityId={params.id as string}
      listRoute="/entities"
    />
  );
}

// RouteShell handles:
// - Feature flag gating (redirect when disabled)
// - Data fetching via react-query
// - Route-specific navigation callbacks
// - Loading/error/not-found states
// - Delegation to LensContent components
```
**Tags:** architecture, deduplication, routeshell, lens, performance

---

## LESSON: One-Shot Batch File Replacement

**Date:** 2026-03-03
**Context:** Needed to replace 11 route pages simultaneously
**Failure:** N/A - documenting successful batch operation
**Root Cause:** Each replacement was independent and followed identical pattern
**Guard Added:** When replacing multiple files with same pattern, batch all Write operations in ONE message
**Test Added:** Count LOC before/after: `for f in app/*/[*]/page.tsx; do wc -l "$f"; done | awk '{sum+=$1} END {print sum}'`
**Reusable Pattern:**
```
1. Read all target files first (tool requirement)
2. Create template for replacement
3. Write ALL replacements in single message (parallel execution)
4. Verify TypeScript compilation once at end
```
**Tags:** orchestration, batch-operations, file-replacement, performance

---

## LESSON: Permission Hooks Already Used PermissionService

**Date:** 2026-03-03
**Context:** Phase 16.2-02 planned to "refactor 12 permission hooks to read from lens_matrix.json"
**Failure:** Unnecessary planning - hooks were already refactored
**Root Cause:** Didn't verify current state of permission hooks before creating plan
**Guard Added:** Before planning refactoring work, grep for the expected pattern first
**Test Added:** `grep "usePermissions" src/hooks/permissions/*.ts` - verify delegation pattern exists
**Reusable Pattern:** Trust but verify - always read current implementation before planning changes
**Tags:** planning, verification, pre-check, permission-hooks

---

## LESSON: RBAC Test Failures Reveal Actual Permission Configuration

**Date:** 2026-03-02
**Context:** Action coverage tests showed assumed roles didn't match backend RBAC
**Failure:** N/A - documenting successful discovery pattern
**Root Cause:** Frontend assumptions about role requirements didn't match backend action registry
**Guard Added:** Use 403 responses to discover actual role requirements
**Test Added:** Phase 1 positive tests + Phase 2 denial tests provide complete RBAC coverage
**Reusable Pattern:**
```typescript
// If positive test returns 403: role requirement is HIGHER than assumed
// If denial test passes: RBAC is correctly enforced
// If denial test fails: role can actually access the action

// Discovered corrections:
// add_equipment_note: crew → hod
// record_equipment_hours: crew → hod
// adjust_stock_quantity: hod → captain
// view_compliance_status: hod → crew (crew CAN access)
```
**Tags:** rbac, e2e-testing, permissions, role-discovery, action-coverage

---

## LESSON: State Files Can Drift - Verify Against Filesystem

**Date:** 2026-03-03
**Context:** STATE.md showed Phase 19 as "complete (4/4 waves)", ROADMAP.md showed "0/4 plans" - contradictory
**Failure:** Attempted to execute already-completed work (Plan 19-04)
**Root Cause:** STATE.md was updated optimistically, ROADMAP.md and SUMMARY files weren't updated after execution
**Guard Added:** Before executing a plan, verify: `ls .planning/phases/{phase}/*-SUMMARY.md | wc -l` equals plan count
**Test Added:** Compare `ls *-PLAN.md | wc -l` vs `ls *-SUMMARY.md | wc -l` - must match for complete phases
**Reusable Pattern:**
```bash
# Verify phase completion status
PLANS=$(ls .planning/phases/19-*/*-PLAN.md | wc -l)
SUMMARIES=$(ls .planning/phases/19-*/*-SUMMARY.md | wc -l)
if [ "$PLANS" -eq "$SUMMARIES" ]; then
  echo "Phase complete"
else
  echo "Phase incomplete: $SUMMARIES/$PLANS plans executed"
fi
```
**Tags:** state-management, verification, gsd, phase-tracking, drift-detection

---

## LESSON: Wave 4 E2E Tests Already Existed - Summary File Missing

**Date:** 2026-03-03
**Context:** 12 E2E test files (614 tests) existed in test/e2e/ but 19-04-SUMMARY.md was never created
**Failure:** Progress check showed "unexecuted plan" when work was actually done
**Root Cause:** Execution completed but summary wasn't written (possible context window exhaustion)
**Guard Added:** After plan execution, ALWAYS verify summary file exists before marking complete
**Test Added:** `[ -f ".planning/phases/{phase}/{plan}-SUMMARY.md" ] || echo "MISSING SUMMARY"`
**Reusable Pattern:** Summary file is the source of truth for plan completion, not just artifact existence
**Tags:** gsd, summaries, verification, completion-tracking

---

## LESSON: "Different Architecture" ≠ "Complete" — Verify Against Target Architecture

**Date:** 2026-03-03
**Context:** Email uses Situation pattern (EmailOverlay, single-URL SPA mode) which works. Assumed this meant "no migration needed."
**Failure:** Documented GAP-027 as "FALSE GAP" when Email actually needs conversion to fragmented route architecture
**Root Cause:** Confused "functional in old pattern" with "compatible with new architecture"
**Guard Added:** When a component uses a different pattern, explicitly ask: "Does this need conversion to target architecture?"
**Test Added:** Check LensRenderer.tsx for entity registration: `grep "case 'email'" LensRenderer.tsx` — if missing, conversion needed
**Reusable Pattern:**
```
Working ≠ Complete
"Different pattern" triggers TWO questions:
1. Does it work in OLD architecture? (Verify — may be false)
2. Does it work in NEW architecture? (Verify — may need conversion)
```
**Tags:** architecture, migration, verification, false-assumptions

---

## LESSON: OAuth/Fetch Patterns Are Sacred — Map Before Touching

**Date:** 2026-03-03
**Context:** Email conversion requires touching components with complex OAuth integrations (Outlook, Microsoft Graph API)
**Failure:** N/A - documenting protection pattern before conversion
**Root Cause:** OAuth/auth flows have subtle invariants that break silently if modified
**Guard Added:** Before any email conversion work, identify and document SACRED patterns:
**Test Added:** After email conversion, verify all OAuth flows still work (connect, reconnect, dual 401 handling)
**Reusable Pattern:**
```typescript
// SACRED - DO NOT MODIFY:
// 1. oauth-utils.ts (entire file) — READ/WRITE app separation, forbidden scopes
// 2. useEmailData.ts:185-218 (authFetch) — Dual 401 handling (Outlook vs JWT)
// 3. useEmailData.ts:900-996 (useOutlookConnection) — 5-minute buffer
// 4. authHelpers.ts:64-96 (getValidJWT) — 60-second buffer
// 5. Token exchange location — Render backend only, never frontend

// SAFE to modify:
// - Component layouts (JSX structure)
// - React Query cache keys
// - Error UI
// - Data transformation
```
**Tags:** oauth, security, architecture, sacred-patterns, email

---

## LESSON: Celeste Is a PA, Not a Filing Cabinet — Test Accordingly

**Date:** 2026-03-09
**Context:** Repeatedly suggesting weak, developer-structured NLP test prompts like "show me all overdue work orders" or bare keywords like "pump"
**Failure:** These sanitized prompts only validate the happy path and don't reflect how real crew members interact with the system
**Root Cause:** No persistent memory of the core product vision — Celeste's search bar is a Personal Assistant interface where users issue ACTION-BASED commands across domains
**Guard Added:** NEVER test with structured/clean prompts. ALWAYS use real action-based queries:
  - "faults on generator 23"
  - "overdue work orders"
  - "log hours of rest"
  - "who signed for the filters last tuesday"
  - "create wo for turbocharger inspection"
  - "overheating alarm watermaker"
  - "unsigned hours of rest this week"
**Test Added:** Before suggesting any test query, ask: "Would a chief engineer actually type this?" If it sounds like a developer wrote it, rewrite it.
**Reusable Pattern:** The NLP pipeline is mature (months of curation). When search results look wrong, the bug is almost always a display/mapping issue in the frontend, not a pipeline failure. Fix the last mile, don't question the pipeline.
**Tags:** nlp, search, product-vision, testing, ux, personal-assistant

---

## LESSON: Sequential Await on Analytics-Only Code Is a Latency Tax

**Date:** 2026-03-10
**Context:** L1 queries took 8-10s despite backend search completing in 0-2s. Investigated the full request lifecycle.
**Failure:** `await orchestrator.extract(q)` on line 971 of `f1_search_streaming.py` blocked for 3-5s waiting for GPT-4o-mini — but the extraction result was ANALYTICS ONLY, never used to filter or rank search results.
**Root Cause:** The extraction was implemented as a sequential `await` during initial development when it was expected to feed into search. After LAW 22 (no threshold amputation), extraction became analytics-only but the `await` was never changed to fire-and-forget.
**Guard Added:** Any `await` in the hot path must justify WHY it blocks. If the result isn't used before the next phase, use `asyncio.create_task()` and collect later.
**Test Added:** Ground truth test suite monitors L1 latency — target <3s (currently 1.9s avg).
**Reusable Pattern:** Audit every `await` in the request path: does the NEXT line use the result? If not, fire-and-forget.
**Tags:** performance, asyncio, latency, f1-search, analytics

---

## LESSON: Coverage Controller INSTRUCTION_PATTERNS Penalize Polite English

**Date:** 2026-03-10
**Context:** L1 (natural language) queries had 66.7% pass rate vs L5 (codes) at 100%. System had inverted bias — penalizing good English.
**Failure:** `coverage_controller.py:45-53` defines INSTRUCTION_PATTERNS including "please", "check", "see", "ensure", "verify", "confirm". Any L1 query containing these → `needs_ai=True` → 3-5s GPT call.
**Root Cause:** The coverage controller was designed to detect queries needing AI extraction. But natural language almost ALWAYS contains instruction words, making the AI path the default for polite users while terse "EPIRB battery" queries skip it entirely.
**Guard Added:** Entity extraction is now fire-and-forget — the coverage controller still decides `needs_ai`, but it no longer blocks the search path. The latency penalty is eliminated regardless of the decision.
**Test Added:** Ground truth L1-L5 bias gap metric — target <15% (currently 13.3%, was 33.3%).
**Reusable Pattern:** When a classifier gates a slow path, check if the gated path actually affects the output. If it's analytics-only, don't gate — fire unconditionally in the background.
**Tags:** bias, nlp, coverage-controller, latency, f1-search

---

## LESSON: Embedding Budget Is a Step Function, Not a Bell Curve

**Date:** 2026-03-10
**Context:** L1 embedding budget was 150ms, L2 was 800ms. Local dev (Sydney) has 262ms TCP latency to OpenAI.
**Failure:** Embeddings NEVER worked on local dev. OpenAI returns the EXACT SAME 1536-d vector whether you wait 150ms or 5000ms. There's no partial embedding or quality gradient.
**Root Cause:** Treated budget as a quality control (Parkinson's Law concern) when it's actually binary: API responds in time → full vector, doesn't → nothing. The correct budget is `f(network_latency)`, not `f(desired_quality)`.
**Guard Added:** Embedding budgets now env-var configurable: `F1_L1_EMBEDDING_BUDGET_MS` (default 500ms), `F1_L2_EMBEDDING_BUDGET_MS` (default 2000ms). Production overrides via env vars.
**Test Added:** Ground truth suite checks `embeddings_count > 0` in finalized events. L3 went from 66.7% → 100% after fix (vector search now works locally).
**Reusable Pattern:** Before setting any timeout, ask: "Does more time give better results, or is it binary?" Binary operations need `f(latency)` budgets, not arbitrary constants.
**Tags:** embeddings, timeout, openai, physics, f1-search

---

## LESSON: Preamble Stripping Improves pg_trgm But Has Diminishing Returns

**Date:** 2026-03-10
**Context:** "Show me the fuel filter" failed pg_trgm (0 results) while "fuel filter" worked. pg_trgm similarity = |intersection| / |union| of 3-grams. "Show me the" adds ~12 noise trigrams.
**Failure:** Initial assumption was preamble stripping would fix most L1 failures. It helped (L1 went from 66.7% → 80%) but remaining failures have different root causes (data dedup, rewrite cap, signal dilution).
**Root Cause:** Preamble stripping is additive — it adds a cleaner rewrite alongside the original. But the 3-rewrite cap means it competes with other rewrites (WO-normalization, stopword). Long queries still dilute TSV signal even after stripping.
**Guard Added:** Preamble stripping is belt-and-suspenders, not primary fix. Original query always kept. Max 12 conservative patterns (no action verbs like "check", "verify").
**Test Added:** 21/22 unit tests for `_strip_preamble()`. The 1 "failure" (not stripping "Please check") is correct — "check" is an action verb, not a preamble.
**Reusable Pattern:** When adding query rewrites, the rewrite cap limits how many fixes can stack. Each rewrite slot is precious — prioritize by signal impact.
**Tags:** trigram, preamble, rewrites, f1-search, cortex

---

## LESSON: Duplicate Data in search_index Causes Unfixable Ranking Dilution

**Date:** 2026-03-10
**Context:** Item #2 "Raw Water Pump Seal Kit" found at rank #6, failing @3 target. Investigated signal breakdown.
**Failure:** 3 parts with identical name ("Raw Water Pump Seal Kit"), 2 shopping items, and 1 email ALL compete for the same TSV/vector signals. Target consistently at rank #4-6 at BOTH L1 and L2.
**Root Cause:** Projection worker creates separate search_index rows for each part, even when names are identical. RRF correctly distributes score across duplicates — there IS no single right answer when 3 items are identical.
**Guard Added:** None (pipeline is working correctly). Flagged for projection worker dedup.
**Test Added:** Item #2 is documented as a known data quality limitation in ground truth suite.
**Reusable Pattern:** When an item fails ranking at ALL literacy levels (not just L1), the issue is data quality, not the pipeline. Check for duplicates before debugging the search algorithm.
**Tags:** data-quality, search-index, ranking, projection-worker, dedup

---

## LESSON: The 3-Rewrite Cap Creates Priority Conflicts Between Fixes

**Date:** 2026-03-10
**Context:** Fix 5 (WO-normalization) was designed to fix Item #11 by adding "WO-0037" rewrite. Fix 3 (preamble stripping) already uses one rewrite slot.
**Failure:** Query "Show me work order 37 for the sewage system service" generates 4 rewrites: original + preamble_stripped + wo_normalized + wo_normalized_stripped. The cap of 3 cuts the BEST variant (stripped + normalized: "WO-0037 for the sewage system service").
**Root Cause:** `rewrites[:3]` cap at line ~549 of `rewrites.py`. This was set for performance (each rewrite = 1 SQL call in hyper_search_multi). But it creates priority conflicts when multiple rewrite strategies apply to the same query.
**Guard Added:** Rewrite cap raised from 3→5 (Fix 7). Priority chain: original > preamble_stripped > connector_stripped > wo_normalized > stopword > abbreviation. First 5 win.
**Test Added:** Item #12 GPS Signal Lost L1 went from MISS → rank #1 after cap raise + connector stripping. Item #11 still MISS (different root cause — TSV dilution on long query, not cap).
**Reusable Pattern:** Fixed-size rewrite slots create a priority queue problem. When adding a new rewrite strategy, verify it doesn't get cut by the cap for the queries it's supposed to fix. Raising the cap was zero-cost here because all rewrites go in ONE SQL call via f1_search_cards array parameters.
**Tags:** rewrites, cortex, architecture, rewrite-cap, f1-search

---

## LESSON: Connector-Phrase Stripping Unlocks Precise TSV Matching

**Date:** 2026-03-10
**Context:** Item #12 "Show me the GPS signal lost fault with code E032" was MISS at L1 while L2 "GPS signal lost fault E032" ranked #1. The difference: "with code" adds 2 extra TSV AND requirements.
**Failure:** TSV uses `plainto_tsquery('english', ...)` which ANDs all non-stopword tokens. "with" and "code" are non-stopwords in the search context, creating AND requirements that don't match search_index content.
**Root Cause:** Mid-query connector phrases like "with code", "for the", "from the" add AND requirements that poison TSV matching without contributing to search intent.
**Guard Added:** `_CONNECTOR_PATTERNS` in `cortex/rewrites.py` (5 patterns) strips these phrases as an additive rewrite. Combined with rewrite cap of 5, the stripped variant survives to search.
**Test Added:** Run 3 verified: Item #12 L1 rank #1 (was MISS). Only 1 result returned = highly precise match.
**Reusable Pattern:** When TSV fails on L1 queries but works on L2, compare token counts. If L1 has extra connector phrases ("with", "for the", "from the"), strip them as rewrite variants. The key is that TSV ANDs are strict — every extra non-stopword token MUST match.
**Tags:** tsv, connector-stripping, rewrites, f1-search, cortex

---

## LESSON: "Vague In = Vague Out" Applies to Fault Queries Too

**Date:** 2026-03-10
**Context:** Item #13 L4 "fault for generator overheating with coolant temperature" ranked #17, while L1-L3 with fault code FLT-AC6CD65E all ranked #1.
**Failure:** Not a pipeline failure — the query lacks the unique identifier (fault code) that distinguishes this specific fault from other generator faults.
**Root Cause:** "generator overheating" and "coolant temperature" are common terms that match many faults. Without FLT-AC6CD65E, the system correctly ranks more specific matches higher.
**Guard Added:** None — this is the system working as designed. Queries without unique identifiers get ambiguous results.
**Test Added:** Documented in ground truth suite as "vague in = vague out" — not a regression.
**Reusable Pattern:** When a failure appears at one literacy level but not others, compare what distinguishing signal the passing queries carry. If the failing query lacks a unique identifier, the ranking is correct — the query is genuinely ambiguous.
**Tags:** ranking, vague-queries, fault-codes, f1-search, ground-truth

---

## LESSON: JWT Auth Requires `aud` Claim for Supabase Verification

**Date:** 2026-03-10
**Context:** Self-minted JWT tokens for testing returned 401 "Signature verification failed".
**Failure:** The PyJWT library was encoding the token correctly (HS256, correct secret), but the API's `jwt.decode()` call includes `audience='authenticated'` which requires an `aud` claim in the token.
**Root Cause:** Missing `'aud': 'authenticated'` in the JWT payload. The PyJWT decode with `audience=` parameter raises `InvalidAudienceError` (subclass of `InvalidTokenError`) which gets caught and re-raised as "Signature verification failed" — misleading error message.
**Guard Added:** When minting test JWTs for Supabase, always include `aud: 'authenticated'`. Also need real user_id (sub claim) that exists in master DB — self-registration tokens get 403.
**Test Added:** Test script now uses stored JWT from `/tmp/jwt_token.txt` (minted from real Supabase auth).
**Reusable Pattern:** Supabase JWT claims require: `sub` (real user UUID), `aud: 'authenticated'`, `role: 'authenticated'`, `iss: 'supabase'`, `exp`, `iat`. Missing any of these causes verification failure.
**Tags:** jwt, supabase, auth, testing, f1-search
