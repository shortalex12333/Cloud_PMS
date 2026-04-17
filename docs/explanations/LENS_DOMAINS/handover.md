# Handover — Complete Feature Explanation

**Written by:** HANDOVER01 (2026-04-17 (updated))  
**For:** Any new engineer, agent, or worker picking up this feature  
**Repo:** `Cloud_PMS` — `shortalex12333/Cloud_PMS`  
**Scope:** Everything about the handover feature — frontend, backend, DB, microservice, ledger, bugs, traps, limitations  
**Updates:** Updated with PRs #607-636 and 39/39 test results  
**Test status: 39/39 CLEAN PASS (Apr 17, 2026)**

---

## 1. What This Feature Is (Plain English)

When a crew member finishes their rotation on a yacht and someone new comes on board, there needs to be a formal knowledge transfer. Traditionally this is a Word document written at 10pm on the last night, with no structure, no accountability, and no links to actual records.

CelesteOS replaces that. Throughout the rotation, crew members tap a button ("Add to Handover") on any fault, work order, equipment record, or part to queue it. When it's time to hand over, one click assembles everything into a professional, structured, LLM-processed document. The outgoing crew signs it. The HOD (Head of Department) reviews and countersigns. The incoming crew receives it and signs to acknowledge. The ledger records the whole chain permanently.

Every role generates their own handover — deckhand, stew, engineer, captain. Each scoped to their department.

---

## 2. The User Journey (Step by Step)

### Step 1 — Tagging items (throughout the rotation)
- Crew member is on a fault lens, work order lens, or parts page
- Clicks "Add to Handover" action button
- A popup appears — summary is **pre-filled** from the entity data (no typing required)
- Category auto-set: fault → `urgent`, part → `fyi`, etc.
- One tap confirm → item lands in `handover_items` table
- **Critical items** immediately trigger a ledger notification to all HOD-level users on the vessel

### Step 2 — Viewing draft items
- Navigate to `/handover-export`
- Two tabs: **Queue** (auto-detected candidates) and **Draft Items** (things already added)
- Queue shows: Open Faults / Overdue Work Orders / Low Stock Parts / Pending Purchase Orders
- Each queue row has `+ Add` button — tapping it runs the same add_to_handover action
- Draft Items tab shows all `handover_items` for this user, grouped by day (Today expanded)
- Click any item → popup to Edit / Delete
- Click "Add Note" → create a freetext note (not linked to any entity)

### Step 3 — Generating the export
- Click "Export" button in Draft Items tab
- Frontend POSTs to `POST /v1/handover/export` on Render API
- Render fetches all the user's pending handover_items
- Render calls the **handover-export microservice** (separate service at `handover-export.onrender.com`)
- Microservice runs LLM pipeline: classify → group → merge → render Jinja2 HTML
- Returns professional HTML document + structured sections JSON
- Render writes: `handover_entries`, `handover_drafts`, `handover_draft_sections`, `handover_draft_items`, `handover_exports` to TENANT DB
- Ledger event fires → HOD notified to review
- User is redirected to `/handover-export/{export_id}`

### Step 4 — Reviewing and signing
- User sees generated document at `/handover-export/{export_id}`
- Document is editable while `review_status = 'pending_review'` (contentEditable inline)
- Can save edits via `POST /v1/handover/export/{id}/save-draft`
- User draws signature on canvas → "Confirm & Sign"
- POSTs to `/v1/handover/export/{id}/submit`
- `review_status` moves to `pending_hod_signature`
- HOD notified via ledger_events

### Step 5 — HOD countersign
- HOD sees notification in ledger panel
- Reviews document → countersigns
- POSTs to `/v1/handover/export/{id}/countersign`
- `review_status` moves to `complete`
- Captain + Manager notified via ledger_events
- Document indexed for search

### Step 6 — Incoming crew receives
- Incoming crew member sees the completed handover on their device
- Reads it, signs to acknowledge (uses same `/sign/incoming` route)
- `signoff_complete = true` in `handover_signoffs` table

---

## 3. Architecture — Three Layers

```
LAYER 1: FRONTEND (Vercel — Next.js App Router)
  app.celeste7.ai
  Supabase client → MASTER DB only (auth only)
  All operational data → via Render API

LAYER 2: API (Render — Python FastAPI)
  pipeline-core.int.celeste7.ai
  Service-role access to TENANT DB
  Validates MASTER JWT, then hits TENANT for all data

LAYER 3: MICROSERVICE (Render — Python FastAPI)
  handover-export.onrender.com
  Stateless — receives items JSON, returns HTML + sections
  No DB access. OpenAI GPT-4o-mini only.
  Env flag: HANDOVER_USE_MICROSERVICE=true (in celeste-unified)
```

### Two Supabase Projects — CRITICAL

