# Agent Communication Protocol

**How agents report progress, escalate blockers, and communicate with orchestrator**

---

## 🎯 Purpose

Prevent agents from running for hours/days without communication.

**Required behaviors:**
- Regular progress updates
- Milestone reporting
- Blocker escalation
- Checkpoint pauses
- Status file maintenance

---

## 📊 Communication Channels

### 1. Status File (Machine-Readable)

**File:** `.agent_status.json`

**Updated:** After every action completed

**Format:**
```json
{
  "agent": "Agent 2",
  "phase": "verification",
  "status": "in_progress",
  "current_action": "create_work_order",
  "actions_completed": 1,
  "actions_total": 5,
  "time_elapsed_minutes": 55,
  "last_update": "2026-01-22T14:30:00Z",
  "blockers": [],
  "next_milestone": "Action 2 complete",
  "eta_minutes": 240
}
```

**How to update:**
```bash
cat > .agent_status.json << 'EOF'
{
  "agent": "Agent 2",
  "status": "in_progress",
  "current_action": "assign_work_order",
  "actions_completed": 2,
  "actions_total": 5,
  "time_elapsed_minutes": 115,
  "last_update": "2026-01-22T15:30:00Z"
}
EOF
```

---

### 2. Progress Log (Human-Readable)

**File:** `AGENT_PROGRESS.md`

**Updated:** After each milestone

**Format:**
```markdown
# Agent Progress Log

## Agent 2: Verification Operator

**Started:** 2026-01-22 14:00
**Current time:** 2026-01-22 15:30
**Elapsed:** 1h 30m

### Milestones Completed

- [x] Action 1: create_work_order (55 min) ✅
- [x] Action 2: assign_work_order (60 min) ✅
- [ ] Action 3: add_note (in progress)
- [ ] Action 4: mark_fault_resolved
- [ ] Action 5: get_work_order_details

### Current Status

Working on: Action 3 (add_note)
Time spent: 15 min
Findings so far:
- Action 1: Missing audit log, no validation
- Action 2: Missing audit log, no validation
- Action 3: In progress

### Blockers

None

### Next Checkpoint

Action 3 complete (ETA: 14:30)
```

**How to update:**
```bash
# Append to log
echo "- [x] Action 2: assign_work_order (60 min) ✅" >> AGENT_PROGRESS.md
```

---

### 3. Milestone Reports (User Notification)

**When:** After each major milestone

**Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MILESTONE REACHED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent: Agent 2 (Verification Operator)
Milestone: Action 2 of 5 complete
Time: 2h 00m elapsed
Progress: 40% (2/5 actions)

Status: ✅ On track

Findings:
- Action 1 (create_work_order): Missing audit, no validation
- Action 2 (assign_work_order): Missing audit, no validation

Pattern emerging: 2/2 actions missing audit logs

Next: Action 3 (add_note) starting now
ETA for next milestone: 60 minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Milestones:**
- **Agent 2:** After each action (5 milestones)
- **Agent 3:** After pattern categorization complete
- **Agent 4:** After each pattern fixed + every 10 actions verified

---

### 4. Blocker Escalation (Immediate)

**When:** Stuck for >15 minutes

**Format:**
```
🚨 BLOCKER ESCALATION 🚨

Agent: Agent 2
Action: create_work_order
Blocker: Test failing with 500 error
Time stuck: 20 minutes

Details:
- Running: ./scripts/verify.sh create_work_order
- Expected: Test passes
- Actual: 500 Internal Server Error
- Error: Handler crashes at line 1847

Options:
1. Document failure and continue (recommended)
2. Investigate further (may exceed 60 min limit)
3. Skip this action (not recommended)

Waiting for guidance...
```

**How agent handles blockers:**
1. Try for 15 minutes
2. If still blocked → escalate (show message above)
3. Wait for user response OR
4. Auto-resolve: Document failure, mark "needs investigation", continue

---

## ⏱️ Checkpoint Schedule

### Agent 2 (Verification Operator)

**Checkpoints every 60 minutes (after each action):**

```
Checkpoint 1: After action 1 (create_work_order)
  ↓ Report: Findings, time spent, continue? (auto-yes if <60 min)

Checkpoint 2: After action 2 (assign_work_order)
  ↓ Report: Findings, patterns emerging, continue? (auto-yes)

Checkpoint 3: After action 3 (add_note)
  ↓ Report: Findings, patterns confirmed, continue? (auto-yes)

Checkpoint 4: After action 4 (mark_fault_resolved)
  ↓ Report: Findings, ready for final action? (auto-yes)

Checkpoint 5: After action 5 (get_work_order_details)
  ↓ Report: All findings, patterns identified, create handoff? (PAUSE)
```

**PAUSE points (require user confirmation):**
- Before creating AGENT_2_HANDOFF.md
- If >3 actions fail tests
- If no patterns emerge (unexpected)

