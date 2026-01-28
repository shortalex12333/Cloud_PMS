# 02_GLOBAL_ROUTER_FLOW.md

**Date:** 2026-01-22
**Purpose:** How search becomes action (Apple Spotlight model for yacht management)
**Status:** Layer A - Core Control Flow

---

## PRODUCT MODEL

**CelesteOS = Apple Spotlight for yacht management**

- One search bar
- No navigation menu
- UI morphs dynamically based on what user is doing
- RAG-powered search (Supabase vector search on manuals, docs, data)
- Micro-action buttons appear contextually

**Core principle:** Search is passive. Click is commitment.

---

## THE CONTROL FLOW (4 Stages)

```
┌─────────────────────────────────────┐
│ 1. INPUT                            │
│    User types natural language      │
│    "gen 2 overheating, show manual" │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│ 2. ENTITY EXTRACTION + RAG SEARCH   │
│    Extract: equipment, fault, part  │
│    Retrieve: docs, manuals, data    │
│    Return: ranked results           │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│ 3. USER CLICKS RESULT               │
│    → SITUATION ACTIVATES            │
│    Click inventory → Inventory View │
│    Click document → Document View   │
│    Click WO → Work Order View       │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│ 4. MICRO-ACTIONS APPEAR             │
│    Buttons contextually filtered    │
│    User clicks → Confirm → Commit   │
└─────────────────────────────────────┘
```

---

## STAGE 1: INPUT

### What Arrives

- Natural language query from single search bar
- User context: `user_id`, `yacht_id`, `role`, `department`
- Session context: Recent entities viewed, recent actions

### Query Examples

| Query | User Intent |
|-------|-------------|
| `"gen 2 overheating, show manual"` | Find equipment + manual, investigate issue |
| `"create work order for galley chiller"` | Explicit action request |
| `"check stock for fuel filter"` | Inventory lookup |
| `"show me what I worked on today"` | Ledger history query |

### What Happens

Query goes to backend:
1. Entity extraction (NER/LLM)
2. RAG search (Supabase vector search)
3. Returns ranked results

---

## STAGE 2: ENTITY EXTRACTION + RAG SEARCH

### Entity Extraction

Extract structured entities from query:

| Entity Type | Examples | Database Lookup |
|-------------|----------|-----------------|
| **equipment** | "gen 2", "CAT 3512", "galley chiller" | `pms_equipment` (name, aliases) |
| **fault** | "overheating", "alarm", "fault #123" | `pms_faults` (symptoms, fault_code) |
| **part** | "fuel filter", "P/N 12345" | `pms_parts` (part_number, description) |
| **work_order** | "WO-456", "open work orders" | `pms_work_orders` (title, status) |
| **person** | "assign to Mike", "Chief Engineer" | `user_roles` (name, role) |
| **intent** | "create", "show", "add to handover" | Action keyword matching |

### RAG Search (Supabase Vector Search)

Simultaneously search:
1. **Documents/Manuals** (`pms_document_chunks`) - Semantic search on embeddings
2. **Operational Data** (equipment, WOs, faults, inventory) - Keyword + filter
3. **Ledger History** (`ledger_events`) - User's recent activity

### Result Grouping

Return results grouped by domain:

```
[Equipment]
  - Generator 2 (CAT 3512B) - Engine Room
  - Galley Chiller - Deck 2

[Documents]
  - CAT 3512 Service Manual - Section 4.2 (Cooling System)
  - Troubleshooting Guide - Overheating

[Work Orders]
  - WO-789: Gen 2 Maintenance (Open)

[Faults]
  - Fault #456: High Coolant Temp - Gen 2 (Open)
```

### Context Extraction

Also extract query context for later filtering:

- **Symptom keywords:** "overheating", "vibration", "leaking"
- **Urgency signals:** "urgent", "emergency", "again"
- **Action intent:** "create", "show", "add", "check"

**This context will filter which micro-actions appear after click.**

---

## STAGE 3: USER CLICKS RESULT → SITUATION ACTIVATES

### Search Bar Guardrails (Non-Negotiable)

**Search results are PASSIVE. No actions appear in search.**

Search may show:
- Entity previews (one-line)
- Status badges ("Overdue", "Out of Stock")
- Domain grouping

Search MUST NEVER show:
- Action buttons
- Editable fields
- Auto-open entities (even at 100% confidence)

**Why:** Trust depends on this boundary. Search informs, never nudges.

---

### Click → Situation Activation

When user clicks a result, a **domain situation** activates.

| User Clicks | Situation Activates | UI Changes To |
|-------------|---------------------|---------------|
| Inventory item | **Inventory Situation** | Inventory detail view |
| Document/Manual | **Document Situation** | Document viewer |
| Work Order | **Work Order Situation** | WO detail view |
| Fault | **Fault Situation** | Fault detail view |
| Equipment | **Equipment Situation** | Equipment overview |

**One domain at a time. UI morphs completely.**

---

### Situation State Machine

Each situation follows: **IDLE → CANDIDATE → ACTIVE**

