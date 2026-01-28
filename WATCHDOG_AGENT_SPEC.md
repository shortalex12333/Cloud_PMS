# Watchdog Agent Specification

**Meta-orchestrator that monitors working agents and ensures mission compliance**

---

## 🎯 Purpose

Monitor working agents (Agent 2, 3, 4) to ensure:
- Agents stay focused on their mission
- Success criteria are being met
- Files are being created correctly
- Agents don't drift from task
- Progress is happening
- Quality standards maintained

---

## 🔍 What Watchdog Monitors

### 1. Status File (`.agent_status.json`)

**Check every:** 5 minutes

**What to verify:**
- File exists
- Last update timestamp is recent (<90 min)
- Status matches expected phase
- Current action matches expected sequence
- No blockers unaddressed for >30 min

**Example checks:**
```javascript
// Agent 2 should be on one of these actions
const AGENT_2_ACTIONS = ['create_work_order', 'assign_work_order', 'add_note', 'mark_fault_resolved', 'get_work_order_details'];

// Check status file
const status = JSON.parse(readFile('.agent_status.json'));

// Verify freshness
const minutesAgo = (Date.now() - new Date(status.last_update)) / 60000;
if (minutesAgo > 90) {
  ALERT('Status file stale - no update in ' + minutesAgo + ' minutes');
}

// Verify on-task
if (status.agent === 'Agent 2' && !AGENT_2_ACTIONS.includes(status.current_action)) {
  ALERT('Agent 2 working on wrong action: ' + status.current_action);
}
```

---

### 2. Progress Log (`AGENT_PROGRESS.md`)

**Check every:** 10 minutes

**What to verify:**
- File exists (once agent starts)
- Milestones are being completed
- No action taking >90 min
- Patterns being documented (Agent 2)

**Example checks:**
```bash
# Count completed actions
COMPLETED=$(grep -c '\[x\]' AGENT_PROGRESS.md)

# Agent 2 should have 0-5 completed
# If 0 after 2 hours → ALERT
# If >5 → ALERT (doing too much)
```

---

### 3. Verification Files (`_VERIFICATION/verify_*.md`)

**Check every:** 15 minutes

**What to verify:**
- Files being created
- 6 proofs section filled in
- Gaps section has actual gaps listed
- Status marked (✅ or ⚠️)
- Time spent documented

**Example checks:**
```bash
# Agent 2 should create 5 files total
VERIFY_FILES=$(ls _VERIFICATION/verify_*.md 2>/dev/null | wc -l)

# After 2 hours, expect at least 1 file
# After 5 hours, expect 5 files

# Check file quality
if grep -q '\[PASTE RESPONSE\]' _VERIFICATION/verify_create_work_order.md; then
  ALERT('Verification file has unfilled placeholders');
fi
```

---

### 4. Dashboard (`VERIFICATION_DASHBOARD.md`)

**Check every:** 10 minutes

**What to verify:**
- Shows current progress
- Matches status file
- Actions checked off as completed

---

### 5. Handoff Files

**Check when expected:**
- `AGENT_2_HANDOFF.md` after 5 hours
- `AGENT_3_HANDOFF.md` after 6 hours (5 + 1)
- `VERIFICATION_COMPLETE.md` after 2-3 days

**What to verify:**
- File exists when agent reports complete
- Contains required sections
- Patterns documented (Agent 2 → 3)
- Fix approaches documented (Agent 3 → 4)

---

## ⏱️ Monitoring Schedule

### Agent 2 (5 hours)

**Timeline expectations:**
```
0:00  - Agent starts
0:05  - .agent_status.json exists
0:60  - First verification file exists
1:00  - First milestone report
2:00  - Second milestone report (2/5 complete)
3:00  - Third milestone report (3/5 complete)
4:00  - Fourth milestone report (4/5 complete)
5:00  - Fifth milestone report (5/5 complete)
5:00  - AGENT_2_HANDOFF.md exists
```

