# Warranty Lens — Complete Developer Guide

> **Who this is for:** Any developer picking up warranty for the first time — frontend, backend, or full-stack.  
> **Scope:** Everything from the database row to the rendered UI. Bugs found, traps hit, techniques used.  
> **Verified against:** commit `6b7278c0` on `main`, April 2026.

---

## 1. What the warranty domain does

A warranty claim is a formal record that a piece of equipment is defective, damaged, or failed within its warranty period, and the vessel is seeking repair, replacement, or reimbursement from the manufacturer or vendor.

The lifecycle is:

```
crew/officer drafts claim
       ↓
HOD (Head of Department) submits for approval
       ↓
Captain or Manager approves OR rejects
       ↓ (if approved)
Captain or Manager closes the claim
```

Every state change is logged. Every read is logged. Every stakeholder is notified. Nothing is silent.

---

## 2. File map — exact paths

### Frontend

| File | Purpose |
|---|---|
| `apps/web/src/components/lens-v2/entity/WarrantyContent.tsx` | The entire detail view — all sections, all action buttons |
| `apps/web/src/components/lens-v2/actions/AttachmentUploadModal.tsx` | Generic file upload modal (reusable, not warranty-specific) |
| `apps/web/src/components/lens-v2/sections/AttachmentsSection.tsx` | Renders attachment rows — image or document thumbnail |
| `apps/web/src/lib/normalizeWarranty.ts` | Defensive field normalisation between API response and component |
| `apps/web/src/hooks/useEntityLens.ts` | Data fetch, action execution, refetch — shared by all entity lenses |
| `apps/web/src/contexts/EntityLensContext.tsx` | React context that glues the hook to WarrantyContent |
| `apps/web/src/app/warranties/page.tsx` | List page — renders all claims, "File New Claim" button |
| `apps/web/src/app/warranties/[id]/page.tsx` | Detail page — thin wrapper, delegates to EntityLensPage |
| `apps/web/e2e/shard-31-fragmented-routes/route-warranties.spec.ts` | Playwright e2e — 19 tests covering list, CRUD, state transitions |

### Backend

| File | Purpose |
|---|---|
| `apps/api/routes/entity_routes.py` | `GET /v1/entity/warranty/{id}` — serves the full detail payload |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | All 7 warranty handler implementations |
| `apps/api/action_router/registry.py` | ActionDefinition entries — RBAC, required_fields, field_metadata |
| `apps/api/action_router/ledger_metadata.py` | Maps action → event_type for the safety net ledger write |
| `apps/api/routes/handlers/internal_adapter.py` | Phase 4 bridge — see Section 7 |
| `apps/api/routes/p0_actions_routes.py` | `POST /v1/actions/execute` — the single execute endpoint |
| `apps/api/handlers/universal_handlers.py` | `soft_delete_entity()` — handles archive and void |

---

## 3. The state machine

### States

| State | What it means |
|---|---|
| `draft` | Being written. Not submitted. Crew can still edit. |
| `submitted` | Sent to captain/manager for decision. Locked from edits. |
| `approved` | Approved. Awaiting closure (payment received, repair done). |
| `rejected` | Sent back. Drafter can revise and resubmit. |
| `closed` | Done. Final state. |
| `archived` | Soft-deleted. Removed from active view. `deleted_at` is set. |

### Transitions

```
draft ──submit──→ submitted ──approve──→ approved ──close──→ closed
                       │
                    reject
                       │
                       ↓
                   rejected ──submit──→ submitted (loop)

draft ──archive──→ archived (at any point)
```

### Who can do what (RBAC)

| Action | Roles |
|---|---|
| `draft_warranty_claim` | crew, chief_engineer, chief_officer, captain |
| `file_warranty_claim` | chief_engineer, chief_officer, captain, manager |
| `submit_warranty_claim` | chief_engineer, chief_officer, captain |
| `approve_warranty_claim` | captain, manager |
| `reject_warranty_claim` | captain, manager |
| `close_warranty_claim` | captain, manager |
| `add_warranty_note` | chief_engineer, chief_officer, captain, manager |
| `compose_warranty_email` | chief_engineer, chief_officer, captain, manager |
| `archive_warranty` | chief_engineer, chief_officer, captain, manager |
| `void_warranty` | chief_engineer, chief_officer, captain, manager |

The role check happens **before** the payload reaches the handler. Enforced in `p0_actions_routes.py` — role not in `allowed_roles` → `403` before any DB touch.

---

## 4. Data flow — end to end

### Reading a warranty