| State | When | What It Means |
|-------|------|---------------|
| **IDLE** | User on search surface | No entity selected, no actions |
| **CANDIDATE** | User clicks result | Preview shown, NO actions yet |
| **ACTIVE** | User opens detail OR views history OR opens manual | Micro-actions now allowed |

**ACTIVE triggers:**
- User opens detail view (clicks into entity)
- User views history tab
- User opens linked manual
- User commits a mutation

**Evidence tracking** (deterministic flags):
- `opened_manual` (ACTIVE)
- `viewed_history` (ACTIVE)
- `mutation_committed` (ACTIVE + suppress further nudges)
- `repeated_queries_count` (boosts confidence)

---

## STAGE 4: MICRO-ACTIONS APPEAR

### Action Filtering (Context-Aware)

**Not all actions appear.** Actions are filtered by:

1. **Situation type** (Inventory vs Document vs WO)
2. **Query context** (did user mention "overheating"? "create"?)
3. **User role** (Chief Engineer vs Crew)
4. **Entity state** (can't close a fault that's not diagnosed)

### Example: Equipment Situation + "Overheating" Context

**Query:** `"gen 2 overheating, show manual"`
**User clicks:** Generator 2 (equipment result)
**Situation:** Equipment (ACTIVE after viewing manual)

**All equipment actions (from registry):**
- view_equipment_history
- view_equipment_manual
- view_linked_faults
- create_work_order
- add_equipment_note
- add_to_handover
- view_equipment_parts
- update_equipment_status

**Context filtering** (user mentioned "overheating"):

**Primary actions (top buttons):**
- [Show Manual] (context match: "manual" in query)
- [View Faults] (context match: overheating = symptom)
- [Create Work Order] (high relevance: overheating = problem to fix)

**Dropdown (▼ More actions):**
- View History
- View Parts
- Add Note
- Add to Handover
- Update Status

**Result:** 3 primary buttons + dropdown. Not 8 buttons.

---

### Action Types (READ vs MUTATE)

| Type | Behavior | Examples |
|------|----------|----------|
| **READ** | Execute immediately, no confirmation | View history, Show manual, Check stock |
| **MUTATE** | Require confirmation + signature (if needed) | Create WO, Adjust quantity, Mark complete |

**READ actions:** Click → execute → show results
**MUTATE actions:** Click → form → confirm → commit

---

### Multiple MUTATE Actions

**Scenario:** User types vague query that matches multiple mutations.

**Example (BAD QUERY):**
`"fix gen 2"`
- Too vague. System cannot be precise.

**Example (GOOD QUERY):**
`"gen 2 is overheating again, show me the manual and changes"`
- Clear intent: investigate + document
- User clicks manual → Document Situation
- Action buttons: [Add to Handover] [Create Work Order]

**If both are MUTATEs:**
- **Primary button:** Most relevant (based on context)
- **Dropdown:** Other MUTATEs

**User must choose explicitly. No auto-execution.**

---

### Action Button UI Pattern

**Primary Actions (max 3):**
```
[Show Manual]  [View Faults]  [Create Work Order]
```

**More Actions (dropdown):**
```
[▼ More]
  - View History
  - View Parts
  - Add Note
  - Add to Handover
```

**Dropdown contains:**
- Less relevant READ actions
- Secondary MUTATE actions
- Actions that didn't match query context

---

## ACTION EXECUTION FLOW

### READ Actions (Simple)

```
User clicks [View History]
  ↓
Execute query (SELECT from pms_work_orders, ledger_events)
  ↓
Show results in UI
```

**No confirmation needed. Immediate execution.**

---

### MUTATE Actions (2-Table Atomic Write)

```
User clicks [Create Work Order]
  ↓
Form appears (pre-filled from context)
User enters: description, priority, assigned_to
  ↓
User clicks [Confirm/Sign]
  ↓
ATOMIC TRANSACTION:
  BEGIN
  1. INSERT pms_work_orders (status=active, ...)
  2. INSERT ledger_events (event_type=work_order_created, user_id, timestamp, summary)
  3. [IF action requires audit] INSERT pms_audit_log (old_state, new_state, signature)
  COMMIT (or ROLLBACK if any write fails)
  ↓
Success → Show confirmation + next actions
```

**Key Rules:**

1. **Operational table first** (`pms_work_orders`) - holds current state
2. **Ledger always** (`ledger_events`) - timeline for history + accountability
3. **Audit if required** (`pms_audit_log`) - compliance for high-risk actions
4. **Atomic:** If ledger write fails → ROLLBACK operational write
5. **No drafts for MVP** - form → commit, no intermediate save

---

### 2-Table vs 3-Table Write

| Action Risk | Tables Written | Example |
|-------------|----------------|---------|
| **Low risk** | 2 tables (operational + ledger) | Add note, Add photo |
| **High risk** | 3 tables (operational + ledger + audit) | Create WO, Mark complete, Adjust inventory |

**Audit log requirement:**
- Signature-required actions: MUST write audit log
- If audit write fails: ROLLBACK entire transaction

---

## LEDGER DUAL PURPOSE

