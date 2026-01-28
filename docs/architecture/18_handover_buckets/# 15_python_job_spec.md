# 15_python_job_spec.md

# Python Job Specification — Handover Pipeline

This document defines the **Python job architecture** responsible for generating, updating, and exporting handover drafts in Celeste.

The job layer replaces the current n8n automation.  
It must be deterministic, idempotent, auditable, and failure-safe.

---

## Core responsibility

Python jobs are responsible for:

- assembling handover drafts
- running summarisation and grouping logic
- creating command synthesis sections
- maintaining draft state
- preparing exports after sign-off
- never bypassing review or acceptance

No job may publish or send a handover.

---

## Job types

### 1) Draft Generation Job

**Purpose:**  
Assemble a new draft from candidate handover entries.

**Trigger:**

- Scheduled (end of watch, end of day)
- Manual request by authorized user

**Steps:**

1. Fetch candidate handover_entries  
2. Apply domain grouping  
3. Apply overlap rules  
4. Detect duplicates  
5. Summarise narratives  
6. Rank by risk  
7. Generate command synthesis  
8. Create handover_draft + sections + items  
9. Set draft state = DRAFT  

**Idempotency rule:**

If no new entries exist since last draft:
- do not create a new draft
- return existing DRAFT

---

### 2) Draft Regeneration Job

**Purpose:**  
Regenerate an existing draft after edits or merge confirmations.

**Trigger:**

- User requests regenerate
- Classification corrections applied

**Steps:**

- Reload draft source entries
- Reapply grouping and ranking
- Preserve user edits
- Update draft items
- Maintain draft_id

No regeneration allowed after ACCEPTED state.

---

### 3) Command Synthesis Refresh Job

**Purpose:**  
Update Command bucket summaries when underlying entries change.

**Trigger:**

- New high-risk entry added
- Conflict resolved
- Draft regenerated

Must not alter any non-command section.

---

### 4) Export Preparation Job

**Purpose:**  
Generate HTML/PDF snapshot after SIGNED state.

**Trigger:**

- Draft enters SIGNED state

**Steps:**

- Load signed draft
- Render templates
- Generate PDF/HTML
- Store in signed storage path
- Record document_hash
- Create handover_export record if requested

Must not run before SIGNED.

---

## Execution model

- Jobs run in isolated workers
- No shared mutable state
- All writes occur through Supabase transactions
- All failures logged

---

## Locking rules

- Only one DRAFT per vessel at a time
- Draft generation job must acquire vessel lock
- If lock exists, job exits gracefully

---

## Retry behavior

If a job fails:

- no partial draft published
- no state transition occurs
- retry allowed
- failure logged

---

## Observability

Each job must log:

- job_id
- job_type
- vessel_id
- start_time / end_time
- status (success/failure)
- error trace if failed

---

## Security

Jobs execute with service credentials:

- read/write handover tables
- read ledger and source docs
- write storage snapshots

Jobs never impersonate human users.

---

## Performance targets

- Draft generation < 30 seconds for 500 entries
- Export rendering < 10 seconds
- Lock wait < 5 seconds

If exceeded, performance warning logged.

---

## Non-negotiable

- No job may alter signed handovers
- No job may publish unsigned drafts
- No job may skip trace creation
- No job may delete evidence

Automation assists.  
Authority remains human.

---
```
