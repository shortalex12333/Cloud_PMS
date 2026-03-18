# Show Related — Backend Deep Dive

> **Audience:** Engineer implementing the "Show Related" UI feature.
> **Scope:** Complete backend analysis — tables, queries, auth, security, V2 path, known gaps.
> **Source files read:** `related_handlers.py` (959 lines), `related_routes.py` (280 lines),
> `embedding_shadow_logger.py` (312 lines), `context_nav/related_expansion.py` (432 lines),
> `workers/embedding_worker_1536.py` (first 80 lines).

---

## 1. Two Implementations Exist — Know Which One Is Active

Before anything else: there are **two parallel related-entity systems** in the codebase. Only one is wired to the live API.

| | Active (V1) | Legacy (context_nav) |
|---|---|---|
| **File** | `handlers/related_handlers.py` | `context_nav/related_expansion.py` |
| **Registered in** | `routes/related_routes.py` | Nowhere active |
| **Link table** | `pms_entity_links` | `user_added_relations` |
| **Table naming** | `pms_work_orders`, `pms_equipment`, `pms_faults` | `work_orders`, `equipment`, `faults` (no prefix) |
| **User relations** | One-directional source→target | Bidirectional (forward + reverse queries) |

The `context_nav/related_expansion.py` file appears to be a prior design pass. It queries tables
without `pms_` prefixes, which likely don't exist in the production schema — and it references
`user_added_relations` instead of `pms_entity_links`. Do not build anything on top of it.
**Everything below refers to the active `related_handlers.py` implementation.**

---

## 2. API Endpoints

### GET `/v1/related`

```
GET /v1/related?entity_type=work_order&entity_id=<uuid>&limit=10
Authorization: Bearer <JWT>
```

**Returns:**
```json
{
  "status": "success",
  "groups": [
    {
      "group_key": "parts",
      "label": "Parts",
      "count": 3,
      "items": [ { "entity_id": "...", "entity_type": "part", "title": "...", ... } ],
      "limit": 10,
      "has_more": false
    }
  ],
  "add_related_enabled": true,
  "group_counts": { "parts": 3, "previous_work": 2 },
  "missing_signals": [],
  "metadata": { "limit_per_group": 10, "total_items": 5 }
}
```

**Roles:** All authenticated crew can call this endpoint. There is no role gate on the GET path.

### POST `/v1/related/add`

```
POST /v1/related/add
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "source_entity_type": "work_order",
  "source_entity_id": "<uuid>",
  "target_entity_type": "fault",
  "target_entity_id": "<uuid>",
  "link_type": "related",
  "note": "Optional note up to 500 chars"
}
```

**Roles:** HOD / chief_engineer / chief_officer / captain / manager only. Crew gets 403.

---

## 3. How the Backend Determines What Is "Related"

### Step-by-step execution of `GET /v1/related`

```
Request arrives with JWT
        ↓
get_authenticated_user() middleware
  → Extracts: user_id, yacht_id, tenant_key_alias from JWT
  → yacht_id NEVER accepted from query params — auth context only
        ↓
get_tenant_client(tenant_key_alias)
  → Creates a Supabase client scoped to the right tenant DB
        ↓
handlers.get_related(yacht_id, user_id, entity_type, entity_id, limit)
        ↓
Step 1: Validate entity_type against VALID_ENTITY_TYPES whitelist
Step 2: Validate limit (1–50)
Step 3: _get_entity_details() — verifies entity exists AND belongs to yacht
  → SELECT from pms_work_orders/pms_equipment/pms_faults where id=entity_id AND yacht_id=yacht_id
  → Returns None if not found → 404
Step 4: Route to entity-type specific FK retrieval:
  - work_order → _get_work_order_relations()
  - equipment  → _get_equipment_relations()
  - fault      → _get_fault_relations()
  - all others → (no FK queries, explicit links only)
Step 5: _get_explicit_links() — always runs, appended as last group
Step 6: _merge_explicit_into_groups() — deduplicate explicit links into FK groups
Step 7: _is_hod_or_manager() → sets add_related_enabled in response
Step 8: Shadow logging (if SHOW_RELATED_SHADOW=true)
Step 9: Return grouped response
```

---

## 4. FK Query Map — What Gets Fetched For Each Entity Type

### Work Order → 4 FK groups

