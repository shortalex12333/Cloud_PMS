# Verification Methodology

**How to verify 64 actions without getting overwhelmed**

**Purpose:** Step-by-step methodology to prevent AI overwhelm, avoid hallucination, and find patterns before fixing in bulk
**Audience:** AI agents, engineers verifying actions
**Reading time:** 10 minutes
**Critical:** Follow this EXACTLY to avoid "whack-a-mole" bug fixes

---

## 🎯 The Core Problem

**What we experienced:**
- AI gets overwhelmed trying to verify everything at once
- AI "lies" (hallucinates) about what it tested
- AI doesn't understand how to properly test
- AI tries to fix bugs as it finds them → whack-a-mole
- No pattern detection → same bug fixed 20 times individually

**Why this happened:**
- No scope boundaries (AI tries to verify "everything")
- No clear success criteria (AI guesses what "done" means)
- No forced focus (AI jumps between actions)
- Immediate fixing (no pattern analysis)

---

## 🚫 The Golden Rules

### Rule 1: ONE ACTION AT A TIME
**Never work on 2 actions simultaneously.**

If you're verifying `create_work_order`, you ONLY care about `create_work_order`. Ignore:
- Other actions in the same file
- Related actions
- "Similar" bugs in other actions
- "Quick fixes" you notice elsewhere

### Rule 2: OBSERVE FIRST, FIX LATER
**Document what you find. Do NOT fix it.**

If you find audit log missing:
- ✅ Write: "Action X - Audit log missing"
- ❌ Fix handler code immediately

We'll fix in bulk after finding patterns.

### Rule 3: HTTP 200 ≠ SUCCESS
**Always verify the 6 proofs.**

Don't trust the handler. Verify:
1. HTTP 200 returned
2. Response contains entity ID
3. Database row exists
4. Database row has correct values
5. Audit log entry exists
6. Audit log entry has correct values

### Rule 4: USE THE CHECKLIST
**Don't work from memory.**

Every action verification MUST:
- Copy ACTION_VERIFICATION_TEMPLATE.md
- Fill in ALL sections
- Check off ALL items
- Document findings

No shortcuts.

---

## 📋 Three-Phase Approach

### Phase 1: Quick Survey (5 Actions)
**Goal:** Find common patterns quickly

**Time:** 1 hour per action, 5 hours total
**Actions to verify:** Pick 5 representative actions from different categories

**Suggested 5:**
1. `create_work_order` (create entity)
2. `assign_work_order` (update relationship)
3. `add_note` (simple create)
4. `mark_fault_resolved` (status update)
5. `get_work_order_details` (read-only)

**Process for EACH action:**
```
1. Copy template (1 min)
2. Find handler in p0_actions_routes.py (2 min)
3. Identify table used (2 min)
4. Query BEFORE state (5 min)
5. Execute action via test (10 min)
6. Query AFTER state (5 min)
7. Check audit log (5 min)
8. Test 400/404 errors (10 min)
9. Document findings (20 min)
```

**What to record:**
- ✅ Works perfectly (all 6 proofs pass)
- ⚠️ HTTP 200 but missing audit log
- ⚠️ HTTP 200 but wrong data in database
- ⚠️ 400/404 not tested
- ⚠️ RLS not verified
- ❌ Handler crashes (500 error)

**Output:** `_VERIFICATION/PHASE_1_FINDINGS.md`

**Example findings:**
```markdown
## Phase 1 Findings (5 actions verified)

### Patterns Found:
1. **Audit log gap (4/5 actions):**
   - create_work_order - No audit log
   - assign_work_order - No audit log
   - mark_fault_resolved - No audit log
   - get_work_order_details - No audit log (expected for read-only)
   - add_note - HAS audit log ✅

2. **Missing 400 validation (3/5 actions):**
   - create_work_order - No validation for empty title
   - assign_work_order - No validation for invalid user_id
   - add_note - Has validation ✅

3. **RLS not tested (5/5 actions):**
   - None verified cross-yacht isolation

### Individual Findings:
- create_work_order: Works but no audit, no validation
- assign_work_order: Works but no audit, no validation
- add_note: Works perfectly (has audit + validation)
- mark_fault_resolved: Works but no audit
- get_work_order_details: Works but RLS untested
```

---

