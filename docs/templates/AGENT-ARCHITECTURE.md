# The Claude Code Configuration Architecture

**Reference document explaining the three-layer system for Claude Code customization.**

---

## Why This Matters

Most Claude Code setups fail because people conflate the three layers. Each layer has a different purpose, scope, and trigger mechanism. Understanding the architecture is the difference between Claude Code being a tool and Claude Code being a team member.

---

## The Three Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: CLAUDE.md                                   │
│                     "The Operating System"                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Loaded: EVERY session, automatically                                     │
│  • Purpose: How to BEHAVE and OPERATE                                       │
│  • Scope: Broad behavioral rules                                            │
│  • Size: Concise (always in context)                                        │
│  • Location: Project root or ~/.claude/CLAUDE.md (global)                   │
│                                                                             │
│  Contains: Work approach, task management, mistake handling,                │
│            verification standards, autonomy expectations                    │
│                                                                             │
│  Does NOT contain: Specific procedures, reference material, scripts         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: Skills                                      │
│                       "The Capabilities"                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Loaded: Only when TRIGGERED by matching task                             │
│  • Purpose: How to DO specific things (expertise)                           │
│  • Scope: Narrow technical capabilities                                     │
│  • Size: Can be large (loaded on demand)                                    │
│  • Location: .claude/skills/skill-name/SKILL.md                             │
│                                                                             │
│  Examples: docker-local-first, repo-structure-discipline,                   │
│            database-analytics, api-design-patterns                          │
│                                                                             │
│  Progressive disclosure: Description always visible → SKILL.md on trigger  │
│                          → references/ loaded when needed                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LAYER 3: Slash Commands                                 │
│                        "The Shortcuts"                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Loaded: When USER explicitly invokes /commandname                        │
│  • Purpose: On-demand workflows YOU trigger                                 │
│  • Scope: Discrete, repeatable actions                                      │
│  • Size: Single prompt file                                                 │
│  • Location: .claude/commands/commandname.md                                │
│                                                                             │
│  Examples: /techdebt, /review, /plan, /lessons                              │
│                                                                             │
│  Difference from skills: Skills are passive (Claude decides),               │
│                          Commands are active (YOU invoke)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: CLAUDE.md — The Operating System

### What It Is

`CLAUDE.md` is a markdown file that Claude Code reads **at the start of every session**, automatically. No triggers. No conditions. Always loaded, always active.

Think of it as Claude Code's operating manual. It doesn't teach Claude how to do specific tasks — it teaches Claude **how to think, behave, and operate**.

### What Goes In It

**How to approach work:**
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan — don't keep pushing
- Write detailed specs upfront to reduce ambiguity

**How to manage tasks:**
- Write plans to `tasks/todo.md` with checkable items
- Mark items complete as you go
- Add review section when done

**How to handle mistakes:**
- After ANY correction, update `tasks/lessons.md` with the pattern
- Write rules that prevent the same mistake
- Review lessons at session start

**How to verify work:**
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask: "Would a staff engineer approve this?"

**Quality standards:**
- For non-trivial changes: "is there a more elegant way?"
- If a fix feels hacky, implement the elegant solution instead
- Don't over-engineer simple fixes

### What Does NOT Go In It

- Specific technical procedures (those are skills)
- Reference material about tools (those are skill reference files)
- One-off scripts or commands (those are slash commands)

**CLAUDE.md is about behavior, not capability.**

### The Self-Improvement Loop

This is the most powerful mechanism:

```
1. Claude makes a mistake or you correct it
2. Claude updates tasks/lessons.md with what went wrong
3. Next session, Claude reads lessons.md and applies those rules
4. The same mistake never happens twice
```

This is **institutional memory**. Every correction becomes a permanent rule. Over weeks, `tasks/lessons.md` accumulates the specific patterns and gotchas of YOUR codebase.

### Example Lessons Entry

