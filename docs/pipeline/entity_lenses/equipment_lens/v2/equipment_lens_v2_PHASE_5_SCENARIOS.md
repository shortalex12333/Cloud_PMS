# Equipment Lens v2 - PHASE 5: SCENARIOS

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 5 defines complete user journey scenarios with:
- Realistic personas (who, where, what device, mental state)
- Natural language articulation (how users actually speak)
- Step-by-step flows (query → focus → act)
- Success and error paths
- Notification triggers
- Ledger entries

---

## SCENARIO FORMAT

Each scenario follows this structure:

```
## Scenario N: Title

**Persona**: Role
**Location**: Where on yacht
**Device**: Phone/Tablet/Laptop
**Mental State**: Stress level, context
**Natural Articulation**: What they actually say/type

### Journey
1. Query
2. Focus
3. Action
4. System Response
5. Ledger Entry
6. Notification (if triggered)

### Error Paths
| Condition | Expected HTTP | Message |
```

---

## SCENARIO 1: Engineer Discovers Failed Generator (BREAKDOWN)

**Persona**: Engineer (2nd Engineer)
**Location**: Engine room, standing at Generator #2, alarm sounding
**Device**: Tablet (oil on fingers)
**Mental State**: High stress - alarm just went off, needs to document fast

**Natural Articulation**: "Gen 2 is down" / "Mark gen 2 failed"

### Journey

**Step 1: Query**
```
User types: "gen 2"
System: Searches pms_equipment WHERE (name ILIKE '%gen%' OR code ILIKE '%gen%2%')
Results: [
  { id: "gen2-uuid", name: "Generator #2", code: "GEN-02", status: "operational" }
]
```

**Step 2: Focus**
```
User: Taps "Generator #2"
System: Shows equipment detail card with current status, no active faults
Available Actions (for engineer role):
  - update_equipment_status
  - add_equipment_note
  - attach_file_to_equipment
  - create_work_order_for_equipment
```

**Step 3: Quick Photo Capture**
```
User: Taps camera icon (attach_file_to_equipment)
Action: Takes photo of oil leak at alternator
Payload: {
  equipment_id: "gen2-uuid",
  file: <photo binary>,
  description: "Oil leak at alternator bearing"
}
Response: 200 OK
{
  "success": true,
  "data": {
    "attachment_id": "attach-uuid",
    "storage_path": "yacht-uuid/equipment/gen2-uuid/abc123.jpg"
  }
}
```

**Step 4: Update Status**
```
User: Taps "Update Status"
Selects: status = "failed"
Enters: attention_reason = "Alternator bearing failure - oil leak"
Payload: {
  equipment_id: "gen2-uuid",
  status: "failed",
  attention_reason: "Alternator bearing failure - oil leak"
}
Response: 200 OK
{
  "success": true,
  "data": {
    "equipment_id": "gen2-uuid",
    "old_status": "operational",
    "new_status": "failed",
    "attention_flag": true
  }
}
```

**Step 5: Create Work Order**
```
User: Taps "Create Work Order"
Pre-filled: equipment_id, equipment_name
Enters:
  title: "Generator #2 alternator bearing replacement"
  type: "corrective" (dropdown)
  priority: "critical" (dropdown)
  fault_severity: "critical" (appears because type=corrective)
Payload: {
  equipment_id: "gen2-uuid",
  title: "Generator #2 alternator bearing replacement",
  type: "corrective",
  priority: "critical",
  fault_severity: "critical"
}
Response: 200 OK
{
  "success": true,
  "data": {
    "work_order_id": "wo-uuid",
    "wo_number": "WO-2026-0143",
    "fault_id": "fault-uuid",
    "fault_code": "FLT-2026-0089"
  }
}
```

### Ledger Entries (3 total)

