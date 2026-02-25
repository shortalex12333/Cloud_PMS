# F1 Search Pipeline Hardening - Requirements Tracking

## Project Context
- **Supabase Project ID:** vzsohavtuotocgrfkfyd
- **Started:** 2026-02-20
- **Target:** 60% Recall@3 baseline, iterating to 90%+

---

## Phase 1: Database State Verification
**Status:** COMPLETE
**Completed:** 2026-02-20

### Findings:
| Item | Status | Notes |
|------|--------|-------|
| embedding_jobs table | EXISTS | 4700 done, 19 queued |
| search_index table | EXISTS | - |
| Embedding enqueue trigger | NOT INSTALLED | Critical gap |
| Unique constraint | EXISTS | idx_embedding_jobs_unique_object |

### Missing Columns in embedding_jobs:
- [ ] priority (INTEGER)
- [ ] worker_id (TEXT)
- [ ] started_at (TIMESTAMPTZ)
- [ ] completed_at (TIMESTAMPTZ)

### Dead Tables (to drop):
- [ ] action_executions
- [ ] navigation_contexts
- [ ] predictive_state
- [ ] situation_detections
- [ ] suggestion_log
- [ ] symptom_reports

---

## Phase 2: Schema Fixes
**Status:** COMPLETE

### 2a: Add missing columns to embedding_jobs
```sql
ALTER TABLE embedding_jobs ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;
ALTER TABLE embedding_jobs ADD COLUMN IF NOT EXISTS worker_id TEXT;
ALTER TABLE embedding_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE embedding_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
```

### 2b: Install embedding enqueue trigger
- File: supabase/migrations/20260206000007_embedding_enqueue_trigger.sql
- Trigger name: trg_enqueue_embedding_on_search_index
- Covers 17 entity types

### 2c: Drop dead tables
- 6 tables marked for deletion

---

## Phase 3: Worker Verification
**Status:** PENDING

### embedding_worker_1536.py
- [x] Consumes from embedding_jobs table (verified in code)
- [x] Circuit breaker pattern implemented
- [x] MAX_TOKENS truncation (24000 chars)
- [x] DLQ pattern (marks jobs as 'failed')
- [ ] Verify deployment on Render

### Render Deployments:
- embedding-worker: srv-d61l5rfgi27c73cc36gg
- projection-worker: srv-d62i0fu3jp1c73bnul70

---

## Phase 4: Testing
**Status:** PENDING

### Pilot Tests:
- Location: /test/pilot/pilot_test.ts
- Run: `cd apps/web && npx tsx ../../test/pilot/pilot_test.ts`
- Baseline needed before changes

### Current Metrics (from last run):
- Recall@3: 10.49% (34/324 hits)
- Target: 60% minimum

---

## Change Log
| Date | Change | By | Verified |
|------|--------|-----|----------|
| 2026-02-20 | Initial state verification | Claude | Yes |
| 2026-02-20 | Phase 2a: Added columns (priority, worker_id, started_at, completed_at) | Agent | Verified |
| 2026-02-20 | Phase 2b: Installed embedding enqueue trigger (17 entity types) | Agent | Verified |
| 2026-02-20 | Phase 2c: Dropped 6 dead tables | Agent | Verified |
| 2026-02-20 | Phase 3: Trigger fire test passed (19→20 queued jobs) | Agent | Verified |

---

## Rules Enforced:
1. NO assumptions - verify with queries
2. Use sub-agents for parallel work
3. All test files in /test folder only
4. Clean organizational structure
5. Incremental changes with validation
