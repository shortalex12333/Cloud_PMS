# Multi-Agent Verification Plan

**How to verify 64 actions using 4 specialized agents**

**Total time:** 3-4 days
**Agents needed:** 4
**Handoff points:** Clear success criteria between agents

---

## 🎯 Overview

Instead of one AI getting overwhelmed, we use **4 specialized agents**:

```
Agent 1: Setup Engineer (2 hours)
   ↓ Handoff: Automation ready
Agent 2: Verification Operator (5 hours)
   ↓ Handoff: 5 actions verified
Agent 3: Pattern Analyst (1 hour)
   ↓ Handoff: Patterns categorized
Agent 4: Bulk Fixer (2-3 days)
   ↓ Handoff: All 64 actions compliant
```

**Each agent has:**
- ✅ Clear scope (one job only)
- ✅ Success criteria (when to stop)
- ✅ Handoff checklist (what next agent needs)
- ✅ Time limit (prevent overwhelm)

---

## 🤖 Agent 1: Setup Engineer

**Job:** Create automation so verification is brain-dead simple

**Time:** 2 hours
**Input:** Existing documentation
**Output:** Starter kit ready to use

### Scope

**Create 5 files:**
1. `verify.sh` - Main automation script
2. `next_action.sh` - Advance to next action
3. `QUICK_VERIFY_TEMPLATE.md` - 30-line template (not 215)
4. `VERIFICATION_DASHBOARD.md` - Single source of truth
5. `.verification_context` - State tracking (JSON)

**Create 1 helper:**
- `scripts/verification_helpers.js` - Database query helpers

**Test:**
- Run `./verify.sh` on `create_work_order`
- Verify template pre-fills correctly
- Verify timer works
- Verify state saves

### Success Criteria

Agent 1 is DONE when:
- [ ] `./verify.sh` runs without errors
- [ ] Creates verification file with pre-filled data
- [ ] Timer sends notification after 60 min
- [ ] `./next_action.sh` advances to next action
- [ ] `.verification_context` updates automatically
- [ ] Test run on create_work_order completes
- [ ] VERIFICATION_DASHBOARD.md shows progress

### Deliverables

**Files created:**
```
scripts/
  verify.sh                    ← Main script
  next_action.sh               ← Advance script
  verification_helpers.js      ← Query helpers

QUICK_VERIFY_TEMPLATE.md       ← 30-line template
VERIFICATION_DASHBOARD.md      ← Progress dashboard
.verification_context          ← State file (auto-updated)
```

**Documentation:**
```
AGENT_1_HANDOFF.md             ← Instructions for Agent 2
```

### Time Breakdown

- Create verify.sh: 30 min
- Create next_action.sh: 15 min
- Create QUICK_VERIFY_TEMPLATE.md: 20 min
- Create VERIFICATION_DASHBOARD.md: 15 min
- Create verification_helpers.js: 30 min
- Test automation: 10 min
- **Total: 2 hours**

### How to Launch Agent 1

```bash
# From this conversation, spawn Agent 1:
# Give it this prompt:

"You are Agent 1: Setup Engineer.

Your ONLY job: Create verification automation.

Read these files:
1. MULTI_AGENT_VERIFICATION_PLAN.md (this file)
2. PREVENTING_AI_OVERWHELM.md (context)
3. VERIFICATION_METHODOLOGY.md (what we're automating)

Create these files:
1. scripts/verify.sh
2. scripts/next_action.sh
3. QUICK_VERIFY_TEMPLATE.md
4. VERIFICATION_DASHBOARD.md
5. scripts/verification_helpers.js
6. AGENT_1_HANDOFF.md

Test: Run ./verify.sh create_work_order

Success criteria: All checkboxes in 'Agent 1 Success Criteria' section checked.

Time limit: 2 hours

When done: Create AGENT_1_HANDOFF.md and stop."
```

---

## 🤖 Agent 2: Verification Operator

**Job:** Verify exactly 5 actions, no more, no less

**Time:** 5 hours (1 hour per action)
**Input:** Automation from Agent 1
**Output:** 5 verified actions + pattern observations

### Scope

**Verify these 5 actions ONLY:**
1. `create_work_order` (create entity)
2. `assign_work_order` (update relationship)
3. `add_note` (simple create)
4. `mark_fault_resolved` (status update)
5. `get_work_order_details` (read-only)