```sql
-- 1. File attachment
INSERT INTO pms_audit_log (entity_type, entity_id, action, signature)
VALUES ('equipment', 'gen2-uuid', 'attach_file_to_equipment', '{}');

-- 2. Status change
INSERT INTO pms_audit_log (entity_type, entity_id, action, old_values, new_values, signature)
VALUES ('equipment', 'gen2-uuid', 'update_equipment_status',
        '{"status": "operational", "attention_flag": false}',
        '{"status": "failed", "attention_flag": true, "attention_reason": "Alternator bearing failure"}',
        '{}');

-- 3. Work order creation
INSERT INTO pms_audit_log (entity_type, entity_id, action, new_values, signature)
VALUES ('equipment', 'gen2-uuid', 'create_work_order_for_equipment',
        '{"work_order_id": "wo-uuid", "wo_number": "WO-2026-0143", "fault_id": "fault-uuid"}',
        '{}');
```

### Notifications Triggered

```sql
-- Critical equipment failure → chief_engineer + captain
INSERT INTO pms_notifications (user_id, topic, source, source_id, title, body, level, cta_action_id, cta_payload)
VALUES
  -- To Chief Engineer
  ((SELECT id FROM auth_users_profiles WHERE role = 'chief_engineer' LIMIT 1),
   'equipment_critical_failure', 'equipment', 'gen2-uuid',
   'CRITICAL: Generator #2 Failed',
   'Generator #2 marked as FAILED by Engineer. Reason: Alternator bearing failure - oil leak',
   'critical',
   'focus_equipment',
   '{"equipment_id": "gen2-uuid"}'),
  -- To Captain
  ((SELECT id FROM auth_users_profiles WHERE role = 'captain' LIMIT 1),
   'equipment_critical_failure', 'equipment', 'gen2-uuid',
   'CRITICAL: Generator #2 Failed',
   'Generator #2 marked as FAILED by Engineer. Reason: Alternator bearing failure - oil leak',
   'critical',
   'focus_equipment',
   '{"equipment_id": "gen2-uuid"}');
```

### Error Paths

| Condition | Expected HTTP | Message |
|-----------|---------------|---------|
| Deckhand attempts status update | 403 | (RLS blocks silently) |
| Invalid status value "broken" | 400 | "Invalid status: must be one of operational, degraded, failed, maintenance" |
| File too large (>25MB) | 400 | "File exceeds maximum size of 25MB" |
| Equipment not found | 404 | "Equipment not found" |

---

## SCENARIO 2: Deckhand Reports Windlass Issue (OBSERVATION)

**Persona**: Deckhand
**Location**: Bow, anchor station, morning departure
**Device**: Phone (wet from spray)
**Mental State**: Curious/concerned - noticed unusual noise, wants to log it

**Natural Articulation**: "Windlass sounds weird" / "Something wrong with the anchor winch"

### Journey

**Step 1: Query**
```
User types: "windlass"
Results: [{ id: "wl-uuid", name: "Anchor Windlass", code: "DK-WL-01", status: "operational" }]
```

**Step 2: Focus**
```
User: Taps "Anchor Windlass"
Available Actions (for deckhand role):
  - add_equipment_note ✓
  - attach_file_to_equipment ✓
  - update_equipment_status ✗ (not shown - role blocked)
  - create_work_order_for_equipment ✗ (not shown)
```

**Step 3: Add Note**
```
User: Taps "Add Note"
Enters:
  text: "Unusual grinding noise when hauling anchor. Noticed during morning departure."
  note_type: "observation"
  requires_ack: true (checkbox - wants engineer to see)
Payload: {
  equipment_id: "wl-uuid",
  text: "Unusual grinding noise when hauling anchor. Noticed during morning departure.",
  note_type: "observation",
  requires_ack: true
}
Response: 200 OK
```

**Step 4: Attach Video**
```
User: Records 15-second video of sound
Payload: {
  equipment_id: "wl-uuid",
  file: <video binary>,
  description: "Sound of windlass during anchor haul"
}
Response: 200 OK
```

### Ledger Entries

