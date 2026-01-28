# Work Order Lens P1: Show Related — Deep Architecture Plan

**Date:** 2026-01-28
**Mission:** Deliver deterministic, RLS-safe "related side panel" for every focused entity
**Timeline:** 4-hour implementation + ongoing refinement
**Status:** 🔴 PLANNING PHASE

---

## Executive Summary

This document provides a comprehensive architectural plan for implementing the "Show Related" feature. While basic scaffolding exists, this plan addresses the deeper complexities of:

1. **Embeddings-powered similarity** (optional P1.5, required P2)
2. **Production-grade performance** (sub-200ms p95 latency)
3. **Comprehensive edge cases** (equipment hierarchies, cross-domain links, temporal patterns)
4. **RLS security depth** (role transitions, impersonation, service accounts)
5. **Observability** (query traces, user behavior analytics, relevance feedback)

---

## Part 1: Current State Assessment

### ✅ What Exists (Scaffolding Complete)

```
✓ 8-phase documentation (~78KB)
✓ Registry actions (view_related_entities, add_entity_link)
✓ RelatedHandlers with 5 FK relation types
✓ Routes: GET /v1/related, POST /v1/related/add
✓ Docker tests (10 scenarios)
✓ Commit: 34d32a5
```

### ⚠️ What's Missing (Deep Implementation Gaps)

```
⚠️ Embeddings strategy (storage, generation, similarity queries)
⚠️ Performance optimization (query plans, indexes, caching)
⚠️ Edge case handling (equipment hierarchies, orphaned entities, circular refs)
⚠️ Advanced match reasons (text mentions, temporal patterns, user feedback)
⚠️ Production observability (traces, metrics, alerting)
⚠️ Frontend integration details (real-time updates, optimistic UI, undo)
⚠️ Rollout strategy (feature flags, A/B testing, gradual rollout)
⚠️ Load testing (concurrent users, cache thrashing, DB pressure)
```

---

## Part 2: Embeddings Architecture (Critical Path)

### 2.1 Why Embeddings Matter

**Problem:** FK joins alone miss:
- Semantic similarity ("starboard main engine bearing" vs "right primary engine bearing")
- Implicit relationships (work orders mentioning same symptoms)
- Historical patterns (similar failures on similar equipment)

**Solution:** Hybrid approach combining **deterministic FK joins** (weight: 100-80) with **semantic similarity** (weight: 60-40).

### 2.2 Embeddings Storage Schema

```sql
-- New table: pms_entity_embeddings
CREATE TABLE public.pms_entity_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  entity_type TEXT NOT NULL CHECK (entity_type IN ('work_order', 'part', 'manual', 'equipment', 'fault')),
  entity_id UUID NOT NULL,
  embedding_model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  embedding_vector VECTOR(1536), -- pgvector extension
  source_text TEXT NOT NULL, -- what was embedded
  metadata JSONB DEFAULT '{}', -- denormalized fields for filtering
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ,
  UNIQUE (yacht_id, entity_type, entity_id, embedding_model)
);

-- Indexes
CREATE INDEX idx_embeddings_yacht_entity ON pms_entity_embeddings(yacht_id, entity_type, entity_id);
CREATE INDEX idx_embeddings_vector ON pms_entity_embeddings USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);

-- Enable RLS
ALTER TABLE pms_entity_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "embeddings_select_policy" ON pms_entity_embeddings
  FOR SELECT
  USING (yacht_id = public.get_user_yacht_id());
```

### 2.3 Embedding Generation Pipeline

**Trigger Strategy:**
```sql
-- Async trigger on entity insert/update
CREATE OR REPLACE FUNCTION trigger_embedding_generation()
RETURNS TRIGGER AS $$
BEGIN
  -- Insert into job queue (supabase edge function or pg_cron)
  INSERT INTO pms_background_jobs (job_type, payload, yacht_id)
  VALUES (
    'generate_embedding',
    jsonb_build_object(
      'entity_type', TG_TABLE_NAME,
      'entity_id', NEW.id,
      'source_text', NEW.title || ' ' || COALESCE(NEW.description, '')
    ),
    NEW.yacht_id
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER work_order_embedding_trigger
AFTER INSERT OR UPDATE OF title, description ON pms_work_orders
FOR EACH ROW EXECUTE FUNCTION trigger_embedding_generation();
```

**Background Worker:**
```python
# apps/api/workers/embedding_worker.py
async def process_embedding_job(job_id: str, payload: dict):
    """Generate and store embedding for an entity."""
    entity_type = payload["entity_type"]
    entity_id = payload["entity_id"]
    source_text = payload["source_text"]

    # Generate embedding (OpenAI API)
    embedding = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=source_text[:8000]  # truncate to model limit
    )

    # Store in DB
    await db.table("pms_entity_embeddings").upsert({
        "yacht_id": payload["yacht_id"],
        "entity_type": entity_type,
        "entity_id": entity_id,
        "embedding_vector": embedding.data[0].embedding,
        "source_text": source_text,
        "metadata": {
            "title": payload.get("title"),
            "status": payload.get("status"),
            "equipment_id": payload.get("equipment_id")
        },
        "updated_at": datetime.utcnow()
    }).execute()
```

### 2.4 Similarity Query Integration

**Query Pattern:**
```sql
-- Find similar work orders via embeddings
SELECT
  e.entity_id,
  e.entity_type,
  e.metadata->>'title' AS title,
  1 - (e.embedding_vector <=> focal.embedding_vector) AS similarity_score,
  ARRAY['embedding_similar']::TEXT[] AS match_reasons,
  60 AS weight  -- Lower than FK joins
FROM pms_entity_embeddings e
JOIN pms_entity_embeddings focal ON (
  focal.entity_type = 'work_order' AND focal.entity_id = :work_order_id
)
WHERE e.yacht_id = :yacht_id
  AND e.entity_type IN ('work_order', 'part', 'manual')
  AND e.entity_id != :work_order_id
  AND 1 - (e.embedding_vector <=> focal.embedding_vector) > 0.7  -- similarity threshold
ORDER BY similarity_score DESC
LIMIT 10;
```

**Handler Integration:**
```python
async def _query_embedding_similar(self, entity_id: str, yacht_id: str, limit: int = 10):
    """Query similar entities via embeddings (optional layer)."""
    try:
        result = self.db.rpc("get_embedding_similar", {
            "p_entity_type": "work_order",
            "p_entity_id": entity_id,
            "p_yacht_id": yacht_id,
            "p_threshold": 0.7,
            "p_limit": limit
        }).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Embedding similarity failed: {e}")
        return []  # Graceful degradation
```

### 2.5 Embeddings Rollout Strategy

**Phase 1 (P1 - Optional):**
- ✅ FK joins only (current implementation)
- 🔄 Add embedding generation pipeline (background)
- 🔄 Backfill existing entities (batch job)
- ❌ Don't show embedding results yet (collect data first)

**Phase 2 (P1.5 - Soft Launch):**
- ✅ Show embedding results in separate "Similar" group (weight: 60)
- ✅ A/B test: 50% of users see embeddings, 50% FK only
- ✅ Measure relevance: track which items users click on

**Phase 3 (P2 - Full Integration):**
- ✅ Merge FK + embedding results with hybrid ranking
- ✅ User feedback loop: "Was this helpful?" → retrain model
- ✅ Fine-tune thresholds based on production data

---

## Part 3: Performance Optimization Deep Dive

### 3.1 Query Performance Analysis

**Current Query Plan Issues:**
```sql
-- EXPLAIN ANALYZE for FK join queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.id, p.name, p.part_number
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = '...' AND wop.yacht_id = '...';

-- Expected issues:
-- ❌ Sequential scan on pms_work_order_parts (missing index)
-- ❌ Nested loop join (should be hash join for large result sets)
-- ❌ No shared_buffers hits (cold cache)
```