**For each action:**
1. Run `./verify.sh [action_name]`
2. Fill in QUICK_VERIFY_TEMPLATE (30 lines)
3. Document gaps in template
4. Run `./next_action.sh`
5. Move to next action

**DO NOT:**
- Fix any bugs found
- Verify more than 5 actions
- Investigate side issues (write in RELATED_ISSUES.md)
- Spend more than 60 min per action

### Success Criteria

Agent 2 is DONE when:
- [ ] 5 verification files exist (_VERIFICATION/verify_*.md)
- [ ] All 5 marked "Status: ✅ Verified" in VERIFICATION_DASHBOARD.md
- [ ] PHASE_1_FINDINGS.md shows summary of 5 actions
- [ ] At least 2 patterns identified (e.g., "4/5 missing audit")
- [ ] RELATED_ISSUES.md has any side issues documented
- [ ] Total time: ~5 hours
- [ ] `.verification_context` shows PHASE=1_COMPLETE

### Deliverables

**Files created:**
```
_VERIFICATION/
  verify_create_work_order.md         ← Action 1
  verify_assign_work_order.md         ← Action 2
  verify_add_note.md                  ← Action 3
  verify_mark_fault_resolved.md       ← Action 4
  verify_get_work_order_details.md    ← Action 5

  PHASE_1_FINDINGS.md                 ← Summary
  RELATED_ISSUES.md                   ← Side issues
```

**Documentation:**
```
AGENT_2_HANDOFF.md                    ← Instructions for Agent 3
```

### Time Breakdown

- Action 1 (create_work_order): 60 min
- Action 2 (assign_work_order): 60 min
- Action 3 (add_note): 60 min
- Action 4 (mark_fault_resolved): 60 min
- Action 5 (get_work_order_details): 60 min
- **Total: 5 hours**

### Automation Usage

**For each action:**
```bash
# 1. Start verification
./verify.sh create_work_order

# Script outputs:
# ✅ Handler found at line 1847
# ✅ Test found: tests/e2e/mutation_proof_create_work_order.spec.ts
# 🧪 Running test...
# ✅ Test PASS
# 📝 Template created: _VERIFICATION/verify_create_work_order.md
# ⏱️  Timer started: 60 minutes

# 2. Fill in template (30 lines)
# Open _VERIFICATION/verify_create_work_order.md
# Fill in 6 proofs, error cases, gaps

# 3. Advance to next action
./next_action.sh

# Script outputs:
# ✅ Progress saved
# ✅ Dashboard updated
# 📊 Progress: 1/5 actions complete
# ⏭️  Next action: assign_work_order
# Run: ./verify.sh assign_work_order
```

### How to Launch Agent 2

```bash
# After Agent 1 completes, spawn Agent 2:

"You are Agent 2: Verification Operator.

Your ONLY job: Verify exactly 5 actions.

Read these files:
1. AGENT_1_HANDOFF.md (from Agent 1)
2. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 2 section)
3. QUICK_VERIFY_TEMPLATE.md (template to fill)

For each action:
1. Run ./verify.sh [action_name]
2. Fill in template (30 lines)
3. Run ./next_action.sh
4. Repeat

Actions to verify (in order):
1. create_work_order
2. assign_work_order
3. add_note
4. mark_fault_resolved
5. get_work_order_details

Time limit: 1 hour per action, 5 hours total

Success criteria: All checkboxes in 'Agent 2 Success Criteria' checked.

When done: Create AGENT_2_HANDOFF.md and stop."
```

---

## 🤖 Agent 3: Pattern Analyst

**Job:** Analyze 5 actions, find patterns, prioritize

**Time:** 1 hour
**Input:** 5 verified actions from Agent 2
**Output:** Patterns categorized and prioritized

### Scope

**Analyze findings from 5 actions:**
1. Read all 5 verification files
2. Read PHASE_1_FINDINGS.md
3. Categorize gaps into patterns
4. Calculate severity + scope
5. Prioritize patterns
6. Design bulk fix approach for each pattern

**DO NOT:**
- Fix any patterns
- Verify more actions
- Implement solutions

### Success Criteria

Agent 3 is DONE when:
- [ ] PATTERN_ANALYSIS.md complete
- [ ] All gaps categorized into patterns
- [ ] Patterns prioritized (HIGH → MEDIUM → LOW)
- [ ] Fix approach designed for each pattern
- [ ] Effort estimated for each pattern
- [ ] Pattern threshold applied (60%+ = pattern)
- [ ] `.verification_context` shows PHASE=2_COMPLETE

