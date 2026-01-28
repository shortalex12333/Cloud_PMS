# Purchasing Cluster - User Journeys

**Cluster:** PROCURE (Shopping List / Purchase Orders / Supplier Management)
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Shopping List Item / Purchase Order
**Entry points:** Parts Reorder Alert → Add to Shopping List, Work Order → Order Part, Search → PO Detail
**Terminal states:** fulfilled (received), cancelled
**Can create other entities:** Purchase Orders, Receiving Sessions (cross-cluster), Handover Entries
**Highest-risk action:** approve_purchase (signature required at irreversible commit — financial commitment to supplier)

---

## SCOPE

**Cluster:** PROCURE
**Actions covered:** 8 / 8
**MVP actions:** 8
**Future actions:** 0
**Signature-required actions:** 1 (approve_purchase when total > $1000 or captain approval required)

**Purpose:** Request parts, get approval, create purchase orders, track deliveries. Maintain procurement accountability and budget control.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Shopping List = `IDLE` → `CANDIDATE`, Approval Flow = `CANDIDATE` → `ACTIVE`
**Primary actions shown:** Max 2-3 (add_to_shopping_list, approve_shopping_item prioritized)
**RAG influence:** Prefills part + quantity from work order context, suggests urgency, never auto-commits
**Conditional signature:** Prompt appears if approval >$1000 or critical urgency

---

## STATE EXPLOSION VIGILANCE

This cluster is **high-stakes financial**: every action leads toward supplier payment.

❌ **NO silent state transitions** — Shopping list status changes logged explicitly
❌ **NO implicit commits** — PO creation requires explicit approval
❌ **NO derived state without storage** — All approval steps stored in shopping_list table
❌ **NO system-inferred mutations** — User must confirm every procurement step

**This is a financial gravity zone.** Every shopping list approval = budget commitment. Every PO = supplier contract.

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (6)

| Action | Risk | Signature | Pattern | Financial Impact | Status |
|--------|------|-----------|---------|------------------|--------|
| add_to_shopping_list | LOW | ❌ | `[SINGLE_STEP]` | No (request only) | ✅ MVP |
| edit_shopping_item | LOW | ❌ | `[SINGLE_STEP]` | No (pre-approval edit) | ✅ MVP |
| approve_shopping_item | MEDIUM | Conditional | `[SINGLE_STEP]` | Yes (budget commitment) | ✅ MVP |
| create_purchase_order | MEDIUM | ❌ | `[SINGLE_STEP]` | Yes (supplier commitment) | ✅ MVP |
| cancel_shopping_item | LOW | ❌ | `[SINGLE_STEP]` | No (reverses request) | ✅ MVP |
| attach_invoice | LOW | ❌ | `[SINGLE_STEP]` | No (documentation only) | ✅ MVP |

### Read Actions (2)

| Action | Purpose | Status |
|--------|---------|--------|
| track_delivery | View delivery status for PO | ✅ MVP |
| show_pending_approvals | List shopping items awaiting approval | ✅ MVP |

---

## GOLD JOURNEY (Primary Path)

**Link:** Inferred from inventory receiving session (parts must be ordered first)

**Actions covered:**
- add_to_shopping_list (MUTATE_LOW)
- approve_shopping_item (MUTATE_MEDIUM, conditional signature)
- create_purchase_order (MUTATE_MEDIUM)
- [Cross-cluster] start_receiving_session → see `inventory_cluster_journeys.md`

**Pattern:** `[MULTI_STEP]` across cluster boundary

**This is the most common path:** Part needed → add to shopping list → approval → create PO → receive delivery

**Signature required when:**
- Total purchase order value > $1000
- Captain approval policy enabled (yacht-specific configuration)
- Supplier is new/unvetted

---

## JOURNEY VARIATIONS

### V1: Add Part to Shopping List (Request)

