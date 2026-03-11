# Orchestration Model

**Claude Code as Project Manager, Not Worker**

---

## The Core Principle

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  CLAUDE CODE = ORCHESTRATOR / PROJECT MANAGER                                 ║
║  SUB-AGENTS = WORKERS                                                         ║
║                                                                               ║
║  The orchestrator PLANS, DELEGATES, REVIEWS, and VERIFIES                    ║
║  The orchestrator does NOT execute copious tasks directly                    ║
║                                                                               ║
║  When in doubt: DELEGATE to sub-agent, don't do it yourself                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Why This Matters

### The Anti-Pattern (What Goes Wrong)

```
User: "Implement feature X"
         ↓
Claude Code: "Sure, let me write all this code..."
         ↓
[50+ edits, 20+ files, 2 hours later]
         ↓
Claude Code: "Done! Here's what I did..."
         ↓
User: "This broke Y, missed Z, forgot about A..."
         ↓
[Context lost, guardrails forgotten, scope crept]
```

**Problems:**
- Single agent context gets bloated
- Guardrails from CLAUDE.md forgotten mid-task
- No second pair of eyes
- Scope creep undetected
- Verification skipped under time pressure
- Quality degrades as context grows

### The Pattern (What Should Happen)

```
User: "Implement feature X"
         ↓
Claude Code (Orchestrator): "Let me plan this..."
         ↓
[Creates GSD plan with 5 tasks]
         ↓
Claude Code: "Spawning sub-agent for Task 1..."
         ↓
Sub-Agent 1: [Executes Task 1 with fresh context + specific guardrails]
         ↓
Claude Code: "Reviewing Task 1 output..."
         ↓
[Verifies against plan, checks guardrails]
         ↓
Claude Code: "Task 1 verified. Spawning sub-agent for Task 2..."
         ↓
[Repeat with review gates between each task]
```

**Benefits:**
- Each sub-agent has fresh, focused context
- Orchestrator maintains strategic view
- Review gates catch drift
- Guardrails enforced at each handoff
- Verification built into workflow
- Quality maintained throughout

---

## Orchestrator Responsibilities

### 1. PLAN (Before Any Work)

```
[ ] Understand the full request
[ ] Break into discrete, delegatable tasks
[ ] Identify dependencies between tasks
[ ] Create GSD plan or task breakdown
[ ] Identify which sub-agent type for each task
[ ] Define success criteria for each task
```

### 2. DELEGATE (Spawn Sub-Agents)

```
[ ] Write clear, scoped prompts for sub-agents
[ ] Include relevant context from files (not full history)
[ ] Specify guardrails and constraints
[ ] Define expected output format
[ ] Set verification criteria
```

### 3. REVIEW (After Each Task)

```
[ ] Did sub-agent stay in scope?
[ ] Did output meet success criteria?
[ ] Were guardrails followed?
[ ] Does output align with overall plan?
[ ] Any drift that needs correction?
```

### 4. VERIFY (Before Claiming Done)

```
[ ] All tasks completed?
[ ] Integration between tasks correct?
[ ] End-to-end behavior verified?
[ ] No regressions introduced?
[ ] Documentation updated?
```

### 5. COURSE-CORRECT (When Things Drift)

```
[ ] Pause execution
[ ] Re-read CLAUDE.md for guardrails
[ ] Re-read original request
[ ] Identify where drift occurred
[ ] Adjust plan
[ ] Resume with corrections
```

---

## When to Delegate vs. Do Directly

### ALWAYS DELEGATE

| Task Type | Sub-Agent Type | Why |
|-----------|---------------|-----|
| Multi-file edits | Task (Explore) → Task (general-purpose) | Fresh context per task |
| Research/exploration | Task (Explore) | Specialized for search |
| Code implementation | Task (general-purpose) | Focused execution |
| Test writing | Task (general-purpose) | Isolated concern |
| Documentation | Task (general-purpose) | Separate from code |
| Complex debugging | Task (gsd-debugger) | Systematic approach |

### OK TO DO DIRECTLY

| Task Type | Why OK |
|-----------|--------|
| Single file, <20 line edit | Too small to delegate |
| Reading a single file | Information gathering |
| Running a single command | Quick verification |
| Answering a question | No execution needed |
| Planning | Orchestrator's job |

### RULE OF THUMB

```
If a task will take >5 tool calls → DELEGATE
If a task touches >2 files → DELEGATE
If a task requires remembering context from 10+ messages ago → DELEGATE
If you feel yourself "getting into the weeds" → STOP, DELEGATE
```

---

## Sub-Agent Types and When to Use

### Explore Agent
```
Use for: Finding files, understanding codebase structure, searching
Trigger: "Where is X?", "How does Y work?", "Find all Z"
Thoroughness: quick / medium / very thorough
```

### General-Purpose Agent
```
Use for: Implementation, edits, complex tasks requiring multiple tools
Trigger: "Implement X", "Fix Y", "Add Z"
```

### Plan Agent
```
Use for: Designing implementation approach, architecture decisions
Trigger: "How should we build X?", "What's the best approach for Y?"
```

### GSD Agents
```
gsd-debugger: Systematic debugging with checkpoints
gsd-executor: Execute plans with atomic commits
gsd-verifier: Verify phase completion
gsd-planner: Create detailed phase plans
```

### Domain-Specific Agents
```
code-reviewer: Review completed work against plan
code-simplifier: Simplify and refine code
```

---

## The Review Gate

After EVERY sub-agent completes, the orchestrator MUST:

