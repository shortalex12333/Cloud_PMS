# Quick Launch Guide

**Fast reference for launching the autonomous verification system**

---

## 🚀 RECOMMENDED: Resume Agent 2 (Complete Phase 1)

**Current Progress:** 1/5 actions verified
**Time Remaining:** ~4 hours
**Output:** PHASE_1_FINDINGS.md + AGENT_2_HANDOFF.md

### Step 1: Launch Agent 2

**Terminal 1:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste this file:** `AGENT_2_PROMPT.md`

### Step 2: Launch Watchdog (5 min later)

**Terminal 2:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
claude chat
```

**Paste this file:** `WATCHDOG_PROMPT.md`

---

## 📊 What You'll See

**Terminal 1:**
```
[14:00] Starting Action 2: assign_work_order
[14:55] 🎯 MILESTONE: Action 2 of 5 Complete
[15:00] Starting Action 3...
```

**Terminal 2:**
```
[14:05] 🔍 WATCHDOG STATUS - Check 1
        Status: ✅ Fresh
        Progress: ✅ On track (2/5)
```

---

## ✅ Success Indicators

- ✅ Milestone reports every ~60 min (Terminal 1)
- ✅ Watchdog status every 10 min (Terminal 2)
- ✅ Files created in `_VERIFICATION/`
- ✅ No CRITICAL alerts

---

## 🔍 Monitor Status (Third Terminal)

```bash
# Quick status
cat .agent_status.json

# Progress
cat AGENT_PROGRESS.md

# Watchdog log
cat .watchdog_log.md
```

---

## 🎯 Full Documentation

See `AUTONOMOUS_VERIFICATION_SYSTEM_READY.md` for complete details.
