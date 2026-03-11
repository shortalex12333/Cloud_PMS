# Templates Directory

**Bootstrap documents for tasking Claude agents.**

---

## Quick Reference

| Template | When to Use |
|----------|-------------|
| **FRAMEWORK.md** | Paste to any fresh Claude to establish 4-mode methodology |
| **QUICK-START.md** | Condensed version of FRAMEWORK.md (single page) |
| **TASK-TEMPLATE.md** | Examples for how to structure task requests |
| **AGENT-ARCHITECTURE.md** | Reference explaining the 3-layer Claude Code system |
| **AGENT-ONBOARDING-TEMPLATE.md** | Copy this to create project-specific onboarding docs |
| **PHASE-PROMPT-TEMPLATE.md** | Bootstrap fresh Claude for a specific phase (after /clear) |
| **ORCHESTRATION-MODEL.md** | Claude Code as PM/orchestrator, not worker |
| **SKILLS-OVERVIEW.md** | Education document for all 3 core skills |
| **DOCKER-LOCAL-FIRST.md** | Context for deployment/Docker work |

---

## The 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: CLAUDE.md         │ Always loaded │ Behavioral rules  │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 2: Skills            │ On trigger    │ Domain expertise  │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 3: Commands          │ User invokes  │ /techdebt, /plan  │
└─────────────────────────────────────────────────────────────────┘
         ↑
These templates are for BOOTSTRAPPING fresh Claudes that don't
have access to your project's CLAUDE.md (e.g., Claude.ai)
```

---

## When to Use What

### Starting a Fresh Claude.ai Conversation

```
1. Paste FRAMEWORK.md or QUICK-START.md
   → Establishes 4-mode methodology

2. Paste project's AGENT-ONBOARDING.md
   → Gives project context, files, status

3. Give specific task using TASK-TEMPLATE.md format
   → Clear scope, constraints, mode to start in
```

### Working in Claude Code (CLI)

No need to paste templates — Claude Code automatically reads:
- `CLAUDE.md` at project root
- `~/.claude/CLAUDE.md` (global)
- Skills in `.claude/skills/`
- `tasks/lessons.md`

### Creating a New Project Onboarding Doc

```
1. Copy AGENT-ONBOARDING-TEMPLATE.md
2. Save as docs/ON_GOING_WORK/[AREA]/[PROJECT]/AGENT-ONBOARDING.md
3. Fill in all placeholders
4. Remove the checklist section at the bottom
```

---

## Template Purposes

### FRAMEWORK.md
**Full methodology reference.** Use when you need Claude to understand the complete 4-mode system, file organization rules, lesson format, and feature requirements table.

**Size:** ~370 lines
**Use for:** New agents, complex tasks, establishing discipline

### QUICK-START.md
**Condensed single-page version.** Same rules, less detail.

**Size:** ~120 lines
**Use for:** Quick tasks, agents already familiar with the methodology

### TASK-TEMPLATE.md
**Examples of task formats.** Shows how to structure requests for frontend, backend, database, DevOps, bug fixes, refactoring, and research tasks.

**Use for:** Reference when writing task prompts

### AGENT-ARCHITECTURE.md
**Deep explanation of the 3-layer system.** Explains CLAUDE.md vs Skills vs Commands, when each is loaded, progressive disclosure, and the self-improvement loop.

**Use for:** Understanding the system, onboarding new team members

### AGENT-ONBOARDING-TEMPLATE.md
**Blank template for project-specific onboarding.** Copy and customize for each major project/feature.

**Use for:** Creating new project onboarding docs (like SPOTLIGHT_SEARCH/AGENT-ONBOARDING.md)

### PHASE-PROMPT-TEMPLATE.md
**Per-phase agent bootstrap template.** Self-contained context for fresh Claude sessions after `/clear`. Includes SYSTEM ROLE, FILES TO READ, TASK, all 4 modes, HANDOFF section.

**Use for:** Creating prompts for GSD phase execution, relay-race style agent handoffs

### ORCHESTRATION-MODEL.md
**Claude Code as PM, not worker.** Defines when to delegate to sub-agents vs. work directly. Includes review gates, drift detection, recovery protocol.

**Key rule:** >5 tool calls → DELEGATE, >2 files → DELEGATE

**Use for:** Preventing scope creep, maintaining guardrails, ensuring quality

### DOCKER-LOCAL-FIRST.md
**Local development context.** Explains why local Docker is superior, what Claude can observe, the 96GB Mac Studio setup, and observability commands.

**Use for:** Any work involving builds, deployments, or debugging

---

## Workflow Diagram

```
Fresh Claude                          Claude Code (CLI)
Conversation
     │                                     │
     ▼                                     ▼
