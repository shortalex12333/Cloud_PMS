# Entity Lens Builder - Anti-Hallucination Operating Procedure

**Status**: LOCKED - Do not modify without review
**Template**: `fault_lens_v5_FINAL.md`

---

## Non-Negotiable Rules

### 1. Every New Lens Must Ship With 3 Artifacts

| Artifact | Source | Purpose |
|----------|--------|---------|
| **DB Truth Snapshot** | `pg_catalog` introspection | Tables, columns, types, nullability, constraints, indexes, triggers, enums, functions, RLS policies |
| **Action Contract Matrix** | Per microaction | REQUIRED / OPTIONAL / CONTEXT / BACKEND_AUTO + exact tables written/read |
| **Diff Report** | Doc vs DB comparison | Mismatches + migration candidates |

> **If any artifact is missing → STOP. Do not proceed.**

---

### 2. No Schema Guessing

- Every table/column/type/nullability/RLS policy MUST be copied from DB snapshot
- If you can't find it in the snapshot, it doesn't exist
- "ACTUAL DEPLOYED" means pasted from introspection, not from migrations

---

### 3. No Invented Helpers

- Any DB function/trigger/policy referenced in SQL MUST appear in snapshot
- If `generate_fault_code()` isn't in `pg_proc`, don't use it
- Mark missing functions as **BLOCKER**

---

### 4. Action Activation Rules

- No actions on search results list unless query contains explicit action intent
- Actions only appear when user focuses a single entity
- Lens actions limited to **max 6** (fewer if lens is read-mostly)

---

### 5. RLS Proof Required

For each microaction that writes:
1. **DB table RLS** must be proven deployed (policy name + cmd)
2. **Storage RLS** must be proven deployed if files involved
3. If either missing → mark as **BLOCKER** → action disabled in UI

---

### 6. Canonical Patterns (Single Source of Truth)

| Pattern | Implementation |
|---------|----------------|
| Yacht isolation | `public.get_user_yacht_id()` ONLY |
| Audit signature | Always present (`{}` when not required) |
| Storage vs DB | Must pass BOTH RLS checks |
| entity_type values | Canonical list only (fault, work_order, note, attachment, equipment, part, inventory_item, shopping_list_item, receiving_event) |

---

## G0 Lens Builder Prompt

Copy/paste this when employing an agent to build a new lens:

```
You are building an Entity Lens for [LENS_NAME].

Read these files first:
1. docs/architecture/entity_lenses/fault_lens_v5_FINAL.md (template doctrine)
2. docs/architecture/entity_lenses/LENS_BUILDER_OPERATING_PROCEDURE.md (this file)
3. Latest DB truth snapshot (run introspection or read existing snapshot)

Non-negotiable rules:
1. No schema guessing. Every table/column/type/nullability/RLS policy must be copied from DB snapshot.
2. No invented helpers. Any referenced DB function/trigger/policy must appear in snapshot.
3. No actions on search results list unless query contains action intent.
4. Lens actions limited (max 6; fewer if lens is read-mostly).
5. For each microaction: include tables read, tables written, field classification, and RLS proof (policy name + cmd).
6. If a required policy doesn't exist → mark as BLOCKER and STOP.

Output required:
1. [lens_name]_lens_vX_DB_GROUNDED.md
2. [lens_name]_lens_vX_DIFF.md listing doc↔DB mismatches and required migrations

Nothing else. No prose. No explanations. Just the artifacts.
```

---

## Required Document Structure

Every lens document MUST follow this structure:

```
# Entity Lens: [Name] (DB-GROUNDED)

# BLOCKERS (if any)
| ID | Blocker | Affects | Resolution |

# PART 0: CANONICAL HELPERS
- Yacht ID Resolution (reference to public.get_user_yacht_id())
- Audit entity_type Convention
- Signature Invariant

# PART 1: EXACT DATABASE SCHEMA
- Per table: columns, types, nullability, classification
- Constraints/doctrines (DELETION, EQUIPMENT, etc.)
- Missing columns + migration status

# PART 2: MICRO-ACTIONS WITH FIELD CLASSIFICATION
- ACTION ACTIVATION DOCTRINE
- Per action:
  - Blocker status (if any)
  - Tables Written/Read
  - Field Classification (REQUIRED/OPTIONAL/CONTEXT/BACKEND_AUTO)
  - Real SQL
  - RLS Proof
  - Ledger UI Event (derived, not table write)

# PART 3: [ENTITY] CREATION FLOW (if applicable)
- Trigger conditions
- Field flow
- Real SQL with blocker annotations

# PART 4: STATUS CASCADE (if applicable)
- Trigger code

# PART 5: RLS POLICIES
- Per table: ACTUAL DEPLOYED vs PROPOSED
- Legacy warnings where applicable
- Storage Bucket Policies (SEPARATE section)
- Policy Gap Summary

# PART 6: [ENTITY] HISTORY QUERY
- Real SQL for common queries

# PART 7: GAPS & MIGRATION STATUS

# PART 8: SUMMARY
- Actions table with blocker status
- Creation flow summary
- Status cascade summary
```

---

## Blocker Resolution Workflow

1. Agent identifies blocker during lens build
2. Blocker added to BLOCKERS section with ID (B1, B2, etc.)
3. Affected action marked with blocker ID
4. Action noted as "disabled in UI"
5. Migration candidate added to DIFF report
6. Human reviews and deploys migration
7. Agent re-introspects DB
8. If blocker resolved → remove from doc, enable action

---

## What Stops Drift

| Control | Why It Works |
|---------|--------------|
| `public.get_user_yacht_id()` ONLY | No competing patterns |
| Signature always present | Downstream code can rely on `{}` check |
| Storage RLS ≠ DB RLS | Forces both checks in upload flow |
| BLOCKER system | No aspirational actions ship |
| 3 artifacts required | Can't ship without proof |

---

**END OF OPERATING PROCEDURE**
