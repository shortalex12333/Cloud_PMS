# Phase Checklist Master

**Purpose**: Granular task tracking for each phase across all lenses
**Format**: Matches screenshot checklist pattern (PHASE X.Y: Task)

---

## LENS: [NAME] - Full Checklist

### PHASE 0: Pre-Flight
```
[ ] PHASE 0.1: Confirm db_truth_snapshot available
[ ] PHASE 0.2: Confirm fault_lens_v5_FINAL.md read
[ ] PHASE 0.3: Confirm LENS_BUILDER_OPERATING_PROCEDURE.md read
[ ] PHASE 0.4: Confirm migrations folder accessible
[ ] PHASE 0.5: Confirm RLS policies extractable
[ ] PHASE 0.6: Acknowledge GLOBAL RULES
[ ] PHASE 0.7: **GATE: All inputs confirmed**
```

### PHASE 1: Scope & Doctrine Lock
```
[ ] PHASE 1.1: Define what lens IS
[ ] PHASE 1.2: Define what lens is NOT
[ ] PHASE 1.3: Classify (Read-only / Write-through / Operational)
[ ] PHASE 1.4: Define allowed query patterns
[ ] PHASE 1.5: Define forbidden query patterns
[ ] PHASE 1.6: Define escape hatches
[ ] PHASE 1.7: Write doctrine statement
[ ] PHASE 1.8: Review for dashboard/button leaks
[ ] PHASE 1.9: **GATE: Scope frozen**
```

### PHASE 2: DB Truth Grounding
```
[ ] PHASE 2.1: List primary table (from snapshot)
[ ] PHASE 2.2: List secondary tables (from snapshot)
[ ] PHASE 2.3: Extract all columns with types
[ ] PHASE 2.4: Extract nullable flags
[ ] PHASE 2.5: Extract default values
[ ] PHASE 2.6: Extract CHECK constraints
[ ] PHASE 2.7: Extract FK constraints
[ ] PHASE 2.8: Extract UNIQUE constraints
[ ] PHASE 2.9: Extract triggers
[ ] PHASE 2.10: Extract enums used
[ ] PHASE 2.11: Extract ACTUAL DEPLOYED RLS (SELECT)
[ ] PHASE 2.12: Extract ACTUAL DEPLOYED RLS (INSERT)
[ ] PHASE 2.13: Extract ACTUAL DEPLOYED RLS (UPDATE)
[ ] PHASE 2.14: Extract ACTUAL DEPLOYED RLS (DELETE)
[ ] PHASE 2.15: Build Doc vs DB diff table
[ ] PHASE 2.16: Flag BLOCKERs for missing RLS
[ ] PHASE 2.17: **GATE: All schema from snapshot only**
```

### PHASE 3: Entity & Relationship Model
```
[ ] PHASE 3.1: Define primary entity
[ ] PHASE 3.2: Define secondary entities (list)
[ ] PHASE 3.3: Map FK path 1
[ ] PHASE 3.4: Map FK path 2
[ ] PHASE 3.5: Map FK path 3 (if any)
[ ] PHASE 3.6: Verify no inferred joins
[ ] PHASE 3.7: Verify no vector joins
[ ] PHASE 3.8: Draw textual ER diagram
[ ] PHASE 3.9: Define allowed traversals
[ ] PHASE 3.10: Define forbidden traversals
[ ] PHASE 3.11: **GATE: All relationships in schema**
```

### PHASE 4: Micro-Actions Contract
```
[ ] PHASE 4.1: List candidate actions (max 6)
[ ] PHASE 4.2: Action 1 - intent phrasing
[ ] PHASE 4.3: Action 1 - trigger condition
[ ] PHASE 4.4: Action 1 - tables read
[ ] PHASE 4.5: Action 1 - tables written
[ ] PHASE 4.6: Action 1 - field classification
[ ] PHASE 4.7: Action 1 - signature req
[ ] PHASE 4.8: Action 1 - RLS proof
[ ] PHASE 4.9: Action 2 - intent phrasing
[ ] PHASE 4.10: Action 2 - trigger condition
[ ] PHASE 4.11: Action 2 - tables read
[ ] PHASE 4.12: Action 2 - tables written
[ ] PHASE 4.13: Action 2 - field classification
[ ] PHASE 4.14: Action 2 - signature req
[ ] PHASE 4.15: Action 2 - RLS proof
[ ] PHASE 4.16: Action 3 - (repeat pattern if exists)
[ ] PHASE 4.17: Action 4 - (repeat pattern if exists)
[ ] PHASE 4.18: Action 5 - (repeat pattern if exists)
[ ] PHASE 4.19: Action 6 - (repeat pattern if exists)
[ ] PHASE 4.20: Remove actions without RLS proof
[ ] PHASE 4.21: **GATE: All actions have RLS proof**
```