```markdown
## LESSON: Database connections

**Date:** 2026-02-15
**Context:** Worker was crashing under load
**Failure:** Opened new DB connection inside a loop
**Root Cause:** Didn't use connection pool
**Guard Added:** ALWAYS use pool from services/db.py
**Reusable Pattern:** Never create connections in loops
**Tags:** database, performance, workers
```

### Where CLAUDE.md Lives

```
your-project/
├── CLAUDE.md              ← Project-level (reads this first)
├── tasks/
│   ├── todo.md            ← Current task plan
│   └── lessons.md         ← Accumulated lessons
└── ...

~/.claude/
├── CLAUDE.md              ← Global (applies to all projects)
└── ...
```

---

## Layer 2: Skills — The Capabilities

### What They Are

Skills are self-contained knowledge modules that Claude consults **when triggered by a relevant task**. They sit dormant until Claude encounters a matching task.

Think of CLAUDE.md as personality and work ethic. Skills are **expertise**.

### Comparison

| Aspect | CLAUDE.md | Skills |
|--------|-----------|--------|
| Loaded | Every session, automatically | Only when triggered |
| Purpose | How to behave | How to do specific things |
| Scope | Broad behavioral rules | Narrow technical capabilities |
| Size | Concise (always in context) | Can be large (on demand) |
| Structure | Single markdown file | Folder with SKILL.md + references |

### Skill Anatomy

```
.claude/skills/
└── skill-name/
    ├── SKILL.md                    ← Core rules (loaded when triggered)
    └── references/                 ← Deep reference material
        ├── detailed-guide.md
        └── examples.md
```

### Progressive Disclosure (Why This Is Smart)

```
Level 1: Skill name + description (~100 words)
         Claude sees this for ALL skills, all the time
         This is how it decides whether to consult a skill
              ↓
Level 2: SKILL.md body
         Read when the task matches the description
              ↓
Level 3: Reference files
         Read only when SKILL.md says to for specific subtask
```

Claude isn't burning context on your Docker skill when asking a database question. It only loads what's relevant.

### The Description Is Everything

The skill's YAML description is the trigger mechanism:

**Bad description:**
```yaml
description: Docker best practices.
```

**Good description:**
```yaml
description: >
  Enforces local Docker build and verification before any push to remote
  platforms. Triggers on any task involving builds, deployments, Docker,
  Render, Vercel, CI/CD, git push, build failures, environment variables,
  dependency changes, or any suggestion to "push and see if it works."
```

The good description names specific scenarios and phrases. Undertriggering is worse than overtriggering.

### Example Skills

| Skill | Triggers When |
|-------|---------------|
| `repo-structure-discipline` | Creating files, reviewing structure, version suffixes |
| `docker-local-first` | Deployment, build failures, CI/CD work |
| `database-analytics` | Postgres queries, data questions |

---

## Layer 3: Slash Commands — The Shortcuts

### What They Are

Slash commands are quick-trigger actions invoked by typing `/commandname`. They're shortcuts that run a specific workflow.

### How They Differ from Skills

- **Skills:** Passive — Claude decides when to use them
- **Commands:** Active — YOU invoke them explicitly

| Scenario | Mechanism |
|----------|-----------|
| Claude automatically checks Docker build | Skill triggered |
| You type `/techdebt` for codebase audit | Command invoked |

### What Makes a Good Slash Command

Commands you'd run on demand, repeatedly:

- `/techdebt` — Scan for dead code, duplicates, structural rot
- `/plan` — Force Claude into plan mode
- `/review` — Pre-push review checklist
- `/lessons` — Review and update tasks/lessons.md

### How to Create Them

```
.claude/
└── commands/
    ├── techdebt.md          ← /techdebt
    ├── review.md            ← /review
    └── plan.md              ← /plan
```

Each file is the prompt that runs when invoked.

---

## How All Three Layers Work Together

