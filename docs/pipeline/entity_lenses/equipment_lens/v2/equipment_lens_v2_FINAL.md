# Equipment Lens v2 - FINAL

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Version**: v2 FINAL
**Status**: READY FOR IMPLEMENTATION
**Date**: 2026-01-27
**Gold Standard Reference**: Certificate Lens v2

---

## EXECUTIVE SUMMARY

The Equipment Lens governs all operations for vessel equipment hierarchy, status tracking, maintenance linkages, and parts BOM relationships. Equipment is the **anchor entity** for operational work.

### Key Metrics

| Metric | Value |
|--------|-------|
| Primary Table | `pms_equipment` (24 columns) |
| Related Tables | `pms_equipment_parts_bom`, `pms_notes`, `pms_attachments` |
| Actions Registered | 7 mutations + 3 READ handlers |
| Scenarios Documented | 12 full user journeys |
| Ledger Events | 7 distinct audit entries |
| Notification Triggers | 5 |
| Role Tiers | 3 (Crew, Engineers, Authority) |

### Blockers

| ID | Description | Status |
|----|-------------|--------|
| B1 | pms_notes RLS | ⚠️ VERIFY |
| B2 | pms_attachments RLS | ⚠️ VERIFY |
| B3 | Storage write policies | ⚠️ VERIFY |
| B4 | pms_notifications table | NEW (migration ready) |

---

## PART 0: CANONICAL HELPERS

### Yacht ID Resolution

```sql
public.get_user_yacht_id() → UUID
-- Returns yacht_id for current authenticated user
-- SECURITY DEFINER, STABLE
```

### Role Helpers

```sql
public.get_user_role() → TEXT
-- Returns role string: 'engineer', 'captain', etc.

public.is_hod(user_id UUID, yacht_id UUID) → BOOLEAN
-- Returns true for: captain, chief_engineer, chief_officer, purser, manager

public.is_manager() → BOOLEAN
-- Returns true for: manager
```

### Audit Entity Type

```sql
entity_type = 'equipment'
```

### Signature Invariant

```sql
-- Non-signed action:
signature = '{}'::jsonb

-- Signed action (decommission):
signature = :signature_payload::jsonb  -- NEVER NULL
```

---

## PART 1: DATABASE SCHEMA

### Table: `pms_equipment` (24 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `parent_id` | uuid | YES | OPTIONAL |
| `name` | text | NOT NULL | REQUIRED |
| `code` | text | YES | OPTIONAL |
| `description` | text | YES | OPTIONAL |
| `location` | text | YES | OPTIONAL |
| `manufacturer` | text | YES | OPTIONAL |
| `model` | text | YES | OPTIONAL |
| `serial_number` | text | YES | OPTIONAL |
| `installed_date` | date | YES | OPTIONAL |
| `criticality` | equipment_criticality | YES | OPTIONAL |
| `system_type` | text | YES | OPTIONAL |
| `status` | text | YES | BACKEND_AUTO |
| `attention_flag` | boolean | YES | BACKEND_AUTO |
| `attention_reason` | text | YES | CONTEXT |
| `attention_updated_at` | timestamptz | YES | BACKEND_AUTO |
| `metadata` | jsonb | YES | BACKEND_AUTO |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `updated_by` | uuid | YES | BACKEND_AUTO |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO |
| `deleted_by` | uuid | YES | BACKEND_AUTO |
| `deletion_reason` | text | YES | OPTIONAL |

### Status Values (CHECK Constraint)

```sql
'operational', 'degraded', 'failed', 'maintenance', 'decommissioned'
```

### Criticality Enum

```sql
'low', 'medium', 'high', 'critical'
```

---

## PART 2: MICRO-ACTIONS

### Action Summary

| # | Action | Variant | Signed | Allowed Roles |
|---|--------|---------|--------|---------------|
| 1 | `update_equipment_status` | MUTATE | NO | engineer+ |
| 2 | `add_equipment_note` | MUTATE | NO | all crew |
| 3 | `attach_file_to_equipment` | MUTATE | NO | all crew |
| 4 | `create_work_order_for_equipment` | MUTATE | NO | engineer+ |
| 5 | `link_part_to_equipment` | MUTATE | NO | engineer+ |
| 6 | `flag_equipment_attention` | MUTATE | NO | engineer+ |
| 7 | `decommission_equipment` | SIGNED | **YES** | captain, manager |

### Role Permission Matrix

| Role | View | Note | Attach | Status | WO | Parts | Decomm |
|------|------|------|--------|--------|----|----|--------|
| `deckhand` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `steward` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `engineer` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `eto` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `chief_engineer` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `chief_officer` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `captain` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔐 |
| `manager` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔐 |

---

## PART 2B: ACTION ROUTER REGISTRATION

### Registry Entries

