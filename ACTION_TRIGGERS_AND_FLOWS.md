# Action Triggers & Entity Flow Map

**Purpose:** Visual reference for all action trigger conditions, entity interlinking, and situational flows

---

## I. Entity Relationship & Action Flow Diagram

```
┌──────────────┐     triggers     ┌──────────────┐     creates      ┌──────────────┐
│   FAULT      │ ────────────────>│  WORK ORDER  │ ────────────────>│     NOTE     │
│              │                   │              │                   │              │
│ • code       │     links to      │ • status     │     requires     │ • content    │
│ • severity   │<──────────────────│ • priority   │<──────────────────│ • timestamp  │
│ • recurrence │                   │ • outcome    │                   └──────────────┘
└──────────────┘                   └──────────────┘
      │ │                                │ │
      │ └─────────────┐                 │ └──────────────┐
      │               │                 │                │
      v               v                 v                v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  EQUIPMENT   │ │   HANDOVER   │ │     PARTS    │ │  INVENTORY   │
│              │ │              │ │  (PLANNED)   │ │ TRANSACTIONS │
│ • manual     │ │ • priority   │ │              │ │              │
│ • status     │ │ • next action│ │ • quantity   │ │ • usage      │
│ • critical   │ └──────────────┘ └──────────────┘ │ • receive    │
└──────────────┘                        │           └──────────────┘
      │                                 │                  │
      │                                 v                  v
      │                          ┌──────────────┐   ┌──────────────┐
      │                          │   SHOPPING   │   │     PART     │
      └────────>                 │     LIST     │   │   (MASTER)   │
              manual_available   │              │   │              │
                                 │ • state      │   │ • stock      │
                                 │ • urgency    │   │ • thresholds │
                                 └──────────────┘   └──────────────┘
                                        │                  │
                                        v                  │
                                 ┌──────────────┐         │
                                 │   PURCHASE   │         │
                                 │    ORDER     │         │
                                 │              │         │
                                 └──────────────┘         │
                                        │                 │
                                        v                 │
                                 ┌──────────────┐         │
                                 │  RECEIVING   │         │
                                 │   SESSION    │         │
                                 │              │         │
                                 │ • checkbox   │<────────┘
                                 │   = truth    │   updates stock
                                 └──────────────┘
```

---

## II. Action Trigger Conditions (Complete Matrix)

### A. Fault-Triggered Actions

| Condition | Action | Urgency | Pre-fill Data |
|-----------|--------|---------|---------------|
| `fault.severity = 'critical' AND fault.work_order_id IS NULL` | `create_work_order_from_fault` | CRITICAL | title, equipment, priority=critical |
| `fault.occurrence_count >= 3 AND last_occurrence <= 7 days` | `add_to_handover` | HIGH | category=ongoing_fault, priority=high |
| `fault.severity IN ('high', 'critical') AND fault.status != 'resolved'` | `add_to_handover` | NORMAL | category=ongoing_fault |
| `fault.equipment.manual_available = TRUE` | `show_manual_section` | N/A | document_id, section=fault.code |
| `fault.work_order_id IS NOT NULL` | `view_related_work_order` | N/A | work_order_id |

**SQL Trigger Query:**
```sql
-- Auto-add to handover for recurring faults
SELECT f.id, f.code, f.equipment_id
FROM pms_faults f
WHERE f.yacht_id = $yacht_id
  AND f.occurrence_count >= 3
  AND f.last_occurrence > NOW() - INTERVAL '7 days'
  AND f.status IN ('active', 'acknowledged')
  AND NOT EXISTS (
    SELECT 1 FROM pms_handover_items hi
    WHERE hi.source_type = 'fault'
      AND hi.source_id = f.id
      AND hi.status IN ('draft', 'published')
  );
```

### B. Work Order-Triggered Actions

| Condition | Action | Urgency | Pre-fill Data |
|-----------|--------|---------|---------------|
| `wo.status IN ('candidate', 'in_progress')` | `add_note` | N/A | category=update |
| `wo.status IN ('candidate', 'in_progress', 'pending_parts')` | `add_part` | N/A | work_order_id |
| `wo.status = 'in_progress'` | `mark_complete` | N/A | outcome=resolved, time_spent |
| `wo.parts_added.count > 0 AND wo.parts_logged.count < wo.parts_added.count` | `log_part_usage` | NORMAL | parts list, quantities |
| `wo.status IN ('in_progress', 'blocked', 'pending_parts')` | `add_to_handover` | NORMAL | category=work_in_progress |
| `wo.age_days > 7 AND wo.notes.count = 0` | UI FLAG | LOW | Visual reminder |