```
Session starts
    │
    ▼
Claude reads CLAUDE.md                    ← Layer 1: Behavioral rules
Claude reads tasks/lessons.md             ← Previous mistakes loaded
Claude sees all skill descriptions        ← Layer 2: Awareness of capabilities
    │
    ▼
You give Claude a task
    │
    ├── "Fix the build failure on Render"
    │       │
    │       ▼
    │   docker-local-first skill triggers    ← Layer 2
    │   Claude reads SKILL.md
    │   Claude follows: reproduce locally first
    │   Claude follows CLAUDE.md: enters plan mode (Layer 1)
    │   Claude builds locally, verifies, pushes once
    │
    ├── "Create a new utility file for auth helpers"
    │       │
    │       ▼
    │   repo-structure skill triggers        ← Layer 2
    │   Claude checks for existing auth files
    │   Claude places file correctly, clear name
    │
    ├── You type "/techdebt"
    │       │
    │       ▼
    │   Slash command fires                   ← Layer 3
    │   repo-structure skill may also trigger
    │   Claude runs full audit
    │
    ├── Claude makes a mistake, you correct it
    │       │
    │       ▼
    │   CLAUDE.md rule: update lessons        ← Layer 1
    │   Claude writes to tasks/lessons.md
    │   Next session, lesson is permanent
```

---

## Why CLAUDE.md Comes First

**Skills without CLAUDE.md:** Claude knows HOW to build Docker locally, but doesn't know to plan first, verify after, or capture lessons. The skill fires in a vacuum.

**CLAUDE.md without skills:** Claude knows to plan first and capture lessons, but might lack deep Docker knowledge. The behavior is right even if capability is missing.

**CLAUDE.md + skills:** Claude plans, consults the skill for specifics, executes with discipline, verifies, captures lessons. The full system.

**The behavioral layer is the foundation. Everything else builds on it.**

---

## For Fresh Claude Conversations

When starting a NEW Claude conversation (Claude.ai, new session without project context):

1. **Paste FRAMEWORK.md or QUICK-START.md** — Establishes the 4-mode methodology
2. **Paste project context** — The AGENT-ONBOARDING.md for your project
3. **Give specific task** — Using TASK-TEMPLATE.md format

This bootstrap process gives the fresh Claude:
- Behavioral rules (from framework)
- Project context (from onboarding)
- Clear task scope (from template)

---

## The Compounding Effect

| Week | What Happens |
|------|--------------|
| 1 | CLAUDE.md in place. Claude plans before building, verifies before pushing. |
| 2 | Lessons accumulating. Docker skill active. Builds happen locally. |
| 4 | 15 lessons. Claude knows your codebase's gotchas. /techdebt catches duplicates. |
| 8 | 30 lessons. Claude is a team member who never repeats mistakes. |
| 12 | Haven't corrected Claude on a repeated mistake in a month. System self-sustaining. |

**Not a one-time improvement — a system that improves itself every session.**

---

## File Structure Reference

```
your-project/
├── CLAUDE.md                              ← Layer 1: Always loaded
├── tasks/
│   ├── todo.md                            ← Task tracking
│   └── lessons.md                         ← Self-improvement memory
├── .claude/
│   ├── skills/                            ← Layer 2: On-demand expertise
│   │   ├── repo-structure-discipline/
│   │   │   └── SKILL.md
│   │   ├── docker-local-first/
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   └── database-analytics/
│   │       ├── SKILL.md
│   │       └── references/
│   └── commands/                          ← Layer 3: User-invoked
│       ├── techdebt.md
│       ├── review.md
│       └── plan.md
├── docs/
│   └── templates/                         ← Bootstrap documents
│       ├── FRAMEWORK.md
│       ├── QUICK-START.md
│       ├── TASK-TEMPLATE.md
│       └── AGENT-ARCHITECTURE.md (this file)
└── src/
```

---

## Quick Reference

| Layer | When Loaded | Purpose | Location |
|-------|-------------|---------|----------|
| **CLAUDE.md** | Every session | Behavior | Project root |
| **Skills** | Task match | Expertise | .claude/skills/ |
| **Commands** | User invokes | Workflows | .claude/commands/ |
| **Lessons** | Every session | Memory | tasks/lessons.md |
| **Templates** | Paste to fresh Claude | Bootstrap | docs/templates/ |