```
Browser
  → GET /v1/entity/warranty/{id}   (entity_routes.py line 446)
  → auth middleware validates JWT
  → resolve_yacht_id() enforces tenant scope
  → query v_warranty_enriched view  (enriched with equipment name, days_until_expiry, status_label)
  → _get_attachments()  generates signed URLs (1h TTL) from pms_attachments
  → query pms_notes WHERE warranty_id = {id}
  → query pms_audit_log WHERE entity_type='warranty' AND entity_id={id}
  → fire-and-forget: write view event to ledger_events
  → get_available_actions()  resolves which action buttons to show based on status + user role
  → return full JSON response
```

The component (`WarrantyContent.tsx`) never fetches directly. It reads from `useEntityLensContext()`, which is fed by `useEntityLens.ts`, which called the endpoint above.

### Executing an action

```
Button click in WarrantyContent.tsx
  → executeAction(actionId, payload)  from context
  → POST /v1/actions/execute  (p0_actions_routes.py)
  → role check against registry
  → required_fields validation
  → context resolution: entity_id → warranty_id
  → INTERNAL_HANDLERS[actionId](params)  via internal_adapter.py
  → handler: update pms_warranty_claims
  → handler: insert pms_audit_log
  → handler: insert pms_notifications (per recipient)
  → safety net: write ledger_events if handler didn't set _ledger_written=True
  → return {status: "success", ...}
  → WarrantyContent calls refetch()
  → fresh GET re-renders the lens
```

---

## 5. Database tables

### `pms_warranty_claims`

The primary table. One row per warranty claim.

Key columns:

```sql
id                UUID        primary key
yacht_id          UUID        tenant isolation — every query must include this
claim_number      varchar     auto-generated: WC-YYYY-NNN
title             text        human name for the claim
status            enum        draft | submitted | approved | rejected | closed | archived
claim_type        enum        repair | replacement | refund | manufacturer_defect |
                              premature_failure | incorrect_part | damage_in_transit | other
vendor_name       varchar
manufacturer      varchar
part_number       varchar
serial_number     varchar
purchase_date     date
warranty_expiry   date        when the warranty period ends (NOT when the claim expires)
claimed_amount    numeric
approved_amount   numeric     set by approver, may differ from claimed
currency          varchar     default USD
equipment_id      UUID FK     optional — which piece of equipment is defective
fault_id          UUID FK     optional — fault that triggered this claim
work_order_id     UUID FK     optional — related work order
drafted_by        UUID        who created the claim
drafted_at        timestamp
submitted_by      UUID
submitted_at      timestamp
approved_by       UUID
approved_at       timestamp
rejected_by       UUID
rejected_at       timestamp
rejection_reason  text
email_draft       jsonb       {subject, to, body, composed_at, composed_by}
deleted_at        timestamp   null = active, set = soft-deleted
```

### `v_warranty_enriched`

A Postgres VIEW that joins `pms_warranty_claims` with `pms_equipment` and adds computed fields:

- `equipment_name`, `equipment_code` — from the equipment join
- `days_until_expiry` — integer, computed from `warranty_expiry - NOW()`
- `status_label` — human-readable string ("Draft", "Submitted", etc.)
- `workflow_stage` — integer (0=draft, 1=submitted, 2=approved/rejected, 3=closed)

**Always query this view for the detail endpoint** — never query `pms_warranty_claims` directly in entity_routes. The view is used at `entity_routes.py line 453`.

### `pms_notes` (warranty FK added)

Notes belong to a single parent entity via a nullable FK column. Warranty's column:

```sql
warranty_id   UUID FK   references pms_warranty_claims(id)
```

**Important:** This column was added via migration in April 2026. If you see a warranty with no notes despite notes existing, check that `warranty_id` is populated correctly in the insert. The generic `add_note()` handler in the dispatcher maps `warranty_id` from params.

### `pms_attachments`

One row per uploaded file, regardless of entity type:

```sql
entity_type     varchar   "warranty"
entity_id       UUID      warranty_id
storage_bucket  varchar   "pms-warranty-documents"
storage_path    varchar   "warranty/{id}/{timestamp}-{filename}"
filename        varchar   original filename (unsanitized)
mime_type       varchar
file_size       integer   bytes
category        varchar   "claim_document"
uploaded_by     UUID
```

### `pms_audit_log`

Direct state-change audit. Written by individual handlers (submit/approve/reject/close). **Not** the same as `ledger_events`.

```sql
entity_type   "warranty"
entity_id     warranty_id
action        "submitted" | "approved" | "rejected" | "closed"
user_id       who did it
new_values    {"status": "submitted"}
```

