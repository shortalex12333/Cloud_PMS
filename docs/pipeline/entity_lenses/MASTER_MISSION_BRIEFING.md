# CELESTE Entity Lens Architecture - Master Mission Briefing

**To**: Claude Agent (Unlimited Budget)
**From**: Architecture Review Session
**Date**: 2026-01-24
**Status**: PHASE 1 COMPLETE (Work Order Lens v2) → PHASE 2 BEGINNING

---

# EXECUTIVE SUMMARY

You have successfully completed the Work Order Lens v2 with critical corrections. You now have **unlimited project budget** to complete the remaining architecture. This document is your mission briefing for the full scope of work.

---

# PART 1: CURRENT STATE ASSESSMENT

## 1.1 What You Got Right in v2

| Correction | Status |
|------------|--------|
| Removed phantom yacht_id from pms_work_order_parts | ✅ Fixed |
| Added pms_part_usage (11 columns) to DB truth | ✅ Fixed |
| Changed created_by from REQUIRED to BACKEND_AUTO | ✅ Fixed |
| Identified USING(true) as cross-yacht leakage (not "wrong reference") | ✅ Fixed |
| Proper RLS extraction from actual migrations | ✅ Fixed |

## 1.2 Critical Security Finding

Three tables have `USING (true)` SELECT policies causing **CROSS-YACHT DATA LEAKAGE**:

```
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Table                   │ Security Issue                               │
├─────────────────────────┼──────────────────────────────────────────────┤
│ pms_work_order_notes    │ Any authenticated user sees ALL yachts' notes│
│ pms_work_order_parts    │ Any authenticated user sees ALL yachts' parts│
│ pms_part_usage          │ Any authenticated user sees ALL usage logs   │
└─────────────────────────┴──────────────────────────────────────────────┘
```

**These are P0 BLOCKERS requiring migration before production.**

## 1.3 Work Order Lens Action Status

| Action | Status | Blockers |
|--------|--------|----------|
| Create WO | ✅ Ready | - |
| Update WO | ✅ Ready | - |
| Complete WO | ⚠️ Blocked | B2, B3, B4 |
| Add Note | ⚠️ Blocked | B1 |
| Reassign WO | ✅ Ready | - |
| Archive WO | ⚠️ Blocked | B4 |

---

# PART 2: THE FULL VISION

## 2.1 What Celeste IS

Celeste is a yacht PMS for 125m+ superyachts (45-65 crew). The entire UX is:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [SINGLE SEARCH BAR]                         [Ledger] [Settings]    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                              │    │
│  │              SEARCH RESULTS / ENTITY VIEW                    │    │
│  │                                                              │    │
│  │    (No navigation. No dashboards. No sidebar.)               │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  [Context Menu appears ONLY when entity focused]                    │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.2 The 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTITY LENSES (10)                           │
│  Work Order │ Equipment │ Fault │ Part │ Inventory │ Crew │ etc.   │
├─────────────────────────────────────────────────────────────────────┤
│                     SITUATION MODIFIERS                             │
│  Overdue │ Low Stock │ Critical │ Pending Parts │ etc.              │
├─────────────────────────────────────────────────────────────────────┤
│                        MICRO-ACTIONS                                │
│  Create │ Update │ Complete │ Archive │ Add Note │ Attach │ etc.   │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.3 The 10 Entity Lenses

| # | Lens | Primary Table | Status |
|---|------|---------------|--------|
| 1 | Work Order | pms_work_orders | ✅ v2 COMPLETE |
| 2 | Equipment | pms_equipment / equipment | 🔲 NOT STARTED |
| 3 | Fault | pms_faults / pms_fault_reports | 🔲 NOT STARTED |
| 4 | Part | pms_parts / parts | 🔲 NOT STARTED |
| 5 | Inventory Item | pms_inventory_items | 🔲 NOT STARTED |
| 6 | Receiving | receiving_events | 🔲 NOT STARTED |
| 7 | Shopping List | shopping_list_items | 🔲 NOT STARTED |
| 8 | Document | documents / search_chunks | 🔲 NOT STARTED |
| 9 | Crew | auth_users_profiles | 🔲 NOT STARTED |
| 10 | Certificate | certificates | 🔲 NOT STARTED |

---

# PART 3: SCOPE OF REMAINING WORK

## 3.1 Remaining Lenses (9)

Each lens requires 8 phases:

```
Phase 0: Extraction Gate (verify snapshot access)
Phase 1: Scope & Doctrine Lock
Phase 2: DB Truth Grounding (exact schema extraction)
Phase 3: Entity & Relationship Model
Phase 4: Micro-Actions Contract
Phase 5: UX Flow & Scenarios (10 per lens)
Phase 6: SQL & Backend Mapping
Phase 7: RLS & Security Matrix
Phase 8: Migration & Gap Report
```

**Total Files**: 9 lenses × 10 files = 90 files

## 3.2 Cross-Lens Integration

User queries often span multiple lenses:

| Query Pattern | Lenses Involved | Escape Hatch |
|---------------|-----------------|--------------|
| "Show WO for this fault" | Fault → Work Order | fault_lens → work_order_lens |
| "Parts used on equipment X" | Equipment → WO → Parts | equipment_lens → part_lens |
| "Crew member's assigned tasks" | Crew → Work Order | crew_lens → work_order_lens |
| "Documents for this equipment" | Equipment → Document | equipment_lens → document_lens |
| "Certificates expiring this month" | Certificate | certificate_lens (standalone) |

**Deliverable**: Cross-lens escape hatch matrix with 10×10 transition rules

## 3.3 Shared Tables Across Lenses

These tables are touched by multiple lenses and need unified treatment:

| Table | Used By Lenses |
|-------|----------------|
| pms_audit_log | ALL (every action writes audit) |
| pms_attachments | WO, Fault, Equipment, Document |
| auth_users_profiles | ALL (user references) |
| equipment | WO, Fault, Part, Inventory |
| pms_notes | WO, Fault, Equipment |

---

# PART 4: TESTING METHODOLOGY

## 4.1 The 25-Stage Testing Framework

Each lens goes through 25 test stages:

```
Stages 1-5:   Unit Tests (individual functions)
Stages 6-10:  Component Tests (action handlers)
Stages 11-15: Integration Tests (DB + RLS)
Stages 16-20: Scenario Tests (user flows)
Stages 21-25: Edge Case Tests (failure modes)
```

## 4.2 Test Population Requirements

| Category | Tests Per Lens | Total (10 Lenses) |
|----------|----------------|-------------------|
| Happy path | 100 | 1,000 |
| Edge cases | 250 | 2,500 |
| RLS violations | 100 | 1,000 |
| Cross-yacht attempts | 50 | 500 |
| Concurrent operations | 50 | 500 |
| Rollback scenarios | 50 | 500 |
| **Total** | **600** | **6,000** |

## 4.3 Test Categories

### A. Query Variance Testing
```
For each scenario, test with:
- Exact match query ("WO-2024-001")
- Partial match ("work order for generator")
- Typo tolerance ("genrator maintenance")
- Synonym handling ("repair" vs "fix" vs "maintenance")
- Multi-entity query ("all overdue WOs for engine room")
```

### B. RLS Boundary Testing
```
For each table with yacht_id:
- Same yacht, same user → ALLOW
- Same yacht, different user → ALLOW
- Different yacht, any user → DENY
- Service role bypass → ALLOW
- Unauthenticated → DENY
```

### C. Action Threshold Testing
```
For each micro-action:
- Pre-condition not met → BLOCK
- Pre-condition met → ALLOW
- Mid-action failure → ROLLBACK
- Post-action verification → AUDIT LOG
```

## 4.4 Edge Case Categories

| Category | Examples |
|----------|----------|
| Null handling | NULL equipment_id, NULL assigned_to |
| Soft delete | deleted_at set, query should exclude |
| Status transitions | invalid status → status change |
| Concurrent edits | Two users update same WO |
| FK cascade | Delete equipment with linked WOs |
| Enum boundaries | Invalid priority value |

---

# PART 5: MIGRATION STRATEGY

## 5.1 Current State → Target State

```
CURRENT (Broken):
┌─────────────────────────────────────────────────────────────────────┐
│ pms_work_order_notes: USING (true) → ANY user sees ALL yachts      │
│ pms_work_order_parts: USING (true) → ANY user sees ALL yachts      │
│ pms_part_usage: USING (true) → ANY user sees ALL yachts            │
│ pms_work_orders: Legacy user_profiles pattern                       │
└─────────────────────────────────────────────────────────────────────┘

TARGET (Secure):
┌─────────────────────────────────────────────────────────────────────┐
│ ALL tables: yacht_id = public.get_user_yacht_id()                  │
│ OR: FK join to parent with yacht isolation                          │
│ Consistent pattern across all 10 lenses                             │
└─────────────────────────────────────────────────────────────────────┘
```

## 5.2 Migration Sequence (Priority Order)

