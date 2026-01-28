# Receiving — Situational Active State

**CelesteOS**

---

## Purpose

Receiving exists to **confirm physical reality** when parts arrive onboard.

It answers one question only:

> “Did this item arrive, and what did we do with it?”

Receiving is **human-verified, transactional, auditable**, and **non-intelligent**.

---

## Core Doctrine

* **Checkbox = truth**
* **Nothing is real until a human ticks it**
* **No confidence, no inference, no automation**
* **Receiving confirms reality — it does not predict it**

---

## Entry Conditions (How Receiving Becomes Active)

Receiving can only be entered via explicit user intent:

1. Search → `Receive delivery`
2. Search → 📷 camera icon → upload packing slip
3. Order / Shopping List → `Receive items`

Receiving is **never auto-triggered**.

---

## Situation States

### 1. IDLE

No receiving context exists.

---

### 2. CANDIDATE

User has initiated a receiving flow but has not committed.

Examples:

* Order selected
* Packing slip uploaded
* No items confirmed yet

**Allowed actions**

* Select order
* Upload packing slip
* View expected items

**Disallowed**

* Inventory mutation
* Order status updates
* Finance posting

---

### 3. ACTIVE (Receiving Session)

A receiving table is visible.
This is the **only state where receiving actions are allowed**.

---

### 4. REVIEW

User has ticked at least one item and is reviewing the summary.

No new scanning or uploads allowed here.

---

### 5. COMMITTED

Receiving session has been submitted.

Events are written.
State is immutable.

---

## Receiving UI — Canonical Structure

### Receiving Table (Required)

Every receiving session must show a table with:

| ✔ | Item | Expected Qty | Delivered Qty | Status |
| - | ---- | ------------ | ------------- | ------ |

**Rules**

* All checkboxes are **unchecked by default**
* Delivered Qty is editable before checking
* Only checked rows are processed
* Unchecked rows are ignored (remain pending)

---

## Human Verification Rule (Non-Negotiable)

* Each item must be **explicitly ticked**
* If it is not ticked, it **does not exist**
* OCR / barcode / parsing may prefill rows — **never auto-check**

This removes all “confidence” logic and liability.

---

## Discrepancy Handling (Unified)

For any checked item where Delivered ≠ Expected, user must select **one**:

* Missing
* Damaged
* Incorrect

Optional:

* Photo
* Short note

All discrepancies share the same flow and backend structure.

---

## Immediate Installation Flow (Optional, Explicit)

After item confirmation, system may ask once:

> “Were any of these installed immediately?”

* Default: No
* If Yes → user selects item(s)

For selected items:

* **Skip inventory**
* Mark order line as `Installed`
* Optionally link to Work Order
* Generate audit + finance events

No inventory bounce.
No forced WO creation.

---

## Review Screen (Before Commit)

Before submission, user must see a plain-language summary:

> You are about to:
>
> * Add **X items** to inventory
> * Mark **Y items** as installed
> * Flag **Z items** as missing / damaged
> * Leave remaining items pending

Buttons:

* `Confirm & Save`
* `Cancel`

No hidden side effects.

---

## Commit Effects (Backend Events)

Only on **Confirm & Save**:

### Inventory

* `inventory_receive_event` for each checked item added
* Quantity updates applied

### Orders / Shopping List

* Line items marked:

  * Received
  * Partially received
  * Installed
  * Missing / Damaged

Orders are **never closed**, only fulfilled incrementally.

### Finance

* Spend posted against received or installed items
* Linked to order reference

### Audit

Each item generates immutable events:

* who confirmed
* what quantity
* when
* discrepancies (if any)
* photos / notes

---

## Barcode & Label Preparation

* For items added to inventory:

  * System prepares barcode label PDFs
* User may:

  * Download
  * Email to self
  * Print later

No printer integrations.
No forced printing.

---

## Packing Slip Handling

### Camera Icon (Search)

* 📷 icon in search bar opens:

  * Take photo
  * Upload PDF

### Behavior

* OCR extracts line items
* System suggests matching order(s)
* User must confirm order
* Receiving table is populated as **draft only**

No auto-binding.
No auto-checking.

---

## Backwards Compatibility (Split Deliveries)

* Orders support:

  * Pending
  * Partial
  * Fulfilled

If another box arrives later:

* User re-enters Receiving
* Remaining open lines are shown
* Process repeats

No reopening hacks.
No data overwrite.

---

## Security & Session Handling

* Receiving sessions auto-lock after inactivity
* Resume requires explicit user action (e.g. “I’m back”)
* No background mutations allowed

---

## Explicit Non-Goals (Out of Scope by Design)

* ❌ Confidence scores
* ❌ Auto-receiving
* ❌ Auto-printing
* ❌ Supplier auto-emails
* ❌ Inventory edits without checkboxes
* ❌ Forced work orders

---

## Mental Model (Do Not Violate)

> **Receiving is a checklist, not intelligence.**
> If a human didn’t tick it, it didn’t happen.

---