**SQL Trigger Query:**
```sql
-- Work orders with unlogged parts
SELECT wo.id, wo.number, COUNT(wop.id) AS parts_unlogged
FROM pms_work_orders wo
JOIN pms_work_order_parts wop ON wo.id = wop.work_order_id
WHERE wo.yacht_id = $yacht_id
  AND wo.status IN ('in_progress', 'completed')
  AND wop.quantity_used < wop.quantity_planned
GROUP BY wo.id, wo.number
HAVING COUNT(wop.id) > 0;
```

### C. Part/Inventory-Triggered Actions

| Condition | Action | Urgency | Pre-fill Data |
|-----------|--------|---------|---------------|
| `part.stock_level <= part.critical_threshold` | `add_to_shopping_list` | CRITICAL | quantity=(min - current), reason=critical |
| `part.stock_level < part.minimum_threshold` | `add_to_shopping_list` | NORMAL | quantity=(min - current), reason=low |
| `part.stock_level = 0` | `add_to_shopping_list` | HIGH | quantity=minimum, reason=out_of_stock |
| Always available | `check_stock_level` | N/A | part_id |
| Context: WO viewing | `add_to_work_order` | N/A | part_id, quantity=1 |

**SQL Trigger Query:**
```sql
-- Parts below critical threshold (auto-flag for shopping list)
SELECT p.id, p.name, p.stock_level, p.critical_threshold,
       (p.minimum_threshold - p.stock_level) AS quantity_needed
FROM pms_parts p
LEFT JOIN pms_shopping_list sl ON p.id = sl.part_id
  AND sl.state IN ('CANDIDATE', 'ACTIVE', 'COMMITTED')
WHERE p.yacht_id = $yacht_id
  AND p.stock_level <= p.critical_threshold
  AND p.active = TRUE
  AND sl.id IS NULL  -- Not already in shopping list
ORDER BY p.stock_level ASC;
```

### D. Shopping List-Triggered Actions

| Condition | Action | Urgency | Role Restriction |
|-----------|--------|---------|------------------|
| `item.state = 'CANDIDATE'` | `approve` | N/A | HOD only |
| `item.state = 'CANDIDATE'` | `edit_quantity` | N/A | Any |
| `item.state = 'CANDIDATE'` | `remove` | N/A | Creator or HOD |
| `item.state IN ('CANDIDATE', 'ACTIVE')` | `assign_supplier` | N/A | Any |
| `item.state = 'COMMITTED'` | `receive` | N/A | Receiving role |
| `item.state = 'MISSING'` | `reorder` | HIGH | HOD |

**SQL State Transition:**
```sql
-- Approve shopping list items (HOD action)
UPDATE pms_shopping_list
SET state = 'ACTIVE',
    reviewed_by = $user_id,
    reviewed_at = NOW()
WHERE id = ANY($item_ids)
  AND yacht_id = $yacht_id
  AND state = 'CANDIDATE';

-- Then create purchase order
INSERT INTO pms_purchase_orders (yacht_id, po_number, supplier_name, status, created_by)
VALUES ($yacht_id, generate_po_number(), $supplier, 'pending', $user_id)
RETURNING id;

-- Link approved items to PO
UPDATE pms_shopping_list
SET state = 'COMMITTED',
    purchase_order_id = $po_id,
    approved_by = $user_id,
    approved_at = NOW(),
    ordered_at = NOW()
WHERE id = ANY($item_ids);
```

### E. Receiving-Triggered Actions

| Condition | Action | State Requirement |
|-----------|--------|-------------------|
| `session.status = 'CANDIDATE'` | `confirm_order` | Upload complete |
| `session.status = 'ACTIVE'` | `check_item` | Checkbox interaction |
| `session.status = 'ACTIVE' AND item.delivered != item.expected` | `mark_discrepancy` | Item checked |
| `session.status = 'ACTIVE' AND item.checked = TRUE` | `mark_installed` | Optional |
| `session.status = 'REVIEW'` | `commit_receiving` | ≥1 item checked |

