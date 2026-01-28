# Work Order Lens — v2 FINAL (Gold Spec)

Purpose: Lock a backend‑authoritative, DB‑grounded spec that mirrors the Certificates “gold” standard. No UI authority. Actions are deterministic, signed where required, RLS‑scoped by helpers, and every mutation is written to the immutable ledger.

Status Summary
- Scope: Work orders across fault/equipment contexts, signatures, photos, reassignment, archive.
- DB truth: Canonical tables, RLS helpers, indexes, deterministic triggers.
- Actions: 13 executable actions with domain/variant/roles/required_fields.
- Acceptance: Roles × CRUD, isolation & storage, edge‑case mapping, audit invariants.
- Journeys: Real on‑board scenarios (engine room breakdown, reassignment, completion cascade, archive).

---

## 1) Doctrine (Guardrails)
- Backend authority: UI renders only what backend exposes via `GET /v1/actions/list`.
- Deterministic: Triggers may prefill/reorder/promote, but never mutate state automatically.
- Roles (capability‑first):
  - HOD set: `chief_engineer`, `chief_officer`, `captain`, `purser`.
  - `manager` is separate; HOD‑equivalent only where explicitly allowed.
  - Other auth roles map upward; never used directly in RLS/action policies.
- Signatures: Always present in ledger. `{}` for non‑signed; canonical JSON for signed:
  ```json
  {
    "signed_at": "...",
    "user_id": "...",
    "role_at_signing": "...",
    "signature_type": "pin_totp",
    "signature_hash": "..."
  }
  ```
- Error mapping: 400 validation, 403 role/RLS denial, 404 not found/inaccessible, 409 conflict, 500 hard fail (CI fails).

---

## 2) DB Truth (Canonical)

### 2.1 Tables (primary and related)
- `pms_work_orders` (primary)
  - Core: `id (uuid pk)`, `yacht_id (uuid)`, `status (enum: draft|active|in_progress|completed|cancelled|deferred)`, `title`, `description`, `priority`, `fault_id (uuid)`, `equipment_id (uuid)`, `assigned_to (uuid)`, `wo_number`, `metadata jsonb`, timestamps, accountability cols.
  - RLS: deny‑by‑default; `yacht_id = public.get_user_yacht_id()`; writes gated by `public.is_hod(user_id)` and per‑action policy (see 7. RLS Matrix).

- `pms_work_order_notes`
  - `id`, `work_order_id`, `note_text`, `note_type`, `created_by`, timestamps.
  - RLS: fixed (B1). JOIN on `work_order_id` → `pms_work_orders.yacht_id`.

- `pms_work_order_parts`
  - `id`, `work_order_id`, `part_id`, `quantity`, `notes`, timestamps.
  - RLS: fixed (B2). JOIN on `work_order_id` → `pms_work_orders.yacht_id`.

- `pms_part_usage`
  - `id`, `part_id`, `work_order_id`, `yacht_id`, `quantity_used`, timestamps.
  - RLS: fixed (B3). Yacht‑scoped.

- `doc_metadata`
  - `id`, `yacht_id`, `bucket`, `storage_path`, `content_type`, `entity_type`, `entity_id`, timestamps.
  - RLS: yacht‑scoped; storage path must match writable prefixes.

- `pms_audit_log`
  - `id`, `yacht_id`, `action`, `entity_type`, `entity_id`, `actor_user_id`, `actor_role`, `payload_snapshot jsonb`, `signature jsonb NOT NULL`, `created_at`.
  - Invariants: signature NOT NULL; `{}` for non‑signed; signed JSON for signed actions.
  - Isolation: No FK to tenant auth.users (see `20260126_013_drop_pms_audit_log_user_fk.sql`).

### 2.2 RLS Helpers (required)
- `public.get_user_yacht_id()`
- `public.is_hod(user_id)`  (TRUE for HOD set)
- `public.is_manager(user_id)`
All policies must call helpers; no inline role literals.

### 2.3 Indexes (performance & scope)
- `pms_work_orders(yacht_id, status)`
- `pms_work_orders(fault_id)`
- `pms_audit_log(entity_type, entity_id, created_at desc)`
- `doc_metadata(yacht_id, entity_type, entity_id)`