| Group key | Table | Join condition | Sort | Filter |
|-----------|-------|----------------|------|--------|
| `parts` | `pms_work_order_parts` → nested `pms_parts` | `work_order_id = entity_id` | `created_at DESC` | `deleted_at IS NULL` |
| `manuals` | `doc_metadata` | `equipment_ids @> [equipment_id]` via RPC or contains() | `updated_at DESC` | `doc_type='manual'`, `deleted_at IS NULL` |
| `previous_work` | `pms_work_orders` | `equipment_id = focused.equipment_id AND id != entity_id` | `last_activity_at DESC NULLS LAST` | `deleted_at IS NULL` |
| `attachments` | `pms_attachments` | `entity_type='work_order' AND entity_id = entity_id` | `uploaded_at DESC` | `deleted_at IS NULL` |

**Prerequisite:** Groups 2 and 3 only run if `focused.equipment_id` is non-null. If the work order has no equipment linked, those groups are omitted and `"no_equipment_linked"` is added to `missing_signals`.

**Hardcoded omission:** `"handover_group_omitted_v1"` is always appended to `missing_signals` for work orders — handover relationships are deferred to V2.

### Equipment → 2 FK groups

| Group key | Table | Join condition |
|-----------|-------|----------------|
| `faults` | `pms_faults` | `equipment_id = entity_id` |
| `work_orders` | `pms_work_orders` | `equipment_id = entity_id` |

### Fault → 2 FK groups

| Group key | Table | Join condition |
|-----------|-------|----------------|
| `equipment` | `pms_equipment` | `id = focused.equipment_id` (single row) |
| `work_orders` | `pms_work_orders` | `fault_id = entity_id` |

**Prerequisite:** The `equipment` group only runs if `focused.equipment_id` is non-null.

### Part, Manual, Attachment, Handover

No FK traversal implemented. Only explicit links from `pms_entity_links` are returned.

---

## 5. Explicit Links (`pms_entity_links` table)

After FK groups are built, explicit links are always fetched and merged in.

**Schema (inferred from handler queries):**
```sql
pms_entity_links (
  id                   UUID PRIMARY KEY,
  yacht_id             UUID NOT NULL,         -- tenant isolation
  source_entity_type   TEXT NOT NULL,
  source_entity_id     UUID NOT NULL,
  target_entity_type   TEXT NOT NULL,
  target_entity_id     UUID NOT NULL,
  link_type            TEXT NOT NULL,         -- 'related','reference','evidence','manual'
  note                 TEXT,                  -- max 500 chars
  created_by           UUID NOT NULL,         -- user_id of creator
  created_at           TIMESTAMPTZ
)
-- NOTE: NO deleted_at column. Deletion is hard delete only.
```

**How they're merged:** After all FK groups are built, explicit links for the same entity
are merged into the matching FK group (deduplicated by `entity_id`). When deduped, the
`match_reasons` arrays are unioned. Items that don't match any FK group remain in a
separate `"explicit_links"` / `"Linked by Crew"` group.

**Merge logic gap:** The `_type_matches_group()` mapping routes `"work_order"` to
`"previous_work"` — so an explicitly linked work order merges into the `previous_work` group.
If someone links a work order that isn't on the same equipment, it will still appear in
`previous_work`, which has the label "Previous Work Orders." This label will be misleading
for cross-equipment explicit links.

---

## 6. Soft Delete Handling

This is explicitly documented in the handler and matters for correctness:

| Table | Has `deleted_at` | Filter applied |
|-------|-----------------|----------------|
| `pms_work_orders` | ✅ | `.is_("deleted_at", "null")` |
| `pms_equipment` | ✅ | `.is_("deleted_at", "null")` |
| `pms_faults` | ✅ | `.is_("deleted_at", "null")` |
| `pms_parts` | ✅ | `.is_("deleted_at", "null")` |
| `pms_work_order_parts` | ✅ | `.is_("deleted_at", "null")` |
| `pms_attachments` | ✅ | `.is_("deleted_at", "null")` |
| `doc_metadata` | ✅ | Applied via RPC or fallback query |
| `pms_entity_links` | ❌ | Hard delete only, no filter needed |
| `handover_exports` | ❌ | No filter needed |

---

## 7. Item Weight / Ordering

Each item in every group has a `weight` field. Within a group, items are ordered by the
database query (usually `created_at DESC` or `last_activity_at DESC`). The `weight` field
indicates the confidence tier of the relationship signal:

