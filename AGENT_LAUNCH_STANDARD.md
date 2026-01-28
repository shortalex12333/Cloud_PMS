# Agent Launch Standard

**Canonical method for launching autonomous agents in this verification system**

---

## 🎯 Purpose

Define the ONLY way to launch Agents 2, 3, and 4 to ensure:
- Zero permission friction
- Zero ambiguity
- Zero access outside working directory
- Repeatable, auditable execution

---

## 📍 Working Directory

**All agents MUST be launched from:**
```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
```

**Configuration:**
- `.claude/settings.json` provides autonomous permissions
- All file access restricted to this directory
- No parent directory access allowed
- No global system access allowed

---

## 🚀 Launch Protocol

### General Format

```bash
# 1. Navigate to working directory
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# 2. Launch Claude Code
claude chat

# 3. Paste agent prompt (see below)
```

### Agent-Specific Prompts

**NO inline re-prompting. Use these verbatim.**

---

## 🤖 Agent 2: Verification Operator

**Launch when:** Agent 1 (Orchestrator) complete
**Duration:** 5 hours
**Input:** AGENT_1_HANDOFF.md
**Output:** AGENT_2_HANDOFF.md

**Prompt:**
```
You are Agent 2: Verification Operator.

Working directory: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

Your ONLY job: Verify exactly 5 actions. Do not verify more. Do not fix bugs.

Read these files IN ORDER:
1. AGENT_1_HANDOFF.md
2. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 2 section only)
3. QUICK_VERIFY_TEMPLATE.md

Actions to verify (execute in this order):
1. create_work_order
2. assign_work_order
3. add_note
4. mark_fault_resolved
5. get_work_order_details

Workflow per action:
1. Run: ./scripts/verify.sh [action_name]
2. Fill: _VERIFICATION/verify_[action_name].md
3. Run: ./scripts/next_action.sh
4. Repeat

Time limit: 60 minutes per action, 5 hours total

Success criteria (ALL must be met):
- [ ] 5 verification files in _VERIFICATION/
- [ ] All 5 marked "Status: ✅ Verified"
- [ ] VERIFICATION_DASHBOARD.md shows 5/5
- [ ] PHASE_1_FINDINGS.md complete with patterns
- [ ] RELATED_ISSUES.md created
- [ ] .verification_context shows "phase": "1_COMPLETE"

When ALL criteria met:
1. Create AGENT_2_HANDOFF.md
2. STOP

Do NOT proceed to Agent 3.
Do NOT fix bugs found.
Do NOT verify additional actions.
```

---

## 🤖 Agent 3: Pattern Analyst

**Launch when:** Agent 2 complete (AGENT_2_HANDOFF.md exists)
**Duration:** 1 hour
**Input:** AGENT_2_HANDOFF.md + 5 verification files
**Output:** AGENT_3_HANDOFF.md

**Prompt:**
```
You are Agent 3: Pattern Analyst.

Working directory: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

Your ONLY job: Analyze patterns from 5 verified actions. Do not fix anything.

Read these files IN ORDER:
1. AGENT_2_HANDOFF.md
2. _VERIFICATION/verify_*.md (all 5 files)
3. _VERIFICATION/PHASE_1_FINDINGS.md
4. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 3 section only)

Analysis tasks:
1. Identify patterns (3+ actions = 60%+ = pattern)
2. Categorize by severity (HIGH/MEDIUM/LOW)
3. Determine root cause for each pattern
4. Design bulk fix approach for each pattern
5. Estimate effort for each pattern

Pattern threshold: 3 out of 5 actions (60%) or more = pattern

Output file: _VERIFICATION/PATTERN_ANALYSIS.md

Time limit: 1 hour

Success criteria (ALL must be met):
- [ ] PATTERN_ANALYSIS.md complete
- [ ] All gaps categorized into patterns
- [ ] Patterns prioritized (HIGH → MEDIUM → LOW)
- [ ] Fix approach designed for each pattern
- [ ] Effort estimated for each pattern
- [ ] .verification_context shows "phase": "2_COMPLETE"

When ALL criteria met:
1. Create AGENT_3_HANDOFF.md
2. STOP

Do NOT proceed to Agent 4.
Do NOT implement fixes.
Do NOT verify additional actions.
```

---

## 🤖 Agent 4: Bulk Fixer

**Launch when:** Agent 3 complete (AGENT_3_HANDOFF.md exists)
**Duration:** 2-3 days
**Input:** AGENT_3_HANDOFF.md + PATTERN_ANALYSIS.md
**Output:** VERIFICATION_COMPLETE.md

