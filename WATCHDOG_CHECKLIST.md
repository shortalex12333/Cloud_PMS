# Watchdog Monitoring Checklist

**Quick reference for what watchdog checks and when**

---

## ⏱️ Every 5 Minutes

### Status File Check

```bash
cat .agent_status.json
```

**Verify:**
- [ ] File exists
- [ ] Last update < 90 min ago (Agent 2/3) or < 120 min ago (Agent 4)
- [ ] Status = "in_progress" or "complete"
- [ ] Current action matches expected sequence
- [ ] No blockers unaddressed

**Alert if:**
- ❌ File missing
- ❌ Stale (no update in >90/120 min)
- ❌ Invalid JSON
- ❌ Agent on wrong action

---

## ⏱️ Every 10 Minutes

### Progress Check

```bash
cat AGENT_PROGRESS.md
cat VERIFICATION_DASHBOARD.md
```

**Agent 2 - Verify:**
- [ ] Actions completed = expected for time elapsed
- [ ] 0-5 actions total (not more)
- [ ] Milestone reports appearing
- [ ] No action taking >90 min

**Agent 3 - Verify:**
- [ ] Checkpoints progressing (1 → 2 → 3)
- [ ] Each checkpoint <30 min
- [ ] PATTERN_ANALYSIS.md created after checkpoint 3

**Agent 4 - Verify:**
- [ ] Patterns being fixed OR actions being verified
- [ ] Progress reports every 10 actions (Phase 2)
- [ ] No pattern taking >8 hours

**Alert if:**
- ❌ Behind schedule
- ❌ Too many actions (Agent 2: >5)
- ❌ Same task for >90 min with no progress

---

### File Creation Check

```bash
ls -l _VERIFICATION/
```

**Agent 2 - Verify:**
- [ ] 0-5 verification files (verify_*.md)
- [ ] PHASE_1_FINDINGS.md (after 5 actions)
- [ ] RELATED_ISSUES.md created
- [ ] AGENT_2_HANDOFF.md (when complete)

**Agent 3 - Verify:**
- [ ] PATTERN_ANALYSIS.md exists
- [ ] AGENT_3_HANDOFF.md (when complete)

**Agent 4 - Verify:**
- [ ] PATTERN_FIXES.md exists
- [ ] 59 new verification files (64 total)
- [ ] MUTATION_PROOFS.md updated
- [ ] VERIFICATION_COMPLETE.md (when complete)

**Alert if:**
- ❌ Files missing for time elapsed
- ❌ Too many files (Agent 2: >5 verify files)
- ❌ Required files not created

---

## ⏱️ Every 30 Minutes

### Quality Check

**Re-read latest verification file:**

```bash
# Find most recent
LATEST=$(ls -t _VERIFICATION/verify_*.md | head -1)
cat "$LATEST"
```

**Verify:**
- [ ] No unfilled placeholders (`[PASTE`, `TODO`, `FILL IN`)
- [ ] 6 proofs section complete
- [ ] Gaps section has actual gaps listed
- [ ] Status marked (✅ or ⚠️)
- [ ] Time spent documented
- [ ] Actual query results pasted (not summaries)

**Alert if:**
- ❌ Templates unfilled
- ❌ Sections missing
- ❌ No gaps documented (suspicious)
- ❌ No actual query results shown

---

### Mission Compliance Check

**Agent 2 - Red flags:**

```bash
grep -i 'fix\|implement\|helper' AGENT_PROGRESS.md
```

- [ ] NOT trying to fix bugs
- [ ] NOT implementing solutions
- [ ] NOT creating helper functions
- [ ] ONLY verifying 5 actions

**Agent 3 - Red flags:**

```bash
grep -i 'implement\|apply.*fix\|create.*helper' AGENT_PROGRESS.md
ls _VERIFICATION/verify_update_*.md 2>/dev/null
```

- [ ] NOT implementing fixes
- [ ] NOT creating helpers
- [ ] NOT verifying actions

**Agent 4 - Red flags:**

```bash
# Check phase
grep '"phase"' .agent_status.json
ls _VERIFICATION/verify_*.md | wc -l
```

- [ ] NOT skipping pattern fixes
- [ ] NOT verifying before fixing patterns
- [ ] NOT verifying >64 actions

**Alert if:**
- 🚨 Agent working outside defined mission
- 🚨 Agent fixing when should observe (Agent 2/3)
- 🚨 Agent skipping required steps

---

## ⏱️ Every 1 Hour

### Detailed Verification

**Re-read all created files:**

```bash
# All verification files
for f in _VERIFICATION/verify_*.md; do
  # Check quality
  # Count placeholders
  # Verify completeness
done
```

**Agent 2 - After 1 hour:**
- [ ] At least 1 action verified
- [ ] Verification file complete
- [ ] Patterns emerging (document in progress)