**SQL Workflow:**
```sql
-- Commit receiving session (Checkbox = Truth)
-- Only checked items affect inventory/finance
WITH checked_items AS (
  SELECT ri.id, ri.part_id, ri.delivered_quantity, ri.installed, ri.status
  FROM pms_receiving_items ri
  WHERE ri.receiving_session_id = $session_id
    AND ri.checked = TRUE  -- ONLY CHECKED ITEMS
)
-- Insert inventory transactions for non-installed items
INSERT INTO pms_inventory_transactions (yacht_id, part_id, transaction_type, quantity, receiving_session_id, user_id, timestamp)
SELECT $yacht_id, ci.part_id, 'receive', ci.delivered_quantity, $session_id, $user_id, NOW()
FROM checked_items ci
WHERE ci.installed = FALSE
  AND ci.status = 'ok';

-- Update shopping list status
UPDATE pms_shopping_list sl
SET state = CASE
    WHEN all_received THEN 'FULFILLED'
    WHEN some_received THEN 'PARTIALLY_FULFILLED'
    ELSE sl.state
  END,
  actual_unit_cost = $cost,
  actual_cost = $cost * quantity,
  fulfilled_at = CASE WHEN all_received THEN NOW() ELSE NULL END
WHERE sl.id IN (
  SELECT ri.shopping_list_item_id FROM checked_items ci JOIN pms_receiving_items ri ON ci.id = ri.id
);

-- Update session status
UPDATE pms_receiving_sessions
SET status = 'COMMITTED',
    committed_at = NOW(),
    committed_by = $user_id,
    total_items = (SELECT COUNT(*) FROM pms_receiving_items WHERE receiving_session_id = $session_id),
    items_received = (SELECT COUNT(*) FROM checked_items WHERE status = 'ok'),
    items_installed = (SELECT COUNT(*) FROM checked_items WHERE installed = TRUE),
    items_missing = (SELECT COUNT(*) FROM checked_items WHERE status = 'missing'),
    items_damaged = (SELECT COUNT(*) FROM checked_items WHERE status = 'damaged')
WHERE id = $session_id;
```

### F. Handover-Triggered Actions

| Condition | Action | Who |
|-----------|--------|-----|
| `item.status = 'published' AND item.acknowledged_at IS NULL` | `acknowledge` | Owner |
| `item.status = 'published' AND item.source_id IS NOT NULL` | `view_source_entity` | Any |
| `handover.status = 'draft'` | `publish` | Shift lead |
| `handover.age_days > 7 OR source_resolved = TRUE` | `archive` | Auto or Manual |

**SQL Reminder Logic:**
```sql
-- Unacknowledged items requiring attention
SELECT
  hi.id,
  hi.title,
  hi.priority,
  hi.owner_name,
  hi.published_at,
  EXTRACT(EPOCH FROM (NOW() - hi.published_at)) / 3600 AS hours_unacknowledged
FROM pms_handover_items hi
WHERE hi.yacht_id = $yacht_id
  AND hi.status = 'published'
  AND hi.acknowledged_at IS NULL
  AND (
    (hi.priority = 1 AND hi.published_at < NOW() - INTERVAL '1 hour')   -- Urgent: 1hr
    OR (hi.priority = 2 AND hi.published_at < NOW() - INTERVAL '4 hours')  -- High: 4hrs
    OR (hi.priority = 3 AND hi.published_at < NOW() - INTERVAL '6 hours')  -- Normal: shift+2hrs
  )
ORDER BY hi.priority ASC, hi.published_at ASC;
```

### G. Document Viewing-Triggered Actions

| Condition | Action | Context |
|-----------|--------|---------|
| `doc_chunk.fault_code_refs.length > 0` | `create_work_order_from_fault` | Fault exists, no WO |
| `doc_chunk.part_refs.length > 0` | `check_stock_level` | Part identified |
| `doc_chunk.section_title LIKE '%Safety%' OR '%Critical%'` | `add_to_handover` | Flagged section |
| `equipment.manual_available = TRUE` | `show_manual` | Always available |

**SQL Context Extraction:**
```sql
-- Extract actionable entities from document chunk
SELECT
  dc.id AS chunk_id,
  dc.fault_code_refs,
  dc.equipment_refs,
  dc.part_refs,
  f.id AS fault_id,
  f.work_order_id,
  p.id AS part_id,
  p.stock_level
FROM pms_document_chunks dc
LEFT JOIN UNNEST(dc.fault_code_refs) AS fault_code ON TRUE
LEFT JOIN pms_faults f ON f.code = fault_code AND f.yacht_id = $yacht_id
LEFT JOIN UNNEST(dc.part_refs) AS part_name ON TRUE
LEFT JOIN pms_parts p ON p.name ILIKE ('%' || part_name || '%') AND p.yacht_id = $yacht_id
WHERE dc.document_id = $document_id
  AND dc.page_number = $current_page;
```

