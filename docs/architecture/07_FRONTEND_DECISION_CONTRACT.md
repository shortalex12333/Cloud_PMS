# 07_FRONTEND_DECISION_CONTRACT.md

**Date:** 2026-01-22
**Purpose:** Deterministic rules for when situations activate, when actions surface, how RAG influences UI, and what payload shape frontend expects
**Status:** Global Contract (applies to all clusters)

---

## WHY THIS EXISTS

The frontend must NEVER infer when to show actions, when to activate situations, or when to trust RAG suggestions. This document is the single source of truth for:

1. **Situation lifecycle** (IDLE → CANDIDATE → ACTIVE)
2. **Action surfacing** (which buttons appear, when, and how many)
3. **RAG influence** (suggestions vs. execution authority)
4. **Payload contract** (what fields backend MUST return)

**Rule:** If it's not in this contract, frontend doesn't do it.

---

## A. SITUATION STATE MACHINE

### States

| State | Meaning | UI Behavior |
|-------|---------|-------------|
| `IDLE` | No entity in focus, search bar active | Show search results only, no action buttons |
| `CANDIDATE` | Entity clicked, detail view opening | Show entity summary + primary actions (max 2-3) |
| `ACTIVE` | User clicked action or opened form | Show action form with prefill, commit button enabled |
| `COOLDOWN` | User completed action, showing success | Remain on entity detail, show "next actions" suggestions |
| `IDLE` (return) | 30 seconds of inactivity or user navigates away | Clear entity context, return to search |

### Triggers (Deterministic)

| Trigger Event | State Transition | Example |
|---------------|------------------|---------|
| User types in search bar | → `IDLE` | "gen 2 overheating" |
| User clicks search result (entity) | `IDLE` → `CANDIDATE` | Clicks "Generator 2" |
| User clicks action button | `CANDIDATE` → `ACTIVE` | Clicks [Create Work Order] |
| User clicks [Confirm] in form | `ACTIVE` → `COOLDOWN` | Confirms "Report Fault" |
| Success message shown (3 sec) | `COOLDOWN` → `CANDIDATE` | "✓ Fault reported" → back to entity detail |
| 30 sec idle OR user navigates | `CANDIDATE/COOLDOWN` → `IDLE` | Timeout or clicks search bar |

### Domain-Specific Overrides

**Documents (READ-only domain):**
- `CANDIDATE` state only (no `ACTIVE` for mutations)
- Action buttons: [View], [Add to Handover], [Show Related]
- No mutation forms

**Receiving Session (RESUMABLE domain):**
- `ACTIVE` state persists across page refreshes (session_id stored)
- Banner shows: "You have an active receiving session RCV-2026-001"
- Click banner → returns to `ACTIVE` state at last checked item

**Checklists (LOOPING domain):**
- `ACTIVE` state persists until all items checked
- Progress bar shows: "5/12 items checked"
- Cannot exit `ACTIVE` until completion or explicit cancel

### Core Principle

**Situations never activate automatically.** User must explicitly click to transition from `IDLE` to `CANDIDATE`.

**RAG cannot trigger state transitions.** Only user clicks.

---

## B. ACTION SURFACING RULES

### Rule 1: Search Results = Zero Actions

**Hard constraint:** Search results MUST NEVER show action buttons or editable fields.

**Allowed in search results:**
- ✅ Entity name + one-line summary
- ✅ Status badge ("Overdue", "Critical", "Out of Stock")
- ✅ Domain grouping ("Faults", "Work Orders", "Parts")
- ✅ Confidence indicator (internal - not shown to user)

**Forbidden in search results:**
- ❌ Action buttons ([Create WO], [Add to Handover])
- ❌ Editable fields
- ❌ Auto-open entity (even at 100% confidence)

**Why:** Trust depends on this boundary. Search informs, never nudges.

---

### Rule 2: Entity Detail = Max 2-3 Primary Actions

