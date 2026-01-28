# Work Order Lens - PHASE 4: Micro-Actions Contract

**Status**: COMPLETE
**Action Count**: 6 (maximum for operational lens)
**Created**: 2026-01-24

---

## BLOCKERS CARRIED FORWARD

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| **B1** | Legacy RLS pattern | All write actions | Migrate to `public.get_user_yacht_id()` |
| **B3** | `user_has_role()` may not be deployed | Role-based actions | Verify or deploy function |

---

## ACTION ACTIVATION DOCTRINE

### When Actions Appear

```
Actions appear ONLY when:
1. User has queried for work order(s)
2. A SINGLE work order is focused (entity card displayed)
3. User has appropriate role for the action

Actions NEVER appear:
- On search results list (multiple WOs)
- Before entity focus
- As floating/ambient buttons
```

### Action Trigger Types

| Trigger | Description | Example |
|---------|-------------|---------|
| **FOCUS** | Entity card is displayed | User clicked WO in results |
| **QUERY_INTENT** | Query contains action keyword | "complete WO-2026-042" |
| **CONTEXT** | Related entity provides context | From Fault: "create WO for this" |

---

## THE 6 ACTIONS

| # | Action | Mutation Tier | Signature Required |
|---|--------|--------------|-------------------|
| 1 | Create Work Order | WRITE | NO |
| 2 | Update Work Order | WRITE | NO |
| 3 | Complete Work Order | WRITE | NO (but confirmation) |
| 4 | Add Note | WRITE | NO |
| 5 | Reassign Work Order | WRITE | YES (HoD) |
| 6 | Archive Work Order | WRITE | YES (Captain/HoD) |

---

## Action 1: Create Work Order

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `create_work_order` |
| **Blocker Status** | B1 (RLS legacy) |
| **Mutation Tier** | WRITE |
| **Signature Required** | NO |

### Intent Phrasing

- "create work order for generator"
- "new work order"
- "create WO for coolant leak"
- "make a work order"

### Trigger Condition

| Type | Condition |
|------|-----------|
| QUERY_INTENT | Query contains "create work order" or "new WO" |
| CONTEXT | From Equipment or Fault focus, user requests WO creation |

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_equipment` | id, name, category | Equipment lookup |
| `pms_faults` | id, title, severity | Fault linking |
| `auth_users_profiles` | id, full_name | Assignment candidates |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_orders` | all required columns | Main entity |
| `pms_audit_log` | standard columns | Audit trail |

### Field Classification

| Field | Classification | Source | Notes |
|-------|----------------|--------|-------|
| `id` | BACKEND_AUTO | gen_random_uuid() | |
| `yacht_id` | BACKEND_AUTO | `public.get_user_yacht_id()` | Canonical |
| `wo_number` | BACKEND_AUTO | `generate_wo_number(yacht_id)` | |
| `title` | REQUIRED | User input | |
| `description` | OPTIONAL | User input | |
| `type` | REQUIRED | User selection | Enum |
| `priority` | REQUIRED | User selection | Default: medium |
| `status` | BACKEND_AUTO | 'draft' or 'open' | |
| `equipment_id` | OPTIONAL | Context or user | |
| `fault_id` | OPTIONAL | Context | |
| `assigned_to` | OPTIONAL | User selection | |
| `due_date` | OPTIONAL | User input | |
| `created_at` | BACKEND_AUTO | NOW() | |
| `created_by` | BACKEND_AUTO | auth.uid() | |

### Signature Requirement

```json
{
  "required": false,
  "value": "'{}'::jsonb"
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_orders` | "Users can manage their yacht work orders" | ALL | `yacht_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid())` |