**Optimization Strategy:**

```sql
-- 1. Covering indexes (include columns in index to avoid table lookups)
CREATE INDEX idx_wo_parts_covering ON pms_work_order_parts(work_order_id, yacht_id)
INCLUDE (part_id, quantity, created_at);

-- 2. Partial indexes (exclude soft-deleted rows)
CREATE INDEX idx_pms_parts_active ON pms_parts(id, yacht_id)
WHERE deleted_at IS NULL;

-- 3. Multi-column indexes for common filters
CREATE INDEX idx_pms_documents_equipment_type ON pms_documents(equipment_id, doc_type, yacht_id)
WHERE deleted_at IS NULL;

-- 4. GIN index for JSONB metadata (if using metadata filters)
CREATE INDEX idx_entity_links_metadata ON pms_entity_links USING gin(metadata jsonb_path_ops);
```

### 3.2 Caching Strategy

**Layer 1: Application Cache (Redis)**
```python
# Cache entire related response for 60s
@cache(ttl=60, key_prefix="related")
async def get_related(yacht_id: str, entity_type: str, entity_id: str):
    # ...implementation
    pass

# Invalidate on write
async def add_entity_link(...):
    result = await db.insert(...)
    # Invalidate cache for both source and target
    await cache.delete(f"related:{source_entity_type}:{source_entity_id}")
    await cache.delete(f"related:{target_entity_type}:{target_entity_id}")
    return result
```

**Layer 2: DB Statement Cache**
```python
# Use prepared statements (Supabase handles this)
# Ensure connection pooling (pgBouncer)
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
```

**Layer 3: Materialized Views (for expensive aggregations)**
```sql
-- If "previous work orders on same equipment" is slow
CREATE MATERIALIZED VIEW mv_equipment_work_history AS
SELECT
  equipment_id,
  yacht_id,
  jsonb_agg(
    jsonb_build_object(
      'work_order_id', id,
      'title', title,
      'created_at', created_at,
      'status', status
    ) ORDER BY created_at DESC
  ) AS work_orders
FROM pms_work_orders
WHERE deleted_at IS NULL
GROUP BY equipment_id, yacht_id;

CREATE UNIQUE INDEX ON mv_equipment_work_history(equipment_id, yacht_id);

-- Refresh strategy
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_equipment_work_history;
-- Run via pg_cron every 5 minutes
```

### 3.3 Query Batching & N+1 Prevention

**Problem:**
```python
# ❌ N+1 query antipattern
for group in groups:
    for item in group["items"]:
        # Fetches entity details one at a time
        details = await fetch_entity_details(item["entity_id"])
```

**Solution: DataLoader Pattern**
```python
# ✅ Batch fetch with DataLoader
from aiodataloader import DataLoader

class EntityDetailsLoader(DataLoader):
    async def batch_load_fn(self, entity_ids):
        # Fetch all in one query
        result = await db.table("pms_work_orders").select("*").in_("id", entity_ids).execute()
        # Return in same order as requested
        lookup = {row["id"]: row for row in result.data}
        return [lookup.get(eid) for eid in entity_ids]

loader = EntityDetailsLoader()
# All fetches are automatically batched
details = await asyncio.gather(*[loader.load(item["entity_id"]) for item in items])
```

### 3.4 Response Size Optimization

**Problem:** Large responses (>1MB) slow down network and parsing.

**Solutions:**
```python
# 1. Pagination for large groups
async def list_related(self, ..., offset: int = 0, limit: int = 10):
    # Return paginated results with cursors
    return {
        "groups": [
            {
                "group_key": "parts",
                "total_count": 150,  # full count
                "items": parts[offset:offset+limit],
                "next_cursor": encode_cursor(offset + limit) if offset + limit < 150 else None
            }
        ]
    }

# 2. Field selection (sparse fieldsets)
async def list_related(self, ..., fields: List[str] = None):
    # Only return requested fields
    if fields:
        return {item: {k: v for k, v in item.items() if k in fields} for item in items}

# 3. Response compression (gzip)
# FastAPI handles this automatically if client sends Accept-Encoding: gzip
```

---

## Part 4: Advanced Match Reasons Taxonomy

### 4.1 Complete Match Reason Classification

```python
# Match reason constants with weights
MATCH_REASONS = {
    # FK joins (100-90)
    "FK:wo_part": {"weight": 100, "label": "Part on this work order", "icon": "🔩"},
    "FK:wo_attachment": {"weight": 100, "label": "Attached to this work order", "icon": "📎"},
    "FK:equipment": {"weight": 90, "label": "Same equipment", "icon": "⚙️"},
    "FK:fault": {"weight": 90, "label": "Related fault", "icon": "⚠️"},
    "FK:equipment_manual": {"weight": 90, "label": "Equipment manual", "icon": "📖"},
    "FK:equipment_handover": {"weight": 90, "label": "Equipment handover notes", "icon": "📝"},

    # Derived relationships (80-70)
    "same_equipment": {"weight": 80, "label": "Previous work on same equipment", "icon": "🔄"},
    "same_fault_type": {"weight": 75, "label": "Similar fault type", "icon": "🔍"},
    "explicit_link": {"weight": 70, "label": "Manually linked by HOD", "icon": "🔗"},

    # Embeddings-based (60-50)
    "embedding_similar": {"weight": 60, "label": "Semantically similar", "icon": "🧠"},
    "embedding_parts": {"weight": 55, "label": "Similar parts mentioned", "icon": "🔩"},

    # Text mentions (50-40)
    "mentions:PARTNUM": {"weight": 50, "label": "Part number mentioned in description", "icon": "💬"},
    "mentions:EQUIPNAME": {"weight": 45, "label": "Equipment name mentioned", "icon": "💬"},
    "mentions:FAULT_CODE": {"weight": 45, "label": "Fault code mentioned", "icon": "💬"},

    # Temporal patterns (40-30)
    "temporal:recent": {"weight": 40, "label": "Recently related (within 7 days)", "icon": "⏰"},
    "temporal:seasonal": {"weight": 35, "label": "Seasonal pattern", "icon": "📅"},

    # User behavior (30-20)
    "user_viewed_together": {"weight": 30, "label": "Users often view these together", "icon": "👥"},
    "user_feedback": {"weight": 25, "label": "Marked helpful by users", "icon": "👍"},
}
```

### 4.2 Match Reason Combination Logic

```python
def merge_match_reasons(items: List[dict]) -> List[dict]:
    """Deduplicate items and merge match reasons."""
    seen = {}
    for item in items:
        eid = item["entity_id"]
        if eid in seen:
            # Merge match reasons (keep unique)
            existing_reasons = set(seen[eid]["match_reasons"])
            new_reasons = set(item["match_reasons"])
            seen[eid]["match_reasons"] = sorted(existing_reasons | new_reasons)

            # Take highest weight
            seen[eid]["weight"] = max(seen[eid]["weight"], item["weight"])

            # Increment match count (for sorting)
            seen[eid]["match_count"] = seen[eid].get("match_count", 1) + 1
        else:
            seen[eid] = item
            seen[eid]["match_count"] = 1

    # Sort by weight DESC, then match_count DESC
    return sorted(seen.values(), key=lambda x: (-x["weight"], -x["match_count"]))
```

### 4.3 Text Mentions Detection

