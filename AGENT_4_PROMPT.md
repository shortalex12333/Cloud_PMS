# Agent 4: Bulk Fixer - Enhanced Prompt

**Copy this ENTIRE prompt when launching Agent 4**

---

You are Agent 4: Bulk Fixer.

Working directory: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS`

## 🎯 YOUR JOB (TWO PHASES)

**PHASE 1:** Fix patterns in bulk (HIGH → MEDIUM → LOW)
**PHASE 2:** Verify all 64 actions

## 📚 READ THESE FILES FIRST (IN ORDER)

1. `AGENT_3_HANDOFF.md` (from Agent 3)
2. `AGENT_COMMUNICATION_PROTOCOL.md` (defines how you communicate)
3. `_VERIFICATION/PATTERN_ANALYSIS.md`
4. `MULTI_AGENT_VERIFICATION_PLAN.md` (Agent 4 section only)

---

## 🔧 PHASE 1: FIX PATTERNS IN BULK

### Workflow for EACH Pattern (Priority Order)

#### Step 1: Read Pattern Details

From `PATTERN_ANALYSIS.md`, extract:
- Pattern name
- Severity
- Scope (N/5 from sample, projected N/64 total)
- Root cause
- Fix approach
- Estimated effort

#### Step 2: Update Status

```bash
cat > .agent_status.json << EOF
{
  "agent": "Agent 4",
  "status": "in_progress",
  "phase": "fixing_patterns",
  "current_pattern": "[PATTERN_NAME]",
  "patterns_fixed": [N],
  "patterns_total": [TOTAL],
  "time_elapsed_minutes": [MINUTES],
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

#### Step 3: Design Solution ONCE

Example: Missing Audit Logs
```python
# Create helper: apps/api/utils/audit.py
async def write_audit_log(client, action, entity_id, yacht_id, user_id, changes):
    await client.table('pms_audit_log').insert({
        'action': action,
        'entity_id': entity_id,
        'yacht_id': yacht_id,
        'user_id': user_id,
        'changes': changes
    }).execute()
```

#### Step 4: Apply to ALL Affected Actions

```bash
# Find all affected handlers
grep -n 'if action ==' apps/api/routes/p0_actions_routes.py | grep -E '(create|update|delete)'

# Add audit call to each handler
# (Manual editing or sed for pattern replacement)
```

#### Step 5: Create Test Helper

```typescript
// tests/helpers/audit.ts
export async function verifyAuditLog(action, entity_id) {
  const { data } = await supabase.from('pms_audit_log')...
  expect(data).toBeTruthy();
}
```

#### Step 6: Add to All Tests

```typescript
// Add to each mutation test
await verifyAuditLog('create_work_order', response.entity_id);
```

#### Step 7: Test Pattern Fix

```bash
# Run all affected tests
npx playwright test tests/e2e/mutation_proof_*.spec.ts

# Document results
```

#### Step 8: Document in PATTERN_FIXES.md

```markdown
### Fix H1: Missing Audit Logs

**Pattern:** Missing audit logs (30 actions affected)
**Time spent:** [HOURS]

**Implementation:**
1. Created apps/api/utils/audit.py ✅
2. Added to 30 handlers ✅
3. Created tests/helpers/audit.ts ✅
4. Updated 30 tests ✅

**Test Results:**
- Pass rate: [N]/30 ([XX]%)
- Failures: [LIST if any]

**Status:** ✅ Complete / ⚠️ Partial
```

#### Step 9: Output Pattern Completion Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PATTERN FIXED: [PATTERN_NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 4 (Bulk Fixer)
Phase: Pattern Fixes
Pattern: [N] of [TOTAL]
Time: [HH:MM] elapsed

Pattern Details:
- Name: [PATTERN_NAME]
- Severity: HIGH/MEDIUM/LOW
- Actions affected: [N]

Implementation:
✅ Helper created: [FILE]
✅ Applied to [N] handlers
✅ Test helper created: [FILE]
✅ Updated [N] tests

Test Results:
- Tests run: [N]
- Tests passed: [N]
- Tests failed: [N]
- Pass rate: [XX]%

Status: ✅ Pattern fixed / ⚠️ Partial success

Next: [NEXT_PATTERN] or Phase 2 (verification)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Step 10: Move to Next Pattern

Repeat steps 1-9 for each pattern in priority order.

---

### ⏸️ PAUSE POINT: After All Patterns Fixed

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PHASE 1 COMPLETE: All Patterns Fixed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 4 (Bulk Fixer)
Phase: Pattern fixes complete
Time: [HH:MM] total

Summary:
- Patterns fixed: [N]
- HIGH severity: [N] fixed
- MEDIUM severity: [N] fixed
- LOW severity: [N] fixed / deferred

Overall test pass rate: [XX]%

Files created:
✅ apps/api/utils/audit.py (helper)
✅ tests/helpers/audit.ts (test helper)
✅ _VERIFICATION/PATTERN_FIXES.md (documentation)

Next: Phase 2 (verify remaining 59 actions)

⏸️  PAUSE - Waiting for user confirmation to proceed to Phase 2...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Ask:**
```
Phase 1 complete. All patterns fixed. Review PATTERN_FIXES.md.

Should I proceed to Phase 2 (verify remaining 59 actions)?

Type 'yes' to continue or provide feedback.
```

**Wait for user response.**

---

## ✅ PHASE 2: VERIFY REMAINING 59 ACTIONS

### After User Confirms Phase 2

**Actions already verified:** 5 (by Agent 2)
**Actions remaining:** 59

**Action list:** Read from `tests/fixtures/microaction_registry.ts` (64 total, skip 5 already done)

### Workflow for EACH Action

Similar to Agent 2, but faster (patterns already fixed):

1. **Update status:**
```bash
cat > .agent_status.json << EOF
{
  "agent": "Agent 4",
  "status": "in_progress",
  "phase": "verifying_actions",
  "current_action": "[ACTION_NAME]",
  "actions_verified": [N],
  "actions_total": 64,
  "time_elapsed_minutes": [MINUTES],
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

2. **Run verification:**
```bash
./scripts/verify.sh [action_name]
```

3. **Fill template (lighter verification since patterns fixed):**
   - 6 proofs (should all pass now)
   - Error cases (should be fixed)
   - Gaps (should be minimal)

4. **Run next action:**
```bash
./scripts/next_action.sh
```

5. **Every 10 actions, output progress report:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PROGRESS: [N]/64 Actions Verified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 4 (Bulk Fixer)
Phase: Verification
Progress: [N]/64 ([XX]%)
Time: [HH:MM] elapsed

Recent actions verified:
- Action [N-9]: [NAME] ✅
- Action [N-8]: [NAME] ✅
...
- Action [N]: [NAME] ✅

Pass rate: [N]/[N] ([XX]%)
Failures: [N] (see PATTERN_FIXES.md)

ETA: [HOURS] remaining

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### ⏸️ FINAL PAUSE: After All 64 Actions Verified

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PHASE 2 COMPLETE: All 64 Actions Verified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 4 (Bulk Fixer)
Phase: Verification complete
Time: [HH:MM] total (Phase 1 + Phase 2)

Summary:
- Total actions: 64
- Actions verified: 64
- Actions passed: [N]
- Actions partial: [N]
- Actions failed: [N]
- Pass rate: [XX]%

Files created:
- 59 new verification files (_VERIFICATION/verify_*.md)
- PATTERN_FIXES.md (complete)
- MUTATION_PROOFS.md (updated to 64/64)

Ready to create final report.

⏸️  PAUSE - Waiting for user confirmation to create VERIFICATION_COMPLETE.md...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Ask:**
```
All 64 actions verified. Review progress.

Should I create VERIFICATION_COMPLETE.md and mark system complete?

Type 'yes' to finalize or provide feedback.
```

**Wait for user response.**

---

## ✅ AFTER FINAL USER CONFIRMATION

1. **Update final status:**
```bash
cat > .agent_status.json << EOF
{
  "agent": "Agent 4",
  "status": "complete",
  "phase": "complete",
  "actions_verified": 64,
  "actions_total": 64,
  "patterns_fixed": [N],
  "time_elapsed_minutes": [TOTAL],
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "verification_complete": true
}
EOF
```

2. **Update context:**
```bash
cat > .verification_context << EOF
{
  "phase": "3_COMPLETE",
  "actions_verified": 64,
  "patterns_fixed": [N],
  "system_status": "complete"
}
EOF
```

3. **Output final completion report:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅✅✅ VERIFICATION SYSTEM COMPLETE ✅✅✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 4 (Bulk Fixer)
Status: COMPLETE
Total time: [DAYS] days

PHASE 1: Pattern Fixes
- Patterns fixed: [N]
- Time: [HH:MM]
- Status: ✅ Complete

PHASE 2: Action Verification
- Actions verified: 64/64
- Pass rate: [XX]%
- Time: [HH:MM]

OVERALL RESULTS:
✅ All 64 actions verified
✅ All patterns fixed
✅ Test suite passing ([XX]%)
✅ System compliant with standards

Files created:
✅ 59 verification files
✅ PATTERN_FIXES.md
✅ MUTATION_PROOFS.md (64/64)
✅ VERIFICATION_COMPLETE.md

System ready for production.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

4. **Create `VERIFICATION_COMPLETE.md`:**

Document:
- Complete summary of all 4 agents
- Pattern fixes implemented
- All 64 actions verified
- Test pass rate
- Known issues (if any)
- Recommendations
- System status: READY

5. **STOP**

---

## 🚨 BLOCKER PROTOCOL

**If stuck for >15 minutes:**

```
🚨 BLOCKER ESCALATION 🚨

Agent: Agent 4
Phase: [PHASE]
Task: [CURRENT_TASK]
Time stuck: [MINUTES]

Problem:
[DESCRIPTION]

What I tried:
1. [ATTEMPT 1]
2. [ATTEMPT 2]

Recommendation: [SUGGESTION]

Auto-resolving in 5 minutes if no response...
```

**Auto-resolve:**
- Document issue in PATTERN_FIXES.md
- Continue to next pattern/action
- Flag for manual review

---

## ⏱️ TIME ESTIMATE

**Phase 1 (Pattern fixes):** Varies by patterns (est. 6-12 hours)
**Phase 2 (Verify 59 actions):** ~8 hours (using automation)
**Total:** 2-3 days

**Checkpoints:**
- After each pattern fixed (~every 2-4 hours)
- Every 10 actions verified (~every hour)
- Before Phase 2 (PAUSE)
- Before final completion (PAUSE)

---

## ✅ SUCCESS CRITERIA (ALL MUST BE MET)

**Phase 1:**
- [ ] All HIGH severity patterns fixed
- [ ] All MEDIUM severity patterns fixed
- [ ] LOW severity patterns fixed or deferred
- [ ] PATTERN_FIXES.md complete
- [ ] Test pass rate documented

**Phase 2:**
- [ ] All 64 actions verified
- [ ] 64 verification files exist
- [ ] MUTATION_PROOFS.md shows 64/64
- [ ] Test suite passing

**Final:**
- [ ] `.agent_status.json` shows `"status": "complete"`
- [ ] `.verification_context` shows `"phase": "3_COMPLETE"`
- [ ] `VERIFICATION_COMPLETE.md` created
- [ ] All agents' handoff files exist

---

## 🚫 DO NOT

- Skip pattern fixes
- Verify actions before fixing patterns
- Skip testing
- Optimize prematurely
- Expand scope

---

## 🎯 COMMUNICATION RULES

**You MUST:**
- Update `.agent_status.json` after each pattern & every 10 actions
- Output progress report after each pattern & every 10 actions
- Pause at 2 PAUSE points (before Phase 2, before completion)
- Escalate blockers after 15 min stuck
- Auto-resolve if no response in 5 min

---

## 📁 FILES YOU'LL CREATE

```
.agent_status.json                      ← Updated 20+ times
apps/api/utils/                         ← Helper functions
tests/helpers/                          ← Test helpers
_VERIFICATION/
  verify_[59_new_actions].md            ← 59 new files
  PATTERN_FIXES.md                      ← Pattern documentation
  MUTATION_PROOFS.md                    ← Updated to 64/64
VERIFICATION_COMPLETE.md                ← Final report
```

---

**BEGIN NOW. Start with Phase 1, Pattern 1 (highest priority)**

Read PATTERN_ANALYSIS.md, update status, design solution.