### `ledger_events`

Immutable append-only global event log. Written two ways:

1. **Direct by handlers** via `_ledger_read()` pattern (certificate style)
2. **Safety net** via `p0_actions_routes.py` after every executed action
3. **View events** via `entity_routes.py` — fires on every GET

For warranty view events (entity_routes.py line 467):

```python
get_supabase_client().table("ledger_events").insert({
    "event_type": "view",
    "entity_type": "warranty",
    "action": "view_warranty_claim",
    "source_context": "microaction",   # MUST be one of: microaction|search|read_beacon|bulk|system
    "proof_hash": sha256(yacht_id + warranty_id + action + timestamp),
    ...
})
```

**Critical:** Must use `get_supabase_client()` (service role key), NOT the tenant client. RLS policy `ledger_events_insert_service_only` blocks tenant-scoped clients from inserting. Using the wrong client causes a silent failure caught by `except Exception: pass`.

### `pms_notifications`

Delivery table for in-app notifications. Key constraint:

```sql
idempotency_key   varchar   NOT NULL — no default
```

**This catches new developers every time.** Any INSERT without `idempotency_key` raises a NOT NULL violation, caught silently by `except Exception: pass`. The notification is never written. Use the upsert pattern:

```python
supabase.table("pms_notifications").upsert(
    rows,
    on_conflict="yacht_id,user_id,idempotency_key"
).execute()
```

Key format used: `warranty_{action}:{warranty_id}:{recipient_user_id}`.

---

## 6. Notification hierarchy

When a crew member submits, the right people need to know. The warranty domain uses role-based escalation identical to the HoR violation pattern.

```
_get_approver_user_ids(supabase, yacht_id)
  → queries auth_users_roles WHERE role IN ('captain', 'manager')
  → deduplicates (same user may hold multiple roles)
  → returns list of user_ids
```

| Action | Who gets notified | Priority |
|---|---|---|
| `submit_warranty_claim` | All captain + manager users on the vessel | normal |
| `approve_warranty_claim` | Drafter + submitter (if different from approver) | normal |
| `reject_warranty_claim` | Drafter + submitter (if different from approver) | **high** |
| `close_warranty_claim` | Drafter + submitter | normal |
| `compose_warranty_email` | All captain + manager users | normal |
| `add_warranty_note` | Drafter + submitter + approver (excluding note author) | low |

---

## 7. The Phase 4 bridge (things you need to understand)

The action dispatch system has two layers that confuse everyone:

**Layer 1 — `INTERNAL_HANDLERS` dict** (`internal_dispatcher.py` near bottom)  
Contains all callable warranty handlers. This is the "legacy" layer.

**Layer 2 — `HANDLERS` dict** (`routes/handlers/__init__.py`)  
This is what the execute endpoint actually looks up. Built from Phase 4 native handlers PLUS the internal_adapter shim.

**The bridge** — `internal_adapter.py`:
```python
_ACTIONS_TO_ADAPT = [
    "submit_warranty_claim",
    "approve_warranty_claim",
    ...
]

HANDLERS = {action_id: _make_adapter(action_id) for action_id in _ACTIONS_TO_ADAPT}
```

`_make_adapter()` wraps each `INTERNAL_HANDLERS` function to accept the Phase 4 calling convention `(payload, context, yacht_id, user_id, user_context, db_client)` and converts it to the flat `params` dict the legacy handlers expect.

**If an action is in `INTERNAL_HANDLERS` but NOT in `_ACTIONS_TO_ADAPT`** → it returns `INVALID_ACTION` from the execute endpoint. This was the root bug found in April 2026 — all 6 warranty state-change actions were missing from `_ACTIONS_TO_ADAPT`. The UI showed action buttons (because `available_actions` reads from the registry, not the adapter), but clicking them did nothing.

---

## 8. Attachments — the upload flow

The upload modal (`AttachmentUploadModal.tsx`) is **generic** — it works for any entity. Don't create a domain-specific upload modal. Pass props:

```tsx
<AttachmentUploadModal
  open={uploadModalOpen}
  onClose={() => setUploadModalOpen(false)}
  entityType="warranty"
  entityId={entityId}
  bucket="pms-warranty-documents"
  category="claim_document"
  yachtId={entity?.yacht_id ?? user?.yachtId ?? ''}
  userId={user?.id ?? ''}
  onComplete={() => refetch()}
/>
```

**Upload path format:** `warranty/{entityId}/{Date.now()}-{sanitizedFilename}`