**Agent 2 - After 5 hours:**
- [ ] 5 actions verified
- [ ] PHASE_1_FINDINGS.md complete
- [ ] 2+ patterns identified
- [ ] AGENT_2_HANDOFF.md exists

**Agent 3 - After 1 hour:**
- [ ] All 3 checkpoints complete
- [ ] PATTERN_ANALYSIS.md exists
- [ ] Patterns categorized by severity
- [ ] Fix approaches documented
- [ ] AGENT_3_HANDOFF.md exists

**Agent 4 - Every 4 hours:**
- [ ] Pattern fixed OR 10+ actions verified
- [ ] PATTERN_FIXES.md updated OR new verify files
- [ ] Progress report issued
- [ ] Tests run and documented

---

## 🎯 Success Criteria Verification

### When Agent Reports "Complete"

**Agent 2 Checklist:**
```bash
# Run all checks
./scripts/check_agent_2_success.sh  # (if script exists)

# Manual checks:
ls _VERIFICATION/verify_*.md | wc -l                    # = 5
test -f _VERIFICATION/PHASE_1_FINDINGS.md              # exists
grep -c "Pattern" _VERIFICATION/PHASE_1_FINDINGS.md   # >= 2
test -f _VERIFICATION/RELATED_ISSUES.md                # exists
test -f AGENT_2_HANDOFF.md                             # exists
grep '"status": "complete"' .agent_status.json         # true
grep '"phase": "1_COMPLETE"' .verification_context     # true
```

- [ ] 5 verification files ✅
- [ ] PHASE_1_FINDINGS.md ✅
- [ ] 2+ patterns identified ✅
- [ ] RELATED_ISSUES.md exists ✅
- [ ] AGENT_2_HANDOFF.md ✅
- [ ] Status = "complete" ✅
- [ ] Context = "1_COMPLETE" ✅

**ALL must be checked. If ANY unchecked → FAIL**

---

**Agent 3 Checklist:**
```bash
test -f _VERIFICATION/PATTERN_ANALYSIS.md              # exists
grep -c "HIGH SEVERITY" _VERIFICATION/PATTERN_ANALYSIS.md
grep -c "Fix approach:" _VERIFICATION/PATTERN_ANALYSIS.md
test -f AGENT_3_HANDOFF.md                             # exists
grep '"status": "complete"' .agent_status.json         # true
```

- [ ] PATTERN_ANALYSIS.md ✅
- [ ] Patterns categorized ✅
- [ ] Fix approaches documented ✅
- [ ] AGENT_3_HANDOFF.md ✅
- [ ] Status = "complete" ✅

**ALL must be checked. If ANY unchecked → FAIL**

---

**Agent 4 Checklist:**
```bash
test -f _VERIFICATION/PATTERN_FIXES.md                 # exists
ls _VERIFICATION/verify_*.md | wc -l                    # = 64
grep "64/64" _VERIFICATION/MUTATION_PROOFS.md          # exists
test -f VERIFICATION_COMPLETE.md                        # exists
grep '"status": "complete"' .agent_status.json         # true
```

- [ ] PATTERN_FIXES.md ✅
- [ ] 64 verification files ✅
- [ ] MUTATION_PROOFS.md shows 64/64 ✅
- [ ] VERIFICATION_COMPLETE.md ✅
- [ ] Status = "complete" ✅

**ALL must be checked. If ANY unchecked → FAIL**

---

## 🚨 Alert Thresholds

### CRITICAL (Immediate alert, stop monitoring)

- Status file stale >2 hours
- Agent clearly off-mission (fixing when shouldn't)
- File corruption (invalid JSON)
- Success criteria impossible to meet
- Agent creating wrong files

**Action:** Alert user, pause monitoring, wait for intervention

---

### WARNING (Monitor closely, alert if persists)

- Status file stale 90-120 min
- Action/pattern taking >90 min
- Quality issues in files
- Missing expected milestone
- Progress slower than expected

**Action:** Note in log, check again in 10 min, alert if still present

---

### INFO (Normal, log only)

- Status fresh
- Progress on track
- Files being created
- Quality checks passing
- Milestones reached

**Action:** Log, continue monitoring

---

## 📝 Watchdog Log Format

```markdown
### [TIME] - Check [N]
Status: ✅/⚠️/❌ [FRESH/STALE]
Progress: ✅/⚠️/❌ [ON TRACK/BEHIND/AHEAD]
Files: ✅/⚠️/❌ [COUNT/EXPECTED]
Quality: ✅/⚠️/❌ [PASS/ISSUES]
Mission: ✅/🚨 [COMPLIANT/OFF-MISSION]
Alerts: [NONE/LIST]
```

---

## ✅ Watchdog Completed When

**Agent reports complete AND all success criteria verified:**

1. Generate final report
2. Document total monitoring time
3. List all alerts (if any)
4. Assess overall quality
5. Recommend: PROCEED or REVIEW
6. STOP monitoring

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Quick monitoring checklist
**Used by:** Watchdog agent