```
MASTER:  qvzmkaamzaqxpzbewjxe.supabase.co  → auth + user directory only
TENANT:  vzsohavtuotocgrfkfyd.supabase.co  → ALL operational data
```

The frontend's `supabase` client (from `supabaseClient.ts`) points at **MASTER** via `NEXT_PUBLIC_SUPABASE_URL`. This is correct for auth. It is **completely wrong** for operational tables. Do not call `supabase.from('handover_items')` or any PMS table directly from the frontend — those tables don't exist in MASTER. You will get a 400 with no useful error message.

All operational reads/writes from frontend → Render API → TENANT DB.

---

## 4. Database Tables

All tables live in **TENANT DB** (`vzsohavtuotocgrfkfyd`).

### Primary tables

| Table | Purpose | Key columns |
|---|---|---|
| `handover_items` | The draft queue. One row per "Add to Handover" tap | `id, yacht_id, added_by, entity_type, entity_id, summary, category, section, is_critical, export_status, status, deleted_at` |
| `handover_exports` | The generated document record | `id, yacht_id, draft_id, review_status, outgoing_signed_at, incoming_signed_at, hod_signed_at, signoff_complete, document_hash, original_storage_url, signed_storage_url` |
| `handover_drafts` | The LLM-assembled document metadata | `id, yacht_id, state, period_start, period_end, department, generated_by_user_id, total_entries, critical_entries` |
| `handover_draft_sections` | Department sections within a draft | `id, draft_id, bucket_name, section_order, display_title, item_count, critical_count` |
| `handover_draft_items` | Individual LLM-summarised items | `id, draft_id, section_id, section_bucket, summary_text, domain_code, is_critical, item_order, entity_url, source_entry_ids` |
| `handover_entries` | Immutable truth seeds from LLM merge | `id, yacht_id, narrative_text, source_entity_type, is_critical, status` — **NO DELETE policy — permanent** |
| `handover_signoffs` | Outgoing/incoming signature records | `id, draft_id, outgoing_user_id, outgoing_signed_at, incoming_user_id, incoming_signed_at, signoff_complete, document_hash` |
| `handover_sources` | Email/document sources for handover items | `id, yacht_id, source_type, is_processed, classification` |

### Views

| View | What it does |
|---|---|
| `v_handover_draft_complete` | Aggregates draft + sections as nested JSON. Use this to fetch a full document in one query. |
| `v_handover_export_items` | Items joined to their section with section title, order, entity links. Use for export rendering. |
| `v_handover_signoffs` | Flattens outgoing/incoming as separate rows with `signoff_type` column. |

### Audit / Notification tables

| Table | Purpose |
|---|---|
| `pms_audit_log` | Immutable compliance trail. One row per action per actor. Never deleted. |
| `ledger_events` | Notification bus. Frontend polls/subscribes. Each row is a notification TO a specific `user_id`. |

### Handover item `status` values

```
status column:       pending | acknowledged | completed | deferred
export_status col:   pending | exported
```

Do not use `status="exported"` — that column has a check constraint. The export tracking uses `export_status`.

### `handover_exports.review_status` state machine

```
pending_review → pending_hod_signature → complete
```

`save-draft` requires `pending_review`. `submit` requires `pending_review`. `countersign` requires `pending_hod_signature`.

---

## 5. Frontend Files — Exact Paths

```
apps/web/src/
├── app/
│   └── handover-export/
│       ├── page.tsx                    ← Queue + Draft Items tabs
│       └── [id]/
│           └── page.tsx                ← Generated document detail page
│
├── components/
│   ├── handover/
│   │   ├── HandoverDraftPanel.tsx      ← Draft items list, CRUD, export button
│   │   └── HandoverQueueView.tsx       ← Auto-detected candidate items
│   └── lens-v2/
│       └── entity/
│           └── HandoverContent.tsx     ← The rendered document + signing UI
│
├── lib/
│   ├── handoverExportClient.ts         ← API client helpers for handover export
│   └── microactions/
│       └── handlers/
│           └── handover.ts             ← Microaction handler for add_to_handover
│
└── components/shell/
    └── api.ts                          ← fetchHandoverQueue() lives here (line ~226)
```

### Key component details

**`HandoverDraftPanel.tsx`**
- Two variants: `drawer` (slides in from right, 460px) and `page` (inline, for the tab)
- Reads items via `GET /v1/handover/items` (Render API — NOT direct Supabase)
- Groups by day, collapsible, Today expanded by default
- `ItemPopup` handles Edit / Add / Delete modes
- Export button → `POST /v1/handover/export` → redirects to `/handover-export/{id}`
- After export, calls `POST /v1/handover/items/mark-exported` to update status