### Deliverables

**Files created:**
```
_VERIFICATION/
  PATTERN_ANALYSIS.md                 ← Pattern categorization
```

**Updated:**
```
VERIFICATION_DASHBOARD.md             ← Shows Phase 2 complete
```

**Documentation:**
```
AGENT_3_HANDOFF.md                    ← Instructions for Agent 4
```

### Analysis Template

**For each pattern found:**
```markdown
### Pattern H1: Missing Audit Logs

**Severity:** HIGH (compliance requirement)
**Scope:** 4/5 actions (80%)
**Projected total:** ~51/64 actions
**Actions affected:**
- create_work_order
- assign_work_order
- mark_fault_resolved
- get_work_order_details (expected for read)

**Root cause:**
No enforcement mechanism, audit not part of handler template

**Fix approach:**
1. Create write_audit_log() helper
2. Add to ALL mutation handlers
3. Create verifyAuditLog() test helper
4. Add audit test to ALL mutation tests

**Estimated effort:** 5 hours (10 min × 30 actions)
**Priority:** 1 (fix first)
```

### Time Breakdown

- Read 5 verification files: 15 min
- Categorize gaps into patterns: 20 min
- Calculate severity + scope: 10 min
- Design fix approaches: 10 min
- Estimate effort: 5 min
- **Total: 1 hour**

### How to Launch Agent 3

```bash
# After Agent 2 completes, spawn Agent 3:

"You are Agent 3: Pattern Analyst.

Your ONLY job: Analyze patterns from 5 verified actions.

Read these files:
1. AGENT_2_HANDOFF.md (from Agent 2)
2. _VERIFICATION/verify_*.md (all 5 verification files)
3. _VERIFICATION/PHASE_1_FINDINGS.md
4. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 3 section)

Analyze:
1. What gaps appear in 3+ actions? (60%+ = pattern)
2. What's the root cause of each pattern?
3. How to fix each pattern in bulk?
4. How long will each pattern take to fix?

Output: PATTERN_ANALYSIS.md with all patterns categorized

Pattern threshold: 3/5 actions (60%) or more = pattern

Time limit: 1 hour

Success criteria: All checkboxes in 'Agent 3 Success Criteria' checked.

When done: Create AGENT_3_HANDOFF.md and stop."
```

---

## 🤖 Agent 4: Bulk Fixer

**Job:** Fix patterns in bulk, verify all 64 actions

**Time:** 2-3 days
**Input:** Patterns from Agent 3
**Output:** All 64 actions compliant

### Scope

**For each pattern (HIGH → MEDIUM → LOW):**
1. Design solution ONCE
2. Apply to ALL affected actions
3. Test pattern fix on all affected actions
4. Document results in PATTERN_FIXES.md
5. Move to next pattern

**After all patterns fixed:**
1. Verify remaining 59 actions (64 - 5 already done)
2. Ensure all pass 6 proofs
3. Update MUTATION_PROOFS.md tracker

**DO NOT:**
- Fix bugs individually
- Skip testing
- Move to next pattern before current one complete

### Success Criteria

Agent 4 is DONE when:
- [ ] All HIGH severity patterns fixed
- [ ] All MEDIUM severity patterns fixed
- [ ] All LOW severity patterns fixed (or deferred)
- [ ] All 64 actions verified
- [ ] Test pass rate documented for each pattern
- [ ] PATTERN_FIXES.md complete
- [ ] MUTATION_PROOFS.md shows 64/64 complete
- [ ] `.verification_context` shows PHASE=3_COMPLETE

### Deliverables

**Files created:**
```
_VERIFICATION/
  PATTERN_FIXES.md                    ← All pattern fixes documented
  verify_[remaining_59].md            ← Remaining 59 actions verified

apps/api/utils/
  audit.py                            ← Audit helper (if needed)
  validation.py                       ← Validation helpers (if needed)

tests/helpers/
  audit.ts                            ← Test helpers
  rls.ts                              ← RLS test helpers
```

**Updated:**
```
_VERIFICATION/MUTATION_PROOFS.md      ← 64/64 complete
VERIFICATION_DASHBOARD.md             ← All actions verified
```

**Documentation:**
```
VERIFICATION_COMPLETE.md              ← Final report
```

### Time Breakdown (Estimated)

