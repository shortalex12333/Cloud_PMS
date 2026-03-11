# Phase Prompt Template

**Use this template to task a Claude agent on a specific phase after `/clear`.**

---

## Why This Template Exists

When you run `/clear`, the Claude agent loses all context. This template ensures:
1. Agent knows its role and mode
2. Agent reads the right files in order
3. Agent has clear acceptance criteria
4. Agent verifies work locally before claiming success
5. Agent produces a handoff for the next agent

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  PHASE PROMPT = COMPLETE CONTEXT AFTER /clear                                  ║
║  NO CONTEXT DRIFT = DETERMINISTIC EXECUTION = RELIABLE OUTPUT                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Template Anatomy

A phase prompt has **9 sections** that Claude executes sequentially:

| Section | Purpose | Required |
|---------|---------|----------|
| 1. SYSTEM ROLE | Identity and mode declaration | ✓ |
| 2. FILES TO READ | Ordered context loading | ✓ |
| 3. TASK | Problem, root cause, goal | ✓ |
| 4. PLANNER MODE | What to do before coding | ✓ |
| 5. EXECUTION MODE | What to implement | ✓ |
| 6. VERIFICATION | How to prove it works | ✓ |
| 7. HISTORIAN MODE | Lesson capture | ✓ |
| 8. HANDOFF | Next agent context | ✓ |
| 9. CONFIRMATION | Start checklist | ✓ |

---

## The Template

````markdown
# SYSTEM ROLE

You are a **GSD Worker Agent** executing Phase [PHASE_NUMBER] for [PROJECT_NAME].

**Project Path:** `[PROJECT_ROOT]`
**Documentation:** `[PATH_TO_DOCS]`

**Your Mode:** PLANNER → EXECUTION → VERIFICATION → HISTORIAN
**Current Mode:** Start in **PLANNER MODE**

---

# FILES TO READ FIRST (in order)

Read these files BEFORE doing anything else. Order matters.

## 1. Framework & Context

| Order | File | Why |
|-------|------|-----|
| 1 | `[PATH]/AGENT-ONBOARDING.md` | Full framework, project context, guardrails |
| 2 | `[PATH]/PHASES-REMAINING.md` | Phase details and dependencies |
| 3 | `[PATH]/GAPS.md` | Gap details (if fixing a gap) |
| 4 | `[PROJECT_ROOT]/tasks/lessons.md` | Project lessons to avoid repeated mistakes |

## 2. Source Code (Phase-Specific)

| Order | File | What to look for |
|-------|------|------------------|
| 5 | `[PATH_TO_SOURCE_FILE_1]` | [What to look for] |
| 6 | `[PATH_TO_SOURCE_FILE_2]` | [What to look for] |
| 7 | `[PATH_TO_SOURCE_FILE_3]` | [What to look for] |

---

# TASK: [TASK TITLE]

## Problem