**`HandoverQueueView.tsx`**
- Calls `fetchHandoverQueue(vesselId)` → `GET /v1/actions/handover/queue` (note: this is under `/v1/actions/` prefix, not `/v1/handover/`)
- Four sections: Open Faults, Overdue Work Orders, Low Stock Parts, Pending Purchase Orders
- Each item has `+ Add` → `POST /v1/actions/execute` with `action: 'add_to_handover'`
- Already-queued items show green `✓ Added` (optimistic set of `entity_id`s)

**`HandoverContent.tsx`**
- The detail lens for a completed export
- Renders the document HTML inline (cover, TOC, sections, items, entity links)
- Inline editing when `status === 'pending_review'` (uses `contentEditable`)
- Signature block: two columns (Prepared By / Reviewed By) — currently static layout
- "Sign Handover" button → canvas wet-signature modal → `executeAction('sign_handover')`
- **Gap:** The action ID in the component is `sign_handover` but the registry has `sign_handover_outgoing` and `sign_handover_incoming`. The button is present but the action doesn't resolve. This is the next thing to fix.
- "Export PDF" → `window.print()`

---

## 6. Backend Files — Exact Paths

```
apps/api/
├── routes/
│   ├── handover_export_routes.py       ← ALL handover HTTP endpoints
│   │                                      prefix: /v1/handover
│   │                                      Endpoints: /export, /exports, /export/{id},
│   │                                                /export/{id}/content,
│   │                                                /export/{id}/save-draft,
│   │                                                /export/{id}/submit,
│   │                                                /export/{id}/countersign,
│   │                                                /items (GET/PATCH/DELETE),
│   │                                                /items/mark-exported
│   │
│   ├── p0_actions_routes.py            ← Action execution + handover queue
│   │                                      prefix: /v1/actions
│   │                                      Key endpoints: /handover/queue, /handover (GET items legacy)
│   │
│   └── handlers/
│       ├── handover_handler.py         ← Delegates add_to_handover_execute to HandoverHandlers
│       └── ledger_utils.py             ← build_ledger_event() helper — used everywhere
│
├── handlers/
│   ├── handover_handlers.py            ← HandoverHandlers class
│   │                                      add_to_handover_prefill()
│   │                                      add_to_handover_execute()   ← MAIN add path
│   │                                      edit_handover_item_execute()
│   │                                      export_handover_execute()
│   │                                      regenerate_handover_summary_execute()
│   │
│   └── handover_workflow_handlers.py   ← HandoverWorkflowHandlers class
│                                          sign_outgoing(), sign_incoming()
│                                          get_pending_handovers()
│                                          _notify_ledger_export_ready()
│
├── services/
│   ├── handover_export_service.py      ← HandoverExportService, create_export_ready_ledger_event()
│   ├── handover_html_parser.py         ← Parses generated HTML back into editable sections
│   └── handover_microservice_client.py ← HTTP client that calls handover-export.onrender.com
│
└── action_router/
    ├── registry.py                     ← Action definitions (line ~905: add_to_handover)
    ├── dispatchers/
    │   └── internal_dispatcher.py      ← add_to_handover() function (line ~705)
    │                                      THIS is what the action router actually calls
    └── ledger_metadata.py              ← Maps action IDs to ledger event types
```

### Two `add_to_handover` paths — understand this or you will be confused

There are **two separate code paths** for adding a handover item:

**Path A — Action Router (primary, used by frontend Queue + entity lens):**
```
POST /v1/actions/execute {action: 'add_to_handover'}
  → action_router/router.py
  → INTERNAL_HANDLERS["add_to_handover"]  (registry.py line ~905)
  → internal_dispatcher.py::add_to_handover()  (line ~705)
  → direct INSERT into handover_items
```

**Path B — Handler route (secondary, called via p0_actions_routes.py):**
```
Some routes in p0_actions_routes.py (line ~177, ~201)
  → routes/handlers/handover_handler.py::add_to_handover_action()
  → handlers/handover_handlers.py::HandoverHandlers.add_to_handover_execute()
  → INSERT into handover_items
```

Both paths insert into `handover_items`. Both have been fixed with `category_map`, correct column names, and critical cascade. But if you only fix one, the other breaks silently.

---

## 7. The Action Router — How "Add to Handover" Works

When a user clicks `+ Add` on the Queue page or "Add to Handover" from an entity lens:

1. Frontend calls `POST /v1/actions/execute` with:
   ```json
   {
     "action": "add_to_handover",
     "context": { "yacht_id": "..." },
     "payload": {
       "entity_type": "fault",
       "entity_id": "uuid",
       "summary": "Equipment name — Fault code",
       "category": "standard",
       "section": "Engineering"
     }
   }
   ```

2. Action router validates JWT → extracts `user_id`, `yacht_id`, `role` from token
3. Checks `add_to_handover` allowed_roles: `["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]`
4. Validates `required_fields: ["summary"]`
5. Dispatches to `internal_dispatcher.py::add_to_handover()`
6. Category normalised: `critical→urgent`, `standard→fyi`, `low→fyi`
7. Entity ownership verified (fault/WO/equipment confirmed to belong to this yacht)
8. Row inserted into `handover_items`
9. Audit log written to `pms_audit_log`
10. If `is_critical=True`: ledger notification fired to all HOD+ users on yacht