**When `CANDIDATE` state activates (entity detail view):**

Show **2-3 primary actions only**, selected by:

1. **Role permission** (filter by user role first)
2. **Entity state** (fault.status = 'reported' → cannot close)
3. **Journey frequency** (gold journey actions prioritized)
4. **Risk level** (MUTATE_LOW before MUTATE_HIGH)

Everything else goes behind **"More ▾"** dropdown.

**Example (Fault Detail - Engineer Role):**

Primary actions:
- [Diagnose Fault] (MUTATE_MEDIUM, gold journey)
- [Add Note] (MUTATE_LOW, frequent)
- [More ▾] → dropdown with 8 other actions

**Not this:**
- ❌ 12 buttons in a grid (overwhelming)
- ❌ Greyed-out buttons for forbidden actions (hide instead)

---

### Rule 3: Primary Action Selection Algorithm

```typescript
function selectPrimaryActions(entity, user, actions) {
  // 1. Filter by permission
  const allowed = actions.filter(a => hasPermission(user.role, a));

  // 2. Filter by entity state
  const available = allowed.filter(a => isAvailable(entity.state, a));

  // 3. Rank by frequency + risk
  const ranked = available.sort((a, b) => {
    if (a.is_gold_journey && !b.is_gold_journey) return -1;
    if (a.risk_level === 'LOW' && b.risk_level !== 'LOW') return -1;
    return 0;
  });

  // 4. Take top 2-3
  return ranked.slice(0, 3);
}
```

**Output:**
- Primary actions (visible buttons)
- Secondary actions (dropdown under "More")

**Guardrail:** If only 1 action available, show 1 button (not 3 placeholders).

---

### Rule 4: Permission Handling

**Hidden by default, NOT greyed out.**

**Wrong:**
```
[Approve Purchase] (greyed, with tooltip "You don't have permission")
```

**Right:**
```
(Button not shown at all)
```

**Why:** Reduces visual clutter, eliminates "why can't I click this?" confusion.

**Exception:** If action recently removed due to state change (e.g., fault closed), show temporary message: "This fault is closed. Reopen to edit."

---

### Rule 5: Conflict Handling (Multiple MUTATE Candidates)

**Scenario:** User searches "fix gen 2" but yacht has 3 generators.

**System behavior:**
- Show disambiguation UI
- List 3 options (Generator 2A, 2B, 2C)
- User MUST select one
- No auto-selection (even at high confidence)

**Scenario:** User types "create work order" but fault has multiple unresolved issues.

**System behavior:**
- Show chooser: "Create work order for which fault?"
- List faults with equipment context
- User MUST select one
- No auto-assume

**Rule:** Multiple MUTATE candidates → show chooser, never auto-execute.

---

## C. RAG INFLUENCE RULES

### What RAG Can Do

RAG outputs are **assistive, not authoritative**.

**Allowed:**

1. **Suggest actions**
   ```json
   {
     "suggested_actions": [
       {
         "action_id": "diagnose_fault",
         "confidence": 0.85,
         "reason": "Manual section found: CAT 3512 Troubleshooting"
       }
     ]
   }
   ```
   - Frontend shows: "💡 Suggested: Diagnose Fault (manual found)"
   - User must click to proceed

2. **Prefill form fields**
   ```json
   {
     "prefill": {
       "equipment_id": "uuid-gen-2",
       "equipment_name": "Generator 2",
       "symptom": "overheating",
       "source": "search_query",
       "confidence": 0.92
     }
   }
   ```
   - Fields pre-filled but editable
   - User can override

3. **Provide evidence links**
   ```json
   {
     "evidence": [
       {
         "type": "manual_page",
         "title": "CAT 3512 - Cooling System Troubleshooting",
         "page": 47,
         "url": "/documents/cat-3512-manual#page=47"
       }
     ]
   }
   ```
   - Shown as "📄 Related: CAT 3512 Manual, Page 47"
   - Click to open (READ action)

