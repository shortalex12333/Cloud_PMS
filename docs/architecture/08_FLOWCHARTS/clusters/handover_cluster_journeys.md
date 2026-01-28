# Handover Cluster - User Journeys

**Cluster:** HANDOVER & COMMUNICATION
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Handover Entry
**Entry points:** Search → Handover List, Fault/WO/Equipment Detail → Add to Handover
**Terminal states:** acknowledged, archived
**Can create other entities:** None (handover is terminal output for shift continuity)
**Highest-risk action:** None (all actions are informational - no inventory, no operational state changes)

---

## SCOPE

**Cluster:** HANDOVER & COMMUNICATION
**Actions covered:** 8 / 8
**MVP actions:** 8
**Future actions:** 0
**Signature-required actions:** 0 (all informational)

**Purpose:** Transfer knowledge quickly, clearly, and consistently between crew shifts. Ensure continuity and reduce chaos in transitions.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Fault/WO Detail → Add to Handover = `CANDIDATE` → `ACTIVE`
**Primary actions shown:** Max 2-3 (add_to_handover, add_note prioritized for shift transitions)
**RAG influence:** Prefills summary from entity context, suggests critical items, never auto-commits

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (6)

| Action | Risk | Signature | Pattern | Status |
|--------|------|-----------|---------|--------|
| add_to_handover | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_document_to_handover | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_document_section_to_handover | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_note | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| edit_handover_section | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| acknowledge_handover | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |

### Read/Output Actions (2)

| Action | Purpose | Status |
|--------|---------|--------|
| export_handover | Generate PDF/email of handover for shift change | ✅ MVP |
| generate_summary | AI-generated summary of handover entries | ✅ MVP |

---

## GOLD JOURNEY (Primary Path)