### Prefill — auto-populated summaries

Before the user confirms, `GET /v1/actions/add_to_handover/prefill` can be called to get pre-populated fields:

- **Fault** → summary = `{equipment_name} — {fault_code}\n{description}`, category = `ongoing_fault`
- **Work Order** → summary = `WO-{number}: {title}\nEquipment: {name}\nStatus: {status}`, category = `work_in_progress`
- **Equipment** → summary = `{name} ({manufacturer} {model})\nLocation: {location}`, category = `equipment_status`
- **Part** → summary = `{name} ({part_number})\nStock: {qty} ({stock_status})`, category = `general`

This means the user almost never has to type. The form arrives pre-filled.

---

## 8. The LLM Microservice

**Repo:** `github.com/shortalex12333/handover_export`  
**URL:** `https://handover-export.onrender.com`  
**Feature flag:** `HANDOVER_USE_MICROSERVICE=true` (set in Render env for celeste-unified)  
**Local:** runs on `:10000` via `docker compose up` in the `handover_export` repo

### What it does

Takes raw `handover_items` (JSON array), returns professional HTML + structured sections. No DB. No storage. Stateless.

### Pipeline

```
Input: [{entity_type, summary, category, is_critical, entity_url, ...}]

Stage 1 — CLASSIFY (GPT-4o-mini, concurrent, semaphore=10)
  Each item gets a maritime department bucket:
  Electrical | Projects | Financial | Galley/Laundry | Risk |
  Admin/Compliance | Fire Safety | Tenders | Logistics | Deck | General

Stage 2 — GROUP
  Items grouped by bucket. Only merges items with same entity_id (true duplicates).

Stage 3 — MERGE (GPT-4o-mini, concurrent, semaphore=5)
  Each group → one professional summary in 2nd person ("You need to...")
  Preserves ALL specifics: part numbers, vendor names, measurements, dates.
  Extracts action items with priority tags: CRITICAL | HIGH | NORMAL

Stage 4 — RENDER (Jinja2)
  templates/handover_report.html
  A4-ready HTML: cover page, TOC, sections by department, items numbered,
  entity deep links ("View Fault →"), dual signature block, footer with hash
```

### Key design decisions

- Every item preserved (no AI curation of what to include)
- Detail preservation over brevity (the merge prompt explicitly instructs GPT to keep all specifics)
- System fonts only (no Google CDN — yacht satellite internet)
- `autoescape=True` in Jinja2 (prevents XSS from LLM output)
- SHA-256 of rendered HTML = `document_hash` (tamper evidence)

### If the microservice is down

Fallback path exists in `handover_export_routes.py`. If the microservice call fails, the old basic HTML export runs instead (less structured, no LLM processing).

---

## 9. Ledger + Notification Cascade

### Tables

- `pms_audit_log` — compliance trail. Every significant write gets one row. Has `old_values` / `new_values` jsonb. Never deleted.
- `ledger_events` — notification bus. Frontend subscribes. Each row is a notification TO a `user_id`. Frontend shows these as the "recent activity" ledger panel.

### Helper functions (in `handover_export_routes.py`)

```python
_get_role_users(db, yacht_id, roles)
  # Queries auth_users_roles (NOT auth_users_profiles — see bugs section)
  # Returns [{user_id, role, department, name}]

_write_handover_event(db, yacht_id, actor_id, actor_role, target_user_id,
                       entity_id, event_type, action, change_summary, ...)
  # Writes one row to pms_audit_log AND one row to ledger_events
  # Both writes in try/except — never raises, never blocks the main action
```

### Cascade hierarchy

```
CREW adds critical item
  └─ ledger_events → all chief_engineer, chief_officer, captain on yacht
     action: "critical_item_added"  event_type: "escalation"

CREW deletes draft item
  └─ ledger_events → all chief_engineer, chief_officer, captain
     action: "draft_item_deleted"   event_type: "delete"

CREW submits (signs) export
  └─ ledger_events → all chief_engineer, chief_officer, captain
     action: "requires_countersignature"  event_type: "handover"
     (This is _notify_hod_for_countersign — fixed from broken version)

HOD countersigns
  └─ ledger_events → all captain, manager
     action: "handover_countersigned"  event_type: "handover"

EDIT / save-draft / mark-exported
  └─ pms_audit_log only (actor-only, no notification cascade)
```

### Role lookup table

```
auth_users_roles (TENANT DB)
  columns: id, user_id, yacht_id, role, department, is_active, assigned_at
  roles: crew | engineer | eto | chief_engineer | chief_officer | captain | manager
```

---

## 10. Domain Interactions

