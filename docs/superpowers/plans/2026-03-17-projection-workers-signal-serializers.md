# Projection Workers + Signal Serializer Completeness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get projection + embedding workers running locally against the real Supabase DB, verify `search_index` is populated with proof, add missing entity serializers for lenses not yet covered, and run the full show-related-signal test suite to 14 passed / 0 skipped.

**Architecture:**
The pipeline is two separate workers with two separate queues. Postgres triggers fire on `INSERT`/`UPDATE` into `pms_*` tables → insert a row into `search_index` with `embedding_status='pending'` AND a job into `embedding_jobs` with `status='queued'`. The **projection worker** claims `search_index WHERE embedding_status IN ('pending','processing')`, reads column mappings from the `search_projection_map` DB table, fetches the source row, builds `search_text`/`filters`/`payload`, and marks `embedding_status='indexed'`. The **embedding worker** then claims from `embedding_jobs`, reads `search_text` from `search_index`, calls OpenAI `text-embedding-3-small`, and writes `embedding_1536` back. Both workers must run to complete the pipeline.

**Tech Stack:** Python 3.11, psycopg2, Docker Compose, OpenAI API, PostgreSQL/Supabase, Playwright/TypeScript

---

## Chunk 1: Operational — Launch Workers + Verify DB

### Task 1: Pre-flight checks (no Docker yet)

**Files:** none — diagnostic only

- [ ] **Step 1.1: Verify OPENAI_API_KEY is set in shell**

```bash
echo "OPENAI_API_KEY starts with: ${OPENAI_API_KEY:0:8}"
```
Expected: `sk-proj-` or similar. If empty → export before continuing.

- [ ] **Step 1.2: Check the search_projection_map table exists and has rows**

Run in Supabase SQL editor (or psql with the direct connection):
```sql
SELECT COUNT(*) FROM search_projection_map WHERE enabled = true;
```
Expected: ≥ 10 rows (one per domain). If 0 or table doesn't exist → see Task 2 (backfill).

- [ ] **Step 1.3: Check embedding_jobs table exists**

```sql
SELECT COUNT(*) FROM embedding_jobs WHERE status = 'queued';
```
Expected: some queued jobs. If table doesn't exist → the trigger isn't writing there;
embedding worker will starve (note in observations, continue with projection worker only).

- [ ] **Step 1.4: Check current search_index state for test yacht**

```sql
SELECT embedding_status, COUNT(*)
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY embedding_status
ORDER BY COUNT(*) DESC;
```
Record the counts — this is your baseline before running workers.

---

### Task 2: Backfill search_projection_map (if empty)

**Context:** The projection_worker reads column mappings from `search_projection_map`.
If this table is empty the worker runs silently but builds no search_text — entities end up with `embedding_status='indexed'` but empty/null `search_text`, making them unsearchable.

**Files:** none — SQL only

- [ ] **Step 2.1: Check if table is empty**

```sql
SELECT domain, object_type FROM search_projection_map LIMIT 5;
```

If empty → run Step 2.2. If populated → skip Task 2.

- [ ] **Step 2.2: Verify what the worker would do with empty mappings**

Look at projection_worker.py `process_item()` lines 722–784:
```
if not mapping:
    # No mapping but item exists - proceed with embedding
    return True, ""   ← THIS IS THE SILENT FAILURE
```
Empty MAPPINGS dict means process_item returns True for everything without updating search_text.
The item gets marked 'indexed' but search_text remains NULL → embedding worker embeds empty string.

- [ ] **Step 2.3: If table is empty, seed it from projection.yaml**

The `projection.yaml` contains the authoritative column specs. The simplest fix is to seed
`search_projection_map` directly. Run this SQL (adjust as needed based on exact schema):

```sql
-- Check table schema first
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'search_projection_map';
```

Then insert rows matching projection.yaml. The key columns are:
`domain`, `source_table`, `object_type`, `search_text_cols`, `filter_map`, `payload_map`, `enabled`

**NOTE:** If the table schema doesn't match what's expected, the projection worker
will fail on `load_mappings()` with a ProgrammingError. This is the most likely first error.
Fix by seeding the table with rows from projection.yaml.

- [ ] **Step 2.4: Verify mappings loaded**

```sql
SELECT domain, source_table, object_type FROM search_projection_map WHERE enabled = true ORDER BY domain;
```
Expected: ≥ 10 rows across work_orders, faults, equipment, parts, etc.