**Link:** [Sarah's Night Shift - Fault → Handover](../../04_USER_JOURNEYS.md#journey-1-sarahs-night-shift--fault--handover)

**Actions covered:**
- add_to_handover (MUTATE_LOW)

**Pattern:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

**This is the most common path:** Crew adds entity (fault, equipment issue, etc.) to handover for next shift awareness.

---

## JOURNEY VARIATIONS

### V1: Add Document to Handover

**WHO:** Any crew member
**TRIGGER:** Found important manual section or procedure relevant to next shift
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User viewing document (e.g., "CAT 3512 Manual - Troubleshooting")
2. Clicks: [Add to Handover]
3. Form appears:
   ```
   Add Document to Handover

   Document: CAT 3512 Manual - Cooling System Troubleshooting
             (pre-filled, locked)

   Summary: [text field - required]
   "Brief note about why this is relevant"

   Priority: [Normal / High / Critical]

   [Cancel] [Add to Handover]
   ```
4. User enters: "Refer to Section 4.2 for Gen 2 coolant issue diagnosis"
5. Clicks [Add to Handover]
6. Success: "✓ Document added to handover"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT handover_entries (
     yacht_id, entity_type='document',
     entity_id=document_id,
     summary="Refer to Section 4.2 for Gen 2...",
     priority='normal',
     created_by, created_at
   )
2. INSERT ledger_events (
     event_type='handover_created',
     entity_type='handover', entity_id=new_entry_id,
     user_id, timestamp,
     summary="User added CAT 3512 Manual to handover"
   )
COMMIT
```

#### Differs from Gold

- **Links document** (not fault)
- **Provides manual reference** for next shift

#### System Guarantees

✅ Handover entry always created (or transaction fails)
✅ Document reference preserved
✅ Ledger entry written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

### V2: Add Document Section to Handover

**WHO:** Any crew member
**TRIGGER:** Found specific page/section of manual relevant to issue
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User viewing manual page (e.g., "CAT 3512 Manual, Page 47")
2. Clicks: [Add This Section to Handover]
3. Form appears:
   ```
   Add Manual Section to Handover

   Document: CAT 3512 Manual
   Section: Page 47 - Coolant Pump Seal Replacement

   Snippet: (first 200 chars shown)
   "1. Drain coolant from system. 2. Remove pump housing bolts..."

   Summary: [text field - required]
   "Why next shift needs to see this"

   [Cancel] [Add to Handover]
   ```
4. User enters: "Instructions for Gen 2 seal replacement. Parts arriving tomorrow."
5. Success: "✓ Manual section added to handover"

#### Database Operations

```sql
INSERT handover_entries (
  entity_type='document_section',
  entity_id=document_id,
  document_page=47,
  document_snippet="1. Drain coolant...",
  summary="Instructions for Gen 2 seal replacement...",
  priority='high'
)
```

#### Differs from V1

- **Specific page/section** (not whole document)
- **Includes snippet** for quick reference

---

### V3: Add Note (General Handover)

**WHO:** Any crew member
**TRIGGER:** Information that doesn't link to specific entity
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User types: "add to handover" or clicks [Handover] from menu
2. Form appears:
   ```
   Add Handover Note

   Summary: [text field - required]
   "Brief title for handover item"

   Details: [text area]
   "Full explanation"

   Priority: [Normal / High / Critical]

   Category: [Dropdown: General / Safety / Operations / Supplies]

   [Cancel] [Add Note]
   ```
3. User fills:
   - Summary: "Port fuel tank gauge reading incorrect"
   - Details: "Gauge shows 75% but dipstick confirms 90%. Likely sensor drift. Monitor for now."
   - Priority: Normal
   - Category: Operations
4. Success: "✓ Note added to handover"

#### Database Operations

```sql
INSERT handover_entries (
  entity_type='general',
  entity_id=NULL,
  summary="Port fuel tank gauge reading incorrect",
  details="Gauge shows 75% but dipstick confirms 90%...",
  priority='normal',
  category='operations'
)
```

#### Differs from Gold

- **No linked entity** (general note)
- **Categorized** for filtering

---

### V4: Edit Handover Entry

**WHO:** Entry creator or HOD
**TRIGGER:** Need to correct or add detail to existing entry
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views handover list
2. Clicks entry: "Gen 2 overheating (added by Sarah)"
3. Clicks: [Edit]
4. Form appears (pre-filled with current values):
   ```
   Edit Handover Entry

   Summary: "Generator 2 - Overheating (alarm triggered again)"

   Details: "Alarm triggered at 02:15. Checked coolant level - normal.
             Unsure of cause. Mike diagnosed this 2 days ago, issue
             may have returned."

   Priority: High

   [Cancel] [Save Changes]
   ```
5. User adds: "UPDATE: Mike confirmed pump seal failure. WO-123 created. Parts on order."
6. Success: "✓ Handover updated"

#### Database Operations

```sql
UPDATE handover_entries
SET details=CONCAT(details, '\n\nUPDATE: Mike confirmed pump seal failure...'),
    updated_by=user_id,
    updated_at=NOW()
WHERE id=entry_id
  AND (created_by=user_id OR user_role IN ('chief_engineer', 'captain'))
```

#### System Guarantees

✅ Only creator or HOD can edit
✅ Edit history preserved (updated_at tracked)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

### V5: Acknowledge Handover

**WHO:** Incoming shift crew
**TRIGGER:** Shift change, reviewing handover from previous shift
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. Mike arrives for day shift
2. Types: "handover"
3. Sees handover list with items from Sarah's night shift
4. Reviews each item
5. At bottom: [Acknowledge Handover]
6. Confirmation:
   ```
   Acknowledge Handover

   You are acknowledging:
   - 3 items from Sarah (3rd Engineer)
   - 1 item from Chief Engineer
   - 2 general notes

   By acknowledging, you confirm you have reviewed all handover items.

   Optional note: [text area]

   [Cancel] [Acknowledge]
   ```
7. Mike clicks [Acknowledge]
8. Success: "✓ Handover acknowledged"

#### Database Operations

```sql
-- Mark all unacknowledged entries for this shift as acknowledged
UPDATE handover_entries
SET acknowledged_by=user_id,
    acknowledged_by_name=user_name,
    acknowledged_at=NOW()
WHERE yacht_id=user_yacht_id
  AND acknowledged_at IS NULL
  AND created_at > (shift_start_time)
```

#### System Guarantees

✅ Acknowledgment logged (accountability)
✅ Timestamp recorded (when shift took over)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation** (batch update)

#### What Does NOT Happen

❌ No requirement to acknowledge (optional, but recommended)
❌ No signature (acknowledgment ≠ legal acceptance)
❌ Acknowledged items still visible (can be viewed in history)

---

### V6: Export Handover

**WHO:** HOD or crew preparing shift change report
**TRIGGER:** Shift change, crew rotation, management reporting
**PATTERN:** `[READ_ONLY]` with export action

#### Screen Flow

1. User views handover list
2. Clicks: [Export Handover]
3. Options appear:
   ```
   Export Handover

   Date Range: ○ Current shift  ● Last 24 hours  ○ This week

   Format: ● PDF  ○ Excel  ○ Email

   Include:
   ☑ All entries
   ☑ Acknowledged status
   ☑ Linked entities (faults, WOs)
   ☐ Photos/attachments

   [Cancel] [Export]
   ```
4. User selects options, clicks [Export]
5. Download: `Handover_2026-01-22.pdf`

#### What Gets Exported

- Handover entries (summary + details)
- Priority flags
- Creator names + timestamps
- Acknowledged by (if applicable)
- Linked entity references (clickable in PDF if digital)

#### System Guarantees

✅ Export includes all entries in range
✅ No data modification (READ-only)
✅ Ledger entry written (export logged for audit)

---

### V7: Generate Summary (AI)

**WHO:** HOD preparing shift summary
**TRIGGER:** Need concise overview of many handover items
**PATTERN:** `[READ_ONLY]` with AI processing

#### Screen Flow

1. User views handover list (12 items)
2. Clicks: [Generate Summary]
3. Processing: "Generating summary..."
4. AI summary appears:
   ```
   Handover Summary - Night Shift (Jan 22)

   🔴 High Priority (2 items):
   - Generator 2 pump seal failure confirmed. WO-123 created. Parts arriving Tue.
   - Port engine oil pressure trending down. Monitor next 24h.

   ⚠️ Normal Priority (8 items):
   - Bilge pump routine check completed.
   - Hydraulic hose replaced on deck crane.
   - ...

   ✅ Completed This Shift:
   - 4 work orders completed
   - 1 fault resolved

   📋 Action Required (Day Shift):
   - Receive parts delivery (Gen 2 seal)
   - Monitor port engine oil pressure
   ```
5. User can: [Copy] [Export as PDF] [Add to Email]

#### System Guarantees

✅ Summary generated from handover entries only
✅ Priority-based grouping
✅ No data modification
✅ Can regenerate if entries change

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] add_to_handover - Gold (Sarah's journey)
- [x] add_document_to_handover - V1
- [x] add_document_section_to_handover - V2
- [x] add_note - V3
- [x] edit_handover_section - V4
- [x] acknowledge_handover - V5

### Read/Output Actions
- [x] export_handover - V6
- [x] generate_summary - V7

**Coverage:** 8/8 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why |
|--------|------------|-----|
| add_to_handover | ❌ | No signature required (informational) |
| add_document_to_handover | ❌ | No signature required (informational) |
| add_document_section_to_handover | ❌ | No signature required (informational) |
| add_note | ❌ | No signature required (informational) |
| edit_handover_section | ❌ | No signature required (informational) |
| acknowledge_handover | ❌ | No signature required (informational) |
| export_handover | ❌ | No signature (READ-only) |
| generate_summary | ❌ | No signature (READ-only) |

**Rule:** All handover actions are informational. No operational state changes, no inventory impact, no signatures required.

---

## HANDOVER LIFECYCLE

```
NULL (no handover entry)
  ↓ add_to_handover / add_note / add_document
CREATED (visible in handover list)
  ↓ edit_handover_section (optional)
CREATED (updated)
  ↓ acknowledge_handover (by next shift)
ACKNOWLEDGED (shift accepted)
  ↓ (automatic after 7 days or manual)
ARCHIVED (moved to history, not in active list)
```

**No terminal "closed" state:** Handover entries persist until archived. Acknowledgment doesn't remove them.

---

## CROSS-CLUSTER RELATIONSHIPS

### Handover ← Faults
- Faults added to handover via `add_to_handover`
- Critical faults auto-create handover entries (`[AUTO_CREATE]`)
- See: `faults_cluster_journeys.md` V1

### Handover ← Work Orders
- WOs added to handover when status unclear or delayed
- See: `work_orders_cluster_journeys.md`

### Handover ← Equipment
- Equipment issues without formal fault can be added
- "Gen 3 running rough" → Handover note (not fault)

### Handover ← Documents
- Manual sections added for reference
- Bulletins, procedures shared across shifts

### Handover → Nothing
**Handover is terminal:** Doesn't create other entities. It's the output channel for continuity.

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Ambiguous Entity Link
**Trigger:** User types "add gen 2 to handover" but multiple Gen 2 entities exist (fault, WO, equipment)
**System behavior:** Show disambiguation: "Add to handover: ○ Fault #456 ○ WO-123 ○ Equipment (Gen 2)"
**Cannot proceed until:** User selects specific entity

### 2. Missing Summary
**Trigger:** User tries to add handover entry with empty summary field
**System behavior:** Show validation error: "Summary required (min 10 chars)"
**Cannot proceed until:** User enters summary

### 3. Edit Permission
**Trigger:** User tries to edit someone else's handover entry (not HOD)
**System behavior:** Show error: "Only entry creator or HOD can edit this handover item"
**Cannot proceed:** Action blocked

### 4. Duplicate Detection (Optional)
**Trigger:** User adds handover entry very similar to existing one
**System behavior:** Show: "Similar handover entry exists: '[summary]'. Add anyway?"
**User choice:** Add duplicate OR view existing entry

**Guardrail principle:** System stops for permission errors, warns for duplicates (doesn't block).

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | add_to_handover, add_document, add_section, add_note, edit, acknowledge | 6 |
| `[READ_ONLY]` | export, generate_summary | 2 |

**Note:** This cluster is intentionally simple. All mutations are single-step, informational, no signatures. This reflects handover's purpose: frictionless communication.

---

## AUTO_CREATE vs USER-INITIATED

**Most handover actions are USER-initiated:**
- Crew explicitly adds items they think next shift needs to know

**One exception - AUTO_CREATE:**
- `report_fault` with severity='critical' auto-creates handover entry
- See: `faults_cluster_journeys.md` V1
- This is `[AUTO_CREATE]` pattern (commits silently, no user confirmation)

**No AUTO_ESCALATION in this cluster:**
- System doesn't propose "add to handover?" prompts
- User decides what's worth handing over

---

**Status:** Handover cluster fully documented. Template fits naturally. All handover actions confirmed informational (no signatures). Batch 1 complete. Ready for sanity check.
