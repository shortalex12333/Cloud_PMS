# Certificates Domain — Complete Engineer Reference

**Written:** 2026-04-14  
**Author:** CERTIFICATE01  
**Status:** Current as of PR #525 merged to main  
**Scope:** Everything about the certificate domain — DB, API, action router, ledger, frontend, cross-domain wiring, bugs, limitations, flow.

---

## What certificates actually are

A certificate in the maritime context is not a document. It is a **dated legal obligation** issued by an external authority (flag state, classification society, port state control). If it lapses, the vessel cannot legally operate. An inspector can detain the vessel. The insurer can void coverage.

The certificate system is therefore not a filing cabinet. It is a **compliance countdown clock with a tamper-evident evidence trail**.

There are two distinct certificate types in this system:

- **Vessel certificates** — issued to the vessel itself. ISM, ISPS, SOLAS, MLC, CLASS, FLAG, LOAD_LINE, MARPOL, IOPP, TONNAGE, IOPP, MANNING, REGISTRATION. Cover the ship's right to operate under specific regulations.
- **Crew certificates** — issued to individual seafarers. STCW, ENG1, COC (Certificate of Competency), GMDSS, BST (Basic Safety Training), MEDICAL_CARE. Cover the seafarer's qualifications.

Both live in the same UI page but separate DB tables.

---

## The three database tables

All tables live in the **TENANT Supabase** (`vzsohavtuotocgrfkfyd`), not the MASTER.

### `pms_vessel_certificates`

The primary vessel certificate store. 371 rows in production (338 seed, 33 real as of 2026-04-14).

```
id                uuid         PK
yacht_id          uuid         FK → yacht_registry(id) ON DELETE CASCADE
certificate_type  text         NOT NULL  (uppercase, e.g. "ISM", "CLASS", "FLAG")
certificate_name  text         NOT NULL  (e.g. "ISM Safety Management Certificate")
certificate_number text                  unique per yacht+type
issuing_authority text         NOT NULL  (e.g. "DNV GL", "Flag State")
issue_date        date
expiry_date       date
last_survey_date  date                   vessel-specific — survey window start
next_survey_due   date                   vessel-specific — survey window end
status            text         NOT NULL  DEFAULT 'valid'
                               ENUM: valid | expired | superseded | suspended | revoked
document_id       uuid         FK → doc_metadata(id) ON DELETE SET NULL
properties        jsonb        DEFAULT '{}'  — stores supersede reason, cascade metadata
created_at        timestamptz  NOT NULL
deleted_at        timestamptz             soft-delete field
deleted_by        uuid                    soft-delete actor (no FK — plain UUID)
source            text         DEFAULT 'manual'  — 'manual' | 'imported'
source_id         text                   external ID if imported
imported_at       timestamptz
import_session_id uuid         FK → import_sessions(id)
is_seed           boolean      DEFAULT true  — seed data flag, NOT shown in UI
```

**Critical:** `is_seed = true` records are filtered out by the view. 338 of 353 rows are seed data. Only 15+ are real.

**Triggers:**
- `trg_certificates_cache_invalidate` — fires on INSERT/UPDATE, invalidates F1 cache for the `certificate` entity type.

**Indexes:** `yacht_id`, `status`, `certificate_type`, `expiry_date`, `next_survey_due`, `document_id`, `import_session_id`.

### `pms_crew_certificates`

Crew / seafarer certificate store. 38 rows in production.

```
id                uuid         PK
yacht_id          uuid         FK → yacht_registry(id) ON DELETE CASCADE
person_node_id    uuid         FK → search_graph_nodes(id) ON DELETE SET NULL  (nullable)
person_name       text         NOT NULL  — free text, not FK to crew table
certificate_type  text         NOT NULL  (e.g. "STCW Basic Safety Training")
certificate_number text
issuing_authority text
issue_date        date
expiry_date       date
document_id       uuid         FK → doc_metadata(id) ON DELETE SET NULL
properties        jsonb        DEFAULT '{}'
created_at        timestamptz  NOT NULL
source            text         DEFAULT 'manual'
source_id         text
imported_at       timestamptz
import_session_id uuid         FK → import_sessions(id)
status            text         NOT NULL  DEFAULT 'valid'
                               ENUM: valid | expired | revoked | suspended
deleted_at        timestamptz             added 2026-04-14
deleted_by        uuid                    added 2026-04-14 (no FK constraint — matches vessel pattern)
```

