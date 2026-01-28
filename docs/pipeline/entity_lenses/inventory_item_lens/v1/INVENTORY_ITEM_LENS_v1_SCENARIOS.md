# Inventory Item Lens: User Journeys & Scenarios

**Version**: v1
**Date**: 2026-01-27
**Parent Document**: `INVENTORY_ITEM_LENS_v1_FINAL.md`

---

# 10 REAL-WORLD SCENARIOS

## Scenario 1: Emergency Breakdown - Find Part Fast

**Actor**: Chief Engineer (Mike)
**Context**: Generator #2 failed. Alarm blaring. 12 guests on board.
**Physical State**: Engine room, 45C, ear protection, one hand free

### User Journey

| Step | Traditional (7 steps) | Celeste (3 steps) |
|------|----------------------|-------------------|
| 1 | Open inventory system | Type "cat fuel filter" |
| 2 | Navigate to parts module | See result with stock + location |
| 3 | Search by part number | Tap to focus |
| 4 | Find part in list | See "Engine Room Store - Shelf B2" |
| 5 | Check stock level | See "3 units available" |
| 6 | Note location | [Use for WO] button visible |
| 7 | Walk to location | - |

**Steps Saved**: 57%

### Auto-Population

Query: "cat fuel filter" or "1R-0751"

**Extracted**:
- PART_NAME = "cat fuel filter" OR PART_NUMBER = "1R-0751"

**Pre-filled on [Use for WO]**:
- `part_id` = resolved UUID
- `usage_reason` = "work_order"
- `quantity` = 1 (default)

### Audit Entry

```json
{
  "action": "consume_part",
  "entity_type": "part",
  "entity_id": "filter-uuid",
  "old_values": {"quantity_on_hand": 3},
  "new_values": {"quantity_on_hand": 2},
  "signature": {},
  "metadata": {
    "work_order_id": null,
    "quantity": 1,
    "context": "breakdown_response"
  }
}
```

### Unhappy Path

| Condition | Behavior |
|-----------|----------|
| Part not found | "No results for 'xyz'" |
| Out of stock | Show 0 with red badge + [Add to Shopping List] prominent |
| Part deactivated | 409 "Part deactivated on {date}" + [Reactivate] option |

---

## Scenario 2: Pre-Service Parts Check

**Actor**: ETO (Sarah)
**Context**: 500-hour service on Main Engine #1 scheduled for tomorrow
**Physical State**: Workshop, laptop, planning mode

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open maintenance schedule | Type "parts for ME1 service" |
| 2 | Find the task | Backend surfaces related manual section |
| 3 | Open equipment record | "Page 234, Section 1.1, MTU Manual" |
| 4 | Find linked parts | Click → see parts mentioned |
| 5 | Check each part's stock | Color-coded stock status |
| 6 | Create shopping list for missing | [Add to Shopping List] pre-filled |

**Steps Saved**: 50%

### Important Note

Celeste does NOT summarize parts needed. Instead:
1. RAG retrieves the manual section mentioning parts for this service
2. User clicks to see the source document
3. User identifies parts from authoritative source
4. User adds to shopping list as needed

**No AI guessing. Only surfacing facts.**

---

## Scenario 3: Record Part Usage for Work Order

**Actor**: Deckhand (Tom)
**Context**: Just replaced impeller, work order WO-2026-0045 open
**Physical State**: Deck, phone, hands semi-clean

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open work order | Type "used impeller for WO-0045" |
| 2 | Navigate to parts tab | System detects consumption intent |
| 3 | Search for part | Action button: "Use Part" |
| 4 | Select part | Pre-fills part + WO + qty=1 |
| 5 | Enter quantity | Confirm and submit |
| 6 | Save | Stock auto-decremented |
| 7 | Verify stock updated | Audit trail created |

**Steps Saved**: 57%

### Auto-Population

Query: "used impeller for WO-0045"

**Extracted**:
- ACTION = "consume_part" (from "used")
- PART_NAME = "impeller"
- WORK_ORDER = "WO-0045"

**Pre-filled**:
- `part_id` = lookup("impeller", yacht_id) → UUID
- `work_order_id` = lookup("WO-0045", yacht_id) → UUID
- `quantity` = 1

### Explicit Action Request

If Tom types just "log part usage":
- Action button renders in search results
- Clicking opens modal with empty form
- Tom selects part manually

---

## Scenario 4: Receiving Parts Delivery