| Weight | Source |
|--------|--------|
| 100 | Direct FK match (part on this WO, attachment on this WO, equipment for this fault) |
| 90 | One-hop FK (manuals via equipment, faults on this equipment) |
| 80 | Two-hop / lateral FK (previous WOs on same equipment) |
| 70 | Explicit manual link from `pms_entity_links` |

In V1, `weight` is assigned statically and does not affect ordering — the database sort
order is what determines item order. In V2, weight will be blended with cosine similarity
score via the `alpha` parameter.

---

## 8. Security Model

### Authentication

Every request goes through `get_authenticated_user()` FastAPI dependency.
This middleware:
- Validates the JWT signature
- Extracts `user_id`, `yacht_id`, `tenant_key_alias` from token claims
- Returns an `auth` dict injected into the route handler

**Critical invariant #1 (explicitly coded):** `yacht_id` is NEVER accepted from the
client payload. It is always and only read from the server-resolved auth context.
The comment is in `related_routes.py:59` and `related_routes.py:226-227`.

### Multi-Tenancy

`get_tenant_client(auth['tenant_key_alias'])` creates a Supabase client for the correct
tenant database. All queries then run inside that tenant's schema. Every query additionally
filters `WHERE yacht_id = auth['yacht_id']` — this is a double boundary: wrong tenant DB
won't have the yacht at all, but even within a tenant, cross-yacht access is blocked by
the explicit `yacht_id` filter.

### Role-Based Access Control

The system has two RBAC layers for related entities:

**Layer 1 — Viewing:** No role gate. All authenticated crew (`role = any`) can call
`GET /v1/related`. The `add_related_enabled` field in the response tells the UI whether
to show the "Link Related" button.

**Layer 2 — Mutating links:** `POST /v1/related/add` requires HOD-tier roles.
The check happens in two places:
1. Application-level: `_is_hod_or_manager()` queries `auth_users_roles` table:
   ```python
   role in ["chief_engineer", "chief_officer", "captain", "manager", "hod"]
   ```
2. Database-level: The route's error handler also catches RLS policy violations
   (string-matching `"policy"` / `"permission"` / `"rls"` in the exception) and
   returns 403 — so even if the application check is bypassed, the DB will block it.

**The role check uses the database, not the JWT.** The `auth_users_roles` table is
queried live at request time. This means role changes take effect immediately — there is
no stale JWT window for permissions.

### Audit Trail

Every `add_related` call writes to `pms_audit_log`:
```python
{
  "action": "add_entity_link",
  "entity_type": "entity_link",
  "entity_id": link["id"],
  "user_id": user_id,
  "yacht_id": yacht_id,
  "new_values": { "source": "work_order:<id>", "target": "fault:<id>", "link_type": "related" },
  "signature": {},   # Non-signed action (invariant)
  "metadata": { "source": "lens", "lens": "work_orders" }
}
```

Audit log failure is non-fatal — it logs a warning but does not roll back the link creation.

---

## 9. The `search_index` Table and Embedding Infrastructure

The embedding worker (`workers/embedding_worker_1536.py`) is a separate background process.
It is completely decoupled from the related entity query path in V1.

**How it works:**
1. Something enqueues a job in the `embedding_jobs` table (queue-driven, not explored in full)
2. The worker claims jobs from `embedding_jobs`
3. For each job, it fetches `search_text` from the `search_index` table
4. Calls OpenAI `text-embedding-3-small` API to get a 1536-dimensional float vector
5. Writes the vector to `search_index.embedding_1536` column (pgvector)
6. Updates `embedding_jobs` status to `done` or `failed`

The worker uses a **circuit breaker** (5 consecutive failures → pause 60s) and a **dead-letter queue** pattern (max 3 retries before marking `failed`). It connects via Supavisor (port 6543) for connection pooling.

**In V1, embeddings play no role in related entity ranking.** The shadow logger checks if
`focused.get("embedding")` is set, but `_get_entity_details()` never SELECTs the `embedding`
column — so `focused_embedding` is always `None` in production, and the shadow logger
exits immediately with "No focused embedding."

**For V2** (vector reranking), the plan is:
- Blend FK weight with cosine similarity via: `final_score = fk_weight + (alpha * 100 * cosine)`
- Alpha starts at 0.0 (V1 current) and increases as validation builds confidence
- The shadow logger simulates what ordering would look like at alpha=0.1, 0.3, 0.5, 1.0
- `SHOW_RELATED_SHADOW=true` enables logging without affecting production ordering

---

## 10. `related_text` Field