**BLOCKER B1**: Policy uses legacy pattern. Should use `public.get_user_yacht_id()`.

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[new_work_order_id]",
  "action": "created",
  "actor": "[user_id]",
  "summary": "Created WO-2026-042: Generator maintenance"
}
```

---

## Action 2: Update Work Order

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `update_work_order` |
| **Blocker Status** | B1 (RLS legacy) |
| **Mutation Tier** | WRITE |
| **Signature Required** | NO |

### Intent Phrasing

- "update this work order"
- "change priority to high"
- "edit WO details"
- "update due date"

### Trigger Condition

| Type | Condition |
|------|-----------|
| FOCUS | Single WO focused + edit intent |
| QUERY_INTENT | "update WO-2026-042" |

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_work_orders` | current state | Optimistic locking |
| `pms_equipment` | id, name | If changing equipment |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_orders` | modified fields only | |
| `pms_audit_log` | old_values, new_values | Delta capture |

### Field Classification

| Field | Classification | Notes |
|-------|----------------|-------|
| `title` | OPTIONAL | User can change |
| `description` | OPTIONAL | User can change |
| `type` | OPTIONAL | User can change (if not started) |
| `priority` | OPTIONAL | User can change |
| `equipment_id` | OPTIONAL | User can change |
| `assigned_to` | OPTIONAL | Requires Reassign action if different |
| `due_date` | OPTIONAL | User can change |
| `due_hours` | OPTIONAL | User can change |
| `updated_at` | BACKEND_AUTO | NOW() |
| `updated_by` | BACKEND_AUTO | auth.uid() |

### Signature Requirement

```json
{
  "required": false,
  "value": "'{}'::jsonb"
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_orders` | "Users can manage their yacht work orders" | ALL | Legacy pattern |

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[work_order_id]",
  "action": "updated",
  "actor": "[user_id]",
  "summary": "Updated WO-2026-042: Changed priority to high"
}
```

---

## Action 3: Complete Work Order

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `complete_work_order` |
| **Blocker Status** | B1 (RLS legacy) |
| **Mutation Tier** | WRITE |
| **Signature Required** | NO (confirmation required) |

### Intent Phrasing

- "complete this work order"
- "mark WO-2026-042 as done"
- "finish this WO"
- "close out work order"

### Trigger Condition

| Type | Condition |
|------|-----------|
| FOCUS | Single WO focused + status is 'in_progress' |
| QUERY_INTENT | "complete WO-2026-042" |

### Pre-conditions

1. WO status must be 'in_progress' or 'open'
2. User must be assigned_to OR have engineer+ role
3. All required checklist items must be completed (if checklist exists)

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_work_orders` | status, assigned_to | Validation |
| `pms_work_order_checklist` | is_completed, is_required | Checklist validation |
| `pms_work_order_parts` | part_id, quantity | Parts to deduct |
| `pms_parts` | quantity_on_hand | Stock check |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_orders` | status, completed_at, completed_by, completion_notes | |
| `pms_faults` | status, resolved_at, resolved_by | Via trigger cascade |
| `pms_work_order_history` | completion record | History snapshot |
| `pms_parts` | quantity_on_hand | Deduct used parts |
| `pms_part_usage` | usage record | Audit inventory |
| `pms_audit_log` | standard | |

### Field Classification

| Field | Classification | Notes |
|-------|----------------|-------|
| `status` | BACKEND_AUTO | Set to 'completed' |
| `completed_at` | BACKEND_AUTO | NOW() |
| `completed_by` | BACKEND_AUTO | auth.uid() |
| `completion_notes` | OPTIONAL | User input |
| `updated_at` | BACKEND_AUTO | NOW() |
| `updated_by` | BACKEND_AUTO | auth.uid() |

### Signature Requirement

```json
{
  "required": false,
  "value": "'{}'::jsonb",
  "confirmation": {
    "required": true,
    "message": "Are you sure you want to complete this work order? Parts will be deducted from inventory."
  }
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_orders` | "Users can manage their yacht work orders" | UPDATE | Legacy pattern |
| `pms_faults` | N/A | UPDATE | Via trigger (service role) |

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[work_order_id]",
  "action": "completed",
  "actor": "[user_id]",
  "summary": "Completed WO-2026-042: Generator oil change"
}
```

### Cascade Effect

```
WO.status = 'completed'
  → TRIGGER: cascade_wo_status_to_fault()
    → pms_faults.status = 'resolved'
    → pms_faults.resolved_at = NOW()
    → pms_faults.resolved_by = [user_id]
