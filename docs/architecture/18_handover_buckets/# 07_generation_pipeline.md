# 07_generation_pipeline.md

# Handover Generation Pipeline

This document defines how Celeste assembles **handover drafts** from stored handover entries and linked ledger events.

Generation is **narrative synthesis**, not record extraction.

No content is created without traceability.  
No content is removed without evidence.

---

## Core purpose

Transform many raw handover entries into:

- a readable narrative
- ordered by operational relevance
- grouped by presentation buckets
- with preserved source linkage
- and explicit uncertainty marking

Generation never replaces raw truth.  
It produces a draft view only.

---

## Pipeline trigger

Draft generation may be triggered by:

- scheduled interval (e.g., end of watch / end of day)
- manual user request
- pre-signoff preparation

If generation fails, previous signed handover remains active.

---

## Input sources

Pipeline consumes:

- `handover_entries` with status = candidate
- linked `ledger_events`
- linked `documents` (emails, manuals, reports)
- role bias configuration
- domain-to-bucket map
- overlap rules

---

## Generation stages

### Stage 1 — Fetch

- Load all candidate handover entries in time window
- Exclude suppressed entries
- Preserve ordering timestamps

---

### Stage 2 — Domain grouping

- Group entries by presentation bucket
- Within each bucket, group by primary domain
- Preserve secondary domain references

No content merged at this stage.

---

### Stage 3 — Duplicate detection

- Detect near-identical narratives
- Propose merges
- Preserve all source references
- Mark merge candidates for user confirmation

No silent deduplication allowed.

---

### Stage 4 — Summarisation

- Compress repetitive narratives
- Retain operational meaning
- Preserve original phrasing where possible
- Attach confidence score
- Mark if summarisation occurred

Summaries must always link back to raw entries.

---

### Stage 5 — Risk-based ranking

Within each bucket:

- Sort by risk tag priority
- Then by recency
- Then by unresolved duration

Risk tag ordering:

1. Safety-Critical  
2. Compliance-Critical  
3. Guest-Impacting  
4. Cost-Impacting  
5. Operational-Debt  
6. Informational

---

### Stage 6 — Command synthesis

Generate Command bucket entries:

- Operational Risk State
- Guest Experience State
- Vessel Readiness State

These are created by:

- scanning unresolved high-risk items
- summarising cross-domain exposure
- marking uncertainty if evidence conflicts

Command entries always reference underlying items.

---

### Stage 7 — Draft assembly

Create `handover_draft` object:

- Sections per bucket
- Ordered items per section
- Embedded references
- Risk markers
- Confidence indicators

Draft state = DRAFT.

---

## Output object

```

handover_draft:
id
vessel_id
generated_at
state = DRAFT

```
```

handover_draft_sections:
bucket_name
section_order

```
```

handover_draft_items:
section_bucket
domain_code
summary_text
source_entry_ids[]
risk_tags[]
confidence
item_order

```

---

## Uncertainty handling

If:

- source records conflict
- maintenance logs disagree
- evidence incomplete

Then:

- summary_text must include uncertainty statement
- confidence set to LOW
- conflict flag attached

No forced certainty.

---

## Audit linkage

Every summary item must retain:

- pointer to raw handover entries
- pointer to ledger events
- pointer to source documents

This ensures full traceability.

---

## Non-negotiable

- No raw entry overwritten
- No silent merge
- No silent summarisation
- No risk tag removal
- No deletion during generation

Drafts are views.  
Entries are truth.

---
```