### Phase 2: Pattern Analysis (1 Hour)
**Goal:** Identify which bugs are widespread vs isolated

**Don't fix anything yet. Just categorize.**

**Create:** `_VERIFICATION/PATTERN_ANALYSIS.md`

**Template:**
```markdown
# Pattern Analysis

## Pattern 1: Missing Audit Logs
**Severity:** HIGH (compliance requirement)
**Scope:** 4/5 actions (80%)
**Affected actions:**
- create_work_order
- assign_work_order
- mark_fault_resolved
- get_work_order_details (expected for read-only)

**Root cause hypothesis:**
- Audit logging not enforced in handler pattern
- No automated test for audit log presence

**Fix approach:**
- Add audit logging to ALL mutation actions (not read-only)
- Create test helper: `verifyAuditLog(action, entity_id)`
- Estimate: 30 actions need audit logging added

---

## Pattern 2: Missing Input Validation
**Severity:** MEDIUM
**Scope:** 3/5 actions (60%)
**Affected actions:**
- create_work_order
- assign_work_order

**Root cause hypothesis:**
- No validation layer before handler logic
- Relying on database constraints (too late)

**Fix approach:**
- Add Pydantic models for all action payloads
- Validate before executing handler logic
- Estimate: 40 actions need validation models

---

## Pattern 3: RLS Untested
**Severity:** HIGH (security requirement)
**Scope:** 5/5 actions (100%)
**Affected actions:** ALL

**Root cause hypothesis:**
- No test pattern for cross-yacht isolation
- Tests only use single yacht_id

**Fix approach:**
- Add RLS test to template
- Create test helper: `verifyRLS(action, entity_id, wrong_yacht_id)`
- Estimate: All 64 actions need RLS tests
```

**Analysis questions:**
1. Which patterns affect the most actions?
2. Which patterns are highest severity?
3. Can we fix patterns in bulk or need individual fixes?
4. Are there systemic issues (missing layer, no enforcement)?

---

### Phase 3: Bulk Fixes (Varies)
**Goal:** Fix patterns, not individual bugs

**Process:**

**For each pattern:**

1. **Design the fix ONCE**
   - Example: "Add audit logging to all mutation handlers"
   - Create helper function: `write_audit_log(action, entity_id, yacht_id, user_id, changes)`

2. **Apply to ALL affected actions**
   - Don't fix 1 action at a time
   - Fix all 30 actions that need audit logging in one pass
   - Use search/replace where possible

3. **Test the pattern fix**
   - Create test helper that verifies pattern
   - Run on all affected actions
   - Example: `verifyAuditLog()` test helper

4. **Document the fix**
   - Update: `_VERIFICATION/PATTERN_FIXES.md`
   - Record: Which pattern, how many actions fixed, test results

**Example pattern fix:**

**Pattern:** Missing audit logs (30 actions)

**Fix approach:**
```python
# Create audit helper (apps/api/utils/audit.py)
async def write_audit_log(
    supabase_client,
    action: str,
    entity_id: str,
    entity_type: str,
    yacht_id: str,
    user_id: str,
    changes: dict
):
    """Write audit log entry for any action"""
    await supabase_client.table('pms_audit_log').insert({
        'action': action,
        'entity_id': entity_id,
        'entity_type': entity_type,
        'yacht_id': yacht_id,
        'user_id': user_id,
        'changes': changes,
        'created_at': datetime.now().isoformat()
    }).execute()

# Add to every mutation handler
if action == "create_work_order":
    # ... existing logic ...

    # NEW: Add audit logging
    await write_audit_log(
        tenant_supabase,
        action="create_work_order",
        entity_id=result['id'],
        entity_type="work_order",
        yacht_id=yacht_id,
        user_id=user_id,
        changes={'status': 'created', 'title': payload['title']}
    )
```

**Test pattern fix:**
```typescript
// Add to test helper
async function verifyAuditLog(action: string, entity_id: string) {
    const { data: audit } = await supabase
        .from('pms_audit_log')
        .select('*')
        .eq('action', action)
        .eq('entity_id', entity_id)
        .single();

    expect(audit).toBeTruthy();
    expect(audit.action).toBe(action);
    expect(audit.entity_id).toBe(entity_id);
}

// Use in all mutation tests
test('create_work_order mutation proof', async () => {
    // ... existing test ...
    await verifyAuditLog('create_work_order', response.entity_id);
});
```