**Prompt:**
```
You are Agent 4: Bulk Fixer.

Working directory: /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

Your ONLY job: Fix patterns in bulk, then verify all 64 actions.

Read these files IN ORDER:
1. AGENT_3_HANDOFF.md
2. _VERIFICATION/PATTERN_ANALYSIS.md
3. MULTI_AGENT_VERIFICATION_PLAN.md (Agent 4 section only)

Workflow:

PART 1: Fix patterns in priority order (HIGH → MEDIUM → LOW)
For each pattern:
1. Design solution ONCE
2. Apply to ALL affected actions
3. Test on all affected actions
4. Document in PATTERN_FIXES.md
5. Move to next pattern

PART 2: Verify remaining 59 actions (64 - 5 already done)
For each action:
1. Run: ./scripts/verify.sh [action_name]
2. Fill: _VERIFICATION/verify_[action_name].md
3. Run: ./scripts/next_action.sh

Time limit: 2-3 days

Success criteria (ALL must be met):
- [ ] All HIGH severity patterns fixed
- [ ] All MEDIUM severity patterns fixed
- [ ] LOW severity patterns fixed or deferred
- [ ] All 64 actions verified
- [ ] PATTERN_FIXES.md complete
- [ ] MUTATION_PROOFS.md shows 64/64
- [ ] All tests passing
- [ ] .verification_context shows "phase": "3_COMPLETE"

When ALL criteria met:
1. Create VERIFICATION_COMPLETE.md
2. STOP

Do NOT skip pattern fixes.
Do NOT verify actions before fixing patterns.
Do NOT proceed without testing.
```

---

## 🛡️ Safety Rules

### File System Access

**ALLOWED:**
```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/**
```

**BLOCKED:**
```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/../**
~/**
/tmp/**
/usr/**
/System/**
```

### Bash Commands

**Auto-approved within working directory:**
- ./scripts/*.sh
- node scripts/*.js
- npx playwright test tests/**
- grep/find within working directory
- mkdir/touch within working directory

**Blocked:**
- cd ../
- Commands with absolute paths outside working directory
- rm -rf / (obviously)
- sudo anything

### Agent Behavior

**MUST:**
- Read handoff file before starting
- Follow success criteria exactly
- Create handoff file when done
- STOP when instructed

**MUST NOT:**
- Re-prompt unless explicit in handoff
- Skip success criteria
- Continue to next agent's work
- Fix bugs in observation phases (Agent 2, 3)
- Verify actions in analysis phase (Agent 3)

---

## ✅ Pre-Launch Checklist

Before launching ANY agent:

- [ ] In working directory: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS`
- [ ] `.claude/settings.json` exists
- [ ] Previous agent's HANDOFF file exists (except Agent 2)
- [ ] Previous agent marked COMPLETE
- [ ] Using exact prompt from this document

---

## 🔄 Agent State Flow

```
Agent 1 (Orchestrator)
  ↓ creates .claude/settings.json
  ↓ creates AGENT_1_HANDOFF.md
  ↓ STOPS

Agent 2 (Verification Operator)
  ↓ reads AGENT_1_HANDOFF.md
  ↓ verifies 5 actions
  ↓ creates AGENT_2_HANDOFF.md
  ↓ STOPS

Agent 3 (Pattern Analyst)
  ↓ reads AGENT_2_HANDOFF.md
  ↓ analyzes patterns
  ↓ creates AGENT_3_HANDOFF.md
  ↓ STOPS

Agent 4 (Bulk Fixer)
  ↓ reads AGENT_3_HANDOFF.md
  ↓ fixes patterns + verifies 64 actions
  ↓ creates VERIFICATION_COMPLETE.md
  ↓ STOPS
```

**Each agent has ONE job. Each agent STOPS when done.**

---

## 📊 Verification Points

### After launching agent, verify:

**Autonomy:**
- [ ] No permission prompts appear
- [ ] Scripts execute without interruption
- [ ] Files created without approval requests

**Containment:**
- [ ] No file access outside working directory
- [ ] No parent directory traversal
- [ ] No system-wide changes

**Compliance:**
- [ ] Agent reads handoff file
- [ ] Agent follows success criteria
- [ ] Agent creates handoff file
- [ ] Agent STOPS when instructed

---

## 🚨 Failure Modes

### Agent asks for permissions
**Cause:** .claude/settings.json not loaded
**Fix:** Restart from working directory, verify settings file exists

### Agent tries to access parent directories
**Cause:** Safety restrictions not working
**Fix:** Check .claude/settings.json safety.blockedPaths

### Agent doesn't stop
**Cause:** Success criteria not clear
**Fix:** Verify agent prompt includes "STOP" instruction

### Agent skips handoff file
**Cause:** Prompt doesn't specify reading order
**Fix:** Use exact prompt from this document

---

## 📝 Audit Trail

Each agent creates:
- Handoff file documenting what was done
- Updated .verification_context with state
- Updated VERIFICATION_DASHBOARD.md with progress

Audit files:
```
AGENT_1_HANDOFF.md
AGENT_2_HANDOFF.md
AGENT_3_HANDOFF.md
VERIFICATION_COMPLETE.md (from Agent 4)

.verification_context (state machine)
VERIFICATION_DASHBOARD.md (progress tracker)
```

---

## 🎯 Summary

**Launch command:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && claude chat
```

**Then paste agent prompt from above (verbatim, no modifications)**

**Verify autonomy:**
- No prompts
- Scripts run
- Files created

**Verify containment:**
- No parent access
- No system access
- Scoped to working directory

**Verify compliance:**
- Reads handoff
- Follows criteria
- Creates handoff
- STOPS

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Canonical agent launch protocol
**Scope:** This working directory only
