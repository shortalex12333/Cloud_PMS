# Certificate Lens — Complete Developer Guide

> **Who this is for:** Any developer picking up certificates for the first time — frontend, backend, or full-stack.
> **Scope:** Everything from the database row to the rendered UI. Bugs found, traps hit, techniques used.
> **Verified against:** commit `47cfc3e7` on `main`, 2026-04-14. PR #525 merged.

---

## 1. What the certificate domain does

A certificate is not a document. It is a **compliance countdown clock**.

Every certificate represents a dated legal obligation — class, flag state, safety equipment, crew training — that, if missed, stops the vessel operating. Port state control can detain the vessel. The flag state can issue a deficiency. The insurer can void coverage. Miss a certificate expiry and the whole operation stops.

So certificates are not filed — they are **monitored**, **renewed**, **supersede**d, and **tracked with full chain-of-custody evidence**. The system must know:

- Who issued it (issuing authority)
- When it was issued
- When it expires
- What it covers (scope, capacity, flag state, trading area, conditions)
- Who is responsible for renewing it
- Every change ever made to it (audit trail)
- Every person who ever viewed it (ledger read log)

There are two domains of certificates:

| Domain | Table | Examples |
|---|---|---|
| **Vessel** | `pms_vessel_certificates` | ISM, ISPS, SOLAS, MLC, CLASS, FLAG, LOAD_LINE, IOPP, MARPOL, TONNAGE |
| **Crew** | `pms_crew_certificates` | STCW, ENG1, COC, GMDSS, BST, PSC, AFF, MEDICAL_CARE |

Both are compliance-critical. Both go through the same lens, list, and action router.

---

## 2. File map — exact paths

### Frontend

| File | Purpose |
|---|---|
| `apps/web/src/app/certificates/page.tsx` | List page — unified vessel + crew list via `v_certificates_enriched` view |
| `apps/web/src/components/lens-v2/entity/CertificateContent.tsx` | The entire detail view — all sections, all action buttons |
| `apps/web/src/components/lens-v2/mapActionFields.ts` | Shared utility that builds ActionPopup fields from registry metadata |
| `apps/web/src/components/lens-v2/actions/ActionPopup.tsx` | Generic mutation form modal with signature widget for SIGNED actions |
| `apps/web/src/components/lens-v2/actions/AddNoteModal.tsx` | Note composition modal |
| `apps/web/src/hooks/useEntityLens.ts` | Data fetch, action execution, refetch — shared by all entity lenses |
| `apps/web/src/contexts/EntityLensContext.tsx` | React context glue |
| `apps/web/src/features/entity-list/components/FilteredEntityList.tsx` | The list component with filter panel |
| `apps/web/e2e/shard-33-lens-actions/certificate-actions.spec.ts` | Playwright e2e — action gating tests |
| `apps/web/e2e/shard-34-lens-actions/certificate-actions-full.spec.ts` | Full CRUD e2e |

### Backend

| File | Purpose |
|---|---|
| `apps/api/routes/certificate_routes.py` | REST GET endpoints: `/api/v1/certificates/{vessel,crew,expiring,{id},{id}/history}` |
| `apps/api/handlers/certificate_handlers.py` | The `CertificateHandlers` class and `get_certificate_handlers()` factory. **1300+ lines. Source of truth.** |
| `apps/api/routes/handlers/certificate_phase4_handler.py` | Phase 4 route shim — 5 native handlers (create_vessel, create_crew, update, link_doc, supersede). See Section 9. |
| `apps/api/handlers/schema_mapping.py` | `get_table()` helper — maps logical names (`"vessel_certificates"`) to actual table names (`"pms_vessel_certificates"`) |
| `apps/api/action_router/registry.py` | ActionDefinition entries for all 10 cert actions — RBAC, required_fields, field_metadata |
| `apps/api/action_router/ledger_metadata.py` | Maps action → event_type for the safety net ledger write |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | INTERNAL_HANDLERS dict — wires cert actions to `_cert_*` wrapper functions |
| `apps/api/routes/handlers/internal_adapter.py` | Phase 4 bridge — `_ACTIONS_TO_ADAPT` list |
| `apps/api/routes/p0_actions_routes.py` | `POST /api/v1/actions/execute` — the single execute endpoint with `_CERT_ACTIONS` mapping |
| `apps/api/tests/cert_binary_tests.py` | 16 binary tests against live DB — each verifies exact row state |

### Database

| Object | Type | Purpose |
|---|---|---|
| `pms_vessel_certificates` | Table | Vessel certs. Has soft-delete, status check, source tracking, F1 cache trigger |
| `pms_crew_certificates` | Table | Crew certs. Has soft-delete, status check, source tracking, import session link |
| `v_certificates_enriched` | View | UNION of vessel + crew, filtered by `is_seed = false AND deleted_at IS NULL`. Adds a `domain` discriminator column. This is what the list page queries. |
| `pms_notes.certificate_id` | Column | FK → `pms_vessel_certificates(id) ON DELETE SET NULL`. Added in migration M4. |
| `refresh_certificate_expiry(p_yacht_id uuid)` | Function | Flips `status = valid → expired` for past-due certs. Writes `status_change` ledger events. Called lazily from both list handlers. |
| `ledger_events` | Table | Immutable audit trail. Every cert mutation + read lands here. |
| `pms_audit_log` | Table | Legacy audit trail — still written but `ledger_events` is canonical. |

---

## 3. Certificate states

### Valid status values (enforced by check constraint)