---

## III. Situational State Machines

### A. Receiving State Machine

```
IDLE
  │
  │ User uploads packing slip OR selects order
  v
CANDIDATE
  │  Order confirmed?
  │  NO → Back to IDLE (cancel)
  │  YES ↓
  v
ACTIVE ─────────────────────────────────────┐
  │                                          │
  │ User ticks ≥1 item                       │
  v                                          │
REVIEW                                       │
  │  Confirm?                                │
  │  NO → Back to ACTIVE (edit more)  ←──────┘
  │  YES ↓
  v
COMMITTED (terminal)
```

**State Actions:**
- **IDLE:** `scan_packing_slip`, `select_order`
- **CANDIDATE:** `confirm_order`, `upload_more`, `cancel`
- **ACTIVE:** `check_item`, `edit_quantity`, `mark_discrepancy`, `mark_installed`
- **REVIEW:** `view_summary`, `back_to_active`, `commit`
- **COMMITTED:** `view_receipt`, `download_labels`

### B. Shopping List State Machine (Item-Level)

```
CANDIDATE
  │
  │ HOD reviews
  v
ACTIVE
  │  Approved?
  │  YES ↓         NO → REJECTED (terminal)
  v
COMMITTED (ordered)
  │
  ├─> PARTIALLY_FULFILLED (some received)
  │       │
  │       └─> FULFILLED (all received)
  │
  ├─> INSTALLED (skip inventory)
  │
  └─> MISSING (not received / damaged)
          │
          └─> Re-add as CANDIDATE (loop back)
```

**State Actions:**
- **CANDIDATE:** `view`, `edit_qty`, `assign_supplier`, `remove`, `add_note`
- **ACTIVE:** `approve`, `reject`, `group_with_others`, `assign_urgency`
- **COMMITTED:** `view_order`, `attach_docs`, `prepare_receiving`
- **PARTIALLY_FULFILLED:** `receive_remaining`, `mark_missing`
- **FULFILLED:** `view_only`, `audit_export`
- **INSTALLED:** `view_linked_wo`, `audit_trail`
- **MISSING:** `re_add_to_list`, `cancel`, `attach_notes`

---

## IV. Threshold Configuration Reference

### Inventory Thresholds

| Threshold | Default Value | Triggers | Urgency |
|-----------|--------------|----------|---------|
| `critical_threshold` | 0 | `add_to_shopping_list` | CRITICAL |
| `low_threshold` | 5 | `add_to_shopping_list` | NORMAL |
| `minimum_threshold` | 10 | Reorder point | N/A |

**Evaluation Logic:**
```typescript
function evaluateInventoryThresholds(part: Part): Action[] {
  const actions: Action[] = [];

  if (part.stock_level <= part.critical_threshold) {
    actions.push({
      id: 'add_to_shopping_list',
      urgency: 'CRITICAL',
      prefill: {
        quantity: part.minimum_threshold - part.stock_level,
        reason: `Critical stock: ${part.stock_level} units (threshold: ${part.critical_threshold})`,
      },
    });
  } else if (part.stock_level < part.minimum_threshold) {
    actions.push({
      id: 'add_to_shopping_list',
      urgency: 'NORMAL',
      prefill: {
        quantity: part.minimum_threshold - part.stock_level,
        reason: `Low stock: ${part.stock_level} units (min: ${part.minimum_threshold})`,
      },
    });
  }

  return actions;
}
```

### Fault Recurrence Thresholds

| Threshold | Value | Triggers | Priority |
|-----------|-------|----------|----------|
| `occurrence_count` | ≥3 | `add_to_handover` | HIGH |
| `time_window` | 7 days | (combined with count) | N/A |
| `severity` | critical | `create_work_order` | CRITICAL |