**Result:**
- 30 actions fixed in bulk
- 1 test helper added
- All future actions will use helper (enforced pattern)

---

## 🔬 Single-Action Verification Protocol

**When verifying ONE action in detail:**

### Step 1: Setup (5 minutes)
```bash
# Copy template
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_[action_name].md

# Find handler
grep -n 'action == "[action_name]"' apps/api/routes/p0_actions_routes.py

# Note line number, open file
```

### Step 2: Read Handler Code (10 minutes)
**ONLY read the handler for this action. Ignore everything else.**

**Extract:**
1. Which table(s) does it use?
2. What validations exist?
3. Does it write audit log?
4. What does it return?

**Document in template:**
```markdown
## Handler Analysis

**File:** apps/api/routes/p0_actions_routes.py
**Line:** 1847-1923
**Tables used:** pms_work_orders
**Validations:** None (relies on DB constraints)
**Audit logging:** NO
**Returns:** {status: 'success', entity_id: ...}
```

### Step 3: Database Schema Check (5 minutes)
**Read DATABASE_RELATIONSHIPS.md for this table ONLY.**

**Verify:**
1. Table name correct?
2. Required columns exist?
3. RLS policy exists?
4. Soft delete policy exists?

**Document findings:**
```markdown
## Database Schema

**Table:** pms_work_orders ✅ (correct name)
**Required columns:** id, yacht_id, title, status, created_at, deleted_at ✅
**RLS policy:** YES - filters by yacht_id ✅
**Soft delete:** YES - deleted_at IS NULL ✅
```

### Step 4: Query BEFORE State (5 minutes)
```javascript
// Query database before executing action
const { data: before } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('yacht_id', TEST_YACHT_ID)
    .eq('title', 'Test Work Order');

console.log('BEFORE:', before.length); // Should be 0
```

### Step 5: Execute Action (10 minutes)
```typescript
// Execute via test
const response = await executeAction('create_work_order', context, {
    title: 'Test Work Order',
    description: 'Test description',
    priority: 'medium'
});

console.log('Response:', response);
// Expected: {status: 'success', entity_id: '...'}
```

### Step 6: Query AFTER State (5 minutes)
```javascript
// Query database after executing action
const { data: after } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('id', response.entity_id)
    .single();

console.log('AFTER:', after);
// Verify: title, description, priority match
```

### Step 7: Check Audit Log (5 minutes)
```javascript
// Query audit log
const { data: audit } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('action', 'create_work_order')
    .eq('entity_id', response.entity_id);

console.log('AUDIT:', audit);
// Expected: 1 entry with correct values
// Reality: May be 0 (missing audit log)
```

### Step 8: Test Error Cases (10 minutes)
```typescript
// Test 400 - Invalid input
const response400 = await executeAction('create_work_order', context, {});
expect(response400.status).toBe('error');
expect(response400.error_code).toBe('VALIDATION_ERROR');

// Test 404 - Entity not found (if applicable)
// Test 403 - Wrong yacht (RLS)
```

### Step 9: Document Findings (10 minutes)
**Fill in template completely:**

```markdown
## Verification Results

### ✅ Success Cases
- [x] HTTP 200 returned
- [x] Response contains entity_id
- [x] Database row created
- [x] Database row has correct values
- [ ] Audit log entry created ❌
- [ ] Audit log entry has correct values ❌

### ❌ Failure Cases
- [ ] 400 for invalid input ❌ (no validation)
- [ ] 404 for invalid entity (N/A)
- [ ] 403 for wrong yacht ⚠️ (not tested)

## Gaps Found
1. **Missing audit log** - No entry in pms_audit_log
2. **No input validation** - Empty payload accepted
3. **RLS not verified** - Cross-yacht test not run

## Recommendation
- Add audit logging to handler
- Add Pydantic validation model
- Add RLS test to test suite
```

### Step 10: Mark DONE (1 minute)
**Update tracker:**
```markdown
# _VERIFICATION/MUTATION_PROOFS.md

## Progress: 2/64 actions verified

- [x] create_work_order (2026-01-22) - Gaps: audit, validation
- [x] add_note (2026-01-22) - Perfect ✅
- [ ] assign_work_order
...
```

**STOP. Move to next action.**

---

## 🚨 How to Avoid Overwhelm