┌─────────────┐                    ┌─────────────────┐
│ Paste       │                    │ Auto-loads      │
│ FRAMEWORK   │                    │ CLAUDE.md       │
└─────────────┘                    │ + Skills        │
     │                             │ + lessons.md    │
     ▼                             └─────────────────┘
┌─────────────┐                           │
│ Paste       │                           │
│ PROJECT     │                           │
│ ONBOARDING  │                           │
└─────────────┘                           │
     │                                     │
     ▼                                     ▼
┌─────────────────────────────────────────────────────┐
│            Give Task (TASK-TEMPLATE format)         │
│                                                     │
│   ## Task: [description]                            │
│   **Context:** ...                                  │
│   **Constraints:** ...                              │
│   **Start in PLANNER MODE:** ...                    │
└─────────────────────────────────────────────────────┘
     │                                     │
     ▼                                     ▼
┌─────────────────────────────────────────────────────┐
│                Claude executes:                     │
│   PLANNER → [approval] → EXECUTION →                │
│   VERIFICATION → HISTORIAN → Done                   │
└─────────────────────────────────────────────────────┘
```

---

## File Locations

```
docs/templates/                      ← You are here
├── README.md                        ← This file
├── FRAMEWORK.md                     ← Full methodology
├── QUICK-START.md                   ← Condensed methodology
├── TASK-TEMPLATE.md                 ← Task format examples
├── AGENT-ARCHITECTURE.md            ← 3-layer system explanation
├── AGENT-ONBOARDING-TEMPLATE.md     ← Blank project template
├── PHASE-PROMPT-TEMPLATE.md         ← Per-phase agent bootstrap
├── ORCHESTRATION-MODEL.md           ← PM/orchestrator model
├── SKILLS-OVERVIEW.md               ← Education doc for all skills
└── DOCKER-LOCAL-FIRST.md            ← Local dev context

docs/ON_GOING_WORK/
├── BACKEND/
│   └── SPOTLIGHT_SEARCH/
│       └── AGENT-ONBOARDING.md      ← Project-specific (example)
└── [OTHER AREAS]/
    └── [OTHER PROJECTS]/
        └── AGENT-ONBOARDING.md      ← Create for each project
```

---

## The Self-Improvement Loop

Every template references `tasks/lessons.md`. This is intentional.

```
Claude makes mistake
        ↓
You correct it
        ↓
Claude writes lesson to tasks/lessons.md
        ↓
Next session, Claude reads lessons
        ↓
Same mistake never happens twice
        ↓
System gets smarter over time
```

**Lessons compound.** Week 1: 3 lessons. Month 1: 15 lessons. Quarter 1: 40+ lessons.

By month 3, Claude knows your codebase's specific gotchas and avoids them automatically.

---

## Creating Good Lessons

When Claude (or you) adds a lesson:

```markdown
## LESSON: [Short Title]

**Date:** YYYY-MM-DD
**Context:** [What were we trying to do?]
**Failure:** [What went wrong?]
**Root Cause:** [Why did it happen?]
**Guard Added:** [What rule prevents this?]
**Test Added:** [What test catches this?]
**Reusable Pattern:** [What can be applied elsewhere?]
**Tags:** [deployment, database, frontend, etc.]
```

Bad lesson: "Don't do that thing"
Good lesson: Specific context, root cause, prevention rule, tags for searchability

---

## Maintenance

| Task | Frequency | How |
|------|-----------|-----|
| Update FRAMEWORK.md | When methodology changes | Edit directly |
| Create project onboarding | Per project | Copy AGENT-ONBOARDING-TEMPLATE |
| Add lessons | Every task completion | Append to tasks/lessons.md |
| Review lessons | Session start | Claude reads automatically |