**Key difference from vessel:** No `last_survey_date`, `next_survey_due`, `is_seed`. No `certificate_name` (cert type IS the name for crew). No `deleted_by` FK constraint.

**Important:** `person_name` is a free text field. It does NOT FK to any crew/person table. This means if a crew member's name changes in the crew system, their certificates stay linked by name string only. Known limitation.

### `pms_certificates` (DROPPED)

Legacy 18-row table. Migrated into `pms_vessel_certificates` (is_seed=false) and dropped on 2026-04-14. **Do not reference this table anywhere.** If you see it in old code, that code is stale.

---

## The unified view: `v_certificates_enriched`

The frontend page does NOT query the raw tables. It queries this view:

```sql
CREATE VIEW v_certificates_enriched AS
  SELECT
    id, yacht_id,
    UPPER(certificate_type) AS certificate_type,  -- normalises case inconsistency
    certificate_name, certificate_number, issuing_authority,
    issue_date, expiry_date, last_survey_date, next_survey_due,
    status, document_id, properties, created_at, deleted_at,
    source, import_session_id, is_seed,
    'vessel' AS domain,
    NULL::uuid AS person_node_id,
    NULL::text AS person_name
  FROM pms_vessel_certificates
  WHERE is_seed = false AND deleted_at IS NULL

  UNION ALL

  SELECT
    id, yacht_id,
    UPPER(certificate_type) AS certificate_type,
    certificate_type AS certificate_name,   -- crew: type IS the name
    certificate_number, issuing_authority,
    issue_date, expiry_date,
    NULL::date AS last_survey_date,         -- vessel-only field
    NULL::date AS next_survey_due,          -- vessel-only field
    status, document_id, properties, created_at, deleted_at,
    source, import_session_id,
    false AS is_seed,
    'crew' AS domain,                       -- discriminator column
    person_node_id, person_name
  FROM pms_crew_certificates
  WHERE deleted_at IS NULL;
```

**The `domain` column is critical.** It tells the frontend and adapter which table the cert came from. Without it, you cannot safely route mutations.

**RLS:** The view inherits RLS from the underlying tables. Authenticated users can only see certs for their `yacht_id`.

---

## Expiry automation: `refresh_certificate_expiry()`

```sql
CREATE FUNCTION refresh_certificate_expiry(p_yacht_id uuid) RETURNS void
```

This DB function:
1. Finds all `pms_vessel_certificates` for the yacht with `status = 'valid'` and `expiry_date < CURRENT_DATE`
2. Updates them to `status = 'expired'`
3. Writes a `status_change` ledger event for each flip, `source_context = 'system'`
4. Does the same for `pms_crew_certificates`

**When it runs:** Called lazily at the start of `list_vessel_certificates` and `list_crew_certificates` handlers. Every time a user opens the certificates list, expired statuses are corrected. There is no nightly cron. If nobody views the page, statuses drift — a known limitation.

**Why lazy:** No `pg_cron` available in Supabase on this plan. Chosen over a Render-side scheduled endpoint to avoid an extra network hop.

---

## File map — exact names and locations

