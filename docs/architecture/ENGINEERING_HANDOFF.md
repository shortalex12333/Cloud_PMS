# ENGINEERING HANDOFF

**Date:** 2026-01-22
**Purpose:** Zero-ambiguity implementation guide for frontend + backend teams
**Status:** Execution Contract - Build exactly what's specified here

---

## PURPOSE

This document tells you **exactly what to build** for MVP. No interpretation needed. No architectural questions left open.

If something is not in this document, **do not build it for MVP.**

---

## FRONTEND IMPLEMENTATION CHECKLIST

### 1. Search Results Display

**MUST:**
- ✅ Show entity name + one-line summary
- ✅ Show status badge (e.g., "Critical", "Overdue", "Out of Stock")
- ✅ Make entire card clickable (navigates to entity detail)

**MUST NOT:**
- ❌ Show action buttons in search results
- ❌ Show editable fields in search results
- ❌ Auto-open entity detail (even at 100% confidence)
- ❌ Show "Quick actions" menu in results

**Reference:** ENTITY_ACTION_SURFACING.md, Rule 1

---

### 2. Entity Detail Layout (4 Segments)

**Every entity detail view MUST have exactly 4 segments:**

#### Segment 1: PRIMARY ACTIONS (2-3 visible buttons)
**Location:** Top of entity card, horizontal row (desktop) or vertical stack (mobile)

**Implementation:**
```tsx
// Example: Fault entity detail
<EntityCard>
  <EntityHeader name={fault.title} status={fault.status} />

  <PrimaryActions>
    <Button onClick={diagnoseFault}>Diagnose Fault</Button>
    <Button onClick={addFaultNote}>Add Note</Button>
    <Button onClick={addToHandover}>Add to Handover</Button>
  </PrimaryActions>

  {/* Rest of segments below */}
</EntityCard>
```

**Selection algorithm:**
1. Filter by user permission (role)
2. Filter by entity state (status)
3. Take top 2-3 from entity-specific primary list (see ENTITY_ACTION_SURFACING.md)

**DO NOT:**
- ❌ Show more than 3 primary buttons
- ❌ Show MUTATE_HIGH actions as primary
- ❌ Reorder actions based on RAG suggestions

---

#### Segment 2: MORE ▾ (secondary actions dropdown)
**Location:** Below primary actions

**Implementation:**
```tsx
<DropdownMenu label="More ▾">
  <DropdownItem onClick={addFaultPhoto}>Add Photo</DropdownItem>
  <DropdownItem onClick={showRelatedDocs}>Show Related Docs</DropdownItem>
  <DropdownItem onClick={showEquipmentHistory}>Equipment History</DropdownItem>
  <DropdownSeparator />
  <DropdownItem onClick={markFalseAlarm}>Mark False Alarm</DropdownItem>
</DropdownMenu>
```

**Rules:**
- Group mutations first, reads second
- Separator between groups
- Max 10 items (if more, create sub-menus)

---

#### Segment 3: EVIDENCE / RELATED (read-only links)
**Location:** Bottom section of entity card

**Implementation:**
```tsx
<RelatedSection heading="Related">
  <RelatedLink icon="equipment" href={`/equipment/${fault.equipment_id}`}>
    View Equipment (#EQ-002)
  </RelatedLink>
  <RelatedLink icon="book" href={`/manual/page/47`}>
    Manual Section (pg. 47)
  </RelatedLink>
  <RelatedLink icon="history" onClick={showSimilarFaults}>
    Similar Past Faults (3)
  </RelatedLink>
</RelatedSection>
```

**Rules:**
- Read-only links only (no mutations)
- Each link shows: icon, label, count/context
- Collapsible on mobile

---

#### Segment 4: SAFETY ACTIONS (signature required, irreversible)
**Location:** Dropdown or bottom sheet (mobile)

**Implementation:**
```tsx
<SafetyActionsDropdown label="⚠️ Safety Actions">
  <SafetyAction
    onClick={markWorkOrderComplete}
    warning="This action is irreversible and requires signature"
  >
    Mark Work Order Complete
  </SafetyAction>
</SafetyActionsDropdown>
```

**Rules:**
- Only show actions with `requires_signature: true`
- Show consequence warning
- Clicking opens signature flow

---

### 3. Situation State Machine

**Implement exactly this state machine:**

