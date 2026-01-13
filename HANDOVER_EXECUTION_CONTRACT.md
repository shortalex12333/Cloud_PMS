# Handover Execution Contract

**Purpose:** Define the rules that govern what enters handover, who owns it, and how it flows.

**Not a feature spec. This is the contract engineers implement against.**

---

## Section 1: Eligibility Rules

### What Gets Into Handover (and Why)

Handover is **not** a log. It's a risk-bearing transfer surface.

**Core Principle:**
> Only items that are **unresolved, risk-bearing, time-sensitive, or blocking another person** enter handover.

---

### 1.1 Work Orders

**INCLUDE:**
- Status: `in_progress` AND shift ending
- Status: `blocked` (any reason)
- Status: `pending_parts` (parts ordered but not received)
- Priority: `critical` or `high` AND status ≠ `completed`
- Has open sub-tasks AND assigned to different crew member

**EXCLUDE:**
- Status: `completed` with no follow-up
- Status: `scheduled` for future date (>24 hours away)
- Routine maintenance with no issues

**Auto-population rule:**
```
IF work_order.status IN ('in_progress', 'blocked', 'pending_parts')
   OR (work_order.priority IN ('critical', 'high') AND work_order.status != 'completed')
THEN auto-add to handover
WITH owner = work_order.assigned_to
```

**Fields pulled:**
- WO number, title, equipment
- Status, priority
- Assigned to (owner)
- Last action taken (from audit log)
- **Next action:** Derived from status
  - `in_progress` → "Continue work"
  - `blocked` → "Resolve blocker: {blocker_reason}"
  - `pending_parts` → "Check parts delivery, ETA: {eta}"

---

### 1.2 Inventory Discrepancies

**INCLUDE:**
- Actual count ≠ system count (after cycle count or usage)
- Critical part stock < minimum threshold
- Part usage without WO link (unauthorized usage)
- Receiving discrepancy (ordered ≠ received)

**EXCLUDE:**
- Normal usage with WO link
- Stock above minimum
- Pending orders (not yet received)

**Auto-population rule:**
```
IF inventory.actual_count != inventory.system_count
   OR (inventory.category = 'critical' AND inventory.quantity < inventory.minimum)
   OR (part_usage.work_order_id IS NULL AND part_usage.quantity > threshold)
THEN auto-add to handover
WITH owner = last_user_to_touch_inventory
```

**Fields pulled:**
- Part name, number, location
- Expected vs Actual count
- Last user who logged usage/count
- **Next action:**
  - Discrepancy → "Investigate and reconcile"
  - Low stock → "Order parts, critical threshold reached"
  - Unauthorized usage → "Identify WO or report loss"

---

### 1.3 Receiving Issues

**INCLUDE:**
- Delivered quantity ≠ ordered quantity
- Damage reported on delivery
- Missing paperwork (invoice, cert)
- Delivery for unknown PO

**EXCLUDE:**
- Clean deliveries (quantity correct, no damage, paperwork complete)

**Auto-population rule:**
```
IF receiving.quantity_received != purchase_order.quantity_ordered
   OR receiving.damage_reported = TRUE
   OR receiving.paperwork_status = 'incomplete'
   OR receiving.purchase_order_id IS NULL
THEN auto-add to handover
WITH owner = receiving_user
```

**Fields pulled:**
- PO number, supplier, part name
- Ordered vs Received quantity
- Damage description (if any)
- Missing documents list
- **Next action:**
  - Qty mismatch → "Contact supplier, file claim"
  - Damage → "Photo, reject, return"
  - Missing docs → "Request from supplier"

---

### 1.4 Faults (Active/Unresolved)

**INCLUDE:**
- Severity: `critical` or `high` AND no linked WO
- Recurring fault (occurred 3+ times in 7 days)
- Fault acknowledged but not diagnosed

**EXCLUDE:**
- Low severity faults with no recent recurrence
- Faults with `completed` WO linked
- Faults older than 30 days with no activity

**Auto-population rule:**
```
IF fault.severity IN ('critical', 'high') AND fault.work_order_id IS NULL
   OR fault.occurrence_count >= 3 AND fault.last_occurrence > NOW() - INTERVAL '7 days'
   OR fault.acknowledged_at IS NOT NULL AND fault.diagnosed_at IS NULL
THEN auto-add to handover
WITH owner = fault.acknowledged_by OR fault.reporter
```

**Fields pulled:**
- Fault code, description, equipment
- Severity, occurrence count
- Last occurrence timestamp
- **Next action:**
  - No WO → "Create work order"
  - Recurring → "Investigate root cause"
  - Undiagnosed → "Complete diagnosis"

