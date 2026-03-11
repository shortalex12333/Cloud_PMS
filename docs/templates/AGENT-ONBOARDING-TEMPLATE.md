# Agent Onboarding Template

**Copy this template for each project/feature. Fill in the placeholders and paste to any Claude agent.**

---

# Agent Onboarding — [PROJECT NAME]

**Paste this entire document to any Claude agent working on [PROJECT NAME].**

---

# PART 1: OPERATING FRAMEWORK

## The Four Modes

You operate in **four modes**. Never mix them. Complete each before moving to next.

| Mode | What You Do | What You DON'T Do |
|------|-------------|-------------------|
| **PLANNER** | Create plan, list files, define criteria | Write code |
| **EXECUTION** | Implement only what's planned, stay in scope | Modify unplanned files |
| **VERIFICATION** | Test, prove it works, check for drift | Assume it works |
| **HISTORIAN** | Write structured lesson, capture patterns | Skip documentation |

## The Three Rules

1. **Plan First** — No code without approved plan
2. **Verify Always** — Prove it works with evidence
3. **Learn Forever** — Structured lesson after every task

## File Organization Rules

| Forbidden | Required |
|-----------|----------|
| `_v1`, `_v2`, `_final`, `_old` suffixes | Clear, purpose-driven names |
| `utils.py`, `helpers.py` | Import, don't copy |
| Create file in wrong place | Right location from start |

---

# PART 2: PROJECT CONTEXT

## Project Goal

[ONE-SENTENCE DESCRIPTION OF WHAT THIS PROJECT/FEATURE DOES]

```
[SIMPLE DIAGRAM OR FLOW IF HELPFUL]
```

## Current Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Phase name] | ✓ Complete |
| 2 | [Phase name] | ◐ In Progress |
| 3 | [Phase name] | ○ Pending |

## Known Gaps / Blockers

| ID | Description | Impact | Fix |
|----|-------------|--------|-----|
| GAP-001 | [What's broken] | [What it blocks] | [How to fix] |

## Key Files

### Frontend (apps/web/src)

| File | Purpose |
|------|---------|
| `[path/to/file.ts]` | [What it does] |
| `[path/to/file.tsx]` | [What it does] |

### Backend (apps/api)

| File | Purpose |
|------|---------|
| `[path/to/file.py]` | [What it does] |
| `[path/to/file.py]` | [What it does] |

## Key Types / Interfaces

```typescript
// [Include critical type definitions agents need to know]
interface ExampleType {
  field: string;
  // ...
}
```

---

# PART 3: GUARDRAILS (Non-Negotiable)

1. **[GUARDRAIL 1]** — [Description]
2. **[GUARDRAIL 2]** — [Description]
3. **[GUARDRAIL 3]** — [Description]
4. **No new random files** — modify existing files listed above
5. **100% tenant isolation** — all lookups scoped by tenant_id

---

# PART 4: LESSONS REFERENCE

**Project lessons:** `tasks/lessons.md`

Read this file before starting any task. Add lessons after completing tasks.

Key lessons for this project:
- [LESSON 1 SUMMARY]
- [LESSON 2 SUMMARY]

---

# PART 5: LOCAL DEVELOPMENT

## Docker Local-First Rule

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  NEVER push code to trigger a remote build without local Docker verification ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Start Local Stack

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
./scripts/local-dev.sh start
```

## Verify Before Push

```bash
./scripts/local-dev.sh health
./scripts/local-dev.sh logs [service]
curl http://localhost:8000/health
```

## Project-Specific Tests

```bash
# [Add project-specific verification commands]
curl -X POST http://localhost:8000/[endpoint] -d '{...}'
```

---

# PART 6: COMMANDS

## GSD (Planning & Execution)

```bash
/gsd:progress           # Check status
/gsd:plan-phase [N]     # Plan next phase
/gsd:execute-phase [N]  # Execute phase
/gsd:verify-work        # Verify completion
```

## Ruflo (Memory)

```bash
npx ruflo memory search --query "[topic]"
npx ruflo memory store --key "[key]" --value "[value]"
```

---

# PART 7: TASK TEMPLATE

## Task: [DESCRIBE TASK]

**Context:**
- Project: [PROJECT NAME]
- Current state: [what exists now]
- Goal: [end state you want]

**Constraints:**
- Scope: [specific files only]
- Tech: [languages, frameworks]
- Priority: [Low/Medium/High/Critical]

**Start in PLANNER MODE:**
1. Read relevant documentation in `docs/ON_GOING_WORK/[path]/`
2. List all files that will change
3. Define acceptance criteria
4. Write plan to tasks/todo.md
5. Wait for my approval

**Do not write code until plan is approved.**

**After completion:**
1. Verify with Docker local test
2. Write structured lesson to tasks/lessons.md
3. Update project documentation

---

# EXAMPLE TASKS

## Example 1: [EXAMPLE TASK NAME]

```markdown
## Task: [Task description]

**Context:**
- Project: [PROJECT NAME]
- Current state: [what exists]
- Goal: [end state]

**Constraints:**
- Scope: [files]
- Tech: [stack]
- Priority: [level]

**Start in PLANNER MODE:**
1. [Step 1]
2. [Step 2]
3. Wait for approval

Do not write code until plan is approved.
```

## Example 2: [ANOTHER EXAMPLE]

```markdown
## Task: [Task description]

[Fill in similarly...]
```

---

# CONFIRMATION

Before starting, confirm:

1. ☐ I understand the 4-mode methodology
2. ☐ I know the current phase status
3. ☐ I know the key files to modify
4. ☐ I will verify locally with Docker before pushing
5. ☐ I will write lessons after completing tasks

**State which mode you are starting in.**

---

# CHECKLIST FOR CREATING THIS DOCUMENT

When filling out this template for a new project:

- [ ] Replace all `[PLACEHOLDER]` text
- [ ] Add project-specific diagram/flow
- [ ] List all phases with current status
- [ ] Document all known gaps/blockers
- [ ] List key files for frontend AND backend
- [ ] Include critical type definitions
- [ ] Define project-specific guardrails
- [ ] Summarize relevant lessons
- [ ] Add project-specific test commands
- [ ] Create 2+ example tasks
- [ ] Remove this checklist section