### 2.4 Deterministic Triggers
- Cascade WO→Fault status (required):
  - `in_progress` → Fault `investigating`
  - `completed` → Fault `resolved`
  - `cancelled` → Fault `open`
  - Migration: `20260125_004_create_cascade_wo_fault_trigger.sql`
  - Tenant status: PENDING (not present on TENANT_1; must apply)

Verification queries:
```sql
-- RLS enabled
select n.nspname, c.relname, c.relrowsecurity
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where c.relname in ('pms_work_order_notes','pms_work_order_parts','pms_part_usage');

-- Cascade trigger exists
select t.tgname from pg_trigger t
join pg_class c on t.tgrelid=c.oid
where c.relname='pms_work_orders' and not t.tgisinternal
  and t.tgname='trg_wo_status_cascade_to_fault';
```

### 2.5 Columns for “My Work Orders” Grouping (Overdue/Critical/Time‑Consuming)
To support deterministic grouping and sorting in the “My Work Orders” surface, the following columns are required on `pms_work_orders`:

- `due_at timestamptz` — Target completion date/time.
- `started_at timestamptz` — When actual work began (for elapsed calculation).
- `estimated_duration_minutes integer` — Planned effort; used to project time‑consuming.
- `severity text` — Controlled values (e.g., 'low','medium','high','critical').
- `criticality_rank smallint` — Numeric rank (lower = more critical) for deterministic ordering.
- `sla_priority text` — Optional SLA tier ('p1','p2','p3') if present on yacht.
- `last_activity_at timestamptz` — Updated by handlers to support “recently active”.
- Soft‑delete (archive) fields: `deleted_at timestamptz`, `deleted_by uuid`, `deletion_reason text`.

Recommended indexes:
```sql
create index if not exists idx_wo_yacht_status_due on pms_work_orders (yacht_id, status, due_at);
create index if not exists idx_wo_yacht_criticality on pms_work_orders (yacht_id, criticality_rank nulls last);
create index if not exists idx_wo_last_activity on pms_work_orders (yacht_id, last_activity_at desc);
```

Derived measures (query‑time):
- `days_remaining = date_trunc('day', due_at) - date_trunc('day', now())`
- `overdue = (due_at is not null and due_at < now() and status not in ('completed','cancelled','deferred'))`
- `time_consuming = coalesce(estimated_duration_minutes,0) >= :threshold`

Soft delete policy: Archived rows remain in DB but are hidden from default “active” queries (predicate `deleted_at is null`). Ledger records archive with signature JSON.

---

## 3) Storage Isolation

Buckets (policy):
- Manuals/docs: `documents` (read‑mostly; delete HoD+)
- Work order images: `pms-work-order-photos` (new, R/W per policy)
  - Path: `{yacht_id}/work_orders/{work_order_id}/{filename}`
  - Writable prefixes: `{yacht_id}/work_orders/`
  - Do not prefix storage_path with `documents/`.
- Other existing buckets (finance, discrepancy, receiving, labels) stay in their domains.

Rationale: WO images are operational; isolating them avoids coupling to manuals storage and allows distinct lifecycle/RLS.

---

## 4) Actions (Backend‑Authoritative Matrix)

For all actions: `domain='work_orders'`, exposed via `GET /v1/actions/list` with `variant`, `allowed_roles`, `required_fields`, `search_keywords`, and file `storage_options` when applicable.

READ (allowed_roles: `crew`, `chief_engineer`, `chief_officer`, `captain`, `manager`)
- `view_work_order_detail`
  - required: `yacht_id`, `work_order_id`
  - keywords: view, detail, show, work, order, wo
- `view_work_order_history`
  - required: `yacht_id`, `work_order_id`
  - keywords: history, audit, changes, work, order, wo
- `view_work_order_checklist`
  - required: `yacht_id`, `work_order_id`
  - keywords: checklist, tasks, work, order, wo

MUTATE (default allowed_roles: `chief_engineer`, `chief_officer`, `captain`; include `manager` only where stated)
- `create_work_order_from_fault` (SIGNED)
  - required: `yacht_id`, `fault_id`, `signature`
  - roles: `chief_engineer`, `chief_officer`, `captain` (manager optional per policy)
  - keywords: create, add, new, work, order, wo, from, fault