```python
import re

async def extract_text_mentions(text: str, yacht_id: str) -> dict:
    """Extract part numbers, equipment names, fault codes from text."""
    mentions = {"parts": [], "equipment": [], "faults": []}

    # Part number patterns (e.g., P12345, PN-ABC-123)
    part_pattern = r'\b(?:P|PN|PART)[-\s]?[A-Z0-9]{3,10}\b'
    part_numbers = re.findall(part_pattern, text, re.IGNORECASE)

    # Lookup parts in DB
    if part_numbers:
        result = await db.table("pms_parts").select("id, name, part_number").in_(
            "part_number", part_numbers
        ).eq("yacht_id", yacht_id).execute()
        mentions["parts"] = result.data

    # Equipment name mentions (fuzzy match against known equipment)
    equipment_cache = await get_yacht_equipment_names(yacht_id)
    for eq_name in equipment_cache:
        if eq_name.lower() in text.lower():
            mentions["equipment"].append({"name": eq_name, "score": 1.0})

    # Fault code patterns (e.g., F-001, FAULT-ABC)
    fault_pattern = r'\b(?:F|FAULT)[-\s]?[A-Z0-9]{3,8}\b'
    fault_codes = re.findall(fault_pattern, text, re.IGNORECASE)

    if fault_codes:
        result = await db.table("pms_faults").select("id, fault_code, title").in_(
            "fault_code", fault_codes
        ).eq("yacht_id", yacht_id).execute()
        mentions["faults"] = result.data

    return mentions
```

---

## Part 5: Edge Cases & Error Handling

### 5.1 Equipment Hierarchy Navigation

**Problem:** Work order is on a child component, manual exists for parent equipment.

```sql
-- Equipment hierarchy table (if exists)
CREATE TABLE IF NOT EXISTS pms_equipment_hierarchy (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  parent_equipment_id UUID REFERENCES pms_equipment(id),
  child_equipment_id UUID REFERENCES pms_equipment(id),
  relationship_type TEXT DEFAULT 'component_of',
  UNIQUE (yacht_id, parent_equipment_id, child_equipment_id)
);

-- Query: Find manuals for parent equipment
WITH RECURSIVE equipment_ancestors AS (
  -- Base case: direct equipment
  SELECT equipment_id AS ancestor_id, 0 AS depth
  FROM pms_work_orders
  WHERE id = :work_order_id

  UNION

  -- Recursive case: walk up hierarchy
  SELECT h.parent_equipment_id, ea.depth + 1
  FROM equipment_ancestors ea
  JOIN pms_equipment_hierarchy h ON h.child_equipment_id = ea.ancestor_id
  WHERE ea.depth < 5  -- prevent infinite loops
)
SELECT DISTINCT
  d.id AS entity_id,
  'manual' AS entity_type,
  d.title,
  e.name AS subtitle,
  ARRAY['FK:equipment_ancestor'] AS match_reasons,
  85 - (ea.depth * 5) AS weight  -- penalize distance
FROM equipment_ancestors ea
JOIN pms_equipment e ON e.id = ea.ancestor_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE d.doc_type = 'manual' AND d.yacht_id = :yacht_id
ORDER BY weight DESC
LIMIT 10;
```

### 5.2 Orphaned Entity Handling

**Problem:** Work order references deleted equipment/fault.

```python
async def _query_related_manuals(self, work_order_id: str, yacht_id: str):
    """Query manuals for equipment (handle deleted equipment gracefully)."""

    # Get work order with equipment
    wo = await self.db.table("pms_work_orders").select(
        "id, equipment_id, pms_equipment(id, name, deleted_at)"
    ).eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()

    equipment = wo.data.get("pms_equipment")

    # If equipment deleted, show warning but don't fail
    if not equipment or equipment.get("deleted_at"):
        logger.warning(f"WO {work_order_id} references deleted equipment")
        return []  # graceful degradation

    # Continue with normal query
    # ...
```

### 5.3 Circular Reference Prevention

**Problem:** Explicit links create cycles (A→B→C→A).

```python
async def add_entity_link(self, ..., prevent_cycles: bool = True):
    """Add explicit link with optional cycle detection."""

    if prevent_cycles:
        # Check if adding this link would create a cycle
        cycle_detected = await self._detect_cycle(
            source_entity_type, source_entity_id,
            target_entity_type, target_entity_id,
            yacht_id
        )

        if cycle_detected:
            raise HTTPException(
                status_code=400,
                detail="Cannot add link: would create circular reference"
            )

    # Proceed with insert
    # ...

async def _detect_cycle(self, src_type, src_id, tgt_type, tgt_id, yacht_id, max_depth=10):
    """DFS to detect if adding edge src→tgt would create a cycle."""

    # Use recursive CTE to traverse graph
    query = """
    WITH RECURSIVE link_graph AS (
      -- Start from target (if we can reach source from target, it's a cycle)
      SELECT target_entity_type, target_entity_id, 1 AS depth
      FROM pms_entity_links
      WHERE source_entity_type = :tgt_type
        AND source_entity_id = :tgt_id
        AND yacht_id = :yacht_id

      UNION

      SELECT el.target_entity_type, el.target_entity_id, lg.depth + 1
      FROM link_graph lg
      JOIN pms_entity_links el ON (
        el.source_entity_type = lg.target_entity_type
        AND el.source_entity_id = lg.target_entity_id
        AND el.yacht_id = :yacht_id
      )
      WHERE lg.depth < :max_depth
    )
    SELECT 1 FROM link_graph
    WHERE target_entity_type = :src_type AND target_entity_id = :src_id
    LIMIT 1;
    """

    result = await self.db.raw_sql(query, {
        "src_type": src_type, "src_id": src_id,
        "tgt_type": tgt_type, "tgt_id": tgt_id,
        "yacht_id": yacht_id, "max_depth": max_depth
    }).execute()

    return len(result.data) > 0
```

### 5.4 Storage Bucket RLS Enforcement

**Problem:** Document metadata returned but user can't access storage bucket.

```python
async def enrich_document_items(self, items: List[dict], user_id: str, yacht_id: str):
    """Enrich documents with access flags (don't return URLs if no access)."""

    for item in items:
        if item["entity_type"] in ("manual", "handover", "attachment"):
            # Check if user can access storage
            has_storage_access = await self._check_storage_access(
                user_id, yacht_id, item["bucket_path"]
            )

            item["has_storage_access"] = has_storage_access

            # Only include URL if access granted
            if has_storage_access:
                item["download_url"] = await self._generate_signed_url(
                    item["bucket_path"], expires_in=3600
                )
            else:
                item["download_url"] = None
                item["access_note"] = "Request access from HOD"

    return items

async def _check_storage_access(self, user_id: str, yacht_id: str, bucket_path: str):
    """Check Supabase Storage RLS for access."""
    try:
        # Attempt to get file metadata (RLS will block if no access)
        result = await self.storage.from_("pms-work-order-photos").list(
            path=bucket_path,
            options={"limit": 1}
        )
        return True
    except Exception as e:
        if "policy" in str(e).lower():
            return False
        raise
```

### 5.5 Temporal Edge Cases

**Problem:** Show recent vs historical work orders.

```python
# Add time-based filtering
async def _query_previous_work(self, work_order_id: str, yacht_id: str,
                                time_filter: str = "all"):
    """Query previous work orders with temporal filtering."""

    query = self.db.table("pms_work_orders").select(
        "id, wo_number, title, status, created_at, equipment_id"
    ).eq("equipment_id", equipment_id).neq("id", work_order_id).eq("yacht_id", yacht_id)

    if time_filter == "recent":
        # Last 30 days
        cutoff = datetime.now() - timedelta(days=30)
        query = query.gte("created_at", cutoff.isoformat())
    elif time_filter == "seasonal":
        # Same month in previous years (for seasonal patterns)
        current_month = datetime.now().month
        query = query.filter("EXTRACT(MONTH FROM created_at)", "eq", current_month)

    result = query.order("created_at", desc=True).limit(20).execute()

    # Add temporal match reason
    items = []
    for wo in result.data:
        created_at = datetime.fromisoformat(wo["created_at"])
        days_ago = (datetime.now() - created_at).days

        if days_ago <= 7:
            match_reason = "temporal:recent"
            weight = 85
        elif days_ago <= 30:
            match_reason = "same_equipment"
            weight = 80
        else:
            match_reason = "same_equipment"
            weight = 75

        items.append({
            "entity_id": wo["id"],
            "wo_number": wo["wo_number"],
            "title": wo["title"],
            "subtitle": f"{days_ago} days ago",
            "match_reasons": [match_reason],
            "weight": weight
        })

    return items
```