---

### 1.5 Document Events (Manual Only)

**INCLUDE (Manual Add Only):**
- New safety bulletin affecting equipment
- Manual section flagged as "critical for next shift"
- Procedure change notification

**EXCLUDE:**
- Routine document views
- Historical manuals with no relevance to current work

**Manual-only rule:**
```
No auto-add for documents.
User must explicitly add via "Add to Handover" action.
```

**Fields required (user input):**
- Document title, section reference
- **Risk:** "What is the risk if not read?"
- **Next action:** "What must the next shift do?"
- Owner: defaults to current user, can reassign

---

### 1.6 Manual Notes (Structured Only)

**NOT ALLOWED:**
- Blank comment boxes
- Freeform text without context

**ALLOWED (Structured Prompts):**
User must answer 3 questions:

1. **What is the risk?**
   - Dropdown: `safety_risk`, `equipment_damage`, `operational_delay`, `regulatory_issue`, `other`
   - Text (max 200 chars): Describe the specific risk

2. **What is blocked or pending?**
   - Text (max 200 chars): What cannot proceed until resolved

3. **What must the next shift do?**
   - Text (max 200 chars): Specific action, not "monitor" or "check"

**Validation:**
- All 3 fields required
- Risk dropdown must be selected
- Next action cannot contain vague words: "monitor", "check", "review", "update"
  - Force specificity: "Check coolant temp at 0800", not "Check coolant"

---

## Section 2: Handover Item Schema

Every handover item, regardless of source, conforms to this schema.

### Core Fields

```typescript
interface HandoverItem {
  // Identity
  id: string;                    // UUID
  handover_id: string;            // Parent handover UUID
  yacht_id: string;               // Yacht isolation

  // Source
  source_type: 'work_order' | 'inventory' | 'receiving' | 'fault' | 'document' | 'manual_note';
  source_id: string | null;       // UUID of source entity (null for manual notes)

  // Ownership
  owner_id: string;               // User UUID - WHO must handle this
  owner_name: string;             // Display name

  // Risk & Priority
  risk_category: 'safety_risk' | 'equipment_damage' | 'operational_delay' | 'regulatory_issue' | 'other';
  priority: 1 | 2 | 3;            // 1=urgent, 2=high, 3=normal

  // Content
  title: string;                  // Max 100 chars, auto-generated from source
  summary_text: string;           // Auto-generated context from source
  next_action: string;            // Max 200 chars, required, specific

  // Status
  status: 'draft' | 'published' | 'acknowledged' | 'archived';

  // Timestamps
  created_at: datetime;
  published_at: datetime | null;
  acknowledged_at: datetime | null;
  acknowledged_by: string | null; // User UUID
  archived_at: datetime | null;

  // Immutability
  is_published: boolean;          // Once true, item is immutable
}
```

### Field Rules

**Title:**
- Auto-generated from source
- Format depends on source_type:
  - `work_order`: "WO-{number}: {title}"
  - `inventory`: "{part_name} - {issue_type}"
  - `receiving`: "Delivery Issue: PO-{number}"
  - `fault`: "{equipment_name} - {fault_code}"
  - `document`: "Manual: {title} - {section}"
  - `manual_note`: User-provided (max 100 chars)

**Summary Text:**
- Auto-populated from source entity fields
- Read-only (user cannot edit)
- Shows context: last action, current state, issue description

**Next Action:**
- User can edit BEFORE publish
- Must be specific and actionable
- Validated against vague terms list
- Required field (cannot be empty)

**Owner:**
- Defaults to:
  - WO: assigned_to
  - Inventory: last user who touched it
  - Receiving: receiving user
  - Fault: acknowledged_by or reporter
  - Manual note: current user
- Can be reassigned BEFORE publish

**Priority:**
- Auto-derived from source:
  - WO priority `critical` → 1 (urgent)
  - WO priority `high` → 2 (high)
  - Fault severity `critical` → 1 (urgent)
  - Inventory critical part → 1 (urgent)
  - All others → 3 (normal)
- User can override BEFORE publish

---

## Section 3: Lifecycle & Accountability

### 3.1 Four States (No More, No Less)

```
Draft → Published → Acknowledged → Archived
```

**State Rules:**

| State        | Who Can Edit | Who Can See | Transitions To        |
|--------------|--------------|-------------|-----------------------|
| Draft        | Creator      | Creator     | Published             |
| Published    | **No one**   | All crew    | Acknowledged, Archived|
| Acknowledged | **No one**   | All crew    | Archived              |
| Archived     | **No one**   | Read-only   | None (terminal)       |