**Watchdog checks:**
- Every 5 min: Status file fresh?
- Every 10 min: Progress happening?
- Every 60 min: Milestone reached?
- After 5 hours: Handoff created?

**Red flags:**
- Status file not updated in 90 min
- Same action for >90 min
- No verification files after 2 hours
- >5 verification files (doing too much)
- No handoff after 6 hours
- Agent trying to fix bugs

---

### Agent 3 (1 hour)

**Timeline expectations:**
```
0:00  - Agent starts
0:05  - .agent_status.json exists
0:15  - Checkpoint 1 report
0:35  - Checkpoint 2 report
1:00  - Checkpoint 3 report
1:00  - PATTERN_ANALYSIS.md exists
1:05  - AGENT_3_HANDOFF.md exists
```

**Watchdog checks:**
- Every 5 min: Status file fresh?
- Every 15 min: Checkpoint reached?
- After 1 hour: Analysis file exists?
- After 1.5 hours: Handoff created?

**Red flags:**
- Status file not updated in 30 min
- No PATTERN_ANALYSIS.md after 1.5 hours
- Agent trying to implement fixes
- Agent verifying additional actions
- Patterns not categorized by severity

---

### Agent 4 (2-3 days)

**Timeline expectations:**
```
Phase 1 (6-12 hours):
- Pattern fixes happening
- PATTERN_FIXES.md being updated
- Tests running

Phase 2 (8-16 hours):
- 59 new verification files
- Progress reports every 10 actions
- MUTATION_PROOFS.md updated to 64/64

Final:
- VERIFICATION_COMPLETE.md created
```

**Watchdog checks:**
- Every 10 min: Status file fresh?
- Every 1 hour: Progress happening?
- Every 4 hours: Pattern fixed or actions verified?
- After 3 days: Completion file exists?

**Red flags:**
- Status file not updated in 2 hours
- Same pattern for >6 hours with no progress
- Verifying actions before fixing patterns
- >64 verification files (too many)
- Tests not being run

---

## 🚨 Intervention Triggers

### CRITICAL - Immediate Alert

**1. Agent Off-Mission**
```
Agent 2 trying to fix bugs → STOP
Agent 3 implementing fixes → STOP
Agent working on undefined actions → STOP
```

**2. Status Stale**
```
No update in >90 min (Agent 2/3)
No update in >2 hours (Agent 4)
```

**3. File Corruption**
```
.agent_status.json invalid JSON
Verification files have templates unfilled
Handoff files missing required sections
```

**4. Success Criteria Violation**
```
Agent 2: >5 actions verified
Agent 3: No patterns found (unexpected)
Agent 4: Skipping pattern fixes
```

---

### WARNING - Monitor Closely

**1. Slow Progress**
```
Action taking >90 min (Agent 2)
Checkpoint taking >30 min (Agent 3)
Pattern fix taking >8 hours (Agent 4)
```

**2. Quality Issues**
```
Verification files incomplete
Gaps section empty (suspicious)
No patterns documented
Test results not shown
```

**3. Process Deviations**
```
Files created out of order
Steps skipped
No milestone reports
Missing progress updates
```

---

## ✅ Success Criteria Verification

### Agent 2 Success

**Watchdog verifies:**
```bash
# Count verification files
VERIFY_COUNT=$(ls _VERIFICATION/verify_*.md 2>/dev/null | wc -l)
if [ $VERIFY_COUNT -ne 5 ]; then
  ALERT "Expected 5 verification files, found $VERIFY_COUNT"
fi

# Check PHASE_1_FINDINGS exists
if [ ! -f "_VERIFICATION/PHASE_1_FINDINGS.md" ]; then
  ALERT "PHASE_1_FINDINGS.md missing"
fi

# Check patterns documented
PATTERNS=$(grep -c "Pattern" _VERIFICATION/PHASE_1_FINDINGS.md)
if [ $PATTERNS -lt 2 ]; then
  ALERT "Expected at least 2 patterns, found $PATTERNS"
fi

# Check handoff created
if [ ! -f "AGENT_2_HANDOFF.md" ]; then
  ALERT "AGENT_2_HANDOFF.md missing"
fi

# Verify status shows complete
STATUS=$(grep -o '"status": *"[^"]*"' .agent_status.json | cut -d'"' -f4)
if [ "$STATUS" != "complete" ]; then
  ALERT "Status should be 'complete', is '$STATUS'"
fi
```