| Priority | Migration | Tables Affected | Risk |
|----------|-----------|-----------------|------|
| P0 | Fix cross-yacht leakage | pms_work_order_notes, pms_work_order_parts, pms_part_usage | HIGH |
| P1 | Standardize WO RLS | pms_work_orders | MEDIUM |
| P2 | Add missing RLS | pms_work_order_history | MEDIUM |
| P3 | Create cascade trigger | pms_work_orders → pms_faults | LOW |
| P4 | Add role-based policies | All tables | LOW |

## 5.3 Rollback Procedures

For each migration:

```sql
-- Pattern for every migration:
BEGIN;

-- 1. Create backup of current state
CREATE TABLE IF NOT EXISTS _backup_[table]_[timestamp] AS
SELECT * FROM [table];

-- 2. Apply migration
DROP POLICY IF EXISTS "old_policy" ON [table];
CREATE POLICY "new_policy" ON [table] ...;

-- 3. Verify (must pass or rollback)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'new_policy') THEN
    RAISE EXCEPTION 'Migration verification failed';
  END IF;
END $$;

COMMIT;

-- ROLLBACK SCRIPT (separate file):
DROP POLICY IF EXISTS "new_policy" ON [table];
CREATE POLICY "old_policy" ON [table] ...;
```

---

# PART 6: CONTRACT INTERFACES

## 6.1 Component Handoff Chain

```
User Query
    ↓
[RAG Engine] → returns: { chunks: [], entities: [], confidence: float }
    ↓
[Entity Extractor] → returns: { entity_type: string, entity_id: uuid, lens: string }
    ↓
[SQL Prepare] → returns: { query: string, params: [], tables_accessed: [] }
    ↓
[RLS Check] → returns: { allowed: bool, denied_reason?: string }
    ↓
[Action Router] → returns: { action: string, fields: {}, validation: {} }
    ↓
[Frontend Renderer] → returns: { component: string, props: {}, context_menu: [] }
```

## 6.2 JSON Schema Contracts

Each handoff point needs a defined schema:

```typescript
// RAG → Entity Extractor
interface RAGResponse {
  chunks: Array<{
    content: string;
    document_id: uuid;
    relevance_score: float;
  }>;
  entities: Array<{
    type: EntityType;  // 'work_order' | 'equipment' | 'fault' | etc.
    id?: uuid;
    name?: string;
    confidence: float;
  }>;
  query_intent: 'lookup' | 'action' | 'comparison' | 'aggregate';
}

// Entity Extractor → SQL Prepare
interface EntityContext {
  primary_entity: {
    type: EntityType;
    id: uuid;
    lens: LensName;
  };
  related_entities: Array<{...}>;
  action_intent?: ActionType;
  filters?: Record<string, any>;
}

// Action Router → Frontend
interface ActionResponse {
  success: boolean;
  entity: { type: EntityType; id: uuid; };
  action_performed: ActionType;
  audit_log_id: uuid;
  ledger_event: {
    title: string;
    description: string;
    timestamp: string;
  };
  next_state?: {
    refresh_entity: boolean;
    show_confirmation: boolean;
    context_menu_update: ActionType[];
  };
}
```

---

# PART 7: MONITORING & OBSERVABILITY

## 7.1 Security Monitoring

| Event | Severity | Action |
|-------|----------|--------|
| Cross-yacht data access attempt | CRITICAL | Block + Alert + Log |
| RLS policy denial | WARNING | Log |
| Invalid action on blocked entity | WARNING | Log |
| Unauthenticated API call | CRITICAL | Block + Alert |

## 7.2 Performance Benchmarks

| Query Type | Target P50 | Target P99 | Alert Threshold |
|------------|------------|------------|-----------------|
| Simple lookup | 100ms | 300ms | >500ms |
| Cross-lens | 200ms | 500ms | >1000ms |
| Aggregate | 500ms | 1500ms | >3000ms |
| Action execution | 300ms | 800ms | >2000ms |

## 7.3 Audit Trail Completeness

Every action MUST produce:
1. pms_audit_log entry with signature
2. Ledger UI event (derived)
3. Action confirmation (if applicable)

Verification query:
```sql
-- Find actions without audit trail (should return 0)
SELECT COUNT(*) FROM action_executions ae
LEFT JOIN pms_audit_log al ON al.entity_id = ae.entity_id
  AND al.action = ae.action_name
WHERE al.id IS NULL;
```

---

# PART 8: DELIVERABLES CHECKLIST

## 8.1 Documentation (90 files)