**Actor**: Bosun (Carlos)
**Context**: DHL delivery arrived with 3 boxes
**Physical State**: Gangway, needs to clear deck quickly

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Find PO in system | Type "receive delivery" or scan |
| 2 | Open PO | System matches to pending orders |
| 3 | Enter each line item | Shows matched items with expected qty |
| 4 | Match to part records | Confirm matches |
| 5 | Update quantities | One-tap commit |
| 6 | Assign locations | Stock updated |
| 7 | Close receiving | Labels auto-generated |

**Steps Saved**: 43%

### Idempotency

If Carlos accidentally submits twice with same `idempotency_key`:
- Second request returns 409 `duplicate_request`
- No double-counting

### Discrepancy Handling

If ordered 2, received 1:
- System highlights discrepancy
- Options: "Accept Partial" | "Report Short" | "Reject"
- Notification to Purser for review

---

## Scenario 5: Monthly Inventory Audit

**Actor**: Purser (Diana)
**Context**: End of month compliance audit
**Physical State**: Walking through stores with tablet

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Print inventory list | Type "count engine room store" |
| 2 | Walk through store | See list filtered by location |
| 3 | Count each item | Tap item → enter actual count |
| 4 | Note discrepancies | System highlights differences |
| 5 | Return to computer | Adjustments applied real-time |
| 6 | Enter adjustments | Reasons required for variances |
| 7 | Save and verify | Audit trail automatic |

**Steps Saved**: 43%

### Large Adjustment Signature

If Diana adjusts from 10 to 2 (>50% change):

```
[Signature Required]

Large adjustment detected: 10 → 2 (80% reduction)

Reason: [Damaged units found during inspection]

By signing, I confirm this adjustment is accurate.

[Sign as Diana (Purser)]
```

### Audit Entry (SIGNED)

```json
{
  "action": "adjust_stock_quantity",
  "entity_type": "part",
  "entity_id": "filter-uuid",
  "old_values": {"quantity_on_hand": 10},
  "new_values": {"quantity_on_hand": 2},
  "signature": {
    "user_id": "diana-uuid",
    "role_at_signing": "purser",
    "signature_type": "stock_adjustment",
    "reason": "Damaged units found during inspection",
    "change_percentage": 0.8,
    "signed_at": "2026-01-27T09:45:00Z",
    "signature_hash": "sha256:..."
  }
}
```

---

## Scenario 6: Low Stock Alert Response

**Actor**: Chief Engineer (Mike)
**Context**: Received low stock notification
**Physical State**: Bridge, checking phone between tasks

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | See email/check system | Tap notification |
| 2 | Search for part | Goes directly to part |
| 3 | Verify stock level | Stock shown + minimum |
| 4 | Decide quantity to order | Suggested quantity shown |
| 5 | Navigate to shopping list | [Add to Shopping List] |
| 6 | Add item | Pre-filled from CTA payload |
| 7 | Set priority | One-tap submit |

**Steps Saved**: 57%

### Notification Payload

```json
{
  "topic": "low_stock",
  "level": "warning",
  "title": "Low Stock: CAT Fuel Filter 1R-0751",
  "body": "2 units remaining. Minimum is 3.",
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "filter-uuid",
    "quantity_requested": 2
  }
}
```

### Escalation Logic

If Mike dismisses without action:
1. Wait 12 hours → Re-notify crew who consumed the part
2. Wait 24 hours → Escalate to Chief Engineer
3. Wait 7 days → Prompt to update minimum quantity

---

## Scenario 7: Transfer Parts Between Locations

**Actor**: Bosun (Carlos)
**Context**: Moving spare impellers from forward store to engine room
**Physical State**: Standing in forward store

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open inventory | Type "transfer impeller to engine room" |
| 2 | Find part | System detects transfer intent |
| 3 | Find source location stock | Shows current locations |
| 4 | Reduce source quantity | Select from_location |
| 5 | Find destination record | Select to_location |
| 6 | Increase destination quantity | Enter quantity |
| 7 | Verify both updated | Submit → both locations updated |

**Steps Saved**: 43%

### Auto-Population

Query: "transfer 2 impellers to engine room"

**Extracted**:
- ACTION = "transfer_part"
- QUANTITY = 2
- PART_NAME = "impellers"
- LOCATION = "engine room" (to_location)

**Pre-filled**:
- `part_id` = lookup("impellers") → UUID
- `quantity` = 2
- `to_location` = "engine room"
- `from_location` = part's current location (default)

### Validation

If `from_location == to_location`:
- 400 `invalid_transfer`: "From and to locations must be different"

---

## Scenario 8: Write Off Damaged Parts