**Key Invariant:**
> Once `published`, the item is **immutable**. Corrections go into the next handover.

---

### 3.2 Lifecycle Flow

#### Step 1: **Creation (Draft State)**

**Trigger:**
- Auto-population from eligibility rules (runs every hour, or on-demand)
- Manual "Add to Handover" action from entity page

**What happens:**
1. System creates handover item with status = `draft`
2. Populates: source, owner, title, summary, next_action (derived)
3. Creator can:
   - Edit next_action (refine specificity)
   - Reassign owner
   - Adjust priority
   - Delete item (if added by mistake)

**Constraints:**
- Draft items are NOT visible to other users
- Draft items do NOT appear in handover brief
- Draft state expires after 24 hours → auto-delete

---

#### Step 2: **Publication (Published State)**

**Trigger:**
- End of shift (manual publish button)
- Scheduled daily (e.g., 0800, 2000 ship time)
- Captain/HOD can publish anytime

**What happens:**
1. All draft items for this handover → status = `published`
2. Set `published_at` timestamp
3. Set `is_published` = true (immutable flag)
4. Create immutable snapshot (JSON blob) for audit
5. Notify next shift (in-app, not email)

**Validation:**
- Refuse publish if ANY item has:
  - Empty next_action
  - Vague next_action (contains banned words)
  - No owner assigned
- Show error: "Cannot publish: 3 items need specific next actions"

**Immutability:**
- Once published, NO fields can be edited
- If mistake found, user must:
  - Add correction as NEW handover item
  - Link to original item (reference field)

---

#### Step 3: **Acknowledgment (Acknowledged State)**

**Trigger:**
- Next shift clicks "Acknowledge" on each item
- Bulk acknowledge (with caution - requires confirmation)

**What happens:**
1. Set status = `acknowledged`
2. Set `acknowledged_at` timestamp
3. Set `acknowledged_by` user_id
4. Item remains visible but marked "Read"

**Read-Receipt Rules:**
- Each item must be individually acknowledged
- Timestamp + user ID recorded
- No reminders unless:
  - Priority 1 (urgent) not acknowledged within 1 hour
  - Priority 2 (high) not acknowledged within 4 hours
  - Priority 3 (normal) not acknowledged within shift start + 2 hours

**Reminder Format:**
- In-app badge count (not push notification)
- Dashboard alert: "3 handover items pending acknowledgment"
- NO Slack-style pings

**Accountability Query:**
```sql
-- Who hasn't acknowledged urgent items?
SELECT h.id, h.title, h.owner_name, h.published_at
FROM handover_items h
WHERE h.status = 'published'
  AND h.priority = 1
  AND h.published_at < NOW() - INTERVAL '1 hour'
  AND h.acknowledged_at IS NULL;
```

---

#### Step 4: **Archival (Archived State)**

**Trigger:**
- Auto-archive after 7 days (published_at + 7 days)
- Manual archive by Captain/HOD
- Linked source entity resolved (e.g., WO completed, fault closed)

**What happens:**
1. Set status = `archived`
2. Set `archived_at` timestamp
3. Move to read-only archive view
4. Remove from active handover brief

**Retention:**
- Archived items kept for 90 days (regulatory compliance)
- After 90 days → soft delete (flag for purge)
- Hard delete after 1 year (GDPR compliance if applicable)

---

### 3.3 Handover Document (Parent Entity)

Each shift has ONE handover document that contains multiple items.

```typescript
interface Handover {
  id: string;                    // UUID
  yacht_id: string;

  // Metadata
  shift_date: date;              // e.g., 2026-01-11
  shift_period: 'day' | 'night'; // Or '0800-2000', '2000-0800'
  created_by: string;            // User UUID who published
  published_at: datetime | null;

  // Status
  status: 'draft' | 'published' | 'archived';

  // Items
  items: HandoverItem[];         // Nested array (or separate table with handover_id FK)

  // Snapshot (Immutability)
  snapshot: JSON | null;         // Immutable copy on publish

  // Signature
  signed_by: string | null;      // User UUID (shift lead or HOD)
  signed_at: datetime | null;
}
```

**Handover Document Lifecycle:**
1. **Draft:** Items being added, not yet published
2. **Published:** Shift ended, handover is live, items visible to next shift
3. **Archived:** 7 days old, moved to historical view

**Signature Rule:**
- Handover must be **signed** by shift lead or HOD before next shift starts
- Signature = acknowledgment that all critical items are captured
- Unsigned handovers older than 4 hours trigger alert to Captain

---

## Section 4: Integration Points (Engineer-Ready)

### 4.1 Work Order Integration

