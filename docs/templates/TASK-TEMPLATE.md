# Task Submission Template

**Copy this template, fill in the placeholders, and submit to Claude.**

---

## BASIC TASK TEMPLATE

```markdown
## Task: [WHAT YOU WANT DONE]

**Context:**
- Project: [project name or path]
- Current state: [what exists now]
- Goal: [end state you want]

**Constraints:**
- Scope: [what's IN scope / what's OUT of scope]
- Tech: [languages, frameworks, patterns to use]
- Priority: [Low / Medium / High / Critical]

**Start in PLANNER MODE:**
1. List all files that will change
2. Define acceptance criteria
3. Identify risks
4. Write plan to tasks/todo.md
5. Wait for my approval before executing

Do not write any code until I approve the plan.
```

---

## EXAMPLES

### Frontend Task

```markdown
## Task: Add dark mode toggle to the settings page

**Context:**
- Project: my-react-app
- Current state: Light theme only, using Tailwind CSS
- Goal: User can toggle dark/light, preference persists in localStorage

**Constraints:**
- Scope: Settings page only (don't touch other pages)
- Tech: React, Tailwind CSS, localStorage
- Priority: Medium

**Start in PLANNER MODE:**
1. List components that need theme support
2. Define state management approach
3. Plan CSS variable structure
4. Write plan to tasks/todo.md
5. Wait for my approval

Do not write any code until I approve the plan.
```

---

### Backend Task

```markdown
## Task: Add rate limiting to authentication endpoints

**Context:**
- Project: api-service
- Current state: No rate limiting, endpoints exposed
- Goal: Prevent brute force on /api/auth/*

**Constraints:**
- Scope: Only /api/auth/* routes
- Tech: Express.js, Redis
- Limits: 5 attempts/minute for login, 3 for register
- Priority: High

**Start in PLANNER MODE:**
1. Define rate limit strategy (key, window, response)
2. List middleware changes
3. Plan error response format
4. Write plan to tasks/todo.md
5. Wait for my approval

After execution, VERIFICATION must include load test evidence.
```

---

### Database Task

```markdown
## Task: Add soft delete to users table

**Context:**
- Project: backend-service
- Current state: Hard delete (rows removed)
- Goal: Soft delete (deleted_at timestamp)

**Constraints:**
- Scope: users table + ALL queries that touch it
- Tech: PostgreSQL, Prisma
- Priority: Critical (production data)

**Start in PLANNER MODE:**
1. Grep codebase for ALL user queries
2. Plan migration (up AND down)
3. List every query needing WHERE deleted_at IS NULL
4. Risk assessment
5. Write plan to tasks/todo.md
6. Wait for my explicit approval

This is HIGH RISK. Extra verification required.
```

---

### DevOps Task

```markdown
## Task: Set up GitHub Actions CI pipeline

**Context:**
- Project: my-service
- Current state: No CI, manual testing
- Goal: Automated test + build on every PR

**Constraints:**
- Scope: CI only (no CD/auto-deploy)
- Tech: GitHub Actions, Node.js 20
- Requirements: tests, lint, build, caching
- Priority: Medium

**Start in PLANNER MODE:**
1. Define workflow triggers
2. Plan job structure
3. Design caching strategy
4. Write plan to tasks/todo.md
5. Wait for my approval

VERIFICATION: Push test PR and confirm all jobs pass.
```

---

### Bug Fix Task

```markdown
## Task: Fix [BUG DESCRIPTION]

**Context:**
- Location: [file or component]
- Expected behavior: [what should happen]
- Actual behavior: [what's happening instead]
- Reproduction: [steps to reproduce]

**Constraints:**
- Scope: Fix only, no refactoring
- Priority: [Low / Medium / High / Critical]

**Start in PLANNER MODE:**
1. Identify root cause (not just symptoms)
2. Propose fix approach
3. List files to modify
4. Plan test to prevent regression
5. Write plan to tasks/todo.md

After fix, write HISTORIAN lesson documenting root cause.
```