---

## Part 6: RLS Security Deep Dive

### 6.1 Multi-Yacht Role Scenarios

**Problem:** User has different roles on different yachts.

```python
# JWT structure
{
  "sub": "user-uuid",
  "yacht_id": "current-yacht-uuid",  # ← Active yacht
  "all_yachts": [
    {"yacht_id": "yacht-1", "role": "crew"},
    {"yacht_id": "yacht-2", "role": "chief_engineer"}
  ]
}

# RLS helpers must use CURRENT yacht
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
  SELECT (auth.jwt() -> 'yacht_id')::TEXT::UUID;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

# NOT all yachts from array
```

### 6.2 Role Transition Handling

**Problem:** User promoted from crew to HOD mid-session.

```python
# Frontend: Poll for role changes every 5 minutes
async function checkRoleUpdate() {
  const response = await fetch('/v1/auth/me');
  const newRole = response.data.role;

  if (newRole !== currentRole) {
    // Force JWT refresh
    await refreshToken();
    // Refresh UI permissions
    window.location.reload();
  }
}

# Backend: Short JWT expiry (15 minutes) forces role refresh
JWT_EXPIRY = 900  # 15 minutes

# RLS: Always check current role in DB (not JWT)
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.auth_users_roles r
    WHERE r.user_id = auth.uid()
      AND r.yacht_id = public.get_user_yacht_id()
      AND r.is_active = true
      AND r.role IN ('chief_engineer', 'chief_officer', 'captain', 'purser')
      AND r.valid_until > NOW()  -- ← Time-bound roles
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;
```

### 6.3 Service Account Access

**Problem:** Background jobs need to read/write without user context.

```sql
-- Service account role
CREATE ROLE service_account WITH LOGIN PASSWORD 'secret';

-- Bypass RLS for service account (use sparingly)
CREATE POLICY "service_account_bypass" ON pms_entity_embeddings
  FOR ALL
  TO service_account
  USING (true)
  WITH CHECK (true);

-- Alternative: Use SECURITY DEFINER functions
CREATE OR REPLACE FUNCTION public.service_generate_embedding(
  p_yacht_id UUID,
  p_entity_type TEXT,
  p_entity_id UUID,
  p_embedding VECTOR
)
RETURNS UUID AS $$
DECLARE
  v_embedding_id UUID;
BEGIN
  INSERT INTO pms_entity_embeddings (yacht_id, entity_type, entity_id, embedding_vector)
  VALUES (p_yacht_id, p_entity_type, p_entity_id, p_embedding)
  RETURNING id INTO v_embedding_id;

  RETURN v_embedding_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to service account
GRANT EXECUTE ON FUNCTION public.service_generate_embedding TO service_account;
```

### 6.4 Impersonation for Support

**Problem:** Support needs to debug user issues without accessing their data.

```python
# Audit log for impersonation
async def impersonate_user(
    support_user_id: str,
    target_user_id: str,
    reason: str,
    duration_minutes: int = 30
):
    """Allow support to impersonate user (with full audit trail)."""

    # Verify support_user has impersonation permission
    if not await has_permission(support_user_id, "impersonate_user"):
        raise HTTPException(403, detail="Not authorized to impersonate")

    # Log impersonation start
    await db.table("pms_audit_log").insert({
        "action": "impersonation_start",
        "user_id": support_user_id,
        "metadata": {
            "target_user_id": target_user_id,
            "reason": reason,
            "duration_minutes": duration_minutes
        },
        "ip_address": request.client.host
    }).execute()

    # Generate temporary JWT with impersonation flag
    jwt = create_jwt({
        "sub": target_user_id,
        "yacht_id": target_yacht_id,
        "impersonated_by": support_user_id,
        "impersonation_expires_at": datetime.now() + timedelta(minutes=duration_minutes)
    })

    return {"jwt": jwt, "expires_in": duration_minutes * 60}

# RLS: Block sensitive actions during impersonation
CREATE POLICY "no_impersonation_writes" ON pms_entity_links
  FOR INSERT
  WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (public.is_hod() OR public.is_manager())
    AND (auth.jwt() ->> 'impersonated_by') IS NULL  -- ← Block writes during impersonation
  );
```

### 6.5 Cross-Tenant Leak Testing

```python
# Automated test for RLS leaks
async def test_cross_yacht_isolation():
    """Verify no data leaks between yachts."""

    # Create two test users on different yachts
    jwt_yacht_a = get_test_jwt(yacht_id="yacht-a-uuid")
    jwt_yacht_b = get_test_jwt(yacht_id="yacht-b-uuid")

    # Create work order on yacht A
    wo_a = await create_test_work_order(jwt_yacht_a)

    # Try to access from yacht B (should fail)
    response = await api_get(
        f"/v1/related?entity_type=work_order&entity_id={wo_a['id']}",
        jwt_yacht_b
    )

    assert response.status_code == 404, "Cross-yacht leak detected!"
    assert "not found" in response.json()["detail"].lower()

    # Try to add link from yacht B to yacht A entity (should fail)
    response = await api_post(
        "/v1/related/add",
        jwt_yacht_b,
        {
            "yacht_id": "yacht-b-uuid",
            "source_entity_type": "work_order",
            "source_entity_id": "yacht-b-wo-id",
            "target_entity_type": "work_order",
            "target_entity_id": wo_a["id"]  # ← Cross-yacht reference
        }
    )

    assert response.status_code in (403, 404), "Cross-yacht link allowed!"
```

---

## Part 7: Testing Strategy (Multi-Layered)

### 7.1 Unit Tests (Handler Logic)

```python
# tests/unit/test_related_handlers.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_merge_match_reasons():
    """Test deduplication and reason merging."""
    items = [
        {"entity_id": "part-1", "match_reasons": ["FK:wo_part"], "weight": 100},
        {"entity_id": "part-1", "match_reasons": ["mentions:PARTNUM"], "weight": 50},
        {"entity_id": "part-2", "match_reasons": ["FK:wo_part"], "weight": 100}
    ]

    merged = merge_match_reasons(items)

    assert len(merged) == 2
    assert set(merged[0]["match_reasons"]) == {"FK:wo_part", "mentions:PARTNUM"}
    assert merged[0]["weight"] == 100  # Highest weight preserved
    assert merged[0]["match_count"] == 2

@pytest.mark.asyncio
async def test_graceful_embedding_failure():
    """Test fallback when embeddings unavailable."""
    with patch("handlers.related_handlers._query_embedding_similar", side_effect=Exception("DB down")):
        result = await list_related(yacht_id="test", entity_type="work_order", entity_id="wo-1")

        # Should still return FK results
        assert result["status"] == "success"
        assert len(result["groups"]) > 0
        # No embedding group
        assert not any(g["group_key"] == "similar" for g in result["groups"])
```

### 7.2 Integration Tests (DB + Handlers)