```

---

## Action 4: Add Note

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `add_work_order_note` |
| **Blocker Status** | None |
| **Mutation Tier** | WRITE |
| **Signature Required** | NO |

### Intent Phrasing

- "add note to this work order"
- "note: waiting for parts"
- "update progress"
- "add comment"

### Trigger Condition

| Type | Condition |
|------|-----------|
| FOCUS | Single WO focused |
| QUERY_INTENT | "add note to WO-2026-042" |

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_work_orders` | id, status | Validation |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_order_notes` | all columns | New note |
| `pms_audit_log` | standard | |

### Field Classification

| Field | Classification | Notes |
|-------|----------------|-------|
| `id` | BACKEND_AUTO | gen_random_uuid() |
| `work_order_id` | CONTEXT | From focused WO |
| `note_text` | REQUIRED | User input |
| `note_type` | OPTIONAL | Default: 'general' |
| `created_at` | BACKEND_AUTO | NOW() |
| `created_by` | BACKEND_AUTO | auth.uid() |

### Signature Requirement

```json
{
  "required": false,
  "value": "'{}'::jsonb"
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_order_notes` | (needs verification) | INSERT | Via WO join |

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[work_order_id]",
  "action": "note_added",
  "actor": "[user_id]",
  "summary": "Added note to WO-2026-042: Waiting for gasket delivery"
}
```

---

## Action 5: Reassign Work Order

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `reassign_work_order` |
| **Blocker Status** | B1, B3 |
| **Mutation Tier** | WRITE |
| **Signature Required** | YES (HoD/Captain) |

### Intent Phrasing

- "reassign this to John"
- "assign WO to 2nd Engineer"
- "change assignment"
- "give this WO to..."

### Trigger Condition

| Type | Condition |
|------|-----------|
| FOCUS | Single WO focused + user is HoD/Captain |
| QUERY_INTENT | "reassign WO-2026-042 to [name]" |

### Pre-conditions

1. User must have HoD or Captain role
2. New assignee must be on same yacht
3. WO status must not be 'completed' or 'cancelled'

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_work_orders` | assigned_to, status | Current state |
| `auth_users_profiles` | id, full_name, role, yacht_id | Validate new assignee |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_orders` | assigned_to, updated_at, updated_by | |
| `pms_audit_log` | + signature | Signed action |

### Field Classification

| Field | Classification | Notes |
|-------|----------------|-------|
| `assigned_to` | REQUIRED | New user UUID |
| `updated_at` | BACKEND_AUTO | NOW() |
| `updated_by` | BACKEND_AUTO | auth.uid() |

### Signature Requirement

```json
{
  "required": true,
  "roles": ["captain", "chief_engineer", "chief_steward", "chief_officer", "purser"],
  "value": {
    "signer_id": "[user_id]",
    "signed_at": "[timestamp]",
    "device_id": "[device]",
    "action_hash": "[hash of action params]"
  }
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_orders` | "Users can manage their yacht work orders" | UPDATE | Legacy + need role check |

**BLOCKER B3**: Need `user_has_role()` function for role verification.

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[work_order_id]",
  "action": "reassigned",
  "actor": "[signer_id]",
  "summary": "Reassigned WO-2026-042 from John to Mike",
  "signature": true
}
```

---

## Action 6: Archive Work Order

### Metadata

| Field | Value |
|-------|-------|
| **Action Name** | `archive_work_order` |
| **Blocker Status** | B1, B3 |
| **Mutation Tier** | WRITE |
| **Signature Required** | YES (Captain/HoD) |

### Intent Phrasing

- "archive this work order"
- "cancel WO-2026-042"
- "delete this work order" (soft delete)

### Trigger Condition

| Type | Condition |
|------|-----------|
| FOCUS | Single WO focused + user is Captain/HoD |

### Pre-conditions

1. User must have Captain or HoD role
2. Must provide deletion_reason
3. WO must not have dependent active items (or cascade archive them)

### Tables Read

| Table | Columns | Purpose |
|-------|---------|---------|
| `pms_work_orders` | status, deleted_at | Current state |
| `pms_work_order_checklist` | is_completed | Check for incomplete items |

### Tables Written

| Table | Columns | Notes |
|-------|---------|-------|
| `pms_work_orders` | deleted_at, deleted_by, deletion_reason, status | Soft delete |
| `pms_faults` | status | Back to 'open' if linked |
| `pms_audit_log` | + signature | Signed action |

### Field Classification

| Field | Classification | Notes |
|-------|----------------|-------|
| `deleted_at` | BACKEND_AUTO | NOW() |
| `deleted_by` | BACKEND_AUTO | auth.uid() |
| `deletion_reason` | REQUIRED | User must provide |
| `status` | BACKEND_AUTO | Set to 'cancelled' |

### Signature Requirement

```json
{
  "required": true,
  "roles": ["captain", "chief_engineer", "chief_steward", "chief_officer", "purser"],
  "value": {
    "signer_id": "[user_id]",
    "signed_at": "[timestamp]",
    "device_id": "[device]",
    "action_hash": "[hash of action params]",
    "reason": "[deletion_reason]"
  }
}
```

### RLS Proof

| Table | Policy Name | Cmd | Condition |
|-------|-------------|-----|-----------|
| `pms_work_orders` | "hod_can_archive_work_orders" | UPDATE | PROPOSED - needs deployment |

**BLOCKER B3**: Need role-based RLS policy.

### Ledger UI Event

```json
{
  "entity_type": "work_order",
  "entity_id": "[work_order_id]",
  "action": "archived",
  "actor": "[signer_id]",
  "summary": "Archived WO-2026-042: Duplicate entry",
  "signature": true
}
```

### Cascade Effect

```
WO.status = 'cancelled' AND deleted_at = NOW()
  → TRIGGER: cascade_wo_status_to_fault()
    → pms_faults.status = 'open' (back to open)
    → pms_faults.resolved_at = NULL
    → pms_faults.resolved_by = NULL