**Database Hook:**
```sql
-- Trigger on pms_work_orders table
CREATE TRIGGER auto_add_to_handover_wo
AFTER INSERT OR UPDATE ON pms_work_orders
FOR EACH ROW
WHEN (
  NEW.status IN ('in_progress', 'blocked', 'pending_parts')
  OR (NEW.priority IN ('critical', 'high') AND NEW.status != 'completed')
)
EXECUTE FUNCTION fn_auto_add_handover_item('work_order', NEW.id, NEW.assigned_to);
```

**API Endpoint:**
- `POST /v1/handover/auto-populate` (cron job every hour)
- Scans `pms_work_orders` table for eligible WOs
- Creates draft handover items if not already present

---

### 4.2 Inventory Integration

**Database Hook:**
```sql
-- Trigger on inventory_transactions or pms_parts table
CREATE TRIGGER auto_add_to_handover_inventory
AFTER INSERT OR UPDATE ON inventory_transactions
FOR EACH ROW
WHEN (
  (NEW.transaction_type = 'cycle_count' AND NEW.actual_count != NEW.system_count)
  OR (NEW.transaction_type = 'usage' AND NEW.work_order_id IS NULL AND NEW.quantity > threshold)
)
EXECUTE FUNCTION fn_auto_add_handover_item('inventory', NEW.part_id, NEW.user_id);
```

**Fields to Pull:**
- `pms_parts.name`, `part_number`, `location`
- `inventory_transactions.expected_count`, `actual_count`
- `inventory_transactions.user_id` → owner

---

### 4.3 Receiving Integration

**Database Hook:**
```sql
-- Trigger on pms_receiving table
CREATE TRIGGER auto_add_to_handover_receiving
AFTER INSERT ON pms_receiving
FOR EACH ROW
WHEN (
  NEW.quantity_received != (SELECT quantity FROM pms_purchase_orders WHERE id = NEW.purchase_order_id)
  OR NEW.damage_reported = TRUE
  OR NEW.paperwork_complete = FALSE
)
EXECUTE FUNCTION fn_auto_add_handover_item('receiving', NEW.id, NEW.received_by);
```

**Fields to Pull:**
- `pms_purchase_orders.po_number`, `supplier_name`
- `pms_receiving.quantity_ordered`, `quantity_received`
- `pms_receiving.damage_notes`, `missing_documents`

---

### 4.4 Fault Integration

**Database Hook:**
```sql
-- Trigger on pms_faults table
CREATE TRIGGER auto_add_to_handover_fault
AFTER INSERT OR UPDATE ON pms_faults
FOR EACH ROW
WHEN (
  (NEW.severity IN ('critical', 'high') AND NEW.work_order_id IS NULL)
  OR (NEW.occurrence_count >= 3 AND NEW.last_occurrence > NOW() - INTERVAL '7 days')
)
EXECUTE FUNCTION fn_auto_add_handover_item('fault', NEW.id, COALESCE(NEW.acknowledged_by, NEW.reported_by));
```

**Fields to Pull:**
- `pms_faults.fault_code`, `title`, `description`
- `pms_equipment.name` (joined)
- `pms_faults.severity`, `occurrence_count`, `last_occurrence`

---

### 4.5 Document Integration (Manual Only)

**No automatic triggers.**

User must explicitly:
1. View document in viewer
2. Click "Add to Handover" action
3. Fill structured prompts:
   - "What is the risk?"
   - "What must the next shift do?"

**API:**
- `POST /v1/handover/items`
- Body:
  ```json
  {
    "source_type": "document",
    "source_id": "doc_chunk_uuid",
    "risk_category": "safety_risk",
    "risk_description": "New MTU bulletin affects coolant system",
    "next_action": "Read section 4.2 before next generator service"
  }
  ```

---

## Section 5: Guardrails (Enforcement Rules)

### GUARDRAIL 1: Handover ≠ Task Creation

**Rule:** Users CANNOT create new work orders directly from handover.

**Why:**
- Prevents lazy deferral ("just put it in handover")
- Maintains clear responsibility chain
- Ensures proper WO creation flow (with all required fields)

**Correct Flow:**
```
User sees handover item → "Fault: Generator 2 overheating"
↓
Handover links to fault entity (source_id)
↓
User clicks "View Fault" → navigates to fault page
↓
From fault page, user clicks "Create Work Order" (standard action)
↓
WO created with proper context, assigned, prioritized
```

**UI Enforcement:**
- Handover item has "View Source" button (NOT "Create WO")
- "View Source" navigates to fault/equipment/etc. page
- Actions available THERE, not in handover view

---

### GUARDRAIL 2: Read-Receipt Without Nagging

