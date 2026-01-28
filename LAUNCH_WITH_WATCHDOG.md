# Launch Agents with Watchdog Monitoring

**Complete guide to launching working agent + watchdog in parallel**

---

## 🎯 Overview

**Two terminals running in parallel:**
1. **Terminal 1:** Working Agent (Agent 2, 3, or 4)
2. **Terminal 2:** Watchdog Agent (monitors Terminal 1)

---

## 🚀 Agent 2 Launch (With Watchdog)

### Terminal 1: Launch Agent 2

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste this prompt:**
```
[COPY ENTIRE CONTENTS OF: AGENT_2_PROMPT.md]
```

**You'll see:**
```
🎯 MILESTONE: Action 1 of 5 Complete
... (every 60 min)
```

---

### Terminal 2: Launch Watchdog

**Wait 5 minutes after Agent 2 starts, then:**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste this prompt:**
```
[COPY ENTIRE CONTENTS OF: WATCHDOG_PROMPT.md]
```

**You'll see:**
```
🔍 WATCHDOG STATUS - Check 1
... (every 10 min)
```

---

### What You'll See

**Terminal 1 (Agent 2):**
```
[14:00] Starting Action 1: create_work_order
[14:55] 🎯 MILESTONE: Action 1 of 5 Complete
[15:00] Starting Action 2: assign_work_order
[15:55] 🎯 MILESTONE: Action 2 of 5 Complete
...
[19:00] ⏸️  PAUSE - Type 'yes' to continue
```

**Terminal 2 (Watchdog):**
```
[14:05] 🔍 WATCHDOG STATUS - Check 1
        Status: ✅ Fresh
        Progress: ✅ On track

[14:15] 🔍 WATCHDOG STATUS - Check 2
        Status: ✅ Fresh
        Progress: ✅ On track

[15:05] 🔍 WATCHDOG STATUS - Check 7
        Status: ✅ Fresh
        Progress: ✅ 1/5 complete
        Files: ✅ 1 verification file

[19:05] 🎯 VERIFYING AGENT 2 SUCCESS CRITERIA
        ✅ 5 verification files
        ✅ PHASE_1_FINDINGS.md exists
        ✅ Patterns identified
        ✅ AGENT_2_HANDOFF.md exists

        AGENT 2 SUCCESS: PASS
        Ready for Agent 3: YES
```

---

## 📊 Monitoring During Execution

### Check Status Anytime

**In a third terminal:**

```bash
# Quick status
cat .agent_status.json

# Progress
cat AGENT_PROGRESS.md

# Watchdog log
cat .watchdog_log.md

# Dashboard
cat VERIFICATION_DASHBOARD.md
```

---

### What Watchdog Monitors

**Every 5 min:**
- Status file freshness

**Every 10 min:**
- Progress happening
- Files being created
- Status report output

**Every 30 min:**
- Quality check (re-reads files)
- Mission compliance check

**Every 1 hour:**
- Detailed verification
- Success criteria progress

---

### Watchdog Alerts

**If something wrong:**

**Terminal 2 shows:**
```
🚨 WATCHDOG ALERT 🚨

Issue: Action taking too long (95 min)
Expected: <60 min

Recommendation: Agent should move to next action

Monitoring...
```

**You can:**
- Let agent auto-resolve (wait 15 min)
- Type guidance in Terminal 1
- Stop agent if critical

---

## 🚀 Agent 3 Launch (With Watchdog)

### After Agent 2 Complete

**Terminal 1: Launch Agent 3**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste:** Contents of `AGENT_3_PROMPT.md`

---

**Terminal 2: Launch New Watchdog**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste:** Contents of `WATCHDOG_PROMPT.md`

**Watchdog will detect it's monitoring Agent 3 automatically.**

---

### What You'll See

**Terminal 1 (Agent 3):**
```
[14:15] 🎯 CHECKPOINT 1: Files Read & Summarized
[14:35] 🎯 CHECKPOINT 2: Patterns Categorized
[15:00] 🎯 CHECKPOINT 3: Fix Approaches Designed
[15:00] ⏸️  PAUSE - Type 'yes' to continue
```

