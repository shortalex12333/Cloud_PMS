# Camera Feature — Inventory Scan & Receiving Workflow

## Why this exists

Because receiving is where inventory becomes real, and right now it’s:

* pen-and-paper
* messy
* wrong
* never reconciled
* never traceable

The camera flow turns “a box arrived” into:

* a verified receiving record
* accurate inventory updates
* order fulfillment status
* discrepancy tracking (missing/damaged)
* label PDFs ready to print

Not fast. **Correct.**

---

## Who uses it and what they’re trying to do

### 1) Receiver (deckhand/steward/logistics/engineer)

**Environment:** storeroom / dock / engine room, phone in one hand, box cutter in the other, bad lighting, loud, rushed.
**Goal:** confirm what arrived without admin overhead.
**Tolerance:** low. Needs a 60–120 second flow.

### 2) Inventory custodian (engineer/HOD delegate)

**Environment:** calm desk moment later, wants correctness.
**Goal:** ensure items are stickered and placed correctly.

### 3) HOD / Purser

**Environment:** managing multiple orders and suppliers.
**Goal:** see what’s arrived, what’s missing, what needs reordering, without chasing crew.

---

# Core doctrine

* **Camera is an assistant, not authority**
* **Checkbox = truth**
* **No auto-commit**
* **Every posted quantity must be explicitly verified**
* **Audit trail is mandatory**

---

## Entry points in UI

### A) Search bar camera icon (primary)

A camera icon inside/next to global search.

Tap → choose:

* **Scan barcode**
* **Photo / upload packing slip**
* **Photo / upload shipping label**

This matches real behavior: *they’re holding the box already.*

### B) Shopping List / Orders screen

Button: `Receive items` → opens the same flow.

---

# The workflow (end-to-end)

## Step 0 — Choose mode

User selects one:

### 1) Packing slip / receiving note (most common)

Used when a box contains 10–40+ items and quantities matter.

### 2) Shipping label (limited usefulness)

Mostly for finding supplier + PO number + tracking reference.

### 3) Barcode scan (optional, sometimes useful)

Useful only if:

* items already have onboard barcodes
* or supplier barcodes map reliably to internal parts

Otherwise it becomes friction.

**Decision:** ship barcode mode as “nice-to-have” but not required for MVP correctness.

---

## Step 1 — Capture

User takes photo(s) or uploads PDF.

**Guardrails**

* Allow multiple photos (packing slips are often long)
* Provide “retake” immediately
* Local preview before upload (avoid garbage images)

**Auto checks (silent)**

* detect blur / unreadable
* if unreadable: ask for retake (one sentence, no scolding)

---

## Step 2 — Extract (precision-first pipeline)

This is backend processing. Design it so it is deterministic and auditable.

### Pipeline (recommended)

1. **OCR** (cheap, reliable, deterministic)
2. **Table/line detection** (heuristics first)
3. **Normalization** (light LLM, not expensive)
4. **Draft receiving rows** output

### Model stance (cost + precision)

* Do **not** use a huge model by default.
* Use OCR + rules to extract structure.
* Use a smaller LLM only to:

  * normalize part names
  * split lines into fields (qty, part number, description)
  * map vendor aliases to internal naming
* Escalate to stronger model only when extraction fails (rare fallback).

This keeps cost low and reliability high.

---

## Step 3 — Match to an order (optional, never forced)

System tries to identify the related order using:

* PO number
* supplier name
* date / reference numbers
* common strings like “PO”, “Order”, “Invoice”

If matched:

* show **suggested order**
* user must confirm

If not matched:

* user can choose:

  * “Select an existing order”
  * “Receive without order” (creates an “Unlinked delivery” record)

**Guardrail:** no silent linkage.

---

## Step 4 — Receiving Draft screen (human verification surface)

This is the heart of precision.

Show a reconciliation table:

| ✔ | Item (draft)      | Qty (draft) | Match                    | Action                          |
| - | ----------------- | ----------- | ------------------------ | ------------------------------- |
| ☐ | Oil filter CAT-A  | 10          | matched to Part #123     | Receive to inventory            |
| ☐ | Seal kit          | 4           | matched to Part #456     | Receive to inventory            |
| ☐ | “Radar dome”      | 1           | matched to Shopping item | Mark arrived → install?         |
| ☐ | Unrecognized line | 2           | no match                 | Choose match / create candidate |