```python
# tests/integration/test_related_queries.py
@pytest.mark.asyncio
async def test_fk_query_performance():
    """Test FK queries complete in <100ms."""
    start = time.time()
    result = await _query_related_parts("test-wo-id", "test-yacht-id")
    elapsed = (time.time() - start) * 1000

    assert elapsed < 100, f"Query too slow: {elapsed}ms"

@pytest.mark.asyncio
async def test_equipment_hierarchy_traversal():
    """Test finding manuals via parent equipment."""
    # Setup: child equipment with no manual, parent has manual
    child_eq = await create_test_equipment(name="Starboard Engine Fuel Pump")
    parent_eq = await create_test_equipment(name="Starboard Main Engine")
    await link_equipment_hierarchy(child_eq["id"], parent_eq["id"])

    manual = await create_test_manual(equipment_id=parent_eq["id"])
    wo = await create_test_work_order(equipment_id=child_eq["id"])

    # Query related for work order
    result = await list_related(..., entity_id=wo["id"])

    # Should find manual via parent equipment
    manuals_group = next(g for g in result["groups"] if g["group_key"] == "manuals")
    assert len(manuals_group["items"]) == 1
    assert manuals_group["items"][0]["entity_id"] == manual["id"]
    assert "FK:equipment_ancestor" in manuals_group["items"][0]["match_reasons"]
```

### 7.3 Load Tests (Concurrent Users)

```python
# tests/load/test_related_load.py
import asyncio
from locust import HttpUser, task, between

class RelatedPanelUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and get JWT."""
        self.jwt = self.login()

    @task(10)  # 10x more common than writes
    def view_related(self):
        """Simulate user viewing related panel."""
        work_order_id = random.choice(self.test_work_orders)
        self.client.get(
            f"/v1/related?entity_type=work_order&entity_id={work_order_id}",
            headers={"Authorization": f"Bearer {self.jwt}"}
        )

    @task(1)
    def add_link(self):
        """Simulate HOD adding explicit link."""
        self.client.post(
            "/v1/related/add",
            json={
                "yacht_id": self.yacht_id,
                "source_entity_type": "work_order",
                "source_entity_id": random.choice(self.test_work_orders),
                "target_entity_type": "part",
                "target_entity_id": random.choice(self.test_parts),
                "link_type": "explicit"
            },
            headers={"Authorization": f"Bearer {self.jwt}"}
        )

# Run: locust -f tests/load/test_related_load.py --host=http://localhost:8000 --users=50 --spawn-rate=5
```

### 7.4 Property-Based Tests (Hypothesis)

```python
# tests/property/test_related_invariants.py
from hypothesis import given, strategies as st

@given(
    items=st.lists(
        st.fixed_dictionaries({
            "entity_id": st.uuids(),
            "match_reasons": st.lists(st.sampled_from(MATCH_REASONS.keys()), min_size=1),
            "weight": st.integers(min_value=20, max_value=100)
        }),
        min_size=0,
        max_size=100
    )
)
def test_merge_preserves_all_entities(items):
    """Property: Merging never loses entities."""
    merged = merge_match_reasons(items)
    unique_ids = {item["entity_id"] for item in items}
    merged_ids = {item["entity_id"] for item in merged}
    assert unique_ids == merged_ids

@given(
    weight1=st.integers(min_value=20, max_value=100),
    weight2=st.integers(min_value=20, max_value=100)
)
def test_merge_takes_max_weight(weight1, weight2):
    """Property: Merged weight is always max of individual weights."""
    items = [
        {"entity_id": "same-id", "match_reasons": ["reason1"], "weight": weight1},
        {"entity_id": "same-id", "match_reasons": ["reason2"], "weight": weight2}
    ]
    merged = merge_match_reasons(items)
    assert merged[0]["weight"] == max(weight1, weight2)
```

### 7.5 Chaos Tests (Failure Injection)

```python
# tests/chaos/test_related_resilience.py
@pytest.mark.chaos
async def test_db_timeout_handling():
    """Test graceful degradation when DB query times out."""
    with patch("supabase.postgrest.execute", side_effect=asyncio.TimeoutError()):
        result = await list_related(...)

        # Should return partial results or error, not crash
        assert result["status"] in ("success", "partial", "error")
        if result["status"] == "partial":
            assert "missing_signals" in result
            assert "db_timeout" in result["missing_signals"]

@pytest.mark.chaos
async def test_embeddings_service_down():
    """Test fallback when embeddings service unavailable."""
    with patch("openai.embeddings.create", side_effect=Exception("Service unavailable")):
        # Should still return FK results
        result = await list_related(...)
        assert result["status"] == "success"
        assert len([g for g in result["groups"] if g["group_key"] != "similar"]) > 0
```

---

## Part 8: Observability & Monitoring

### 8.1 Query Performance Tracing

```python
# Instrumentation with OpenTelemetry
from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

tracer = trace.get_tracer(__name__)

async def list_related(self, yacht_id: str, entity_type: str, entity_id: str):
    """List related entities with full tracing."""

    with tracer.start_as_current_span("list_related") as span:
        span.set_attribute("yacht_id", yacht_id)
        span.set_attribute("entity_type", entity_type)
        span.set_attribute("entity_id", entity_id)

        # Trace individual queries
        with tracer.start_as_current_span("query_parts"):
            parts = await self._query_related_parts(entity_id, yacht_id)
            span.set_attribute("parts_count", len(parts))

        with tracer.start_as_current_span("query_manuals"):
            manuals = await self._query_related_manuals(entity_id, yacht_id)
            span.set_attribute("manuals_count", len(manuals))

        # ... more queries

        with tracer.start_as_current_span("merge_and_rank"):
            merged = self._merge_explicit_links(...)
            span.set_attribute("total_items", sum(len(g) for g in merged.values()))

        return result

# View traces in Jaeger/Honeycomb
# Identify slow queries, N+1 issues, cache misses
```

### 8.2 User Behavior Analytics

```python
# Track which groups users interact with
async def track_related_interaction(
    user_id: str,
    yacht_id: str,
    work_order_id: str,
    interaction_type: str,  # "view", "click", "expand", "add_link"
    entity_id: str = None,
    entity_type: str = None
):
    """Track user interactions for analytics."""

    await db.table("pms_analytics_events").insert({
        "event_type": "related_panel_interaction",
        "user_id": user_id,
        "yacht_id": yacht_id,
        "metadata": {
            "work_order_id": work_order_id,
            "interaction_type": interaction_type,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    }).execute()

# Analytics queries
"""
-- Which groups get expanded most?
SELECT
  metadata->>'entity_type' AS group_type,
  COUNT(*) AS expand_count
FROM pms_analytics_events
WHERE event_type = 'related_panel_interaction'
  AND metadata->>'interaction_type' = 'expand'
GROUP BY group_type
ORDER BY expand_count DESC;

-- Which match reasons lead to clicks?
SELECT
  metadata->>'match_reason' AS reason,
  COUNT(*) AS click_count
FROM pms_analytics_events
WHERE event_type = 'related_panel_interaction'
  AND metadata->>'interaction_type' = 'click'
GROUP BY reason
ORDER BY click_count DESC;
"""
```

### 8.3 Relevance Feedback Loop