**Ledger is NOT just compliance. It's a working feature.**

### 1. User History / Navigation

**Use case:** "What did I work on today?"

User query: `"show me what I worked on"`
→ Query `ledger_events` WHERE user_id = current_user, occurred_at > today
→ Show timeline:
```
Today 14:30 - Viewed Generator 2 manual
Today 14:35 - Created Work Order WO-123
Today 14:40 - Added Fault #456 to handover
```

**User can click any event to jump back to that entity.**

---

### 2. Department Oversight (HOD View)

**Use case:** Chief Engineer wants to see what Engineering team did this week.

Query: `"show engineering work this week"`
→ Query `ledger_events` WHERE department = 'Engineering', occurred_at > this_week
→ Show:
```
Mike (2nd Engineer) - 12 actions this week
  - Created 3 work orders
  - Adjusted inventory 5 times
  - Viewed 8 manuals

Sarah (3rd Engineer) - 8 actions this week
  - Marked 4 WOs complete
  - Added 3 faults to handover
```

**Accountability + supervision tool.**

---

### 3. Compliance / Audit Trail

**Use case:** Inspector asks: "Show me all changes to this equipment in the last 6 months."

Query: Entity-specific ledger filter
→ Query `ledger_events` WHERE entity_type = 'equipment', entity_id = 'gen2', occurred_at > 6_months_ago
→ Show immutable timeline

**Ledger = working memory + supervision + compliance.**

---

## CONFLICT RESOLUTION

### Vague Queries

**Problem:** User types `"fix gen 2"` (too vague)

**System response:**
- Cannot auto-execute any MUTATE action
- Show search results: equipment, faults, manuals, WOs
- Wait for user to click and clarify intent

**Better query:** `"gen 2 overheating again, create work order"`
- Clear intent: create WO
- Pre-fill form with equipment + symptom context

**Rule:** If query is vague → system cannot be precise. Show options, let user click.

---

### Multiple MUTATEs Match

**Problem:** After user clicks, 2+ MUTATE actions are relevant.

**Example:**
- User clicks Fault #456 (high coolant temp)
- Relevant actions: `create_work_order_from_fault`, `add_to_handover`, `close_fault`

**Solution:**
- **Primary button:** Most relevant (e.g., Create WO - highest priority for open fault)
- **Dropdown:** Other MUTATEs (Add to Handover, Close Fault)

**User must explicitly choose. No auto-execution.**

---

## DOMAIN SITUATIONS (Defined)

### 1. Equipment Situation

**Activates when:** User clicks equipment result

**Primary actions (context-filtered):**
- View History
- Show Manual
- Create Work Order
- View Linked Faults

**Dropdown actions:**
- View Parts
- Add Note
- Add to Handover
- Update Status

---

### 2. Document Situation

**Activates when:** User clicks manual/document result

**Primary actions:**
- Open Document Viewer
- Add to Handover (if user is investigating issue)
- Summarize Section

**Dropdown actions:**
- Link to Equipment
- Link to Fault

**Context awareness:** If user mentioned equipment + fault code → suggest "Add to Handover"

---

### 3. Inventory Situation

**Activates when:** User clicks inventory item result

**Primary actions:**
- View Stock Level
- View Location
- Adjust Quantity (MUTATE - requires signature)

**Dropdown actions:**
- Add to Handover
- Create Reorder
- Log Usage

---

### 4. Work Order Situation

**Activates when:** User clicks WO result

**Primary actions:**
- View WO Details
- Add Note
- Mark Complete (MUTATE - requires signature)

**Dropdown actions:**
- Add Parts
- Assign to User
- Add Photo

---

### 5. Fault Situation

**Activates when:** User clicks fault result

**Primary actions:**
- Diagnose Fault
- Create Work Order
- Add to Handover

**Dropdown actions:**
- Close Fault (requires signature)
- Add Note
- View Equipment

---

## OPEN QUESTIONS

### Q1: Entity Confidence Thresholds

**Question:** At what confidence do we show results?

**Current approach:** Show all results above 0.5, let user click.

**Future tuning:** Hide low-confidence results (< 0.5) to reduce noise.

**Status:** V0 defaults acceptable for MVP. Tune based on production data.

---

### Q2: Context Filtering Algorithm

**Question:** How do we prioritize actions based on query context?

**Current approach:** Keyword matching (query contains "overheating" → boost fault-related actions)

**Future enhancement:** ML model trained on user action sequences.

**Status:** Keyword matching sufficient for MVP.

---

### Q3: Ledger Day Anchors

**Question:** How do we group ledger events for "show me this week" queries?

**Current approach:** Query by date range + group by day.

**Optimization:** Pre-compute daily summaries in `ledger_day_anchors` table.

**Status:** Needs investigation. Not blocking for MVP.

---

## NEXT STEPS

1. ✅ Layer A complete (this doc)
2. ⏳ Layer B: Cluster flows (faults, work_orders, inventory, handover)
3. ⏳ Layer C: Action cards (gold set - top 10 actions)

---

**Status:** Core flow defined. Ready for Layer B cluster flows.