| Status | What it means | Terminal? |
|---|---|---|
| `valid` | Active, in force | No |
| `expired` | Past expiry date. Auto-set by `refresh_certificate_expiry()` or manual update. | No (can renew) |
| `suspended` | Temporarily halted. Captain/manager signed action, retains visibility. | No (can be reactivated by update) |
| `revoked` | Issuing authority cancelled. Signed action. | **Yes** — cannot change |
| `superseded` | Replaced by a renewal. New cert issued, old one marked superseded. | **Yes** — cannot change |

Both tables enforce this at the DB level:

```sql
CHECK (status IN ('valid','expired','superseded','suspended','revoked'))
```

### State transitions

```
               create
                 ↓
   ┌──────────→ valid ──renew──→ superseded (+ new valid cert)
   │             │
   │             ├──suspend──→ suspended ──update──→ valid
   │             │
   │             ├──revoke──→ revoked (terminal)
   │             │
   │             └──refresh_expiry──→ expired ──renew──→ superseded (+ new valid)
   │                                      │
   │                                      └──update──→ valid (manual fix)
   │
   └─── expired can be renewed (renew creates a new valid cert)
```

Three operations — renew, suspend, revoke — are **signed actions**. They require a signature payload (PIN + TOTP) and are restricted to captain and manager roles only.

### Domain discriminator

Both tables feed `v_certificates_enriched`. The view adds a synthetic column:

```sql
'vessel' AS domain  -- from pms_vessel_certificates branch
'crew'   AS domain  -- from pms_crew_certificates branch
```

The frontend uses this to choose the right title (vessel cert name vs `"Person Name — Cert Type"`), the right icon, and whether to show vessel-only fields like `last_survey_date`.

---

## 4. Actions — the full list

All 10 actions live in `ACTION_REGISTRY` (`apps/api/action_router/registry.py`).

| Action | Variant | Roles | What it does |
|---|---|---|---|
| `create_vessel_certificate` | MUTATE | chief_engineer, captain, manager | Insert row into `pms_vessel_certificates` |
| `create_crew_certificate` | MUTATE | chief_engineer, captain, manager | Insert row into `pms_crew_certificates` |
| `update_certificate` | MUTATE | chief_engineer, captain, manager | Update fields (name, number, dates, authority). Rejects updates on terminal status. |
| `link_document_to_certificate` | MUTATE | chief_engineer, captain, manager | Attach a `doc_metadata` row as the cert document |
| `renew_certificate` | MUTATE | chief_engineer, captain, manager | Insert new cert with updated dates, mark old as `superseded`. Writes `create` ledger event. |
| `suspend_certificate` | **SIGNED** | **captain, manager only** | Set status=`suspended` with reason |
| `revoke_certificate` | **SIGNED** | **captain, manager only** | Set status=`revoked` with reason |
| `supersede_certificate` | **SIGNED** | **captain, manager only** | Mark current as `superseded`, optionally create replacement. Requires PIN+TOTP signature. |
| `archive_certificate` | **SIGNED** | chief_engineer, chief_officer, captain, manager | Soft-delete: set `deleted_at` and `deleted_by`. Auto-detects vessel vs crew. |
| `add_certificate_note` | MUTATE | chief_engineer, captain, manager | Insert into `pms_notes` with `certificate_id` FK set |

### Read actions

Reads don't go through `/api/v1/actions/execute`. They hit `certificate_routes.py` GET endpoints. But **they still write ledger events** — see Section 7.

| Route | Handler | Event type |
|---|---|---|
| `GET /api/v1/certificates/vessel` | `list_vessel_certificates` | view |
| `GET /api/v1/certificates/crew` | `list_crew_certificates` | view |
| `GET /api/v1/certificates/expiring?days_ahead=N&domain={vessel,crew,all}` | `find_expiring_certificates` | view |
| `GET /api/v1/certificates/{id}?domain={vessel,crew}` | `get_certificate_details` | view |
| `GET /api/v1/certificates/{id}/history?domain={vessel,crew}` | `view_certificate_history` | view |

---

## 5. The list page — `/certificates`

`apps/web/src/app/certificates/page.tsx`

The list renders **both vessel and crew certificates in a single unified view**, queried from `v_certificates_enriched`. The adapter reads the `domain` column and displays each row differently:

```typescript
// Vessel cert: "DNV GL Class Certificate"
// Crew cert:   "John Smith — STCW Basic Safety Training"
const title = c.domain === 'crew'
  ? (c.person_name ? `${c.person_name} — ${c.certificate_type}` : c.certificate_type)
  : (c.certificate_name || c.certificate_number);
```

### Filters

Two filter selects, both `type: 'select'` from `FilterFieldConfig`:

1. **Type** (domain): All / Vessel / Crew
2. **Status**: All / Valid / Expired / Revoked / Superseded / Suspended

The filter config shape matters — it must include `type: 'select'` explicitly or TypeScript breaks. See `apps/web/src/features/entity-list/types/filter-config.ts` for the `FilterFieldConfig` interface.

### Why `v_certificates_enriched` and not the raw tables?

1. **UNION the two tables** — one query, both domains, with a discriminator column.
2. **Filter seed data** — the view has `WHERE is_seed = false` so fleet test fixtures don't pollute the list.
3. **Filter soft-deleted rows** — `WHERE deleted_at IS NULL` on both sides.
4. **Normalise `certificate_type`** — uppercased via `UPPER(certificate_type)` to eliminate case inconsistency (`class` vs `CLASS`).

The view definition lives in the DB, not in git. To recreate:

```sql
CREATE VIEW v_certificates_enriched AS
  SELECT id, yacht_id, UPPER(certificate_type) AS certificate_type,
         certificate_name, certificate_number, issuing_authority,
         issue_date, expiry_date, last_survey_date, next_survey_due,
         status, document_id, properties, created_at, deleted_at,
         source, import_session_id, is_seed,
         'vessel' AS domain, NULL::uuid AS person_node_id, NULL::text AS person_name
  FROM pms_vessel_certificates
  WHERE is_seed = false AND deleted_at IS NULL

  UNION ALL

  SELECT id, yacht_id, UPPER(certificate_type) AS certificate_type,
         certificate_type AS certificate_name, certificate_number,
         issuing_authority, issue_date, expiry_date,
         NULL::date AS last_survey_date, NULL::date AS next_survey_due,
         status, document_id, properties, created_at, deleted_at,
         source, import_session_id, false AS is_seed,
         'crew' AS domain, person_node_id, person_name
  FROM pms_crew_certificates
  WHERE deleted_at IS NULL;
```

---

## 6. The lens — `CertificateContent.tsx`

`apps/web/src/components/lens-v2/entity/CertificateContent.tsx`

### Section order (top to bottom)

| Section | Source of data |
|---|---|
| **IdentityStrip** | cert number, name, status pills, details, primary action button |
| **Holder's Certificates** | Other certs for the same person (crew) or vessel. Only shown if `holder_certificates` array is non-empty. |
| **Coverage Details** | scope, capacity, flag_state, trading_area, endorsement, conditions (vessel-only fields) |
| **Related Equipment** | Equipment rows linked via properties (machinery certs) |
| **Renewal History** | Prior period certs in the supersede chain |
| **History** | `prior_periods` — collapsible year-by-year summary |
| **Audit Trail** | Full `pms_audit_log` entries for this cert (collapsed by default) |
| **Related Certificates** | Linked cert rows (teal cert-link styling) |
| **Notes** | `pms_notes` rows where `certificate_id = this.id` |
| **Attachments** | Uploaded files from storage bucket |

### The primary button

The `renew_certificate` action is the primary button on every cert detail view. It does **not** execute directly — it opens an `ActionPopup` with two required fields (new issue date, new expiry date) and optional ones (new cert number, new issuing authority).

```typescript
const handlePrimary = React.useCallback(() => {
  if (renewAction) openActionPopup(renewAction as any);
}, [renewAction]);
```

This was originally `executeAction('renew_certificate', {})` which silently sent no fields and triggered a `MISSING_REQUIRED_FIELD` error. See Section 10 bugs.

### Secondary actions (dropdown)

Everything in `availableActions` except the primary. The dropdown applies a `DANGER_ACTIONS` set for suspend/archive/revoke — these render with destructive styling.

```typescript
const DANGER_ACTIONS = new Set(['suspend_certificate', 'archive_certificate', 'revoke_certificate']);
```

### Field mapping for ActionPopup

`mapActionFields.ts` reads `field_metadata` from the action registry and converts field types to the right UI component:

| Backend type | UI component |
|---|---|
| `date` / `date-pick` | Date picker |
| `text-area` / `textarea` | Textarea |
| `select` / `enum` | Dropdown |
| `text` (or omitted) | Text input |
| `entity-search` | Typeahead with search |

A field is hidden from the form if it's in `BACKEND_AUTO` set (`yacht_id`, `signature`, `idempotency_key`) or already in `action.prefill`.

---

## 7. Ledger + audit — what gets logged

### Two tables, two purposes

| Table | Purpose | Written by |
|---|---|---|
| `pms_audit_log` | Domain audit trail — old_values, new_values, signatures | Every handler explicitly calls `db.table("pms_audit_log").insert(...)` |
| `ledger_events` | Immutable compliance ledger with `proof_hash` chain | Action router safety net + read handlers |

### Mutation logging (safety net)

Every action that goes through `POST /api/v1/actions/execute` is intercepted by the "Phase B ledger safety net" in `p0_actions_routes.py`:

```python
if isinstance(result, dict) and not result.get("_ledger_written"):
    meta = ACTION_METADATA.get(action)
    if meta:
        ledger_event = build_ledger_event(...)
        db_client.table("ledger_events").insert(ledger_event).execute()
```

For this to work, the action must be in `ACTION_METADATA` (`apps/api/action_router/ledger_metadata.py`). All 10 cert actions are there. Missing entries silently skip the ledger write — this was a real bug, see Section 10.

### Read logging (explicit)

Read handlers call `self._ledger_read()` at the start of every request. Fire-and-forget — never blocks the read response.

```python
def _ledger_read(self, yacht_id, user_id, user_role, action, entity_id=None, summary=None):
    try:
        import hashlib
        now = datetime.now(timezone.utc).isoformat()
        proof_input = f"{yacht_id}{entity_id or ''}{action}{now}"
        proof_hash = hashlib.sha256(proof_input.encode()).hexdigest()
        self.db.table("ledger_events").insert({
            "yacht_id": yacht_id,
            "event_type": "view",
            "entity_type": "certificate",
            "entity_id": entity_id or yacht_id,
            "action": action,
            "user_id": user_id or "00000000-0000-0000-0000-000000000000",
            "user_role": user_role or "unknown",
            "change_summary": summary or action.replace("_", " ").capitalize(),
            "source_context": "microaction",
            "proof_hash": proof_hash,
            "event_timestamp": now,
            "created_at": now,
        }).execute()
    except Exception:
        pass
```

