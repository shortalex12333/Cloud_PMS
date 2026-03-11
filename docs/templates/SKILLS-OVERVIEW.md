# Skills Overview — Educating Claude Agents

**How to leverage the orchestration and verification skills across all Claude instances.**

---

## Quick Reference

| Skill | Purpose | Triggers On |
|-------|---------|-------------|
| **orchestrator-only** | Forces delegation, blocks direct implementation | Any implementation request |
| **verification-integrity** | Detects false test signals | Test pass/fail, 404/401/500 errors |
| **docker-local-first** | Enforces local verification before push | Docker, builds, deployments, git push |

---

## Skill 1: orchestrator-only

### The Problem It Solves

```
WITHOUT THIS SKILL:
User: "Implement feature X"
Claude: "Sure!" → [50 edits] → [lost context] → [forgot guardrails] → FAILURE

WITH THIS SKILL:
User: "Implement feature X"
Claude: "Let me plan and delegate..." → [sub-agents work] → [review gates] → SUCCESS
```

**Solo Claude drowns in copious work. Delegation scales.**

### The Rule

```
╔═══════════════════════════════════════════════════════════════════╗
║  CLAUDE CODE = ORCHESTRATOR ONLY                                  ║
║                                                                   ║
║  ✗ DO NOT use Edit/Write tools directly                          ║
║  ✗ DO NOT implement code yourself                                 ║
║  ✗ DO NOT "just quickly" fix anything                            ║
║                                                                   ║
║  ✓ PLAN using GSD commands                                        ║
║  ✓ DELEGATE using Task tool (sub-agents)                         ║
║  ✓ REVIEW sub-agent output                                        ║
║  ✓ VERIFY using /gsd:verify-work                                 ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Mandatory Workflow

```
1. UNDERSTAND  →  Read files, search codebase, ask questions
2. PLAN        →  /gsd:plan-phase N  (creates execution plan)
3. DELEGATE    →  Task tool OR /gsd:execute-phase (sub-agents work)
4. REVIEW      →  Check output against plan, verify guardrails
5. VERIFY      →  /gsd:verify-work (confirms completion)
```

### How to Delegate

Use the **Task tool** with appropriate sub-agent type:

```
Task(
  subagent_type="general-purpose",  # or "Explore", "Plan", "gsd-executor"
  prompt="## Task: [title]\n\n### Context\n[what agent needs to know]\n\n### Scope\nDO: [what to implement]\nDO NOT: [what to avoid]\n\n### Success Criteria\n[how to verify done]"
)
```

| Task Type | Sub-Agent |
|-----------|-----------|
| Find files, understand code | `Explore` |
| Design approach | `Plan` |
| Implement code | `general-purpose` |
| Execute GSD phase | `gsd-executor` |
| Debug systematically | `gsd-debugger` |
| Verify completion | `gsd-verifier` |

### When This Skill Activates

- Any request containing: implement, create, build, fix, refactor, write code, edit, modify
- Any multi-file changes
- Any feature work
- `always_active: true` — checks every implementation request

### Self-Check Questions

Before ANY action:
```
Am I about to use Edit/Write?      → STOP. Delegate.
Am I making multiple changes?       → STOP. Plan first, then delegate.
Have I planned this work?           → NO? /gsd:plan-phase first.
Am I "in the weeds"?                → STOP. Step back to orchestrator view.
```

---

## Skill 2: verification-integrity

### The Problem It Solves

```
FALSE FAILURE: Test fails, but code is actually correct
  - 404 because route not mounted (not because endpoint broken)
  - 401 because token expired (not because auth broken)
  - Timeout because CI slow (not because code slow)