### PHASE 5: UX Flow & Scenarios
```
[ ] PHASE 5.1: Scenario 1 - Basic Lookup
[ ] PHASE 5.2: Scenario 1 - Traditional flow
[ ] PHASE 5.3: Scenario 1 - Celeste flow
[ ] PHASE 5.4: Scenario 1 - Verification checklist
[ ] PHASE 5.5: Scenario 2 - Status Check
[ ] PHASE 5.6: Scenario 2 - Traditional flow
[ ] PHASE 5.7: Scenario 2 - Celeste flow
[ ] PHASE 5.8: Scenario 2 - Verification checklist
[ ] PHASE 5.9: Scenario 3 - History Query
[ ] PHASE 5.10: Scenario 3 - flows + verification
[ ] PHASE 5.11: Scenario 4 - Related Items
[ ] PHASE 5.12: Scenario 4 - flows + verification
[ ] PHASE 5.13: Scenario 5 - Action Intent (Primary)
[ ] PHASE 5.14: Scenario 5 - flows + verification
[ ] PHASE 5.15: Scenario 6 - Action Intent (Secondary)
[ ] PHASE 5.16: Scenario 6 - flows + verification
[ ] PHASE 5.17: Scenario 7 - Comparison/Multiple
[ ] PHASE 5.18: Scenario 7 - flows + verification
[ ] PHASE 5.19: Scenario 8 - Alert/Exception
[ ] PHASE 5.20: Scenario 8 - flows + verification
[ ] PHASE 5.21: Scenario 9 - Cross-Lens Navigation
[ ] PHASE 5.22: Scenario 9 - flows + verification
[ ] PHASE 5.23: Scenario 10 - Edge Case
[ ] PHASE 5.24: Scenario 10 - flows + verification
[ ] PHASE 5.25: Verify no ambient buttons (all scenarios)
[ ] PHASE 5.26: Verify no dashboards (all scenarios)
[ ] PHASE 5.27: **GATE: All scenarios query-first**
```

### PHASE 6: SQL & Backend Mapping
```
[ ] PHASE 6.1: Action 1 - SELECT queries
[ ] PHASE 6.2: Action 1 - INSERT/UPDATE queries
[ ] PHASE 6.3: Action 1 - triggers involved
[ ] PHASE 6.4: Action 1 - functions involved
[ ] PHASE 6.5: Action 1 - verify functions exist
[ ] PHASE 6.6: Action 1 - transaction boundary
[ ] PHASE 6.7: Action 2 - SELECT queries
[ ] PHASE 6.8: Action 2 - INSERT/UPDATE queries
[ ] PHASE 6.9: Action 2 - triggers + functions
[ ] PHASE 6.10: Action 2 - verify functions exist
[ ] PHASE 6.11: (repeat for remaining actions)
[ ] PHASE 6.12: Label all hypothetical SQL
[ ] PHASE 6.13: **GATE: All SQL uses existing functions**
```

### PHASE 7: RLS & Security Matrix
```
[ ] PHASE 7.1: Build Role × Action matrix
[ ] PHASE 7.2: Row 1 - deckhand permissions
[ ] PHASE 7.3: Row 2 - steward permissions
[ ] PHASE 7.4: Row 3 - engineer permissions
[ ] PHASE 7.5: Row 4 - chief_engineer permissions
[ ] PHASE 7.6: Row 5 - captain permissions
[ ] PHASE 7.7: Document table-level RLS proof
[ ] PHASE 7.8: Document storage bucket (if applicable)
[ ] PHASE 7.9: Storage bucket - read policy
[ ] PHASE 7.10: Storage bucket - write policy
[ ] PHASE 7.11: Storage bucket - delete policy
[ ] PHASE 7.12: Document explicit deny cases
[ ] PHASE 7.13: Verify storage + DB RLS documented
[ ] PHASE 7.14: **GATE: Security matrix complete**
```

### PHASE 8: Migration & Gap Report
```
[ ] PHASE 8.1: List missing columns
[ ] PHASE 8.2: List missing indexes
[ ] PHASE 8.3: List missing RLS policies
[ ] PHASE 8.4: List unsafe existing policies
[ ] PHASE 8.5: List deprecated legacy fields
[ ] PHASE 8.6: Gap 1 - risk assessment
[ ] PHASE 8.7: Gap 1 - proposed migration SQL
[ ] PHASE 8.8: Gap 1 - blocking vs optional
[ ] PHASE 8.9: (repeat for all gaps)
[ ] PHASE 8.10: Compile DIFF report
[ ] PHASE 8.11: **GATE: All gaps have migration plan**
```

### FINAL GATE
```
[ ] FINAL.1: All 8 phases complete
[ ] FINAL.2: All BLOCKERs documented
[ ] FINAL.3: No invented functions
[ ] FINAL.4: No dashboard/button assumptions
[ ] FINAL.5: No severity inference
[ ] FINAL.6: No storage assumptions
[ ] FINAL.7: Compile final lens document
[ ] FINAL.8: Human review
[ ] FINAL.9: **LENS FROZEN**
```

---

## Cross-Reference Checks (run after each phase)

### Spelling/Naming Consistency
```
[ ] Table names match snapshot exactly
[ ] Column names match snapshot exactly
[ ] Function names match snapshot exactly
[ ] Policy names match snapshot exactly
[ ] Enum values match snapshot exactly
```

### Doctrine Consistency
```
[ ] No "dashboard" word anywhere
[ ] No "button" without focus context
[ ] No "navigate to" language
[ ] No "system suggests" language
[ ] All severity is user-provided
[ ] All signature is present ({} when not required)
[ ] yacht_id uses public.get_user_yacht_id() only
```

### SQL Consistency
```
[ ] All INSERTs include signature column
[ ] All INSERTs include yacht_id from function
[ ] All entity_type values from canonical list
[ ] No NULL for NOT NULL columns
[ ] All functions exist in snapshot
```

---

## Output Files Per Lens

```
[lens_name]_lens_PHASE_1_SCOPE.md
[lens_name]_lens_PHASE_2_DB_TRUTH.md
[lens_name]_lens_PHASE_3_ENTITY_GRAPH.md
[lens_name]_lens_PHASE_4_ACTIONS.md
[lens_name]_lens_PHASE_5_SCENARIOS.md
[lens_name]_lens_PHASE_6_SQL_AND_BACKEND.md
[lens_name]_lens_PHASE_7_RLS_MATRIX.md
[lens_name]_lens_PHASE_8_GAPS_AND_MIGRATIONS.md
[lens_name]_lens_vX_FINAL.md (compiled from all phases)
[lens_name]_lens_vX_DIFF.md (gap summary)
```

---

**END OF CHECKLIST MASTER**