---

### Agent 3 Success

**Watchdog verifies:**
```bash
# Check PATTERN_ANALYSIS exists
if [ ! -f "_VERIFICATION/PATTERN_ANALYSIS.md" ]; then
  ALERT "PATTERN_ANALYSIS.md missing"
fi

# Check patterns categorized
HIGH=$(grep -c "HIGH SEVERITY" _VERIFICATION/PATTERN_ANALYSIS.md)
MEDIUM=$(grep -c "MEDIUM SEVERITY" _VERIFICATION/PATTERN_ANALYSIS.md)
if [ $HIGH -eq 0 ] && [ $MEDIUM -eq 0 ]; then
  ALERT "No HIGH or MEDIUM patterns found (suspicious)"
fi

# Check fix approaches documented
FIX_APPROACH=$(grep -c "Fix approach:" _VERIFICATION/PATTERN_ANALYSIS.md)
if [ $FIX_APPROACH -lt 2 ]; then
  ALERT "Expected fix approaches for patterns"
fi

# Check handoff created
if [ ! -f "AGENT_3_HANDOFF.md" ]; then
  ALERT "AGENT_3_HANDOFF.md missing"
fi
```

---

### Agent 4 Success

**Watchdog verifies:**
```bash
# Check PATTERN_FIXES exists
if [ ! -f "_VERIFICATION/PATTERN_FIXES.md" ]; then
  ALERT "PATTERN_FIXES.md missing"
fi

# Count verification files (should be 64 total)
VERIFY_COUNT=$(ls _VERIFICATION/verify_*.md 2>/dev/null | wc -l)
if [ $VERIFY_COUNT -ne 64 ]; then
  ALERT "Expected 64 verification files, found $VERIFY_COUNT"
fi

# Check MUTATION_PROOFS shows 64/64
if ! grep -q "64/64" _VERIFICATION/MUTATION_PROOFS.md; then
  ALERT "MUTATION_PROOFS should show 64/64"
fi

# Check completion file created
if [ ! -f "VERIFICATION_COMPLETE.md" ]; then
  ALERT "VERIFICATION_COMPLETE.md missing"
fi
```

---

## 📝 Watchdog Reports

### Real-Time Status Report

Output every 10 minutes:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 WATCHDOG STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Time: 14:30:00
Monitoring: Agent 2 (Verification Operator)

Status File:
✅ Fresh (updated 3 min ago)
✅ On task (Action 2: assign_work_order)
✅ Progress: 2/5 actions complete

Files Created:
✅ verify_create_work_order.md
✅ verify_assign_work_order.md
⏳ 3 more expected

Quality Checks:
✅ 6 proofs filled in (Action 1)
✅ Gaps documented (Action 1)
⚠️ Action 2 in progress (55 min elapsed)

Alerts: None
Status: ✅ ON TRACK

Next check: 14:40:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Alert Report

When issues detected:
```
🚨 WATCHDOG ALERT 🚨

Time: 15:30:00
Agent: Agent 2
Alert Level: WARNING

Issue: Action taking too long
Details:
- Current action: create_work_order
- Time elapsed: 95 minutes
- Expected: <60 minutes

Recommendation:
Agent should document "needs investigation" and move to next action

Waiting 15 minutes before escalating to CRITICAL...

Auto-intervention in 15 min if no progress.
```

---

## 🛠️ Watchdog Actions

### Monitoring Actions (Automatic)