For this to work, `certificate_routes.py` must pass `user_id` and `user_role` into the handler's `params` dict. This wiring is easy to miss — if you add a new read endpoint, remember to pass `auth.get("user_id")` and `auth.get("role")` into params.

### Expiry logging (DB function)

`refresh_certificate_expiry()` is a PL/pgSQL function. When it flips a cert from `valid` to `expired`, it directly inserts into `ledger_events` with `source_context = 'system'` and `user_id = '00000000-0000-0000-0000-000000000000'` (the sentinel system user). This captures the automatic state change in the ledger with no user attribution.

### What is NOT logged

| Operation | Logged? | Why |
|---|---|---|
| Import pipeline inserts (CSV, seahub) | **No** | Explicit business decision — imports are considered "already externally audited" |
| Direct SQL from Supabase admin console | **No** | Bypasses all application code |
| Frontend Supabase client reads (if they existed) | **No** | List page uses `FilteredEntityList` → direct Supabase query. This is list-page-only, not the detail view. |

---

## 8. Database layer — schema and RLS

### pms_vessel_certificates

```sql
CREATE TABLE pms_vessel_certificates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id uuid NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    certificate_type text NOT NULL,  -- may be mixed case (see normalisation)
    certificate_name text NOT NULL,
    certificate_number text,
    issuing_authority text NOT NULL,
    issue_date date,
    expiry_date date,
    last_survey_date date,
    next_survey_due date,
    status text NOT NULL DEFAULT 'valid'
        CHECK (status IN ('valid','expired','superseded','suspended','revoked')),
    document_id uuid REFERENCES doc_metadata(id) ON DELETE SET NULL,
    properties jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    deleted_by uuid,
    source text DEFAULT 'manual',
    source_id text,
    imported_at timestamptz,
    import_session_id uuid REFERENCES import_sessions(id) ON DELETE SET NULL,
    is_seed boolean DEFAULT true
);
```

Key indexes: `yacht_id`, `(yacht_id, expiry_date) WHERE deleted_at IS NULL`, `(yacht_id, status)`, `(yacht_id, certificate_type)`.

### pms_crew_certificates

Same shape but with `person_node_id uuid REFERENCES search_graph_nodes(id)` and `person_name text NOT NULL` instead of vessel fields. No `last_survey_date` or `next_survey_due`.

### RLS policies

Both tables have:

1. **Users can view yacht certs** — `yacht_id = get_user_yacht_id()`
2. **Officers can insert** — must be in `is_hod()` or allowed role list
3. **Officers can update** — same
4. **Managers can delete** — `is_manager()` AND yacht match
5. **Service role full access** — for backend writes

The backend uses a tenant Supabase client obtained via `get_tenant_client(auth['tenant_key_alias'])`, which has service_role permissions.

---

## 9. Routing chain — from HTTP request to DB write

This is where compound loss happens. Understand this diagram before adding any new certificate action.

```
HTTP POST /api/v1/actions/execute
    │
    ▼
p0_actions_routes.py::execute_action()
    │
    ├─── Role check (before anything else, for security)
    │
    ├─── resolve_entity_context() — maps entity_id → certificate_id if action in _CERT_ACTIONS
    │
    ├─── REQUIRED_FIELDS check — scans {**request.context, **payload}
    │
    ├─── validate_action_payload() — UUID validation, enum checks
    │
    ├─── Look up handler in HANDLERS dict (routes/handlers/__init__.py)
    │    │
    │    ├─ CERT_HANDLERS (certificate_phase4_handler.py) — PRIORITY
    │    │   Handles: create_vessel, create_crew, update, link_doc, supersede
    │    │   Calls _delegate() → get_certificate_handlers() → adapter → CertificateHandlers method
    │    │
    │    └─ ADAPTER_HANDLERS (internal_adapter.py) — fallback
    │        Handles: renew, suspend, revoke, archive, add_note
    │        Calls INTERNAL_HANDLERS[action_id] from internal_dispatcher.py
    │        Which calls _cert_renew/_cert_suspend/_cert_revoke/_cert_archive
    │        Which calls get_certificate_handlers() → adapter → CertificateHandlers method
    │
    ▼
CertificateHandlers._fn(**params)  ← the actual business logic
    │
    ├─── DB operations on pms_vessel_certificates / pms_crew_certificates
    ├─── Audit log insert into pms_audit_log
    │
    ▼
Return result dict
    │
    ▼
p0_actions_routes.py "Ledger safety net"
    │
    ├─ If result doesn't have `_ledger_written: true`
    ├─ If action is in ACTION_METADATA
    ├─ Write to ledger_events table
    │
    ▼
HTTP 200 response
```

### Why two handler layers?