```tsx
enum Situation {
  IDLE = 'idle',
  CANDIDATE = 'candidate',
  ACTIVE = 'active',
  ACTION_PREVIEW = 'action_preview',
  COMMIT = 'commit',
  COOLDOWN = 'cooldown'
}

// State transitions
const transitions = {
  idle: ['candidate'], // user searches
  candidate: ['active', 'idle'], // user clicks entity or clears
  active: ['action_preview', 'candidate'], // user clicks action or back
  action_preview: ['commit', 'cooldown'], // user confirms or cancels
  commit: ['cooldown'], // backend responds
  cooldown: ['active', 'idle'] // timeout or dismiss
}
```

**MUST NOT:**
- ❌ Skip states (e.g., CANDIDATE → COMMIT directly)
- ❌ Auto-transition without user action
- ❌ Allow RAG to control state transitions

**Reference:** SITUATIONS_CLARIFICATION.md

---

### 4. RAG Suggestions (Assistive Only)

**When to show RAG suggestion:**
```tsx
{ragSuggestion && ragSuggestion.confidence > 0.7 && (
  <RagBanner
    backgroundColor="yellow"
    dismissible={true}
  >
    <Icon name="lightbulb" />
    <Text>Suggested: {ragSuggestion.action_label}</Text>
    <Text small>Based on: {ragSuggestion.evidence}</Text>
    <Button onClick={() => openAction(ragSuggestion.action_id)}>
      {ragSuggestion.action_label}
    </Button>
  </RagBanner>
)}
```

**MUST:**
- ✅ Show suggestion in yellow banner
- ✅ Include confidence + evidence source
- ✅ Make banner dismissible
- ✅ Require user click to activate action

**MUST NOT:**
- ❌ Auto-execute suggested action
- ❌ Auto-open action form
- ❌ Promote action to primary segment
- ❌ Override user-entered values with RAG prefill

---

### 5. Action Form Flow

**For all MUTATE actions:**

```tsx
// Step 1: Open form (ACTION_PREVIEW state)
<ActionForm>
  <FormFields>
    {/* Prefilled by RAG if available, user can edit */}
    <Input
      label="Symptom"
      value={ragPrefill?.symptom || ''}
      onChange={setSymptom}
    />
  </FormFields>

  {/* Show diff preview for MUTATE actions */}
  {diffPreview && (
    <DiffPreview>
      <BeforeAfter before={diffPreview.before} after={diffPreview.after} />
    </DiffPreview>
  )}

  <FormActions>
    <Button variant="secondary" onClick={cancel}>Cancel</Button>
    <Button variant="primary" onClick={confirm}>Confirm</Button>
  </FormActions>
</ActionForm>

// Step 2: User clicks Confirm → COMMIT state
<LoadingSpinner message="Executing action..." />

// Step 3: Backend responds → COOLDOWN state
<Toast variant={success ? 'success' : 'error'}>
  {message}
</Toast>
```

**Signature actions add signature step before COMMIT:**
```tsx
<SignatureModal onSign={handleSign} onCancel={cancel}>
  <Text>This action requires your signature</Text>
  <SignaturePad onSign={setSignature} />
  <Button onClick={confirmWithSignature}>Sign & Confirm</Button>
</SignatureModal>
```

---

### 6. Resumable Workflows (Receiving, Checklists)

**Show banner if resumable session exists:**
```tsx
{resumableSession && (
  <ResumableBanner>
    <Icon name="alert" />
    <Text>You have an active {resumableSession.type} ({resumableSession.progress})</Text>
    <Button onClick={resumeSession}>Resume</Button>
    <Button variant="secondary" onClick={cancelSession}>Cancel</Button>
  </ResumableBanner>
)}
```

**Session persists across page refresh** (stored in backend).

---

### 7. Action Visibility Rules

**State-based hiding (NOT greying):**
```tsx
// Example: start_work_order only shown when status='draft'
const primaryActions = useMemo(() => {
  const actions = [];

  // State filter
  if (workOrder.status === 'draft') {
    actions.push({ id: 'start_work_order', label: 'Start' });
  }
  if (workOrder.status === 'in_progress') {
    actions.push({ id: 'add_wo_hours', label: 'Log Hours' });
  }

  // Role filter
  if (user.role === 'chief_engineer' && workOrder.status === 'in_progress') {
    actions.push({ id: 'mark_complete', label: 'Mark Complete' });
  }

  return actions.slice(0, 3); // Max 3
}, [workOrder.status, user.role]);
```

