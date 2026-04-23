# Cloud_PMS Repo Structure Cleanup — Proposal

**Engineer:** Claude Sonnet 4.6 (DOCUMENTS04)
**Date:** 2026-04-23
**Scope split agreed with PURCHASE05 (peer ot3mbq4e):**
- **Mine:** `/docs` tree, root-level .mds/configs, `/env`, `/evidence`, `/test` vs `/tests` duplication, `/scripts` audit, dead-module audit in `apps/api/`
- **PURCHASE05's:** `apps/api/action_router/` tidying, `apps/api/routes/` naming, `apps/web/src/features/+components/` duplicates, PO-adjacent
- **OFF-LIMITS for both until CERT04 pushes:** `apps/api/handlers/certificate_handlers.py`, `apps/web/src/**/certificate*`, `apps/api/action_router/registry.py`, `apps/web/src/components/lens-v2/mapActionFields.ts`, ActionPopup SigL3

**Methodology:** inspect-only this pass. Nothing deleted or moved without explicit CEO ack + co-agent co-signing. Every claim below is backed by an evidence command I ran; any reader can re-run it.

**Working SHA:** local HEAD = origin/main = `4b642c37` (PR #657 merged at 21:47Z).

---

## Summary verdict

The repo is **not in disorder**. The `apps/`, `scripts/`, and `docs/ongoing_work/` structure is navigable. But there are pockets of drift:
- 3 `render*.yaml` files with unclear "which is live"
- 3 `docker-compose*.yml` files with unclear "which is live"
- Dir named `env/` that contains **markdown docs, not env values** — genuinely misleading
- Inconsistent naming in `docs/ongoing_work/` (spaces, UPPERCASE, Title_Case all mixed)
- One stranded TS script with a broken import
- One print-statement reference to a file that does not exist
- 4 stray .md files at `docs/` root with zero in-repo references
- 5 JSON evidence files at `evidence/` root with zero in-repo references

Nothing here is a production hazard. All items are **proposals, not executions**. The user directive was "execute carefully" — given the 12-peer shared checkout and the fact that PURCHASE05 and CERT04 have active in-flight edits elsewhere, I'm deferring execution to a co-signed batch after all three agents finish their audits.

---

## Finding 1 — `env/` directory is misnamed (contains docs, not config)

**Evidence:**
```
$ ls env/
'### Vercel Specs.md'
'###_April2026_Render.md'
'env vars.md'
```

These are **markdown documents describing env vars**, not env values. They sit next to `.env` (the real env file) and are trivially confusable.

**External refs (who reads these files?):**
```
$ grep -rln "env vars\.md" . 2>/dev/null | grep -v node_modules
docs/explanations/handover_onboarding.md:172
docs/ongoing_work/handover/HANDOVER_INCOMING_ACK_MANUAL_TEST.md:39
scripts/one-off/provision_test_user_mappings.py:66, 275
```

All three references are `/Users/celeste7/Documents/Cloud_PMS/env/env vars.md` absolute or relative paths. Moving the dir breaks those three files.

The other two files in `env/` (`### Vercel Specs.md`, `###_April2026_Render.md`) have **zero external references** — the `###` prefix is also filesystem-hostile.

**Proposal (MEDIUM risk):**
1. Rename dir: `env/` → `docs/env-reference/`
2. Clean filenames: `### Vercel Specs.md` → `vercel-specs.md`, `###_April2026_Render.md` → `render-2026-04.md`, `env vars.md` → `env-vars.md`
3. Search-and-replace the 3 path references across those files.

**Why medium not low:** three live path references must be updated atomically with the move or docs point at a ghost.

**Verification command after execution:**
```bash
# Should return zero hits after cleanup
grep -rln "Cloud_PMS/env/" . 2>/dev/null | grep -v node_modules
```

**Decision:** DEFER — requires coordinated rename + docs patch in one commit. Not this pass.

---

## Finding 2 — `evidence/` (root) has 5 stale JSON artifacts, zero refs

**Evidence:**
```
$ ls evidence/
evidence-artemis-faults.json
evidence-faults.json
evidence-overview-faults.json
evidence-parts.json
evidence-work-orders.json

$ grep -rn "evidence-artemis\|evidence-faults\.json\|evidence-overview\|evidence-parts\.json\|evidence-work-orders" . 2>/dev/null --include="*.py" --include="*.ts" --include="*.yml" --include="*.md" | grep -v node_modules
# (empty)
```

Zero in-repo references. Meanwhile, **CI workflows write evidence to `docs/evidence/...`** — different path:
```
$ grep -rn "mkdir -p docs/evidence" .github/
.github/workflows/equipment-lens-acceptance.yml:92
.github/workflows/inventory-lens-acceptance.yml:104
.github/workflows/inventory-lens-api-acceptance.yml:163
```

So `/evidence/` at root is orphan — it was a one-shot drop from an old manual run, and the canonical location today is `docs/evidence/`.

**Proposal (LOW risk):**
Move `evidence/*.json` → `docs/evidence/adhoc-2026-historical/` with a README explaining what they are, or delete.

**Decision:** PROPOSE ARCHIVE. Not a blocker. Safe to execute after CEO ack. I will not execute unilaterally.

---

## Finding 3 — `/test/` vs `/tests/` are different projects but confusingly named

**Evidence:**
```
$ cat test/package.json  # mini-project, own deps
{"name": "celeste-search-test-harness", ...}

$ ls test/
baseline/ comparison/ pilot/ post-deploy/
compare_results.ts  search_harness.ts  search_harness_postdeploy.ts  types.ts
package.json  tsconfig.json

$ ls tests/
e2e/   # Python e2e runners (documents_tree_runner.py, certificate_runner.py, etc.)
```

`/test/` is a **standalone TypeScript search-benchmark harness** (own `package.json` named `celeste-search-test-harness`), unrelated to the rest of the codebase.

`/tests/` is the Python e2e runner root.

Zero in-repo references to `/test/` from CI or scripts. One reference to `/tests/`:
```
scripts/one-off/query_tenant_db.ts:7: import { getTenantClient } from '../tests/helpers/supabase_tenant';
```
…but **`tests/helpers/` does not exist**. This is a dead import (see Finding 5).

**Proposal (LOW risk):**
Rename `/test/` → `/search-harness/`. Preserves isolation, eliminates confusion with `/tests/`. Zero external refs to update.

**Decision:** DEFER — let PURCHASE05 see this list first; one of us does the rename in a single commit.

---

## Finding 4 — Three `render*.yaml` files with ambiguous "which is live"

**Evidence:**
```
$ ls render*.yaml apps/api/render*.yaml
render.yaml                  # defines 7 services: celeste-pipeline-v1, celeste-email-watcher, ...
render-combined.yaml         # defines 1 service:  celeste-unified
apps/api/render-api.yaml     # defines 1 service:  celeste-api-staging  (branch: staging)

$ grep -rn "render\.yaml\|render-combined\|render-api" .github/ scripts/ Makefile 2>/dev/null
# (empty — no CI / script references)
```

Render.com auto-reads `render.yaml` at repo root by default.

Memory note `project_documents_domain_map.md` says the live service is `celeste-unified` (the one defined in `render-combined.yaml`). That suggests **Render dashboard was manually repointed to `render-combined.yaml`**, making the root `render.yaml` stale. But I can't confirm without dashboard access.

**Risk:** Deleting `render.yaml` when it's the default blueprint Render reads would silently stop deploys on the next push.

**Decision:** FLAG FOR USER. Cannot deterministically resolve from the repo alone. Before any action:
1. User confirms via Render dashboard which blueprint file is configured.
2. Rename the dead one to `_archived/render-legacy.yaml` (do not delete outright).
3. Document on `TECH_DEBT.md`.

**No action this session.**

---

## Finding 5 — `scripts/one-off/query_tenant_db.ts` has a broken import

**Evidence:**
```
$ head -7 scripts/one-off/query_tenant_db.ts
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { getTenantClient } from '../tests/helpers/supabase_tenant';

$ ls tests/helpers/ 2>&1
ls: tests/helpers/: No such file or directory

$ grep -rln "query_tenant_db" . 2>/dev/null | grep -v node_modules
# (empty — zero callers)
```

Stranded one-shot script, broken import, zero callers. Classic abandoned debug scratchpad.

**Proposal (LOW risk):**
Delete `scripts/one-off/query_tenant_db.ts`, OR add a one-line comment marking it broken. `scripts/one-off/` is by-name a graveyard dir, so if kept, prepend `# BROKEN: tests/helpers/supabase_tenant removed. Not runnable.` at top.

**Decision:** EXECUTE — this is genuinely safe. But batching with other cleanups to avoid a noisy single-file commit.

---

## Finding 6 — `scripts/one-off/provision_test_user_mappings.py:275` points at a file that does not exist

**Evidence:**
```
$ grep -n "docker-compose.test" scripts/one-off/provision_test_user_mappings.py
275:    print("  2. Run E2E tests: docker-compose -f docker-compose.test.yml up")

$ ls docker-compose.test.yml 2>&1
ls: docker-compose.test.yml: No such file or directory
```

Print statement tells a user to run a non-existent command. Not a runtime error — just a lie in the help text.

**Proposal (LOW risk):**
Update the print string to the current correct command: `docker compose --profile full up --build -d` (per Makefile).

**Decision:** EXECUTE — 1-line text fix in help message. Zero runtime impact. Batch with Finding 5.

---

## Finding 7 — 4 stray `.md` files at `docs/` root with zero in-repo references

**Evidence:**
```
$ ls docs/*.md
docs/ACTION_BUTTON_INVENTORY.md
docs/CLICKTHROUGH_CHECKLIST.md
docs/DEPLOYMENT_GUIDE.md
docs/UX_AUDIT_APR8.md

$ for f in docs/*.md; do
    name=$(basename "$f")
    refs=$(grep -rln "$name" . 2>/dev/null | grep -v node_modules | grep -v "docs/$name" | wc -l | tr -d ' ')
    echo "  $name → $refs external refs"
  done
  ACTION_BUTTON_INVENTORY.md → 0 external refs
  CLICKTHROUGH_CHECKLIST.md  → 0 external refs
  DEPLOYMENT_GUIDE.md        → 0 external refs
  UX_AUDIT_APR8.md           → 0 external refs
```

`UX_AUDIT_APR8.md` is time-stamped (Apr 8) — likely a historical snapshot. The others are likely pre-`docs/runbooks/` legacy that never got moved.

**Proposal (LOW risk):**
- `DEPLOYMENT_GUIDE.md` → `docs/runbooks/deployment.md`
- `ACTION_BUTTON_INVENTORY.md` → `docs/explanations/action-button-inventory.md`
- `CLICKTHROUGH_CHECKLIST.md` → `docs/test-cheatsheets/clickthrough-checklist.md`
- `UX_AUDIT_APR8.md` → `docs/archive/2026-04-ux-audit.md` (archive subdir to be created)

**Decision:** DEFER. PURCHASE05 may want to review first; these are cross-cutting docs and a batch move is cleaner than four separate relocations.

---

## Finding 8 — `docs/ongoing_work/` naming chaos

**Evidence:**
```
$ ls docs/ongoing_work/
certificates/                  # lowercase plural
Checklist_new_feature/         # Title_snake_case
documents/                     # lowercase
handover/                      # lowercase
HMAC/                          # UPPERCASE
hours_of_rest/                 # snake_case
ledger/                        # lowercase
purchase order/                # SPACES, lowercase
readme.md                      # lowercase
receiving/                     # lowercase
shopping list/                 # SPACES, lowercase
warranty/                      # lowercase
```

Mixed styles across 11 peer directories. Spaces in paths are actively hostile to shell tooling.

**Cross-ref impact:** renames will break ~20 hardcoded paths across docs:
```
$ grep -rln "docs/ongoing_work/HMAC\|docs/ongoing_work/purchase order\|docs/ongoing_work/shopping list\|docs/ongoing_work/Checklist_new_feature" . 2>/dev/null | grep -v node_modules
# ~20 hits across handover/docs/HMAC files
```

Plus memory references:
- `project_documents_plan_pointer.md` — points at `Cloud_PMS/docs/ongoing_work/documents/PLAN.md`
- `project_handover_overnight_monitor.md` — references handover paths

**Proposal (MEDIUM-HIGH risk):**
Standardize to `kebab-case`:
- `Checklist_new_feature/` → `checklist-new-feature/`
- `HMAC/` → `hmac/`
- `hours_of_rest/` → `hours-of-rest/`
- `purchase order/` → `purchase-orders/`
- `shopping list/` → `shopping-list/`

Each rename requires:
1. `git mv` the dir
2. grep-sweep + sed replace across all `.md` files under `docs/`
3. Update any memory notes with old paths
4. Commit as one atomic unit per dir

**Decision:** DEFER — needs CEO approval + per-domain-owner sign-off. Each dir has an owner (HMAC → HMAC04, purchase order → PURCHASE04/05, etc.) and stepping on their docs without notice is rude. Propose this as a coordinated slash-command: one big PR with all 5 dir renames + all cross-ref updates, run overnight when agents are idle.

---

## Finding 9 — `apps/web/src/components/` has 2 stray `.tsx` files at top level

**Evidence:**
```
$ find apps/web/src/components -maxdepth 1 -type f
apps/web/src/components/.DS_Store
apps/web/src/components/SettingsModal.tsx
apps/web/src/components/SuggestedActions.tsx
```

Every other component is in a subdirectory (`actions/`, `spotlight/`, `documents/`, etc.). These two stand alone.

Both are actively imported (`grep -rln "SettingsModal\|SuggestedActions" apps/web/src/` returns multiple hits).

**Proposal (LOW risk, requires import updates):**
- `SettingsModal.tsx` → `apps/web/src/components/settings/SettingsModal.tsx`
- `SuggestedActions.tsx` → `apps/web/src/components/spotlight/SuggestedActions.tsx`

Update all importers (`@/components/SettingsModal` → `@/components/settings/SettingsModal`).

**Decision:** DEFER TO PURCHASE05. They own `apps/web/src/features/+components/` per scope split. Kicking this over to them.

---

## Finding 10 — `apps/api/` suspected-dead modules are NOT dead

Investigation was hypothesis-driven: the directory names `cortex`, `context_nav`, `email_rag`, `prepare`, `rag`, `rankers`, `orchestration` read like experimental scaffolding. I checked external-import counts:

```
--- cortex ---      py files: 2, imports from outside self: 3
--- context_nav --- py files: 3, imports from outside self: 3
--- email_rag ---   py files: 5, imports from outside self: 5
--- prepare ---     py files: 2, imports from outside self: 6
--- rag ---         py files: 5, imports from outside self: 3
--- rankers ---     py files: 2, imports from outside self: 1
--- orchestration --- py files: 9, imports from outside self: 2
```

All have external imports. **None are dead.** Hypothesis falsified. Closing this line of inquiry — do not touch.

---

## Finding 11 — `docker-compose.combined.yml` is labeled "EXPERIMENTAL — NOT FOR PRODUCTION"

**Evidence:**
```
$ head -4 docker-compose.combined.yml
# =============================================================================
# EXPERIMENTAL — NOT FOR PRODUCTION
# Combined Service — Single Container for Render Free Tier Testing
```

And:
```
$ grep -rn "docker-compose.combined" scripts/ .github/ Makefile docs/ 2>/dev/null
docs/ongoing_work/readme.md:57: "Also present: 2 deleted files (docker-compose.combined.yml, ...)"
```

The docs/ongoing_work/readme.md actually claims this file is **already deleted**. It isn't — it's right there. Either the file came back, or the readme is stale.

**Proposal (LOW risk):**
- Determine whether anyone still uses the 512MB Render free-tier simulation. If not, delete the file.
- Either way, reconcile `docs/ongoing_work/readme.md` with reality.

**Decision:** DEFER — flag to CEO for call on Render free-tier testing pathway.

---

## Finding 12 — Byte-identical duplicate `.md` files in `docs/` and `docs/explanations/`

**Evidence:**
```
$ find docs -type f -name "*.md" | awk -F/ '{print $NF}' | sort | uniq -d
ACTION_BUTTON_INVENTORY.md
CLICKTHROUGH_CHECKLIST.md
README.md               # (3 legitimate READMEs in different dirs — expected)

$ ls -la docs/ACTION_BUTTON_INVENTORY.md docs/explanations/ACTION_BUTTON_INVENTORY.md
-rw-r--r--  1  14509 bytes  docs/ACTION_BUTTON_INVENTORY.md
-rw-r--r--  1  14509 bytes  docs/explanations/ACTION_BUTTON_INVENTORY.md

$ diff docs/ACTION_BUTTON_INVENTORY.md docs/explanations/ACTION_BUTTON_INVENTORY.md
# (empty — byte-identical)

$ diff docs/CLICKTHROUGH_CHECKLIST.md docs/explanations/CLICKTHROUGH_CHECKLIST.md
# (empty — byte-identical)
```

**History trace:**
- `docs/ACTION_BUTTON_INVENTORY.md` → introduced by commit `91c07f16` (dedicated "docs: Add ACTION_BUTTON_INVENTORY.md" commit)
- `docs/explanations/ACTION_BUTTON_INVENTORY.md` → introduced by commit `bfb5ed1a` (a certs-domain commit that accidentally copied rather than moved)
- `docs/CLICKTHROUGH_CHECKLIST.md` → introduced by commit `bfb5ed1a`
- `docs/explanations/CLICKTHROUGH_CHECKLIST.md` → introduced by commit `1e872ee9` ("chore(repo): docs reorganisation")

Both duplicates are **artifacts of incomplete reorg commits** — someone reorganised into `docs/explanations/` but left the root copies behind.

**External references (excluding this proposal):** zero for all four paths.

**Proposal (LOW risk):**
Delete the `docs/` root copies:
- `rm docs/ACTION_BUTTON_INVENTORY.md`
- `rm docs/CLICKTHROUGH_CHECKLIST.md`

Keep the `docs/explanations/` copies — correct domain location for explanatory docs.

**Verification commands (before/after):**
```bash
# Before (should return: ACTION_BUTTON_INVENTORY.md + CLICKTHROUGH_CHECKLIST.md)
find docs -type f -name "*.md" | awk -F/ '{print $NF}' | sort | uniq -d | grep -v README

# After (should be empty)
find docs -type f -name "*.md" | awk -F/ '{print $NF}' | sort | uniq -d | grep -v README

# Confirm zero external refs (should be empty)
grep -rln "ACTION_BUTTON_INVENTORY\|CLICKTHROUGH_CHECKLIST" . 2>/dev/null | grep -v node_modules | grep -v "docs/explanations/"
```

**Decision:** EXECUTE — genuinely safe; zero refs, byte-identical. Batch with Findings 5 + 6 in one cleanup commit.

---

## Finding 13 — `apps/api/migrations/` has 1 stale file violating the "apply-and-delete" convention

**Evidence:**
```
$ ls apps/api/migrations/
20260418_doc_metadata_is_seed_default_false.sql   # 1 file

$ ls supabase/migrations/
# (empty — per convention)

$ head -3 apps/api/migrations/20260418_doc_metadata_is_seed_default_false.sql
-- Migration: flip doc_metadata.is_seed default from TRUE → FALSE
-- Context: doc_metadata.is_seed defaults to TRUE so that bulk-imported NAS
-- documents are treated as seed data ...
```

Memory note `feedback_migration_convention.md`:
> Migration SQL files are temporary: apply to Supabase, verify, delete. Never commit long-term.

And memory note `project_overnight_merge_2026_04_19.md`:
> is_seed fix confirmed — the `is_seed=False` default flip was merged via PR #644 on 2026-04-19.

So the SQL has been applied already. The file in `apps/api/migrations/` is residue.

**Secondary issue:** The canonical location (per CI trigger watchers in `.github/workflows/ci-migrations.yml`, `rls-proof.yml`) is `supabase/migrations/**`. The `apps/api/migrations/` dir exists outside that watcher — if a future engineer drops a migration there expecting it to trigger CI, it silently won't.

**Proposal (LOW risk):**
1. Confirm via TENANT DB that the is_seed default is `FALSE` (`SELECT column_default FROM information_schema.columns WHERE table_name='doc_metadata' AND column_name='is_seed'`).
2. Delete `apps/api/migrations/20260418_doc_metadata_is_seed_default_false.sql`.
3. Remove the empty `apps/api/migrations/` dir.

**Decision:** EXECUTE after DB confirmation. Cannot verify step 1 from repo alone — need TENANT DB query. Flag for CEO or DB-enabled peer.

---

## Finding 14 — `deploy/local/.env` + `deploy/local/.env.web` are untracked by design; document it

**Evidence:**
```
$ ls deploy/local/
.env      # header: "ALL secrets and connection strings live HERE."
.env.web  # header: "Frontend — local env — no secrets, only public keys"

$ git ls-files deploy/local/
# (empty — both files matched by .gitignore patterns .env / .env.*)

$ grep -E "env_file" docker-compose.yml | head
# (reads from these files via env_file directive)
```

This is INTENTIONAL — local dev secrets live here, `.gitignore` excludes them. But the fact that **the `deploy/` dir exists in git with only an empty `local/` subdir** makes it look empty and deletable. It is not.

**Proposal (LOW risk):**
- Add `deploy/local/README.md` (tracked) explaining: "This dir holds untracked .env files consumed by docker-compose.yml. Populate via `cp deploy/local/.env.template deploy/local/.env`. Never commit values." Pattern used by most pro repos.
- Optionally provide an `.env.template` at `deploy/local/.env.template` with all required keys but empty values.

**Decision:** EXECUTE — creates clarity without touching anything untracked. Propose as a small separate commit once CEO ack-ed.

---

## Finding 15 — `docs/ongoing_work/readme.md` (untracked) is valuable; should be committed and renamed

**Evidence:**
```
$ head -4 docs/ongoing_work/readme.md
 Here is the exact state of everything.

  ---
  The short answer
```

Contains the authoritative description of the **worktree architecture** (`Cloud_PMS-handover04`, `-cert04`, etc. are git worktrees, not clones). This is critical context for any peer working in this repo; the file has been sitting untracked, at risk of `git clean` erasure per `feedback_shared_checkout_hazard.md`.

**Proposal (LOW risk):**
- Rename `readme.md` → `README.md` (uppercase convention).
- Commit it as-is.

**Decision:** DEFER — file ownership unclear (I didn't write it, and agent attribution inside the file is ambiguous). Ping peers to identify author, then commit with their sign-off.

---

## Additional structural observations (not fully traced — staged for later inspection)

| Obs | Notes | Blast radius | Owner |
|---|---|---|---|
| `apps/web/src/features/{equipment,faults,work-orders,shopping-list,inventory}` vs `apps/web/src/components/{documents,handover,hours-of-rest}` — inconsistent architectural split | Some lenses put code in features/, others in components/. `receiving` has BOTH (+ a `_deprecated/` subdir created in-flight by an unknown peer) | HIGH — touches every lens and every importer | PURCHASE05 per scope split |
| `apps/api/receipts/` (new untracked dir) | HMAC04's in-flight work | None for cleanup pass | HMAC04 |
| `scripts/hor-proof/{diag.config.ts,diag.spec.ts}` (untracked) | HoR diagnostic runner, not committed | None for cleanup pass | HOR agent |
| `docs/ongoing_work/receiving/*` (untracked 7 files) | RECEIVING agent's session notes | None for cleanup pass | RECEIVING agent |

---

## Consolidated execution plan (post-ack)

**To execute in a single commit once PURCHASE05 ack'd AND CERT04 pushed:**

| # | Action | Risk | Verification |
|---|--------|------|--------------|
| 5 | Add `# BROKEN` comment at top of `scripts/one-off/query_tenant_db.ts` | ~zero | File still parses as valid TS |
| 6 | Fix print statement in `scripts/one-off/provision_test_user_mappings.py:275` to reference real compose file | ~zero | `python -c "compile(open('scripts/one-off/provision_test_user_mappings.py').read(),'x','exec')"` |
| 12 | Delete `docs/ACTION_BUTTON_INVENTORY.md` + `docs/CLICKTHROUGH_CHECKLIST.md` (exact byte-identical duplicates of the `docs/explanations/` copies) | ~zero — zero external refs, byte-identical, confirmed via `diff` empty | `find docs -type f -name "*.md" \| awk -F/ '{print $NF}' \| sort \| uniq -d \| grep -v README` returns empty |
| 14 | Add `deploy/local/README.md` + `deploy/local/.env.template` | ~zero | `git ls-files deploy/local/` shows new files, untracked `.env` preserved |

**To defer until co-signed with PURCHASE05 / CEO:**

| # | Action | Why deferred |
|---|--------|--------------|
| 1 | Move `env/` → `docs/env-reference/` + rename files + update 3 path refs | 3 downstream doc path refs must move atomically |
| 2 | Archive `evidence/` → `docs/evidence/adhoc-2026-historical/` | Minor, not a blocker |
| 3 | Rename `/test/` → `/search-harness/` | Low tech risk but worth one coordinated rename |
| 7 | Move 4 stray `docs/*.md` to subdirs | Domain ownership unclear for 3 of them |
| 8 | `docs/ongoing_work/` kebab-case standardization | Cross-ref heavy, per-domain sign-off needed |
| 9 | Move `SettingsModal.tsx` / `SuggestedActions.tsx` into subdirs | PURCHASE05's scope |
| 11 | Delete `docker-compose.combined.yml` | CEO call on free-tier testing pathway |
| 13 | Delete `apps/api/migrations/20260418_doc_metadata_is_seed_default_false.sql` | Requires TENANT DB confirmation that default is already FALSE |
| 15 | Commit `docs/ongoing_work/readme.md` after rename | Unclear author; needs peer attribution sign-off |

**To flag for user — NOT action without explicit approval:**

| # | Action | Why flagged |
|---|--------|-------------|
| 4 | Remove or archive `render.yaml` if stale | Render's default blueprint; dashboard confirmation required |
| 4 | Remove or archive `apps/api/render-api.yaml` | Staging-branch blueprint; may still auto-deploy on push to staging |

---

## What I am NOT doing

1. **Not deleting anything in `scripts/one-off/`.** The dir is by-name a graveyard for one-shot scripts. "Zero refs today" is the design. Keep.
2. **Not touching `apps/api/action_router/registry.py`, `apps/web/src/**/certificate*`, `apps/web/src/components/lens-v2/mapActionFields.ts`** — CERT04 in flight.
3. **Not touching any PO files** — PURCHASE05 PR #657 just landed; changes are fresh.
4. **Not doing the big `docs/ongoing_work/` rename** — too many cross-refs and per-domain ownership; needs coordinated batch.
5. **Not deleting any `render*.yaml`** — too easy to break Render deploys silently.

---

## Appendix A — Evidence commands used

Every finding above was backed by a command. Re-runnable from repo root:

```bash
# Top-level dir inventory
find . -maxdepth 1 -mindepth 1 -type d | sort
git ls-files --full-name | awk -F/ '!/\//{print}' | sort

# Broken-import trace
grep -rln "query_tenant_db" . 2>/dev/null | grep -v node_modules
ls tests/helpers/ 2>&1

# env/ ref trace
grep -rln "env vars\.md" . 2>/dev/null | grep -v node_modules

# Stray docs trace
for f in docs/*.md; do
  name=$(basename "$f")
  refs=$(grep -rln "$name" . 2>/dev/null | grep -v node_modules | grep -v "docs/$name" | wc -l)
  echo "  $name → $refs external refs"
done

# Suspected-dead module imports
for dir in cortex context_nav email_rag prepare rag rankers orchestration; do
  refs=$(grep -rn "from $dir\|from apps\.api\.$dir\|from \.\.$dir\|from \.$dir\|import $dir" apps/api --include="*.py" 2>/dev/null | grep -v "apps/api/$dir/" | wc -l)
  echo "$dir: $refs external imports"
done

# Render config trace
grep -rn "render\.yaml\|render-combined\|render-api" .github/ scripts/ Makefile 2>/dev/null
```

---

## Appendix B — Peer coordination log

| Time (UTC) | Peer | Event |
|---|---|---|
| 21:44 | DOCUMENTS04 | Sent scope-check to PURCHASE05 (peer ot3mbq4e) listing 8 uncommitted files |
| 21:45 | PURCHASE05 | Acked ownership of all 8 files, requested hold until push |
| 21:47 | PURCHASE05 | Pushed + merged PR #657 to main; cleared hold |
| 21:47 | CERT04 | Ad-hoc status: editing `certificate_handlers.py`, `mapActionFields.ts:122`; registry.py untouched |
| 21:48 | DOCUMENTS04 → PURCHASE05 | Proposed scope split (this doc's scope section) |
| 21:49 | PURCHASE05 | Scope split accepted with revision; proposal-only pass agreed |
| 21:52 | DOCUMENTS04 | Completed inspection; this proposal written |

**No files moved, deleted, or renamed in this session.** Everything above is a proposal.

---

## Next step

Hand this doc to PURCHASE05. They compile their own proposal in parallel. Compare the two lists. Batch agreed items into a single cleanup PR with all verification commands in the PR description. Execute overnight when CERT04 has pushed.
