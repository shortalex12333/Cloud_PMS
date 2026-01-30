# Receiving Lens v1 - E2E Test Suite

**Architecture**: Search-first, intent-driven entity extraction
**Pattern**: Search → Focus → Act
**Security**: Server-resolved yacht_id, RLS enforcement, role-based actions

---

## Test Accounts

All accounts use the same password: **Password2!**

Yacht ID: `85fe1119-b04c-41ac-80f1-829d23322598` (server-resolved from auth, NEVER sent by client)

| Role | Email | Actions Allowed |
|------|-------|-----------------|
| **CREW** | crew.tenant@alex-short.com | READ only (view_receiving_history) |
| **HOD** | hod.tenant@alex-short.com | MUTATE (create, update, attach, add items, link docs, reject) |
| **CAPTAIN** | captain.tenant@alex-short.com | SIGNED (accept_receiving with PIN+TOTP) |

**Note**: Database roles may show as "member" but RLS policies use `is_hod()` and `is_captain()` functions for permission checks.

---

## Architecture Requirements

### 1. Search-First Navigation ✅

**DO**:
```typescript
await page.goto('/');  // Base URL only
await performSearch(page, 'receiving Racor');
```

**DON'T**:
```typescript
await page.goto('/receiving');  // ❌ NO /receiving page exists
```

### 2. Server-Resolved Context ✅

**DO** (Server resolves yacht_id from JWT):
```typescript
await executeAction(jwt, 'create_receiving', {
  vendor_reference: 'ABC123',
  received_date: '2026-01-29',
  // NO yacht_id sent - server resolves from auth
});
```

**DON'T**:
```typescript
await executeAction(jwt, 'create_receiving', {
  yacht_id: '85fe1119-...', // ❌ NEVER send yacht_id from client
  vendor_reference: 'ABC123',
});
```

### 3. Backend Authority ✅

UI renders **ONLY** what backend returns via suggestions:

```typescript
// Backend returns actions for focused entity
const backendActions = await callBackendSuggestions(jwt, entityId);

// UI renders exactly those actions (no more, no less)
const uiActions = await getRenderedActionIds(page);

// Assert parity
for (const uiAction of uiActions) {
  expect(backendActions).toContain(uiAction);
}
```

### 4. Role-Based Action Visibility ✅

```typescript
// CREW - READ only
const crewActions = await getRenderedActionIds(page);
expect(crewActions).not.toContain('create_receiving');  // ✅ No MUTATE

// HOD - MUTATE actions
const hodActions = await getRenderedActionIds(page);
expect(hodActions).toContain('create_receiving');  // ✅ MUTATE allowed

// CAPTAIN - SIGNED actions
const captainActions = await getRenderedActionIds(page);
expect(captainActions).toContain('accept_receiving');  // ✅ SIGNED allowed
```

---

## Running Tests

### Prerequisites

1. **Backend deployed** with commit `796f247` (receiving handler fix)
2. **Database indexes applied**: `supabase/migrations/20260129_105_receiving_indexes.sql`
3. **Frontend deployed** with search-driven UI at `app.celeste7.ai`

### Setup

```bash
# 1. Install dependencies
npm install

# 2. Authenticate all test accounts (creates storage states)
npx playwright test --config=playwright.receiving.config.ts --global-setup

# 3. Verify storage states created
ls -lh test-results/.auth-states/
# Expected:
# - crew-state.json
# - hod-state.json
# - captain-state.json
```

### Run Tests

```bash
# Run all Receiving Lens tests
npx playwright test --config=playwright.receiving.config.ts

# Run specific test suite
npx playwright test tests/e2e/receiving/receiving_search_entity_extraction.spec.ts

# Run with UI mode (debugging)
npx playwright test --config=playwright.receiving.config.ts --ui

# Run in headed mode (see browser)
npx playwright test --config=playwright.receiving.config.ts --headed
```

### View Results

```bash
# HTML report
npx playwright show-report test-results/receiving/html-report

# JSON results
cat test-results/receiving/results.json | jq

# Artifacts (screenshots, evidence)
ls -lh test-results/artifacts/receiving/
```

---

## Test Coverage

### 1. Search & Entity Extraction (HOD)

- ✅ Search by vendor reference triggers entity extraction
- ✅ Search with action intent surfaces relevant actions
- ✅ Backend-frontend parity validation

### 2. Role-Based Action Surfacing

- ✅ CREW: Read-only, no MUTATE/SIGNED actions visible
- ✅ CAPTAIN: Can see SIGNED actions (accept_receiving)

### 3. Action Execution (HOD)

- ✅ HOD can create receiving via Action Router (MUTATE)
- ✅ CREW cannot create receiving (403 RLS_DENIED)

### 4. View History (READ)

- ✅ view_receiving_history returns audit trail, items, documents
- ✅ Parallel query optimization (Task C performance fix)

### 5. Zero 5xx Errors

- ✅ Search → View Details → Zero 5xx
- ✅ All API calls monitored for server errors

---

## Expected Test Results