```sql
-- Note added
INSERT INTO pms_audit_log (entity_type, entity_id, action, actor_role, new_values, signature)
VALUES ('equipment', 'wl-uuid', 'add_equipment_note', 'deckhand',
        '{"note_id": "note-uuid", "note_type": "observation", "requires_ack": true}',
        '{}');

-- File attached
INSERT INTO pms_audit_log (entity_type, entity_id, action, actor_role, signature)
VALUES ('equipment', 'wl-uuid', 'attach_file_to_equipment', 'deckhand', '{}');
```

### Notification Triggered

```sql
-- requires_ack=true triggers notification to chief_engineer
INSERT INTO pms_notifications (user_id, topic, source, source_id, title, body, level, cta_action_id)
VALUES
  ((SELECT id FROM auth_users_profiles WHERE role = 'chief_engineer' LIMIT 1),
   'equipment_note_requires_ack', 'equipment', 'wl-uuid',
   'Equipment Note Requires Acknowledgment',
   'Deckhand added note to Anchor Windlass: "Unusual grinding noise when hauling anchor..."',
   'info',
   'view_equipment_note');
```

### Key Insight

Deckhand CANNOT change status but CAN flag issues via notes. The `requires_ack` flag routes the observation to the appropriate authority (chief_engineer) via notification system.

---

## SCENARIO 3: Chief Engineer Reviews Attention Items (MORNING BRIEFING)

**Persona**: Chief Engineer
**Location**: Engine control room, morning briefing prep
**Device**: Laptop
**Mental State**: Methodical - reviewing overnight events

**Natural Articulation**: "Show me what needs attention" / "Flagged equipment"

### Journey

**Step 1: Query**
```
User types: "equipment needs attention" or "attention" or "flagged"
System: Recognizes attention filter intent
Query: SELECT * FROM pms_equipment WHERE attention_flag = true AND yacht_id = get_user_yacht_id()
```

**Step 2: Results**
```
Results: [
  { id: "gen2-uuid", name: "Generator #2", status: "failed", attention_reason: "Alternator bearing failure" },
  { id: "wm1-uuid", name: "Watermaker #1", status: "degraded", attention_reason: "Membrane pressure low" },
  { id: "ac3-uuid", name: "AC Unit #3", status: "maintenance", attention_reason: "Scheduled service overdue" }
]
```

**Step 3: Review Each Item**
```
For Generator #2:
  - View full history (audit log)
  - Review associated notes (including deckhand's windlass note in notification)
  - Check linked work order WO-2026-0143
  - Verify parts on order
```

**Step 4: Clear Attention (if acknowledged)**
```
User: For AC Unit #3 (service complete), clears attention
Action: flag_equipment_attention
Payload: {
  equipment_id: "ac3-uuid",
  attention_flag: false
}
Response: 200 OK
```

### Ledger Entry

```sql
INSERT INTO pms_audit_log (entity_type, entity_id, action, actor_role, old_values, new_values, signature)
VALUES ('equipment', 'ac3-uuid', 'flag_equipment_attention', 'chief_engineer',
        '{"attention_flag": true, "attention_reason": "Scheduled service overdue"}',
        '{"attention_flag": false}',
        '{}');
```

---

## SCENARIO 4: Crew Attempts Status Change (PERMISSION DENIED)

**Persona**: Steward
**Location**: Galley
**Device**: Phone
**Mental State**: Helpful - wants to mark espresso machine as fixed

**Natural Articulation**: "Espresso machine is working now"

### Journey

**Step 1: Query & Focus**
```
User types: "espresso"
Focuses on: Espresso Machine (status: "degraded")
```

**Step 2: Attempt Status Update**
```
Available Actions (for steward):
  - add_equipment_note ✓
  - attach_file_to_equipment ✓
  - update_equipment_status ✗ (NOT SHOWN in action list)

User: Looks for status update option
System: Action not available for this role
```

**Step 3: Alternative Path**
```
User: Adds note instead
Action: add_equipment_note
Payload: {
  equipment_id: "espresso-uuid",
  text: "Espresso machine seems to be working normally now. Tested with 3 shots.",
  note_type: "observation",
  requires_ack: true
}
Response: 200 OK
```

### What Happens

