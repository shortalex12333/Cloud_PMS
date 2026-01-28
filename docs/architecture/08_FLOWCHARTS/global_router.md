# Global Router Flow - Mermaid Diagram

**Date:** 2026-01-22
**Purpose:** Visual flowchart of CelesteOS control flow (Apple Spotlight model)
**Status:** Layer A - Core Architecture

---

## Flow Diagram

```mermaid
flowchart TD
    Start([User types in search bar]) --> Extract[Stage 1+2: EXTRACTION + RAG<br/>Entity extraction: equipment, fault, part<br/>RAG search: docs, manuals, data<br/>Return grouped results]

    Extract --> SearchResults[Search Results Displayed<br/>Equipment / Documents / WO / Faults<br/>NO ACTIONS<br/>Passive only]

    SearchResults --> UserClick{User<br/>clicks<br/>result?}

    UserClick -->|No| Idle([IDLE - stays on search])

    UserClick -->|Yes - Equipment| EquipSit[Stage 3: EQUIPMENT SITUATION<br/>CANDIDATE → ACTIVE<br/>when views history/manual]

    UserClick -->|Yes - Document| DocSit[Stage 3: DOCUMENT SITUATION<br/>CANDIDATE → ACTIVE<br/>when opens viewer]

    UserClick -->|Yes - Inventory| InvSit[Stage 3: INVENTORY SITUATION<br/>CANDIDATE → ACTIVE<br/>when views detail]

    UserClick -->|Yes - WO| WOSit[Stage 3: WORK ORDER SITUATION<br/>CANDIDATE → ACTIVE<br/>when opens detail]

    UserClick -->|Yes - Fault| FaultSit[Stage 3: FAULT SITUATION<br/>CANDIDATE → ACTIVE<br/>when opens detail]

    EquipSit --> EquipActions[Stage 4: MICRO-ACTIONS<br/>Primary: Show Manual, View Faults, Create WO<br/>Dropdown: View History, Add Note, etc.]

    DocSit --> DocActions[Stage 4: MICRO-ACTIONS<br/>Primary: Open Viewer, Add to Handover<br/>Dropdown: Link to Equipment, Summarize]

    InvSit --> InvActions[Stage 4: MICRO-ACTIONS<br/>Primary: View Stock, Adjust Qty, View Location<br/>Dropdown: Add to Handover, Reorder]

    WOSit --> WOActions[Stage 4: MICRO-ACTIONS<br/>Primary: View Details, Add Note, Mark Complete<br/>Dropdown: Add Parts, Assign]

    FaultSit --> FaultActions[Stage 4: MICRO-ACTIONS<br/>Primary: Diagnose, Create WO, Add to Handover<br/>Dropdown: Close Fault, Add Note]

    EquipActions --> UserAction{User<br/>clicks<br/>action?}
    DocActions --> UserAction
    InvActions --> UserAction
    WOActions --> UserAction
    FaultActions --> UserAction

    UserAction -->|READ| ExecuteRead[Execute immediately<br/>Query DB → Show results]
    ExecuteRead --> End([Done])

    UserAction -->|MUTATE| ShowForm[Show form<br/>Pre-filled from context<br/>User enters details]

    ShowForm --> UserConfirm{User<br/>confirms?}

    UserConfirm -->|No| Cancelled([Cancelled])

    UserConfirm -->|Yes| Commit[ATOMIC TRANSACTION<br/>BEGIN<br/>1. INSERT/UPDATE operational table<br/>2. INSERT ledger_events<br/>3. INSERT pms_audit_log if required<br/>COMMIT or ROLLBACK]

    Commit --> Success{Success?}

    Success -->|No| Rollback[ROLLBACK<br/>Show error]
    Rollback --> End

    Success -->|Yes| Confirmation[Show confirmation<br/>+ Next actions<br/>Update situation state]
    Confirmation --> End

    style Start fill:#e1f5ff
    style End fill:#e1f5ff
    style Cancelled fill:#ffe1e1
    style Commit fill:#c8e6c9
    style Rollback fill:#ffccbc
    style SearchResults fill:#fff9c4
    style EquipSit fill:#e8f5e9
    style DocSit fill:#e8f5e9
    style InvSit fill:#e8f5e9
    style WOSit fill:#e8f5e9
    style FaultSit fill:#e8f5e9
```

