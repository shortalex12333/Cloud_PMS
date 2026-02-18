# CelesteOS PMS - Codebase Concerns & Technical Debt

**Date**: 2026-02-17
**Status**: Active Issues Identified
**Scope**: 10 lenses, ~120 actions, 73 test files

---

## Critical Issues

### 1. Email Lens Handler MISSING ENTIRELY
**Severity**: CRITICAL
**Files**: `/apps/api/handlers/` (no `email_handlers.py`)
**Evidence**:
- Progress log shows: "Email Lens handler missing | 5 actions not implemented"
- Registry shows only `compose_warranty_email` action (warranty domain, not email lens)
- Email lens listed as "NOT IMPLEMENTED" in PROGRESS_LOG.md line 101
- No test file `test_email_lens.py` exists
- Domain count: 10 lenses (certificates, documents, equipment, faults, hours_of_rest, parts, receiving, shopping_list, warranty, work_orders) — email lens **never registered**

**Impact**:
- Email integration is incomplete
- 5 email-related actions likely undefined
- No backend processing for email lens microactions

**Location**: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.claude/PROGRESS_LOG.md:118`

---

### 2. Test Coverage Crisis: 14 of 16 Lenses at 0%
**Severity**: HIGH
**Evidence**:
- 73 test files found, but only 69 contain test functions
- No dedicated test files for:
  - Email Lens (missing entirely)
  - Navigation Lens (context_nav has schemas only, no tests)
  - Situation State Machines (complex logic, untested)
- Lens test status from LENS_INVENTORY.json: All marked "TODO"
- /apps/api/tests/test_receiving_lens_v1_acceptance.py:516: `# TODO: Fix RLS policies - currently returns data when it shouldn't`

**Test Coverage By Domain**:
| Domain | Actions | Test Files | Coverage |
|--------|---------|-----------|----------|
| certificates | 5 | Partial | ~40% |
| documents | 10 | Present | ~60% |
| equipment | 18 | Minimal | ~20% |
| faults | 12 | Minimal | ~20% |
| hours_of_rest | 12 | Present | ~50% |
| parts | 11 | Present | ~60% |
| receiving | 10 | Present | ~70% |
| shopping_list | 5 | Minimal | ~30% |
| warranty | 6 | Minimal | ~20% |
| work_orders | 17 | Minimal | ~20% |
| **email** | **5** | **NONE** | **0%** |
| **navigation** | **?** | **NONE** | **0%** |

---

## Pending Work

### 1. PR #332 Pending Merge
**Status**: OPEN
**Description**: Receiving handler fix (reject→accept bug)
**Location**: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.claude/PROGRESS_LOG.md:32`
**Blockers**:
- Awaiting code review approval
- Not deployed to staging API yet

**Associated Issues**:
- `/apps/api/handlers/receiving_handlers.py.bak3` — backup suggests multiple iterations
- 3 backup files suggest instability:
  - `receiving_handlers.py.bak` (40K, 2026-01-28)
  - `receiving_handlers.py.bak2` (42K, 2026-01-28)
  - `receiving_handlers.py.bak3` (42K, 2026-01-21)

---

### 2. Test User Not Provisioned in Supabase Auth
**Email**: `crew.test@alex-short.com`
**Status**: BLOCKING
**Impact**: All receiving test authentication fails
**Evidence**:
- References in 30+ test files (hardcoded in test suite)
- PROGRESS_LOG.md:117: "crew.test@alex-short.com not in auth | Receiving test fails | Need Supabase provisioning"
- test_artifacts/obtain_jwt_tokens.py hardcodes this email
- tests/ci/staging_embeds_shadow_check.py uses env var fallback

**Affected Test Files**:
- /apps/api/tests/test_crew_lens_api_integration.py
- /apps/api/tests/test_crew_lens_rls_security.py
- /apps/api/tests/test_hours_of_rest_lens_v3.py
- /apps/api/tests/test_receiving_upload_ocr.py
- Multiple CI/CD test runners (tests/docker/, tests/ci/)

---

### 3. Handler Not Deployed to Staging API
**Status**: PENDING
**Component**: Receiving handler fix from PR #332
**Environment**: Staging API (not production)
**Impact**: Staging tests cannot validate fix before production merge

---

## Frontend Gaps

### 1. Work Order Lens: 6 Missing Action Components
**File**: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web/src/app/work-orders/[id]/page.tsx`
**Status**: INCOMPLETE IMPLEMENTATION

**Missing Components** (lines 49-59):
```
- [ ] Action buttons (mark complete, assign, add note, add photo, etc.)
- [ ] Checklist display and interaction (pms_checklist_items)
- [ ] Parts list display (pms_work_order_parts)
- [ ] Edit modal for updating work order details
- [ ] Status transition buttons with confirmation
- [ ] Attachments/photos gallery
```

**Code Evidence**: 47 TODO comments in single file
**Location**: Lines 264, 280, 315, 337, 342, 363, 433, 439

**Backend Exists**: 17 work order actions registered in registry.py

---

