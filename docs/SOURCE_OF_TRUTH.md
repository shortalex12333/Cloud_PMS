# SOURCE OF TRUTH — DO NOT INFER

> **This file overrides all prior chat claims. If there is a conflict, the file wins.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Operating Plan (NON-NEGOTIABLE)

### Doc Structure

**Static Docs (invariants):**
| File | Purpose |
|------|---------|
| `/docs/SOURCE_OF_TRUTH.md` | Authoritative state + invariants (THIS FILE) |
| `/docs/UI_LOCKS.md` | UI parity + styling locks |
| `/docs/DB_CONTRACT.md` | Tables, RLS, RPC rules, constraints |
| `/docs/TEST_ORDER.md` | Mandatory test order + commands |
| `/docs/HANDOFF_TEMPLATE.md` | Checkpoint format |

**GSD Planning (live state):**
| File | Purpose |
|------|---------|
| `/.planning/PROJECT.md` | Vision, stack, constraints |
| `/.planning/REQUIREMENTS.md` | v1/v2/out-of-scope scoping |
| `/.planning/ROADMAP.md` | Phases + status |
| `/.planning/STATE.md` | Decisions, blockers, position |
| `/.planning/{phase}-CONTEXT.md` | Preferences before planning |
| `/.planning/{phase}-{N}-PLAN.md` | Atomic task with XML |
| `/.claude/PROGRESS_LOG.md` | Live lens tracking |

### GSD Workflow Commands

| Command | When |
|---------|------|
| `/gsd-discuss-phase N` | Before planning — capture preferences |
| `/gsd-plan-phase N` | Research + plan + verify |
| `/gsd-execute-phase N` | Implement with atomic commits |
| `/gsd-verify-work N` | User acceptance testing |
| `/gsd-quick` | Ad-hoc tasks without full planning |
| `/gsd-progress` | Check current position |
| `/gsd-pause-work` | Create handoff mid-phase |
| `/gsd-resume-work` | Restore from last session |

### Rules
1. **SOURCE OF TRUTH RULE**: If chat conflicts with this file, the file wins
2. **PHASE GATING**: Work ONLY on currently declared phase; out-of-scope items go to Backlog
3. **CONTEXT LIMIT SAFETY**: ~65% warn, ~70% stop new work, 75%+ HARD STOP with checkpoint
4. **ZERO-BS COMPLETION**: No "done" without evidence (tests/screenshots/diffs)
5. **PLUGIN USAGE**: Use typescript-lsp, playwright, supabase, etc. to verify, don't assume

### Phase Sequence (GSD)
1. Discuss (capture preferences → CONTEXT.md)
2. Plan (research + XML plans → PLAN.md)
3. Execute (atomic commits per task)
4. Verify (UAT → fixes if needed)
5. Update docs + STATE.md

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
| `create_receiving` | ALL crew | No |
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

---

## Test Users (Staging)

| Role | Email | Password |
|------|-------|----------|
| Captain | captain.test@alex-short.com | Password2! |
| Chief Engineer (HOD) | x@alex-short.com | Password2! |
| HOD | hod.test@alex-short.com | Password2! |
| Crew | crew.test@alex-short.com | Password2! |

**Test Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`

**Note**: Only `x@alex-short.com` and `captain.tenant@alex-short.com` exist in Supabase auth.

---

## Current State (2026-02-17)

### Milestone M1: Lens Completion

| Phase | Lens | Status | Blockers |
|-------|------|--------|----------|
| 1 | Receiving | 80% | PR #332, crew user, staging deploy |
| 2 | Parts/Inventory | 0% | - |
| 3 | Equipment | 0% | - |
| 4 | Faults | 0% | - |
| 5 | Work Orders | 0% | - |
| 6 | Certificates | 0% | - |
| 7 | Handover | 0% | - |
| 8 | Hours of Rest | 0% | - |
| 9 | Warranty | 0% | - |
| 10 | Shopping List | 0% | - |
| 11 | Email | 0% | Handler not created |

### Verified Working — Search Bar Phase
- [x] Shadow only, no border (ChatGPT parity)
- [x] Icons removed: Mic, Search
- [x] Category buttons removed from DOM
- [x] Shadow tokenized via `--celeste-spotlight-shadow`
- [x] Build passes
- [x] PRs merged: #327, #328, #330

### Known Issues
- [x] `accept_receiving` handler missing status validation → **FIXED**
- [x] Tests expect wrong role permissions → **FIXED**
- [ ] Crew test user not in Supabase auth
- [ ] Handler fix not deployed to staging

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

### Phase: Search Bar UX (M0)
- **Status**: COMPLETE
- **Verification**: Build + Screenshot
- **PRs**: #327, #328, #330

### Phase: Lens Completion (M1)
- **Status**: IN_PROGRESS
- **Current**: Phase 1 (Receiving) at 80%
- **Next**: Await GSD command to proceed