**Actor**: Chief Engineer (Mike)
**Context**: Found corroded filters during inspection
**Physical State**: Workshop, documenting findings

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Find part in system | Type "write off oil filters" |
| 2 | Document damage | Action: [Write Off Part] |
| 3 | Get supervisor approval | Fill: quantity, reason, notes |
| 4 | Create adjustment | Signature required |
| 5 | Update stock | Sign and submit |
| 6 | File paperwork | Audit trail automatic |

**Steps Saved**: 50%

### Signature Required

```
[Write Off Part - Signature Required]

Part: Oil Filter VP-3847293
Quantity to write off: 3

Reason: [damaged ▼]
Notes: [Found corroded during monthly inspection. Salt water ingress suspected.]

By signing, I confirm these parts are unfit for use.

[Sign as Mike (Chief Engineer)]
```

---

## Scenario 9: Deactivate Obsolete Part

**Actor**: Captain
**Context**: Part replaced by new model, should not be ordered again
**Physical State**: Office, reviewing inventory

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Find part | Type "deactivate old impeller model" |
| 2 | Mark as inactive | Action: [Deactivate Part] |
| 3 | Add reason | Fill reason field |
| 4 | Get approval | Signature required |
| 5 | Update system | Sign and submit |
| 6 | Notify team | Audit + notification triggered |

**Steps Saved**: 40%

### Effect of Deactivation

After deactivation, any mutation attempt returns:
```
409 Conflict
{
  "error": "part_deactivated",
  "message": "Part 'Old Impeller Model' was deactivated on 2026-01-27. Reactivate to continue.",
  "deactivated_by": "Captain John",
  "deletion_reason": "Replaced by new model P/N 12345"
}
```

---

## Scenario 10: Reverse Erroneous Transaction

**Actor**: Manager
**Context**: Discovered incorrect consumption entry from last week
**Physical State**: Office, reviewing audit trail

### User Journey

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Find transaction | View part history |
| 2 | Identify error | See transaction in audit |
| 3 | Request correction | Action: [Reverse Transaction] |
| 4 | Document reason | Fill reason |
| 5 | Get approval | Signature required |
| 6 | Apply correction | Correcting entry created |
| 7 | Verify | Both entries visible in audit |

**Steps Saved**: 40%

### Reversal Entry

Original transaction:
```json
{
  "id": "txn-001",
  "transaction_type": "consumed",
  "quantity_change": -5,
  "quantity_after": 10
}
```

Reversal transaction:
```json
{
  "id": "txn-002",
  "transaction_type": "reversed",
  "quantity_change": +5,
  "quantity_after": 15,
  "reverses_transaction_id": "txn-001"
}
```

### Important

- Original transaction remains visible (immutable ledger)
- Reversal creates correcting entry
- Net effect: stock restored
- Full audit trail preserved

---

# ACCEPTANCE TESTS FROM SCENARIOS

| # | Scenario | Happy Path Test | Unhappy Path Test |
|---|----------|-----------------|-------------------|
| 1 | Emergency breakdown | deckhand consume → 200, stock decrements | consume deactivated part → 409 |
| 2 | Pre-service check | view parts → 200, shows stock | - |
| 3 | Log usage for WO | consume with WO → 200, links to WO | WO wrong status → 400 |
| 4 | Receiving | receive → 200, stock increments | duplicate idempotency → 409 |
| 5 | Inventory audit | small adjust → 200 | large adjust no sig → 400 |
| 6 | Low stock alert | add_to_shopping_list → 200 | - |
| 7 | Transfer | transfer → 200, both locations updated | from=to → 400 |
| 8 | Write off | write_off + sig → 200 | write_off no sig → 400 |
| 9 | Deactivate | deactivate + sig → 200 | already deactivated → 409 |
| 10 | Reverse | reverse + sig → 200 | already reversed → 409 |

---

# SCENARIOS SUMMARY

| # | Scenario | Steps Saved |
|---|----------|-------------|
| 1 | Emergency Part Lookup | 57% |
| 2 | Pre-Service Parts Check | 50% |
| 3 | Record Part Usage | 57% |
| 4 | Receiving Parts Delivery | 43% |
| 5 | Monthly Inventory Audit | 43% |
| 6 | Low Stock Alert Response | 57% |
| 7 | Transfer Parts | 43% |
| 8 | Write Off Damaged Parts | 50% |
| 9 | Deactivate Obsolete Part | 40% |
| 10 | Reverse Erroneous Transaction | 40% |

**Average Step Reduction**: 48%

---

**END OF SCENARIOS**