```
Search & Entity Extraction - HOD (Chief Engineer)
  ✓ Search for receiving by vendor reference triggers entity extraction
  ✓ Search with action intent surfaces relevant actions
  ✓ Backend-frontend parity: UI renders ONLY backend actions

Role-Based Action Surfacing - CREW (Read-Only)
  ✓ CREW can search and view receiving entities (read-only)

Role-Based Action Surfacing - CAPTAIN (Signed Actions)
  ✓ CAPTAIN can see SIGNED actions for receiving entities

Action Execution - HOD
  ✓ HOD can create receiving via Action Router (MUTATE)
  ✓ CREW cannot create receiving (403 RLS_DENIED)

View History Action - READ
  ✓ view_receiving_history returns audit trail, items, documents

Zero 5xx Errors
  ✓ Flow: Search → View Details → Zero 5xx

10 passed (15s)
```

---

## Evidence Artifacts

All tests generate evidence artifacts in `test-results/artifacts/receiving/`:

```
search_entity_extraction_vendor_reference.png
search_entity_extraction_vendor_reference.json
search_with_action_intent.png
search_with_action_intent.json
backend_frontend_parity.json
crew_read_only_validation.json
captain_signed_actions_validation.json
hod_create_receiving.json
crew_create_receiving_denied.json
view_history_validation.json
zero_5xx_validation.json
```

Each `.json` file contains:
- Test description
- Query/action executed
- Results (status codes, entity IDs, action lists)
- Validation outcomes
- Timestamps

---

## Receiving Actions Reference

| Action | Group | Allowed Roles | Purpose |
|--------|-------|---------------|---------|
| `view_receiving_history` | READ | crew, hod, captain | View receiving details, items, documents, audit trail |
| `create_receiving` | MUTATE | hod, captain | Create new receiving record |
| `attach_receiving_image_with_comment` | MUTATE | hod, captain | Upload invoice/packing slip with comment |
| `update_receiving_fields` | MUTATE | hod, captain | Update vendor ref, received date, etc. |
| `add_receiving_item` | MUTATE | hod, captain | Add part/item to receiving |
| `adjust_receiving_item` | MUTATE | hod, captain | Adjust quantity/condition of item |
| `link_invoice_document` | MUTATE | hod, captain | Link document to receiving |
| `reject_receiving` | MUTATE | hod, captain | Reject receiving and record reason |
| `accept_receiving` | SIGNED | captain | Accept receiving with signature (PIN+TOTP) |

---

## Deployment Verification Checklist

Before running tests, verify:

### Backend (commit 796f247)

```bash
# 1. Check API health
curl https://pipeline-core.int.celeste7.ai/health
# Expected: {"status": "healthy"}

# 2. Check receiving handler is registered
curl https://pipeline-core.int.celeste7.ai/v1/actions/list | jq '.actions[] | select(.id | startswith("receiving"))'
# Expected: 10 receiving actions listed

# 3. Verify view_history fix (wrapped in try/except)
# Check logs for no ValueError propagation
```

### Database

```bash
# 1. Apply indexes migration
psql $DATABASE_URL -f supabase/migrations/20260129_105_receiving_indexes.sql

# 2. Verify indexes created
psql $DATABASE_URL -c "SELECT indexname FROM pg_indexes WHERE tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions', 'pms_audit_log') AND indexname LIKE 'idx_receiving%' OR indexname LIKE 'idx_audit_log%';"
# Expected: 10+ indexes
```

### Frontend (app.celeste7.ai)

```bash
# 1. Check base URL loads
curl -I https://app.celeste7.ai/
# Expected: HTTP/2 200

# 2. Verify search input exists
curl -s https://app.celeste7.ai/ | grep -i 'search-input'
# Expected: data-testid="search-input" found

# 3. Check /receiving route returns 404 (by design)
curl -I https://app.celeste7.ai/receiving
# Expected: HTTP/2 404 (search-first architecture)
```

---

## Troubleshooting

### Tests fail with "No JWT found"

**Cause**: Global setup didn't authenticate properly

**Fix**:
```bash
# Re-run global setup
npx playwright test --config=playwright.receiving.config.ts --global-setup

# Check storage states created
ls -lh test-results/.auth-states/
```

### Tests fail with "Receiving entity not visible"

**Cause**: Search extraction not working or entity cards not rendering

**Fix**:
1. Verify frontend deployed with search-driven UI
2. Check entity extraction works: `POST /v1/search` with query
3. Verify entity cards render with `data-entity-type="receiving"`

### Tests fail with "Backend-frontend parity"

**Cause**: UI inventing actions or missing backend actions

**Fix**:
1. Check suggestions API: `POST /v1/suggestions` with entity_id
2. Verify UI only renders actions from backend response
3. Check console for frontend errors

### Tests fail with "403 RLS_DENIED" unexpectedly

**Cause**: Role mapping issue or RLS policies not aligned

**Fix**:
1. Verify test account roles in database: `SELECT * FROM auth_users_roles WHERE email = 'hod.tenant@alex-short.com';`
2. Check `is_hod()` and `is_captain()` functions work correctly
3. Verify RLS policies use `public.get_user_yacht_id()` not JWT metadata

---

## Next Steps

After tests pass:

1. ✅ **Generate evidence bundle** with all artifacts
2. ✅ **Run stress test** to validate performance (>95% success, P95 < 500ms)
3. ✅ **Test wrong-yacht isolation** (create user on different yacht, verify 404/403)
4. ✅ **Create GitHub Actions CI workflow** to run tests on every PR
5. ✅ **Merge to main** after all tests green

---

**Created**: 2026-01-29
**Branch**: e2e/parts-lens-playwright (to be merged with receiving tests)
**Commit**: TBD (pending commit)
**Author**: Claude Sonnet 4.5
**Status**: Ready for deployment testing
