# 17_test_cases.md

# Handover System Test Cases

This document defines **mandatory test cases** to validate correctness of the handover bucket, overlap, generation, review, and export system.

If any test fails, the handover system is not production-ready.

---

## Test Group A — Entry Creation

### A1 — Manual handover entry capture

**Given:**  
User manually adds narrative text

**When:**  
User selects “Add to handover” and confirms

**Then:**  
- handover_entry is created  
- narrative preserved verbatim  
- classification inferred  
- entry status = candidate  
- source links attached if present  
- no draft generated automatically  

---

### A2 — Proposed addition via search intent

**Given:**  
User searches “generator alarm still unresolved”

**When:**  
Celeste proposes “Add to handover?”

**Then:**  
- proposal is visible  
- user accepts  
- entry stored with inferred domain + risk tags  
- user may edit narrative before save  

**And:**  
If user dismisses  
- no entry stored  
- dismissal logged  

---

### A3 — No silent creation

**Given:**  
High-risk ledger event occurs

**Then:**  
- Celeste may propose addition  
- but no entry stored without user acceptance  

---

## Test Group B — Domain Overlap

### B1 — ETO working on deck equipment

**Given:**  
ETO adds entry about passerelle control fault

**Then:**  
- primary_domain = DECK-01  
- secondary_domain includes ETO-03  
- presentation_bucket = Deck  
- suggested_owner_roles includes Bosun + ETO  

**And:**  
Entry appears only once in Deck section of draft.

---

### B2 — Fire panel fault overlap

**Given:**  
Entry touches Fire Detection + Monitoring

**Then:**  
- primary_domain = ENG-08  
- secondary_domain = ETO-05  
- bucket = Engineering  
- relevance bias includes Chief Engineer + ETO + Captain  

---

### B3 — No duplicate bucket placement

**Given:**  
Entry has multiple secondary domains

**Then:**  
- it appears in only one bucket  
- no duplicate rendering across sections  

---

## Test Group C — Draft Generation

### C1 — Draft creation

**Given:**  
Candidate handover_entries exist

**When:**  
Draft generation job runs

**Then:**  
- handover_draft created  
- grouped into fixed buckets  
- sections only for buckets containing items  
- draft.state = DRAFT  

---

### C2 — Duplicate detection

**Given:**  
Two similar entries exist

**Then:**  
- merge proposal created  
- no silent merge performed  
- both entries retained until user confirms  

---

### C3 — Risk ranking

**Given:**  
Multiple entries in same bucket

**Then:**  
- Safety-Critical appears before Informational  
- newer items rank above older at same risk  

---

### C4 — Command synthesis

**Given:**  
High-risk unresolved entries exist

**Then:**  
- CMD entries created  
- each references underlying source entries  
- no manual editing permitted  

---

## Test Group D — Draft Editing

### D1 — Allowed edit

**Given:**  
Draft in IN_REVIEW

**When:**  
User edits summary text

**Then:**  
- original_text preserved  
- edited_text stored  
- edit history recorded  

---

### D2 — Forbidden edit

**Given:**  
Draft in IN_REVIEW

**When:**  
User attempts to change bucket or domain

**Then:**  
- request rejected  
- classification unchanged  

---

### D3 — No edits after acceptance

**Given:**  
Draft in ACCEPTED

**When:**  
User attempts text edit

**Then:**  
- edit rejected  
- state unchanged  

---

## Test Group E — Acceptance & Signoff

### E1 — Acceptance requires review

**Given:**  
Draft in IN_REVIEW

**When:**  
User tries to accept without scrolling all sections

**Then:**  
- acceptance blocked  

---

### E2 — Successful acceptance

**Given:**  
Draft reviewed

**When:**  
User ticks confirmation + accepts

**Then:**  
- state transitions to ACCEPTED  
- outgoing signatory recorded  

---

### E3 — Countersign required

**Given:**  
Draft in ACCEPTED

**When:**  
Incoming user signs

**Then:**  
- state transitions to SIGNED  
- both identities recorded  
- document_hash generated  

---

### E4 — No export without signoff

**Given:**  
Draft in ACCEPTED

**When:**  
Export requested

**Then:**  
- export rejected  

---

## Test Group F — Export

### F1 — Export after signoff

**Given:**  
Draft in SIGNED

**When:**  
Export requested

**Then:**  
- snapshot generated  
- export record created  
- file stored in signed path  
- recipients logged if email  

---

### F2 — Export immutability

**Given:**  
Signed export exists

**When:**  
New draft created later

**Then:**  
- previous export unchanged  
- new export requires new signature  

---

## Test Group G — Traceability

### G1 — Source trace chain

**Given:**  
Signed handover item

**When:**  
Audit query requests evidence

**Then:**  
- linked handover_entries returned  
- linked ledger_events returned  
- linked documents returned  

---

### G2 — Edit trace

**Given:**  
Narrative edited in review

**When:**  
Audit query requests edit history

**Then:**  
- original_text shown  
- edited_text shown  
- editor identity shown  
- timestamp shown  

---

## Test Group H — Failure Handling

### H1 — Generation job failure

**Given:**  
Draft generation crashes

**Then:**  
- no partial draft stored  
- previous signed handover remains authoritative  

---

### H2 — Export failure

**Given:**  
PDF rendering fails

**Then:**  
- signed snapshot remains valid  
- no export record created  
- retry possible  

---

## Test Group I — Role Biasing

### I1 — Same handover, different role order

**Given:**  
Captain views handover

**Then:**  
- Command + Engineering expanded first  

**And Given:**  
Chief Stew views same handover

**Then:**  
- Interior expanded first  

**But:**  
- content identical for both  

---

## Final Acceptance Condition

All tests above must pass before:

- real crew usage  
- replacement of n8n workflow  
- audit or compliance reliance  

If any test fails,  
handover system must not be released.

---
```