**Terminal 2 (Watchdog):**
```
[14:20] 🔍 WATCHDOG STATUS - Check 1
        Monitoring: Agent 3
        Status: ✅ Fresh
        Progress: ✅ Checkpoint 1 complete

[14:40] 🔍 WATCHDOG STATUS - Check 3
        Status: ✅ Fresh
        Progress: ✅ Checkpoint 2 complete

[15:05] 🎯 VERIFYING AGENT 3 SUCCESS CRITERIA
        ✅ PATTERN_ANALYSIS.md exists
        ✅ Patterns categorized
        ✅ Fix approaches documented
        ✅ AGENT_3_HANDOFF.md exists

        AGENT 3 SUCCESS: PASS
        Ready for Agent 4: YES
```

---

## 🚀 Agent 4 Launch (With Watchdog)

### After Agent 3 Complete

**Terminal 1: Launch Agent 4**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste:** Contents of `AGENT_4_PROMPT.md`

---

**Terminal 2: Launch New Watchdog**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste:** Contents of `WATCHDOG_PROMPT.md`

**Watchdog will detect it's monitoring Agent 4 automatically.**

---

### What You'll See

**Terminal 1 (Agent 4):**
```
[DAY 1]
[10:00] 🎯 PATTERN FIXED: Missing Audit Logs
[13:00] 🎯 PATTERN FIXED: Missing Validation
[15:00] ⏸️  PAUSE - Type 'yes' to start Phase 2

[DAY 2]
[09:00] 🎯 PROGRESS: 10/64 actions verified
[10:00] 🎯 PROGRESS: 20/64 actions verified
...
[15:00] 🎯 PROGRESS: 59/64 actions verified
[15:00] ⏸️  PAUSE - Type 'yes' to finalize

[DAY 3]
[09:00] ✅✅✅ VERIFICATION SYSTEM COMPLETE ✅✅✅
```

**Terminal 2 (Watchdog):**
```
[10:10] 🔍 WATCHDOG STATUS - Check 1
        Monitoring: Agent 4
        Phase: fixing_patterns
        Status: ✅ Fresh

[13:10] 🔍 WATCHDOG STATUS - Check 19
        Status: ✅ Fresh
        Progress: ✅ 1 pattern fixed

[DAY 2]
[09:10] 🔍 WATCHDOG STATUS - Check 142
        Phase: verifying_actions
        Progress: ✅ 10/64 actions

[15:10] 🔍 WATCHDOG STATUS - Check 178
        Progress: ✅ 59/64 actions

[DAY 3]
[09:10] 🎯 VERIFYING AGENT 4 SUCCESS CRITERIA
        ✅ PATTERN_FIXES.md exists
        ✅ 64 verification files
        ✅ MUTATION_PROOFS.md shows 64/64
        ✅ VERIFICATION_COMPLETE.md exists

        AGENT 4 SUCCESS: PASS
        VERIFICATION SYSTEM: COMPLETE ✅
```

---

## 🔧 If Watchdog Detects Issue

### Example: Action Taking Too Long

**Watchdog output:**
```
🚨 WATCHDOG ALERT 🚨

Issue: Action taking too long
Action: create_work_order
Time: 95 minutes
Expected: <60 minutes

Recommendation: Document "needs investigation" and move to next action

Waiting for agent to auto-resolve in 15 min...
```

**Your options:**

**1. Let it auto-resolve (recommended):**
- Wait 15 min
- Agent will document and continue
- Watchdog resumes monitoring

**2. Manual intervention:**
- In Terminal 1, type guidance for agent
- Agent adjusts approach
- Watchdog resumes monitoring

**3. Stop if critical:**
- Stop agent
- Review issue
- Restart from last checkpoint

---

### Example: Agent Off-Mission

**Watchdog output:**
```
🚨🚨🚨 CRITICAL ALERT 🚨🚨🚨

Issue: OFF-MISSION BEHAVIOR DETECTED
Agent: Agent 2
Behavior: Trying to fix bugs (found "implement fix" in progress)

Expected: Agent 2 should only VERIFY, not FIX

Recommendation: STOP agent immediately

Monitoring paused. User intervention required.
```