4. **Raise warnings**
   ```json
   {
     "warnings": [
       {
         "type": "recurring_fault",
         "message": "Similar fault occurred 3 times in last 30 days",
         "severity": "medium"
       }
     ]
   }
   ```
   - Shown as banner: "⚠️ Recurring issue detected"
   - Does not block action

### What RAG Cannot Do

**Forbidden:**

❌ **Execute actions**
- RAG suggests "create work order" → user must confirm

❌ **Activate situations**
- RAG confidence = 0.95 → does NOT auto-open entity
- User must click search result

❌ **Commit mutations**
- RAG prefills form → user must click [Confirm]

❌ **Override user input**
- If RAG prefills "Generator 2" but user changes to "Generator 3" → user wins

### Confidence Thresholds

**From search query extraction:**

| Confidence | Action | Example |
|------------|--------|---------|
| 0.0 - 0.5 | No suggestion | Ambiguous query, show search results only |
| 0.5 - 0.7 | Suggest READ action | "💡 Try: View Generator 2 history" |
| 0.7 - 0.9 | Suggest MUTATE with prefill | "💡 Suggested: Report Fault (form pre-filled)" |
| 0.9 - 1.0 | Strong prefill + highlight | Form auto-opens with prefill, user confirms |

**Critical rule:** Even at 1.0 confidence, user must click [Confirm] to commit.

### RAG as "Invisible Copilot"

**Mental model:** RAG is a helpful assistant that:
- Points to relevant documents
- Fills out tedious form fields
- Warns about patterns
- **Never takes control**

**User always has final say.**

---

## D. BACKEND PAYLOAD SHAPE (CONTRACT)

### Shape 1: Search Results

**Endpoint:** `POST /api/search`

**Request:**
```json
{
  "query": "gen 2 overheating",
  "user_id": "uuid-user",
  "yacht_id": "uuid-yacht"
}
```

**Response:**
```json
{
  "results": [
    {
      "entity_type": "equipment",
      "entity_id": "uuid-gen-2",
      "entity_name": "Generator 2",
      "summary": "MTU 12V4000 M93L - Port Side",
      "status": "operational",
      "confidence": 0.95,
      "badges": ["critical_parts_low"],
      "domain": "equipment"
    },
    {
      "entity_type": "fault",
      "entity_id": "uuid-fault-123",
      "entity_name": "Generator 2 - Overheating",
      "summary": "Reported 2 days ago by Sarah",
      "status": "diagnosed",
      "confidence": 0.88,
      "badges": ["unresolved"],
      "domain": "faults"
    }
  ],
  "total_results": 2,
  "query_interpretation": {
    "equipment_detected": "Generator 2",
    "symptom_detected": "overheating",
    "confidence": 0.92
  }
}
```

**Frontend contract:**
- MUST render `results[]` as list
- MUST show `badges[]` as visual indicators
- MUST NOT show action buttons (Rule 1)
- Click result → transition to Shape 2 (entity detail)

---

### Shape 2: Entity Detail

**Endpoint:** `GET /api/entities/{entity_type}/{entity_id}`

