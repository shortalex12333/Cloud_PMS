# SOURCE OF TRUTH — DO NOT INFER

> **This file overrides all prior chat claims. If there is a conflict, the file wins.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Locked Invariants

### UI Locks — Search Bar (ChatGPT Parity)

| Element | Status | Evidence |
|---------|--------|----------|
| Border | **REMOVED** | No `border` class in SpotlightSearch.tsx |
| Shadow | **TOKENIZED** | `--celeste-spotlight-shadow` in globals.css |
| Mic icon | **REMOVED** | Not in JSX, import removed |
| Search icon | **REMOVED** | Not in JSX, import removed |
| Category buttons | **REMOVED** | Secondary search surface JSX deleted |
| "+" button | **KEPT** | Opens Log Receiving modal, `data-testid="spotlight-add-button"` |
| Utility row | **KEPT** | Email, Menu, Settings (below search bar) |

**Deviation = Regression.** If any of these reappear:
- `border` class on main panel
- `Mic` or `Search` imports
- Category buttons array (`['Faults', 'Work Orders', ...]`)
- `--celeste-spotlight-border` token usage

### CSS Token Locations (Search Bar)
- Light shadow: `globals.css:210` → `--celeste-spotlight-shadow`
- Dark shadow: `globals.css:317` → `--celeste-spotlight-shadow`
- Component: `SpotlightSearch.tsx:786` → `shadow-[var(--celeste-spotlight-shadow)]`

### OCR Pipeline Locks
- Service runs on port 8001 (Docker)
- Engine: Tesseract (ENABLE_TESSERACT=true)
- Storage bucket: `pms-receiving-images`
- Synchronous processing: OCR runs before API response returns
- Tables written: `pms_image_uploads`, `pms_receiving_extractions`

---

## Role Permissions (CANONICAL)

### `is_hod()` Function Returns TRUE For:
```sql
'chief_engineer', 'chief_officer', 'captain', 'purser', 'manager'
```

### Action Permissions (registry.py is source of truth)

| Action | Allowed Roles | Signature Required |
|--------|---------------|-------------------|
| `create_receiving` | ALL crew (crew, deckhand, steward, chef, bosun, engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager) | No |
| `add_receiving_item` | Receiver (owner) or HOD+ | No |
| `update_receiving_fields` | Receiver (owner) or HOD+ | No |
| `accept_receiving` | chief_engineer, chief_officer, purser, captain, manager | Yes |
| `reject_receiving` | HOD+ | No |
| `view_receiving_history` | All crew | No |

### RLS Policies (pms_receiving table)

| Policy Name | Command | Check |
|-------------|---------|-------|
| `receiving_insert_hod` | INSERT | `is_hod(auth.uid(), yacht_id)` |
| `receiving_update_hod` | UPDATE | `is_hod(auth.uid(), yacht_id)` |
| `receiving_select_yacht` | SELECT | `yacht_id = get_user_yacht_id()` |
| `receiving_service_role` | ALL | service_role bypass |

**Note**: Backend uses service_role key, bypassing RLS. Action registry is the source of truth for API permissions.

---

## DB Contracts

### Core Tables (Receiving Domain)
- `pms_receiving` - Main receiving records
- `pms_receiving_items` - Line items
- `pms_receiving_documents` - Attached documents
- `pms_receiving_extractions` - OCR extraction payloads
- `pms_image_uploads` - Uploaded images with OCR results
- `pms_audit_log` - Audit trail

### Required Columns (pms_receiving_extractions)
- `id` (UUID, PK)
- `yacht_id` (UUID, FK)
- `receiving_id` (UUID, FK, nullable)
- `source_document_id` (UUID, FK)
- `payload` (JSONB) - includes `extraction_confidence` inside payload
- `created_at` (timestamp)

**Note**: No separate `confidence` or `status` columns - confidence goes inside `payload.extraction_confidence`

### RLS Verification
- Must verify after each mutation
- yacht_id isolation is mandatory
- service_role bypasses RLS (backend uses this)

---

## Test Users (Staging)

| Role | Email | Password |
|------|-------|----------|
| Captain | captain.test@alex-short.com | Password2! |
| Chief Engineer (HOD) | x@alex-short.com | Password2! |
| HOD | hod.test@alex-short.com | Password2! |
| Crew | crew.test@alex-short.com | Password2! |