**Your action:**
- Stop Agent 2 in Terminal 1
- Review AGENT_PROGRESS.md
- Restart Agent 2 with clear instructions
- Resume watchdog

---

## 📁 Files Created

**During execution:**
```
.agent_status.json              ← Working agent status (updated every action)
.watchdog_log.md                ← Watchdog monitoring log
AGENT_PROGRESS.md               ← Working agent progress
VERIFICATION_DASHBOARD.md       ← Overall dashboard (auto-updated)

_VERIFICATION/
  verify_*.md                   ← Verification files (created by agent)
  PHASE_1_FINDINGS.md           ← Agent 2 findings
  PATTERN_ANALYSIS.md           ← Agent 3 analysis
  PATTERN_FIXES.md              ← Agent 4 fixes

AGENT_[N]_HANDOFF.md            ← Handoff between agents
VERIFICATION_COMPLETE.md        ← Final report (Agent 4)
```

---

## ✅ Success Indicators

**System working correctly when:**

**Terminal 1 (Working Agent):**
- ✅ Milestone reports every ~60 min (Agent 2)
- ✅ Checkpoint reports every ~20 min (Agent 3)
- ✅ Progress reports every ~1-4 hours (Agent 4)
- ✅ Files being created
- ✅ Pauses at PAUSE points

**Terminal 2 (Watchdog):**
- ✅ Status reports every 10 min
- ✅ No critical alerts
- ✅ Quality checks passing
- ✅ Success criteria on track
- ✅ Final verification passes

**Both terminals:**
- ✅ Communication happening
- ✅ Progress visible
- ✅ Issues escalated if found
- ✅ User knows system status

---

## 🎯 Quick Reference

### Agent 2 + Watchdog

**Timeline:** 5 hours
**Terminal 1:** Agent 2 verifies 5 actions
**Terminal 2:** Watchdog checks every 10 min
**Output:** AGENT_2_HANDOFF.md + 5 verification files

---

### Agent 3 + Watchdog

**Timeline:** 1 hour
**Terminal 1:** Agent 3 analyzes patterns
**Terminal 2:** Watchdog checks every 10 min
**Output:** AGENT_3_HANDOFF.md + PATTERN_ANALYSIS.md

---

### Agent 4 + Watchdog

**Timeline:** 2-3 days
**Terminal 1:** Agent 4 fixes patterns + verifies 64 actions
**Terminal 2:** Watchdog checks every 10 min
**Output:** VERIFICATION_COMPLETE.md + 64 verification files

---

## 🚀 Start Now

### Step 1: Launch Agent 2

**Terminal 1:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && claude chat
```
Paste: `AGENT_2_PROMPT.md`

---

### Step 2: Launch Watchdog (5 min later)

**Terminal 2:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && claude chat
```
Paste: `WATCHDOG_PROMPT.md`

---

### Step 3: Monitor Both Terminals

**You'll see:**
- Terminal 1: Working agent progress
- Terminal 2: Watchdog status every 10 min

**You'll know:**
- Exactly what's happening
- If there are issues
- When agent is complete
- If success criteria met

---

## 📊 Expected Output Timeline

```
Terminal 1 (Agent 2)           Terminal 2 (Watchdog)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

14:00 Start Action 1
                               14:05 Status: Fresh ✅
                               14:15 Progress: On track ✅
                               14:25 Quality: OK ✅

15:00 MILESTONE: Action 1
                               15:05 Files: 1/5 ✅
                               15:15 Status: Fresh ✅

15:00 Start Action 2
                               15:25 Progress: On track ✅

16:00 MILESTONE: Action 2
                               16:05 Files: 2/5 ✅

... (continues for 5 hours)

19:00 MILESTONE: Action 5
19:00 PAUSE
                               19:05 VERIFYING SUCCESS ✅
                               19:05 ALL CRITERIA MET ✅
                               19:05 READY FOR AGENT 3 ✅

Type 'yes'
19:01 Creating handoff
19:01 COMPLETE
                               19:06 WATCHDOG COMPLETE ✅
```

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Complete launch guide with watchdog
**Ready:** Launch Agent 2 + Watchdog now