---

### Agent 3 (Pattern Analyst)

**Checkpoints:**

```
Checkpoint 1: After reading all 5 verification files
  ↓ Report: Summary of gaps found, continue?

Checkpoint 2: After pattern categorization
  ↓ Report: Patterns identified, severity assigned, continue?

Checkpoint 3: After fix approach design
  ↓ Report: Fix approaches, effort estimates, create handoff? (PAUSE)
```

**PAUSE points:**
- Before creating AGENT_3_HANDOFF.md
- If no patterns found (unexpected)
- If all patterns are LOW severity (unexpected)

---

### Agent 4 (Bulk Fixer)

**Checkpoints:**

```
Checkpoint 1: After each pattern fix
  ↓ Report: Pattern fixed, test results, continue?

Checkpoint 2: Every 10 actions verified
  ↓ Report: Progress (10/64, 20/64, etc.), continue?

Checkpoint 3: After all patterns fixed
  ↓ Report: All patterns complete, start verification? (PAUSE)

Checkpoint 4: After all 64 actions verified
  ↓ Report: Final results, create completion? (PAUSE)
```

**PAUSE points:**
- Before starting verification (after all patterns fixed)
- Before creating VERIFICATION_COMPLETE.md
- If >10 actions fail tests after pattern fixes

---

## 📝 Template: Milestone Report

**Agent fills in and outputs after each milestone:**

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MILESTONE: [MILESTONE NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Agent:** [AGENT NAME]
**Checkpoint:** [X of Y]
**Time elapsed:** [HH:MM]
**Status:** ✅ On track / ⚠️ Delayed / 🚨 Blocked

**What was completed:**
- [ITEM 1]
- [ITEM 2]

**Findings:**
- [FINDING 1]
- [FINDING 2]

**Patterns observed:**
- [PATTERN 1 if any]

**Next steps:**
- [NEXT STEP]
- ETA: [MINUTES]

**Issues/Blockers:**
- [NONE or LIST]

**Continue? (auto-yes if on track)**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 📝 Template: Blocker Escalation

```markdown
🚨 BLOCKER ESCALATION 🚨

**Agent:** [AGENT NAME]
**Task:** [CURRENT TASK]
**Time stuck:** [MINUTES]

**Problem:**
[DESCRIPTION OF BLOCKER]

**What I tried:**
1. [ATTEMPT 1]
2. [ATTEMPT 2]
3. [ATTEMPT 3]

**Error details:**
```
[ERROR OUTPUT]
```

**Options:**
1. Document and continue (recommended if non-critical)
2. Investigate further (may exceed time limit)
3. Skip this item (not recommended)

**Recommendation:** [AGENT'S SUGGESTION]

**Waiting for guidance or will auto-resolve in 5 minutes...**
```

---

## 🔄 Auto-Resolution Rules

### If user doesn't respond to blocker within 5 minutes:

**Agent 2 (Verification):**
- Document: "Test failed, needs investigation"
- Mark: Status ⚠️ (not ✅)
- Continue: Move to next action
- Note: Add to RELATED_ISSUES.md

**Agent 3 (Analysis):**
- Document: "Unable to determine root cause"
- Mark: Pattern severity UNKNOWN
- Continue: Move to next pattern
- Note: Flag for manual review

**Agent 4 (Fixing):**
- Document: "Pattern fix partially successful"
- Mark: Test pass rate (e.g., 28/30)
- Continue: Move to next pattern
- Note: Document failures in PATTERN_FIXES.md

---

## ✅ Success Indicators

**Agent is communicating properly when:**
- ✅ `.agent_status.json` updates after each action
- ✅ `AGENT_PROGRESS.md` shows milestone completions
- ✅ Milestone reports appear every ~60 min
- ✅ Blockers escalated within 15 min of getting stuck
- ✅ Checkpoints pause when specified
- ✅ User knows exactly what agent is doing

**Agent is NOT communicating when:**
- ❌ No updates for >60 min
- ❌ `.agent_status.json` stale
- ❌ No milestone reports
- ❌ Stuck but no escalation
- ❌ User has no idea what's happening

---

## 📁 Communication Files

```
.agent_status.json              ← Machine-readable (updated every action)
AGENT_PROGRESS.md               ← Human-readable (updated every milestone)
AGENT_[N]_HANDOFF.md            ← Created when agent complete
```

---

## 🎯 Implementation Checklist

**Each agent MUST:**
- [ ] Update `.agent_status.json` after every action
- [ ] Update `AGENT_PROGRESS.md` after every milestone
- [ ] Output milestone report after each checkpoint
- [ ] Escalate blockers after 15 min stuck
- [ ] Pause at specified PAUSE points
- [ ] Auto-resolve blockers if no response in 5 min
- [ ] Create handoff file when complete

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Define agent communication protocol
**Scope:** All agents (2, 3, 4)