**Evaluation Logic:**
```typescript
function evaluateFaultThresholds(fault: Fault): Action[] {
  const actions: Action[] = [];
  const daysSinceLastOccurrence = (Date.now() - fault.last_occurrence) / (1000 * 60 * 60 * 24);

  // Recurring fault
  if (fault.occurrence_count >= 3 && daysSinceLastOccurrence <= 7) {
    actions.push({
      id: 'add_to_handover',
      urgency: 'HIGH',
      prefill: {
        category: 'ongoing_fault',
        priority: 'high',
        summary_text: `${fault.code} occurred ${fault.occurrence_count} times in last 7 days.`,
      },
    });
  }

  // Critical severity without WO
  if (fault.severity === 'critical' && !fault.work_order_id) {
    actions.push({
      id: 'create_work_order_from_fault',
      urgency: 'CRITICAL',
    });
  }

  return actions;
}
```

### Work Order Age Thresholds

| Threshold | Value | Triggers | Type |
|-----------|-------|----------|------|
| `age_without_notes` | >7 days | UI reminder flag | PASSIVE |
| `parts_unlogged` | Any | `log_part_usage` warning | ACTIVE |

**Evaluation Logic:**
```typescript
function evaluateWorkOrderAge(wo: WorkOrder): UIFlags[] {
  const flags: UIFlags[] = [];
  const ageDays = (Date.now() - wo.created_at) / (1000 * 60 * 60 * 24);

  if (wo.status === 'in_progress' && ageDays > 7 && wo.notes.length === 0) {
    flags.push('add_note_reminder');  // Visual indicator, NOT a proactive nudge
  }

  return flags;
}
```

### Handover Acknowledgment Thresholds

| Priority | Threshold | Action |
|----------|-----------|--------|
| 1 (Urgent) | 1 hour | Reminder badge |
| 2 (High) | 4 hours | Reminder badge |
| 3 (Normal) | Shift start + 2 hours | Reminder badge |

**Reminder Query:**
```sql
SELECT COUNT(*)
FROM pms_handover_items
WHERE yacht_id = $yacht_id
  AND owner_id = $user_id
  AND status = 'published'
  AND acknowledged_at IS NULL
  AND (
    (priority = 1 AND published_at < NOW() - INTERVAL '1 hour')
    OR (priority = 2 AND published_at < NOW() - INTERVAL '4 hours')
    OR (priority = 3 AND published_at < NOW() - INTERVAL '2 hours')
  );
```

---

## V. Cross-Entity Action Flows

### Flow 1: Fault → Work Order → Parts → Shopping List → Receiving → Inventory

```
1. FAULT OBSERVED
   ↓
   User: "generator 2 overheating"
   ↓
   System: Shows fault F-2024-089 (occurrence_count=3, severity=high)
   ↓
   Actions offered:
   - create_work_order_from_fault (no WO exists)
   - add_to_handover (recurring fault)
   - show_manual_section (manual available)

2. CREATE WORK ORDER
   ↓
   User clicks: create_work_order_from_fault
   ↓
   Form pre-filled:
   - title: "Generator 2 - MTU-OVHT-01"
   - equipment: Generator 2
   - priority: high
   - description: "Coolant temp high. Occurred 3 times in last 7 days."
   ↓
   User confirms → WO-2024-089 created
   ↓
   fault.work_order_id = WO-2024-089.id

3. ADD PARTS TO WO
   ↓
   User navigates to WO-2024-089
   ↓
   Action: add_part
   ↓
   User searches: "thermostat"
   ↓
   System shows: MTU Thermostat (stock: 0 units ⚠️ Out of Stock)
   ↓
   User adds anyway → Part linked to WO (status: planned)

4. PARTS OUT OF STOCK → SHOPPING LIST
   ↓
   System detects: part.stock_level = 0
   ↓
   Auto-creates shopping list item:
   - part: MTU Thermostat
   - quantity: 1 (from WO) + 10 (minimum threshold) = 11
   - source: work_order_usage
   - source_id: WO-2024-089
   - state: CANDIDATE
   - urgency: HIGH

5. HOD APPROVES SHOPPING LIST
   ↓
   HOD reviews shopping list
   ↓
   Action: approve (HOD only)
   ↓
   State: CANDIDATE → ACTIVE → COMMITTED
   ↓
   Purchase order created: PO-2024-015
   ↓
   Order sent to supplier

6. RECEIVING
   ↓
   Parts arrive (3 days later)
   ↓
   User scans packing slip (camera icon in search)
   ↓
   OCR extracts: "MTU Thermostat x11"
   ↓
   System matches to PO-2024-015
   ↓
   Receiving table:
   ☐ MTU Thermostat | Expected: 11 | Delivered: 11 | Status: —
   ↓
   User ticks checkbox ✓
   ↓
   User clicks "Confirm & Save"
   ↓
   Inventory transaction created:
   - part: MTU Thermostat
   - quantity: +11
   - type: receive
   ↓
   part.stock_level updated: 0 → 11

7. WORK ORDER COMPLETION
   ↓
   Engineer uses 1 thermostat
   ↓
   Action: log_part_usage
   ↓
   Form shows: MTU Thermostat x1 (checked)
   ↓
   User confirms → Inventory transaction:
   - quantity: -1
   - type: usage
   - work_order_id: WO-2024-089
   ↓
   part.stock_level: 11 → 10
   ↓
   Engineer marks WO complete
   ↓
   Outcome: resolved
   ↓
   fault.status → resolved (if user checks box)
```