---

### Task 3: Queue backfill (seed pending rows for test entities)

**Context:** Entities created after the projector was removed from Render may exist in
pms_* tables but have NO row in `search_index` at all (trigger never fired, or trigger
was added after the entity was created). Force-queue them before starting the worker.

**Files:** none — SQL only

- [ ] **Step 3.1: Backfill search_index for all test yacht entity types**

```sql
-- Work orders
INSERT INTO search_index (object_type, object_id, yacht_id, embedding_status)
SELECT 'work_order', id, yacht_id, 'pending'
FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET embedding_status = 'pending';

-- Faults
INSERT INTO search_index (object_type, object_id, yacht_id, embedding_status)
SELECT 'fault', id, yacht_id, 'pending'
FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET embedding_status = 'pending';

-- Equipment
INSERT INTO search_index (object_type, object_id, yacht_id, embedding_status)
SELECT 'equipment', id, yacht_id, 'pending'
FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET embedding_status = 'pending';

-- Parts
INSERT INTO search_index (object_type, object_id, yacht_id, embedding_status)
SELECT 'part', id, yacht_id, 'pending'
FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET embedding_status = 'pending';

-- Certificates
INSERT INTO search_index (object_type, object_id, yacht_id, embedding_status)
SELECT 'certificate', id, yacht_id, 'pending'
FROM pms_vessel_certificates
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ON CONFLICT (object_type, object_id) DO UPDATE SET embedding_status = 'pending';
```

- [ ] **Step 3.2: Verify queue depth**

```sql
SELECT embedding_status, COUNT(*)
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY embedding_status;
```
Expected: significant number of 'pending' rows.

- [ ] **Step 3.3: Backfill embedding_jobs if table exists**

If embedding_jobs table exists but is empty for recently-created entities:
```sql
-- Only queue items that have search_text but no current embedding job
INSERT INTO embedding_jobs (object_type, object_id, yacht_id, status, priority)
SELECT si.object_type, si.object_id::text, si.yacht_id, 'queued', 5
FROM search_index si
LEFT JOIN embedding_jobs ej
  ON ej.object_type = si.object_type AND ej.object_id = si.object_id::text
WHERE si.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND si.search_text IS NOT NULL
  AND si.search_text != ''
  AND si.embedding_1536 IS NULL
  AND ej.id IS NULL
ON CONFLICT DO NOTHING;
```

---

### Task 4: Launch Docker workers

**Files:** `docker-compose.f1-workers.yml` — no code changes; run only

- [ ] **Step 4.1: Export required env vars**

```bash
export OPENAI_API_KEY="sk-proj-..."   # your key
# These are already hardcoded in docker-compose (check file lines 85, 110)
# PROJECTION_WORKER uses port 6543 (Supavisor) ← correct for psycopg2
# EMBEDDING_WORKER uses port 6543 ← correct
```