**Sanitisation rule:** `name.replace(/[^a-zA-Z0-9._-]/g, '_')` — replaces spaces and special chars with underscores.

**Signed URL TTL:** 1 hour (3600 seconds). Signed URLs are generated fresh on every GET call to the entity endpoint. Do not cache them on the frontend.

**Partial failure handling:** If the Supabase storage upload succeeds but the `pms_attachments` insert fails (network issue, RLS, etc.), the modal still calls `onComplete()` after 1.2s so the UI refreshes. The file exists in storage but has no metadata row. A reconciliation job could clean these up, but currently none exists.

**Accepted MIME types:** PDF, JPEG, PNG, HEIC, WEBP, TIFF, Word (.doc/.docx), Excel (.xls/.xlsx), plain text, ZIP, application/octet-stream (catch-all).

---

## 9. `compose_warranty_email` — what it does and does not do

This action **prepares a draft only**. It does not send an email.

It reads all claim fields, builds a professional letter body, and stores the result as JSON in `pms_warranty_claims.email_draft`:

```json
{
  "subject": "Warranty Claim WC-2026-001 — Defective Pump",
  "to": "Vendor Name",
  "body": "Dear Vendor Name,\n\nWe write regarding warranty claim...",
  "composed_at": "2026-04-14T15:00:00Z",
  "composed_by": "user-uuid"
}
```

The email draft is returned in the entity GET response and rendered in `WarrantyContent.tsx`. Any actual sending would require an email integration (currently not wired to warranty). The action notifies captain/manager that the draft is ready for their review.

---

## 10. Things I wish I knew at the start

### 1. `available_actions` and execute are completely separate systems

`available_actions` in the entity response reads from the **registry** (`registry.py`). The execute endpoint routes through **`HANDLERS`** (built from `internal_adapter.py`). An action can exist in the registry (shows a button) but be missing from `_ACTIONS_TO_ADAPT` (execute returns `INVALID_ACTION`). Always verify both.

### 2. `pms_warranty_claims`, not `pms_warranties`

There is no `pms_warranties` table. The table is `pms_warranty_claims`. Every query, every migration, every handler uses this name. Getting it wrong causes a 500 that says "relation does not exist."

### 3. `pms_audit_log.user_id`, not `performed_by`

The audit log table has a `user_id` column. It does **not** have a `performed_by` column. Older documentation and auto-generated code uses `performed_by` — this is wrong. The insert will fail silently.

### 4. `idempotency_key` is NOT NULL with no default

Every `pms_notifications` insert must include `idempotency_key`. There is no default. Missing it causes a constraint violation swallowed by `except Exception: pass`. You'll never see an error — the notification just won't appear.

### 5. `ledger_events` requires service role, not tenant client

The entity_routes.py uses `get_tenant_client(tenant_key)` for all queries. But `ledger_events` has RLS policy `ledger_events_insert_service_only` that blocks the tenant client from inserting. Use `get_supabase_client()` specifically for ledger writes. Using the tenant client causes a silent failure.

### 6. `source_context` on `ledger_events` has a CHECK constraint

Valid values: `microaction`, `search`, `read_beacon`, `bulk`, `system`. Anything else causes `APIError: violates check constraint "valid_source_context"`. This is caught silently.

### 7. The entity GET endpoint uses `v_warranty_enriched`, not the base table

Never query `pms_warranty_claims` directly for the entity endpoint. The enriched view adds equipment name, expiry calculations, status labels. Frontend components expect these fields — they will render empty or crash without them.

### 8. Docker does not hot-reload

The API container bakes source at build time. If you change Python code and wonder why nothing changed, you need to `docker compose build api && docker compose up -d api`. A running container with stale code will silently ignore your changes.

### 9. The warranty notes FK was added mid-project

`pms_notes.warranty_id` was added via migration in April 2026. If your dev database is from an older dump, it won't have this column. The `add_warranty_note` handler will fail silently. Run the migration:
```sql
ALTER TABLE pms_notes ADD COLUMN IF NOT EXISTS warranty_id UUID REFERENCES pms_warranty_claims(id);
CREATE INDEX IF NOT EXISTS idx_pms_notes_warranty_id ON pms_notes(warranty_id);
```

### 10. `maybe_single()` raises on empty results in some Supabase versions

The Python Supabase client's `.maybe_single()` should return `None` for empty results, but certain versions raise `APIError` on 204 (no content) responses. The safe pattern is `.limit(1).execute()` followed by `result.data[0] if result.data else None`. Both patterns exist in the codebase — if you see warranty queries failing on empty results, switch to `.limit(1)`.