### Flow 2: Document Viewing → Context → Actions

```
1. USER VIEWS MANUAL
   ↓
   Search: "MTU overheating troubleshooting"
   ↓
   Result: Document chunk (Page 142, Section 7.3)
   ↓
   User clicks → PDF viewer opens to page 142

2. SYSTEM EXTRACTS CONTEXT
   ↓
   Document chunk metadata:
   - fault_code_refs: ['MTU-OVHT-01', 'MTU-COOL-02']
   - equipment_refs: ['Generator 2']
   - part_refs: ['Thermostat', 'Coolant Pump']
   ↓
   System queries database:
   - Fault MTU-OVHT-01 exists (active, no WO)
   - Generator 2 exists
   - Thermostat stock: 10 units
   - Coolant Pump stock: 3 units

3. ACTIONS OFFERED (in document viewer sidebar)
   ↓
   - create_work_order_from_fault (Fault MTU-OVHT-01)
   - check_stock_level (Thermostat)
   - check_stock_level (Coolant Pump)
   - add_to_handover (flagged section)

4. USER SELECTS ACTION
   ↓
   User clicks: add_to_handover
   ↓
   Form pre-filled:
   - title: "Manual Reference: MTU 16V4000 - Section 7.3"
   - category: important_info
   - summary: "Overheating troubleshooting section flagged for next shift."
   - next_action: "Review Section 7.3 before next generator service"
   ↓
   User confirms → Handover item created
```

---

## VI. Query Intent → Action Offering Examples

| User Query | Intent Type | Entity Keywords | Action Keywords | Actions Offered | Location |
|------------|-------------|----------------|-----------------|-----------------|----------|
| "create work order for generator 2" | action (explicit) | generator | create, work order | `create_work_order_from_fault` | Beneath search bar |
| "generator 2 status" | information | generator | - | None (shows entity first) | N/A → user clicks entity |
| "generator 2" | information | generator | - | None | Entity page → dropdown |
| "MTU overheating" | information | equipment, fault | - | None | Fault entity → dropdown |
| "add to handover" | action (explicit) | - | add, handover | `add_to_handover` | Modal (select entity) |
| "check stock thermostat" | action (explicit) | part | check, stock | `check_stock_level` | Beneath search / inline |
| "receive delivery" | action (explicit) | - | receive, delivery | `scan_packing_slip`, `select_order` | Receiving screen |
| "log parts for WO-089" | action (explicit) | work order | log, parts | `log_part_usage` | Form opens |
| "thermostat" (viewing WO page) | information | part | - | `add_part` (context: WO) | Entity dropdown |

---

## VII. Implementation Checklist

### Backend Requirements

- [ ] Action registry populated with all P0 actions
- [ ] Pre-fill templates configured for each action
- [ ] Threshold evaluation functions implemented
- [ ] State machine transition validators
- [ ] Audit log triggers on all mutations
- [ ] Query intent parser (keyword-based)
- [ ] Entity context builder (from query results)
- [ ] Action offering engine (evaluates conditions)

### Frontend Requirements

- [ ] Action buttons in entity dropdowns
- [ ] Action buttons beneath search bar (explicit intents)
- [ ] Modal forms for all MUTATE actions
- [ ] Preview screens before commit
- [ ] Receiving checkbox table UI
- [ ] Shopping list state badges
- [ ] Handover acknowledgment UI
- [ ] Document viewer with action sidebar

### Database Requirements

- [ ] All tables created (per schema)
- [ ] Indexes on action-relevant columns
- [ ] RLS policies for yacht isolation
- [ ] Triggers for auto-stock updates
- [ ] Views for common action queries
- [ ] Audit log enabled

---

**END OF TRIGGER & FLOW MAP**
