# PHASE-BASED EXECUTION - MASTER FILE

**Read this first. Follow phases in order. Stop after each phase.**

---

## PREVIOUS CLAUDE FAILURES - DO NOT REPEAT

Previous Claude sessions failed by:
1. **TEST RIGGING** - Changed `expectedStatus` from 200 to 404/500 to make tests "pass"
2. **DATA DESTRUCTION** - Ran DELETE queries that destroyed real documents, shopping items
3. **FAKE DATA** - Used hardcoded fake UUIDs instead of querying real IDs
4. **INFINITE LOOPS** - Kept "fixing" tests indefinitely without stopping to report

**YOU MUST NOT:**
- Change expectedStatus to accept failures
- Delete any data you didn't create (use TEST_* prefix)
- Use fake UUIDs like '11111111-1111-...'
- Continue beyond 5 fix iterations without reporting

---

## THE 6 PHASES

```
PHASE 1: UNDERSTAND → Read, analyze, don't touch code
PHASE 2: MAP        → Trace relationships, identify gaps
PHASE 3: DESIGN     → Plan fixes before coding
PHASE 4: IMPLEMENT  → Execute the design
PHASE 5: TEST       → Run tests, fix issues
PHASE 6: REPORT     → Commit, push, verify CI
```

---

## CRITICAL RULES

1. **Complete one phase before starting next**
2. **Create the output file for each phase**
3. **STOP after each phase and wait for user approval**
4. **NEVER skip phases**
5. **NEVER change test expectations to accept failures**

---

## PHASE FILES

| Phase | Instruction File | Output File |
|-------|------------------|-------------|
| 1 | PHASE_1_UNDERSTAND.md | PHASE_1_REPORT.md |
| 2 | PHASE_2_MAP.md | PHASE_2_MAP.md (same) |
| 3 | PHASE_3_DESIGN.md | PHASE_3_DESIGN.md (same) |
| 4 | PHASE_4_IMPLEMENT.md | PHASE_4_CHANGES.md |
| 5 | PHASE_5_TEST.md | PHASE_5_RESULTS.md |
| 6 | PHASE_6_REPORT.md | PHASE_6_FINAL_REPORT.md |

---

## HOW TO START

Say to Claude:

```
Read /Users/celeste7/Documents/Cloud_PMS/PHASE_MASTER.md

Start Phase 1. Read PHASE_1_UNDERSTAND.md and execute.
Create PHASE_1_REPORT.md.
Stop when done and wait for approval.
```

---

## AFTER EACH PHASE

Claude will stop and say "Phase X complete. Ready for Phase Y."

You respond:
- "Approved. Continue to Phase Y." → Claude reads next phase file
- "Wait." → Claude waits
- "Explain [something]." → Claude explains
- "Redo Phase X." → Claude redoes

---

## KEY DIRECTORIES

```
Documentation (READ ONLY - specs):
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/

Code (READ/WRITE):
/Users/celeste7/Documents/Cloud_PMS/
```

---

## TEST CREDENTIALS & DATA

```
Email: x@alex-short.com
Password: Password2!
Test Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

**Supabase Tables with Test Data:**
- `pms_work_orders` - query for real work order IDs
- `documents` - DO NOT DELETE existing records
- `shopping_list` - DO NOT DELETE existing records
- `pms_task_templates` - use for equipment lookups

---

## SUCCESS CRITERIA

Phase 6 complete with:
- All tests passing locally
- GitHub CI green
- Final report created

---

## IF CLAUDE GOES OFF TRACK

Say: "Stop. Read PHASE_MASTER.md. You are in Phase X. Complete it properly."