```
BACKEND (apps/api/)
│
├── handlers/
│   └── certificate_handlers.py          ← MAIN LOGIC FILE. CertificateHandlers class.
│                                           All 14 registered handlers.
│                                           _renew_certificate_adapter
│                                           _change_certificate_status_adapter (factory for suspend/revoke)
│                                           _archive_certificate_adapter
│                                           _resolve_cert_domain (auto-detects vessel/crew table)
│                                           _ledger_read (view event writer)
│                                           get_certificate_handlers(supabase_client) → dict
│
├── routes/
│   ├── certificate_routes.py            ← REST GET endpoints only.
│   │                                      GET /api/v1/certificates/vessel
│   │                                      GET /api/v1/certificates/crew
│   │                                      GET /api/v1/certificates/expiring
│   │                                      GET /api/v1/certificates/{id}
│   │                                      GET /api/v1/certificates/{id}/history
│   │                                      POST /api/v1/certificates/debug/pipeline-test (dev only)
│   │
│   └── handlers/
│       ├── certificate_phase4_handler.py ← Phase 4 route SHIM. 5 native handlers only:
│       │                                   create_vessel, create_crew, update,
│       │                                   link_document, supersede.
│       │                                   All other cert actions go via internal_adapter.
│       │                                   ⚠️ READ THE BANNER AT TOP before adding anything here.
│       │
│       ├── internal_adapter.py          ← Migration shim. Routes legacy actions to
│       │                                   INTERNAL_HANDLERS in internal_dispatcher.
│       │                                   cert actions in _ACTIONS_TO_ADAPT:
│       │                                   renew, archive, suspend, revoke, add_note
│       │
│       └── __init__.py                  ← Assembles all HANDLERS dicts. CERT_HANDLERS
│                                           takes priority over ADAPTER_HANDLERS.
│
├── action_router/
│   ├── registry.py                      ← All 10 certificate action definitions.
│   │                                      allowed_roles, required_fields, field_metadata.
│   │                                      Lines ~1570 (supersede), ~2546 (add_note),
│   │                                      ~3448 (archive/suspend/revoke), ~3626 (renew),
│   │                                      ~1544 (create_vessel/crew), ~1561 (update/link)
│   │
│   ├── ledger_metadata.py               ← Maps all 10 cert actions to ledger event_type.
│   │                                      Used by p0_actions_routes safety net.
│   │
│   └── dispatchers/
│       └── internal_dispatcher.py       ← INTERNAL_HANDLERS dict.
│                                           _cert_renew, _cert_archive, _cert_suspend,
│                                           _cert_revoke wrappers.
│                                           _cert_supersede_certificate (legacy wrapper)
│                                           All at lines 368–451.
│
├── routes/
│   └── p0_actions_routes.py             ← Handles POST /v1/actions/execute.
│                                           Contains Phase B ledger safety net.
│                                           _CERT_ACTIONS frozenset — maps entity_id → certificate_id.
│                                           REQUIRED_FIELDS dict — validated from merged context+payload.
│
└── tests/
    ├── cert_binary_tests.py             ← 16-test binary suite. Each test verifies
    │                                      exact DB row state. No mocks.
    │                                      Run: python3 tests/cert_binary_tests.py
    │
    └── handlers/
        └── test_remaining_handlers.py   ← Unit tests for certificate_phase4_handler.py.
                                            Imports from routes.handlers.certificate_phase4_handler.

FRONTEND (apps/web/src/)
│
├── app/
│   └── certificates/
│       └── page.tsx                     ← The /certificates page.
│                                           FilteredEntityList → v_certificates_enriched
│                                           Filters: domain (vessel/crew), status
│                                           Adapter: certAdapter — routes crew/vessel
│                                           EntityDetailOverlay → CertificateContent
│
└── components/
    └── lens-v2/
        └── entity/
            └── CertificateContent.tsx   ← The detail lens. 442 lines.
                                            Sections: Identity → Holder Certs →
                                            Coverage → Equipment → Renewal History →
                                            Audit Trail → Related Certs → Notes →
                                            Attachments
                                            Primary action: renew (opens ActionPopup)
                                            Secondary: suspend, revoke, archive, add_note
                                            DANGER_ACTIONS: suspend, archive, revoke
```

---

## How a read works (full flow)

```
User opens /certificates
        ↓
page.tsx — FilteredEntityList queries Supabase directly
        ↓ (client-side, uses MASTER JWT + Supabase anon key)
v_certificates_enriched view
        ↓
Returns domain='vessel'|'crew' per row
        ↓
certAdapter maps domain → title, type, entityRef
        ↓
User clicks a cert → EntityDetailOverlay opens
        ↓
EntityLensPage fetches /v1/entity/certificate/{id}
        ↓
entity_routes.py → certificate_handlers.get_certificate_details()
        ↓
handler calls _ledger_read() [view event to ledger_events]
        ↓
handler reads pms_vessel_certificates OR pms_crew_certificates
        ↓
returns CertificateContent data shape
        ↓
CertificateContent.tsx renders all sections
```