Several queries select a `related_text` column:
```python
self.db.table("pms_parts").select("id, name, part_number, related_text")
self.db.table("pms_work_orders").select("..., related_text, ...")
self.db.table("pms_faults").select("..., related_text, ...")
self.db.table("pms_attachments").select("..., related_text, ...")
```

The handler docstring mentions: *"related_text for explainability (populated by V1 migration)."*
This is a denormalized text column on each entity table, likely a summary used for
embedding generation. In V1, the UI receives it as part of each result item but it is
currently just stored — not processed or displayed by the existing handler.

---

## 11. Known Gaps and Incomplete Areas

These are genuine holes — either bugs, incomplete implementations, or design decisions
that will require attention.

---

### GAP-01: `link_type` default is invalid (BUG)

**Location:** `routes/related_routes.py:65`
```python
link_type: str = Field(default="explicit", description="Link type")
```

**Location:** `handlers/related_handlers.py:36`
```python
VALID_LINK_TYPES = ["related", "reference", "evidence", "manual"]
```

`"explicit"` is not in `VALID_LINK_TYPES`. If a client POSTs without specifying `link_type`,
it defaults to `"explicit"`, which the handler rejects with a 400. The route docstring lists
a different set of link types (`caused_by`, `resolved_by`, `supersedes`, `warranty_for`)
that are also not in `VALID_LINK_TYPES`.

**The route schema and the handler validation are out of sync.** One source of truth needs
to win. Until this is fixed, any client that uses the default `link_type` will receive a 400.

---

### GAP-02: `part`, `manual`, `attachment`, `handover` have no FK traversal

**Location:** `handlers/related_handlers.py:122-124`
```python
else:
    # Generic: just get explicit links
    pass
```

If `entity_type` is `"part"`, `"manual"`, `"attachment"`, or `"handover"`, the handler
skips all FK queries and returns only whatever is in `pms_entity_links`. For an inventory
part, you get no related work orders, no equipment — just manually curated links.

The feature is described as "all site" — meaning every lens gets the button. But without
FK traversal for parts, the panel will be empty unless crew have manually linked things.

---

### GAP-03: Manual-to-equipment FK path uses fragile `contains()` plus RPC fallback

**Location:** `handlers/related_handlers.py:253-267`
```python
result = self.db.rpc("get_equipment_manuals", {...}).execute()
if not result.data:
    result = self.db.table("doc_metadata").select("id, filename, updated_at") \
        .contains("equipment_ids", [equipment_id]) \
        .eq("doc_type", "manual") ...
```

The handler first calls an RPC `get_equipment_manuals` and, **if it returns empty data**,
falls through to a direct `contains()` query on a JSONB array column `equipment_ids`.

Two problems:
1. The RPC fallback logic triggers on empty results, not just on failure. If the RPC exists
   but genuinely returns no manuals, the fallback query runs unnecessarily.
2. If the RPC does not exist in the tenant DB, the `execute()` call will raise an exception
   that's caught by the outer `try/except`, silently omitting the manuals group entirely.

Whether `get_equipment_manuals` RPC exists in production is not visible from code alone.

---

### GAP-04: Shadow logger always receives `None` for focused embedding

**Location:** `handlers/related_handlers.py:146`
```python
focused_embedding = focused.get("embedding") if isinstance(focused, dict) else None
shadow_log_rerank_scores(..., focused_embedding=focused_embedding, ...)
```

**Location:** `handlers/related_handlers.py:648-698` (`_get_entity_details`)
```python
# Work order query:
result = self.db.table("pms_work_orders").select(
    "id, wo_number, title, equipment_id, fault_id, status"   # ← no embedding column
)
```

`_get_entity_details()` never fetches the embedding. `focused_embedding` is always `None`.
The shadow logger exits immediately with:
```
[SHADOW] No focused embedding for work_order:<id>...
```

Shadow logging is currently a no-op for all entity types. Enabling `SHOW_RELATED_SHADOW=true`
in production adds log overhead for zero data value until this is fixed.

---

### GAP-05: Explicit link merge uses misleading group label for cross-equipment WOs

**Location:** `handlers/related_handlers.py:631-641`
```python
def _type_matches_group(self, entity_type: str, group_key: str) -> bool:
    mapping = {
        "work_order": "previous_work",   # ← always maps to "Previous Work Orders"
        ...
    }
```

If a HOD manually links `work_order A → work_order B` (different equipment), and the user
views A's related panel, work_order B will appear inside the "Previous Work Orders" group
(merged by the explicit link). The label is wrong — it implies same-equipment history.