**MUST NOT:**
- ❌ Grey out unavailable actions (hide them completely)
- ❌ Show tooltips explaining why action is hidden

---

### 8. Mobile-Specific Adjustments

**Primary actions:** Vertical stack (not horizontal)
**More ▾:** Full-screen menu (not dropdown)
**Safety actions:** Bottom sheet modal
**Evidence/Related:** Collapsible accordion

---

## BACKEND IMPLEMENTATION CHECKLIST

### 1. Handler Function Structure

**Every handler MUST follow this structure:**

```python
async def action_handler(
    entity_id: str,
    yacht_id: str,
    user_id: str,
    params: Optional[Dict] = None
) -> ActionResponseEnvelope:
    """
    Handler for [action_name].

    Reads: [list tables/columns]
    Writes: [list tables/columns]
    Ledger: [yes/no + event_type]
    Audit: [yes/no]
    Signature: [yes/no]
    """
    builder = ResponseBuilder(action_id, entity_id, entity_type, yacht_id)

    try:
        # 1. Permission check
        if not has_permission(user_id, yacht_id, required_role):
            builder.set_error("FORBIDDEN", "Insufficient permissions")
            return builder.build()

        # 2. State validation
        entity = get_entity(entity_id, yacht_id)
        if entity.status not in allowed_statuses:
            builder.set_error("INVALID_STATE", f"Cannot execute in state: {entity.status}")
            return builder.build()

        # 3. Business logic
        result = execute_action(entity, params)

        # 4. Database writes (in transaction)
        with db.transaction():
            update_entity(entity_id, result)

            # Ledger event (if specified in ACTION_IO_MATRIX)
            write_ledger_event(
                event_type='action_executed',
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                data=result
            )

            # Audit log (if MUTATE action)
            write_audit_log(
                action=action_id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                old_values=entity.to_dict(),
                new_values=result,
                signature=params.get('signature') if requires_signature else None
            )

        # 5. Return response
        builder.set_data(result)
        return builder.build()

    except Exception as e:
        logger.error(f"{action_id} failed: {e}", exc_info=True)
        builder.set_error("INTERNAL_ERROR", str(e))
        return builder.build()
```

**MUST:**
- ✅ Check permissions before execution
- ✅ Validate entity state
- ✅ Use database transaction for writes
- ✅ Write ledger event if specified in ACTION_IO_MATRIX
- ✅ Write audit log for all MUTATE actions
- ✅ Return standardized ActionResponseEnvelope

**MUST NOT:**
- ❌ Execute without permission check
- ❌ Skip audit log for mutations
- ❌ Commit outside transaction
- ❌ Return raw database results (use ResponseBuilder)

---

### 2. Ledger Event Pattern

**When to write ledger event:**
Check ACTION_IO_MATRIX for each action. If "Ledger Event: Yes", write event.

```python
def write_ledger_event(
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    data: Dict,
    yacht_id: str
):
    """Write to ledger for audit trail."""
    db.table('ledger_events').insert({
        'id': uuid4(),
        'yacht_id': yacht_id,
        'event_type': event_type,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'user_id': user_id,
        'event_data': data,
        'created_at': datetime.now(timezone.utc)
    }).execute()
```

**Event types:**
- `fault_created`, `fault_diagnosed`, `fault_resolved`
- `work_order_created`, `work_order_started`, `work_order_completed`
- `inventory_adjusted`, `part_used`, `part_restocked`
- `purchase_order_approved`, `receiving_session_committed`

---

### 3. Audit Log Pattern

**EVERY MUTATE action MUST write to audit log:**

```python
def write_audit_log(
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    old_values: Dict,
    new_values: Dict,
    signature: Optional[Dict],
    yacht_id: str
):
    """Write to pms_audit_log (NON-NEGOTIABLE)."""
    db.table('pms_audit_log').insert({
        'id': uuid4(),
        'yacht_id': yacht_id,
        'action': action,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'user_id': user_id,
        'old_values': old_values,
        'new_values': new_values,
        'signature': signature or {},
        'created_at': datetime.now(timezone.utc)
    }).execute()
```

