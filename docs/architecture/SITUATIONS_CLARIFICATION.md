# SITUATIONS CLARIFICATION

**Date:** 2026-01-22
**Purpose:** Definitive explanation of "Situations" as UI active states (NOT operational context)
**Status:** Architecture Contract - Locked

---

## WHAT WE THOUGHT VS. WHAT IT IS

### What We Originally Thought
"Situations" = Inferred operational contexts like:
- At sea
- In port
- In shipyard
- Emergency mode

**Wrong.** That's operational context detection, which is NOT what "situations" means in CelesteOS.

---

### What It Actually Is

**"Situation" = Frontend Active State**

A situation is the **current UI mode** that the frontend is in, driven by:
1. What the user searched for
2. What entity they clicked
3. What action they previewed
4. What form they're filling
5. What they confirmed/cancelled

**Situations are 100% user-driven, NOT system-inferred.**

---

## SITUATION STATE MACHINE

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌──────┐  search   ┌───────────┐  click    ┌────────┐
│  │ IDLE │ ────────> │ CANDIDATE │ ────────> │ ACTIVE │
│  └──────┘           └───────────┘           └────────┘
│     ▲                     │                      │
│     │                     │ cancel               │ confirm
│     │                     ▼                      ▼
│     │                ┌──────────┐          ┌──────────┐
│     └────────────────│ COOLDOWN │<─────────│  COMMIT  │
│                      └──────────┘          └──────────┘
│                           │                      │
│                           │ timeout (5s)         │ success
│                           └──────────────────────┘
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## STATE DEFINITIONS

### IDLE
**When:** No active search, no entity selected, no action in progress
**UI State:**
- Search bar empty or showing placeholder
- No entity detail cards visible
- No action forms open
- No loading spinners

**Example:**
User just logged in, sees dashboard summary, no interaction yet.

---

### CANDIDATE
**When:** Search results shown, entities available for selection
**UI State:**
- Search results list visible (entities + metadata)
- No entity detail open yet
- Actions: ZERO (per Rule 1)
- User can click an entity to transition to ACTIVE

**Example:**
User typed "gen 2 overheating", sees 3 fault entities in results list.

**Transitions:**
- User clicks entity → ACTIVE
- User clears search → IDLE
- User searches again → CANDIDATE (new results)

---

### ACTIVE
**When:** Entity detail open, actions surfaced, user can interact
**UI State:**
- Entity detail card visible
- Primary actions (2-3) shown as buttons
- "More ▾" dropdown available
- RAG suggestions (if any) shown in yellow banners
- Evidence/Related section populated

**Example:**
User clicked "Fault #F-456 (Gen 2 overheating)", sees fault detail with [Diagnose] [Add Note] [Add to Handover] buttons.

**Transitions:**
- User clicks action → ACTION_PREVIEW
- User clicks back/closes entity → CANDIDATE (returns to search results)
- User clicks related entity → ACTIVE (new entity, new detail card)
- User cancels → COOLDOWN

---

### ACTION_PREVIEW (Sub-state of ACTIVE)
**When:** User clicked action, form opened, preview shown
**UI State:**
- Action form visible (fields prefilled by RAG if applicable)
- Preview panel showing diff (for MUTATE actions)
- Buttons: [Cancel] [Confirm]
- User can edit fields

**Example:**
User clicked [Diagnose Fault], sees form with prefilled "Symptom: Overheating", "Likely cause: Coolant pump seal failure (Manual pg. 47)", [Cancel] [Confirm].

**Transitions:**
- User clicks Confirm → COMMIT
- User clicks Cancel → COOLDOWN
- User edits fields → remains in ACTION_PREVIEW

---

### COMMIT
**When:** User confirmed action, backend executing, response pending
**UI State:**
- Loading spinner visible
- Form inputs disabled
- "Saving..." or "Executing..." message
- User cannot cancel (point of no return)

**Example:**
User clicked [Confirm] on "Diagnose Fault" form, backend writing diagnosis to pms_faults, awaiting response.

**Transitions:**
- Backend success → COOLDOWN (show success toast, return to ACTIVE)
- Backend error → COOLDOWN (show error toast, allow retry)

---