```python
"update_equipment_status": ActionDefinition(
    action_id="update_equipment_status",
    label="Update Status",
    endpoint="/v1/equipment/update-status",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["equipment_id", "status"],
    optional_fields=["attention_reason", "clear_attention"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["status", "update", "mark", "failed", "operational"],
),

"add_equipment_note": ActionDefinition(
    action_id="add_equipment_note",
    label="Add Note",
    endpoint="/v1/equipment/add-note",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
                   "chief_officer", "chief_steward", "purser", "captain", "manager"],
    required_fields=["equipment_id", "text"],
    optional_fields=["note_type", "requires_ack"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["note", "log", "record", "observation"],
),

"attach_file_to_equipment": ActionDefinition(
    action_id="attach_file_to_equipment",
    label="Attach Photo/Document",
    endpoint="/v1/equipment/attach-file",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "steward", "chef", "engineer", "eto", "chief_engineer",
                   "chief_officer", "chief_steward", "purser", "captain", "manager"],
    required_fields=["equipment_id", "file"],
    optional_fields=["description", "tags"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["photo", "picture", "upload", "attach"],
),

"create_work_order_for_equipment": ActionDefinition(
    action_id="create_work_order_for_equipment",
    label="Create Work Order",
    endpoint="/v1/equipment/create-work-order",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["equipment_id", "title", "type", "priority"],
    optional_fields=["description", "assigned_to", "due_date", "fault_severity"],
    domain="equipment",
    variant=ActionVariant.MUTATE,
    search_keywords=["work order", "job", "task", "maintenance"],
),

"decommission_equipment": ActionDefinition(
    action_id="decommission_equipment",
    label="Decommission Equipment",
    endpoint="/v1/equipment/decommission",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["captain", "manager"],
    required_fields=["equipment_id", "reason", "signature"],
    optional_fields=["replacement_equipment_id"],
    domain="equipment",
    variant=ActionVariant.SIGNED,
    search_keywords=["decommission", "remove", "retire"],
),
```

### Storage Configuration

```python
ACTION_STORAGE_CONFIG["attach_file_to_equipment"] = {
    "bucket": "documents",
    "path_template": "{yacht_id}/equipment/{equipment_id}/{filename}",
    "writable_prefixes": ["{yacht_id}/equipment/"],
    "confirmation_required": True,
    "max_file_size_mb": 25,
}
```

### Request Contract Example

```json
{
  "action": "update_equipment_status",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid"
  },
  "payload": {
    "status": "failed",
    "attention_reason": "Alternator bearing failure"
  }
}
```

---

## PART 3: STATUS LIFECYCLE

```
operational (default)
    ↓ (issue detected)
degraded
    ↓ (complete failure)
failed
    ↓ (service started)
maintenance
    ↓ (repair complete)
operational

ANY → decommissioned (TERMINAL, signed, manager/captain only)
```

**Terminal State Rule**: Once `decommissioned`, status cannot be changed. Equipment remains in database (soft delete).

---

## PART 4: RLS POLICIES

### pms_equipment

```sql
-- SELECT: All authenticated users
USING (yacht_id = public.get_user_yacht_id());

-- ALL: Engineers can manage
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() = ANY (ARRAY['engineer', 'eto', 'chief_engineer',
                                            'chief_officer', 'captain', 'manager'])
);

-- Service role bypass
TO service_role USING (true);
```

### RLS Status: ✅ Deployed

---

## PART 5: SCENARIOS SUMMARY

| # | Scenario | Role | Primary Action | Expected |
|---|----------|------|----------------|----------|
| 1 | Generator breakdown | engineer | update_status + create_wo | 200 |
| 2 | Deckhand observation | deckhand | add_note | 200 |
| 3 | Morning attention review | chief_engineer | flag_attention | 200 |
| 4 | Permission denied | steward | (blocked) | 403 |
| 5 | Safety equipment check | chief_officer | add_note | 200 |
| 6 | Handover note | engineer | add_note | 200 |
| 7 | Decommission (signed) | manager | decommission | 200 |
| 8 | Cross-yacht access | any | (blocked) | 404 |
| 9 | Terminal state violation | manager | (blocked) | 400 |
| 10 | Hierarchy navigation | eto | create_wo | 200 |
| 11 | Parts lookup + escape | chief_engineer | (escape) | 200 |
| 12 | Emergency breakdown | engineer | status + photo | 200 |

---

## PART 6: LEDGER INTEGRATION

### Audit Events

| Event | Action | Signature |
|-------|--------|-----------|
| equipment_status_changed | update_equipment_status | {} |
| equipment_note_added | add_equipment_note | {} |
| equipment_file_attached | attach_file_to_equipment | {} |
| equipment_work_order_created | create_work_order_for_equipment | {} |
| equipment_part_linked | link_part_to_equipment | {} |
| equipment_attention_flagged | flag_equipment_attention | {} |
| **equipment_decommissioned** | decommission_equipment | **{signature JSON}** |

### Audit Query