```
┌────────────────────────────────────────────────────────────────────┐
│  REVIEW GATE CHECKLIST                                             │
├────────────────────────────────────────────────────────────────────┤
│  [ ] Output received from sub-agent                                │
│  [ ] Output matches requested scope (no more, no less)             │
│  [ ] Guardrails from CLAUDE.md were followed                       │
│  [ ] Output integrates with previous work                          │
│  [ ] No scope creep detected                                       │
│  [ ] Quality meets standards                                       │
│  [ ] Ready for next task OR needs correction                       │
└────────────────────────────────────────────────────────────────────┘

If ANY check fails → DO NOT PROCEED
Instead: Correct with targeted follow-up OR re-plan
```

---

## Drift Detection

### Signs You've Become a Worker (Not Orchestrator)

```
⚠️ You've made >10 edits without spawning a sub-agent
⚠️ You've lost track of the original request
⚠️ You're "in the weeds" on implementation details
⚠️ You haven't reviewed CLAUDE.md in 20+ messages
⚠️ You're making "just one more quick fix"
⚠️ Context is getting long and confusing
⚠️ You're not sure what the user originally asked for
```

### Recovery Protocol

When drift is detected:

```
1. STOP all execution immediately
2. Re-read CLAUDE.md (full document)
3. Re-read original user request
4. Summarize: "What was asked?" vs "What have I done?"
5. Identify divergence points
6. Create corrective plan
7. Resume with sub-agents, not direct work
```

---

## Integration with GSD

### GSD + Orchestration Model

```
/gsd:progress          → Orchestrator checks status
/gsd:plan-phase        → Orchestrator creates plan (may spawn Plan agent)
/gsd:execute-phase     → Spawns gsd-executor sub-agents
/gsd:verify-work       → Spawns gsd-verifier sub-agent
```

### Phase Execution Pattern

```
Orchestrator:
  1. /gsd:plan-phase N
  2. Review plan, ensure scope is correct
  3. /gsd:execute-phase N (spawns executor agents)
  4. Review each executor's output at gates
  5. /gsd:verify-work (spawns verifier agent)
  6. Review verification results
  7. Only then: phase complete
```

---

## Task Delegation Template

When spawning a sub-agent, use this format:

```markdown
## Task: [Short Title]

### Context
[Relevant background - what does the agent need to know?]

### Scope
**IN SCOPE:**
- [Exactly what to do]
- [Files to modify]
- [Expected changes]

**OUT OF SCOPE:**
- [What NOT to touch]
- [What to leave alone]

### Guardrails
- [Specific rules from CLAUDE.md that apply]
- [Constraints]

### Expected Output
- [What should the agent produce?]
- [Format requirements]

### Success Criteria
- [How will we know it's done correctly?]
- [Verification steps]
```

---

## Paranoid Orchestration

The orchestrator should operate with **paranoia, curiosity, and uncertainty**:

### Paranoia
```
"Did that sub-agent actually do what I asked?"
"Could this have broken something else?"
"Is this REALLY complete or just superficially done?"
"What edge cases might have been missed?"
```

### Curiosity
```
"Why did the sub-agent make that choice?"
"Is there a better approach I didn't consider?"
"What does CLAUDE.md say about this situation?"
"Should I verify this differently?"
```

### Uncertainty
```
"I'm not 100% sure this is right - let me verify"
"This seems too easy - what am I missing?"
"The user might have meant something different"
"Let me check with the user before proceeding"
```

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR MANTRAS                                              │
├────────────────────────────────────────────────────────────────────┤
│  • I PLAN, I don't implement                                       │
│  • I DELEGATE, I don't do                                          │
│  • I REVIEW, I don't assume                                        │
│  • I VERIFY, I don't trust                                         │
│  • When in doubt, DELEGATE                                         │
│  • When drifting, STOP and re-read CLAUDE.md                       │
│  • Fresh context > bloated context                                 │
│  • Review gates are NON-NEGOTIABLE                                 │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  RED FLAGS (Stop and Course-Correct)                               │
├────────────────────────────────────────────────────────────────────┤
│  • >10 edits without delegation                                    │
│  • Lost track of original request                                  │
│  • Making "just one more quick fix"                                │
│  • Haven't checked CLAUDE.md recently                              │
│  • Context feels overwhelming                                      │
│  • Sub-agent output not reviewed                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Example Workflow

### User Request: "Add user authentication to the API"

**❌ WRONG (Worker Mode):**
```
Claude Code: "Sure, let me add auth..."
[Makes 30 edits across 15 files]
[Forgets CLAUDE.md rules about yacht isolation]
[Introduces security vulnerability]
[Claims "done" without verification]
```

**✅ CORRECT (Orchestrator Mode):**
```
Claude Code: "Let me plan this authentication implementation..."

[Creates plan:]
- Task 1: Research existing auth patterns in codebase
- Task 2: Design auth schema and JWT structure
- Task 3: Implement auth middleware
- Task 4: Add protected route decorators
- Task 5: Write tests
- Task 6: Verify end-to-end

[Delegates Task 1 to Explore agent]
→ Reviews output: "Found existing Supabase auth integration"

[Adjusts plan based on findings]

[Delegates Task 2 to Plan agent]
→ Reviews output: "JWT should include yacht_id per CLAUDE.md"

[Delegates Task 3 to general-purpose agent]
→ Reviews output at gate
→ Checks: yacht isolation maintained? ✓

[Continues with review gates at each step]

[Final verification with gsd-verifier]
→ Reviews: all tests pass, security checks pass

[Only then: "Authentication implementation complete"]
```

---

*Remember: The best orchestrator does the least direct work but ensures the highest quality output through disciplined delegation and review.*