The fix is to not merge explicit `work_order` links into `previous_work` when they don't
share `equipment_id`, and instead leave them in `"Linked by Crew"`.

---

### GAP-06: `pms_entity_links` lookup is one-directional

**Location:** `handlers/related_handlers.py:548-554`
```python
result = self.db.table("pms_entity_links").select(...) \
    .eq("source_entity_type", entity_type) \
    .eq("source_entity_id", entity_id) ...
```

Only queries where the entity is the **source**. If entity B was linked as the **target** of
an explicit link from entity A, viewing entity B's related panel will not show entity A.

The older `context_nav/related_expansion.py` implementation queried both directions
(forward + reverse). The active V1 implementation dropped bidirectionality. Users who
link "A relates to B" will not see the relationship when viewing B.

---

### GAP-07: `auth_users_roles` table — role field not cross-referenced with JWT role

The role check queries the live database:
```python
result = self.db.table("auth_users_roles").select("role") \
    .eq("user_id", user_id).eq("yacht_id", yacht_id).eq("is_active", True)
```

This is correct — it's always fresh. But the `_is_hod_or_manager()` method's allowed roles list
(`["chief_engineer", "chief_officer", "captain", "manager", "hod"]`) needs to stay in sync
with how roles are defined in the broader auth system. If a new role is added (e.g., `"first_officer"`),
it requires a code change here — it's a hardcoded list with no single source of truth.

---

### GAP-08: `handover_exports` as link target but no `/v1/related` support for it

`handover` is in `VALID_ENTITY_TYPES` (can be a link target) and in `_entity_exists()`
table map. But `get_related()` has no FK traversal for `entity_type="handover"` — only
explicit links return. This is likely intentional (V1 scope) but not documented as such.

---

## 12. V2 Upgrade Path

The system is designed for a clean V2 upgrade without breaking V1.

**V1 (current):** FK-only ordering. Alpha=0.0. Items ordered by DB sort (recency).

**V2 (planned):**
1. Add `embedding` to `_get_entity_details()` SELECT — fetch focused entity's vector
2. Query each related item's embedding from `search_index` (join by entity_id)
3. Compute cosine similarity between focused embedding and each item's embedding
4. Apply: `final_score = fk_weight + (alpha * 100 * cosine)`
5. Increase alpha from 0.0 toward 1.0 as shadow data validates the improvement

**Shadow data readiness:** The `embedding_shadow_logger.py` infrastructure is fully built.
The only missing piece is fetching embeddings in the query path (GAP-04 above).

---

## 13. Summary: All Tables Touched

| Table | Purpose | Write? |
|-------|---------|--------|
| `pms_work_orders` | Work order FK traversal, previous work | ❌ Read only |
| `pms_equipment` | Equipment FK traversal | ❌ Read only |
| `pms_faults` | Fault FK traversal | ❌ Read only |
| `pms_parts` | Part lookup via WO → parts join | ❌ Read only |
| `pms_work_order_parts` | Junction: which parts are on a WO | ❌ Read only |
| `pms_attachments` | Documents attached to a WO | ❌ Read only |
| `doc_metadata` | Manuals linked to equipment | ❌ Read only |
| `pms_entity_links` | Explicit crew-created links | ✅ Written by POST /add |
| `auth_users_roles` | Role check for add_related permission | ❌ Read only |
| `pms_audit_log` | Audit trail for link creation | ✅ Written by POST /add |
| `search_index` | Embedding store (V2 only) | ❌ Read only (by related) |
| `embedding_jobs` | Embedding queue (worker only) | ❌ Not touched by related |
| `handover_exports` | Handover entity existence check | ❌ Read only |

---

## 14. Quick Reference for the Engineer

**Active API endpoint:** `GET /v1/related?entity_type=<type>&entity_id=<uuid>&limit=10`

**Supported entity types with FK traversal:** `work_order`, `equipment`, `fault`

**Supported entity types (explicit links only):** `part`, `manual`, `attachment`, `handover`

**Who can view:** All authenticated crew

**Who can add links:** `chief_engineer`, `chief_officer`, `captain`, `manager`, `hod`

**Valid link types (from handler — use these, not the route docstring):** `related`, `reference`, `evidence`, `manual`

**DO NOT use:** `context_nav/related_expansion.py` — legacy, wrong table names, not wired

**First bug to fix before shipping the UI:** GAP-01 (`link_type` default `"explicit"` is invalid)
