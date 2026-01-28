# 16_api_endpoints.md

# API Endpoints — Handover System

This document defines the **minimum required API endpoints** to operate the Celeste handover system.

Endpoints must enforce:

- state machine integrity
- traceability
- acceptance gating
- no silent transitions

No endpoint may bypass defined lifecycle rules.

---

## Authentication

All endpoints require:

- authenticated user
- resolved vessel_id context
- role loaded for biasing (not access restriction)

No anonymous access.

---

## Draft endpoints

### Create or fetch active draft

```

POST /handover/draft/generate

```

**Purpose:**
- Trigger draft generation job
- Return active DRAFT id

**Rules:**
- If DRAFT exists → return existing
- If no new entries → return existing
- If draft in ACCEPTED or SIGNED → reject

---

### Get draft

```

GET /handover/draft/{draft_id}

```

**Returns:**
- sections
- items
- risk flags
- edit history
- current state

---

### Enter review state

```

POST /handover/draft/{draft_id}/review

```

**Purpose:**
- Transition DRAFT → IN_REVIEW

**Rules:**
- Only allowed if state = DRAFT
- Locks draft for review session

---

### Edit draft item

```

PATCH /handover/draft/{draft_id}/item/{item_id}

```

**Payload:**
- edited_text
- optional edit_reason

**Rules:**
- Allowed only in IN_REVIEW
- Stores edit history
- Cannot modify classification or sources

---

### Merge draft items

```

POST /handover/draft/{draft_id}/merge

```

**Payload:**
- item_ids[]
- merged_text

**Rules:**
- Allowed only in IN_REVIEW
- Source references combined
- Original items retained as merged history

---

## Acceptance endpoints

### Accept draft (outgoing signatory)

```

POST /handover/draft/{draft_id}/accept

```

**Rules:**
- Only allowed in IN_REVIEW
- Requires confirmation flag
- Records outgoing_user_id + timestamp
- Transitions to ACCEPTED

---

### Countersign draft (incoming signatory)

```

POST /handover/draft/{draft_id}/sign

```

**Rules:**
- Only allowed in ACCEPTED
- Requires confirmation flag
- Records incoming_user_id + timestamp
- Transitions to SIGNED
- Triggers export preparation job

---

## Export endpoints

### Request export

```

POST /handover/draft/{draft_id}/export

```

**Payload:**
- export_type: pdf / html / email
- recipients[] (if email)

**Rules:**
- Only allowed in SIGNED
- Creates export record
- Triggers export rendering

---

### Fetch signed handover

```

GET /handover/signed/{draft_id}

```

**Returns:**
- signed snapshot metadata
- storage URLs (time-limited)

---

### Fetch export

```

GET /handover/export/{export_id}

```

**Returns:**
- export metadata
- storage URLs

---

## Handover entry endpoints

### Add handover entry manually

```

POST /handover/entry

```

**Payload:**
- narrative_text
- optional linked_event_ids[]
- optional linked_document_ids[]

**Rules:**
- Classification inferred
- Proposal preview returned
- Must be confirmed via next endpoint

---

### Confirm proposed handover entry

```

POST /handover/entry/{entry_id}/confirm

```

**Rules:**
- Entry saved as candidate
- Visible to draft generation

---

### Dismiss proposed handover entry

```

POST /handover/entry/{entry_id}/dismiss

```

**Rules:**
- Dismissal logged
- Entry not created

---

## Classification correction endpoint

```

POST /handover/entry/{entry_id}/flag-classification

```

**Purpose:**
- User disputes domain or bucket inference
- Sets classification_flagged = true
- Logs correction request

No direct modification allowed.

---

## Query endpoints

### List handover entries

```

GET /handover/entries?status=candidate

```

### List past signed handovers

```

GET /handover/history

```

---

## State transition summary

```

DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED

```

Invalid transitions must return HTTP 409.

---

## Non-negotiable

- No endpoint may skip acceptance
- No endpoint may modify signed drafts
- No endpoint may create exports before signing
- No endpoint may delete trace records

APIs enforce the rules.  
UI only expresses them.

---
```