**WHO:** Any engineer
**TRIGGER:** Part needed for repair or restock
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views part: "Coolant Pump Seal (GEN-SEAL-001)"
2. Current quantity: 0
3. Clicks: [Order Part]
4. Form appears:
   ```
   Add to Shopping List

   Part: Coolant Pump Seal
   Part Number: GEN-SEAL-001

   Quantity: [numeric - required]

   Urgency: ○ Low  ● Normal  ○ High  ○ Critical

   Reason: [text area - required if Critical]
   "Why is this part needed?"

   Estimated Unit Cost: [$125.00] (pre-filled from part.unit_cost_usd)

   [Cancel]  [Add to Shopping List]
   ```
5. User enters:
   - Quantity: 2
   - Urgency: High
   - Reason: "Generator 2 pump seal failed. Need replacement for upcoming repair."
   - Cost: $125.00
6. Clicks [Add to Shopping List]
7. Success: "✓ Added to shopping list. Awaiting approval."

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT shopping_list (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     part_id = part_id,
     quantity = 2,
     urgency = 'high',
     urgency_reason = "Generator 2 pump seal failed...",
     requested_by = user_id,
     requested_by_name = user_name,
     requested_by_role = user_role,
     status = 'candidate',
     estimated_unit_cost_usd = 125.00,
     created_at = NOW()
   )