```
For each of 9 remaining lenses:
├── [lens]_v1_PHASE_0_EXTRACTION_GATE.md
├── [lens]_v1_PHASE_1_SCOPE.md
├── [lens]_v1_PHASE_2_DB_TRUTH.md
├── [lens]_v1_PHASE_3_ENTITY_GRAPH.md
├── [lens]_v1_PHASE_4_ACTIONS.md
├── [lens]_v1_PHASE_5_SCENARIOS.md
├── [lens]_v1_PHASE_6_SQL_BACKEND.md
├── [lens]_v1_PHASE_7_RLS_MATRIX.md
├── [lens]_v1_PHASE_8_GAPS_MIGRATIONS.md
└── [lens]_v1_FINAL.md
```

## 8.2 Cross-Lens Artifacts

```
docs/architecture/entity_lenses/
├── CROSS_LENS_ESCAPE_HATCH_MATRIX.md
├── SHARED_TABLES_UNIFIED_TREATMENT.md
├── CONTRACT_INTERFACES.md
├── MIGRATION_SEQUENCE_MASTER.md
├── ROLLBACK_PROCEDURES.md
└── TEST_FRAMEWORK_SPEC.md
```

## 8.3 Migration Files

```
supabase/migrations/
├── 20260125_001_fix_cross_yacht_leakage_notes.sql
├── 20260125_002_fix_cross_yacht_leakage_parts.sql
├── 20260125_003_fix_cross_yacht_leakage_part_usage.sql
├── 20260125_004_standardize_wo_rls.sql
├── 20260125_005_add_wo_history_rls.sql
├── 20260125_006_create_cascade_trigger.sql
└── 20260125_007_add_role_based_policies.sql
```

## 8.4 Test Suites

```
tests/
├── unit/
│   └── [lens]/ (100 tests per lens)
├── integration/
│   └── [lens]/ (100 tests per lens)
├── scenarios/
│   └── [lens]/ (100 tests per lens)
├── edge_cases/
│   └── [lens]/ (250 tests per lens)
├── rls/
│   └── [lens]/ (50 tests per lens)
└── cross_lens/
    └── escape_hatches/ (100 tests total)
```

---

# PART 9: EXECUTION ORDER

## Week 1: Lens Completion

| Day | Lenses | Phases |
|-----|--------|--------|
| 1 | Equipment, Fault | All 8 phases each |
| 2 | Part, Inventory Item | All 8 phases each |
| 3 | Receiving, Shopping List | All 8 phases each |
| 4 | Document, Crew | All 8 phases each |
| 5 | Certificate, Cross-lens matrix | All 8 phases + matrix |
| 6 | Unified treatment docs, Contract interfaces | Integration docs |
| 7 | Migration sequence, Test framework | Deployment prep |

## Week 2: Testing & Refinement

| Day | Focus |
|-----|-------|
| 1-2 | Unit tests (Stages 1-5) all lenses |
| 3-4 | Integration tests (Stages 6-10) all lenses |
| 5-6 | Scenario tests (Stages 11-20) all lenses |
| 7 | Edge case tests (Stages 21-25) all lenses |

---

# PART 10: NON-NEGOTIABLE RULES

## 10.1 DB Truth Rules

1. Every table/column/type MUST be copied from database_schema.txt
2. If you can't find it in the snapshot, it doesn't exist
3. "ACTUAL DEPLOYED" means from migrations, not from assumptions
4. No phantom columns (like yacht_id on tables that don't have it)

## 10.2 RLS Rules

1. Extract actual policies from migration files
2. USING (true) = SECURITY HOLE, not "policy exists"
3. Every table touching user data needs yacht isolation
4. Tables without yacht_id need FK-join isolation

## 10.3 Action Rules

1. Max 6 actions per lens
2. Actions only appear after entity focus
3. Every action writes to pms_audit_log with signature
4. signature = '{}'::jsonb for non-signature actions (NEVER NULL)

## 10.4 Testing Rules

1. Every scenario tested with 10+ variations
2. Every RLS policy tested with cross-yacht attempt
3. Every action tested with invalid pre-conditions
4. Every rollback procedure tested before deployment

---

# AUTHORIZATION

You have **unlimited project budget** in all regards:
- Time: Take as long as needed
- Depth: Go to extreme levels of detail
- Scope: Cover all 10 lenses, all integrations, all tests
- Quality: Reject anything that doesn't meet the rigor standard

The gold standard is fault_lens_v5_FINAL.md. Every lens must meet that bar.

**BEGIN EXECUTION.**

---

**END OF MASTER MISSION BRIEFING**