**Every 5 min:**
- Read `.agent_status.json`
- Check timestamp freshness
- Verify on-task

**Every 10 min:**
- Read `AGENT_PROGRESS.md`
- Count completed milestones
- Update watchdog status report

**Every 15 min:**
- Check verification files
- Verify quality (no placeholders)
- Count files created

**Every 1 hour:**
- Re-read all verification files
- Check success criteria progress
- Generate detailed report

---

### Intervention Actions (Manual Trigger)

**When CRITICAL alert:**
1. Output alert to user
2. Suggest specific action
3. Wait for user decision

**User can:**
- Type 'continue' - Dismiss alert, continue monitoring
- Type 'intervene' - Stop agent, require user guidance
- Type 'auto-fix' - Watchdog sends correction to agent

---

## 🔄 Re-Reading Strategy

### When to Re-Read Files

**Status file (`.agent_status.json`):**
- Every 5 minutes (always)

**Verification files:**
- When status shows action complete
- Every 1 hour (quality check)
- Before reporting success

**Handoff files:**
- When status shows agent complete
- Before approving next agent launch

**Pattern files:**
- After Agent 3 complete
- Before Agent 4 starts

---

### What to Look For

**In verification files:**
```bash
# Check for unfilled templates
grep -c '\[PASTE' _VERIFICATION/verify_*.md
# Should be 0

# Check for gaps documented
grep -c 'Gaps found:' _VERIFICATION/verify_*.md
# Should match number of files

# Check for status marked
grep -c 'Status: ✅' _VERIFICATION/verify_*.md
# Should match completed actions
```

**In pattern analysis:**
```bash
# Check patterns have severity
grep -c 'Severity: HIGH' _VERIFICATION/PATTERN_ANALYSIS.md
# Should be >0

# Check fix approaches exist
grep -c 'Fix approach:' _VERIFICATION/PATTERN_ANALYSIS.md
# Should match pattern count

# Check effort estimated
grep -c 'Estimated effort:' _VERIFICATION/PATTERN_ANALYSIS.md
# Should match pattern count
```

---

## 📁 Watchdog Log

**File:** `.watchdog_log.md`

**Updated:** Every check

**Format:**
```markdown
# Watchdog Log

## Session: 2026-01-22 14:00

### 14:00 - Started monitoring Agent 2
- Status: in_progress
- Current action: create_work_order

### 14:05 - Check 1
- Status: ✅ Fresh
- Progress: ✅ On track
- Files: 0/5

### 14:10 - Check 2
- Status: ✅ Fresh
- Progress: ✅ On track
- Files: 0/5
- Note: Action 1 in progress (10 min)

### 14:60 - Check 12
- Status: ✅ Fresh
- Progress: ✅ Milestone 1 complete
- Files: 1/5 ✅
- Quality: verify_create_work_order.md complete

### 15:30 - Check 18
- Status: ⚠️ Stale (no update in 30 min)
- Progress: ⚠️ Action 2 taking >90 min
- Files: 1/5
- ALERT: Slow progress

### 19:00 - Agent 2 Complete
- Status: ✅ Complete
- Files: 5/5 ✅
- Handoff: ✅ AGENT_2_HANDOFF.md created
- Patterns: 3 identified
- Success criteria: ✅ ALL MET

Ready for Agent 3.
```

---

## ✅ Watchdog Success Criteria

**Watchdog is working correctly when:**
- ✅ Status reports every 10 min
- ✅ Alerts trigger appropriately
- ✅ Files monitored correctly
- ✅ Quality checks performed
- ✅ Success criteria verified
- ✅ Intervention suggestions accurate
- ✅ Log file maintained

**Watchdog has done its job when:**
- ✅ Agent completes successfully
- ✅ All files created correctly
- ✅ Success criteria met
- ✅ No critical issues unresolved
- ✅ Handoff file verified
- ✅ Ready for next agent

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Watchdog monitoring specification
**Monitors:** Agents 2, 3, 4
