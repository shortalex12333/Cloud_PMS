---
phase: 14-handover-export-editable
plan: "06"
subsystem: api
tags: [python, embedding, search, openai, psycopg2, queue, handover]

requires:
  - phase: 14-05
    provides: countersign endpoint that inserts into search_index_queue

provides:
  - handle_handover_export() handler in embedding worker
  - ENTITY_HANDLERS registry for queue-based entity indexing
  - process_queue_batch() function consuming search_index_queue
  - apps/api/migrations/035_search_index_queue.sql migration
  - build_handover_export_embedding_text() in embedding_text_builder.py
  - handover_exports mapping in projection.yaml
  - Queue integration in main worker loop alongside existing delta embedding

affects:
  - search
  - handover-export

tech-stack:
  added: []
  patterns:
    - "ENTITY_HANDLERS dict: entity_type string maps to handler(entity_id, cur) -> dict"
    - "Queue worker pattern: FOR UPDATE SKIP LOCKED on status=pending for concurrent-safe processing"
    - "JSON field defensive parsing: JSONB fields handled as both dict and str (psycopg2 may return either)"
    - "ProgrammingError catch on queue processing: missing table never crashes main worker loop"

key-files:
  created:
    - apps/api/migrations/035_search_index_queue.sql
  modified:
    - apps/api/workers/embedding_worker_1536.py
    - apps/api/services/embedding_text_builder.py
    - apps/api/config/projection.yaml

key-decisions:
  - "Use psycopg2 cursor (not async Supabase client) for queue handler — matches existing worker architecture"
  - "process_queue_batch() catches ProgrammingError to survive missing search_index_queue table gracefully"
  - "ENTITY_HANDLERS typed as Dict[str, Callable[[str, Any], dict]] for extensibility"
  - "Embedding upsert uses ON CONFLICT(entity_type, entity_id) matching migration UNIQUE constraint"
  - "build_handover_export_embedding_text() added to factory for reuse by projection_worker path"

requirements-completed: []

duration: 10min
completed: 2026-02-18
---

# Phase 14 Plan 06: Embedding Worker Integration Summary

**psycopg2-native queue processor with handle_handover_export() handler that extracts edited_content sections and dual-signature metadata into 1536-dim search embeddings**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-18T16:33:32Z
- **Completed:** 2026-02-18T16:43:32Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `handle_handover_export()` extracts text from `edited_content.sections` and both JSONB signature fields, generates 1536-dim embedding, upserts into `search_index` with ON CONFLICT
- `ENTITY_HANDLERS` dict registers `handover_export` as first queue-based entity type -- extensible for future entity types
- `process_queue_batch()` picks up pending items from `search_index_queue` with FOR UPDATE SKIP LOCKED, marks complete/failed, integrated into main worker loop alongside existing delta embedding loop
- Migration `035_search_index_queue.sql` creates table with status CHECK constraint, UNIQUE(entity_type, entity_id), and partial index on pending rows
- `build_handover_export_embedding_text()` added to embedding_text_builder.py factory (3000 char max)
- `handover_exports` mapping added to projection.yaml with search_text, filters, payload config

## Task Commits

Each task was committed atomically:

1. **Task 1: Add handover export handler + queue processing** - `bf947c92` (feat)
2. **Task 2: Create search_index_queue migration** - `2e6477b0` (chore)
3. **Task 3: Text builder + projection config** - `3b4e07de` (feat)

## Files Created/Modified
- `apps/api/workers/embedding_worker_1536.py` - Added handle_handover_export(), ENTITY_HANDLERS dict, process_queue_batch(), queue integration in main loop
- `apps/api/migrations/035_search_index_queue.sql` - Table definition with constraints and index
- `apps/api/services/embedding_text_builder.py` - Added build_handover_export_embedding_text() and registered in factory
- `apps/api/config/projection.yaml` - Added handover_exports mapping with search_text, filters, payload config

## Decisions Made
- Used psycopg2 cursor instead of async Supabase client: the existing worker is sync psycopg2, introducing a second client library would be architectural scope (Rule 4 threshold). Adapted the plan's async Supabase pattern to sync psycopg2 cursor with the same semantics.
- Wrapped queue processing in ProgrammingError catch so a missing `search_index_queue` table never crashes the main delta-embedding worker loop during staged rollout.
- Defensive JSON parsing for JSONB fields (both dict and str): psycopg2 with RealDictCursor returns JSONB as Python dicts, but string fallback guards against unexpected serialization.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Adaptation] Converted async Supabase client pattern to sync psycopg2**
- **Found during:** Task 1 (implement handle_handover_export)
- **Issue:** Plan specifies `async def handle_handover_export(entity_id, supabase)` using Supabase Python client. The existing worker uses psycopg2 (sync) throughout and has no Supabase client dependency.
- **Fix:** Implemented handler as `def handle_handover_export(entity_id: str, cur)` using psycopg2 cursor. Equivalent semantics — same SQL queries, same upsert logic. process_queue_batch() passes the active cursor instead of a Supabase client.
- **Files modified:** apps/api/workers/embedding_worker_1536.py
- **Verification:** Python AST parses cleanly; function signatures match ENTITY_HANDLERS type annotation
- **Committed in:** bf947c92 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — adaptation to existing tech stack)
**Impact on plan:** Necessary adaptation to avoid introducing async Supabase client into a sync psycopg2 worker. Functional outcome identical: handover exports get indexed from the queue.

## Issues Encountered
None — adaptation was straightforward given the clear precedent set by process_batch().

## User Setup Required
None — migration `28_create_search_index_queue.sql` should be applied to the database via the existing apply_migrations.py script or direct psql connection.

## Next Phase Readiness
- Signed handovers with `review_status='complete'` will now be indexed for semantic search when inserted into `search_index_queue`
- The countersign endpoint (14-05) already inserts into `search_index_queue` via `_trigger_indexing()`
- Migration must be applied before the worker can process queue items (graceful fallback prevents crashes until then)

---
*Phase: 14-handover-export-editable*
*Completed: 2026-02-18*

## Self-Check: PASSED

- FOUND: apps/api/workers/embedding_worker_1536.py (handle_handover_export at line 273)
- FOUND: apps/api/migrations/035_search_index_queue.sql
- FOUND: apps/api/services/embedding_text_builder.py (build_handover_export_embedding_text)
- FOUND: apps/api/config/projection.yaml (handover_exports mapping)
- FOUND commit: bf947c92 feat(14-06): add handover export handler to embedding worker
- FOUND commit: 2e6477b0 chore(14-06): add migration for search_index_queue table
- FOUND commit: 3b4e07de feat(14-06): add handover export indexing support