---

## Key Decision Points

### 1. User Click on Search Result (Stage 3)

**5 possible domain situations:**
- Equipment → Equipment Situation
- Document → Document Situation
- Inventory → Inventory Situation
- Work Order → Work Order Situation
- Fault → Fault Situation

**State transition:** IDLE → CANDIDATE (clicked) → ACTIVE (opened detail/manual/history)

---

### 2. Action Type (READ vs MUTATE)

**READ actions:**
- Execute immediately
- No confirmation needed
- Examples: View history, Show manual, Check stock

**MUTATE actions:**
- Show form (pre-filled from context)
- Require user confirmation
- Atomic write to 2-3 tables
- Examples: Create WO, Adjust quantity, Mark complete

---

### 3. MUTATE Commit (Atomic Transaction)

**2-table write (low risk):**
1. INSERT/UPDATE operational table (`pms_work_orders`, `pms_inventory`, etc.)
2. INSERT `ledger_events` (timeline)

**3-table write (high risk - requires signature):**
1. INSERT/UPDATE operational table
2. INSERT `ledger_events`
3. INSERT `pms_audit_log` (compliance)

**Rule:** If any write fails → ROLLBACK entire transaction

---

## Color Legend

| Color | Meaning |
|-------|---------|
| 🔵 Blue | Start/End points |
| 🟢 Green | Commit (success path) |
| 🟡 Yellow | Search results (passive) |
| 🟢 Light Green | Domain situations (active states) |
| 🟠 Orange | Rollback (error) |
| 🔴 Red | Cancelled |

---

## Critical Paths

### Fast Path (READ action)
```
Search → Click Result → Situation Activates → Click READ Action → Execute → Done
```
**Latency target:** < 500ms

### MUTATE Path (requires confirmation)
```
Search → Click Result → Situation Activates → Click MUTATE Action → Form → Confirm → Commit → Done
```
**Latency target:** < 1000ms (excluding user form entry time)

---

## Search Bar Guardrails

**Search results are PASSIVE. No actions allowed.**

✅ Search MAY show:
- Entity previews (one-line)
- Status badges ("Overdue", "Out of Stock")
- Domain grouping

❌ Search MUST NEVER show:
- Action buttons
- Editable fields
- Auto-open entities (even at 100% confidence)

**Why:** Trust depends on this boundary. Search informs, never nudges.

---

## Situation State Machine

```
IDLE (on search surface)
  ↓
  User clicks result
  ↓
CANDIDATE (preview shown, NO actions yet)
  ↓
  User opens detail / views history / opens manual
  ↓
ACTIVE (micro-actions now allowed)
```

**ACTIVE triggers (deterministic evidence):**
- `opened_manual`
- `viewed_history`
- `mutation_committed`
- `repeated_queries_count` (boosts confidence)

---

## Domain Situations

| Situation | Primary Actions | Dropdown Actions |
|-----------|-----------------|------------------|
| **Equipment** | Show Manual, View Faults, Create WO | View History, Add Note, Add to Handover |
| **Document** | Open Viewer, Add to Handover | Link to Equipment, Summarize |
| **Inventory** | View Stock, Adjust Qty, View Location | Add to Handover, Reorder |
| **Work Order** | View Details, Add Note, Mark Complete | Add Parts, Assign |
| **Fault** | Diagnose, Create WO, Add to Handover | Close Fault, Add Note |

**Context filtering:** If user mentioned "overheating" in query → prioritize fault-related actions.

---

## Ledger Dual Purpose

**Ledger is NOT just compliance. It's a working feature.**

1. **User History:** "What did I work on today?" → Query `ledger_events` for navigation
2. **Department Oversight:** HOD sees team activity → Accountability tool
3. **Compliance:** Inspector audit trail → Immutable record

**Ledger = working memory + supervision + compliance.**

---

**Reference:** See `02_GLOBAL_ROUTER_FLOW.md` for detailed stage definitions.