**Pattern fixes:**
- HIGH Pattern 1 (Missing audit): 5 hours
- HIGH Pattern 2 (Missing validation): 6 hours
- MEDIUM Pattern 1 (Inconsistent errors): 3 hours
- MEDIUM Pattern 2 (No RLS tests): 4 hours
- Verify remaining 59 actions: 8 hours (using automation)
- **Total: 26 hours (~3 days)**

### Bulk Fix Example

**Pattern: Missing Audit Logs (30 actions)**

```bash
# 1. Create helper (30 min)
cat > apps/api/utils/audit.py << 'EOF'
async def write_audit_log(client, action, entity_id, yacht_id, user_id, changes):
    await client.table('pms_audit_log').insert({
        'action': action,
        'entity_id': entity_id,
        'yacht_id': yacht_id,
        'user_id': user_id,
        'changes': changes
    }).execute()
EOF

# 2. Find all affected handlers (5 min)
grep -n 'if action ==' apps/api/routes/p0_actions_routes.py | grep -E '(create|update|delete|assign|mark)'

# 3. Add audit call to each handler (5 min × 30 = 150 min)
# Use sed or manual editing to add after each successful mutation

# 4. Create test helper (15 min)
cat > tests/helpers/audit.ts << 'EOF'
export async function verifyAuditLog(action, entity_id) {
  const { data } = await supabase.from('pms_audit_log')...
  expect(data).toBeTruthy();
}
EOF

# 5. Add to all tests (3 min × 30 = 90 min)
# Add: await verifyAuditLog(action, entity_id);

# 6. Run all tests (10 min)
npx playwright test

# 7. Document results (15 min)
# Update PATTERN_FIXES.md

Total: ~5 hours for 30 actions
```

### How to Launch Agent 4

```bash
# After Agent 3 completes, spawn Agent 4:

"You are Agent 4: Bulk Fixer.

Your ONLY job: Fix patterns in bulk, verify all 64 actions.

Read these files:
1. AGENT_3_HANDOFF.md (from Agent 3)
2. _VERIFICATION/PATTERN_ANALYSIS.md
3. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 4 section)

For each pattern (HIGH → MEDIUM → LOW):
1. Design solution ONCE
2. Apply to ALL affected actions
3. Test on all affected actions
4. Document in PATTERN_FIXES.md
5. Move to next pattern

After patterns fixed:
1. Use ./verify.sh to verify remaining 59 actions
2. Update MUTATION_PROOFS.md tracker

Time limit: 3 days

Success criteria: All checkboxes in 'Agent 4 Success Criteria' checked.

When done: Create VERIFICATION_COMPLETE.md and stop."
```

---

## 📊 Agent Summary Table

| Agent | Job | Time | Input | Output | Success Gate |
|-------|-----|------|-------|--------|--------------|
| **1. Setup Engineer** | Create automation | 2h | Documentation | Starter kit | `./verify.sh` works |
| **2. Verification Operator** | Verify 5 actions | 5h | Automation | 5 verified actions | PHASE_1_FINDINGS.md complete |
| **3. Pattern Analyst** | Find patterns | 1h | 5 actions | Patterns categorized | PATTERN_ANALYSIS.md complete |
| **4. Bulk Fixer** | Fix in bulk | 2-3d | Patterns | 64 actions verified | MUTATION_PROOFS.md 64/64 |

**Total:** ~3-4 days, 4 agents

---

## 🚀 Launch Sequence

### Step 1: Launch Agent 1 (NOW)

```bash
# User runs:
"Launch Agent 1: Setup Engineer using the prompt in MULTI_AGENT_VERIFICATION_PLAN.md"

# Agent 1 creates:
# - verify.sh
# - next_action.sh
# - QUICK_VERIFY_TEMPLATE.md
# - VERIFICATION_DASHBOARD.md
# - verification_helpers.js
# - AGENT_1_HANDOFF.md

# Agent 1 stops after 2 hours
```

### Step 2: Launch Agent 2 (After Agent 1)

```bash
# User runs:
"Launch Agent 2: Verification Operator using prompt in MULTI_AGENT_VERIFICATION_PLAN.md"

# Agent 2 reads: AGENT_1_HANDOFF.md
# Agent 2 verifies: 5 actions
# Agent 2 creates: AGENT_2_HANDOFF.md

# Agent 2 stops after 5 hours
```

### Step 3: Launch Agent 3 (After Agent 2)