---

### Refactor Task

```markdown
## Task: Refactor [COMPONENT/MODULE]

**Context:**
- Current state: [what's wrong with current code]
- Goal: [what improvement you want]
- Why: [performance / readability / maintainability]

**Constraints:**
- Scope: [specific files/modules]
- Behavior: Must NOT change (refactor only)
- Priority: [Low / Medium]

**Start in PLANNER MODE:**
1. Document current behavior (tests should pass before AND after)
2. Plan refactor approach
3. List files to modify
4. Define verification strategy
5. Write plan to tasks/todo.md

HIGH RISK of regression. Verification must show identical behavior.
```

---

### Research Task

```markdown
## Task: Research [TOPIC]

**Context:**
- Project: [project name]
- Question: [what you need to know]
- Purpose: [why you need this information]

**Constraints:**
- Scope: Research only (no implementation)
- Output: Summary document with recommendations

**Approach:**
1. Explore codebase for relevant patterns
2. Research external best practices
3. Compare options with tradeoffs
4. Write recommendations to [output location]

This is research mode. No code changes.
```

---

### Multi-Phase Project

```markdown
## Project: [PROJECT NAME]

**Context:**
- Current state: [starting point]
- End goal: [final state]
- Timeline: [any deadlines]

**Phases:**
1. Phase 1: [description]
2. Phase 2: [description]
3. Phase 3: [description]

**Constraints:**
- Tech: [stack]
- Scope: [boundaries]
- Priority: [level]

**Framework:**
Complete each phase fully before starting next:
- PLANNER → EXECUTION → VERIFICATION → HISTORIAN
- Each phase gets its own plan in tasks/todo.md
- Each phase ends with structured lesson

Start with Phase 1 in PLANNER MODE.
Do not combine phases.
```

---

## QUICK TEMPLATES

### One-Liner (Simple Task)
```
Add [feature] to [location]. Plan first, wait for approval.
```

### Bug Report Format
```
Bug: [description]
Expected: [behavior]
Actual: [behavior]
Fix it. Document root cause in lesson.
```

### Urgent Fix
```
URGENT: [problem]
Location: [file]
Fix immediately but still run verification.
Write lesson after.
```

---

## PHRASES TO INCLUDE

Add these to ensure framework compliance:

| Phrase | What It Does |
|--------|--------------|
| "Start in PLANNER MODE" | Forces planning first |
| "Wait for my approval" | Prevents premature execution |
| "Write plan to tasks/todo.md" | Creates trackable plan |
| "Run /review before completing" | Triggers verification |
| "Write structured lesson" | Forces learning capture |
| "This is HIGH RISK" | Signals extra caution |
| "Do not skip modes" | Explicit enforcement |
| "Stay in scope" | Prevents feature creep |

---

## RESPONSE CHECKLIST

When Claude responds to your task, verify:

- [ ] Started in PLANNER MODE (not jumping to code)
- [ ] Listed files to modify
- [ ] Defined acceptance criteria
- [ ] Asked for approval before executing
- [ ] (After execution) Provided verification evidence
- [ ] (After verification) Wrote structured lesson

If Claude skips any step, say:
> "Stop. You skipped [PLANNER/VERIFICATION/HISTORIAN] MODE. Go back."

---

## BLANK TEMPLATE (COPY THIS)

```markdown
## Task: [YOUR TASK HERE]

**Context:**
- Project:
- Current state:
- Goal:

**Constraints:**
- Scope:
- Tech:
- Priority:

**Start in PLANNER MODE:**
1. List all files that will change
2. Define acceptance criteria
3. Identify risks and rollback plan
4. Write plan to tasks/todo.md
5. Wait for my approval before executing

[ADD ANY TASK-SPECIFIC REQUIREMENTS HERE]

Do not write code until I approve the plan.
After completion, write structured lesson.
```