- Steward cannot directly change status (RLS blocks)
- Note with `requires_ack` notifies chief_steward/chief_engineer
- Authorized personnel can then update status

### If Steward Tries API Directly

```bash
# Steward attempts direct API call (bypassing UI)
curl -X POST "$BASE_URL/v1/equipment/update-status" \
  -H "Authorization: Bearer $STEWARD_JWT" \
  -d '{"equipment_id":"espresso-uuid","status":"operational"}'

# Response: 403 Forbidden
# (RLS blocks: role not in allowed list)
```

---

## SCENARIO 5: Pre-Departure Safety Equipment Check

**Persona**: Chief Officer
**Location**: Bridge, preparing departure checklist
**Device**: Tablet
**Mental State**: Systematic, checklist-driven

**Natural Articulation**: "Lifesaving equipment" / "Safety equipment status"

### Journey

**Step 1: Query**
```
User types: "lifesaving equipment"
System: Filters by system_type = 'lifesaving'
Results: [
  { name: "Liferaft #1", status: "operational", last_inspection: "2026-01-15" },
  { name: "Liferaft #2", status: "operational" },
  { name: "EPIRB", status: "operational", expiry: "2027-03-01" },
  { name: "Life Jackets Cabinet", status: "operational" }
]
```

**Step 2: Spot Check Update**
```
User: Focuses on EPIRB
Action: add_equipment_note
Payload: {
  equipment_id: "epirb-uuid",
  text: "Pre-departure check complete. Battery indicator green. Test button responsive.",
  note_type: "inspection"
}
Response: 200 OK
```

### Ledger Entry

```sql
INSERT INTO pms_audit_log (entity_type, entity_id, action, actor_role, new_values, signature)
VALUES ('equipment', 'epirb-uuid', 'add_equipment_note', 'chief_officer',
        '{"note_type": "inspection"}', '{}');
```

---

## SCENARIO 6: Engineer Handover - End of Watch

**Persona**: Engineer going off watch
**Location**: Engine room → cabin
**Device**: Tablet
**Mental State**: Tired, wants to communicate status to relief

**Natural Articulation**: "What's the status for handover?" / "Show pending items"

### Journey

**Step 1: Query**
```
User types: "handover" or "status summary"
System: Recognizes handover intent
```

**Step 2: Handover Summary View**
```
System aggregates:
- Equipment with attention_flag = true (3 items)
- Open work orders assigned to engineering (5 items)
- Unacknowledged notes requiring action (2 items)
- Recent status changes (last 12 hours) (4 items)
```

**Step 3: Add Handover Note**
```
User: Focuses on Generator #2
Action: add_equipment_note
Payload: {
  equipment_id: "gen2-uuid",
  text: "Waiting on parts from MAN dealer. Expected Wednesday. Do not attempt start. Running on Gen #1 only - monitor load carefully.",
  note_type: "handover"
}
Response: 200 OK
```

### Notification Triggered

```sql
-- Handover note triggers notification to next watch
INSERT INTO pms_notifications (user_id, topic, source, source_id, title, body, level)
VALUES
  -- To all engineers
  ((SELECT id FROM auth_users_profiles WHERE role = 'engineer' AND id != current_user_id() LIMIT 1),
   'equipment_handover_note', 'equipment', 'gen2-uuid',
   'Handover Note: Generator #2',
   'Engineer added handover note: "Waiting on parts from MAN dealer..."',
   'info');
```

### Context-Aware Action Filtering

**Important**: If user is actively working on a fault (fault focused), suggesting "handover" is LOW FIDELITY because they're in fix mode, not transition mode.

System should:
- Detect active fault context
- Prioritize fault-related actions
- Only suggest handover if:
  - User explicitly queries "handover"
  - Time-based trigger (end of watch window)
  - No active fault/WO in progress

---

## SCENARIO 7: Manager Decommissions Equipment (SIGNED ACTION)

**Persona**: Manager (shore-based)
**Location**: Office
**Device**: Desktop
**Mental State**: Administrative, documentation-focused

**Natural Articulation**: "Decommission the old watermaker" / "Remove WM-01 from service"

