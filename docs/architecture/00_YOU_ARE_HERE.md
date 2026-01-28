# 00_YOU_ARE_HERE.md

**Date:** 2026-01-22
**Purpose:** Action count reconciliation and current system state
**Status:** Source of Truth

---

## BUILD TARGET

**We design for 76 canonical actions.**
**We ship what's in the registry (71 actions).**
**We explicitly tag 5 actions as "future" (graph-RAG, certificates).**

**Verification, not implementation, is the gap.**
Only 1/71 actions proven to write to database. Only 4/71 have audit logs. 0/71 have RLS tests.

This is the blocker to production. Architecture design must be built on **what's provable**, not what's aspirational.

---

## EXECUTIVE SUMMARY

**CelesteOS** is a search-first control system for yacht management. Every user interaction flows through:

```
Natural Language Input → Entity Extraction → Situation Analysis → Valid Actions → Risk-Gated Confirmation → Commit + Audit
```

This document reconciles conflicting action counts across documentation, registry, and implementations.

---

## ACTION COUNT RECONCILIATION

### Sources of Truth (Conflicting Claims)

| Source | Count | Location | Date | Notes |
|--------|-------|----------|------|-------|
| **Action Registry** | **71 actions** | `apps/api/actions/action_registry.py` | Current | **PRIMARY SOURCE** - Programmatic definition |
| **Canonical List V2** | 76 actions | `CELESTEOS CANONICAL MICRO-ACTION LIST (V2 — FINAL).md` | 2026-01-14 | 12 clusters, includes 22 "new" actions for RAG/docs |
| **Claude A Orientation** | 64 defined<br/>80 implemented | `REPO_ORIENTATION_STEP2_DEFINITIONS_VS_REALITY.md` | 2026-01-22 | Found 18 undocumented + 2 missing |
| **Handler Implementations** | ~80 handlers | `apps/api/routes/p0_actions_routes.py` + executor | Current | Actual backend implementations |

---

### TRUTH TABLE: Action Status by Source

This table shows which actions exist where:

| Action Status | Count | Notes |
|---------------|-------|-------|
| **In Registry + Implemented** | **71** | ✅ Current production actions |
| **In Canonical List but NOT in Registry** | 5 | ⚠️ Planned actions (documents, certificates, graph-RAG) |
| **Implemented but NOT in Registry** | ~9 | ⚠️ Undocumented handlers (fault lifecycle, equipment CRUD) |
| **In Registry but implementation unclear** | ? | ⚠️ Needs verification |

---

### RECONCILED ACTION LIST

**Production-Ready Actions: 71** (as of 2026-01-22)

These are registered in `action_registry.py` with full metadata (READ/MUTATE classification, domain, entity types, audit requirements).

#### By Domain

| Domain | READ Actions | MUTATE Actions | Total |
|--------|--------------|----------------|-------|
| **inventory** | 5 | 3 | 8 |
| **manual** | 2 | 0 | 2 |
| **equipment** | 4 | 2 | 6 |
| **work_orders** | 3 | 8 | 11 |
| **fault** | 4 | 5 | 9 |
| **handover** | 1 | 5 | 6 |
| **hours_of_rest** | 3 | 1 | 4 |
| **purchasing** | 1 | 7 | 8 |
| **checklists** | 1 | 3 | 4 |
| **shipyard** | 2 | 3 | 5 |
| **fleet** | 3 | 0 | 3 |
| **predictive** | 2 | 0 | 2 |
| **mobile** | 1 | 2 | 3 |
| **TOTAL** | **32** | **39** | **71** |

---

### ACTIONS IN CANONICAL LIST V2 BUT NOT IN REGISTRY (5 actions)

These are planned/aspirational actions from the canonical list that are not yet registered:

1. **trace_related_faults** (Graph-RAG) - Fault relationship tracing
2. **trace_related_equipment** (Graph-RAG) - Equipment dependency tracing
3. **view_linked_entities** (Graph-RAG) - Cross-entity navigation
4. **show_document_graph** (Graph-RAG) - Document relationship visualization
5. **add_certificate** (Compliance) - Certificate management

**Status:** Not blocking. These are future enhancements for graph-RAG and certificate tracking.

---

### ACTIONS IMPLEMENTED BUT NOT IN REGISTRY (Claude A Findings)