```bash
# User runs:
"Launch Agent 3: Pattern Analyst using prompt in MULTI_AGENT_VERIFICATION_PLAN.md"

# Agent 3 reads: AGENT_2_HANDOFF.md
# Agent 3 analyzes: Patterns
# Agent 3 creates: AGENT_3_HANDOFF.md

# Agent 3 stops after 1 hour
```

### Step 4: Launch Agent 4 (After Agent 3)

```bash
# User runs:
"Launch Agent 4: Bulk Fixer using prompt in MULTI_AGENT_VERIFICATION_PLAN.md"

# Agent 4 reads: AGENT_3_HANDOFF.md
# Agent 4 fixes: All patterns in bulk
# Agent 4 verifies: Remaining 59 actions
# Agent 4 creates: VERIFICATION_COMPLETE.md

# Agent 4 stops after 2-3 days
```

---

## ✅ Handoff Checklist

**Agent 1 → Agent 2:**
- [ ] `verify.sh` executable and tested
- [ ] `next_action.sh` executable and tested
- [ ] QUICK_VERIFY_TEMPLATE.md created
- [ ] VERIFICATION_DASHBOARD.md created
- [ ] Test run on create_work_order successful
- [ ] AGENT_1_HANDOFF.md created with instructions

**Agent 2 → Agent 3:**
- [ ] 5 verification files created
- [ ] All 5 marked complete in dashboard
- [ ] PHASE_1_FINDINGS.md summarizes findings
- [ ] At least 2 patterns identified
- [ ] RELATED_ISSUES.md has side issues
- [ ] AGENT_2_HANDOFF.md created

**Agent 3 → Agent 4:**
- [ ] PATTERN_ANALYSIS.md complete
- [ ] Patterns prioritized (HIGH → MEDIUM → LOW)
- [ ] Fix approach designed for each pattern
- [ ] Effort estimated for each pattern
- [ ] AGENT_3_HANDOFF.md created with fix plan

**Agent 4 → Complete:**
- [ ] All patterns fixed
- [ ] All 64 actions verified
- [ ] PATTERN_FIXES.md documents all fixes
- [ ] MUTATION_PROOFS.md shows 64/64
- [ ] Test suite passing
- [ ] VERIFICATION_COMPLETE.md created

---

## 🎯 Why This Works

**Prevents overwhelm:**
- ✅ Each agent has ONE job
- ✅ Clear time limits
- ✅ Handoff checklist (know when done)
- ✅ Can't move forward until success criteria met

**Prevents scope creep:**
- ✅ Agent 1 doesn't verify actions
- ✅ Agent 2 doesn't fix bugs
- ✅ Agent 3 doesn't implement fixes
- ✅ Agent 4 doesn't analyze patterns (already done)

**Prevents hallucination:**
- ✅ Automation generates proof (can't fake it)
- ✅ Success criteria are checkboxes (binary)
- ✅ Handoff docs show what was actually created

**Enables parallel work (future):**
- Agent 2 verifies actions 1-5 (one instance)
- Agent 2' verifies actions 6-10 (parallel instance)
- Agent 3 combines findings from both

---

## 📁 File Structure After All Agents

```
BACK_BUTTON_CLOUD_PMS/
├── scripts/
│   ├── verify.sh                      ← Agent 1
│   ├── next_action.sh                 ← Agent 1
│   └── verification_helpers.js        ← Agent 1
│
├── _VERIFICATION/
│   ├── verify_create_work_order.md    ← Agent 2
│   ├── verify_assign_work_order.md    ← Agent 2
│   ├── ... (64 total)                 ← Agent 2 + Agent 4
│   ├── PHASE_1_FINDINGS.md            ← Agent 2
│   ├── RELATED_ISSUES.md              ← Agent 2
│   ├── PATTERN_ANALYSIS.md            ← Agent 3
│   ├── PATTERN_FIXES.md               ← Agent 4
│   └── MUTATION_PROOFS.md             ← Agent 4
│
├── QUICK_VERIFY_TEMPLATE.md           ← Agent 1
├── VERIFICATION_DASHBOARD.md          ← Agent 1, updated by all
├── .verification_context              ← Agent 1, updated by all
├── AGENT_1_HANDOFF.md                 ← Agent 1
├── AGENT_2_HANDOFF.md                 ← Agent 2
├── AGENT_3_HANDOFF.md                 ← Agent 3
└── VERIFICATION_COMPLETE.md           ← Agent 4
```

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Multi-agent plan to verify 64 actions without overwhelm
**Next Step:** Launch Agent 1: Setup Engineer