**Rule:** Next shift must acknowledge each item, but system doesn't spam.

**Implementation:**
1. **Acknowledgment Required:**
   - Each handover item has "Acknowledge" button
   - Cannot mark as acknowledged without clicking (no bulk auto-ack)
   - Timestamp + user_id recorded

2. **Reminder Thresholds:**
   - Priority 1 (urgent): Reminder after 1 hour if not acknowledged
   - Priority 2 (high): Reminder after 4 hours
   - Priority 3 (normal): Reminder after shift start + 2 hours

3. **Reminder Format:**
   - In-app badge count (e.g., "3 pending")
   - Dashboard alert box (top of page)
   - NO push notifications
   - NO email
   - NO Slack pings

4. **Escalation (Captain Visibility):**
   - If urgent item not acknowledged after 2 hours → alert to Captain
   - Captain can see: who owns item, when published, why not acknowledged

**Query for Dashboard Badge:**
```sql
-- Count unacknowledged items for current user
SELECT COUNT(*)
FROM handover_items
WHERE owner_id = $user_id
  AND status = 'published'
  AND acknowledged_at IS NULL;
```

---

### GUARDRAIL 3: No Edits After Publish

**Rule:** Published handover items are immutable.

**Why:**
- Audit integrity (maritime regulations)
- Prevents "covering up" mistakes
- Forces clear correction process

**Correction Flow:**
```
User finds error in published item
↓
User creates NEW handover item
↓
References original item in "Corrects Item #123"
↓
Original item remains visible (with correction link)
```

**Database Enforcement:**
```sql
-- Row-level security policy
CREATE POLICY no_update_published ON handover_items
FOR UPDATE
USING (is_published = FALSE);
```

---

### GUARDRAIL 4: Vague Next Actions Blocked

**Rule:** Next action field cannot contain vague terms.

**Banned Words:**
- "monitor"
- "check" (unless followed by specific metric)
- "review"
- "update"
- "watch"
- "inspect" (unless followed by specific component)

**Validation:**
```typescript
const VAGUE_TERMS = ['monitor', 'check', 'review', 'update', 'watch'];

function validateNextAction(text: string): boolean {
  const lowerText = text.toLowerCase();

  // Check for vague terms
  for (const term of VAGUE_TERMS) {
    if (lowerText.includes(term)) {
      // Exception: "check coolant temp at 0800" is OK
      // "check generator" is NOT OK
      const hasSpecificity = /\b(at|by|before|until|if)\b/.test(lowerText);
      if (!hasSpecificity) {
        return false; // Reject
      }
    }
  }

  // Must be at least 20 chars (forces specificity)
  if (text.length < 20) {
    return false;
  }

  return true;
}
```

**Error Message:**
> "Next action must be specific. Instead of 'Check generator', say 'Check generator coolant temp at 0800, log reading'."

---

## Section 6: Summary (The Contract)

### What Engineers Implement:

1. **Auto-Population Engine**
   - Cron job (hourly): scan WOs, inventory, receiving, faults
   - Apply eligibility rules
   - Create draft handover items

2. **Handover Item CRUD**
   - Create: auto or manual (with validation)
   - Read: current handover + archives
   - Update: ONLY if status = `draft`
   - Delete: ONLY if status = `draft`

3. **Publish Workflow**
   - Validate all items (next_action, owner)
   - Create immutable snapshot
   - Transition status: `draft` → `published`
   - Notify next shift (in-app)

4. **Acknowledgment System**
   - Individual item acknowledgment
   - Timestamp + user_id
   - Reminder logic (thresholds by priority)
   - Dashboard badge count

5. **Lifecycle Management**
   - Auto-archive after 7 days
   - Retention for 90 days
   - Hard delete after 1 year

6. **Guardrail Enforcement**
   - Block WO creation from handover view
   - Validate next_action (no vague terms)
   - Immutability after publish (DB policy)
   - Read-receipt reminders (no spam)

---

### What Product/Design Owns:

1. **UI for Handover Brief**
   - Dashboard widget or `/briefing` page
   - Show: items by priority, grouped by status
   - Actions: View Source, Acknowledge, (if draft) Edit

2. **Structured Input Forms**
   - 3-question prompt for manual notes
   - Dropdown for risk_category
   - Validation error messages

3. **Captain Visibility**
   - Handover history (weekly, monthly)
   - Unacknowledged items report
   - Signature audit trail

4. **Archive View**
   - Read-only historical handovers
   - Search by date, owner, source type
   - Export to PDF (if needed for compliance)

---

**END OF CONTRACT**

This is the execution foundation. Implementation details (file names, component structure) come next, but ONLY after this contract is validated and locked.