FALSE SUCCESS: Test passes, but code is actually wrong
  - Test was skipped (didn't run at all)
  - No assertions (nothing verified)
  - 200 OK but response body is garbage
```

**Surface signals lie. This skill forces verification of the verification.**

### The Rule

```
╔═══════════════════════════════════════════════════════════════════╗
║  NEVER TRUST A SIGNAL AT FACE VALUE                               ║
║                                                                   ║
║  FAIL might mean: auth, routing, env, test quality — not code     ║
║  PASS might mean: skipped, no assertions, mocked — not correct    ║
║                                                                   ║
║  ALWAYS ASK: Is this signal telling me what I think?              ║
╚═══════════════════════════════════════════════════════════════════╝
```

### On Failure — Ask These Questions

```
┌─────────────────────────────────────────────────────────────────┐
│  GOT A FAILURE? CHECK BEFORE DEBUGGING CODE:                    │
├─────────────────────────────────────────────────────────────────┤
│  [ ] Is auth configured? (401/403)                              │
│  [ ] Is route mounted? (404)                                    │
│  [ ] Is environment correct? (500)                              │
│  [ ] Is service running? (connection refused)                   │
│  [ ] Is database seeded? (empty results)                        │
│  [ ] Is test itself correct? (outdated expectations)            │
│                                                                 │
│  If ANY unchecked → FALSE FAILURE → Fix environment, not code   │
└─────────────────────────────────────────────────────────────────┘
```

### On Success — Ask These Questions

```
┌─────────────────────────────────────────────────────────────────┐
│  GOT A SUCCESS? CHECK BEFORE CLAIMING DONE:                     │
├─────────────────────────────────────────────────────────────────┤
│  [ ] Did test actually run? (not skipped)                       │
│  [ ] Are assertions present? (not empty test)                   │
│  [ ] Is response CONTENT correct? (not just status 200)         │
│  [ ] Did real code run? (not over-mocked)                       │
│  [ ] Would this catch a regression?                             │
│                                                                 │
│  If ANY unchecked → FALSE SUCCESS → Strengthen the test         │
└─────────────────────────────────────────────────────────────────┘
```

### Common False Failure Patterns

| Signal | Looks Like | Actually |
|--------|------------|----------|
| 401 Unauthorized | Auth broken | Token missing/expired |
| 404 Not Found | Endpoint missing | Route not mounted |
| 500 Internal Error | Code bug | Missing env var |
| Connection refused | Service crashed | Service not started |
| Timeout | Code slow | CI runner overloaded |
| Assertion failed | Logic wrong | Test expects old behavior |

### Common False Success Patterns

| Signal | Looks Like | Actually |
|--------|------------|----------|
| "PASS" | Verified | Test was skipped |
| Test completes | Working | No assertions present |
| HTTP 200 | Correct | Response body is wrong |
| All green | Done | Tests are over-mocked |
| Length > 0 | Has data | Data is garbage |

### When This Skill Activates

- Test failure or pass
- HTTP status codes (404, 401, 403, 500)
- Claims like "it works", "tests pass", "all green"
- CI/CD results
- curl output analysis
- Any verification step

### Quick Diagnostic Commands

```bash
# Auth check
curl -v -H "Authorization: Bearer $TOKEN" $URL 2>&1 | head -30

# Route check
curl -s $BASE/openapi.json | jq '.paths | keys[]'

# Service check
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Find skipped tests
pytest tests/ -v 2>&1 | grep -i skip

# Find tests without assertions
grep -rL "assert" tests/*.py | grep "test_"
```

---

## Skill 3: docker-local-first

### The Problem It Solves

```
WRONG: Code → git push → Remote build → See if works → Fix → push → repeat
       └────────────── EACH ITERATION COSTS $$ AND TIME ──────────────┘

RIGHT: Code → Docker build locally → Verify → THEN push once
       └────── FREE, SECONDS ──────┘         └── Remote builds ONCE ──┘
```

**Remote platforms are for deploying verified code, not for testing.**

### The Rule

```
╔═══════════════════════════════════════════════════════════════════╗
║  NEVER PUSH CODE TO TRIGGER A REMOTE BUILD WITHOUT LOCAL VERIFY   ║
║                                                                   ║
║  Local Docker build: $0, 30 seconds                               ║
║  Remote build fail:  Build minutes charged, 5-8 minutes wasted    ║
║                                                                   ║
║  BUILD LOCALLY. TEST LOCALLY. VERIFY LOCALLY. PUSH ONCE.          ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Why Local Docker is Superior for AI

Claude can observe EVERYTHING locally:

```
LOCAL DOCKER (Full Observability):
├── docker stats     → CPU, memory, network in real-time
├── docker logs      → Full application output
├── docker exec      → Shell into container, inspect state
├── Exit codes       → Know exactly what failed
├── File system      → Check what was written
└── Network          → See all connections

REMOTE (Black Box):
├── Endpoint response → That's it
└── Build logs        → After the fact, limited
```

### Pre-Push Checklist

```bash
# BEFORE EVERY git push:
docker build -t app:local .
docker run --rm -p 8000:8000 --env-file .env.local app:local
curl http://localhost:8000/health
docker logs <container> | grep -i error

# ALL PASS? → Then push
# ANY FAIL? → Fix locally (free) → Repeat
```

### When This Skill Activates

- Creating/modifying Dockerfiles
- Any `git push` that triggers remote build
- Build failures on Render/Vercel/CI
- "Push and see if it works" suggestions
- Environment variable changes
- Dependency changes

---

## How to Ensure Every Claude Uses These Skills

### For Claude Code (CLI) — Automatic

Skills in `.claude/skills/` are automatically available. The skills are deployed at:

```
/Volumes/Backup/CELESTE/.claude/skills/
├── orchestrator-only/SKILL.md       ✓ Global
├── verification-integrity/SKILL.md  ✓ Global
├── docker-local-first/SKILL.md      ✓ Global
└── ...
```

Claude Code reads these automatically based on triggers.

### For Fresh Claude.ai Conversations — Manual

Paste this preamble at the start of any Claude.ai conversation:

```markdown
## Operating Rules

### 1. Orchestrator Only
You are an ORCHESTRATOR, not a worker. You do NOT implement code directly.
- PLAN using structured task breakdowns
- DELEGATE by describing tasks for sub-agents
- REVIEW outputs against plan
- VERIFY completion

If asked to implement something, respond with a PLAN for how sub-agents would do it.

### 2. Verification Integrity
Never trust test signals at face value.
- FAIL might mean: auth, routing, env — not code bug
- PASS might mean: skipped, no assertions — not verified

Always ask: "Is this signal telling me what I think?"

### 3. Docker Local-First
Never suggest pushing code to test on remote platforms.
Always verify locally with Docker first.
```

### For Project-Specific Claude Instances

Each project has skills in `.claude/skills/`:

```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.claude/skills/
├── orchestrator-only/SKILL.md       ✓ Project
├── verification-integrity/SKILL.md  ✓ Project
└── ...
```

These override or supplement global skills.

---

## Skill Interaction Diagram

```
USER REQUEST
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  orchestrator-only ACTIVATES                                    │
│  "Is this implementation work?"                                 │
│       │                                                         │
│       ├── YES → Force PLAN → DELEGATE → REVIEW → VERIFY         │
│       │         (no direct Edit/Write allowed)                  │
│       │                                                         │
│       └── NO (just reading/planning) → Proceed                  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Sub-agent executes work                                        │
│  Returns results                                                │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  verification-integrity ACTIVATES                               │
│  "Is this result trustworthy?"                                  │
│       │                                                         │
│       ├── FAIL received → Check for false failure patterns      │
│       │                   (auth? routing? env?)                 │
│       │                                                         │
│       └── PASS received → Check for false success patterns      │
│                           (skipped? no assertions? mocked?)     │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  docker-local-first ACTIVATES (if deployment involved)          │
│  "Was this verified locally before push?"                       │
│       │                                                         │
│       ├── NO → Block push, require local verification           │
│       │                                                         │
│       └── YES → Allow push                                      │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
VERIFIED COMPLETE
```

---

## Teaching Moments

### When Claude Tries to Edit Directly

```
❌ Claude: "Let me make that edit for you..."
   → Skill intercepts: "STOP. You are orchestrator-only.
      Delegate this to a sub-agent via Task tool."
```

### When Claude Claims "Tests Pass"

```
❌ Claude: "All tests pass, we're done!"
   → Skill intercepts: "STOP. Verify this is a REAL success.
      Did tests actually run? Are assertions present?
      Is response content correct, not just status?"
```

### When Claude Suggests "Push and See"

```
❌ Claude: "Let's push and see if the build works..."
   → Skill intercepts: "STOP. Verify locally first.
      docker build -t app:local . && docker run ...
      Only push after local verification passes."
```

---

## Summary Card (Print This)

```
┌─────────────────────────────────────────────────────────────────┐
│  THREE SKILLS EVERY CLAUDE MUST FOLLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ORCHESTRATOR-ONLY                                           │
│     • Do NOT implement directly                                 │
│     • PLAN → DELEGATE → REVIEW → VERIFY                         │
│     • Use Task tool + sub-agents                                │
│                                                                 │
│  2. VERIFICATION-INTEGRITY                                      │
│     • FAIL ≠ code broken (check env first)                      │
│     • PASS ≠ verified (check assertions)                        │
│     • Always verify the verification                            │
│                                                                 │
│  3. DOCKER-LOCAL-FIRST                                          │
│     • Never push to test remotely                               │
│     • Build + verify locally first                              │
│     • Push only verified code                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  MANTRA: Plan. Delegate. Verify locally. Trust nothing.         │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Locations

```
Global Skills (all projects):
/Volumes/Backup/CELESTE/.claude/skills/
├── orchestrator-only/SKILL.md
├── orchestration-discipline/SKILL.md
├── verification-integrity/SKILL.md
│   └── references/
│       ├── false-failures.md
│       ├── false-successes.md
│       └── verification-checklist.md
└── docker-local-first/SKILL.md

Project Skills (this project):
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/.claude/skills/
├── orchestrator-only/SKILL.md
└── verification-integrity/SKILL.md

Documentation:
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/docs/templates/
├── SKILLS-OVERVIEW.md              ← This file
├── ORCHESTRATION-MODEL.md          ← Full orchestration documentation
├── PHASE-PROMPT-TEMPLATE.md        ← Per-phase agent prompts
└── ...
```
