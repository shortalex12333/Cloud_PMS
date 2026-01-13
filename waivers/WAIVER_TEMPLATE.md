# Waiver: {action_name}

**Status:** ACTIVE | EXPIRED
**Created:** YYYY-MM-DD
**Expiry:** YYYY-MM-DD (Max 90 days from creation)

---

## Guard Information

**Guard:** G1.X - {Guard Name}
**Action:** {action_name}
**Handler File:** {handler_file_name}.py
**Classification:** MUTATE_LOW | MUTATE_MEDIUM | MUTATE_HIGH

---

## Waiver Details

### Reason
{Why we cannot implement this guard right now. Be specific.}

**Examples:**
- "Concurrency control requires version field not yet added to schema"
- "Foreign key validation blocked by pending data migration"
- "Input validation schema not finalized pending UX review"

### Mitigation
{What we're doing instead to maintain safety. Required.}

**Examples:**
- "Using database-level unique constraints to prevent duplicates"
- "Manual validation in frontend, will add backend validation post-migration"
- "Rate limiting at API gateway level temporarily"

### Expiry Date
**Date:** YYYY-MM-DD
**Max Duration:** 90 days from creation

{Waiver automatically expires on this date. CI will block if expired.}

### Owner
**GitHub Handle:** @{engineer_github_handle}
**Team:** Engineering | Product | Security

{Owner is responsible for resolving this before expiry.}

---

## Acceptance Criteria

{What must be true to remove this waiver?}

**Checklist:**
- [ ] {Criterion 1 - e.g., "Schema migration completed"}
- [ ] {Criterion 2 - e.g., "Version field added to table"}
- [ ] {Criterion 3 - e.g., "Handler updated with concurrency control"}
- [ ] {Criterion 4 - e.g., "Tests passing"}
- [ ] Waiver file deleted
- [ ] CI check passes

---

## Context

{Additional context, links to issues, PRs, etc.}

**Related:**
- Issue: #{issue_number}
- PR: #{pr_number}
- Discussion: {link}

---

## Validation

This waiver will be validated by CI on every build.

**CI Checks:**
- [ ] Expiry date not passed
- [ ] All required fields present
- [ ] Guard is G1 (not G0 - G0 cannot be waived)
- [ ] Mitigation is documented

**If this waiver expires, CI will BLOCK deployment.**

---

## Example (DELETE THIS SECTION BEFORE COMMITTING)

```markdown
# Waiver: update_equipment

**Status:** ACTIVE
**Created:** 2026-01-12
**Expiry:** 2026-04-12

---

## Guard Information

**Guard:** G1.1 - Concurrency Control
**Action:** update_equipment
**Handler File:** equipment_mutation_handlers.py
**Classification:** MUTATE_MEDIUM

---

## Waiver Details

### Reason
Concurrency control (optimistic locking) requires a `version` field in the `equipment` table. This field is planned but not yet added due to pending schema migration that consolidates multiple version-related changes.

### Mitigation
Using database-level `updated_at` timestamp checks as interim measure:
- Handler validates `updated_at` matches expected value
- Returns conflict error if timestamps don't match
- Frontend forces user to refresh and retry

This provides partial protection against concurrent updates, though not as robust as version-based locking.

### Expiry Date
**Date:** 2026-04-12
**Max Duration:** 90 days

Migration is scheduled for 2026-03-15. Allows 4 weeks buffer for handler updates and testing.

### Owner
**GitHub Handle:** @alice
**Team:** Engineering

---

## Acceptance Criteria

- [x] Schema migration PR created (#456)
- [ ] Schema migration merged and deployed
- [ ] `version` field added to equipment table
- [ ] Handler updated with version-based locking
- [ ] Tests added for concurrent update scenarios
- [ ] Waiver file deleted
- [ ] CI check passes

---

## Context

**Related:**
- Issue: #445 (Add concurrency control to all MUTATE_MEDIUM handlers)
- PR: #456 (Schema migration: add version fields)
- Discussion: Slack #engineering 2026-01-10

---

## Validation

CI validates this waiver on every build. Will BLOCK if expired.
```

---

**INSTRUCTIONS:**
1. Copy this template to `waivers/{action_name}.md`
2. Fill in all {placeholders}
3. Delete the example section
4. Commit to repo
5. CI will validate on next run
6. Delete this file when guard is implemented

**REMEMBER:** G0 guards CANNOT be waived. Only G1 guards are waiver-eligible.