**IMPORTANT:** The list page queries Supabase DIRECTLY from the browser using the anon key + RLS. The detail view goes through the Render API. These are different auth paths.

---

## How a mutation works (full flow)

Example: captain clicks "Renew Certificate"

```
CertificateContent.tsx
        ↓
handlePrimary() → openActionPopup(renewAction)
        ↓
ActionPopup renders fields: new_issue_date, new_expiry_date
        ↓
User fills form → submits
        ↓
executeAction('renew_certificate', {new_issue_date, new_expiry_date})
        ↓
POST /v1/actions/execute {action, context:{yacht_id, entity_id, certificate_id}, payload}
        ↓
p0_actions_routes.py
  1. Role check (registry allowed_roles: chief_engineer, captain, manager)
  2. REQUIRED_FIELDS check (merged context + payload)
  3. _CERT_ACTIONS mapping: entity_id → certificate_id
  4. validate_action_payload()
  5. RLS entity validation
  6. Routes to HANDLERS["renew_certificate"]
        ↓
HANDLERS lookup order:
  certificate_phase4_handler.py HANDLERS → not found (renew not in Phase 4)
  internal_adapter HANDLERS → found (renew is in _ACTIONS_TO_ADAPT)
        ↓
internal_adapter calls INTERNAL_HANDLERS["renew_certificate"]
        ↓
_cert_renew() in internal_dispatcher.py
        ↓
get_certificate_handlers(db).get("renew_certificate")
        ↓
_renew_certificate_adapter() in certificate_handlers.py
  1. _resolve_cert_domain() — finds which table the cert is in
  2. Validates not superseded/revoked
  3. Inserts new cert (copy old fields, new dates)
  4. Updates old cert status → 'superseded'
  5. Writes pms_audit_log entry
  6. Returns {status, renewed_certificate_id, superseded_certificate_id}
        ↓
p0_actions_routes Phase B ledger safety net
  ACTION_METADATA["renew_certificate"] → event_type='create'
  Inserts to ledger_events
        ↓
Frontend: onSuccess → refetch entity → CertificateContent re-renders
```

---

## The 10 certificate actions

| action_id | Layer | Roles | Notes |
|---|---|---|---|
| `create_vessel_certificate` | Phase 4 shim → handlers | chief_engineer, captain, manager | |
| `create_crew_certificate` | Phase 4 shim → handlers | chief_engineer, captain, manager | |
| `update_certificate` | Phase 4 shim → handlers | chief_engineer, captain, manager | Blocked on superseded/revoked |
| `link_document_to_certificate` | Phase 4 shim → handlers | chief_engineer, captain, manager | Validates doc_id exists first |
| `supersede_certificate` | Phase 4 shim → handlers | captain, manager | **SIGNED** — requires full signature payload |
| `renew_certificate` | internal_adapter → dispatcher | chief_engineer, captain, manager | Creates new cert, supersedes old |
| `suspend_certificate` | internal_adapter → dispatcher | captain, manager only | Sets status='suspended', SIGNED |
| `revoke_certificate` | internal_adapter → dispatcher | captain, manager only | Sets status='revoked', SIGNED |
| `archive_certificate` | internal_adapter → dispatcher | captain, manager | Soft-delete, both tables |
| `add_certificate_note` | internal_adapter → dispatcher | chief_engineer, captain, manager | Writes to pms_notes.certificate_id |

### Adding a new certificate action — required steps

1. Add `ActionDefinition` to `registry.py` with `domain="certificates"`
2. Add handler function in `handlers/certificate_handlers.py`, register in `get_certificate_handlers()`
3. Add `_cert_*` wrapper in `action_router/dispatchers/internal_dispatcher.py`
4. Add to `INTERNAL_HANDLERS` dict in same file
5. Add to `_ACTIONS_TO_ADAPT` in `routes/handlers/internal_adapter.py`
6. Add to `ACTION_METADATA` in `action_router/ledger_metadata.py`
7. Do NOT add to `certificate_phase4_handler.py` unless it is a Phase 4 native handler

---

## Certificate status lifecycle