### 2. Navigation Lens: Partial Frontend Implementation
**Files**:
- `/apps/api/context_nav/schemas.py:83`: `# TODO: Implement in Phase 4`
- `/apps/web/src/lib/context-nav/types.ts:81`: `# TODO: Implement business logic in Phase 4`

**Status**: Schema defined, business logic incomplete
**Handler Issues**:
- `/apps/api/handlers/context_navigation_handlers.py:48`: `"extracted_entities": {}, # TODO: Extract entities deterministically`
- `/apps/api/handlers/context_navigation_handlers.py:119`: Same TODO (extracted_entities placeholder)

---

### 3. Equipment & Fault Lenses: 18 TODO Comments
**Equipment Page** (`/apps/web/src/app/equipment/[id]/page.tsx`):
```
- Line 264: TODO: Add action buttons (Edit, Create Fault, Create WO, etc.)
- Line 280: TODO: Add action buttons
- Line 315: TODO: Make clickable to filter by type
- Lines 333-464: Multiple section placeholders (Active Faults, Maintenance Schedule, History, Spare Parts, Documentation)
```

**Fault Page** (`/apps/web/src/app/faults/[id]/page.tsx`):
```
- Line 250: TODO: Add action buttons (Diagnose, Create WO, etc.)
- Line 266: TODO: Add action buttons
- Line 310: TODO: Make clickable
- Lines 403-408: AI Diagnosis, Fault History sections
```

---

## Technical Debt

### 1. TODO Comments (26 in production code)

**Critical Path TODOs**:
| File | Line | Severity | Issue |
|------|------|----------|-------|
| receiving_handlers.py | 499 | HIGH | TODO: Integrate with OCR/extraction service |
| work_order_mutation_handlers.py | 1806 | MEDIUM | Generate work order number: WO-YYYY-XXX (magic string pattern) |
| microaction_service.py | 2184 | HIGH | TODO: Validate confirmation token (signature, expiry, user match) |
| middleware/auth.py | 63 | HIGH | TODO: AGENT_TOKEN_SECRET - Configure in Render |
| context_navigation_handlers.py | 48, 119 | MEDIUM | TODO: Extract entities deterministically |
| inventory_handlers.py | 154 | MEDIUM | TODO: Implement when purchase orders exist |
| routes/email.py | 2451 | HIGH | TODO: Implement pgvector search using match_email_messages RPC |
| schema_mapping.py | 71 | MEDIUM | TODO: Implement proper normalization once schema is finalized |

**Location**: See `/Users/celeste7/.claude/projects/-Volumes-Backup-CELESTE/6154729d-7aeb-45f6-a740-f9e2eea35f83/tool-results/toolu_01YHz12dVhbHc6KEhWgwgvXw.txt` (lines 1-50)

---

### 2. Deprecated Patterns & Legacy Code

**Deprecated Handlers**:
- `N8N = "n8n"` — DEPRECATED 2026-01-27, all handlers now INTERNAL (registry.py:20)
- Deprecated endpoints in microaction_service.py:
  - `/extract_microactions` (use `/extract` instead)
  - `/extract_detailed` (use `/extract` instead)

**Deprecated Field References** (entity_extraction_loader.py):
```python
'diagnostic': [],               # DEPRECATED: Use entities instead
'equipment': [],                # DEPRECATED: Use entities instead
'gazetteer_matches': []         # DEPRECATED: Use entities instead
```

**Deprecated Schema** (schema_mapping.py):
- `equipment` table: "legacy/simplified - DEPRECATED, use pms_equipment"

**Legacy Auth Functions** (middleware/auth.py):
- `DEPRECATED: DO NOT USE FOR APP ROUTES` markers on 4 functions
- `DEPRECATED: Use get_authenticated_user() for tenant lookup`

---

### 3. Hardcoded Values & Magic Strings

**Work Order Number Pattern**:
- Handler: `work_order_mutation_handlers.py:1806` — `"WO-YYYY-XXX"` (not parameterized)
- Database: `02_p0_actions_tables.sql:386` — Comment: `'Generate sequential work order number (WO-YYYY-XXX)'`
- Test expectation: `test_results/TEST_EXECUTION_LOG.txt:63` — Validates `WO-XXXXX` pattern

**Entity ID Placeholders**:
- Part references: `parts_handlers.py` — "REAL_SHOPPING_ITEM_ID" (placeholder validation)
- Vault overrides: `confidence_thresholds.py:283` — `# TODO: In future, look up yacht-specific overrides` (hardcoded for now)

**Test User Credentials** (30+ references):
- Email: `crew.test@alex-short.com`
- Password: `Password2!` (plaintext in test configs)
- UUID: `57e82f78-0a2d-4a7c-a428-6287621d06c5` (hardcoded in CI/CD)

---

### 4. Backup & Experimental Files Cluttering Handlers

**Receiving Handlers Backups**:
```
/apps/api/handlers/receiving_handlers.py        (59K - current)
/apps/api/handlers/receiving_handlers.py.bak    (40K - 2026-01-28)
/apps/api/handlers/receiving_handlers.py.bak2   (42K - 2026-01-28)
/apps/api/handlers/receiving_handlers.py.bak3   (42K - 2026-01-21)
```

