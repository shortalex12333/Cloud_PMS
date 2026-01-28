```markdown
# 18_handover_bucket

This folder defines **how Celeste captures, builds, stores, reviews, and signs handovers**.

Handover in Celeste is not a task list.  
Not a planning board.  
Not a performance tracker.

Handover is **continuity of operational reality**.

If this folder is implemented correctly:

- Knowledge survives crew rotation  
- Context is not lost in PDF exports  
- Reports are traceable to real events  
- No handover is published without human acceptance  
- No system silently decides what “matters”

---

## Core Principle

**The ledger records what happened.  
The handover explains what matters.**

Ledger = immutable facts  
Handover = curated narrative

One never overwrites the other.

---

## Why this folder exists

Traditional yacht software produces handover reports by:

- scraping emails
- grouping by vague categories
- auto-generating task lists
- emailing PDFs
- losing source context

The result looks professional  
but is **un-auditable, lossy, and untrusted**.

Celeste’s handover model fixes this by enforcing:

- explicit capture of handover candidates  
- human acceptance before publication  
- permanent linkage to source events  
- stable bucket taxonomy  
- role-aware grouping  
- export only after sign-off

---

## What this folder contains

This folder is split into four layers:

### 1) Principles and taxonomy
Defines what buckets exist and how overlap works.

- `00_principles.md`
- `01_bucket_taxonomy.md`
- `02_domain_to_bucket_map.md`
- `03_role_bucket_biasing.md`
- `04_overlap_rules.md`

These ensure classification never degrades into  
“General Outstanding”.

---

### 2) Handover lifecycle
Defines how drafts are built, reviewed, accepted, and locked.

- `05_handover_draft_model.md`
- `06_add_to_handover_intent.md`
- `07_generation_pipeline.md`
- `08_review_accept_signoff.md`
- `09_export_email_print.md`

These enforce:

- no silent publishing  
- no auto-removal of content  
- explicit human responsibility

---

### 3) Implementation layer
Defines database, storage, APIs, and audit rules.

- `10_supabase_schema.md`
- `11_storage_paths_naming.md`
- `12_audit_traceability.md`
- `13_failure_modes_guardrails.md`
- `14_n8n_to_python_parity.md`
- `15_python_job_spec.md`
- `16_api_endpoints.md`
- `17_test_cases.md`

These make the system buildable, testable, and enforceable.

---

### 4) Templates and data tables

```

/templates
handover_report.html
handover_email.html
handover_pdf.css
handover_section.md

/tables
bucket_list.csv
domain_map.csv
role_bias_matrix.csv

```

Templates preserve **brand uniformity**.  
Tables preserve **machine consistency**.

---

## Non-negotiable rules

- Nothing enters a handover without user acceptance  
- Nothing leaves a handover without user acceptance  
- No entry loses its source reference  
- No entry is silently reclassified  
- No handover is exported before sign-off  
- No handover becomes a task planner  

Any change violating these rules is rejected.

---

## Intended outcome

A new crew member opens a handover and:

- understands the current vessel state  
- sees unresolved issues clearly  
- trusts the narrative  
- can trace every statement to evidence  

No archaeology.  
No folklore.  
No “ask the last guy”.

---

## Status

This folder defines **authoritative handover behavior**.

All pipeline code, AI grouping, storage, and UI must comply with these documents.

If implementation disagrees with this folder,  
the implementation is wrong.

---
```