```
         ┌──────────┐
         │  valid   │◄──────── (renewed cert starts here)
         └────┬─────┘
              │
    ┌─────────┼──────────┬──────────┐
    ▼         ▼          ▼          ▼
expired   superseded  suspended  revoked
              │
         (terminal)
```

- **valid** → expired (auto, via `refresh_certificate_expiry`)
- **valid** → superseded (via `supersede_certificate` SIGNED action — old cert when renewed)
- **valid** → suspended (via `suspend_certificate` SIGNED — captain/manager only)
- **valid** → revoked (via `revoke_certificate` SIGNED — captain/manager only)
- **expired** → valid (via `renew_certificate` — creates new cert, old becomes superseded)
- **superseded** → terminal. Cannot be changed.
- **revoked** → terminal. Cannot be changed.

Status check constraints:
- `pms_vessel_certificates`: `valid | expired | superseded | suspended | revoked`
- `pms_crew_certificates`: `valid | expired | revoked | suspended`

---

## Ledger coverage — what gets logged and how

Every certificate operation is logged. No exceptions.

### Mutations (via ACTION_METADATA safety net in p0_actions_routes)

```
create_vessel_certificate  → event_type: create
create_crew_certificate    → event_type: create
update_certificate         → event_type: update
link_document_to_certificate → event_type: update
supersede_certificate      → event_type: status_change
renew_certificate          → event_type: create
suspend_certificate        → event_type: status_change
revoke_certificate         → event_type: status_change
archive_certificate        → event_type: update
add_certificate_note       → event_type: update
```

The safety net fires after every successful handler execution where `result["_ledger_written"]` is falsy. Fire-and-forget — never blocks the mutation response.

### Reads (via `_ledger_read()` in CertificateHandlers)

```
list_vessel_certificates   → event_type: view
list_crew_certificates     → event_type: view
get_certificate_details    → event_type: view
view_certificate_history   → event_type: view
find_expiring_certificates → event_type: view
```

Written synchronously inside each handler. Fire-and-forget — never blocks the read response. `user_id` and `user_role` come from params injected by `certificate_routes.py`.

### Expiry automation

```
refresh_certificate_expiry() → event_type: status_change, source_context: system
user_id: 00000000-0000-0000-0000-000000000000 (sentinel for system actor)
```

### What is NOT logged

- **Import pipeline** — `import_service.py` writes directly to the DB tables, bypasses the action router and ledger safety net. Imported certs have no ledger trace. This is intentional (imports are considered externally audited at source).

---

## Cross-domain interactions

### With work orders
**Currently:** None. A cert renewal does not automatically create a work order.
**Gap:** In real vessel ops, renewing an ISM cert requires booking a class surveyor — that's a work order. No bridge exists. Future: `renew_certificate` could optionally create a linked work order.

### With the ledger
**Current:** All 10 mutations + 5 reads + expiry automation write to `ledger_events`. Full coverage. The `proof_hash` chain on ledger_events provides tamper-evidence.

### With documents (`doc_metadata`)
**Current:** `link_document_to_certificate` attaches a single doc to a cert. `document_id` is a single FK — one cert can only have one directly linked document.
**Gap:** Multi-document support doesn't exist. Certificate PDFs are stored as attachments via `pms_attachments` (uploaded via the Attachments section in the lens), not via `document_id`.

### With the handover system
**Current:** None. Certificate register is not includable in a handover export.
**Gap:** Real-world handovers include a cert register. Not wired.

### With notifications
**Current:** None. No expiry warnings are pushed to any user.
**Gap:** 90-day, 30-day, 7-day expiry notifications would be standard maritime practice. Not built.

### With the import pipeline (`import_service.py`)
**Current:** Certs can be imported from CSV. `source = 'imported'`, `import_session_id` is set. The import writes directly to `pms_vessel_certificates` and `pms_crew_certificates` bypassing the action router.
**Ledger gap:** No ledger entry is written for imported certs.

### With `pms_audit_log`
**Current:** All mutation handlers in `certificate_handlers.py` write to `pms_audit_log` directly, in addition to the ledger safety net writing to `ledger_events`. This is double-logging — `pms_audit_log` is the handler-level audit, `ledger_events` is the router-level ledger.
**Why both:** `pms_audit_log` includes `old_values`/`new_values` diffs which `ledger_events` does not currently populate. They serve different purposes.