- `create_work_order`
  - required: `yacht_id`, `title`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: create, add, new, work, order, wo
- `update_work_order`
  - required: `yacht_id`, `work_order_id`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: update, edit, modify, work, order, wo
- `update_work_order_status`
  - required: `yacht_id`, `work_order_id`, `new_status`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: start, resume, in_progress, close, cancel, status
- `add_work_order_note`
  - required: `yacht_id`, `work_order_id`, `note_text`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: add, note, comment, work, order, wo
- `add_work_order_photo`
  - required: `yacht_id`, `work_order_id`, `filename`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: add, photo, image, upload, work, order, wo
  - storage_options: bucket `pms-work-order-photos`; path template `{yacht_id}/work_orders/{work_order_id}/{filename}`
- `add_parts_to_work_order`
  - required: `yacht_id`, `work_order_id`, `part_id`, `[quantity]`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: add, part, parts, work, order, wo
- `assign_work_order`
  - required: `yacht_id`, `work_order_id`, `assigned_to`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: assign, owner, delegate, work, order, wo
- `mark_work_order_complete`
  - required: `yacht_id`, `work_order_id`, `completion_notes`, `[parts_used]`
  - roles: `chief_engineer`, `chief_officer`, `captain`
  - keywords: complete, close, finish, done, work, order, wo

SIGNED (elevated)
- `reassign_work_order`
  - required: `yacht_id`, `work_order_id`, `assignee_id`, `reason`, `signature`
  - allowed_roles: `chief_engineer`, `chief_officer`, `captain`, `manager`
  - keywords: reassign, assign, owner, handover, work, order, wo
- `archive_work_order`
  - required: `yacht_id`, `work_order_id`, `deletion_reason`, `signature`
  - allowed_roles: `captain`, `manager`
  - keywords: archive, cancel, remove, soft delete, work, order, wo

READ (aggregation)
- `view_my_work_orders`
  - required: `yacht_id`
  - behavior: returns current user’s WO list partitioned into groups: Overdue (sorted by days overdue desc, then criticality), Critical (by criticality_rank asc), Time‑Consuming (estimated_duration_minutes desc), and “Everything else” (status/priority sort). Uses deterministic SQL based on columns in 2.5.
  - keywords: my, work, orders, overdue, critical, time, consuming

---

## 5) Acceptance Matrix (Copy of Certificates intent)

Roles & CRUD
- crew create/update → 403
- HOD (chief_engineer/chief_officer) create/update → 200
- SIGNED actions (reassign, archive) → 200 for captain/manager (and HOD where specified), others 403

Isolation & Storage
- Anon REST read → [] or 401/403; service role shows rows
- Cross‑yacht path/ID → 400/403
- File actions include `storage_options` with per‑yacht prefixes; reject arbitrary paths

Edge Cases
- Invalid work_order_id / fault_id → 404
- Duplicate WO from same fault without override → 409
- Invalid status transition → 400
- Missing signature for SIGNED actions → 400
- Double completion/archival → 400/409

Audit Invariant
- Non‑signed actions → `signature = {}`
- Signed actions → signature is non‑null JSON with canonical keys (see 1. Doctrine)

Execution Gates
- Docker fast loop: role/RLS, storage safety, error mapping, basic happy paths
- Staging CI (real JWTs): create from fault (SIGNED) 200; reassign (SIGNED) 200; archive (SIGNED) 200; crew denies; zero 500s
 - “My Work Orders” groups deterministic given seed data; deleted rows excluded; ordering stable

---

## 6) Journeys (On‑Board Reality)

6.1 Engine Room Breakdown + Photo
- Intent: “create work order from fault ABC123”
- Flow:
  1) `GET /v1/actions/list?q=create+work+order+from+fault&domain=work_orders`
  2) UI shows SIGNED badge; opens modal; path preview `{yacht_id}/work_orders/<id>/pump.jpg`
  3) `POST /v1/actions/execute` with `{fault_id, title, priority, signature}` → 200
  4) `POST /v1/actions/execute` add_work_order_photo → 200 (storage validated)
  5) Ledger: create (signature JSON), photo (signature `{}`)