### Journey

**Step 1: Query & Focus**
```
User types: "watermaker 1"
Focuses on: Watermaker #1 (status: "failed" for 60 days)
```

**Step 2: Verify Pre-conditions**
```
Equipment shows:
- Status: "failed"
- Attention: "Beyond economic repair per survey"
- Active WOs: None (all closed)
- Last activity: 45 days ago
```

**Step 3: Initiate Decommission (GATED)**
```
User: Clicks "Decommission Equipment"
System: Shows GATED confirmation modal:
  ┌─────────────────────────────────────────────────────────────┐
  │  ⚠️  DECOMMISSION EQUIPMENT                                 │
  │                                                             │
  │  You are about to decommission:                             │
  │  Watermaker #1 (WM-01)                                      │
  │                                                             │
  │  ⚠️  This action is PERMANENT and cannot be reversed.       │
  │                                                             │
  │  Reason: [________________________________]                 │
  │                                                             │
  │  Replacement Equipment (optional):                          │
  │  [Watermaker #3 ▼]                                          │
  │                                                             │
  │  ☑️  I confirm this equipment should be permanently         │
  │      removed from active service.                           │
  │                                                             │
  │  [Cancel]                    [Sign & Decommission]          │
  └─────────────────────────────────────────────────────────────┘
```

**Step 4: Provide Signature**
```
Payload: {
  equipment_id: "wm1-uuid",
  reason: "Replaced by Watermaker #3 per refit specification. Unit scrapped.",
  replacement_equipment_id: "wm3-uuid",
  signature: {
    user_id: "manager-uuid",
    role_at_signing: "manager",
    signature_type: "decommission_equipment",
    equipment_id: "wm1-uuid",
    reason: "Replaced by Watermaker #3 per refit specification. Unit scrapped.",
    replacement_equipment_id: "wm3-uuid",
    signed_at: "2026-01-27T14:00:00Z",
    signature_hash: "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
  }
}
Response: 200 OK
```

### Ledger Entry (SIGNED)

```sql
INSERT INTO pms_audit_log (
  entity_type, entity_id, action, actor_role,
  old_values, new_values, signature
) VALUES (
  'equipment', 'wm1-uuid', 'decommission_equipment', 'manager',
  '{"status": "failed"}',
  '{"status": "decommissioned", "replacement_equipment_id": "wm3-uuid"}',
  '{
    "user_id": "manager-uuid",
    "role_at_signing": "manager",
    "signature_type": "decommission_equipment",
    "equipment_id": "wm1-uuid",
    "reason": "Replaced by Watermaker #3 per refit specification. Unit scrapped.",
    "replacement_equipment_id": "wm3-uuid",
    "signed_at": "2026-01-27T14:00:00Z",
    "signature_hash": "sha256:7f83b..."
  }'::jsonb  -- NOT empty {} - this is a SIGNED action
);
```

### Post-Decommission State

- Equipment status = 'decommissioned' (TERMINAL)
- Equipment `deleted_at` = NOW()
- Equipment remains in database (soft-delete doctrine)
- Future queries: `WHERE status != 'decommissioned'` excludes it
- Historical queries include it for audit trail

### Error Paths

| Condition | Expected HTTP | Message |
|-----------|---------------|---------|
| Chief Engineer attempts decommission | 403 | (RLS blocks - not in allowed_roles) |
| Missing signature payload | 400 | "This action requires a signature" |
| Invalid signature format | 400 | "Signature payload is invalid" |
| Already decommissioned | 409 | "Equipment is already decommissioned" |
| Captain with valid signature | 200 | (Allowed) |

---

## SCENARIO 8: Cross-Yacht Access Attempt (SECURITY)

**Persona**: Engineer from Yacht A
**Location**: Logged into system
**Mental State**: Accidentally or intentionally accessing wrong yacht's data

### Journey

**Step 1: Attempt Direct API Call**
```bash
# Engineer (Yacht A) tries to access Yacht B equipment
curl -X GET "$BASE_URL/v1/equipment/yacht-b-equipment-uuid" \
  -H "Authorization: Bearer $YACHT_A_ENGINEER_JWT"
```