**MUST include:**
- ✅ Before state (old_values)
- ✅ After state (new_values)
- ✅ User ID
- ✅ Signature data (if action requires signature)

---

### 4. Signature Verification Pattern

**For actions with `requires_signature: true`:**

```python
def verify_signature(
    user_id: str,
    action_id: str,
    params: Dict
) -> bool:
    """
    Verify digital signature.

    MVP: Accept any signature (tap accept)
    Post-MVP: Verify PIN/biometric
    """
    signature = params.get('signature')
    if not signature:
        return False

    # MVP: Just check signature exists
    if 'user_id' in signature and 'timestamp' in signature:
        return True

    # Post-MVP: Add PIN/biometric verification here

    return False
```

**MVP implementation:**
- ✅ Accept signature if present (user_id + timestamp)
- ✅ Store signature in audit log
- ❌ Do NOT validate PIN/biometric (MVP ships with tap accept)

---

### 5. RLS Enforcement

**EVERY query MUST enforce yacht isolation:**

```python
# Correct: RLS enforced
result = db.table('pms_faults').select('*').eq('yacht_id', yacht_id).eq('id', entity_id).execute()

# WRONG: Missing yacht_id filter
result = db.table('pms_faults').select('*').eq('id', entity_id).execute()
```

**RLS check pattern:**
```python
def enforce_rls(yacht_id: str, user_id: str):
    """Verify user has access to yacht."""
    user = db.table('user_accounts').select('yacht_id').eq('id', user_id).single().execute()
    if user.data['yacht_id'] != yacht_id:
        raise PermissionError(f"User {user_id} cannot access yacht {yacht_id}")
```

---

### 6. Prefill vs Preview vs Execute

**Many MUTATE actions have 3 steps:**

```python
# Step 1: Prefill (RAG suggestions)
async def add_fault_note_prefill(entity_id: str, yacht_id: str, user_id: str):
    """Return RAG-suggested note text (user can edit)."""
    fault = get_fault(entity_id)
    rag_suggestions = get_rag_context(fault)

    return {
        'prefilled_values': {
            'note_text': rag_suggestions.get('suggested_note', ''),
            'note_type': 'diagnosis'
        },
        'evidence': rag_suggestions.get('evidence_links', [])
    }

# Step 2: Preview (show diff before commit)
async def add_fault_note_preview(entity_id: str, yacht_id: str, params: Dict):
    """Return before/after preview (no writes)."""
    fault = get_fault(entity_id)

    return {
        'before': {
            'notes_count': len(fault.notes)
        },
        'after': {
            'notes_count': len(fault.notes) + 1,
            'new_note': params['note_text']
        }
    }

# Step 3: Execute (actual mutation)
async def add_fault_note_execute(entity_id: str, yacht_id: str, user_id: str, params: Dict):
    """Write note to database."""
    with db.transaction():
        # Write to metadata.notes array
        db.table('pms_faults').update({
            'metadata': db.func.jsonb_set(
                'metadata',
                ['notes'],
                db.func.jsonb_insert('metadata->>notes', -1, {
                    'note_text': params['note_text'],
                    'created_by': user_id,
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
            ),
            'updated_at': datetime.now(timezone.utc),
            'updated_by': user_id
        }).eq('id', entity_id).execute()

        # Audit log
        write_audit_log(...)

    return {'success': True}
```

**Not all actions have prefill/preview** - check ACTION_IO_MATRIX.

---

### 7. Error Handling

**Return structured errors:**

```python
class ActionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

# Error codes
ERROR_CODES = {
    'NOT_FOUND': 'Entity not found',
    'FORBIDDEN': 'Insufficient permissions',
    'INVALID_STATE': 'Action not allowed in current state',
    'VALIDATION_ERROR': 'Invalid input parameters',
    'INTERNAL_ERROR': 'Server error'
}

# Usage
if not entity:
    raise ActionError('NOT_FOUND', f"Fault {entity_id} not found")
```

---

## EXPLICIT "DO NOT" LIST

### Frontend

❌ **DO NOT** show action buttons in search results
❌ **DO NOT** auto-open entity detail (even at 100% confidence)
❌ **DO NOT** let RAG auto-execute actions
❌ **DO NOT** override user input with RAG prefill
❌ **DO NOT** show more than 3 primary actions
❌ **DO NOT** grey out unavailable actions (hide them)
❌ **DO NOT** reorder actions based on RAG confidence
❌ **DO NOT** skip situation states (follow state machine exactly)
❌ **DO NOT** create new action segments beyond the 4 defined
❌ **DO NOT** show tooltips explaining hidden actions