6.2 Mid‑Watch Reassignment (Handover)
- Intent: “reassign WO‑2026‑042 to Sam — shift change”
- Flow:
  1) List → reassign_work_order (SIGNED)
  2) Execute with `{assignee_id, reason, signature}` → 200
  3) Ledger: signature JSON; checklist untouched; notifications (optional) to new assignee

6.3 Completion Cascade (Parts Usage)
- Intent: “complete WO‑2026‑042 — replaced seals x2”
- Flow:
  1) Execute mark_work_order_complete with `{completion_notes, parts_used}` → 200
  2) Deduct stock (INSUFFICIENT_STOCK → 400)
  3) Trigger cascades fault to resolved (post‑migration)
  4) Ledger: signature `{}`; payload snapshot includes parts_deducted

6.4 Archive Cancelled WO (Captain)
- Intent: “archive WO‑2025‑118 — duplicate”
- Flow:
  1) Execute archive_work_order with `{deletion_reason, signature}` → 200
  2) Trigger returns fault to open
  3) Ledger: signature JSON

Example cURL (create from fault):
```bash
curl -X POST "$API_BASE/v1/actions/execute" \
 -H "Authorization: Bearer $HOD_JWT" -H "Content-Type: application/json" \
 -d '{
  "action": "create_work_order_from_fault",
  "context": {"yacht_id": "'$YACHT_ID'"},
  "payload": {
    "fault_id": "'$FAULT_ID'",
    "title": "Seal leak corrective",
    "priority": "routine",
    "signature": {
      "signed_at": "'$(date -u +%FT%TZ)'",
      "user_id": "'$USER_ID'",
      "role_at_signing": "chief_engineer",
      "signature_type": "pin_totp",
      "signature_hash": "test-hash"
    }
  }
}'
```

6.5 Add Note by Paraphrase + Time Qualifier
- Intent: “add note to winch work order from yesterday: cleaned and inspected winch, found wear on brake pads”
- Guardrails:
  - Extraction gate resolves by deterministic filters in order: equipment match (exact/alias), time window (yesterday), assignee=self by default, status in (active,in_progress), fuzzy on title tokens limited to whitelist.
  - If >1 candidate, return disambiguation list (WO‑numbers + titles); no guesses.
- Flow:
  1) System narrows candidate WOs for equipment=winch and started_at::date = current_date - 1.
  2) If single match, execute `add_work_order_note` with provided text → 200; else present choices for selection.
  3) Ledger: signature `{}` (non‑signed note); record payload snapshot with `note_type`.

6.6 Show All Work Orders for Equipment
- Intent: “show all work orders for winch this month”
- Flow:
  1) Use read list (view_my_work_orders or equipment‑scoped read) filtering by equipment_id and date range.
  2) Results partitioned by Overdue/Critical/Time‑Consuming if requested; else default sort.
  3) No actions are invented; actions appear only after focusing a single WO.

---

## 7) RLS Matrix (Policy Sketch)

High‑level policy (all tables deny‑by‑default):
- SELECT: `yacht_id = public.get_user_yacht_id()` OR JOIN on WO.yacht_id
- INSERT/UPDATE/DELETE on work orders:
  - HOD write: `public.is_hod(auth.uid()) = true`
  - Manager write: `public.is_manager(auth.uid()) = true` for explicitly allowed actions
- Notes/parts usage: JOIN to WO; same yacht; writer must be HOD/assignee

Helpers (migration if missing):
```sql
create or replace function public.is_hod(uid uuid) returns boolean as $$
  select exists (
    select 1 from auth_users_roles r
    where r.user_id = uid and r.is_active
      and r.role in ('chief_engineer','chief_officer','captain','purser')
  );
$$ language sql stable;

create or replace function public.is_manager(uid uuid) returns boolean as $$
  select exists (
    select 1 from auth_users_roles r
    where r.user_id = uid and r.is_active and r.role = 'manager'
  );
$$ language sql stable;
```

---

## 8) Notifications (In‑App v1)