Historical migration. The system is moving from "Phase 3" (everything in `internal_dispatcher.py`'s `INTERNAL_HANDLERS` dict) to "Phase 4" (domain-native handlers in `routes/handlers/*.py`). Five cert actions were rewritten as Phase 4 native. Five are still routed through the adapter. Both work identically from the user perspective.

**The priority rule:** `CERT_HANDLERS` is merged FIRST in `routes/handlers/__init__.py`, so if an action is in both, the Phase 4 version wins. The adapter only handles what Phase 4 doesn't cover.

### Adding a new certificate action

Follow this checklist exactly. Missing a step creates a silent failure.

1. Add to `ACTION_REGISTRY` in `apps/api/action_router/registry.py` with correct `allowed_roles`, `required_fields`, `field_metadata`, `variant`, `domain="certificates"`.
2. Implement the handler in `apps/api/handlers/certificate_handlers.py` as an adapter function (see existing patterns).
3. Register it in the dict returned by `get_certificate_handlers()`.
4. Add a wrapper in `apps/api/action_router/dispatchers/internal_dispatcher.py` (pattern: `_cert_<name>`).
5. Add the wrapper to `INTERNAL_HANDLERS` dict in `internal_dispatcher.py`.
6. Add the action name to `_ACTIONS_TO_ADAPT` list in `apps/api/routes/handlers/internal_adapter.py`.
7. Add to `ACTION_METADATA` in `apps/api/action_router/ledger_metadata.py` — if missed, mutations succeed but don't log to the ledger.
8. Add the action name to `_CERT_ACTIONS` frozenset in `apps/api/routes/p0_actions_routes.py` — if missed, `entity_id` from context won't map to `certificate_id`.
9. Add to `REQUIRED_FIELDS` dict in `p0_actions_routes.py` if there are required fields beyond yacht_id.
10. Update the frontend `CertificateContent.tsx` to surface the action (add to primary button or dropdown).

Miss step 7 → action works but no ledger entry.
Miss step 8 → 400 "MISSING_REQUIRED_FIELD: certificate_id" in production.
Miss step 9 → 400 for any field not listed.

This is precisely why `certificate_phase4_handler.py` now has an architectural boundary banner at the top — to force engineers to read this checklist.

---

## 10. Bugs I hit during this work — and fixes

### Bug 1: `_supersede_certificate_adapter` missing `return _fn`

**Symptom:** `supersede_certificate` returned HTTP 501 "not registered in certificate_handlers".

**Cause:** The outer factory function was missing `return _fn` at the end. It implicitly returned `None`. The dict had `"supersede_certificate": None` — the key existed but the value was falsy, so `handlers.get("supersede_certificate")` returned None and `_delegate` raised 501.

**Fix:** Added `return _fn` after the inner async function definition.

**Lesson:** Every adapter factory in `certificate_handlers.py` MUST end with `return _fn`. If you copy-paste a new adapter, verify the return.

### Bug 2: `maybe_single()` returns None (not a response object) on no-match

**Symptom:** Crew cert operations returned `'NoneType' object has no attribute 'data'`.

**Cause:** The Supabase Python client's `maybe_single()` behaviour depends on version. In the version we're using, when no row matches it returns `None` for the whole response, not a response object with `data=None`. Code like `result.data` then crashes.

**Fix:** Use `.limit(1).execute()` and guard with `getattr(result, 'data', None) or []` instead of `maybe_single()`. See `_resolve_cert_domain()` in `certificate_handlers.py`.

**Lesson:** Never use `maybe_single()` in this codebase. Use `.limit(1).execute()` and check `rows[0]` if the list is non-empty.

### Bug 3: `_delegate()` didn't pass context → KeyError on `certificate_id`

**Symptom:** Supersede returned 400 `VALIDATION_ERROR: 'certificate_id'` even though `certificate_id` was sent in the request.

**Cause:** The frontend sends `certificate_id` in the request `context`, not the `payload`. The `_delegate()` function in `certificate_phase4_handler.py` was only passing `{**{"yacht_id": ..., "user_id": ...}, **payload}` to the adapter. The `context` dict was never merged in, so `certificate_id` was lost.

**Fix:** Updated `_delegate()` to accept `context` as an argument and merge it into the params dict.

**Lesson:** Any handler that reads `certificate_id` from params must have context merged into those params. Double-check the handler chain if you see KeyError on an ID field.

### Bug 4: `p0_actions_routes.py` had no `_CERT_ACTIONS` mapping

**Symptom:** Even after Bug 3 was fixed, the p0_actions_routes layer was still rejecting requests. The `resolve_entity_context()` function maps `entity_id` → domain-specific IDs (`equipment_id`, `fault_id`, etc.) but had no mapping for certificate actions.

**Fix:** Added `_CERT_ACTIONS` frozenset with all 10 cert action names and an `elif action in _CERT_ACTIONS: ctx.setdefault("certificate_id", entity_id)` branch in `resolve_entity_context()`.

**Lesson:** The EntityLensPage frontend always sends `entity_id` in context. Every domain needs a mapping in `resolve_entity_context()` to translate that to its specific ID field name.

### Bug 5: `p0_actions_routes.py` REQUIRED_FIELDS check only scanned `payload`

**Symptom:** Even after Bugs 3 and 4, supersede was returning 400 `MISSING_REQUIRED_FIELD: certificate_id`.

**Cause:** `payload.get(f)` on line 896 only checked the payload dict. Certificate_id was in the context, so it was invisible to this check.

**Fix:** Changed to `merged_for_check = {**request.context, **payload}` and scanned the merged dict.

**Lesson:** Required fields validation must always check merged context+payload, not just payload.

### Bug 6: `pms_notes` was missing `certificate_id` column

**Symptom:** `add_certificate_note` threw a DB error "column certificate_id does not exist".

**Cause:** The `add_note` handler in `internal_dispatcher.py` had `if params.get("certificate_id"): note_data["certificate_id"] = params["certificate_id"]` — it was designed to support the column, but the migration to actually add it was never run.

**Fix:** Migration M4 — `ALTER TABLE pms_notes ADD COLUMN certificate_id uuid REFERENCES pms_vessel_certificates(id) ON DELETE SET NULL;`

**Lesson:** When adding a note to any entity, check that `pms_notes` actually has that FK column. The handler code might reference a column that doesn't exist.

### Bug 7: Legacy `pms_certificates` table still existed but was bypassed

**Symptom:** 18 real vessel certificates were in `pms_certificates` (a legacy table) that the frontend never queried. `v_certificates_enriched` only reads `pms_vessel_certificates`. Users couldn't see those 18 certs.

**Fix:** Migration M1 — copied 18 rows into `pms_vessel_certificates` with `is_seed=false`, normalised `certificate_type` to uppercase, dropped the legacy table.

**Lesson:** If you find a table with fewer rows than the "active" one, check if it's being queried by the frontend. Legacy tables silently hide data.

### Bug 8: `pms_crew_certificates` had no `status` column

**Symptom:** Crew cert expiry couldn't be tracked. Suspend/revoke had nowhere to write the new status.

**Fix:** Migration M3 — `ALTER TABLE pms_crew_certificates ADD COLUMN status text NOT NULL DEFAULT 'valid' CHECK (status IN ('valid','expired','revoked','suspended'));`

**Lesson:** Check that every domain table has the columns the handlers expect. Don't assume schema parity between related tables.

### Bug 9: `pms_crew_certificates` had no `deleted_at` column

**Symptom:** `archive_certificate` worked for vessel certs (which had `deleted_at`) but silently failed for crew certs (which didn't).

**Fix:** Migration M6 — added `deleted_at timestamptz` and `deleted_by uuid` columns to crew certs.

**Lesson:** Soft-delete needs two columns on every table that supports it. Don't add a FK constraint on `deleted_by` unless you're sure the user UUIDs will exist in `auth.users` — I tried that initially and it caused test failures.

### Bug 10: 5 certificate actions missing from `ACTION_METADATA`

**Symptom:** Create, update, supersede, link_document actions ran successfully but left no ledger trace.

**Cause:** `ACTION_METADATA` in `ledger_metadata.py` had only 5 cert entries. The other 5 actions (`create_vessel_certificate`, `create_crew_certificate`, `update_certificate`, `link_document_to_certificate`, `supersede_certificate`) were missing.

**Fix:** Added all 5 entries with correct event types (create / update / status_change).

**Lesson:** Always audit `ACTION_METADATA` when touching any domain. The safety net is only a net for actions it knows about.

### Bug 11: `refresh_certificate_expiry()` flipped status but didn't log

**Symptom:** Expired certs auto-flipped from `valid → expired` with no audit trail. Silent status change.

**Fix:** Rewrote the PL/pgSQL function to insert a `ledger_events` row for every cert it flipped, with `source_context='system'` and the sentinel system user UUID.

**Lesson:** Any automatic state change (triggers, cron jobs, DB functions) must write to the ledger. Automatic does not mean invisible.

### Bug 12: Import pipeline bypassed the ledger

**Symptom:** Certs created by the import pipeline never appeared in the ledger.

**Decision:** Explicit business decision — imports are treated as "already externally audited" and intentionally do not write to the ledger. This is documented behaviour, not a bug. If this ever changes, the import service needs to write `create` ledger events for every inserted cert.

### Bug 13: `ENTITY_TABLE_MAP["certificate"]` pointed only to vessel

**Symptom:** Generic `soft_delete_entity()` handler worked for vessel certs but couldn't delete crew certs.

**Fix:** Stopped using generic `soft_delete_entity` for certificates. Wrote a dedicated `_archive_certificate_adapter` that calls `_resolve_cert_domain()` to auto-detect which table the cert lives in.

**Lesson:** Generic entity handlers break for domains with multiple tables. Don't use them — write domain-aware handlers.

### Bug 14: Pre-push hook rejected branch names containing "main"

**Symptom:** `git push -u origin feat/certificate-domain-...` was rejected with "BLOCKED: Direct push to 'main'".

**Cause:** `.git/hooks/pre-push` used `[[ "$remote_ref" == *"main"* ]]` — substring match. Branch names containing "domain", "remain", "maintenance" etc. all matched.

**Fix:** Changed to exact match: `[[ "$remote_ref" == "refs/heads/main" ]]`.

**Lesson:** Never use substring matching for branch protection.

---

## 11. Things I wish I knew at the start

### The two-file naming collision

`handlers/certificate_handlers.py` (plural, CertificateHandlers class) and `routes/handlers/certificate_handler.py` (singular, Phase 4 route shim) coexisted. The one-letter difference was a compound-loss trap. I renamed the singular one to `certificate_phase4_handler.py` to make the shim boundary explicit.

If you see `certificate_handlers.py` in an import, it's the source of truth (CertificateHandlers class, 1300+ lines). If you see `certificate_phase4_handler.py`, it's a thin shim that delegates back to `certificate_handlers.py`. Adding logic to the shim is almost always wrong.

### Render vs local deployments

The Render backend auto-deploys on merge to `main`. If role tests fail against Render with errors like "501 not implemented" that match OLD code paths, the cause is always that your fix hasn't been deployed yet. Render deploys take 3–5 minutes after merge.

Use Docker locally BEFORE pushing. Run:

```bash
bash scripts/dev/pre-push-check.sh
```

This builds the Dockerfile exactly as Render will, runs the 16 binary handler tests, and reports pass/fail. If it passes locally, Render will pass. If Render fails but Docker passes, the deploy hasn't completed.

### The `FEATURE_CERTIFICATES` env var

Every certificate route in `certificate_routes.py` has `if not check_feature_flag(): raise HTTPException(404, ...)`. This checks `os.getenv("FEATURE_CERTIFICATES", "false").lower() == "true"`.

- **Local Docker:** must be set in `docker-compose.yml` under the api service environment section. I added it during this work.
- **Render:** must be set in the Render dashboard. It is currently set.
- **Frontend dev:** irrelevant — the frontend doesn't check this flag.

If you get mysterious 404s on `/api/v1/certificates/*` endpoints, this is the first thing to check.

### The user role comes from TENANT DB, not MASTER

The test users table was wrong. `captain.tenant@alex-short.com` is labelled "HOD / chief_engineer" in the test docs but is actually `captain` in the `auth_users_roles` table on the TENANT DB. There is **no chief_engineer test user**.

The action router resolves the user role via `lookup_tenant_for_user()` which queries:

```
TENANT DB → auth_users_roles table → role column
```

It does NOT use `user_accounts.role` on the MASTER DB. Don't trust the master user_accounts table for role authorization.

To check a real role:

```sql
SELECT u.email, ar.role, ar.department
FROM auth_users_roles ar
JOIN auth.users u ON u.id = ar.user_id
WHERE u.email = 'captain.tenant@alex-short.com';
```

### The route prefix is `/api/v1/certificates`, not `/v1/certificates`

The `certificate_routes.py` router is mounted at `/api/v1/certificates/*` in `pipeline_service.py` line 299:

```python
app.include_router(certificate_router, prefix="/api/v1/certificates", tags=["certificates"])
```

If you try to hit `localhost:8000/v1/certificates/vessel` it will 404. The action router (`/v1/actions/execute`) and the REST routes (`/api/v1/certificates/*`) use different prefixes.

### Supabase pooler ports differ

The tenant DB has two ports:

- **5432** — direct connection (preferred for testing)
- **6543** — Supavisor pooler (what the app uses in production)

Port 6543 often has connection timeouts from local machines. Use 5432 for ad-hoc SQL. The app config uses 6543 for pooling.

```bash
# Direct:
psql "postgresql://postgres:PASSWORD@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require"

# Pooler:
psql "postgresql://postgres:PASSWORD@db.vzsohavtuotocgrfkfyd.supabase.co:6543/postgres?sslmode=require"
```

### Binary testing means DB row verification, not HTTP codes

Don't trust HTTP 200 as proof of success. A handler can return 200 while writing nothing to the DB, or writing the wrong thing. Binary tests must verify the exact row state in the DB AFTER the operation:

```python
# Call the handler
await handlers["renew_certificate"](**params)

# Verify the exact state change
old_row = db.table("pms_vessel_certificates").select("*").eq("id", old_id).execute().data[0]
assert old_row["status"] == "superseded"

new_row = db.table("pms_vessel_certificates").select("*").eq("id", new_id).execute().data[0]
assert new_row["expiry_date"] == "2027-02-01"

audit = db.table("pms_audit_log").select("*").eq("entity_id", old_id).execute().data
assert any(a["action"] == "renew_certificate" for a in audit)
```

16/16 binary tests live in `apps/api/tests/cert_binary_tests.py`. Run them after any cert change.

---

## 12. Known limitations and Phase 2 work

- **No notification system** — 90/30/7 day expiry alerts don't exist. `find_expiring_certificates` is a read endpoint only; nothing calls it automatically or sends alerts to assigned officers.
- **No certificate assignment** — there is no "responsible officer" per cert. You can't say "Chief Engineer owns renewal of this ISM cert".
- **No ledger integration with finance** — cert renewal costs (class survey fees, flag state fees) cannot be recorded against a cert entity in the finance ledger. Planned for Phase 2.
- **No PDF export / compliance register** — port state control inspections expect a printable cert register. Not built. The closest is `find_expiring_certificates` which returns JSON grouped by urgency.
- **No cert template library** — every cert is entered manually. No library of standard cert types with pre-filled fields per issuing authority.
- **`view_certificate_history` reads from `pms_audit_log`** — not from `ledger_events`. These two tables have drifted slightly. The canonical compliance trail is `ledger_events`; the domain audit view still uses `pms_audit_log` for backwards compatibility.
- **Import pipeline is deliberately excluded from the ledger** — see Bug 12.
- **Only one `document_id` per cert** — the table has `document_id uuid` as a single FK, not a list. For multiple documents use `pms_attachments` with `entity_type='certificate'` and `entity_id=<cert_id>`.

---

## 13. Test strategy

### 1. Binary handler tests (the bedrock)

`apps/api/tests/cert_binary_tests.py` — 16 tests that:

1. Create a fresh test cert
2. Call the handler directly against the live tenant DB
3. Query the DB to verify exact row state
4. Clean up

These don't test HTTP routing. They test that the handler logic produces the correct DB state.

Run with:

```bash
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co" \
SUPABASE_SERVICE_KEY="<tenant_service_key>" \
MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co" \
MASTER_SUPABASE_JWT_SECRET="<master_jwt_secret>" \
FEATURE_CERTIFICATES="true" \
python3 apps/api/tests/cert_binary_tests.py
```

### 2. Role-based API tests

`/tmp/role_test_verified.sh` (not committed, write fresh per session). Tests:

- crew → 403 on all mutations
- captain → 200 on renew, suspend, revoke, supersede
- manager → 200 on renew, suspend, revoke, create

Uses real JWTs from Supabase auth. Points at either `localhost:8000` (Docker) or `https://pipeline-core.int.celeste7.ai` (Render).

### 3. Docker pre-push check

`scripts/dev/pre-push-check.sh` — builds Docker image, starts container, runs healthcheck, runs binary handler tests, tears down. This is the gate that makes sure Render never receives broken code.

### 4. Playwright e2e

- `apps/web/e2e/shard-33-lens-actions/certificate-actions.spec.ts`
- `apps/web/e2e/shard-34-lens-actions/certificate-actions-full.spec.ts`

These test the frontend — clicking buttons, filling ActionPopup forms, verifying the UI updates. They do NOT test the ledger or audit layer — that's what binary tests cover.

### 5. Role test verification checklist

Before claiming a role test failure is real:

1. Is the user's TENANT role (from `auth_users_roles`) what you think it is? Query the DB.
2. Is FEATURE_CERTIFICATES set in the environment?
3. Is the route prefix `/api/v1/certificates/*` or `/v1/actions/execute`?
4. Is the request hitting the right container (local Docker vs live Render)?
5. Has the latest code been deployed? Check by hitting an endpoint that returned an error in the old code.

---

## 14. Communication with other domains

### Documents

`link_document_to_certificate` attaches a row from `doc_metadata` to a cert via the `document_id` FK. The cert handler validates the document exists before linking. Document deletion cascades via `ON DELETE SET NULL`.

### Equipment

Vessel certs can link to equipment via the `properties` JSON field (e.g., machinery certs for a specific engine). There is no FK — the link is soft via `properties.equipment_id`. The frontend `Related Equipment` section reads from `related_equipment` in the detail response.

### Notes

`pms_notes` has `certificate_id` as one of several optional FKs. Adding a note calls the generic `add_note` handler which detects the FK column based on which ID is in the params. This handler is shared with equipment, faults, work orders, warranties, documents, parts.

### Audit log

`pms_audit_log` is written by every cert mutation with `entity_type = "certificate"` and `entity_id = <cert_uuid>`. This is how `view_certificate_history` produces its response.

### Ledger

`ledger_events` is written by:
- The action router safety net (all mutations)
- The `_ledger_read` helper (all reads)
- `refresh_certificate_expiry()` DB function (auto-expiry)

Every row has `entity_type = "certificate"` and forms part of the tamper-evident compliance chain via `proof_hash`.

### Handover

Handover exports can include cert status snapshots. The handover module pulls from `pms_vessel_certificates` and `pms_crew_certificates` directly via its own queries — it doesn't go through the cert handlers. Changes to cert schema need to be communicated to HANDOVER01 because their queries may break.

### Hours of Rest (HoR)

No direct interaction. Crew certs and HoR records both reference crew via person_name/person_node_id but are independent domains.

### Warranty

No direct interaction. Both have signed actions and audit/ledger coverage but operate on different tables.

---

## 15. Quick-reference commands

### DB queries

```sql
-- Count certs by domain and status
SELECT domain, status, COUNT(*) FROM v_certificates_enriched GROUP BY domain, status;

-- Recent ledger events for certs
SELECT action, event_type, entity_id, user_role, change_summary, created_at
FROM ledger_events
WHERE entity_type = 'certificate'
ORDER BY created_at DESC
LIMIT 20;

-- Force expiry refresh for a yacht
SELECT refresh_certificate_expiry('<yacht_uuid>');

-- Find all certs linked to a specific document
SELECT id, certificate_name FROM pms_vessel_certificates WHERE document_id = '<doc_id>';
```

### Action router calls

```bash
# Get a JWT (any role)
JWT=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: $MASTER_ANON" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' | jq -r .access_token)

# Call renew
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "renew_certificate",
    "context": {"yacht_id": "85fe1119-...", "certificate_id": "<cert_id>"},
    "payload": {"new_issue_date": "2026-01-01", "new_expiry_date": "2027-01-01"}
  }'
```

### Read certs

```bash
# List vessel certs
curl "https://pipeline-core.int.celeste7.ai/api/v1/certificates/vessel?limit=10" \
  -H "Authorization: Bearer $JWT"

# Get single cert
curl "https://pipeline-core.int.celeste7.ai/api/v1/certificates/<cert_id>?domain=vessel" \
  -H "Authorization: Bearer $JWT"

# Find expiring within 90 days
curl "https://pipeline-core.int.celeste7.ai/api/v1/certificates/expiring?days_ahead=90&domain=all" \
  -H "Authorization: Bearer $JWT"
```

### Local Docker

```bash
# Start the API locally
docker compose --profile api up -d

# Healthcheck
curl localhost:8000/health

# Run binary tests
bash scripts/dev/pre-push-check.sh

# Tear down
docker compose --profile api down
```

---

## 16. Handover notes to the next engineer

1. **Never use `maybe_single()`** in this codebase. Use `.limit(1).execute()` with a length check.
2. **Don't add logic to `certificate_phase4_handler.py`** unless it's a Phase 4 native action. The architectural banner at the top of that file explains why.
3. **Always update `ACTION_METADATA` and `_CERT_ACTIONS`** when adding a new cert action. Six places total — the checklist is in Section 9.
4. **Binary test every change** against the live tenant DB. HTTP 200 lies.
5. **Use Docker locally before pushing.** Render is the last gate, not the first.
6. **The `renew_certificate` button opens a popup, it doesn't execute directly.** Don't "simplify" this back.
7. **Crew certs lived without a `status` column for months.** Double-check schema parity if you add anything that assumes both tables are identical.
8. **The import pipeline intentionally bypasses the ledger.** This is a business decision. If you need to change it, ask.
9. **`captain.tenant@alex-short.com` is a captain, not an HOD.** The test docs lie. Query `auth_users_roles` to check.
10. **`v_certificates_enriched` is the single source of truth for the list page.** Both tables feed it. Don't query either table directly from the frontend.
