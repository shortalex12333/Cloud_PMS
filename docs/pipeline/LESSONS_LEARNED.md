# Lessons Learned: Certificates Lens Implementation

This document captures what we thought was true at the start vs what we discovered during implementation. Use this to avoid repeating mistakes on the next lens.

---

## False Assumptions (What We Got Wrong)

### 1. Endpoint Location

**Plan said:**
> Add `GET /list` endpoint to `apps/api/action_router/router.py`

**Reality:**
The API routes are in `apps/api/routes/p0_actions_routes.py`, not `action_router/router.py`. Adding the endpoint to `router.py` caused a **404** because that file isn't mounted to the FastAPI app.

**Fix:** Always check where existing endpoints are mounted before adding new ones:
```bash
grep -r "@router" apps/api/routes/
```

**Correct location:** `apps/api/routes/p0_actions_routes.py:4148`

---

### 2. File Creation (Over-Engineering)

**Plan said:**
> Create these new files:
> - `apps/api/action_router/action_search.py`
> - `apps/api/action_router/storage_semantics.py`
> - `apps/api/action_router/schemas/action_list_response.py`

**Reality:**
None of these files were needed. Everything fit cleanly in the existing `registry.py`:
- `search_actions()` - 50 lines
- `get_storage_options()` - 25 lines
- `ACTION_STORAGE_CONFIG` - 20 lines

**Lesson:** Don't create files just because a plan says to. Add code to existing files first; extract only when it grows unwieldy.

---

### 3. Frontend Integration (The Big Gap)

**Plan said:**
> "Backend defines actions; frontend renders blindly"

**Reality:**
The docs never explained HOW the frontend would render actions. The search UI used `/webhook/search` and had NO connection to `/v1/actions/list`. We had to build:

| File | Purpose |
|------|---------|
| `apps/web/src/lib/actionClient.ts` | Added `getActionSuggestions()` client |
| `apps/web/src/hooks/useCelesteSearch.ts` | Detect action intent, fetch suggestions |
| `apps/web/src/components/SuggestedActions.tsx` | Render action buttons |
| `apps/web/src/components/actions/ActionModal.tsx` | Dynamic form + storage confirmation |
| `apps/web/src/components/spotlight/SpotlightSearch.tsx` | Wire in SuggestedActions |

**Lesson:** "Frontend renders blindly" is a principle, not an implementation. Document the specific integration points.

---

### 4. Domain Filter Logic

**Plan said nothing about this.**

**Bug discovered:**
```python
# WRONG - lets through actions with domain=None
if domain and action.domain and action.domain != domain:
    continue

# CORRECT - excludes actions without matching domain
if domain and action.domain != domain:
    continue
```

When domain filter is "certificates", actions without a domain should NOT pass through.

**Lesson:** Write edge-case tests BEFORE implementing filters:
- No query provided → returns all role-allowed actions
- Unknown domain → returns empty list
- Unknown role → returns empty list

---

### 5. Test Script Reference

**Plan said:**
> Docker: `./scripts/test-local-docker.sh`

**Reality (in this repo):**
The script exists and works: `./scripts/test-local-docker.sh`.
You can also run tests directly with compose or pytest:
```bash
./scripts/test-local-docker.sh
# or
docker-compose -f docker-compose.test.yml up --build
# or
cd apps/api && python3 -m pytest tests/docker/run_rls_tests.py -v
```

**Lesson:** Verify referenced scripts exist before documenting them, and provide direct compose/pytest fallbacks.

---

### 6. Missing Frontend Dependency

**Discovered during build:**
```
Cannot find module 'isomorphic-dompurify'
```

The `EmailSearchView.tsx` imported this but it wasn't in `package.json`.

**Fix:**
```bash
npm install isomorphic-dompurify @types/dompurify
```

**Lesson:** Run `npm run build` before declaring "frontend done".

---

### 7. Role Names

**Plan said:**
> Roles: crew (deny), HOD (create/update/link), captain/manager (supersede signed)

**Reality:**
The actual role values used in code are:
- `crew` - basic user
- `chief_engineer` - HOD role (not "HOD")
- `captain` - can supersede
- `manager` - can supersede

**Lesson:** Use exact role strings from the database, not conceptual names.

---

## What Actually Works (Verified)

### Backend Endpoint

```
GET /v1/actions/list?q=add+certificate&domain=certificates
Authorization: Bearer {JWT}
```

**Response:**
```json
{
  "query": "add certificate",
  "actions": [
    {
      "action_id": "create_vessel_certificate",
      "label": "Add Vessel Certificate",
      "variant": "MUTATE",
      "allowed_roles": ["chief_engineer", "captain", "manager"],
      "required_fields": ["yacht_id", "certificate_type", "certificate_name", "issuing_authority"],
      "domain": "certificates",
      "match_score": 0.9,
      "storage_options": {
        "bucket": "documents",
        "path_preview": "{yacht_id}/certificates/{certificate_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
        "confirmation_required": true
      }
    }
  ],
  "total_count": 4,
  "role": "chief_engineer"
}
```

### Role Gating (Tested)

| Role | MUTATE Actions | SIGNED Actions |
|------|---------------|----------------|
| crew | 0 | 0 |
| chief_engineer | 4 | 0 |
| captain | 4 | 1 |
| manager | 4 | 1 |

### Frontend Flow

1. User types "add certificate" in Spotlight search
2. `useCelesteSearch` detects cert action intent
3. Calls `getActionSuggestions("add certificate", "certificates")`
4. `SuggestedActions` renders buttons below search bar
5. Click opens `ActionModal` with dynamic form
6. Submit calls `executeAction()` → backend `/v1/actions/execute`

---

## Files Changed (Actual, Not Planned)

### Backend
| File | Changes |
|------|---------|
| `apps/api/action_router/registry.py` | ActionVariant enum, domain/search metadata, ACTION_STORAGE_CONFIG, search_actions(), get_storage_options() |
| `apps/api/routes/p0_actions_routes.py` | GET /v1/actions/list endpoint |
| `tests/docker/run_rls_tests.py` | 3 new tests for action list |
| `tests/ci/staging_certificates_acceptance.py` | Action list assertions |

### Frontend
| File | Changes |
|------|---------|
| `apps/web/src/lib/actionClient.ts` | ActionSuggestion types, getActionSuggestions() |
| `apps/web/src/hooks/useCelesteSearch.ts` | Action intent detection, suggestions fetch |
| `apps/web/src/components/SuggestedActions.tsx` | **NEW** - Action buttons |
| `apps/web/src/components/actions/ActionModal.tsx` | **NEW** - Dynamic form modal |
| `apps/web/src/components/spotlight/SpotlightSearch.tsx` | Wire in SuggestedActions |
| `apps/web/package.json` | isomorphic-dompurify dependency |

---

## Verification Commands (Actual)

```bash
# Backend tests (from apps/api directory)
python3 -m pytest tests/docker/run_rls_tests.py -v

# Frontend build check
cd apps/web && npm run build

# Type check
npx tsc --noEmit

# Lint
npx next lint
```

---

## Next Lens Checklist

Before starting the next lens, verify:

- [ ] Endpoint location: Check `apps/api/routes/` for existing patterns
- [ ] Role strings: Use exact values from `auth_users_profiles.role`
- [ ] Frontend integration: Plan specific files to modify/create
- [ ] Dependencies: Run `npm run build` early
- [ ] Edge cases: Write tests for empty/null/unknown inputs
- [ ] Domain filter: Test with and without domain parameter