**Response:**
```json
{
  "entity_type": "fault",
  "entity_id": "uuid-fault-123",
  "entity_name": "Generator 2 - Overheating",
  "entity_data": {
    "equipment_id": "uuid-gen-2",
    "equipment_name": "Generator 2",
    "symptom": "overheating",
    "severity": "high",
    "status": "diagnosed",
    "reported_by": "Sarah (3rd Engineer)",
    "reported_at": "2026-01-20T02:15:00Z",
    "diagnosis": "Coolant pump seal failure suspected",
    "linked_entities": {
      "work_order": {
        "id": "uuid-wo-123",
        "title": "Replace Gen 2 Coolant Pump Seal",
        "status": "active"
      }
    }
  },
  "situation_state": "CANDIDATE",
  "allowed_actions": [
    {
      "action_id": "diagnose_fault",
      "action_name": "Diagnose Fault",
      "risk_level": "MEDIUM",
      "requires_signature": false,
      "is_primary": true,
      "available": true,
      "availability_reason": null
    },
    {
      "action_id": "add_fault_note",
      "action_name": "Add Note",
      "risk_level": "LOW",
      "requires_signature": false,
      "is_primary": true,
      "available": true
    },
    {
      "action_id": "close_fault",
      "action_name": "Close Fault",
      "risk_level": "HIGH",
      "requires_signature": true,
      "is_primary": false,
      "available": false,
      "availability_reason": "Fault must be resolved before closing"
    }
  ],
  "suggested_actions": [
    {
      "action_id": "create_work_order_from_fault",
      "confidence": 0.85,
      "reason": "Diagnosis suggests repair needed"
    }
  ],
  "prefill": {
    "equipment_id": "uuid-gen-2",
    "equipment_name": "Generator 2",
    "symptom": "overheating"
  },
  "evidence": [
    {
      "type": "manual_page",
      "title": "CAT 3512 - Cooling System",
      "url": "/documents/cat-3512#page=47"
    }
  ],
  "warnings": []
}
```

**Frontend contract:**
- MUST render entity detail using `entity_data`
- MUST filter `allowed_actions[]` where `is_primary=true` (show max 3)
- MUST hide actions where `available=false` (not grey out)
- MAY show `suggested_actions[]` as hints (not buttons)
- MUST use `prefill` when user clicks action
- MAY show `evidence[]` as related links

---

### Shape 3: Action Preview (Form Open)

**Endpoint:** `GET /api/actions/{action_id}/preview?entity_id={entity_id}`

**Response:**
```json
{
  "action_id": "create_work_order_from_fault",
  "action_name": "Create Work Order from Fault",
  "form_fields": [
    {
      "field_name": "title",
      "field_type": "text",
      "required": true,
      "prefill": "Replace Generator 2 Coolant Pump Seal",
      "validation": {
        "min_length": 5
      }
    },
    {
      "field_name": "description",
      "field_type": "textarea",
      "required": true,
      "prefill": "Fault diagnosis: Coolant pump seal failure. Replace seal and test system.",
      "validation": {
        "min_length": 10
      }
    },
    {
      "field_name": "priority",
      "field_type": "select",
      "required": true,
      "prefill": "high",
      "options": ["low", "normal", "high", "urgent"]
    },
    {
      "field_name": "assigned_to",
      "field_type": "user_select",
      "required": false,
      "prefill": null,
      "options": [
        {"user_id": "uuid-mike", "name": "Mike (2nd Engineer)"},
        {"user_id": "uuid-chief", "name": "Chief Engineer"}
      ]
    }
  ],
  "requires_signature": false,
  "confirmation_message": "This will create a work order and link it to the fault.",
  "gating": {
    "needs_pin": false,
    "needs_signature": false,
    "needs_clarification": false
  },
  "warnings": []
}
```

**Frontend contract:**
- MUST render form using `form_fields[]`
- MUST prefill fields where `prefill` is not null
- MUST validate using `validation` rules
- MUST show confirmation message before submit
- MUST check `gating` flags (PIN, signature, clarification)

---

### Shape 4: Action Commit Result

**Endpoint:** `POST /api/actions/{action_id}/execute`