**Rules**

* All boxes start **unchecked**
* Nothing posts until checked
* Qty is editable before checking
* Each line must resolve to one of:

  * existing inventory part
  * existing shopping list item
  * **candidate new part**
  * ignore (non-item line)

**No confidence scores. No “AI certainty”.**
Just: “here’s what I found — you decide.”

---

## Step 5 — Resolve unknowns (new part flow)

When an item doesn’t match:

User chooses:

1. **Match to existing part** (search within modal)
2. **Create Candidate Part** (fast capture)

   * name (from slip)
   * qty
   * photo (optional)
   * supplier part number (if available)
   * category (optional quick pick)
   * “where will this be stored?” (optional now, required later)

**Guardrail:** Candidate Part is not a full inventory part until reviewed by HOD/custodian.
Prevents garbage.

---

## Step 6 — “Installed immediately?” (simple prompt)

After user checks received lines, show:

> “Were any of these installed immediately?”

Default: No.

If Yes:

* user selects lines
* for each selected line choose:

  * link to an existing WO (optional)
  * or “installed without WO” (still logs event)

Result:

* these lines are marked **Installed**
* they do **not** add stock to inventory

---

## Step 7 — Storage location assignment (only if needed)

For items going into inventory:

If the part already has a known location:

* prefill location, but still allow edit

If new/candidate or missing location:

* prompt user to pick:

  * Store room / locker / box ID (3C etc.)
  * optional “shelf note”

**Guardrail:** if they skip location, it must become a task for inventory custodian later. Don’t block receiving in the moment.

---

## Step 8 — Review & Commit (explicit)

Show a final summary:

* X lines will be added to inventory
* Y lines marked Installed
* Z lines unresolved (will remain pending)
* Missing/Damaged/Incorrect (if any)

Button: **Confirm & Save**

On confirm, write immutable events:

* receiving_session_created
* line_confirmed (per checked line)
* inventory_received (if applicable)
* shopping_list_fulfilled / partially_fulfilled (if linked)
* installed_event (if installed)
* discrepancy_event (if marked)

No silent behavior.

---

# Discrepancies (missing/damaged/incorrect)

In the receiving table, every line can be marked:

* Missing
* Damaged
* Incorrect

When selected:

* optionally attach photo
* optionally add note
* system generates an **email draft** to crew email (not supplier direct)

Also:

* add back to shopping list as Candidate (optional toggle)

---

# Accountability and audit (non-negotiable)

Every receiving commit stores:

* who confirmed each line
* timestamp
* source image(s) stored in Supabase bucket
* the extracted draft text (for traceability)
* the final confirmed values

This is how you protect trust and inspections.

---

# Linking to Shopping List & Inventory

## If item matches Shopping List

* receiving updates that shopping list line:

  * Ordered → Partially fulfilled → Fulfilled
  * or Ordered → Installed

## If item matches Inventory

* inventory quantity increases via receive event
* location assigned (or deferred)
* optional label PDF queued

## If item is new

* Candidate Part created
* shopping list item created (Candidate) if needed
* HOD can later “Promote to Inventory Part”

---

# Label printing (no printer integrations)

This is exactly as you requested: generate PDFs, don’t integrate hardware.

## What gets generated

After commit, show:

* `Download label PDF`
* `Email label PDF`

PDF contents per line:

* Part name
* Part ID
* Barcode (internal)
* Location (if known)
* Optional qty marker

If user received qty = 10, you can either:

* generate 10 labels (common)
  or
* generate 1 label + “Qty:10” (faster)

Make this a toggle:

* “One label per unit” vs “One label per line item”

Default to “per line item” to reduce print load.

---

# Guardrails recap

* No auto-commit
* Checkbox required per line
* Candidate parts don’t pollute inventory
* Orders never “closed”, only fulfilled incrementally
* All source images stored and linked
* Email drafts only, no supplier auto-send
* Precision > speed > cost (use heavy models only as fallback)

---

## What I’d shelve (low upside right now)

* barcode scan as primary receiving method (until you validate vendor barcode mapping)
* automatic location inference (people will distrust it)
* auto-creating orders from slips (too risky)

---