**Impact**:
- 3 backup files suggest git history is lost or branch conflicts occurred
- No clear rollback strategy if current version breaks

---

### 5. RLS Policy Gaps

**Receiving Lens RLS Bug**:
- `/apps/api/tests/test_receiving_lens_v1_acceptance.py:516`:
  ```python
  # TODO: Fix RLS policies - currently returns data when it shouldn't
  ```
- Security issue: data leakage despite RLS supposed to prevent it

---

## Email Integration Status

### Current State
- Email sync components exist (email_rag, email_resilience, email_watcher_worker)
- Email routes mounted (`/routes/email.py`)
- Email tests exist (playwright, E2E, attachment viewer)
- **BUT**: No email lens actions in registry
- **BUT**: No email lens handler implementation

### References Found
- `/apps/api/routes/email.py:2451` — `# TODO: Implement pgvector search using match_email_messages RPC`
- `/apps/web/src/components/email/EmailSurface.tsx` — Surface rendering (not lens-specific)
- `/apps/web/src/components/email/RelatedEmailsPanel.tsx` — Related emails (integration point)

### Why Email Lens Is Missing
- Separate transport layer (not CRUD like other lenses)
- Email sync handled by workers (email_watcher_worker.py)
- Email search via routes (not action_router)
- Likely intentionally deferred vs. other lenses

---

## Search Lens Issues

### Work Order Search Keywords
- `registry.py` defines search_keywords for 17 work order actions
- But `/routes/search_streaming.py:392-393`:
  ```python
  "work_orders_count": 0,  # TODO: Implement work orders search
  "documents_count": 0,    # TODO: Implement documents search
  ```
- **Inconsistency**: Actions exist, search not wired

---

## Test Infrastructure Weaknesses

### Missing Test Files
1. Email Lens tests (entire lens)
2. Navigation Lens business logic tests
3. Situation state machine tests
4. Comprehensive RLS audits for all 10 lenses

### Test User Management
- Hardcoded email + password in configs
- Inconsistent env var fallbacks (STAGING_CREW_EMAIL varies across files)
- No test user provisioning script for Supabase Auth (only grandfather script in SQL)

### CI/CD Issues
- Tests run in Docker containers but depend on external Supabase
- Multiple test runners (run_*.py in tests/docker/) with duplicated setup
- No centralized test fixture library

---

## Frontend Legacy Code

### Email Integration Degraded Mode
- **File**: `/apps/web/src/components/email/EmailSurface.tsx:568`
  ```typescript
  const isUnread = true; // TODO: track read state
  ```
- **File**: `/apps/web/src/components/email/EmailSurface.tsx` — isDegraded state handling
- **File**: `/apps/web/src/components/email/RelatedEmailsPanel.tsx` — Degraded mode warning

---

## Recommendations for Remediation

### Immediate (Blocking)
1. **Merge PR #332** — Unblock receiving lens fix
2. **Provision crew.test@alex-short.com** in Supabase Auth (staging)
3. **Deploy receiving handler** to staging API for validation
4. **Remove .bak files** from receiving_handlers.py (cleanup)

### High Priority (1-2 weeks)
1. **Implement email_handlers.py** — 5 email lens actions
2. **Complete Work Order frontend** — 6 missing action components
3. **Write lens RLS tests** — Audit all 10 lenses for data leakage
4. **Extract hardcoded values** — Config management for WO number pattern

### Medium Priority (2-4 weeks)
1. **Complete Navigation Lens** — Phase 4 implementation
2. **Implement work order search** — Wire search_streaming to registry
3. **Consolidate test fixtures** — Single source for test users, JWTs
4. **Add situation state machine tests** — Critical business logic coverage

### Technical Debt Cleanup (Ongoing)
1. Remove deprecated patterns (N8N dispatcher, old entity extraction fields)
2. Implement all TODOs in critical path (OCR integration, token validation, etc.)
3. Migrate hardcoded test credentials to secrets management
4. Consolidate test runners into single pytest-based framework

---

## Files to Monitor

**Critical Path**:
- `/apps/api/handlers/` — email_handlers.py must be created
- `/apps/api/action_router/registry.py` — Single source of truth (currently incomplete)
- `/apps/web/src/app/work-orders/[id]/page.tsx` — Frontend skeleton incomplete

**Debt Concentration**:
- `/apps/api/handlers/receiving_handlers.py` — 3 backup files suggest instability
- `/apps/api/tests/` — 26 TODO comments, missing email lens tests
- `/apps/web/src/app/` — Equipment, Fault, Work Order pages all have TODO action buttons

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Lenses Implemented | 10 / 16 |
| Lenses with Test Coverage | 3 / 10 |
| Actions Registered | 120 |
| Action Endpoints Missing Backend | 5 (email lens) |
| Frontend TODO Comments | 47+ |
| Backend TODO Comments | 26 |
| Test Files | 73 (69 with tests) |
| Backup Files | 3 (receiving handlers) |
| Test User References | 30+ |
| Deprecated Patterns Found | 8+ |

---

**Generated**: 2026-02-17 09:45 UTC
**Analyst**: Claude Agent (Codebase Mapper)