---

## 11. Cross-domain interactions

### Equipment
- Warranty claims optionally reference one equipment item via `equipment_id`
- The enriched view joins to get `equipment_name` and `equipment_code`
- Frontend renders a "Related Equipment" nav link
- Equipment lens has no back-reference to warranty (navigation is one-directional from warranty)

### Faults
- Optional `fault_id` FK
- A fault may have triggered the warranty claim (equipment failed, raising a fault)
- No back-reference on the fault lens

### Work Orders
- Optional `work_order_id` FK
- A work order may have been raised to document the defect that led to the warranty claim
- No back-reference on the work order lens

### Handover
- Warranty claims can be referenced in handover items via the generic `related_entities` mechanism
- No direct FK — handover items store `entity_type="warranty"` and `entity_id`

### Email
- `compose_warranty_email` stores a draft in the warranty record
- No email is sent automatically
- The email integration (Outlook/SMTP) is separate from this domain

### Ledger / Audit
- Every state change → `pms_audit_log` (direct, in handlers)
- Every action → `ledger_events` (via safety net in `p0_actions_routes.py`)
- Every read → `ledger_events` (via fire-and-forget in `entity_routes.py`)

---

## 12. e2e test coverage

**File:** `apps/web/e2e/shard-31-fragmented-routes/route-warranties.spec.ts`  
**19 tests** covering:
- List page renders
- Status badge rendering per state
- Clicking into detail view
- File new claim modal
- State transition buttons appear/disappear by role
- Attachment section renders
- Notes section renders
- Audit trail renders

**Critical note for running e2e tests:**  
Tests must point at the **MASTER** Supabase URL (for auth/JWT), not the TENANT URL. Using the tenant URL for auth causes JWT validation failures that appear as random 401s. See `CONTEXT_RECOVERY_PROMPT.md` for the env setup.

---

## 13. Limitations and known gaps

| Gap | Description | Workaround |
|---|---|---|
| Email not sent | `compose_warranty_email` prepares only, no send | Manual copy-paste or future email integration |
| No expiry alerts | Warranty expiry date stored but no cron job sends alerts | `days_until_expiry` available in view for frontend warning |
| Attachment deduplication | Same file can be uploaded multiple times | No server-side dedup — check filename before uploading |
| Signed URL TTL | Attachment URLs expire after 1 hour | Fresh URLs generated on every entity GET — don't cache them |
| Partial upload state | If metadata insert fails after storage upload, file exists with no record | No cleanup job exists |
| No multi-file upload | AttachmentUploadModal is single-file | Multiple uploads require multiple modal opens |
| Role hierarchy rigidity | `_get_approver_user_ids` queries captain + manager only | Cannot configure different approvers per vessel |
| `under_review` status removed | Old test data may have `under_review` in `status` column | Safe to ignore — state machine never produces it, UI handles unknown states gracefully |

---

## 14. Quick reference — action IDs

| What you want to do | Action ID |
|---|---|
| Create a new claim | `draft_warranty_claim` or `file_warranty_claim` (same handler) |
| Submit for approval | `submit_warranty_claim` |
| Approve | `approve_warranty_claim` |
| Reject with reason | `reject_warranty_claim` |
| Close after approval | `close_warranty_claim` |
| Add a note | `add_warranty_note` |
| Prepare email draft | `compose_warranty_email` |
| Soft-delete | `archive_warranty` |
| Void (signed) | `void_warranty` |

---

## 15. How to verify it works

```bash
# 1. API health
curl http://localhost:8000/health

# 2. Mint a JWT (captain role) and fetch a warranty entity
# See docs/explanations/Authentication.md for JWT minting

# 3. Check ledger_events for view event after GET
psql $TENANT_DB_URL -c "
  SELECT action, user_role, created_at 
  FROM ledger_events 
  WHERE entity_type='warranty' 
  ORDER BY created_at DESC LIMIT 5;
"

# 4. Check notifications after submit
psql $TENANT_DB_URL -c "
  SELECT user_id, notification_type, idempotency_key 
  FROM pms_notifications 
  WHERE notification_type='warranty_submitted' 
  ORDER BY created_at DESC LIMIT 5;
"

# 5. Verify all captain/manager users were notified (count should match)
psql $TENANT_DB_URL -c "
  SELECT count(*) FROM auth_users_roles 
  WHERE yacht_id='YOUR_YACHT_ID' AND role IN ('captain','manager');
"
```

---

*Last updated: April 2026 | Branch: main | Maintainer: CelesteOS Engineering*