- [ ] **Step 4.2: Build and launch workers**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
docker-compose -f docker-compose.f1-workers.yml up --build projection-worker embedding-worker 2>&1 | tee /tmp/worker-launch.log
```

Expected startup lines from projection-worker:
```
[INFO] Loading mappings...
[INFO] Loaded N domain mappings: ['pms_work_orders', 'pms_faults', ...]
[INFO] Starting worker loop...
[INFO] Processing N items...
```

Expected startup lines from embedding-worker:
```
[INFO] Embedding worker 1536 starting
[INFO] Search index stats: total=N, with_1536=M, needs=K
[INFO] Claiming N jobs from queue...
```

- [ ] **Step 4.3: Watch for errors and diagnose**

Common errors and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| `ProgrammingError: relation "search_projection_map" does not exist` | Table missing from DB | Create table (check supabase migrations) |
| `OperationalError: could not connect` | Wrong DB URL / password | Check DATABASE_URL in docker-compose |
| `load_mappings: Loaded 0 domain mappings` | Table empty | Run Task 2.3 seed SQL |
| `OPENAI_API_KEY not set` | Env var not passed | `export OPENAI_API_KEY=...` in shell before docker-compose |
| `ModuleNotFoundError: yaml` | Missing dep in Docker | Check Dockerfile / requirements |
| `embedding_status = 'indexed'` but search_text NULL | Mappings empty | Seed search_projection_map |

- [ ] **Step 4.4: Let projection worker run for 2-3 minutes**

Watch logs for: `Batch complete. Total: N done, 0 failed.`

Let it process at least one full batch before checking DB.

- [ ] **Step 4.5: Watch for payload source_table issue**

The projector looks up mapping via `payload->>'source_table'` (line 729).
If search_index rows were inserted by the backfill SQL in Task 3 (not by trigger),
the `payload` column will be NULL → `source_table` returns None → projector
falls back to searching MAPPINGS by object_type (lines 737-741).

This fallback works IF MAPPINGS has an entry with matching object_type. Verify:
```sql
SELECT payload->>'source_table' AS src, object_type, COUNT(*)
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND embedding_status = 'pending'
GROUP BY 1, 2 LIMIT 20;
```
If `source_table` is NULL for most rows, the projector will use the object_type fallback.
This is fine as long as MAPPINGS has entries for each object_type.

---

### Task 5: Proof — verify DB state after workers run

- [ ] **Step 5.1: Check indexed row count (primary proof)**

```sql
SELECT embedding_status, COUNT(*)
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY embedding_status;
```
**Expected: 'indexed' count > 0, 'pending' count shrinking.**

- [ ] **Step 5.2: Verify search_text is populated (not null)**

```sql
SELECT object_type, COUNT(*),
       COUNT(search_text) AS has_text,
       COUNT(embedding_1536) AS has_vector
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY object_type
ORDER BY object_type;
```
**This is the critical proof.** If `has_text = 0` for any type → search_projection_map missing that mapping.
If `has_vector = 0` → embedding worker hasn't run yet (wait for embedding_jobs to drain).

- [ ] **Step 5.3: Spot-check a work_order row**

```sql
SELECT object_type, object_id, embedding_status,
       LEFT(search_text, 200) AS search_text_preview,
       (embedding_1536 IS NOT NULL) AS has_vector
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND object_type = 'work_order'
  AND embedding_status = 'indexed'