```sql
SELECT created_at, action, actor_role, old_values, new_values, signature
FROM pms_audit_log
WHERE entity_type = 'equipment' AND entity_id = :equipment_id
ORDER BY created_at DESC;
```

---

## PART 7: NOTIFICATION TRIGGERS

| Trigger | Recipients | Level | CTA |
|---------|------------|-------|-----|
| Status → failed (critical) | captain, chief_engineer | critical | Focus equipment |
| Status → failed (non-critical) | chief_engineer | warning | Focus equipment |
| Note with requires_ack | chief_engineer | info | View note |
| Attention flag set | chief_engineer | warning | Focus equipment |
| Decommissioned | captain, manager | info | View audit |

---

## PART 8: ESCAPE HATCHES

| From Equipment | To Lens | Trigger |
|----------------|---------|---------|
| view_equipment_faults | Fault Lens | Click fault |
| view_equipment_work_orders | Work Order Lens | Click WO |
| create_work_order_for_equipment | Work Order Lens | Create WO |
| view_equipment_parts | Part Lens | Click part |
| Attachment click | Document Lens | Click file |

---

## PART 9: ERROR HANDLING

| Condition | HTTP | Message |
|-----------|------|---------|
| Equipment not found | 404 | "Equipment not found" |
| Invalid status value | 400 | "Invalid status: must be one of..." |
| Terminal state transition | 400 | "Cannot change status from 'decommissioned'" |
| Signature required | 400 | "This action requires a signature" |
| Already decommissioned | 409 | "Equipment is already decommissioned" |
| File too large | 400 | "File exceeds maximum size of 25MB" |
| Cross-yacht access | 404 | "Equipment not found" |

**Rule**: 500 is ALWAYS a bug. All expected conditions return 4xx.

---

## PART 10: DEPLOYMENT CHECKLIST

### Pre-Deploy Verification

```sql
-- RLS enabled
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN ('pms_equipment', 'pms_notes', 'pms_attachments');

-- Policies exist
SELECT tablename, COUNT(*) FROM pg_policies
WHERE tablename IN ('pms_equipment', 'pms_notes', 'pms_attachments')
GROUP BY tablename;

-- Helpers exist
SELECT proname FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'get_user_role', 'is_hod', 'is_manager');
```

### Migrations (if needed)

1. `20260127_001_notes_rls.sql` - Notes RLS policies
2. `20260127_002_attachments_rls.sql` - Attachments RLS policies
3. `20260127_003_storage_write_policies.sql` - Storage bucket policies
4. `20260127_004_create_notifications.sql` - Notifications table
5. `20260127_005_notification_helpers.sql` - Helper functions

### Post-Deploy Tests

```bash
# HOD can update status
curl -X POST "$BASE_URL/v1/equipment/update-status" \
  -H "Authorization: Bearer $HOD_JWT" \
  -d '{"equipment_id":"uuid","status":"maintenance"}'
# Expected: 200

# Crew cannot update status
curl -X POST "$BASE_URL/v1/equipment/update-status" \
  -H "Authorization: Bearer $CREW_JWT" \
  -d '{"equipment_id":"uuid","status":"operational"}'
# Expected: 403

# Crew can add note
curl -X POST "$BASE_URL/v1/equipment/add-note" \
  -H "Authorization: Bearer $CREW_JWT" \
  -d '{"equipment_id":"uuid","text":"Observation"}'
# Expected: 200
```

---

## PHASE FILES REFERENCE

| Phase | File | Purpose |
|-------|------|---------|
| 0 | PHASE_0_EXTRACTION_GATE.md | Entity independence validation |
| 1 | PHASE_1_SCOPE.md | Actions, roles, scenarios outline |
| 2 | PHASE_2_DB_TRUTH.md | Exact production schema |
| 3 | PHASE_3_ENTITY_GRAPH.md | Relationships, escape hatches |
| 4 | PHASE_4_ACTIONS.md | Full action specifications |
| 5 | PHASE_5_SCENARIOS.md | 12 user journey scenarios |
| 6 | PHASE_6_SQL_BACKEND.md | Handler SQL patterns |
| 7 | PHASE_7_RLS_MATRIX.md | RLS policies and verification |
| 8 | PHASE_8_GAPS_MIGRATIONS.md | Blockers and migration scripts |

---

## IMPLEMENTATION ORDER

1. **Verify blockers** - Run verification queries
2. **Deploy migrations** - As needed based on verification
3. **Backend handlers** - `apps/api/handlers/equipment_handlers.py`
4. **Registry entries** - `apps/api/action_router/registry.py`
5. **Dispatcher routing** - `apps/api/action_router/dispatchers/internal_dispatcher.py`
6. **Docker tests** - `tests/docker/run_equipment_rls_tests.py`
7. **Staging CI tests** - `tests/ci/staging_equipment_acceptance.py`
8. **Frontend integration** - Search, actions, modal

---

**END OF EQUIPMENT LENS v2 FINAL**

**Tag**: `equipment-lens-v2-ready`