```python
# Frontend: Allow users to mark items as helpful/not helpful
<button onClick={() => markHelpful(item.entity_id, true)}>👍</button>
<button onClick={() => markHelpful(item.entity_id, false)}>👎</button>

# Backend: Store feedback
async def mark_related_helpful(
    user_id: str,
    yacht_id: str,
    source_entity_id: str,
    target_entity_id: str,
    is_helpful: bool
):
    """Store user feedback on related item relevance."""

    await db.table("pms_related_feedback").insert({
        "yacht_id": yacht_id,
        "user_id": user_id,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "is_helpful": is_helpful,
        "created_at": datetime.utcnow()
    }).execute()

# Use feedback to adjust weights
async def get_feedback_adjusted_weight(base_weight: int, entity_pair: tuple) -> int:
    """Adjust weight based on user feedback."""

    feedback = await db.table("pms_related_feedback").select(
        "is_helpful"
    ).match({
        "source_entity_id": entity_pair[0],
        "target_entity_id": entity_pair[1]
    }).execute()

    if not feedback.data:
        return base_weight

    # Calculate feedback ratio
    helpful_count = sum(1 for f in feedback.data if f["is_helpful"])
    total_count = len(feedback.data)
    helpful_ratio = helpful_count / total_count

    # Boost/penalize based on feedback
    if helpful_ratio > 0.8:
        return int(base_weight * 1.2)  # 20% boost
    elif helpful_ratio < 0.3:
        return int(base_weight * 0.7)  # 30% penalty
    else:
        return base_weight
```

### 8.4 Alerting & SLAs

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

related_requests_total = Counter(
    "related_requests_total",
    "Total related panel requests",
    ["entity_type", "status_code"]
)

related_latency = Histogram(
    "related_latency_seconds",
    "Related panel response time",
    ["entity_type"]
)

related_group_sizes = Gauge(
    "related_group_size",
    "Number of items in each group",
    ["group_key"]
)

# Instrumentation
async def list_related(...):
    start = time.time()

    try:
        result = await _fetch_related(...)
        status_code = 200

        # Record group sizes
        for group in result["groups"]:
            related_group_sizes.labels(group_key=group["group_key"]).set(group["count"])

        return result
    except HTTPException as e:
        status_code = e.status_code
        raise
    finally:
        related_requests_total.labels(entity_type=entity_type, status_code=status_code).inc()
        related_latency.labels(entity_type=entity_type).observe(time.time() - start)

# Alerting rules (Prometheus)
"""
# Alert if p95 latency > 500ms
alert: RelatedPanelSlow
expr: histogram_quantile(0.95, related_latency_seconds) > 0.5
for: 5m
annotations:
  summary: "Related panel is slow (p95 > 500ms)"

# Alert if error rate > 1%
alert: RelatedPanelErrors
expr: rate(related_requests_total{status_code!="200"}[5m]) / rate(related_requests_total[5m]) > 0.01
for: 2m
annotations:
  summary: "Related panel error rate > 1%"
"""
```

---

## Part 9: Frontend Integration (Detailed)

### 9.1 React Component Architecture

```typescript
// components/RelatedPanel/RelatedPanel.tsx
interface RelatedPanelProps {
  entityType: string;
  entityId: string;
  onLinkAdded?: (link: EntityLink) => void;
}

export function RelatedPanel({ entityType, entityId, onLinkAdded }: RelatedPanelProps) {
  const { data, isLoading, error } = useRelated(entityType, entityId);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [isAddingLink, setIsAddingLink] = useState(false);

  // Track analytics
  useEffect(() => {
    if (data) {
      trackEvent('related_panel_viewed', {
        entityType,
        entityId,
        groupsCount: data.groups.length
      });
    }
  }, [data]);

  if (isLoading) return <RelatedPanelSkeleton />;
  if (error) return <RelatedPanelError error={error} />;

  return (
    <aside className="related-panel">
      <header>
        <h2>Related Items</h2>
        {data.add_related_enabled && (
          <button onClick={() => setIsAddingLink(true)}>
            + Add Related
          </button>
        )}
      </header>

      {data.groups.map(group => (
        <RelatedGroup
          key={group.group_key}
          group={group}
          isExpanded={expandedGroups.has(group.group_key)}
          onExpand={() => {
            setExpandedGroups(prev => new Set(prev.add(group.group_key)));
            trackEvent('related_group_expanded', { groupKey: group.group_key });
          }}
          onItemClick={(item) => {
            trackEvent('related_item_clicked', {
              groupKey: group.group_key,
              entityType: item.entity_type,
              matchReasons: item.match_reasons
            });
            navigateToEntity(item.entity_type, item.entity_id);
          }}
        />
      ))}

      {isAddingLink && (
        <AddRelatedLinkModal
          sourceEntityType={entityType}
          sourceEntityId={entityId}
          onClose={() => setIsAddingLink(false)}
          onSuccess={(link) => {
            onLinkAdded?.(link);
            setIsAddingLink(false);
          }}
        />
      )}
    </aside>
  );
}
```

### 9.2 Real-Time Updates (Optional)

```typescript
// hooks/useRelated.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