---

## The `_resolve_cert_domain` function

This is one of the most important utility functions in the domain. It auto-detects which table a certificate belongs to without requiring the caller to specify.

```python
def _resolve_cert_domain(db, yacht_id: str, cert_id: str) -> tuple:
    for domain, table_key in [("vessel", "vessel_certificates"), ("crew", "crew_certificates")]:
        result = db.table(get_table(table_key)).select("*")
                   .eq("yacht_id", yacht_id).eq("id", cert_id)
                   .limit(1).execute()
        rows = getattr(result, "data", None) or []
        if rows:
            return domain, table_key, rows[0]
    raise ValueError(f"Certificate {cert_id} not found or access denied")
```

**Why `.limit(1)` not `.maybe_single()`:** `maybe_single()` in this version of the Supabase Python client returns `None` (the whole response object, not just the data) when no row matches. Accessing `.data` on `None` raises `AttributeError`. `.limit(1)` returns a list response, empty list if no match. This bug was caught by binary tests.

---

## Known bugs found and fixed (2026-04-14)

| Bug | File | Symptom | Fix |
|---|---|---|---|
| `_supersede_certificate_adapter` missing `return _fn` | `handlers/certificate_handlers.py` | supersede always returned 501 "not registered" | Added `return _fn` after inner function definition |
| `maybe_single()` returns `None` response on no-match | `handlers/certificate_handlers.py` | `_resolve_cert_domain` raised `AttributeError: 'NoneType' has no attribute 'data'` | Switched to `.limit(1)` + `getattr(result, "data", None) or []` |
| `_delegate()` didn't pass context | `routes/handlers/certificate_phase4_handler.py` | `supersede_certificate` raised `KeyError: 'certificate_id'` | Added `context` param to `_delegate`, merged into params |
| No `_CERT_ACTIONS` in `resolve_entity_context` | `routes/p0_actions_routes.py` | `entity_id` from EntityLensPage never mapped to `certificate_id` for cert actions | Added `_CERT_ACTIONS` frozenset + mapping |
| REQUIRED_FIELDS check payload-only | `routes/p0_actions_routes.py` | False 400 on supersede (cert_id in context, not payload) | Changed to `{**request.context, **payload}` for the check |
| `pms_notes` had no `certificate_id` column | DB | `add_certificate_note` silently failed — insert threw column-not-found | Added `certificate_id uuid FK → pms_vessel_certificates(id)` |
| `pms_crew_certificates` had no `status` column | DB | Crew cert health was computed-only, never stored | Added `status text NOT NULL DEFAULT 'valid'` with check constraint |
| `pms_crew_certificates` had no `deleted_at`/`deleted_by` | DB | Archive on crew certs failed | Added both columns (no FK on `deleted_by`, matching vessel pattern) |
| 5 cert actions missing from `ACTION_METADATA` | `action_router/ledger_metadata.py` | create_vessel, create_crew, update, link_doc, supersede wrote no ledger events | Added all 5 |
| Read operations wrote no ledger events | `handlers/certificate_handlers.py` | Compliance gap — views were invisible | Added `_ledger_read()` helper, called in all 5 read handlers |
| `maybe_single()` in `link_document_to_certificate` | `handlers/certificate_handlers.py` | Same AttributeError as above | Fixed with `.limit(1)` pattern |

---

## Known limitations

### No chief_engineer test user exists
The test user table claims `captain.tenant@alex-short.com` has role `chief_engineer`. In the TENANT DB (`auth_users_roles`), they actually have role `captain`. There is no test user with `chief_engineer` role in the system. Role gating for chief_engineer is verified only through registry inspection + binary handler tests, not via a real JWT.

### Crew cert `person_name` is free text
No FK to any crew/person record. If someone renames a crew member in the crew system, their certificates remain linked only by name string. Searching by crew member does a `ilike` pattern match on `person_name`.

### Single document per cert
`document_id` is a single FK. If a cert has multiple associated PDFs (e.g., original + renewal letter + survey report), only one can be linked via `document_id`. Additional files go in the Attachments section via `pms_attachments`, which is not searched or filtered.