**Request:**
```json
{
  "entity_id": "uuid-fault-123",
  "field_values": {
    "title": "Replace Generator 2 Coolant Pump Seal",
    "description": "...",
    "priority": "high",
    "assigned_to": "uuid-mike"
  },
  "signature_data": null,
  "pin": null
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "✓ Work order WO-567 created",
  "entity_created": {
    "entity_type": "work_order",
    "entity_id": "uuid-wo-567",
    "entity_name": "Replace Generator 2 Coolant Pump Seal"
  },
  "ledger_event_id": "uuid-ledger-123",
  "audit_log_id": null,
  "next_actions": [
    {
      "action_id": "add_wo_part",
      "action_name": "Add Parts to Work Order",
      "reason": "Specify parts needed for repair"
    }
  ],
  "situation_state": "COOLDOWN"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error_code": "VALIDATION_FAILED",
  "error_message": "Title must be at least 5 characters",
  "field_errors": {
    "title": "Too short"
  },
  "situation_state": "ACTIVE"
}
```

**Frontend contract:**
- IF `success=true`: Show success message, offer `next_actions[]`, transition to `COOLDOWN`
- IF `success=false`: Show `error_message`, highlight `field_errors`, remain in `ACTIVE`
- MUST write `ledger_event_id` to local log (for offline sync)

---

## E. PRIMARY ACTION SELECTION (DETERMINISTIC)

### Selection Criteria (Priority Order)

**Step 1: Permission Filter**
- Remove actions where `user.role` not in `allowed_roles`

**Step 2: State Availability Filter**
- Remove actions where `entity.state` does not allow action
- Example: Cannot close fault with status='reported'

**Step 3: Rank by Gold Journey**
- Actions in gold journeys rank higher
- Example: `diagnose_fault` in "Mike's Morning" gold journey → prioritized

**Step 4: Rank by Risk Level**
- MUTATE_LOW before MUTATE_MEDIUM before MUTATE_HIGH
- Rationale: Low-friction actions first

**Step 5: Rank by Frequency**
- Actions used >50% of time rank higher
- Based on ledger event counts (backend analytics)

**Step 6: Take Top 2-3**
- Primary actions: positions 1-3
- Secondary actions: dropdown under "More"

### Example (Fault Detail - 3rd Engineer)

**Available actions after filters:**
1. diagnose_fault (MEDIUM, gold journey, 85% frequency)
2. add_fault_note (LOW, gold journey, 90% frequency)
3. add_fault_photo (LOW, 60% frequency)
4. create_work_order_from_fault (MEDIUM, gold journey, 70% frequency)
5. add_to_handover (LOW, gold journey, 95% frequency)
6. mark_fault_false_alarm (LOW, 15% frequency)
7. show_manual_section (READ, 50% frequency)

**Ranking logic:**
- add_fault_note (LOW, gold, 90%) → #1
- diagnose_fault (MEDIUM, gold, 85%) → #2
- add_to_handover (LOW, gold, 95%) → #3

**Result:**
- **Primary:** [Add Note] [Diagnose Fault] [Add to Handover]
- **More ▾:** create_work_order, add_photo, false_alarm, show_manual

---

## F. SPECIAL CASES

### Resumable Sessions

**Receiving session, checklists:**
- `situation_state` persists across page refreshes
- Backend stores `session_id` in user context
- Frontend shows banner: "You have an active receiving session RCV-2026-001"
- Click banner → resume at last checkpoint

**Payload:**
```json
{
  "resumable_session": {
    "session_type": "receiving",
    "session_id": "uuid-session-123",
    "session_name": "RCV-2026-001",
    "progress": "3/5 items checked",
    "resume_url": "/receiving/uuid-session-123"
  }
}
```

---

### Multi-Entity Selection

**Purchase order creation from multiple shopping items:**
- User selects 5 items from list (checkboxes)
- Clicks [Create Purchase Order]
- Backend validates: all items approved, same supplier
- Frontend shows PO form with items pre-listed

**No auto-selection.** User must explicitly check items.

---

### Offline Mode (Future)

**Not MVP, but contract should allow:**
- Actions queue locally
- Sync when connection restored
- `ledger_event_id` used for deduplication

**Payload includes:**
```json
{
  "offline_capable": true,
  "idempotency_key": "uuid-event-123"
}
```

---

## G. VALIDATION SUMMARY