The handover feature is connected to every other domain in the PMS. Here is what it reads from each:

| Domain | Table | Why handover reads it |
|---|---|---|
| Faults | `pms_faults` | Prefill for add_to_handover. Queue auto-detection (open faults). |
| Work Orders | `pms_work_orders` | Prefill. Queue auto-detection (overdue WOs). |
| Equipment | `pms_equipment` | Prefill (equipment name, location, manufacturer). |
| Parts/Inventory | `pms_parts`, `pms_part_stock` | Queue auto-detection (low stock). Prefill with stock levels. |
| Purchase Orders | `pms_purchase_orders` | Queue auto-detection (pending orders). |
| Documents | `documents` | Can be added to handover via entity lens. |
| Certificates | `pms_vessel_certificates`, `pms_crew_certificates` | Relevant for vessel-level handover (expiring certs = critical items). |
| Crew / Roles | `auth_users_roles` | HOD lookup for cascade notifications. Incoming crew selection. |
| Ledger | `ledger_events`, `pms_audit_log` | Written to on every handover state change. |
| Search index | `search_index` | Written to after countersign for full-text search. |
| Supabase Storage | bucket: `handover-exports` | HTML documents stored at `{yacht_id}/original/{draft_id}.html` and `{yacht_id}/signed/{export_id}.html` |

---

## 11. Bugs Found and Fixed (This Session)

These are real bugs that were in production. Know them so you don't reintroduce them.

### Bug 1 — HandoverDraftPanel hitting MASTER DB
**Symptom:** `POST https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/handover_items 400 (Bad Request)`  
**Cause:** `HandoverDraftPanel.tsx` used `supabase.from('handover_items')` — the frontend supabase client points at MASTER, not TENANT. `handover_items` doesn't exist in MASTER.  
**Fix:** All 6 direct supabase DB calls replaced with `fetch(RENDER_API_URL/...)`. Auth token still comes from `supabase.auth.getSession()` (correct — MASTER JWT).  
**File:** `apps/web/src/components/handover/HandoverDraftPanel.tsx`