### COOLDOWN
**When:** Action completed (success or error), brief UI pause before returning to normal
**UI State:**
- Success toast (green) or error toast (red) visible for 3-5 seconds
- Entity detail card still visible (refreshed with new data if success)
- Actions available again after cooldown

**Example:**
User successfully diagnosed fault, sees green toast "✓ Diagnosis saved", fault detail refreshes to show new diagnosis.

**Transitions:**
- Timeout (3-5s) → ACTIVE (toast dismisses, user can act again)
- User manually dismisses toast → ACTIVE
- User closes entity → CANDIDATE or IDLE

---

## SPECIAL CASE: RESUMABLE SITUATIONS

Some actions create **persistent sub-situations** that can be resumed later:

### Receiving Session (Resumable)
**When:** User starts "Receive Items" action, begins checking in PO items
**UI State:**
- Receiving session card visible (orange banner: "Receiving Session Active")
- List of PO items with checkboxes
- [Check In] button per item
- [Commit Session] button (signature required)
- [Cancel Session] button

**Persistence:**
- Session survives page refresh (stored in backend)
- User can navigate away, return later
- Banner shows: "You have an active receiving session. [Resume] [Cancel]"

**Transitions:**
- User clicks [Resume] → ACTIVE (receiving session)
- User clicks [Commit Session] → COMMIT → COOLDOWN → IDLE (session ends)
- User clicks [Cancel Session] → COOLDOWN → IDLE (session discarded)

---

### Checklist Execution (Resumable)
**When:** User opens checklist for work order, starts marking items complete
**UI State:**
- Checklist card visible (blue banner: "Checklist: 3/10 items complete")
- List of checklist items with completion status
- [Mark Complete] per item
- [Complete Checklist] button (signature required, only when all required items done)

**Persistence:**
- Checklist state saved in backend
- User can close, return later
- Banner shows: "Checklist in progress (3/10). [Resume]"

**Transitions:**
- User clicks [Resume] → ACTIVE (checklist)
- User completes all items → [Complete Checklist] enabled
- User clicks [Complete Checklist] → COMMIT → COOLDOWN → IDLE (checklist marked complete)

---

## SITUATION TRIGGERS (What Causes State Changes)

### IDLE → CANDIDATE
**Trigger:** User enters search query + presses Enter OR selects search suggestion
**Backend:** Search API called, results returned
**Frontend:** Renders search results list

---

### CANDIDATE → ACTIVE
**Trigger:** User clicks entity in search results
**Backend:** Entity detail API called
**Frontend:** Renders entity detail card with actions

---

### ACTIVE → ACTION_PREVIEW
**Trigger:** User clicks primary action button OR "More ▾" action
**Backend:** Prefill API called (if action has prefill step)
**Frontend:** Renders action form with prefilled values

---

### ACTION_PREVIEW → COMMIT
**Trigger:** User clicks [Confirm] button
**Backend:** Execute API called (mutation committed)
**Frontend:** Disables form, shows loading spinner

---

### COMMIT → COOLDOWN
**Trigger:** Backend responds (success or error)
**Frontend:** Shows toast notification, refreshes entity data

---

### COOLDOWN → ACTIVE
**Trigger:** Timeout (3-5s) OR user dismisses toast
**Frontend:** Hides toast, enables actions again

---

### ACTIVE → CANDIDATE
**Trigger:** User clicks back button OR closes entity detail
**Frontend:** Returns to search results list

---

### CANDIDATE → IDLE
**Trigger:** User clears search OR navigates away from search page
**Frontend:** Returns to dashboard/home view

---

## SITUATIONS DO NOT INFER CONTEXT

**Situations are NOT:**
- ❌ Operational mode detection ("yacht is at sea")
- ❌ Environmental sensing ("engine room is hot")
- ❌ Predictive alerts ("failure imminent")
- ❌ Automatic action execution ("create work order automatically")

**Situations ARE:**
- ✅ UI mode ("user is viewing fault detail")
- ✅ Interaction state ("user is filling diagnosis form")
- ✅ Navigation state ("user came from search results")
- ✅ Progress tracking ("receiving session 60% complete")

---

## RAG'S ROLE IN SITUATIONS