export function useRelated(entityType: string, entityId: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['related', entityType, entityId],
    queryFn: () => fetchRelated(entityType, entityId),
    staleTime: 60_000, // Cache for 1 minute
  });

  // Subscribe to real-time updates (Supabase Realtime)
  useEffect(() => {
    const channel = supabase
      .channel(`related:${entityType}:${entityId}`)
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'pms_entity_links',
        filter: `source_entity_id=eq.${entityId}`
      }, (payload) => {
        // Invalidate cache when links change
        queryClient.invalidateQueries(['related', entityType, entityId]);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [entityType, entityId, queryClient]);

  return query;
}
```

### 9.3 Optimistic UI Updates

```typescript
// hooks/useAddRelatedLink.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useAddRelatedLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: AddLinkRequest) => addEntityLink(link),

    onMutate: async (newLink) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries(['related']);

      // Snapshot previous value
      const previousData = queryClient.getQueryData([
        'related',
        newLink.source_entity_type,
        newLink.source_entity_id
      ]);

      // Optimistically update
      queryClient.setQueryData(
        ['related', newLink.source_entity_type, newLink.source_entity_id],
        (old: RelatedResponse) => ({
          ...old,
          groups: old.groups.map(group => {
            if (group.group_key === 'explicit_links') {
              return {
                ...group,
                count: group.count + 1,
                items: [
                  {
                    entity_id: newLink.target_entity_id,
                    entity_type: newLink.target_entity_type,
                    title: '(Loading...)',
                    match_reasons: ['explicit_link'],
                    weight: 70,
                    _optimistic: true
                  },
                  ...group.items
                ]
              };
            }
            return group;
          })
        })
      );

      return { previousData };
    },

    onError: (err, newLink, context) => {
      // Rollback on error
      queryClient.setQueryData(
        ['related', newLink.source_entity_type, newLink.source_entity_id],
        context.previousData
      );
      toast.error('Failed to add link');
    },

    onSuccess: () => {
      toast.success('Link added successfully');
    },

    onSettled: (data, error, variables) => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries([
        'related',
        variables.source_entity_type,
        variables.source_entity_id
      ]);
    }
  });
}
```

### 9.4 Accessibility Features

```typescript
// components/RelatedPanel/RelatedGroup.tsx
export function RelatedGroup({ group, isExpanded, onExpand, onItemClick }) {
  return (
    <section
      className="related-group"
      aria-labelledby={`group-${group.group_key}-label`}
    >
      <button
        onClick={onExpand}
        aria-expanded={isExpanded}
        aria-controls={`group-${group.group_key}-content`}
        className="group-header"
      >
        <h3 id={`group-${group.group_key}-label`}>
          {group.label} ({group.count})
        </h3>
        <Icon name={isExpanded ? 'chevron-down' : 'chevron-right'} />
      </button>

      {isExpanded && (
        <ul
          id={`group-${group.group_key}-content`}
          className="group-items"
          role="list"
        >
          {group.items.map((item, idx) => (
            <li key={item.entity_id} role="listitem">
              <button
                onClick={() => onItemClick(item)}
                className="item-button"
                aria-label={`View ${item.title} (${item.match_reasons.join(', ')})`}
              >
                <div className="item-content">
                  <span className="item-title">{item.title}</span>
                  <span className="item-subtitle">{item.subtitle}</span>
                </div>

                <div className="item-meta">
                  {item.match_reasons.map(reason => (
                    <span
                      key={reason}
                      className="match-reason-chip"
                      title={MATCH_REASONS[reason].label}
                    >
                      {MATCH_REASONS[reason].icon}
                    </span>
                  ))}
                </div>
              </button>

              {/* Feedback buttons */}
              <div className="item-actions" role="group" aria-label="Feedback">
                <button
                  onClick={() => markHelpful(item.entity_id, true)}
                  aria-label="Mark as helpful"
                >
                  👍
                </button>
                <button
                  onClick={() => markHelpful(item.entity_id, false)}
                  aria-label="Mark as not helpful"
                >
                  👎
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

---

## Part 10: Rollout & Operations Plan

### 10.1 Phased Rollout Strategy

**Week 1: Internal Alpha (Single Yacht)**
```python
# Feature flag configuration
FEATURE_FLAGS = {
    "related_panel_enabled": {
        "enabled_yachts": ["yacht-internal-test-uuid"],
        "enabled_roles": ["chief_engineer", "captain"],
        "enabled_percentage": 100
    }
}

# Middleware check
async def check_feature_flag(request: Request, feature: str):
    yacht_id = request.state.yacht_id
    user_role = request.state.user_role

    config = FEATURE_FLAGS.get(feature, {})

    # Check yacht whitelist
    if yacht_id not in config.get("enabled_yachts", []):
        return False

    # Check role whitelist
    if user_role not in config.get("enabled_roles", []):
        return False

    # Check percentage rollout
    if random.random() * 100 > config.get("enabled_percentage", 0):
        return False

    return True

# Route guard
@router.get("/v1/related")
async def view_related(request: Request, ...):
    if not await check_feature_flag(request, "related_panel_enabled"):
        raise HTTPException(404, detail="Feature not available")
    # ... proceed
```

**Week 2-3: Beta (10 Yachts, A/B Test)**
```python
FEATURE_FLAGS["related_panel_enabled"]["enabled_yachts"] = [
    "yacht-1", "yacht-2", ..., "yacht-10"
]
FEATURE_FLAGS["related_panel_enabled"]["enabled_percentage"] = 50  # A/B test

# Track variant assignment
async def assign_ab_variant(user_id: str, experiment: str) -> str:
    """Consistent variant assignment (sticky sessions)."""
    hash_value = int(hashlib.md5(f"{user_id}:{experiment}".encode()).hexdigest(), 16)
    variant = "control" if hash_value % 2 == 0 else "treatment"

    await db.table("pms_ab_experiments").upsert({
        "user_id": user_id,
        "experiment": experiment,
        "variant": variant,
        "assigned_at": datetime.utcnow()
    }).execute()

    return variant

# Analytics: Compare metrics
"""
SELECT
  variant,
  COUNT(DISTINCT user_id) AS users,
  AVG(session_duration_seconds) AS avg_session_duration,
  SUM(CASE WHEN event_type = 'related_item_clicked' THEN 1 ELSE 0 END) AS clicks
FROM pms_ab_experiments e
JOIN pms_analytics_events a ON a.user_id = e.user_id
WHERE e.experiment = 'related_panel_v1'
GROUP BY variant;
"""
```

**Week 4: General Availability (All Yachts)**
```python
FEATURE_FLAGS["related_panel_enabled"] = {
    "enabled_yachts": "*",  # All yachts
    "enabled_roles": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
    "enabled_percentage": 100
}

# Remove feature flag checks (bake into code)
```

### 10.2 Incident Response Playbook

**Runbook: High Latency (p95 > 500ms)**

1. **Identify Slow Queries**
   ```sql
   -- Check pg_stat_statements for slow queries
   SELECT
     query,
     mean_exec_time,
     calls,
     total_exec_time
   FROM pg_stat_statements
   WHERE query LIKE '%pms_entity_links%' OR query LIKE '%pms_work_orders%'
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. **Check Cache Hit Rate**
   ```bash
   # Redis cache hit rate
   redis-cli info stats | grep cache_hit_rate

   # DB cache hit rate
   SELECT
     sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
   FROM pg_statio_user_tables;
   ```

3. **Temporary Mitigations**
   ```python
   # Reduce query limits
   DEFAULT_LIMIT = 5  # Down from 10

   # Disable embeddings temporarily
   ENABLE_EMBEDDINGS = False

   # Increase cache TTL
   CACHE_TTL = 300  # 5 minutes (up from 60s)
   ```

4. **Long-Term Fixes**
   - Add missing indexes
   - Partition large tables
   - Optimize query plans (rewrite joins)
   - Scale DB vertically (more CPU/RAM)

**Runbook: High Error Rate (> 1%)**

1. **Check Error Distribution**
   ```python
   # View recent errors
   SELECT
     status_code,
     error_message,
     COUNT(*) AS occurrences
   FROM api_error_logs
   WHERE endpoint = '/v1/related' AND created_at > NOW() - INTERVAL '10 minutes'
   GROUP BY status_code, error_message
   ORDER BY occurrences DESC;
   ```

2. **Common Issues**
   - **500 errors:** DB connection pool exhausted → scale up pool size
   - **404 errors:** Entity not found → check if seed data migrated
   - **403 errors:** RLS policy misconfigured → verify JWT claims
   - **409 errors:** Duplicate links → expected, but high rate suggests UI issue

3. **Circuit Breaker**
   ```python
   from circuitbreaker import circuit

   @circuit(failure_threshold=5, recovery_timeout=60)
   async def _query_embedding_similar(...):
       # If embeddings fail 5 times, stop trying for 60s
       # ... implementation
   ```

### 10.3 Data Migration Checklist

**Pre-Migration (Week 0)**
- [ ] Backup production DB
- [ ] Test migrations on staging (exact copy of production)
- [ ] Verify rollback scripts work
- [ ] Schedule maintenance window (low-traffic hours)

**Migration Steps (Week 1)**
```bash
# 1. Create embeddings table
psql -f supabase/migrations/20260128_create_embeddings_table.sql

# 2. Add indexes
psql -f supabase/migrations/20260128_add_performance_indexes.sql

# 3. Add unique constraint (may fail if duplicates exist)
# First, find duplicates:
SELECT yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type, COUNT(*)
FROM pms_entity_links
GROUP BY 1,2,3,4,5,6
HAVING COUNT(*) > 1;

# Deduplicate (keep oldest)
DELETE FROM pms_entity_links a
USING pms_entity_links b
WHERE a.id > b.id
  AND a.yacht_id = b.yacht_id
  AND a.source_entity_type = b.source_entity_type
  AND a.source_entity_id = b.source_entity_id
  AND a.target_entity_type = b.target_entity_type
  AND a.target_entity_id = b.target_entity_id
  AND a.link_type = b.link_type;

# Now add constraint
ALTER TABLE pms_entity_links ADD CONSTRAINT unique_entity_link
  UNIQUE (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type);

# 4. Backfill embeddings (background job)
python scripts/backfill_embeddings.py --batch-size 100 --yacht-id all
```

**Post-Migration Validation**
- [ ] Run Docker tests against production (read-only)
- [ ] Verify zero 500 errors in first hour
- [ ] Check p95 latency < 200ms
- [ ] Monitor error logs for unexpected issues
- [ ] Verify RLS policies active (`SELECT * FROM pg_policies WHERE tablename = 'pms_entity_embeddings'`)

### 10.4 Monitoring Dashboard

**Key Metrics (Grafana)**
```yaml
# Panel 1: Request Rate
- Metric: rate(related_requests_total[5m])
- Breakdown: by entity_type, status_code
- Alert: < 0.1 req/s (feature not being used)

# Panel 2: Latency Distribution
- Metric: histogram_quantile(0.95, related_latency_seconds)
- Breakdown: by entity_type
- Alert: > 0.5s

# Panel 3: Group Sizes
- Metric: avg(related_group_size) by group_key
- Use: Understand which groups are most populated

# Panel 4: Cache Hit Rate
- Metric: rate(cache_hits[5m]) / rate(cache_requests[5m])
- Alert: < 80%

# Panel 5: Error Rate
- Metric: rate(related_requests_total{status_code!="200"}[5m]) / rate(related_requests_total[5m])
- Alert: > 1%

# Panel 6: User Engagement
- Metric: rate(related_item_clicked[1h])
- Use: Track feature adoption

# Panel 7: Embeddings Queue Depth
- Metric: embedding_jobs_pending
- Alert: > 1000 (backlog building up)
```

---

## Part 11: Implementation Timeline (Revised 8-Hour Plan)

Given the depth of this plan, here's a realistic 8-hour timeline:

### Hours 0-1: Deep Planning & Schema Finalization
- ✅ Review this architecture document
- ✅ Finalize DB schema (embeddings table, indexes, constraints)
- ✅ Create migration scripts with rollback plans
- ✅ Set up feature flags infrastructure

### Hours 1-3: Backend Core Implementation
- ✅ Implement embeddings generation pipeline (background worker)
- ✅ Add embeddings similarity query to RelatedHandlers
- ✅ Implement advanced match reasons (text mentions, temporal)
- ✅ Add equipment hierarchy traversal
- ✅ Implement cycle detection for explicit links
- ✅ Add comprehensive error handling (404, 409, 500 → 4xx)

### Hours 3-4.5: Performance Optimization
- ✅ Add covering indexes (from PHASE_8)
- ✅ Implement DataLoader pattern (batch fetching)
- ✅ Add Redis caching layer
- ✅ Optimize query plans (EXPLAIN ANALYZE)
- ✅ Add response compression

### Hours 4.5-6: Testing Deep Dive
- ✅ Unit tests (match reason merging, deduplication)
- ✅ Integration tests (FK queries, equipment hierarchy)
- ✅ Load tests (50 concurrent users)
- ✅ Property-based tests (invariants)
- ✅ Chaos tests (DB timeout, embeddings failure)
- ✅ RLS leak tests (cross-yacht isolation)

### Hours 6-7: Observability & Monitoring
- ✅ Add OpenTelemetry tracing
- ✅ Add Prometheus metrics (latency, error rate, group sizes)
- ✅ Implement user behavior analytics
- ✅ Add relevance feedback collection
- ✅ Set up alerting rules (PagerDuty)
- ✅ Create Grafana dashboard

### Hours 7-8: Frontend Integration & Documentation
- ✅ Create React component with real-time updates
- ✅ Implement optimistic UI updates
- ✅ Add accessibility features (ARIA labels, keyboard nav)
- ✅ Write frontend integration guide
- ✅ Create incident response runbook
- ✅ Document rollout plan (alpha → beta → GA)
- ✅ Prepare demo for stakeholders

---

## Part 12: Success Metrics (Exit Criteria for P1)

### Technical Metrics
- ✅ **Zero 500 errors** in staging CI (10,000 requests)
- ✅ **p95 latency < 200ms** for all entity types
- ✅ **Cache hit rate > 80%** after warm-up
- ✅ **100% RLS coverage** (all queries scoped by yacht_id)
- ✅ **Zero cross-yacht leaks** in security tests
- ✅ **Query performance**: All FK joins < 50ms, embeddings < 100ms

### User Engagement Metrics (Week 4 GA)
- 📊 **Adoption rate**: > 60% of users view related panel at least once per day
- 📊 **Click-through rate**: > 20% of related items clicked
- 📊 **Link creation rate**: > 5 explicit links added per yacht per week (HOD+ users)
- 📊 **Relevance score**: > 70% of feedback is positive (👍)
- 📊 **Time to resolution**: Average work order resolution time decreases by 15% (due to finding relevant info faster)

### Business Metrics (Month 3)
- 💰 **Cost per request**: < $0.001 (embeddings + DB queries)
- 💰 **Infrastructure cost**: No additional servers needed (within existing capacity)
- 💰 **Support tickets**: < 5 bug reports per month
- 💰 **Feature satisfaction**: > 8/10 NPS from HOD+ users

---

## Part 13: Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Embeddings cost too high | Medium | High | Cache embeddings, batch generation, use cheaper model |
| Queries too slow (>500ms) | Medium | High | Add indexes, use materialized views, implement pagination |
| RLS policy misconfiguration | Low | Critical | Automated RLS tests, manual security review, staging validation |
| Equipment hierarchy loops | Low | Medium | Max depth limit (5 levels), cycle detection |
| Cache invalidation bugs | Medium | Medium | Short TTL (60s), conservative invalidation strategy |
| DB connection pool exhaustion | Low | High | Connection pooling (pgBouncer), query timeout limits |
| Embeddings service downtime | Medium | Low | Graceful degradation (FK only), circuit breaker |
| Cross-yacht data leak | Low | Critical | Comprehensive RLS tests, bug bounty program |

---

## Part 14: Open Questions & Future Work

### Open Questions
1. **Embeddings model choice**: text-embedding-3-small vs ada-002 vs open-source?
2. **Similarity threshold**: 0.7 cosine similarity or lower/higher?
3. **Group ordering**: Fixed order (parts → manuals → ...) or dynamic based on counts?
4. **Pagination strategy**: Cursor-based or offset-based?
5. **Real-time updates**: Supabase Realtime or polling? (performance trade-off)

### Future Work (P2+)
- **Hybrid search**: Combine FK + embeddings + text mentions with learned ranking model
- **User personalization**: Show groups most relevant to user's role/history
- **Collaborative filtering**: "Users who viewed this also viewed..."
- **Smart suggestions**: Auto-suggest links based on patterns
- **Graph visualization**: Show entire relationship graph as interactive diagram
- **Export to PDF**: Generate "Related Items Report" for work orders
- **Mobile app**: Offline support, push notifications for related updates
- **Voice interface**: "Alexa, show me related items for work order 123"

---

## Conclusion

This deep architecture plan transforms the P1 scaffolding into a production-ready, scalable, observable system. Key enhancements over basic implementation:

1. **Embeddings pipeline** for semantic similarity (optional P1.5, required P2)
2. **Performance optimization** (indexes, caching, batching) for sub-200ms latency
3. **Advanced match reasons** (text mentions, temporal patterns, user feedback)
4. **Comprehensive testing** (unit, integration, load, property-based, chaos)
5. **Full observability** (tracing, metrics, analytics, alerting)
6. **Production-grade frontend** (real-time, optimistic UI, accessibility)
7. **Phased rollout strategy** (alpha → beta → GA with A/B testing)
8. **Incident response playbook** for operational excellence

**Estimated Total Effort:**
- Core implementation: 8 hours (backend + frontend + tests)
- Embeddings pipeline: +4 hours
- Performance optimization: +2 hours
- Observability: +2 hours
- Documentation: +2 hours
- **Total: ~18 hours** for full production-ready system

**Recommended Approach:**
1. **Week 1**: Implement core P1 (8 hours) - FK joins, basic tests, routes
2. **Week 2**: Add embeddings pipeline (4 hours) - background, no UI yet
3. **Week 3**: Performance + observability (4 hours) - indexes, caching, metrics
4. **Week 4**: Rollout + polish (2 hours) - feature flags, monitoring dashboard

This plan ensures we deliver a robust, scalable, maintainable feature that will serve users well for years to come.

---

**Status:** 🟢 **READY FOR IMPLEMENTATION**
**Next Action:** Review with team, prioritize P1 vs P1.5 features, begin Hour 0 (schema finalization)