### Frontend Validates (Before Sending)
- ✅ Required fields filled
- ✅ Field format (email, numeric, min/max length)
- ✅ Client-side constraints (positive numbers, date ranges)

### Backend Validates (Authority)
- ✅ Permission check (role, ownership)
- ✅ State machine rules (cannot skip states)
- ✅ Business logic (cannot adjust inventory to negative)
- ✅ Signature requirements (if gating.needs_signature)

**Rule:** Frontend validation is UX. Backend validation is security.

---

## H. ERROR HANDLING

### Error Types

| Error Code | Meaning | Frontend Action |
|------------|---------|-----------------|
| `VALIDATION_FAILED` | Form field validation error | Highlight field, show message, stay in form |
| `PERMISSION_DENIED` | User lacks role permission | Show error modal, return to entity detail |
| `STATE_CONFLICT` | Entity state forbids action | Show explanation, suggest alternative action |
| `NETWORK_ERROR` | Connection lost | Show retry button, queue for offline sync |
| `SIGNATURE_REQUIRED` | Signature missing for high-risk action | Show signature prompt, retry |

### Retry Logic

**Transient errors (NETWORK_ERROR):**
- Retry 3 times with exponential backoff (1s, 2s, 4s)
- If still fails, show: "Cannot connect. Action will sync when online."

**Permanent errors (PERMISSION_DENIED, STATE_CONFLICT):**
- Do not retry
- Show clear explanation + alternative path

---

## I. PERFORMANCE CONTRACT

### Response Time Targets

| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| Search | 200ms | 500ms |
| Entity detail | 300ms | 800ms |
| Action preview | 150ms | 400ms |
| Action commit | 500ms | 2000ms |

### Payload Size Limits

| Payload | Max Size | Reason |
|---------|----------|--------|
| Search results | 50 results | Prevent scroll fatigue |
| Entity detail | 5 KB | Mobile bandwidth |
| Form prefill | 2 KB | Fast render |

### Caching Rules

**Frontend may cache:**
- ✅ Search results (5 min TTL)
- ✅ Entity detail (2 min TTL)
- ❌ Action preview (always fresh - state-dependent)
- ❌ Commit result (never cache)

---

## J. ACCESSIBILITY

### Keyboard Navigation

**Required shortcuts:**
- `/` → Focus search bar
- `Esc` → Cancel form, return to entity detail
- `Enter` → Submit form (when in text field)
- `Tab` → Navigate form fields

### Screen Reader

**ARIA labels required:**
- `role="search"` on search bar
- `role="button"` on action buttons
- `aria-label="Add note to fault"` on icons
- `aria-live="polite"` on success messages

---

## K. TESTING CONTRACT

### Frontend Must Test

**Situation state transitions:**
- IDLE → CANDIDATE on entity click
- CANDIDATE → ACTIVE on action click
- ACTIVE → COOLDOWN on success
- Timeout returns to IDLE

**Action surfacing:**
- Max 3 primary actions shown
- Hidden actions in dropdown
- Forbidden actions not rendered (not greyed)

**RAG prefill:**
- Fields pre-filled but editable
- User can override prefill
- Prefill never auto-commits

### Backend Must Provide

**Test fixtures for:**
- Search results with varying confidence
- Entity detail with all `allowed_actions[]` permutations
- Action preview with all field types
- Error responses for all error codes

---

## L. MIGRATION PATH

**For MVP:**
- Implement Shapes 1-4 (search, detail, preview, commit)
- Implement Situation states (IDLE, CANDIDATE, ACTIVE)
- Implement primary action selection (max 3)

**Post-MVP:**
- Add resumable session banner
- Add offline queueing
- Add keyboard shortcuts
- Refine confidence thresholds based on real usage

---

**Status:** Frontend contract locked. This is the deterministic truth table for all UI decisions. Backend must honor payload shapes. Frontend must not infer beyond this contract.