### No multi-cert supersede chain UI
The `properties.supersedes` and `properties.renews` fields track the chain, but the frontend `Renewal History` section only shows the `pms_audit_log` entries — not a visual chain of cert → superseded → superseded by → new cert.

### Expiry is lazy-evaluated
`refresh_certificate_expiry()` only runs when a list endpoint is called. If nobody views the page, certs past expiry date stay `status='valid'` in the DB indefinitely. There is no background job.

### Import pipeline has no ledger trail
Certs ingested from Seahub CSV or other import sources arrive silently — no `ledger_events` row is written. The `import_session_id` column tracks the batch, but not at ledger level.

### Feature flag dependency
All certificate API routes (`/api/v1/certificates/*`) check `FEATURE_CERTIFICATES=true` env var. If this is not set on Render, every read endpoint returns 404. The action router path (`/v1/actions/execute`) does not check this flag — mutations work regardless. This asymmetry is a known inconsistency.

### No notifications
No 90/30/7-day expiry warnings are sent to any user. No assignment field exists per certificate to know who is responsible for renewal.

### Certificate type case inconsistency
Historical data in `pms_vessel_certificates` has mixed case types: `class`, `CLASS`, `safety`, `SOLAS`. The view normalises to UPPERCASE via `UPPER(certificate_type)`. New inserts should always be uppercase. The handlers do not enforce this on create — only the view normalises on read.

---

## Things I wish I knew at the start

**1. There are three routing layers and they interact in a specific priority order.**
When `/v1/actions/execute` receives a cert action, it hits `p0_actions_routes.py`, which consults the unified `HANDLERS` dict. That dict is assembled in `routes/handlers/__init__.py` with this priority: `CERT_HANDLERS` (certificate_phase4_handler.py) takes precedence over `ADAPTER_HANDLERS` (internal_adapter.py). If a cert action is in `CERT_HANDLERS`, it goes there. If not, it falls through to the adapter which routes to `INTERNAL_HANDLERS` in `internal_dispatcher.py`.

**2. The Phase 4 shim (`certificate_phase4_handler.py`) handles exactly 5 actions.**
All others (renew, archive, suspend, revoke, add_note) go through the adapter path. Adding a new action to the shim when it should go in the dispatcher causes it to work for the Phase 4 path but fail on the action router path. The banner at the top of `certificate_phase4_handler.py` explains this.

**3. `maybe_single()` in this Supabase Python client is broken.**
When no row matches, it returns `None` for the whole response object, not a response object with `data=None`. Any code that does `result = ...maybe_single().execute(); if result.data:` will raise `AttributeError: 'NoneType' object has no attribute 'data'` when the cert is not in that table. Always use `.limit(1)` + `getattr(result, "data", None) or []`.

**4. The frontend queries the view directly, not the API, for the list.**
`FilteredEntityList` uses the Supabase client directly (browser-side, anon key + RLS) to query `v_certificates_enriched`. The detail view goes through the Render API. These are different auth paths. This matters when debugging 404s vs empty lists.

**5. `is_seed = true` hides 338 of 353 vessel cert rows.**
The view filters `WHERE is_seed = false`. If the list is empty, this is usually why. The seed data is there but hidden. Any cert you create via the UI will have `is_seed = false`.

**6. The ledger safety net only fires on mutations via p0_actions_routes.**
Read operations via GET endpoints (`/api/v1/certificates/*`) do not go through the safety net. They write to the ledger only because `_ledger_read()` was explicitly added to each handler. If you add a new read handler, you must also add a `_ledger_read()` call.

**7. `entity_id` from the frontend context is NOT automatically `certificate_id`.**
The EntityLensPage sends `entity_id` in the context. For most domains (fault, work order, equipment) the `resolve_entity_context()` function in `p0_actions_routes.py` maps this to the domain-specific key. For certificates, `_CERT_ACTIONS` frozenset handles this mapping to `certificate_id`. If you add a new cert action and forget to add it to `_CERT_ACTIONS`, the action will fail with MISSING_REQUIRED_FIELD.

**8. `supersede_certificate` requires a complete signature payload.**
Not just `{"signature": {}}` — the router validates that these four keys are present: `signed_at`, `user_id`, `role_at_signing`, `signature_type`. Any test that sends a minimal signature will get 400 from the router, not 403.