2. INSERT ledger_events (
     event_type='shopping_item_added',
     entity_type='shopping_list', entity_id=new_item_id,
     user_id, timestamp,
     summary="User added Coolant Pump Seal (qty: 2) to shopping list"
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Part exists
const part = await getPart(part_id);
if (!part) throw Error("Part not found");

// 2. Quantity positive
if (quantity <= 0) throw Error("Quantity must be positive");

// 3. If critical urgency, reason required
if (urgency === 'critical' && (!urgency_reason || urgency_reason.length < 10)) {
  throw Error("Critical urgency requires detailed reason (min 10 chars)");
}
```

#### System Guarantees

✅ Shopping item created with status='candidate'
✅ Awaits approval (cannot be ordered without approval)
✅ Ledger entry written (traceability)
✅ No signature required (informational request)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No purchase order created (approval required first)
❌ No supplier contacted
❌ No budget deducted (request only)
❌ No inventory changed

---

### V2: Approve Shopping Item (Budget Commitment)

**WHO:** Chief Engineer, Chief Officer, or Captain
**TRIGGER:** Shopping list item awaiting approval
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[CONDITIONAL_SIGNATURE]`

#### Screen Flow

1. Chief Engineer views pending approvals
2. Sees: "Coolant Pump Seal (GEN-SEAL-001) - Qty: 2 - Est. Cost: $250"
3. Requested by: Mike (3rd Engineer) - Urgency: High
4. Reason: "Generator 2 pump seal failed. Need replacement for upcoming repair."
5. Clicks item to review
6. Sees full details + part history
7. Clicks: [Approve]
8. Confirmation:
   ```
   Approve Shopping Item

   Part: Coolant Pump Seal (GEN-SEAL-001)
   Quantity: 2
   Estimated Cost: $250.00

   Requested by: Mike (3rd Engineer)
   Urgency: High

   ⚠️ Approving commits budget for this purchase.

   Approval Notes: [optional]

   [Cancel]  [Approve]
   ```
9. Chief Engineer clicks [Approve]
10. Success: "✓ Shopping item approved. Ready to create purchase order."

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE shopping_list
   SET status = 'approved',
       approved_by = user_id,
       approved_by_name = user_name,
       approved_at = NOW(),
       updated_at = NOW()
   WHERE id = shopping_item_id
     AND yacht_id = user_yacht_id
     AND status IN ('candidate')

2. INSERT ledger_events (
     event_type='shopping_item_approved',
     entity_type='shopping_list', entity_id=shopping_item_id,
     user_id, timestamp,
     summary="Chief Engineer approved Coolant Pump Seal (qty: 2, est. $250)"
   )

3. [If signature required] INSERT pms_audit_log (
     action_id='approve_shopping_item',
     entity_type='shopping_list', entity_id=shopping_item_id,
     old_values={status:'candidate'},
     new_values={status:'approved', approved_by: user_name},
     changes_summary="Approved shopping item: $250 commitment",
     user_id, timestamp, signature=<signature_data>, risk_level='medium'
   )

COMMIT
```

#### Signature Required When

**Conditional signature logic:**
- **Signature required** if ANY of:
  - Total estimated cost > $1000
  - Urgency = 'critical' AND captain_approval_required = TRUE (yacht config)
  - Supplier is new/unvetted (supplier.vetted = FALSE)

**No signature required** if:
- Cost ≤ $1000 AND urgency ≠ 'critical'
- Routine restock
- Approved supplier

#### Validation Rules

```typescript
// 1. User has approval authority
if (!['chief_engineer', 'chief_officer', 'captain', 'admin'].includes(user.role)) {
  throw Error("Insufficient permissions to approve");
}

// 2. Item in correct status
if (item.status !== 'candidate') {
  throw Error("Item already approved or committed");
}

// 3. Signature check (if required)
if (requiresSignature(item) && !signature_data) {
  throw Error("Signature required for this approval");
}
```

#### System Guarantees

✅ Status changed to 'approved'
✅ Approver logged (accountability)
✅ Budget commitment recorded
✅ Ledger entry written
✅ Signature required at irreversible commit (conditional)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No purchase order created yet (separate action)
❌ No supplier contacted yet
❌ No parts ordered (approval ≠ ordering)

---

### V3: Create Purchase Order (Supplier Commitment)

**WHO:** Chief Engineer or Captain
**TRIGGER:** Multiple approved shopping items ready to order from same supplier
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. Chief Engineer views approved shopping items
2. Sees 5 items approved, all from "Marine Parts Supply Co."
3. Clicks: [Create Purchase Order]
4. Form appears:
   ```
   Create Purchase Order

   Items Selected: 5

   1. Coolant Pump Seal (GEN-SEAL-001) - Qty: 2 - $250
   2. MTU Oil Filter (MTU-0001) - Qty: 10 - $450
   3. Hydraulic Hose (HYD-3875) - Qty: 5 - $200
   4. V-Belt Set (BELT-A45) - Qty: 1 - $75
   5. Impeller Kit (IMP-2024) - Qty: 3 - $225

   Total Items: 5
   Total Value: $1,200.00

   Supplier: [Marine Parts Supply Co.] (pre-filled or dropdown)

   Supplier Contact: [optional]

   Delivery Address: [pre-filled from yacht config]

   Expected Delivery: [date picker - optional]

   Notes: [optional]

   [Cancel]  [Create Purchase Order]
   ```
5. Chief Engineer reviews, clicks [Create Purchase Order]
6. Success: "✓ Purchase Order PO-2026-012 created. Send to supplier: [Email] [Print PDF]"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT pms_purchase_orders (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     po_number = 'PO-2026-012',  -- Auto-generated
     supplier_name = 'Marine Parts Supply Co.',
     supplier_contact = supplier_contact,
     total_items = 5,
     total_value_usd = 1200.00,
     status = 'draft',
     created_by = user_id,
     created_by_name = user_name,
     created_at = NOW()
   ) RETURNING id INTO new_po_id

2. FOR EACH shopping_item IN selected_items:
     UPDATE shopping_list
     SET status = 'committed',
         po_id = new_po_id,
         updated_at = NOW()
     WHERE id = shopping_item.id
       AND status = 'approved'

3. INSERT ledger_events (
     event_type='purchase_order_created',
     entity_type='purchase_order', entity_id=new_po_id,
     user_id, timestamp,
     summary="Chief Engineer created PO-2026-012 ($1,200, 5 items)"
   )

4. INSERT pms_audit_log (
     action_id='create_purchase_order',
     entity_type='purchase_order', entity_id=new_po_id,
     old_values={},
     new_values={po_number:'PO-2026-012', total_value:1200, items:5},
     changes_summary="Created purchase order: $1,200 supplier commitment",
     user_id, timestamp, risk_level='medium'
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. All items must be approved
for (const itemId of shopping_list_item_ids) {
  const item = await getShoppingListItem(itemId);
  if (item.status !== 'approved') {
    throw Error(`Item ${item.part_number} must be approved before adding to PO`);
  }
}

// 2. All items must be from user's yacht
const invalidItems = shopping_list_item_ids.filter(id =>
  item.yacht_id !== user.yacht_id
);
if (invalidItems.length > 0) {
  throw Error("Cannot create PO with items from different yachts");
}

// 3. Supplier name required
if (!supplier_name || supplier_name.length < 2) {
  throw Error("Supplier name required");
}
```

#### System Guarantees

✅ PO created with unique number (PO-YYYY-###)
✅ Shopping items linked to PO (status = 'committed')
✅ Supplier commitment logged
✅ Audit trail written (financial event)
✅ No signature required (informational) — approval already signed
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No email sent to supplier (manual or separate action)
❌ No inventory received yet (waiting for delivery)
❌ No payment made (PO ≠ payment)

---

### V4: Cancel Shopping Item

**WHO:** Requester or Chief Engineer
**TRIGGER:** Part no longer needed or request was error
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views shopping item: "Hydraulic Hose (HYD-3875) - Status: Candidate"
2. Clicks: [Cancel Item]
3. Confirmation:
   ```
   Cancel Shopping Item

   Part: Hydraulic Hose (HYD-3875)
   Quantity: 5
   Status: Candidate (not yet approved)

   Reason: [text area - optional]

   [Back]  [Cancel Item]
   ```
4. User enters: "Found spare hose in storage. No longer needed."
5. Clicks [Cancel Item]
6. Success: "✓ Shopping item cancelled"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE shopping_list
   SET status = 'cancelled',
       cancelled_by = user_id,
       cancelled_at = NOW(),
       cancellation_reason = "Found spare hose in storage...",
       updated_at = NOW()
   WHERE id = shopping_item_id
     AND yacht_id = user_yacht_id
     AND status IN ('candidate', 'approved')  -- Cannot cancel if committed to PO

2. INSERT ledger_events (
     event_type='shopping_item_cancelled',
     entity_type='shopping_list', entity_id=shopping_item_id,
     user_id, timestamp,
     summary="User cancelled Hydraulic Hose: Found spare hose in storage"
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Only requester or senior roles can cancel
if (item.requested_by !== user.id && !['chief_engineer', 'captain', 'admin'].includes(user.role)) {
  throw Error("Only requester or senior crew can cancel shopping items");
}

// 2. Cannot cancel if committed to PO
if (item.status === 'committed') {
  throw Error("Cannot cancel item already committed to purchase order. Cancel PO instead.");
}
```

#### System Guarantees

✅ Item status changed to 'cancelled'
✅ Reason logged (if provided)
✅ Ledger entry written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No PO affected (can only cancel pre-commit items)
❌ No supplier notified
❌ No refund issued (nothing was purchased)

---

### V5: Attach Invoice (Documentation)

**WHO:** Chief Engineer or Admin
**TRIGGER:** Invoice received from supplier after delivery
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views PO: "PO-2026-012 - Status: Received"
2. Clicks: [Attach Invoice]
3. Form appears:
   ```
   Attach Invoice to Purchase Order

   PO Number: PO-2026-012
   Supplier: Marine Parts Supply Co.
   Total Value: $1,200.00

   Invoice File: [Upload PDF/Image]

   Invoice Number: [optional text field]

   Invoice Date: [date picker - optional]

   Notes: [optional]

   [Cancel]  [Attach Invoice]
   ```
4. User uploads invoice PDF
5. Enters invoice number: "INV-54321"
6. Clicks [Attach Invoice]
7. Success: "✓ Invoice attached to PO-2026-012"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT pms_purchase_order_documents (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     po_id = po_id,
     document_type = 'invoice',
     file_url = 'https://.../invoices/INV-54321.pdf',
     invoice_number = 'INV-54321',
     invoice_date = '2026-01-20',
     uploaded_by = user_id,
     uploaded_by_name = user_name,
     uploaded_at = NOW()
   )

2. UPDATE pms_purchase_orders
   SET has_invoice = TRUE,
       updated_at = NOW()
   WHERE id = po_id

3. INSERT ledger_events (
     event_type='invoice_attached',
     entity_type='purchase_order', entity_id=po_id,
     user_id, timestamp,
     summary="User attached invoice INV-54321 to PO-2026-012"
   )

COMMIT
```

#### System Guarantees

✅ Invoice stored and linked to PO
✅ File uploaded to secure storage
✅ Ledger entry written (traceability)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

## READ-ONLY ACTIONS

### track_delivery

**Purpose:** View current delivery status for a purchase order

**Flow:**
- User views PO detail
- Sees: Status: Shipped (Expected: Jan 25, 2026)
- Optional: Tracking number, carrier, estimated arrival

**Pattern:** `[READ_ONLY]`

**Use case:** "When is my order arriving?"

---

### show_pending_approvals

**Purpose:** List all shopping items awaiting approval (Chief Engineer view)

**Flow:**
- Chief Engineer types: "pending approvals"
- System queries: WHERE status='candidate'
- Shows list with requester, part, quantity, urgency, cost

**Pattern:** `[READ_ONLY]`

**Use case:** Daily procurement review

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] add_to_shopping_list - V1
- [x] edit_shopping_item - (Similar to add, pre-approval metadata changes)
- [x] approve_shopping_item - V2
- [x] create_purchase_order - V3
- [x] cancel_shopping_item - V4
- [x] attach_invoice - V5

### Read Actions
- [x] track_delivery - Brief description
- [x] show_pending_approvals - Brief description

**Coverage:** 8/8 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why | Financial Impact? |
|--------|------------|-----|-------------------|
| add_to_shopping_list | ❌ | No signature required (informational) | No |
| edit_shopping_item | ❌ | No signature required (informational) | No |
| approve_shopping_item | Conditional | Signature required at irreversible commit (if >$1000 or critical) | Yes |
| create_purchase_order | ❌ | No signature required (informational) | Yes |
| cancel_shopping_item | ❌ | No signature required (informational) | No |
| attach_invoice | ❌ | No signature required (informational) | No |

**Rule:** Signature required at budget commitment (approval) ONLY when high-value or critical. PO creation does NOT require signature because approval already captured commitment.

**Conditional Signature Logic (approve_shopping_item):**
- Signature required if: cost > $1000 OR urgency='critical' + captain_approval_required OR new supplier
- Otherwise: No signature (routine approval)

**Financial Impact Column:** 3 actions affect budget/supplier commitments.

---

## PURCHASING STATE MACHINE

### Shopping List Item Lifecycle
```
NULL (no item)
  ↓ add_to_shopping_list
CANDIDATE (awaiting approval)
  ↓ edit_shopping_item (optional)
CANDIDATE (updated)
  ↓ approve_shopping_item (+ conditional signature)
APPROVED (ready to order)
  ↓ create_purchase_order
COMMITTED (linked to PO)
  ↓ [Cross-cluster] start_receiving_session
  ↓ [Cross-cluster] commit_receiving_session
FULFILLED (received)

Alternative paths:
CANDIDATE → cancel_shopping_item → CANCELLED
APPROVED → cancel_shopping_item → CANCELLED
```

### Purchase Order Lifecycle
```
NULL (no PO)
  ↓ create_purchase_order
DRAFT (created, ready to send)
  ↓ [Manual action] send to supplier
SENT (supplier notified)
  ↓ [Supplier ships]
SHIPPED (in transit)
  ↓ start_receiving_session
RECEIVING (delivery arrived, checking items)
  ↓ commit_receiving_session
RECEIVED (delivery completed)
  ↓ attach_invoice
CLOSED (invoice attached, payment processed)
```

**Guardrails:**
- Cannot create PO from unapproved items
- Cannot cancel item after committed to PO
- Cannot start receiving session without PO (unless manual receiving)
- Cannot attach invoice before PO received

---

## CROSS-CLUSTER RELATIONSHIPS

### Purchasing → Inventory
- `create_purchase_order` enables `start_receiving_session`
- `commit_receiving_session` marks shopping items as 'fulfilled'
- See: `inventory_cluster_journeys.md` (receiving session flow)

### Purchasing ← Faults / Work Orders
- Fault diagnosis may recommend parts → add to shopping list
- Work order parts list may trigger procurement
- See: `faults_cluster_journeys.md`, `work_orders_cluster_journeys.md`

### Purchasing → Handover
- Critical procurement delays can be added to handover
- See: `handover_cluster_journeys.md`

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Unapproved Item in PO Creation
**Trigger:** User tries to create PO including items with status='candidate'
**System behavior:** Show error: "Cannot create PO. 2 items not yet approved: [list]"
**Cannot proceed until:** All items approved

### 2. Duplicate Shopping Request
**Trigger:** User adds part to shopping list that already has pending request
**System behavior:** Show warning: "Existing shopping request for this part (qty: 5). Add another request or increase quantity?"
**User choice:** Add duplicate OR update existing

### 3. Approval Authority Missing
**Trigger:** 3rd Engineer tries to approve shopping item
**System behavior:** Show error: "Insufficient permissions. Only Chief Engineer or Captain can approve."
**Cannot proceed:** Action blocked

### 4. High-Value Approval Without Signature
**Trigger:** User approves item >$1000 without providing signature
**System behavior:** Show prompt: "This approval requires signature (total: $1,200)"
**Cannot proceed until:** Signature captured

### 5. Cancel Committed Item
**Trigger:** User tries to cancel item already committed to PO
**System behavior:** Show error: "Cannot cancel. Item already committed to PO-2026-012. Cancel entire PO instead."
**Cannot proceed:** Action blocked

**Guardrail principle:** System stops for financial commitments, approval authority violations, and state conflicts.

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | add_to_shopping_list, edit_shopping_item, approve_shopping_item, create_purchase_order, cancel_shopping_item, attach_invoice | 6 |
| `[READ_ONLY]` | track_delivery, show_pending_approvals | 2 |
| `[CONDITIONAL_SIGNATURE]` | approve_shopping_item (when >$1000 or critical) | 1 |

---

## FINANCIAL GRAVITY NOTES

**Actions with financial impact: 2**
- approve_shopping_item (budget commitment)
- create_purchase_order (supplier commitment)

**Why only 1 conditional signature despite 2 financial actions?**
- **approve_shopping_item** = irreversible budget commitment (requires signature if high-value)
- **create_purchase_order** = informational (approval signature already captured commitment)

**This maintains healthy signature rate (<10%).**

---

## APPROVAL WORKFLOW CLARITY

**Critical distinction:**
- **Approval** = budget commitment ("yes, we will buy this")
- **PO creation** = execution of approved budget ("send order to supplier")

**Signature happens at commitment (approval), not at execution (PO).**

This prevents "sign everything" fatigue while maintaining financial accountability.

---

**Status:** Purchasing cluster fully documented. Financial gravity acknowledged. Conditional signature logic locked. Template validated. Ready for equipment cluster (Batch 2 final file).