**Step 2: RLS Enforcement**
```sql
SELECT * FROM pms_equipment
WHERE id = 'yacht-b-equipment-uuid'
  AND yacht_id = public.get_user_yacht_id()  -- Returns Yacht A ID
-- Result: 0 rows (equipment belongs to Yacht B)
```

**Step 3: Response**
```
Response: 404 Not Found
{
  "error": "equipment_not_found",
  "message": "Equipment not found"
}
```

### Key Security Principles

1. **Return 404, not 403**: Don't reveal that the equipment EXISTS in another yacht
2. **RLS is the authority**: All queries filtered by `get_user_yacht_id()`
3. **No audit entry**: No data was accessed, no audit row created
4. **Rate limiting**: Anomaly detection should log repeated 404s

---

## SCENARIO 9: Invalid Status Transition (TERMINAL STATE)

**Persona**: Manager
**Attempted Action**: Restore decommissioned equipment to operational

### Journey

**Step 1: Focus on Decommissioned Equipment**
```
User: Focuses on Watermaker #1 (status: "decommissioned")
System shows: Status badge with "DECOMMISSIONED" and no edit option
```

**Step 2: Attempt Status Update (if forced via API)**
```bash
curl -X POST "$BASE_URL/v1/equipment/update-status" \
  -H "Authorization: Bearer $MANAGER_JWT" \
  -d '{"equipment_id":"wm1-uuid","status":"operational"}'
```

**Step 3: Backend Validation**
```python
# Handler checks
if current_status == 'decommissioned':
    raise HTTPException(
        status_code=400,
        detail={
            "error": "invalid_state_transition",
            "message": "Cannot change status from 'decommissioned'. This is a terminal state.",
            "current_status": "decommissioned"
        }
    )
```

**Step 4: Response**
```
Response: 400 Bad Request
{
  "error": "invalid_state_transition",
  "message": "Cannot change status from 'decommissioned'. This is a terminal state.",
  "current_status": "decommissioned"
}
```

### No Ledger Entry

Action was rejected, no audit row created.

---

## SCENARIO 10: Equipment Hierarchy Navigation

**Persona**: ETO
**Context**: Troubleshooting electrical issue on Main Engine #1

**Natural Articulation**: "Show me fuel system on engine 1" / "ME1 fuel"

### Journey

**Step 1: Query**
```
User types: "ME1 fuel"
System: Searches with hierarchy awareness
```

**Step 2: Hierarchy Results**
```
Results show tree structure:
├── Main Engine #1 (ME-01)
│   └── Fuel Injection System (ME-01-FUEL)
│       ├── Fuel Pump (ME-01-FUEL-PUMP)
│       └── Injector Rail (ME-01-FUEL-INJ)
```

**Step 3: Focus on Child**
```
User: Clicks "Fuel Pump"
System shows:
- Parent breadcrumb: Main Engine #1 > Fuel Injection System > Fuel Pump
- Equipment details for Fuel Pump
- Actions apply to Fuel Pump (not parent)
```

**Step 4: Action on Child**
```
User: Creates work order for Fuel Pump
Action: create_work_order_for_equipment
Payload: {
  equipment_id: "fuel-pump-uuid",  // Child equipment
  title: "Fuel pump pressure test",
  type: "preventive",
  priority: "routine"
}
```

### Hierarchy Behavior Rules

| Action | Behavior |
|--------|----------|
| Note on parent | Note attached to parent only |
| Status on parent | Status changes parent only (NOT children) |
| Decommission parent | Children become orphaned (parent_id points to decommissioned equipment) |
| WO on child | WO linked to child, not parent |

---

## SCENARIO 11: Parts Lookup and Shopping List Escape

**Persona**: Chief Engineer
**Context**: Planning watermaker service, needs to order parts

**Natural Articulation**: "What parts do I need for watermaker service?"

### Journey

