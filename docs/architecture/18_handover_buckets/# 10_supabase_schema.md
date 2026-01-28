# 10_supabase_schema.md

# Supabase Schema — Handover System

This document defines the **database schema** required to implement Celeste’s handover system.

Schema design enforces:

- immutable truth storage
- auditable narrative drafting
- explicit acceptance and countersign
- traceable exports
- zero silent modification

If schema design deviates from these rules, the implementation is incorrect.

---

## Table: handover_entries

Raw handover entry captured at moment of operational relevance.

These are **truth seeds**.  
They are never overwritten or summarised.

```

## handover_entries

id                      uuid (pk)
vessel_id               uuid
created_at              timestamp
created_by_user_id      uuid
created_by_role         text

primary_domain          text   -- e.g. DECK-01
secondary_domains       text[] -- optional

presentation_bucket     text   -- Engineering / Deck / Interior / etc

suggested_owner_roles   text[] -- inferred from domain + overlap

risk_tags               text[] -- Safety-Critical, etc

narrative_text          text   -- user-authored or edited text

source_event_ids        uuid[] -- ledger events
source_document_ids     uuid[] -- emails, files, etc

status                  text   -- candidate / suppressed / resolved

classification_flagged  boolean default false -- user flagged taxonomy error

```

---

## Table: handover_drafts

Represents an assembled draft handover.

```

## handover_drafts

id                      uuid (pk)
vessel_id               uuid

period_start            timestamp
period_end              timestamp

generated_at            timestamp
generated_by_version    text

state                   text -- DRAFT / IN_REVIEW / ACCEPTED / SIGNED

last_modified_at        timestamp

```

---

## Table: handover_draft_sections

Defines visible document structure.

```

## handover_draft_sections

id                      uuid (pk)
draft_id                uuid (fk handover_drafts.id)

bucket_name             text -- Command / Engineering / ETO / Deck / Interior / Admin
section_order           integer

```

---

## Table: handover_draft_items

Summarised narrative entries inside a draft.

```

## handover_draft_items

id                      uuid (pk)
draft_id                uuid (fk handover_drafts.id)

section_bucket          text
domain_code             text

summary_text            text

source_entry_ids        uuid[] -- references handover_entries
source_event_ids        uuid[] -- references ledger

risk_tags               text[]
confidence_level        text -- LOW / MEDIUM / HIGH

item_order              integer

conflict_flag           boolean default false
uncertainty_flag        boolean default false

```

---

## Table: handover_draft_edits

Audit trail of human edits.

```

## handover_draft_edits

id                      uuid (pk)
draft_id                uuid
draft_item_id           uuid

edited_by_user_id       uuid
edited_at               timestamp

original_text           text
edited_text             text
edit_reason             text nullable

```

---

## Table: handover_signoffs

Stores acceptance and countersignature.

```

## handover_signoffs

id                      uuid (pk)
draft_id                uuid

outgoing_user_id        uuid
outgoing_signed_at      timestamp

incoming_user_id        uuid
incoming_signed_at      timestamp

document_hash           text

```

---

## Table: handover_exports

Tracks exported artifacts.

```

## handover_exports

id                      uuid (pk)
draft_id                uuid

export_type             text -- pdf / html / email

storage_path            text

exported_by_user_id     uuid
exported_at             timestamp

recipients              text[] nullable

document_hash           text

```

---

## Table: handover_sources (optional helper)

Maps external source material.

```

## handover_sources

id                      uuid (pk)

source_type             text -- email / document / work_order / message
external_id             text -- id in external system
storage_path            text nullable

created_at              timestamp

```

---

## Enum constraints

Recommended enums:

```

presentation_bucket:

* Command
* Engineering
* ETO_AVIT
* Deck
* Interior
* Admin_Compliance

risk_tags:

* Safety_Critical
* Compliance_Critical
* Guest_Impacting
* Cost_Impacting
* Operational_Debt
* Informational

draft_state:

* DRAFT
* IN_REVIEW
* ACCEPTED
* SIGNED

```

---

## Referential guarantees

- handover_draft_items.source_entry_ids must reference existing handover_entries
- handover_signoffs.draft_id must reference SIGNED draft only
- handover_exports.draft_id must reference SIGNED draft only

---

## Non-negotiable

- No cascade delete on handover_entries
- No update on ledger references
- No overwrite of narrative_text after creation
- No deletion of signed drafts
- No export without signoff

---

## Outcome

This schema guarantees:

- traceable operational truth
- human-controlled narrative
- auditable responsibility transfer
- exportable professional records

No silent automation.  
No lost context.  
No broken chain of custody.

---
```