LIMIT 3;
```
Expected: `search_text_preview` contains WO title text; `has_vector = true`.

---

## Chunk 2: Code — Add Missing Entity Serializers + Fix E2E Test

### Task 6: Add missing asyncpg serializers to entity_serializer.py

**File:** `apps/api/services/entity_serializer.py`

**Context:** The signal endpoint (`GET /v1/show-related-signal?entity_type=certificate&...`)
returns 400 for any type not in `_SERIALIZERS`. Lenses in search_index that can appear
as signal results should also be queryable as sources. Currently missing:
`certificate`, `receiving`, `handover_item`, `shopping_item`, `warranty_claim`, `purchase_order`, `supplier`, `email`.

The asyncpg path is used when `READ_DB_DSN` is set (production + local Docker API).

- [ ] **Step 6.1: Add certificate serializer**

In `apps/api/services/entity_serializer.py`, after `_serialize_handover`, add:

```python
async def _serialize_certificate(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT certificate_name, certificate_number, certificate_type,
               issuing_authority, status
        FROM pms_vessel_certificates
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [row["certificate_name"] or "Certificate"]
    if row["certificate_type"]:
        parts.append(f"type: {row['certificate_type']}")
    if row["issuing_authority"]:
        parts.append(f"authority: {row['issuing_authority']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["certificate_number"]:
        parts.append(f"number: {row['certificate_number']}")
    return "; ".join(parts)


async def _serialize_receiving(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT vendor_name, vendor_reference, notes, status, received_date
        FROM pms_receiving
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [f"Receiving from {row['vendor_name']}" if row.get("vendor_name") else "Receiving"]
    if row["vendor_reference"]:
        parts.append(f"ref: {row['vendor_reference']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["notes"]:
        parts.append(str(row["notes"])[:200])
    return "; ".join(parts)


async def _serialize_handover_item(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT summary, entity_type, section, category, action_summary, status
        FROM handover_items
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [row["summary"] or "Handover item"]
    if row["entity_type"]:
        parts.append(f"type: {row['entity_type']}")
    if row["section"]:
        parts.append(f"section: {row['section']}")
    if row["category"]:
        parts.append(f"category: {row['category']}")
    if row["action_summary"]:
        parts.append(str(row["action_summary"])[:200])
    return "; ".join(parts)


async def _serialize_shopping_item(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT part_name, part_number, manufacturer, source_notes, status, urgency
        FROM pms_shopping_list_items
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [row["part_name"] or "Shopping item"]
    if row["part_number"]:
        parts.append(f"part_number: {row['part_number']}")
    if row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    if row["urgency"]:
        parts.append(f"urgency: {row['urgency']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    return "; ".join(parts)


async def _serialize_email(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT subject, preview_text, from_display_name, folder
        FROM email_messages
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [row["subject"] or "Email"]
    if row["from_display_name"]:
        parts.append(f"from: {row['from_display_name']}")
    if row["folder"]:
        parts.append(f"folder: {row['folder']}")
    if row["preview_text"]:
        parts.append(str(row["preview_text"])[:200])
    return "; ".join(parts)
```

- [ ] **Step 6.2: Register the new serializers in `_SERIALIZERS` dict**

Replace the existing `_SERIALIZERS` dict at the bottom of `entity_serializer.py`:

```python
_SERIALIZERS: Dict[str, Callable] = {
    "work_order": _serialize_work_order,
    "fault": _serialize_fault,
    "equipment": _serialize_equipment,
    "part": _serialize_part,
    "inventory": _serialize_part,       # alias — same table as part
    "manual": _serialize_manual,
    "document": _serialize_manual,      # alias
    "handover": _serialize_handover,    # queries handover_exports
    "handover_export": _serialize_handover,  # explicit alias
    "certificate": _serialize_certificate,
    "receiving": _serialize_receiving,
    "handover_item": _serialize_handover_item,
    "shopping_item": _serialize_shopping_item,
    "email": _serialize_email,
}
```

- [ ] **Step 6.3: Verify file compiles (syntax check)**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -m py_compile services/entity_serializer.py && echo "OK"
```
Expected: `OK` with no output errors.

---

### Task 7: Add matching Supabase fallback serializers

**File:** `apps/api/handlers/show_related_signal_handlers.py`
**Function:** `_serialize_entity_supabase_sync()`

The Supabase fallback path is used when `READ_DB_DSN` is not set. It must mirror the asyncpg serializers exactly or the two paths will diverge.

- [ ] **Step 7.1: Add certificate case**

In `_serialize_entity_supabase_sync()`, after the `elif entity_type == "handover":` block
and before the final `else: return None`, add:

```python
        elif entity_type == "certificate":
            r = supabase.table("pms_vessel_certificates").select(
                "certificate_name, certificate_number, certificate_type, issuing_authority, status"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row["certificate_name"] or "Certificate"]
            if row.get("certificate_type"):
                parts.append(f"type: {row['certificate_type']}")
            if row.get("issuing_authority"):
                parts.append(f"authority: {row['issuing_authority']}")
            if row.get("status"):
                parts.append(f"status: {row['status']}")
            if row.get("certificate_number"):
                parts.append(f"number: {row['certificate_number']}")
            return "; ".join(parts) if parts else None

        elif entity_type == "receiving":
            r = supabase.table("pms_receiving").select(
                "vendor_name, vendor_reference, notes, status"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [f"Receiving from {row['vendor_name']}" if row.get("vendor_name") else "Receiving"]
            if row.get("vendor_reference"):
                parts.append(f"ref: {row['vendor_reference']}")
            if row.get("status"):
                parts.append(f"status: {row['status']}")
            if row.get("notes"):
                parts.append(str(row["notes"])[:200])
            return "; ".join(parts) if parts else None

        elif entity_type == "handover_item":
            r = supabase.table("handover_items").select(
                "summary, entity_type, section, category, action_summary, status"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row.get("summary") or "Handover item"]
            if row.get("entity_type"):
                parts.append(f"type: {row['entity_type']}")
            if row.get("section"):
                parts.append(f"section: {row['section']}")
            if row.get("category"):
                parts.append(f"category: {row['category']}")
            if row.get("action_summary"):
                parts.append(str(row["action_summary"])[:200])
            return "; ".join(parts) if parts else None

        elif entity_type == "handover_export":
            # Explicit alias for 'handover' — same table, same query
            r = supabase.table("handover_exports").select(
                "title, content"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row.get("title") or "Handover"]
            if row.get("content"):
                parts.append(str(row["content"])[:300])
            return "; ".join(parts) if parts else None

        elif entity_type == "shopping_item":
            r = supabase.table("pms_shopping_list_items").select(
                "part_name, part_number, manufacturer, source_notes, status, urgency"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row.get("part_name") or "Shopping item"]
            if row.get("part_number"):
                parts.append(f"part_number: {row['part_number']}")
            if row.get("manufacturer"):
                parts.append(f"manufacturer: {row['manufacturer']}")
            if row.get("urgency"):
                parts.append(f"urgency: {row['urgency']}")
            if row.get("status"):
                parts.append(f"status: {row['status']}")
            return "; ".join(parts) if parts else None

        elif entity_type == "email":
            r = supabase.table("email_messages").select(
                "subject, preview_text, from_display_name, folder"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row.get("subject") or "Email"]
            if row.get("from_display_name"):
                parts.append(f"from: {row['from_display_name']}")
            if row.get("folder"):
                parts.append(f"folder: {row['folder']}")
            if row.get("preview_text"):
                parts.append(str(row["preview_text"])[:200])
            return "; ".join(parts) if parts else None
```

- [ ] **Step 7.2: Verify file compiles**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -m py_compile handlers/show_related_signal_handlers.py && echo "OK"
```

---

### Task 8: Expand VALID_ENTITY_TYPES in E2E test

**File:** `apps/web/e2e/shard-34-lens-actions/show-related-signal.spec.ts`

**Context:** The item quality test asserts that every result's `entity_type` is in
`VALID_ENTITY_TYPES`. Now that the projector will index certificates, emails,
shopping items, etc., those types can appear in results. The test must accept them.

- [ ] **Step 8.1: Expand the set**

Replace:
```typescript
const VALID_ENTITY_TYPES = new Set([
  'work_order', 'fault', 'equipment', 'part', 'inventory',
  'manual', 'document', 'handover',
]);
```

With:
```typescript
// All entity types that appear in search_index (from projection.yaml mapping)
// Kept in sync with apps/api/services/entity_serializer.py _SERIALIZERS keys.
const VALID_ENTITY_TYPES = new Set([
  'work_order', 'fault', 'equipment', 'part', 'inventory',
  'manual', 'document', 'handover', 'handover_export',
  'certificate', 'receiving', 'handover_item',
  'shopping_item', 'email',
  // Less common but valid from projector
  'work_order_note', 'note', 'warranty_claim', 'purchase_order', 'supplier',
]);
```

- [ ] **Step 8.2: Verify TypeScript compiles**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web
npx tsc --noEmit --skipLibCheck 2>&1 | head -20
```
Expected: no errors for the changed file.

---

### Task 9: Update _map_to_related_item for new types (if not already handled)

**File:** `apps/api/handlers/show_related_signal_handlers.py`
**Function:** `_map_to_related_item()`

**Context:** `_map_to_related_item` maps raw search_index results to RelatedItem shape.
Check if `receiving`, `handover_item`, `handover_export`, `shopping_item`, `email`,
`certificate` are already handled. From current code:
- `certificate` → falls into `document/manual/certificate` branch ✓
- `email` → explicit branch ✓
- `shopping_item` → explicit branch ✓
- `handover` → explicit branch ✓
- `receiving` → falls to generic fallback (fine)
- `handover_item` → falls to generic fallback (fine)
- `handover_export` → falls to generic fallback (fine)

**Decision:** No changes needed to `_map_to_related_item` — generic fallback handles the
new types adequately. Certificate is already covered by the `document/manual/certificate`
branch on line 488. Only add a branch if you observe malformed output in practice.

- [ ] **Step 9.1: Confirm no change needed**

```bash
grep -A5 "elif object_type in.*document.*manual.*certificate" \
  /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/handlers/show_related_signal_handlers.py
```
Expected: branch exists and includes 'certificate' in the tuple.

---

### Task 10: Run the E2E spec and verify 14 passed / 0 skipped

- [ ] **Step 10.1: Ensure local API and frontend are running**

```bash
# In separate terminals:
# Terminal 1 — API (port 8000)
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
uvicorn pipeline_service:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend (port 3001)
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web
npm run dev -- --port 3001
```

- [ ] **Step 10.2: Run the signal spec**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web
E2E_NO_SERVER=1 \
E2E_BASE_URL=http://localhost:3001 \
SUPABASE_JWT_SECRET="ep2o/+mEQD..." \
npx playwright test e2e/shard-34-lens-actions/show-related-signal.spec.ts \
  --project=shard-34-lens-actions \
  --reporter=list
```

**Expected result: 14 passed, 0 skipped**

- [ ] **Step 10.3: If navigation test still skips — diagnose**

If `signal-also-related` section never appears after `seedSearchIndex()`, the issue
is in how the fixture's upserted row is being picked up by f1_search_cards RPC.

Diagnose:
```sql
-- Verify the seeded row is indexed
SELECT object_type, object_id, embedding_status, LEFT(search_text, 100) as preview,
       (embedding_1536 IS NOT NULL) as has_vector
FROM search_index
WHERE content_hash = 'test-fixture-hash';
```

If `embedding_status = 'pending'` → worker is overwriting our fixture row (we set it
to 'indexed', but if the projector claims it before the test runs, it will set it back
to 'processing'). Fix: re-read fixture task implementation — upsert must set `source_version`
very high (e.g., 9999) so the projector's `WHERE source_version < EXCLUDED.source_version`
guard skips it.

If `embedding_status = 'indexed'` but no results → text may not match FTS query.
Check what entity_text the WO produces:
```sql
SELECT search_text FROM search_index
WHERE object_type = 'work_order'
  AND object_id = '<the_seeded_wo_id>';
```
Then check if `plainto_tsquery('english', '<entity_text>')` matches the fixture's tsv:
```sql
SELECT to_tsvector('english', 'EQUIPMENT_NAME maintenance work order inspection')
  @@ plainto_tsquery('english', 'ENTITY_TEXT_HERE') AS matches;
```

- [ ] **Step 10.4: Record final state**

```sql
-- Final proof query — save this output
SELECT
  COUNT(*) FILTER (WHERE embedding_status = 'indexed') AS indexed,
  COUNT(*) FILTER (WHERE embedding_status = 'pending') AS pending,
  COUNT(*) FILTER (WHERE embedding_1536 IS NOT NULL) AS has_vector,
  COUNT(DISTINCT object_type) AS type_coverage
FROM search_index
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

## Memory + Agent Hygiene Rules (READ BEFORE WORKING OVERNIGHT)

### For every agent spawned:

1. **Memory-first**: Before taking any action, read `tasks/lessons.md` and the
   relevant memory files in `.claude/projects/-Volumes-Backup-CELESTE/memory/`
2. **Scope discipline**: Each agent must work ONLY within the files listed for its task.
   Do not touch files from other tasks even if they look related.
3. **Proof before marking done**: Never mark a step ✓ without running the verification
   command and seeing the expected output.
4. **On unexpected error**: STOP. Do not retry. Post the full error to the orchestrator.
   The orchestrator will diagnose and assign the right fix.
5. **DB changes are permanent**: All SQL runs against the real Supabase DB. Test SQL
   with `ROLLBACK` first if unsure. Never run DELETE or UPDATE without a WHERE clause.

### Derailment protocol:

If any agent's output doesn't match "Expected:" in a verification step:
1. **STOP** — do not proceed to next step
2. Post the actual vs expected diff to the orchestrator
3. Orchestrator re-reads the plan and assigns corrected task
4. Resume from the failed step only — do not re-run completed steps

### Memory files to update after completion:

After all tasks done, update or create:
- `memory/project_show_related_signal_v2.md` — add "Workers running locally" entry, entity types covered
- `memory/reference_local_dev_setup.md` — add docker-compose.f1-workers.yml as local worker launcher

---

## Critical Constraints (DO NOT VIOLATE)

| Constraint | Rule |
|------------|------|
| LAW 9 (Projection Immutability) | Never add `embedding_1536`, `embedding_status`, `learned_keywords` to projection_worker upsert SET clause |
| Vector dimension | `embedding_1536` column expects exactly 1536 floats — any other size fails the index |
| Port 6543 for workers | psycopg2 requires Supavisor session pooler — port 5432 (direct) fails with prepared statements |
| No blanket kills | Never kill all python processes — user runs multiple Claude sessions |
| content_hash = 'test-fixture-hash' | Fixture cleanup targets ONLY rows with this hash |
| source_version guard | Projector skips rows WHERE source_version >= existing. Set fixture source_version high (9999) to prevent overwrite |

---

## Success Criteria

| Criterion | Verification |
|-----------|-------------|
| Workers launched without error | Docker logs show `Batch complete. Total: N done` |
| search_index populated | SQL: `COUNT(*) WHERE embedding_status='indexed' AND search_text IS NOT NULL > 0` |
| Vectors written | SQL: `COUNT(*) WHERE embedding_1536 IS NOT NULL > 0` |
| New serializers compile | `python -m py_compile` returns 0 |
| E2E spec passes | `14 passed, 0 skipped` in Playwright output |