**RAG can influence but NOT control situations.**

**Allowed:**
- ✅ Prefill action form fields (user can edit)
- ✅ Suggest actions (user must click to activate)
- ✅ Show evidence links (user can click to navigate)
- ✅ Warn about patterns ("recurring issue detected")

**Forbidden:**
- ❌ Auto-transition situations (e.g., skip CANDIDATE → ACTIVE)
- ❌ Auto-execute actions (e.g., skip ACTION_PREVIEW → COMMIT)
- ❌ Override user input (e.g., force prefilled values)
- ❌ Change action grouping (e.g., promote action to Primary)

**Example:**
RAG detects "Gen 2 overheating" matches Manual pg. 47.
- ✅ Allowed: Show yellow banner "💡 Manual pg. 47 suggests checking coolant pump seal" with [View Manual] link
- ❌ Forbidden: Auto-open Manual pg. 47 without user clicking

---

## SITUATION PERSISTENCE

### Session-Scoped Situations (Lost on Refresh)
- CANDIDATE (search results)
- ACTIVE (entity detail)
- ACTION_PREVIEW (form open)

**Reason:** These are transient UI states. Re-searching/re-clicking is expected.

---

### Persistent Situations (Survive Refresh)
- Receiving Session (backend state: receiving_sessions table)
- Checklist Execution (backend state: pms_checklist_items)

**Reason:** These are multi-step processes requiring resumability.

**UI Treatment:**
- Show resumable banner at top of page
- User can click [Resume] to return to persistent situation
- User can click [Cancel] to discard persistent situation

---

## SITUATIONS ≠ PERMISSIONS ≠ STATE

**Three Orthogonal Concepts:**

### 1. Situation (UI Mode)
**What it is:** Current frontend active state
**Controlled by:** User actions (search, click, confirm)
**Example:** User is in ACTIVE situation viewing Fault #F-456

---

### 2. Permission (Role-Based Access)
**What it is:** What actions user.role can execute
**Controlled by:** Backend auth middleware
**Example:** 3rd Engineer cannot mark work order complete (only Chief Engineer can)

---

### 3. State (Entity Status)
**What it is:** Current lifecycle stage of entity
**Controlled by:** Backend mutation logic
**Example:** Fault status='resolved' (cannot diagnose resolved fault)

**Situations use permissions + state to determine which actions to surface, but situations themselves are independent.**

---

## EXAMPLE: FULL SITUATION FLOW

**Scenario:** Sarah (3rd Engineer) diagnoses a fault

### Step 1: IDLE
Sarah is on dashboard, no active search.

---

### Step 2: IDLE → CANDIDATE
Sarah types "gen 2 overheating" in search bar, presses Enter.
- **Trigger:** Search query submitted
- **Backend:** Search API returns 3 faults
- **Frontend:** Renders search results (3 fault cards, zero actions)
- **Situation:** CANDIDATE

---