**9. The test user roles are NOT what the test table says.**
`captain.tenant@alex-short.com` appears to be `chief_engineer` in documentation but is actually `captain` in the TENANT DB `auth_users_roles` table. The action router resolves role from TENANT DB, not from the MASTER DB `user_accounts` table. Always check `auth_users_roles` directly to know what role a user actually has.

**10. `deleted_by` has no FK constraint on crew certs.**
I added it without a FK initially (matching the vessel cert pattern where `deleted_by` also has no FK). Then I made the mistake of adding `REFERENCES auth.users(id)`. This caused test failures when the synthetic test user UUID didn't exist in `auth.users`. The correct pattern — matching vessel certs — is a plain UUID with no FK constraint.

---

## Running the binary tests

The 16-test binary suite hits the live tenant DB. Each test verifies exact DB row state — no mocks.

```bash
cd /Users/celeste7/Documents/CLOUD_PMS/apps/api

SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co" \
SUPABASE_SERVICE_KEY="<from /Documents/Cloud_PMS/env/env vars.md>" \
MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co" \
MASTER_SUPABASE_JWT_SECRET="<from env vars.md>" \
FEATURE_CERTIFICATES="true" \
python3 tests/cert_binary_tests.py
```

Expected output: `RESULTS: 16/16 PASS | 0/16 FAIL`

The pre-push Docker check also runs these:

```bash
bash scripts/dev/pre-push-check.sh
```

---

## Role permissions quick reference

| Action | crew | chief_engineer | captain | manager |
|---|---|---|---|---|
| View list | ✓ | ✓ | ✓ | ✓ |
| View detail | ✓ | ✓ | ✓ | ✓ |
| View history | ✓ | ✓ | ✓ | ✓ |
| Create vessel cert | ✗ | ✓ | ✓ | ✓ |
| Create crew cert | ✗ | ✓ | ✓ | ✓ |
| Update cert | ✗ | ✓ | ✓ | ✓ |
| Renew cert | ✗ | ✓ | ✓ | ✓ |
| Link document | ✗ | ✓ | ✓ | ✓ |
| Add note | ✗ | ✓ | ✓ | ✓ |
| Supersede (SIGNED) | ✗ | ✗ | ✓ | ✓ |
| Suspend (SIGNED) | ✗ | ✗ | ✓ | ✓ |
| Revoke (SIGNED) | ✗ | ✗ | ✓ | ✓ |
| Archive | ✗ | ✗ | ✓ | ✓ |
| Delete (hard) | ✗ | ✗ | ✗ | ✓ |

SIGNED actions require a signature payload with: `signed_at`, `user_id`, `role_at_signing`, `signature_type`.

---

## Environment variables

All from `/Users/celeste7/Documents/Cloud_PMS/env/env vars.md`

| Variable | Used by | Purpose |
|---|---|---|
| `FEATURE_CERTIFICATES` | Render + Docker | Gates all `/api/v1/certificates/*` GET endpoints. Must be `true`. Does NOT gate mutation endpoints via action router. |
| `SUPABASE_URL` | Render API | Tenant DB URL (`vzsohavtuotocgrfkfyd`) |
| `SUPABASE_SERVICE_KEY` | Render API | Bypasses RLS for service operations |
| `MASTER_SUPABASE_URL` | Render API | Master DB URL (`qvzmkaamzaqxpzbewjxe`) for auth |
| `MASTER_SUPABASE_JWT_SECRET` | Render API | JWT verification |

The frontend (`apps/web`) uses the Supabase anon key + RLS for direct DB queries (the list view). No additional env vars needed for cert reads.

---

## PR history (this domain)

| PR | What | Status |
|---|---|---|
| #522 | Complete cert domain — renew/suspend/revoke/expiry/crew parity, 4 pre-existing bugs fixed, Docker pre-push check | Merged |
| #524 | Cert ledger reads + ACTION_METADATA gaps (opened separately, landed in #525) | Merged via #525 |
| #525 | Full package: cert+ledger+HoR+handover — all domains on one branch | Merged to main 2026-04-14T16:08Z |