Goal: Deterministic nudges for pending work (no email/push in v1).

Schema (new migrations):
- `pms_notifications`
  - `id uuid pk`, `yacht_id uuid`, `user_id uuid`, `topic text`, `source text`, `source_id uuid`,
    `title text`, `body text`, `level text check in ('info','warning','critical')`,
    `cta_action_id text`, `cta_payload jsonb`,
    `status text check in ('pending','sent','read','dismissed')`,
    `send_after timestamptz`, timestamps
  - Unique idempotency: `(user_id, source, source_id, topic, date_trunc('day', send_after))`
  - RLS: yacht_id + user_id

- `pms_user_preferences` (channel toggles, quiet hours, frequency caps)

- View `v_pending_work_items` (example: draft WOs older than 6h for chief_engineer)

Delivery: in‑app list + mark read/dismiss; CTA opens ActionModal with backend‑provided `cta_action_id` / payload.

Acceptance:
- Draft WO beyond 6h generates one notification for chief_engineer; crew receives none.
- Mark read prevents re‑notify (idempotency holds).

---

## 9) Migrations (Planned / Required)

Deployed (per tenant brief):
- 20260125_001_fix_cross_yacht_notes.sql (B1)
- 20260125_002_fix_cross_yacht_parts.sql (B2)
- 20260125_003_fix_cross_yacht_part_usage.sql (B3)

Pending (must apply):
- 20260125_004_create_cascade_wo_fault_trigger.sql — deploy & verify trigger on `pms_work_orders`
- 20260127_104_alter_pms_work_orders_add_sla_and_soft_delete.sql — add grouping/soft‑delete fields + indexes
- 20260127_105_create_pms_entity_links.sql — support deterministic “Show Related” panel
- 20260127_106_create_v_my_work_orders_summary.sql — view that partitions “My Work Orders”
- 20260127_100_create_pms_notifications.sql — notifications table + RLS + unique index
- 20260127_101_create_pms_user_preferences.sql — user prefs + RLS
- 20260127_102_create_v_pending_work_items.sql — reference views for deterministic in‑app nudges
- 20260127_103_helpers_is_hod_is_manager.sql — standardize helpers if missing

Runbook (staging/tenant):
```bash
psql "$TENANT_DSN" -f supabase/migrations/20260125_004_create_cascade_wo_fault_trigger.sql
psql "$TENANT_DSN" -f supabase/migrations/20260127_100_create_pms_notifications.sql
psql "$TENANT_DSN" -f supabase/migrations/20260127_101_create_pms_user_preferences.sql
psql "$TENANT_DSN" -f supabase/migrations/20260127_102_create_v_pending_work_items.sql
psql "$TENANT_DSN" -f supabase/migrations/20260127_103_helpers_is_hod_is_manager.sql
```

Verification:
```sql
-- Cascade
select tgname from pg_trigger t join pg_class c on t.tgrelid=c.oid
where c.relname='pms_work_orders' and t.tgname='trg_wo_status_cascade_to_fault';

-- Notifications idempotency
select indexdef from pg_indexes where tablename='pms_notifications' and indexname like '%unique%';

-- “My Work Orders” view exists
select 1 from pg_views where viewname='v_my_work_orders_summary';
```

---

## 10) Verification Checklist (Pre‑Build)
1. DB helpers present: `is_hod`, `is_manager`, `get_user_yacht_id`.
2. RLS ON for notes/parts/part_usage; policies call helpers.
3. Cascade trigger deployed and verified on tenant.
4. Storage bucket chosen for WO photos (`pms-work-order-photos`) with safe prefixes.
5. Registry entries complete for all 13 actions, with domain/variant/roles/required_fields.
6. /v1/actions/list returns correct `storage_options` for photo action.
7. Acceptance matrix transcribed to tests (Docker + staging CI) — zero 500s.
8. Ledger invariant enforced (signature NOT NULL) and history queries documented.
9. Notifications migrations applied (v1 in‑app only), RLS verified.

---

## 11) References
- Certificates template: Action suggestions contract, acceptance matrix, storage semantics pattern.
- This lens inherits the same guarantees; only the domain and concrete actions differ.