Claude A reported 18 undocumented actions in Jan 22 orientation. **Critical finding:** Some of these ARE now in the registry (e.g., `report_fault`, `assign_work_order`, `create_work_order`).

**Likely reconciliation:** Registry was updated after Claude A's scan OR Claude A was comparing against an old catalog file.

**Actions still needing verification:**

| Action | Status | Priority |
|--------|--------|----------|
| `acknowledge_fault` | ⚠️ Handler exists, not in current registry | P0 - Critical fault lifecycle |
| `close_fault` | ⚠️ Handler exists, not in current registry | P0 - Critical fault lifecycle |
| `resolve_fault` | ⚠️ Handler exists, not in current registry | P0 - Critical fault lifecycle |
| `reopen_fault` | ⚠️ Handler exists, not in current registry | P1 - Fault lifecycle edge case |
| `update_fault` | ⚠️ Handler exists, not in current registry | P1 - Fault mutation |
| `mark_fault_false_alarm` | ⚠️ Handler exists, not in current registry | P2 - Fault status |
| `list_faults` | ⚠️ Handler exists, not in current registry | P0 - Critical READ |
| `view_fault_detail` | ⚠️ Handler exists, not in current registry | P0 - Critical READ (may be alias of `view_fault`) |
| `check_stock_level` | ⚠️ Handler exists, not in current registry | P1 - May be alias of `view_stock_levels` |

**Next Step:** Verify if these are true gaps or aliases of registered actions.

---

## VERIFICATION STATUS

### What Claude A Found (2026-01-22)

| Metric | Status | Count |
|--------|--------|-------|
| **HTTP 200 Success** | ✅ 95% | 61/64 tested |
| **Database Mutations Verified** | ❌ **CRITICAL GAP** | 1/64 (1.5%) |
| **Audit Logging Complete** | ❌ **CRITICAL GAP** | 4/64 (6%) |
| **RLS Tested** | ❌ **CRITICAL GAP** | 0/64 (0%) |