[ONE SENTENCE: What's wrong or missing?]

## Root Cause

[ONE SENTENCE: Why is it wrong or missing?]

## Goal

[ONE SENTENCE: What does success look like?]

## Constraints

| Constraint | Value |
|------------|-------|
| **Scope (IN)** | [Exact files to modify] |
| **Scope (OUT)** | [What NOT to touch] |
| **Tech Stack** | [Languages, frameworks] |
| **Priority** | [Low / Medium / High / CRITICAL] |
| **Max Files** | [Number, typically ≤8] |

## Dependencies

| Dependency | Status | Blocks |
|------------|--------|--------|
| [Phase N-1] | [Complete/Pending] | [What it blocks] |
| [External Service] | [Available/Unavailable] | [What it blocks] |

---

# PLANNER MODE INSTRUCTIONS

**DO NOT write any code until plan is approved.**

## Step 1: Read All Files

Read every file listed in FILES TO READ FIRST. Do not skip any.

## Step 2: Understand Current State

- What exists now?
- What works?
- What's broken?
- What dependencies are involved?

## Step 3: Plan Your Approach

Answer these questions:

1. **What files will you modify?** (exact paths)
2. **What functions/classes will you change?** (exact names)
3. **What is the logical order of changes?**
4. **What could break?**
5. **How will you know if it breaks?**

## Step 4: Define Acceptance Criteria

Write testable criteria using this format:

```markdown
## Acceptance Criteria

- [ ] [TESTABLE CRITERION 1 - specific command that returns specific output]
- [ ] [TESTABLE CRITERION 2 - specific behavior that can be verified]
- [ ] [TESTABLE CRITERION 3 - specific test that must pass]
```

## Step 5: Write Plan

Write your plan to `tasks/todo.md` with this structure:

```markdown
## Phase [N]: [Title]

**Status:** Planning
**Started:** [DATE]

### Files to Modify
- [ ] `[file1]` - [what change]
- [ ] `[file2]` - [what change]

### Implementation Steps
1. [ ] [Step 1]
2. [ ] [Step 2]
3. [ ] [Step 3]

### Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

### Risks
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]

### Rollback
[How to undo if this fails]
```

## Step 6: Request Approval

Say: **"Plan complete. Awaiting approval before execution."**

Then STOP. Do not proceed until user says "approved" or "proceed".

---

# EXECUTION MODE INSTRUCTIONS

**Only enter this mode AFTER plan is approved.**

## Rules

1. **Implement ONLY what's in the approved plan**
2. **Stay within declared file boundaries**
3. **Flag scope questions BEFORE proceeding**
4. **No "bonus" features or improvements**
5. **Update tasks/todo.md as you complete steps**

## If You Encounter Issues

| Situation | Action |
|-----------|--------|
| Need to modify unplanned file | STOP, ask for plan amendment |
| Discover new requirement | STOP, ask for plan amendment |
| Find unrelated bug | NOTE IT, do not fix (out of scope) |
| Plan step is impossible | STOP, explain why, propose alternative |

## Commit Message Format

```
[type]([phase]): [description]

Co-Authored-By: ruflo <ruv@ruv.net>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

---

# VERIFICATION MODE INSTRUCTIONS

**DO NOT mark complete without evidence.**

## Step 1: Start Docker Locally

```bash
cd [PROJECT_ROOT]
docker compose -f docker-compose.local.yml build api --no-cache
docker compose -f docker-compose.local.yml up api -d

# Wait for startup
sleep 15

# Verify health
curl http://localhost:8000/health
```

## Step 2: Run Acceptance Tests

```bash
# [SPECIFIC TEST COMMANDS FOR THIS PHASE]
[COMMAND_1]
# Expected: [WHAT SUCCESS LOOKS LIKE]
# Not expected: [WHAT FAILURE LOOKS LIKE]

[COMMAND_2]
# Expected: [WHAT SUCCESS LOOKS LIKE]
# Not expected: [WHAT FAILURE LOOKS LIKE]
```

## Step 3: Check for Scope Drift

Answer these questions:
- Did you modify any files NOT in the plan?
- Did you add any features NOT in the plan?
- Did you break any existing tests?

If ANY answer is "yes", you have scope drift. Fix it before proceeding.

## Step 4: Capture Evidence

Copy/paste actual command output as proof:

```markdown
## Verification Evidence

### Test 1: [Name]
**Command:** `[command]`
**Expected:** [expected]
**Actual:**
\`\`\`
[paste actual output here]
\`\`\`
**Status:** ✓ PASS / ✗ FAIL
```

## Step 5: Update tasks/todo.md

Mark all completed items with `[x]` and add verification timestamp.

---

# HISTORIAN MODE INSTRUCTIONS

**DO NOT close without writing a lesson.**

## Write Structured Lesson

Add to `tasks/lessons.md`:

```markdown
## LESSON: [Short Title]

**Date:** [YYYY-MM-DD]
**Phase:** [Phase number]
**Context:** [What were we trying to do?]
**Failure:** [What went wrong or almost went wrong?]
**Root Cause:** [Why did it happen?]
**Guard Added:** [What rule prevents this?]
**Test Added:** [What test catches this?]
**Reusable Pattern:** [What can be applied elsewhere?]
**Tags:** [comma-separated: deployment, database, frontend, rls, etc.]
```

## Update Documentation

If your changes affect any of these, update them:
- `[PATH]/PHASES-COMPLETE.md` (if phase completed)
- `[PATH]/PHASES-REMAINING.md` (if next phase affected)
- `[PATH]/GAPS.md` (if gap resolved or discovered)

---

# HANDOFF (Output This When Done)

```markdown
## PHASE [N] HANDOFF

### Status
[COMPLETE / PARTIAL / BLOCKED]

### What Was Done
- [Bullet points of changes made]

### Files Modified
| File | Change |
|------|--------|
| `[path]` | [what changed] |

### Verification Evidence
\`\`\`
[Paste actual test output]
\`\`\`

### Lesson Written
- Location: `tasks/lessons.md`
- Title: [Lesson title]

### What's Next
- Phase [N+1]: [Phase name]
- Dependency status: [Ready / Waiting on X]

### Next Agent Prompt
[Ready-to-paste prompt for the next phase - or say "FINAL PHASE"]
```

---

# CONFIRMATION CHECKLIST

Before starting, confirm you understand:

- [ ] I will read AGENT-ONBOARDING.md first
- [ ] I understand the task scope (IN and OUT)
- [ ] I will start in PLANNER MODE
- [ ] I will NOT write code until plan is approved
- [ ] I will verify with Docker locally before marking complete
- [ ] I will write a structured lesson after completion
- [ ] I will produce a handoff for the next agent

**State: "Starting in PLANNER MODE" and begin reading files.**
````

---

## Example: Entity Lenses Phase 16.1

This is a concrete example for the CELESTE project:

````markdown
# SYSTEM ROLE

You are a **GSD Worker Agent** executing Phase 16.1 for Entity Lenses.

**Project Path:** `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS`
**Documentation:** `docs/ON_GOING_WORK/BACKEND/LENSES/`

**Your Mode:** PLANNER → EXECUTION → VERIFICATION → HISTORIAN
**Current Mode:** Start in **PLANNER MODE**

---

# FILES TO READ FIRST (in order)

## 1. Framework & Context

| Order | File | Why |
|-------|------|-----|
| 1 | `docs/ON_GOING_WORK/BACKEND/LENSES/AGENT-ONBOARDING.md` | Full framework, project context |
| 2 | `docs/ON_GOING_WORK/BACKEND/LENSES/PHASES-REMAINING.md` | Phase 16.1 details |
| 3 | `docs/ON_GOING_WORK/BACKEND/LENSES/GAPS.md` | GAP-001 details |
| 4 | `tasks/lessons.md` | Previous learnings |

## 2. Source Code

| Order | File | What to look for |
|-------|------|------------------|
| 5 | `apps/api/action_router/router.py` | Line ~1248: prepare_action() |
| 6 | `apps/api/routes/p0_actions_routes.py` | Existing mounted routes |
| 7 | `apps/api/pipeline_service.py` | How routers are included |

---

# TASK: Mount /prepare Endpoint

## Problem

`/v1/actions/prepare` returns 404 in production.

## Root Cause

`action_router/router.py` defines `prepare_action()` but that router is never included in `pipeline_service.py`. Only `p0_actions_router` is mounted.

## Goal

`curl -X POST http://localhost:8000/v1/actions/prepare` returns JSON (not 404).

## Constraints

| Constraint | Value |
|------------|-------|
| **Scope (IN)** | `p0_actions_routes.py` only |
| **Scope (OUT)** | `pipeline_service.py`, frontend, tests |
| **Tech Stack** | Python, FastAPI |
| **Priority** | CRITICAL |
| **Max Files** | 2 |

## Dependencies

| Dependency | Status | Blocks |
|------------|--------|--------|
| Phase 16 | Complete | Nothing |
| Docker local | Available | Verification |

---

# PLANNER MODE INSTRUCTIONS

1. Read all 7 files listed above
2. Understand where prepare_action() is defined
3. Plan copy of models + handler to p0_actions_routes.py
4. Define acceptance: `curl localhost:8000/v1/actions/prepare` returns JSON
5. Write plan to tasks/todo.md
6. **WAIT for approval**

---

# VERIFICATION

```bash
# Start Docker
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
docker compose -f docker-compose.local.yml build api --no-cache
docker compose -f docker-compose.local.yml up api -d
sleep 15

# Test /prepare endpoint
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'

# Expected: JSON with action_id, prefill, etc.
# NOT expected: 404 or "Not Found"

# Check OpenAPI
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
print([p for p in d.get('paths',{}).keys() if 'prepare' in p.lower()])
"
# Expected: ['/v1/actions/prepare']
```

---

# CONFIRMATION CHECKLIST

- [ ] I will read AGENT-ONBOARDING.md first
- [ ] I understand scope: p0_actions_routes.py only
- [ ] I will start in PLANNER MODE
- [ ] I will NOT write code until plan is approved
- [ ] I will verify with Docker locally
- [ ] I will write lesson after completion
- [ ] I will produce handoff for Phase 17

**State: "Starting in PLANNER MODE" and begin reading files.**
````

---

## Workflow Summary

```
1. /clear                           ← Fresh Claude context
2. Paste phase prompt               ← Full context restored
3. Claude reads files               ← PLANNER MODE
4. Claude outputs plan              ← PLANNER MODE
5. User approves                    ← Gate
6. Claude implements                ← EXECUTION MODE
7. Claude tests locally             ← VERIFICATION MODE
8. Claude writes lesson             ← HISTORIAN MODE
9. Claude outputs HANDOFF           ← Context for next agent
10. /clear                          ← Ready for next phase
11. Paste next agent prompt         ← From HANDOFF section
12. Repeat
```

---

## Key Principles

| Principle | Why It Matters |
|-----------|----------------|
| **Ordered file reads** | Most important context first |
| **Explicit mode declaration** | "Start in PLANNER MODE" prevents rushing |
| **Testable acceptance criteria** | "curl returns X" not "it should work" |
| **Docker local-first** | Verify before claiming success |
| **Mandatory lesson** | Learning compounds across phases |
| **Structured handoff** | Next agent doesn't guess context |

---

## Anti-Patterns to Avoid

| Bad | Good |
|-----|------|
| "Fix the bug" | "Fix GAP-001: curl returns 404 instead of JSON" |
| "Read the codebase" | "Read router.py:1248 for prepare_action" |
| "Test it works" | "curl localhost:8000/v1/actions/prepare returns JSON" |
| "Update docs" | "Write lesson to tasks/lessons.md with failure/guard/pattern" |
| "I think it works" | "Here is the curl output proving it works" |
| Session ends abruptly | Session ends with HANDOFF containing next prompt |
| "Approved" without reading plan | Read plan, verify scope, then approve |

---

## Error Recovery Patterns

### If Claude Skips Planning

```
STOP. You skipped PLANNER MODE.
Go back and read the files listed in FILES TO READ FIRST.
Then write a plan to tasks/todo.md.
Then wait for my approval.
```

### If Claude Claims Success Without Evidence

```
STOP. You skipped VERIFICATION MODE.
Run the test commands and paste the actual output.
I need to see evidence, not assertions.
```

### If Claude Doesn't Write Lesson

```
STOP. You skipped HISTORIAN MODE.
Add a structured lesson to tasks/lessons.md.
What almost went wrong? What guard prevents it?
```

### If Claude Modifies Unplanned Files

```
STOP. You have scope drift.
Files modified: [list]
Files in plan: [list]
Either revert the unplanned changes or amend the plan first.
```

---

## Multi-Phase Coordination

When phases depend on each other:

```markdown
## Dependencies

| Phase | Name | Status | Output |
|-------|------|--------|--------|
| 16 | Prefill Integration | ✓ Complete | PrepareResponse type |
| **16.1** | **Mount /prepare** | **○ Current** | **/v1/actions/prepare API** |
| 17 | Readiness States | ○ Blocked | Needs 16.1 |
| 18 | Route & Disambiguation | ○ Blocked | Needs 17 |

## Blocking Rule

Do NOT start Phase 17 until Phase 16.1 verification passes.
The /prepare endpoint must return JSON before readiness states can be tested.
```

---

## Integration with GSD Commands

```bash
# Before starting
/gsd:progress                    # Check overall status

# After planning
/gsd:add-todo                    # If plan reveals new work

# After execution
/gsd:verify-work                 # Run automated verification

# After completion
/gsd:execute-phase [N+1]         # Start next phase
```

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────────┐
│  PHASE PROMPT STRUCTURE                                            │
├────────────────────────────────────────────────────────────────────┤
│  1. SYSTEM ROLE        → Identity + mode declaration               │
│  2. FILES TO READ      → Ordered context (7+ files typical)        │
│  3. TASK               → Problem / Root Cause / Goal / Constraints │
│  4. PLANNER MODE       → Read → Plan → Approval gate               │
│  5. EXECUTION MODE     → Implement plan exactly                    │
│  6. VERIFICATION       → Docker local → Evidence → Scope check     │
│  7. HISTORIAN MODE     → Structured lesson                         │
│  8. HANDOFF            → Status + Evidence + Next prompt           │
│  9. CONFIRMATION       → Checklist → "Starting in PLANNER MODE"    │
└────────────────────────────────────────────────────────────────────┘
```

---

*See also: FRAMEWORK.md, AGENT-ONBOARDING-TEMPLATE.md, TASK-TEMPLATE.md, DOCKER-LOCAL-FIRST.md*