### Backend

❌ **DO NOT** execute actions without permission check
❌ **DO NOT** skip audit log for MUTATE actions
❌ **DO NOT** commit database writes outside transaction
❌ **DO NOT** query without yacht_id filter (RLS enforcement)
❌ **DO NOT** return raw database results (use ResponseBuilder)
❌ **DO NOT** auto-create entities without user confirmation
❌ **DO NOT** infer user intent (no "smart" auto-actions)
❌ **DO NOT** validate PIN/biometric for MVP (tap accept only)
❌ **DO NOT** create new tables beyond SCHEMA_GAPS_MIGRATIONS.md
❌ **DO NOT** add columns without migration spec

---

## MVP SCOPE VS POST-MVP SCOPE

### MVP (Ship First)

**Frontend:**
- ✅ 4-segment action layout (all 10 entity types)
- ✅ Situation state machine (IDLE → CANDIDATE → ACTIVE → COMMIT → COOLDOWN)
- ✅ RAG suggestions (yellow banner, dismissible, never auto-execute)
- ✅ Action forms (prefill, preview, confirm)
- ✅ Signature flow (tap accept, store signature)
- ✅ Resumable workflows (receiving, checklists)

**Backend:**
- ✅ ~45-50 canonical actions (see MVP_EXECUTION_SLICE.md)
- ✅ Permission checks (role-based)
- ✅ State validation (status-based action filtering)
- ✅ Ledger events (for all specified actions)
- ✅ Audit log (for all MUTATE actions)
- ✅ RLS enforcement (yacht isolation)
- ✅ P0 schema migrations (shopping_list, purchase_order_items, PO tracking columns)

**Signature:**
- ✅ Tap accept (no PIN/biometric)
- ✅ Store signature in audit log (user_id + timestamp)

---

### Post-MVP (After Launch)

**Frontend:**
- 📋 PIN/biometric signature verification
- 📋 Offline mode
- 📋 Push notifications for resumable workflows
- 📋 Advanced RAG features (multi-step reasoning)
- 📋 Bulk actions

**Backend:**
- 📋 Remaining actions (~20-30 future actions)
- 📋 P1/P2 schema migrations (documents, time tracking)
- 📋 Predictive alerts
- 📋 Fleet-wide reporting
- 📋 Third-party integrations

**Signature:**
- 📋 PIN verification
- 📋 Biometric (fingerprint/face)
- 📋 Multi-party signatures

---

## TESTING REQUIREMENTS

### Frontend Tests

**Action surfacing:**
- ✅ Search results show zero actions
- ✅ Entity detail shows max 3 primary actions
- ✅ Actions filtered by role + state
- ✅ RAG suggestions never auto-execute

**Situation transitions:**
- ✅ State machine follows defined transitions
- ✅ No skipped states
- ✅ Resumable workflows persist across refresh

**Visual regression:**
- ✅ All 10 entity types conform to 4-segment layout
- ✅ Mobile layout matches spec

---

### Backend Tests

**Handler execution:**
- ✅ Permission check enforced
- ✅ State validation works
- ✅ Audit log written for all MUTATE actions
- ✅ Ledger event written when specified
- ✅ RLS enforced (yacht isolation)

**Data integrity:**
- ✅ Transaction rollback on error
- ✅ Signature stored in audit log
- ✅ Before/after diff accurate

---

## DEFINITION OF DONE

### Frontend
- [ ] All 10 entity types implemented with 4-segment layout
- [ ] Situation state machine implemented
- [ ] RAG suggestions shown but never auto-execute
- [ ] Action forms show prefill, preview, confirm
- [ ] Signature flow implemented (tap accept)
- [ ] Resumable workflows functional
- [ ] Visual regression tests pass

### Backend
- [ ] MVP action handlers implemented (45-50 actions)
- [ ] Permission checks enforced
- [ ] Audit log written for all MUTATE actions
- [ ] Ledger events written as specified
- [ ] RLS enforced on all queries
- [ ] P0 schema migrations deployed
- [ ] Integration tests pass

---

**Start building. No more questions.**