```

---

## ACTION SUMMARY TABLE

| # | Action | Trigger | Tables Written | RLS Proof | Signature | Blocker |
|---|--------|---------|----------------|-----------|-----------|---------|
| 1 | Create WO | QUERY_INTENT / CONTEXT | pms_work_orders, pms_audit_log | Legacy | NO | B1 |
| 2 | Update WO | FOCUS + intent | pms_work_orders, pms_audit_log | Legacy | NO | B1 |
| 3 | Complete WO | FOCUS + intent | pms_work_orders, pms_faults, pms_work_order_history, pms_parts, pms_part_usage, pms_audit_log | Legacy | NO (confirm) | B1 |
| 4 | Add Note | FOCUS | pms_work_order_notes, pms_audit_log | TBD | NO | None |
| 5 | Reassign WO | FOCUS + HoD | pms_work_orders, pms_audit_log | Legacy + role | YES | B1, B3 |
| 6 | Archive WO | FOCUS + HoD | pms_work_orders, pms_faults, pms_audit_log | Legacy + role | YES | B1, B3 |

---

## PHASE 4 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 4.1 Actions listed (6) | ✅ |
| 4.2 Intent phrasing for each | ✅ |
| 4.3 Trigger conditions for each | ✅ |
| 4.4 Tables read for each | ✅ |
| 4.5 Tables written for each | ✅ |
| 4.6 Field classifications for each | ✅ |
| 4.7 Signature requirements for each | ✅ |
| 4.8 RLS proof for each | ✅ (with blockers noted) |
| 4.9 Ledger events for each | ✅ |
| BLOCKERS documented | ✅ (B1, B3) |

**Proceeding to Phase 5: UX Flow & Scenarios**