**Test Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`

**Note**: Only `x@alex-short.com` and `captain.tenant@alex-short.com` exist in Supabase auth. Others may not be provisioned.

---

## Test Order (MANDATORY)

1. **DB constraints, RLS, FK** - Verify policies match expectations
2. **Backend logic** - Handler state validation, role checks
3. **Frontend UX parity** - Playwright E2E tests
4. **OCR end-to-end** - Fake invoice upload → extraction → database

---

## Current State (2026-02-17)

### Verified Working — Search Bar Phase
- [x] Shadow only, no border (ChatGPT parity)
- [x] Icons removed: Mic, Search
- [x] Category buttons removed from DOM
- [x] Shadow tokenized via `--celeste-spotlight-shadow`
- [x] Build passes
- [x] Screenshot: `~/Desktop/spotlight-tokenized-final.png`
- [x] PRs merged: #327, #328, #330

### Verified Working — OCR/Receiving
- [x] OCR pipeline synchronous processing
- [x] Docker service healthy on port 8001
- [x] Multi-role authentication (Captain, Chief Engineer)
- [x] Image upload to Supabase storage
- [x] Tesseract OCR extraction
- [x] pms_image_uploads populated
- [x] pms_receiving_extractions populated
- [x] RLS yacht isolation
- [x] "+" button opens receiving modal
- [x] Playwright receiving-plus-button-journey: 9/9 passed

### NOT Verified (Search Bar)
- [ ] Light mode rendering (only dark mode screenshotted)
- [ ] Mobile responsiveness

### Known Issues
- [x] `accept_receiving` handler missing status validation → **FIXED** (added `ALREADY_REJECTED` check, line 1275)
- [x] Tests expect wrong role permissions → **FIXED** (test expectations now match registry)
- [ ] Crew test user not in Supabase auth (`crew.test@alex-short.com` → login fails → 403)
- [ ] Handler fix not deployed to staging (reject→accept test still fails against remote API)

### Test Results Summary
| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| receiving-plus-button-journey | 9/9 | 0 | Fixed |
| receiving-COMPREHENSIVE | 8/10 | 2 | Remaining: crew user missing, handler not deployed |
| receiving-simple-test | 1/1 | 0 | |
| receiving-lens-ui-smoke | 1/1 | 0 | |

### Remaining Failures Analysis
| Test | Status | Root Cause | Fix Required |
|------|--------|------------|--------------|
| Crew create (403) | BLOCKED | `crew.test@alex-short.com` not in Supabase auth | Provision test user |
| Reject→Accept (200) | BLOCKED | Handler fix local only, not deployed to staging | Deploy `receiving_handlers.py` |

---

## Files Touched (This Session)

### Search Bar Phase (PRs #327, #328, #330)
- `apps/web/src/components/spotlight/SpotlightSearch.tsx` - Removed icons, buttons, border
- `apps/web/src/styles/globals.css` - Added `--celeste-spotlight-shadow` token
- `apps/web/src/types/actions.ts` - Added 16 missing MicroAction types
- `apps/web/src/types/workflow-archetypes.ts` - Added archetype mappings
- `apps/web/src/components/modals/AddNoteModal.tsx` - Extended EntityType

### Image-processing Repo
- `src/handlers/receiving_handler.py` - Added synchronous OCR
- `src/routes/upload_routes.py` - Added receiving_id param
- `src/models/common.py` - Added extracted_data, confidence fields
- `tests/multi_role_test.py` - Multi-role test suite
- `.env.docker` - Docker environment

### Cloud_PMS Repo
- `apps/web/tests/playwright/receiving-plus-button-journey.spec.ts` - Fixed selectors
- `apps/web/tests/playwright/receiving-COMPREHENSIVE.spec.ts` - Fixed test expectations (HOD can accept, Crew can create)
- `apps/api/handlers/receiving_handlers.py` - Added `ALREADY_REJECTED` status check (line 1275)
- `docs/OCR_ACTION_MAP.md` - Updated with evidence
- `docs/SOURCE_OF_TRUTH.md` - This file
- `docker-compose.ocr.yml` - Unified Docker compose

---

## Invariants Reaffirmed

### Search Bar
1. **No border ever** - Shadow only (ChatGPT parity)
2. **No Mic/Search icons** - Hard removed, not hidden
3. **No category buttons** - DOM deleted, not display:none
4. **Shadow must be tokenized** - Use `var(--celeste-spotlight-shadow)`

### Backend/Receiving
5. **Backend uses service_role** - RLS is bypassed; action registry controls permissions
6. **All crew can create receivings** - Intentional design (draft mode)
7. **Only HOD+ can accept** - Financial accountability
8. **Confidence goes in payload** - Not a separate column
9. **Tests must match registry** - Registry is source of truth for permissions

---

## Phase Boundaries

### Phase: Search Bar UX
- **Status**: COMPLETE
- **Verification**: Build + Screenshot
- **PRs**: #327, #328, #330
- **Safe to compact**: YES

### Phase: Next TBD
- **Status**: NOT STARTED
- **Do not proceed without explicit task assignment**