### Step 3: CANDIDATE → ACTIVE
Sarah clicks "Fault #F-456 (Gen 2 - Coolant temp alarm triggered)"
- **Trigger:** Entity clicked
- **Backend:** Entity detail API returns fault data
- **Frontend:** Renders fault detail card with actions
- **Actions Surfaced:**
  - Primary: [Diagnose Fault] [Add Note] [Add to Handover]
  - More ▾: [Add Photo] [Show Manual] [View Equipment]
  - Evidence: View Equipment (#EQ-002), Manual pg. 47, Similar Faults (2)
- **Situation:** ACTIVE

---

### Step 4: ACTIVE → ACTION_PREVIEW
Sarah clicks [Diagnose Fault]
- **Trigger:** Action button clicked
- **Backend:** Prefill API returns RAG suggestions
  - Symptom: "Overheating"
  - Likely Cause: "Coolant pump seal failure (Manual pg. 47)"
- **Frontend:** Renders diagnosis form with prefilled values (Sarah can edit)
- **Situation:** ACTION_PREVIEW (sub-state of ACTIVE)

---

### Step 5: ACTION_PREVIEW → COMMIT
Sarah reviews prefill, adds note "Confirmed seal leaking, see photo", clicks [Confirm]
- **Trigger:** Confirm button clicked
- **Backend:** Execute API called, writes to pms_faults(~metadata->'diagnosis')
- **Frontend:** Disables form, shows "Saving diagnosis..." spinner
- **Situation:** COMMIT

---

### Step 6: COMMIT → COOLDOWN
Backend responds: success
- **Trigger:** API response received
- **Backend:** Returns updated fault data (diagnosis saved)
- **Frontend:** Shows green toast "✓ Diagnosis saved", refreshes fault detail
- **Situation:** COOLDOWN (3s timeout)

---

### Step 7: COOLDOWN → ACTIVE
Toast auto-dismisses after 3 seconds
- **Trigger:** Timeout
- **Frontend:** Hides toast, enables actions again
- **Situation:** ACTIVE (Sarah can now create work order, add note, etc.)

---

## SITUATIONS IN ERROR SCENARIOS

### Scenario: Backend Error During COMMIT

**Step 1-4:** Same as above (Sarah fills diagnosis form)

**Step 5:** Sarah clicks [Confirm]
- **Situation:** COMMIT

**Step 6:** Backend responds: error (e.g., network timeout, validation failure)
- **Trigger:** API error response
- **Frontend:** Shows red toast "❌ Failed to save diagnosis. Please try again."
- **Situation:** COOLDOWN (3s timeout)

**Step 7:** Toast auto-dismisses
- **Frontend:** Returns to ACTION_PREVIEW (form still filled, Sarah can retry)
- **Situation:** ACTION_PREVIEW

**Sarah's options:**
- Edit diagnosis and click [Confirm] again (retry)
- Click [Cancel] to discard and return to ACTIVE

---

## SITUATIONS AND NAVIGATION

### Intra-Entity Navigation (Staying in ACTIVE)
**Example:** Sarah views Fault #F-456, clicks "View Equipment (#EQ-002)" in Evidence section
- **Situation:** Remains ACTIVE (now viewing Equipment #EQ-002 detail instead of Fault)
- **Navigation:** Entity detail card updates (fault → equipment)
- **Actions:** Equipment actions now shown (not fault actions)

---

### Inter-Entity Navigation (ACTIVE → CANDIDATE)
**Example:** Sarah views Fault #F-456, clicks back button
- **Situation:** ACTIVE → CANDIDATE
- **Frontend:** Returns to search results list (3 faults)
- **User can:** Click another fault, refine search, etc.

---

### Deep Link Navigation (IDLE → ACTIVE)
**Example:** Sarah receives push notification "Fault #F-999 assigned to you", clicks notification
- **Situation:** IDLE → ACTIVE (skips CANDIDATE)
- **Frontend:** Directly opens Fault #F-999 detail card
- **Actions:** Fault actions shown immediately

---

## SITUATIONS IN RESUMABLE WORKFLOWS

### Receiving Session Example

**Day 1:**
1. Mike starts "Receive Items" for PO #P-123 (10 parts)
2. Mike checks in 6 parts, gets interrupted by emergency
3. Mike navigates away (situation persists in backend)

**Day 2:**
4. Mike logs in, sees banner "You have an active receiving session (6/10 items). [Resume] [Cancel]"
5. Mike clicks [Resume]
   - **Situation:** IDLE → ACTIVE (receiving session)
   - **Frontend:** Renders receiving session card with 6/10 items checked
6. Mike checks in remaining 4 items
7. Mike clicks [Commit Session] (signature required)
   - **Situation:** COMMIT → COOLDOWN → IDLE
   - **Backend:** Updates inventory, marks PO status='received'
   - **Frontend:** Shows success toast, dismisses receiving session

---

## KEY TAKEAWAYS

1. **Situations are UI modes, NOT operational contexts**
2. **User actions drive situation transitions (search, click, confirm)**
3. **Situations are orthogonal to permissions and entity state**
4. **RAG can suggest but NEVER auto-transition situations**
5. **Most situations are transient (lost on refresh)**
6. **Some situations are resumable (receiving, checklists)**
7. **State machine is predictable: IDLE → CANDIDATE → ACTIVE → COMMIT → COOLDOWN → ACTIVE**

---

**Status:** Situations clarified. Frontend active states defined. Ready for UI implementation.