### Bug 2 — Wrong column names in internal_dispatcher insert
**Symptom:** `handover_items` insert silently failed or wrote to wrong fields  
**Cause:** `internal_dispatcher.py::add_to_handover` used `summary_text` (no such column — it's `summary`) and `added_at` (no such column — DB uses `created_at` with default). Also lacked `is_critical`, `export_status`, `status` fields.  
**Fix:** Corrected all field names. Added all required fields.  
**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`

### Bug 3 — Category validation rejected new UI values
**Symptom:** `POST /v1/actions/execute` with `category='standard'` or `category='critical'` → "Invalid category" error  
**Cause:** Backend only accepted `["urgent", "in_progress", "completed", "watch", "fyi"]`. Frontend sends `critical | standard | low`.  
**Fix:** Added `category_map` in both `internal_dispatcher.py` and `handover_handlers.py`. `critical→urgent`, `standard→fyi`, `low→fyi`. Normalisation happens before validation.  
**Files:** `apps/api/action_router/dispatchers/internal_dispatcher.py`, `apps/api/handlers/handover_handlers.py`

### Bug 4 — `crew` role blocked from add_to_handover
**Symptom:** `engineer.test@alex-short.com` (role: crew) got "Role 'crew' is not authorized"  
**Cause:** `allowed_roles` in registry.py for `add_to_handover` didn't include `crew`. Every rank should be able to add items.  
**Fix:** Added `crew` to `allowed_roles`. Also fixed `required_fields` from `["yacht_id", "title"]` (title doesn't exist in payload) to `["summary"]`.  
**File:** `apps/api/action_router/registry.py` line ~911

### Bug 5 — `_notify_hod_for_countersign` queried wrong table
**Symptom:** Zero HOD notifications ever sent on handover submission. Silent failure.  
**Cause:** The function queried `auth_users_profiles` for a `role` column. That table has no `role` column. `role` lives in `auth_users_roles`. The query returned 0 rows silently.  
**Fix:** Replaced entire function body with `_get_role_users(supabase, yacht_id, ["chief_engineer", "chief_officer", "captain"])` which queries the correct table.  
**File:** `apps/api/routes/handover_export_routes.py` line ~1262

### Bug 6 — PATCH/DELETE missing ownership check
**Symptom:** Any user on a yacht could edit or delete any other user's handover item  
**Cause:** Agent-introduced regression. The `.eq("added_by", user_id)` filter was dropped from both the PATCH and DELETE queries.  
**Fix:** Restored `.eq("added_by", user_id)` to both. DELETE also restored `deleted_by` and `deletion_reason` fields.  
**File:** `apps/api/routes/handover_export_routes.py`

### Bug 7 — mark-exported used wrong column
**Symptom:** `POST /v1/handover/items/mark-exported` would try to set `status="exported"` — check constraint violation  
**Cause:** The `status` column has a check constraint: only `pending | acknowledged | completed | deferred`. Export tracking uses the separate `export_status` column.  
**Fix:** Changed to `export_status="exported"`, `status="completed"`. Removed invented `exported_at` column (doesn't exist).  
**File:** `apps/api/routes/handover_export_routes.py`

### Bug 8 — Auth race silent save
**Symptom:** Popup closed with no toast, no error when `user.id` was null  
**Cause:** `if (!user?.id) return;` at `HandoverDraftPanel.tsx:533` silently returned  
**Fix:** Added `userReady` flag, disabled buttons until auth loaded. PR #607  
**File:** `apps/web/src/components/handover/HandoverDraftPanel.tsx:506, 371, 478`

### Bug 9 — Slow + Add with no optimistic update
**Symptom:** 2-5 second delay before button changed to "Added"  
**Cause:** Button only flipped after full Render API round-trip at `HandoverQueueView.tsx:325`  
**Fix:** Optimistic flip before API call, revert on error. PR #616  
**File:** `apps/web/src/components/handover/HandoverQueueView.tsx:298-332`

### Bug 10 — Export gave no timing feedback
**Symptom:** User saw nothing during 30-120s LLM export  
**Fix:** Immediate toast "Generating handover — up to 2 minutes" + 10s persistent success toast. PR #616  
**File:** `apps/web/src/components/handover/HandoverDraftPanel.tsx:610-635`

---

## 12. What I Wish I Knew at the Start

**1. There are two add_to_handover code paths.** Both insert into `handover_items`. If you fix the dispatcher, the handler path is still broken. If you fix the handler path, the dispatcher is still broken. They are completely independent. Always fix both.

**2. The frontend supabase client is MASTER-only.** Never call `supabase.from(any_pms_table)` from the frontend. Always go through `fetch(RENDER_API_URL/...)`. The error you get (400 from MASTER) has no useful message about the table not existing.

**3. `auth_users_profiles` has no `role` column.** Role lives in `auth_users_roles`. Name map:
   - `auth_users_profiles`: `id, yacht_id, email, name, is_active`
   - `auth_users_roles`: `id, user_id, yacht_id, role, department, is_active`

**4. `p0_actions_routes.py` has prefix `/v1/actions`.** So `GET /handover` inside that file is actually `/v1/actions/handover`. The handover export routes are separate with prefix `/v1/handover`. This trips you up when adding new handover endpoints — put them in `handover_export_routes.py`, not `p0_actions_routes.py`.

**5. `handover_items.status` vs `handover_items.export_status`.** Two separate columns. `status` tracks workflow state (pending/completed). `export_status` tracks whether items have been pulled into an export (pending/exported). Using the wrong one causes check constraint failures.

**6. The microservice is feature-flagged.** `HANDOVER_USE_MICROSERVICE=true` in the Render environment. In local Docker without this flag, the old basic HTML fallback runs. You will not see the LLM output locally unless you run the handover_export repo separately on `:10000`.

**7. Test data has 82+ HOD users.** Don't panic when you see 82 ledger_events for one critical item add. The test yacht has been seeded with dozens of test users. In real production there are 2-5.

**8. The action registry `required_fields` is validated before dispatch.** If you add a new field that the payload needs to send but it's not in `required_fields`, the action will pass validation even without it. And if a field IS in `required_fields` but the frontend doesn't send it, you'll get a 400 at the gateway. `required_fields` in the registry is the contract.

**9. `handover_entries` has no DELETE policy.** These are the LLM truth seeds — immutable by design. You can never clean them up even in tests. Don't insert junk data into this table.

**10. `HandoverContent.tsx` reads `entity.sections` but the entity lens endpoint doesn't join to sections.** The document body shows "No handover content available" even for real exports because the entity handler returns `handover_exports` without joining `handover_draft_sections` / `handover_draft_items`. This is the next unfixed gap.

---

## 13. Open Gaps and Limitations

These are known, intentional gaps — not bugs. They need to be built.

### Gap 1 — HandoverContent signing action ID mismatch (NEXT PRIORITY)
`HandoverContent.tsx` calls `executeAction('sign_handover', ...)` and checks `getAction('sign_handover')`. The registry has `sign_handover_outgoing` and `sign_handover_incoming`. There is no `sign_handover`. `canSign` is always false — the sign button never shows.
**Fix:** Line 103 in `HandoverContent.tsx`: change `getAction('sign_handover')` to `getAction('sign_handover_outgoing') ?? getAction('sign_handover_incoming')`. Fix `handleSignConfirm` to dispatch the right action ID based on which is available.

### Gap 2 — Entity lens doesn't return `sections` data
`HandoverContent.tsx` reads `entity.sections` to render the document body. The entity handler for `handover_export` returns the raw DB row, which has no `sections`. Sections live in `v_handover_draft_complete`.
**Fix:** In the entity handler for `handover_export`, after fetching the row, fetch `v_handover_draft_complete` by `draft_id` and attach `sections`.

### Gap 3 — No department/role filter on export
`ExportRequest` has `filter_by_user` but no `department` filter. A captain's export includes all items from all crew. A deckhand's export includes only their items because `filter_by_user=true` scopes to `added_by=user_id`.
For a proper crew handover (scoped to their department), you'd want to also filter by `section` or `department`. Not implemented.

### Gap 4 — No incoming crew selector in the export flow
When exporting, there's no UI step to nominate the incoming crew member. `incoming_user_id` in `handover_exports` is always NULL until the incoming person actively signs.
**Simple fix:** Add a `Select incoming crew member` optional dropdown before triggering export. Pull from `auth_users_roles` where `role = outgoing user's role` and `yacht_id = vessel`.

### Gap 5 — Vessel-level handover not implemented
The marketing material describes a "vessel handover" — pulls all items across all crew, appends certificate status, open warranty claims, overdue PMS tasks. The DB has `handover_type` discussed but not implemented. Only crew-level handovers (scoped to one user) exist.

### Gap 6 — PDF export is `window.print()`
The "Export PDF" button calls `window.print()`. This uses the browser print dialog. It works but has no server-side PDF generation, no consistent formatting across environments, no stored PDF.
WeasyPrint is installed in the handover_export microservice — a proper PDF endpoint could be added there.

---

## 14. How to Test Locally

### Run the API

```bash
cd /Users/celeste7/Documents/Cloud_PMS
docker compose --profile api up --build
# API available at http://localhost:8000
```

### Run the microservice (for LLM export)

```bash
cd /Users/celeste7/Documents/handover_export
docker compose up --build
# Microservice available at http://localhost:10000
# But celeste-unified calls handover-export.onrender.com by default
# To use local: set HANDOVER_MICROSERVICE_URL=http://host.docker.internal:10000
```

### Test credentials

```
crew:         engineer.test@alex-short.com    / Password2!
captain:      x@alex-short.com               / Password2!
test yacht:   85fe1119-b04c-41ac-80f1-829d23322598
```

### Verify a full add_to_handover flow

```bash
# Get token
TOKEN=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: {MASTER_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer.test@alex-short.com","password":"Password2!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Add a standard note
curl -X POST "http://localhost:8000/v1/actions/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"add_to_handover","context":{},"payload":{"entity_type":"note","summary":"Test note","category":"standard","section":"Engineering"}}'

# Add a critical note (triggers HOD cascade)
curl -X POST "http://localhost:8000/v1/actions/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"add_to_handover","context":{},"payload":{"entity_type":"note","summary":"Critical engine alarm","category":"critical","section":"Engineering"}}'

# List items
curl "http://localhost:8000/v1/handover/items" -H "Authorization: Bearer $TOKEN"
```

### Verify DB

```bash
psql "postgresql://postgres:%40-Ei-9Pa.uENn6g@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT action, count(*) FROM pms_audit_log WHERE action LIKE '%handover%' GROUP BY action;"
```

---

## 15. Role Matrix

Who can see and do what on the handover page.

| Action | crew | engineer / eto | chief_engineer / chief_officer | captain | manager |
|---|---|---|---|---|---|
| Add item to handover | ✓ | ✓ | ✓ | ✓ | ✓ |
| View own draft items | ✓ | ✓ | ✓ | ✓ | ✓ |
| Edit own draft items | ✓ | ✓ | ✓ | ✓ | ✓ |
| Delete own draft items | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export (generate document) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Submit (sign outgoing) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Countersign (HOD review) | ✗ | ✗ | ✓ | ✓ | ✓ |
| Sign incoming (acknowledge) | ✓ | ✓ | ✓ | ✓ | ✓ |
| View any export on yacht | ✗ | ✗ | ✓ | ✓ | ✓ |
| Receive critical cascade notification | ✗ | ✗ | ✓ | ✓ | — |
| Receive countersign-complete notification | ✗ | ✗ | ✗ | ✓ | ✓ |

**Note:** "View own draft items" means items where `added_by = user_id`. HOD+ can view all exports on their yacht via the exports list endpoint.

The countersign route enforces roles in code:
```python
# handover_export_routes.py — countersign_export()
if auth['role'] not in ["hod", "captain", "manager"]:
    raise HTTPException(status_code=403, detail="Only HOD+ can countersign")
```
Note: The original code checked `["hod", "captain", "manager"]`. `"hod"` is not a real DB role — actual values are `chief_engineer` and `chief_officer`. This was a live bug (any chief engineer would get a 403). Fixed to `["chief_engineer", "chief_officer", "captain", "manager"]` in PR #527.

---

## 16. Business Rules and Enforcement

These are the rules the backend enforces — not suggestions, not frontend-only. Backend validates all of these.

### Ownership on mutations
Every `PATCH /items/{id}` and `DELETE /items/{id}` requires `.eq("added_by", user_id)`. You cannot edit or delete another user's handover item, even if you are on the same yacht. The 404 you get is intentional — it reveals no information about whether the item exists at all.

### Category normalisation (not validation)
The backend accepts `critical | standard | low` (new UI values) as well as `urgent | in_progress | completed | watch | fyi` (legacy DB values). They are normalised before storage:
```
critical  → urgent    (+ sets is_critical=True)
standard  → fyi
low       → fyi
```
The DB `category` column stores only the legacy values. The frontend sends new UI values. Both must be kept in sync.

### `handover_entries` are immutable
The `handover_entries` table has **no DELETE RLS policy**. These are the LLM truth seeds — the original AI-processed summaries before any editing. Once written, they cannot be deleted. Do not seed test data into this table unless you can live with it permanently.

### `handover_exports` state machine
State transitions are enforced by checking `review_status` before each operation:
```
pending_review
  → save-draft:   allowed (can keep editing)
  → submit:       allowed (moves to pending_hod_signature)
  → countersign:  REJECTED (409 — "Not awaiting countersign")

pending_hod_signature
  → save-draft:   REJECTED (400 — "Cannot edit after submission")
  → submit:       REJECTED (400 — "Already submitted")
  → countersign:  allowed (moves to complete)

complete
  → anything:     REJECTED (all mutation routes check status)
```

### Document hash (tamper evidence)
After countersign, `document_hash` = SHA-256 of the rendered HTML. If the HTML is changed after signing, the hash will not match. This is not cryptographically enforced in code today (there is no re-hash-and-compare on read), but the hash is recorded permanently in `pms_audit_log` and `ledger_events` for manual verification.

### Duplicate items are allowed
The `add_to_handover` handler checks for duplicates (`entity_type + entity_id` already in handover_items) but explicitly allows them:
```python
# Note: We allow duplicates for now — multiple shifts may reference same entity
```
This means a fault can be added to handover twice. The LLM merge stage deduplicates only when `entity_id` is identical (true duplicates). Multiple rotation mentions of the same fault are treated as separate items.

### Summary minimum length
3 characters. This was changed from 10 during this session. A standalone note saying "OK" is valid. The reason for lowering: queue items auto-populated from entity names can be short.

### `export_status` vs `status`
`handover_items` has two separate columns:
- `status`: workflow state — `pending | acknowledged | completed | deferred` (check constraint)
- `export_status`: export tracking — `pending | exported`

After mark-exported: `export_status="exported"`, `status="completed"`. Never set `status="exported"` — the check constraint will reject it.

---

## 17. File Change History (This Session — 2026-04-14)

Files changed during the HANDOVER01 session. If you're debugging a regression, these are the files to check.

| File | What changed |
|---|---|
| `apps/web/src/components/handover/HandoverDraftPanel.tsx` | Replaced all 6 direct supabase DB calls with Render API fetch() calls |
| `apps/api/routes/handover_export_routes.py` | Added _get_role_users, _write_handover_event helpers; fixed _notify_hod_for_countersign; added ledger to save_draft, countersign, PATCH, DELETE, mark-exported; fixed PATCH/DELETE ownership checks; fixed mark-exported column names |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Fixed add_to_handover: category_map, correct column names (summary not summary_text), no added_at, added critical HOD cascade |
| `apps/api/action_router/registry.py` | Added crew to add_to_handover allowed_roles; fixed required_fields |
| `apps/api/handlers/handover_handlers.py` | Added category_map normalisation; added critical HOD cascade; added edit audit trail to edit_handover_item_execute |
| `apps/api/handlers/hours_of_rest_handlers.py` | Added ledger event on signoff creation; pms_notifications crew alert |

PRs: #523 (CRUD fix), #525 (ledger cascade), #526 (sync)

| **Session 2 (2026-04-15 to 2026-04-17)** | |
|---|---|
| `HandoverDraftPanel.tsx` | Auth race fix (userReady guard), optimistic +Add, retry cap, export toast |
| `HandoverQueueView.tsx` | Optimistic +Add flip |
| `HandoverContent.tsx` | Sign/countersign wired to /submit and /countersign routes |
| `entity_routes.py` | Sections fallback to v_handover_draft_complete |
| `pipeline_service.py` | CORS: added PATCH/PUT/DELETE |
| `playwright.config.ts` | Shard-49/54 timeout overrides (150s action, 180s test) |
| `shard-52/54 specs` | 19 browser UI tests |

PRs: #607, #616, #624, #627, #631-636

---

*This document was written after a full session working on the handover feature end-to-end. Every bug in section 11 was found in production code and fixed during this session. Every gap in section 13 was confirmed in the live codebase.*
