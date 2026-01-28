# Agent 1 → Agent 2 Handoff

**From:** Agent 1 (Setup Engineer)
**To:** Agent 2 (Verification Operator)
**Date:** [FILL IN]
**Status:** ✅ Ready for Agent 2

---

## 🎯 What I Did (Agent 1)

Created complete automation for verification process:

### Files Created

1. **scripts/verify.sh** - Main automation script
   - Finds handler line number automatically
   - Finds test file automatically
   - Creates verification file from template
   - Pre-fills action name, handler line, test file
   - Runs test and shows result
   - Updates context and dashboard

2. **scripts/next_action.sh** - Advance to next action
   - Saves progress
   - Updates dashboard
   - Shows next action to verify
   - Detects when Phase 1 complete (5/5 actions)

3. **scripts/update_dashboard.sh** - Dashboard auto-updater
   - Called by verify.sh and next_action.sh
   - Updates VERIFICATION_DASHBOARD.md with current progress
   - Shows phase, progress, next steps

4. **QUICK_VERIFY_TEMPLATE.md** - Simplified 30-line template
   - 6 proofs section (not 215 checkpoints)
   - Error cases section
   - Gaps found section
   - Takes ~60 min to fill vs 3+ hours for old template

5. **VERIFICATION_DASHBOARD.md** - Single source of truth
   - Shows current phase
   - Shows actions verified
   - Shows next action
   - Auto-updated by scripts

6. **scripts/verification_helpers.js** - Database query utilities
   - get-entity: Query entity by ID
   - get-audit: Query audit log
   - count: Count entities with filters
   - list-tables: List all PMS tables

### Tested

✅ Ran `./scripts/verify.sh create_work_order`
✅ Script found handler at line 1847
✅ Script found test file
✅ Script created verification file
✅ Template pre-filled with action name
✅ Dashboard updated

---

## 🚀 Your Job (Agent 2)

**Verify exactly 5 actions, no more, no less.**

### Actions to Verify (In Order)

1. `create_work_order`
2. `assign_work_order`
3. `add_note`
4. `mark_fault_resolved`
5. `get_work_order_details`

### Process for Each Action (60 min max)

```bash
# 1. Start verification
./scripts/verify.sh [action_name]

# Script will:
# - Find handler
# - Find test
# - Run test
# - Create verification file
# - Update dashboard

# 2. Fill in verification file
# Open: _VERIFICATION/verify_[action_name].md
# Fill in:
# - 6 proofs (paste actual query results)
# - Error cases (tested? Y/N)
# - Gaps found (list)
# - Time spent

# 3. Advance to next action
./scripts/next_action.sh

# Script will:
# - Save progress
# - Update dashboard
# - Show next action

# 4. Repeat for next action
```

### What to Document

**For EACH action, fill in the verification file with:**

1. **6 Proofs** - Paste ACTUAL query results, not "it works"
   - HTTP 200? [PASTE RESPONSE]
   - Entity ID? [PASTE ID]
   - DB row exists? [PASTE QUERY RESULT]
   - DB row correct? [LIST VALUES]
   - Audit log exists? [PASTE QUERY RESULT OR "MISSING"]
   - Audit log correct? [LIST VALUES OR "N/A"]

2. **Error Cases** - Actually test them
   - 400 invalid input? [TESTED: Y/N]
   - 404 not found? [TESTED: Y/N]
   - 403 wrong yacht? [TESTED: Y/N]

3. **Gaps Found** - List ALL gaps/issues
   - Missing audit log?
   - Missing validation?
   - No RLS test?
   - Other issues?

### Database Query Helpers

Use the helper script for queries:

```bash
# Get entity
node scripts/verification_helpers.js get-entity pms_work_orders [entity_id]

# Get audit log
node scripts/verification_helpers.js get-audit create_work_order [entity_id]

# Count entities
node scripts/verification_helpers.js count pms_work_orders

# List all tables
node scripts/verification_helpers.js list-tables
```

---

## ⚠️ Important Rules