**Step 1: Focus on Equipment**
```
User types: "watermaker 2"
Focuses on: Watermaker #2
```

**Step 2: View Parts Panel**
```
Action: view_equipment_parts (READ)
System queries pms_equipment_parts_bom + pms_parts + pms_inventory_items
```

**Step 3: Parts BOM Display**
```
┌─────────────────────────────────────────────────────────────────┐
│  PARTS REQUIRED FOR: Watermaker #2                              │
├─────────────────────────────────────────────────────────────────┤
│  Part Number   │ Name          │ Qty Req │ Stock │ Status      │
├────────────────┼───────────────┼─────────┼───────┼─────────────┤
│  WM-MEM-001    │ Membrane      │ 2       │ 1     │ ⚠️ LOW      │
│  WM-ORK-001    │ O-Ring Kit    │ 1       │ 5     │ ✓ OK        │
│  WM-PSL-001    │ Pump Seal     │ 1       │ 0     │ ❌ OUT       │
└─────────────────────────────────────────────────────────────────┘
                                        [Add to Shopping List]
```

**Step 4: Escape to Shopping List Lens**
```
User: Clicks "Add to Shopping List" for Pump Seal
Escape hatch: → Shopping List Lens
Pre-filled context: {
  part_id: "pump-seal-uuid",
  quantity: 1,
  reason: "Watermaker #2 service - pump seal replacement",
  equipment_id: "wm2-uuid"
}
```

**Step 5: Return to Equipment Lens**
```
After adding to shopping list:
- Back button returns to Watermaker #2
- Equipment breadcrumb maintained
```

---

## SCENARIO 12: Real-time Breakdown Response (EMERGENCY)

**Persona**: Engineer
**Context**: Alarm sounds, running to machinery space
**Device**: Phone (running)
**Mental State**: Emergency response mode

**Natural Articulation**: "GEN-02" (reads from alarm panel)

### Journey (Optimized for Speed)

**Step 1: Quick Access**
```
User types: "GEN-02" (exact equipment code)
System: Fast single-result if exact code match
Auto-focus: If single match, immediately shows detail
```

**Step 2: Rapid Photo + Status**
```
Combined action flow (mobile-optimized):
1. Camera opens immediately (most likely need in breakdown)
2. User takes photo
3. Status dropdown pre-filled: "failed"
4. Single submit captures both photo + status
```

**Step 3: Work Order Prompt**
```
After photo + status saved:
System shows quick prompt:
  "Create work order for this issue?"
  [Yes] [Later]

If "Later":
  - Notification reminder created for 30 minutes
  - User can continue emergency response
```

**Step 4: Notification Cascade**
```sql
-- Immediate notifications
INSERT INTO pms_notifications VALUES
  -- Chief Engineer: Critical failure
  (chief_engineer_id, 'equipment_critical_failure', 'equipment', 'gen2-uuid',
   'CRITICAL: GEN-02 Failed', '...', 'critical', 'focus_equipment'),

  -- Captain: Critical equipment (if criticality=critical)
  (captain_id, 'equipment_critical_failure', 'equipment', 'gen2-uuid',
   'CRITICAL: Generator #2 Failed', '...', 'critical', 'focus_equipment');
```

### Mobile UX Considerations

| Context | System Behavior |
|---------|-----------------|
| Phone detected | Show camera button prominently |
| Exact code match | Auto-focus, skip result list |
| Status = failed | Auto-expand attention_reason field |
| Criticality = critical | Show notification preview |

---

## SCENARIO SUMMARY

| # | Scenario | Role | Primary Action | HTTP Codes |
|---|----------|------|----------------|------------|
| 1 | Generator breakdown | engineer | update_status + create_wo | 200, 200, 200 |
| 2 | Deckhand observation | deckhand | add_note | 200 |
| 3 | Morning attention review | chief_engineer | flag_attention (clear) | 200 |
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

## NEXT PHASE

Proceed to **PHASE 6: SQL BACKEND** to:
- Define exact SQL for each action
- Specify handler implementations
- Document transaction boundaries

---

**END OF PHASE 5**
