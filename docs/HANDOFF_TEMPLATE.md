# HANDOFF TEMPLATE — CHECKPOINT FORMAT

> **Use this format for all handoffs. No extra commentary.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Template

```markdown
# HANDOFF CHECKPOINT

## Phase
[Phase name]

## Status
[COMPLETE | IN_PROGRESS | BLOCKED]

## Verified Complete
- [x] Item 1 — `file/path.ts`
- [x] Item 2 — `file/path.ts`

## Incomplete/Broken
- [ ] Item 1 — Reason why
- [ ] Item 2 — Reason why

## Files Touched
- `path/to/file1.ts` — Description of changes
- `path/to/file2.css` — Description of changes

## Tests Run
| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| Test 1 | x/x | x | |
| Test 2 | x/x | x | |
| Build | PASS/FAIL | - | |

## Evidence
- Screenshot: `~/Desktop/filename.png`
- PR: #XXX (merged/pending)
- Log: `path/to/output.log`

## Next Single Action
[One specific action to take next]

## Backlog (Out of Scope)
- Item 1 — Why it's out of scope
- Item 2 — Why it's out of scope
```

---

## Rules

1. **No extra commentary** — Only the structured format above
2. **Evidence required** — Every "verified complete" item needs proof
3. **One next action** — Not a list, just the single next step
4. **Out of scope is real** — Don't touch backlog items until assigned

---

## When to Create Handoff

1. At ~70% context usage (MANDATORY)
2. At phase completion
3. Before switching to unrelated work
4. When blocked on external dependency

---

## Context Usage Warnings

| Usage | Action |
|-------|--------|
| ~65% | Warn "approaching checkpoint" |
| ~70% | STOP new work, begin checkpoint |
| 75%+ | HARD STOP, output checkpoint, halt |

---

## GSD Integration

When using GSD, handoffs align with:
- `/gsd-pause-work` — Creates handoff automatically
- `/gsd-resume-work` — Restores from handoff
- `STATE.md` — Tracks position across sessions
- `{phase}-SUMMARY.md` — Created after execution

---

## Example Handoff

```markdown
# HANDOFF CHECKPOINT

## Phase
Search Bar UX (ChatGPT Parity)

## Status
COMPLETE

## Verified Complete
- [x] Border removed — `SpotlightSearch.tsx:786`
- [x] Shadow tokenized — `globals.css:210, 317`
- [x] Mic icon removed — Import deleted from SpotlightSearch.tsx
- [x] Search icon removed — Import deleted from SpotlightSearch.tsx
- [x] Category buttons removed — Secondary search surface JSX deleted

## Incomplete/Broken
(none)

## Files Touched
- `apps/web/src/components/spotlight/SpotlightSearch.tsx` — Removed icons, buttons, border
- `apps/web/src/styles/globals.css` — Added `--celeste-spotlight-shadow` token

## Tests Run
| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| Build | PASS | - | `npm run build` |
| TypeScript | PASS | - | `npx tsc --noEmit` |

## Evidence
- Screenshot: `~/Desktop/spotlight-tokenized-final.png`
- PRs: #327, #328, #330 (merged)

## Next Single Action
Await next task assignment

## Backlog (Out of Scope)
- Light mode screenshot verification
- Mobile responsiveness testing
```