### DO:
- ✅ Verify ONE action at a time
- ✅ Set 60-minute timer per action
- ✅ Paste ACTUAL query results (don't say "it works")
- ✅ Document gaps without fixing them
- ✅ Use `./next_action.sh` to advance
- ✅ Stop after 5 actions (Phase 1 complete)

### DON'T:
- ❌ Fix any bugs found
- ❌ Verify more than 5 actions
- ❌ Spend more than 60 min per action
- ❌ Skip verification file sections
- ❌ Trust HTTP 200 without checking database

---

## 📋 Success Criteria

You're DONE with Agent 2 when:

- [ ] 5 verification files created (_VERIFICATION/verify_*.md)
- [ ] All 5 marked "Status: ✅ Verified" in files
- [ ] VERIFICATION_DASHBOARD.md shows 5/5 complete
- [ ] PHASE_1_FINDINGS.md summarizes all findings
- [ ] At least 2 patterns identified (e.g., "4/5 missing audit")
- [ ] RELATED_ISSUES.md has any side issues
- [ ] Total time: ~5 hours
- [ ] `.verification_context` shows phase: "1_COMPLETE"

---

## 📁 Files You'll Create

```
_VERIFICATION/
├── verify_create_work_order.md         ← Action 1
├── verify_assign_work_order.md         ← Action 2
├── verify_add_note.md                  ← Action 3
├── verify_mark_fault_resolved.md       ← Action 4
├── verify_get_work_order_details.md    ← Action 5
├── PHASE_1_FINDINGS.md                 ← Summary
└── RELATED_ISSUES.md                   ← Side issues
```

---

## 🎯 Quick Start

**Run this NOW:**

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start first action
./scripts/verify.sh create_work_order

# Follow the prompts
# Fill in verification file
# Run next_action.sh when done
```

---

## 📊 Expected Timeline

- Action 1 (create_work_order): 60 min
- Action 2 (assign_work_order): 60 min
- Action 3 (add_note): 60 min
- Action 4 (mark_fault_resolved): 60 min
- Action 5 (get_work_order_details): 60 min
- **Total: 5 hours**

---

## 🔗 References

**Read these:**
- MULTI_AGENT_VERIFICATION_PLAN.md (Agent 2 section)
- VERIFICATION_METHODOLOGY.md (10-step protocol)
- TESTING_STANDARDS.md (what is success)
- QUICK_REFERENCE.md (database query examples)

**Fill these:**
- QUICK_VERIFY_TEMPLATE.md (copy for each action)
- PHASE_1_FINDINGS.md (summary after 5 actions)
- RELATED_ISSUES.md (side issues found)

---

## 💡 Pro Tips

1. **Use the automation** - Don't manually create files
2. **Set timer** - 60 min per action, hard stop
3. **Paste results** - Don't summarize, show actual output
4. **Document gaps** - Don't fix them yet
5. **One at a time** - Close all files except current verification

---

## 🚨 If You Get Stuck

**Problem:** Script won't run
**Solution:** `chmod +x scripts/*.sh` to make executable

**Problem:** Can't find handler
**Solution:** Check script output for line number

**Problem:** Test failing
**Solution:** OK! Document failure, don't investigate >15 min

**Problem:** Found bug in other action
**Solution:** Write in RELATED_ISSUES.md, stay focused on current

**Problem:** Going over 60 min
**Solution:** STOP. Document "needs more investigation" and move on

---

## ✅ When You're Done

Create **AGENT_2_HANDOFF.md** with:
- Summary of 5 actions verified
- Patterns identified (e.g., "4/5 missing audit logs")
- Common gaps found
- Estimated scope for each pattern
- Instructions for Agent 3 (Pattern Analyst)

Then STOP. Don't verify more actions. Don't fix bugs. Hand off to Agent 3.

---

**Agent 1 Status:** ✅ Complete
**Agent 2 Status:** ⏳ Ready to start
**Next Agent:** Agent 3 (Pattern Analyst) - after Agent 2 complete

**Good luck! 🚀**