### Symptom: "I don't know where to start"
**Fix:** Use this exact checklist:
1. Pick ONE action from microaction_registry.ts
2. Copy template
3. Follow 10-step protocol above
4. Mark done
5. Pick next action

### Symptom: "I keep finding related issues"
**Fix:** Write them down, don't fix them.
- Create: `_VERIFICATION/RELATED_ISSUES.md`
- Document: "While verifying X, noticed Y is also broken"
- Continue with X only

### Symptom: "I want to fix this bug now"
**Fix:** NO. Document it.
- You're in **observation phase**, not **fixing phase**
- Phase 1 = Observe (5 actions)
- Phase 2 = Analyze patterns
- Phase 3 = Fix in bulk

### Symptom: "The test is failing, I need to investigate"
**Fix:** Time-box investigation to 15 minutes.
- If you can't identify cause in 15 min → document "Test failed, needs investigation"
- Move to next action
- Come back after pattern analysis

### Symptom: "I'm testing 5 things at once"
**Fix:** STOP. Close all files except:
1. The ONE action verification template you're filling in
2. The handler code for that action (p0_actions_routes.py)
3. The test file for that action

---

## ✅ Success Criteria

**You're doing this RIGHT when:**
1. You can verify 1 action in 1 hour (not 3 hours)
2. You fill in template completely (no skipped sections)
3. You document gaps without fixing them
4. You move to next action without "cleaning up"
5. After 5 actions, you have clear pattern analysis

**You're doing this WRONG when:**
1. You spend 3+ hours on 1 action
2. You jump between actions
3. You fix bugs as you find them
4. You skip template sections
5. You trust HTTP 200 without database verification

---

## 📊 Pattern Detection Examples

### Good Pattern Analysis
```markdown
## Pattern: Missing Audit Logs
- Affects: 4/5 actions (80%)
- Fix: Add audit helper, apply to all mutation actions
- Estimate: 2 hours to fix all 30 actions

## Pattern: No Input Validation
- Affects: 3/5 actions (60%)
- Fix: Create Pydantic models for all actions
- Estimate: 4 hours to add validation layer
```

### Bad Pattern Analysis
```markdown
## Issue: create_work_order missing audit
- Fix: Add audit log to create_work_order handler
```
This is NOT pattern analysis. This is fixing 1 bug individually.

---

## 🎯 Quick Reference

**Phase 1: Quick Survey**
- Verify 5 representative actions
- Document gaps (don't fix)
- Time: 5 hours (1 hour per action)

**Phase 2: Pattern Analysis**
- Categorize findings into patterns
- Prioritize by severity + scope
- Time: 1 hour

**Phase 3: Bulk Fixes**
- Fix patterns, not individual bugs
- Test pattern fix on all affected actions
- Time: Varies (2-8 hours per pattern)

**Single-Action Protocol:**
1. Copy template (1 min)
2. Read handler (10 min)
3. Check schema (5 min)
4. Query BEFORE (5 min)
5. Execute action (10 min)
6. Query AFTER (5 min)
7. Check audit (5 min)
8. Test errors (10 min)
9. Document (10 min)
10. Mark done (1 min)

**Total: 60 minutes per action**

---

## 📁 File Organization

```
_VERIFICATION/
├── PHASE_1_FINDINGS.md          ← Findings from first 5 actions
├── PATTERN_ANALYSIS.md          ← Pattern categorization
├── PATTERN_FIXES.md             ← Bulk fix documentation
├── RELATED_ISSUES.md            ← Side issues found (not fixing yet)
├── verify_create_work_order.md  ← Individual action verification
├── verify_add_note.md
└── ...
```

---

## 💡 Pro Tips

1. **Set a timer** - If you're over 1 hour on a single action, you're going too deep
2. **Use the template** - Don't work from memory, fill in ALL sections
3. **Document, don't fix** - Phase 1 is observation, not repair
4. **Trust the process** - Pattern analysis will reveal the right fix approach
5. **One action at a time** - Close all other files, focus on ONE
6. **Verify the 6 proofs** - HTTP 200 means nothing without database verification
7. **Time-box investigation** - 15 minutes max to debug a failure
8. **Move on** - Better to verify 5 actions partially than 1 action perfectly

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team

**This is the methodology to prevent AI overwhelm and find patterns before fixing in bulk.**
