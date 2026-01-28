# Launch Agents - Quick Reference

**How to launch each agent with full watchdog communication**

---

## 🚀 Quick Launch Commands

### Agent 2: Verification Operator (5 hours)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Then paste:** Contents of `AGENT_2_PROMPT.md`

**Expected output:**
- Milestone reports every 60 min
- Status updates after each action
- PAUSE before creating handoff (after 5 actions)

---

### Agent 3: Pattern Analyst (1 hour)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Then paste:** Contents of `AGENT_3_PROMPT.md`

**Expected output:**
- Checkpoint reports every 20 min
- PAUSE before creating handoff (after analysis complete)

---

### Agent 4: Bulk Fixer (2-3 days)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Then paste:** Contents of `AGENT_4_PROMPT.md`

**Expected output:**
- Pattern completion reports (every 2-4 hours)
- Progress reports every 10 actions (every ~1 hour)
- PAUSE before Phase 2 (after patterns fixed)
- PAUSE before completion (after 64 actions verified)

---

## 📊 Monitor Progress

### Real-Time Status

```bash
# Machine-readable status
cat .agent_status.json

# Human-readable progress
cat AGENT_PROGRESS.md

# Overall dashboard
cat VERIFICATION_DASHBOARD.md
```

### Watch for Updates

```bash
# Auto-refresh status every 10 seconds
watch -n 10 cat .agent_status.json

# Follow progress log
tail -f AGENT_PROGRESS.md
```

---

## 🎯 What to Expect

### Agent 2 Timeline

```
0:00  - Start Action 1
1:00  - 🎯 MILESTONE: Action 1 complete
1:00  - Start Action 2
2:00  - 🎯 MILESTONE: Action 2 complete
2:00  - Start Action 3
3:00  - 🎯 MILESTONE: Action 3 complete
3:00  - Start Action 4
4:00  - 🎯 MILESTONE: Action 4 complete
4:00  - Start Action 5
5:00  - 🎯 MILESTONE: Action 5 complete
5:00  - ⏸️  PAUSE - Type 'yes' to continue
5:00  - Create AGENT_2_HANDOFF.md
5:00  - ✅ STOP
```

### Agent 3 Timeline

```
0:00  - Read files
0:15  - 🎯 CHECKPOINT 1: Files read
0:15  - Categorize patterns
0:35  - 🎯 CHECKPOINT 2: Patterns categorized
0:35  - Design fixes
1:00  - 🎯 CHECKPOINT 3: Fixes designed
1:00  - ⏸️  PAUSE - Type 'yes' to continue
1:00  - Create AGENT_3_HANDOFF.md
1:00  - ✅ STOP
```

### Agent 4 Timeline

```
DAY 1:
0:00  - Start Pattern 1
2:00  - 🎯 PATTERN FIXED: Pattern 1
2:00  - Start Pattern 2
5:00  - 🎯 PATTERN FIXED: Pattern 2
5:00  - Start Pattern 3
7:00  - 🎯 PATTERN FIXED: Pattern 3
7:00  - ⏸️  PAUSE - Type 'yes' to start Phase 2

DAY 2:
0:00  - Start Phase 2 (verify actions)
1:00  - 🎯 PROGRESS: 10/64 actions
2:00  - 🎯 PROGRESS: 20/64 actions
3:00  - 🎯 PROGRESS: 30/64 actions
4:00  - 🎯 PROGRESS: 40/64 actions
5:00  - 🎯 PROGRESS: 50/64 actions
6:00  - 🎯 PROGRESS: 59/64 actions
6:00  - ⏸️  PAUSE - Type 'yes' to finalize

DAY 3:
0:00  - Create VERIFICATION_COMPLETE.md
0:00  - ✅ STOP
```

---

## 🚨 If Agent Gets Stuck

**You'll see:**
```
🚨 BLOCKER ESCALATION 🚨

Agent: Agent [N]
Time stuck: 20 minutes
Problem: [Description]

Auto-resolving in 5 minutes...
```

**Your options:**
1. **Wait 5 min** - Agent will auto-resolve and continue
2. **Type guidance** - Give specific instructions
3. **Type 'continue'** - Agent documents issue and moves on

**Agent will NOT stop - it will document and continue.**

---

## ⏸️ At Pause Points

**You'll see:**
```
⏸️  PAUSE - Waiting for user confirmation to proceed...

Should I [next step]?

Type 'yes' to continue or provide feedback.
```

**Your options:**
1. **Type 'yes'** - Agent continues
2. **Type feedback** - Agent adjusts approach
3. **Type 'stop'** - Agent creates handoff and stops

**Agent WAITS at pause points - will not proceed without confirmation.**

---

## 📁 Key Files

### Read These First
- `AGENT_COMMUNICATION_PROTOCOL.md` - How agents communicate
- `WATCHDOG_SYSTEM_COMPLETE.md` - Complete watchdog overview
- `AGENT_[N]_PROMPT.md` - Enhanced prompts for each agent

### Monitor These During Execution
- `.agent_status.json` - Current status (machine-readable)
- `AGENT_PROGRESS.md` - Milestones completed (human-readable)
- `VERIFICATION_DASHBOARD.md` - Overall progress

### Created by Agents
- `AGENT_2_HANDOFF.md` - Agent 2 → Agent 3
- `AGENT_3_HANDOFF.md` - Agent 3 → Agent 4
- `VERIFICATION_COMPLETE.md` - Final report (Agent 4)

---

## ✅ Success Checklist

### Agent 2 Complete When:
- [ ] 5 verification files created
- [ ] AGENT_2_HANDOFF.md exists
- [ ] PHASE_1_FINDINGS.md shows patterns
- [ ] .agent_status.json shows "status": "complete"

### Agent 3 Complete When:
- [ ] PATTERN_ANALYSIS.md created
- [ ] AGENT_3_HANDOFF.md exists
- [ ] All patterns categorized and prioritized
- [ ] .agent_status.json shows "status": "complete"

### Agent 4 Complete When:
- [ ] PATTERN_FIXES.md complete
- [ ] VERIFICATION_COMPLETE.md exists
- [ ] MUTATION_PROOFS.md shows 64/64
- [ ] .agent_status.json shows "status": "complete"

---

## 🎯 Timeline Summary

```
Agent 1 (Orchestrator): 2 hours     ✅ DONE
  ↓
Agent 2 (Verification): 5 hours     ⏳ Ready to launch
  ↓
Agent 3 (Analysis): 1 hour          ⏸️ After Agent 2
  ↓
Agent 4 (Bulk Fixer): 2-3 days      ⏸️ After Agent 3
  ↓
COMPLETE ✅
```

---

## 🚀 Start Now

**Copy this command:**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && claude chat
```

**Then open and copy contents of:**
```
AGENT_2_PROMPT.md
```

**Paste into Claude and press Enter.**

**You'll see the first status update within 1 minute.**

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Quick launch reference with watchdog
**Next:** Launch Agent 2