**Translation:**
- Actions return HTTP 200 (don't crash)
- Actions likely DO NOT write to database (63/64 unverified)
- Actions DO NOT create audit logs (60/64 missing)
- Cross-yacht data leaks possible (RLS untested)

---

## RISK CLASSIFICATION

CelesteOS uses READ/MUTATE classification, not G0-G3:

| Classification | Count | Requires Signature | Audit Level | Examples |
|----------------|-------|-------------------|-------------|----------|
| **READ** | 32 | No | NONE | view_equipment, view_fault, search_documents |
| **MUTATE (Low Risk)** | ~15 | No | BASIC | add_note, add_photo, tag_for_survey |
| **MUTATE (High Risk)** | ~24 | **Yes** | **FULL** | create_work_order, report_fault, edit_inventory_quantity |

**Guard Rail Notes:**
- **G0-G3 taxonomy is locked** but not directly implemented
- Registry uses `requires_signature` flag for high-risk actions
- Role-based access control exists but enforcement is per-handler (not centralized)

---

## CRITICAL GAPS (From Claude A)

### 1. Database Mutation Verification (P0 - CRITICAL)

**Problem:** Only 1/64 actions proven to write to database.

**Risk:** Actions return HTTP 200 but data may not persist.

**Mitigation:** Verify DB writes for all 39 MUTATE actions (20 hours).

---

### 2. Audit Logging (P0 - COMPLIANCE)

**Problem:** Only 4/64 actions create audit logs.

**Risk:** No forensic trail, compliance violations (ISO 9001, SOLAS).

**Mitigation:** Add audit logging to all 39 MUTATE actions (8 hours).

---

### 3. RLS Testing (P0 - SECURITY)

**Problem:** 0/64 actions tested for row-level security.

**Risk:** Cross-yacht data leaks (User A can see User B's data).

**Mitigation:** Test RLS for 10 most sensitive actions (2 hours).

---

### 4. Undocumented Handlers (P1 - MAINTENANCE)

**Problem:** ~9 handlers exist but not in registry.

**Risk:** Unknown behavior, missing guard rails, no test fixtures.

**Mitigation:** Document role restrictions and expected behavior (4 hours).

---

## WHERE WE ARE

### ✅ What Works

1. **71 actions registered** with full metadata (READ/MUTATE, domains, entity types)
2. **NL→Action pipeline** maps natural language to actions (64/64 tests pass)
3. **JWT validation** enforced (all actions)
4. **Yacht isolation** enforced at application level (all actions)
5. **Two-database model** (MASTER + TENANT) operational
6. **RLS policies** exist on all tables
7. **Test infrastructure** works (E2E, contract tests)

---

### ❌ What Doesn't Work / Unknown

1. **Database mutations unverified** (only 1/71 proven)
2. **Audit logging incomplete** (only 4/71 have logs)
3. **RLS untested** (0/71 actions tested)
4. **~9 undocumented handlers** (fault lifecycle, equipment CRUD)
5. **Status/condition checks** (G2/G3) not centralized
6. **Action counts inconsistent** across docs (64 vs 71 vs 76 vs 80)

---

## NEXT STEPS (Priority Order)

### Phase 1: Layer A Architecture (THIS PHASE - 4 hours)

1. ✅ Create `00_YOU_ARE_HERE.md` (action reconciliation)
2. ⏳ Create `02_GLOBAL_ROUTER_FLOW.md` (core flow definition)
3. ⏳ Create `/08_FLOWCHARTS/global_router.mmd` (mermaid diagram)

### Phase 2: Verification (P0 - 30 hours)

1. **Verify database mutations** for 39 MUTATE actions (20 hours)
2. **Add audit logging** to 39 MUTATE actions (8 hours)
3. **Test RLS** for 10 most sensitive actions (2 hours)

### Phase 3: Layer B - Cluster Flows (P1 - 8 hours)

1. Create cluster flowcharts (faults, work_orders, purchasing, handover)
2. Define happy path / failure path / audit points

### Phase 4: Layer C - Action Cards (P1 - 20 hours)

1. Document "gold set" actions (MUTATE_HIGH + top 10 user journeys)
2. Create action card template (entities, preconditions, reads/writes, success criteria)

---

## ARCHITECTURAL NOTES

### Apple Spotlight Model for Yacht Management

CelesteOS is **NOT** a traditional PMS with modules and dashboards. It is:

**One search bar. No navigation. UI morphs dynamically.**

Traditional yacht software has multiple pages, navigation menus, dashboards. It's a clusterfuck.

CelesteOS: **One page. Dynamically changing based on user's request.**

**Core principle:** Search is passive. Click is commitment.

### Core Flow (4 Stages)

```
1. INPUT
   User types natural language
   ↓
2. ENTITY EXTRACTION + RAG SEARCH
   Extract: equipment, fault, part
   Retrieve: docs, manuals, data (Supabase vector)
   ↓
3. USER CLICKS RESULT → SITUATION ACTIVATES
   Click inventory → Inventory View
   Click document → Document Viewer
   Click work order → WO Detail
   ↓
4. MICRO-ACTIONS APPEAR (Context-filtered)
   Primary buttons (max 3) + Dropdown
   User clicks → Confirm → Commit
```

### Domain Situations (Defined)

**Situation** = which domain view is currently active. UI morphs completely.

| Situation | Activates When | Primary Actions |
|-----------|----------------|-----------------|
| **Equipment** | Click equipment result | View History, Show Manual, Create WO |
| **Document** | Click manual/doc | Open Viewer, Add to Handover |
| **Inventory** | Click inventory item | View Stock, Adjust Quantity, View Location |
| **Work Order** | Click WO result | View Details, Add Note, Mark Complete |
| **Fault** | Click fault result | Diagnose, Create WO, Add to Handover |

**Situation State Machine:** IDLE → CANDIDATE (clicked) → ACTIVE (opened detail/manual/history)

**Evidence tracking (deterministic):**
- `opened_manual` (ACTIVE trigger)
- `viewed_history` (ACTIVE trigger)
- `mutation_committed` (ACTIVE + suppress nudges)

**NOT defined for MVP:** "At sea", "in port", "shipyard" operational modes. Future environment-based filtering.

---

## DOCUMENT LINEAGE

- **Claude A Orientation**: 7 docs created (2026-01-22), identified 64→80 gap
- **Canonical List V2**: 76 actions across 12 clusters (2026-01-14)
- **This Document**: Reconciles all sources, establishes 71 as current truth

---

**Status:** Truth reconciled. Action count is **71 in registry, ~80 implemented, 76 canonical**.

**Critical Finding:** Verification gap is real (1.5% DB mutations verified, 6% audit logging). This is the blocker to production, not action count.

**Next:** Define global router flow in `02_GLOBAL_ROUTER_FLOW.md`.
