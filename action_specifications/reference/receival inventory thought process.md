receival inventory thought process.md
**Checkbox = accountability**. Simple. Defensible. Human.

I’ll do this in the right order:

1. **Hard UX constraints (non-negotiable)**
2. **Receiving ≠ Inventory (how it differs)**
3. **Exact receiving UX flow (step by step)**
4. **Camera-in-search behavior (important)**
5. **What we explicitly do NOT do**

No spec yet. This is the *design law* the spec will be written from.

---

## 1) Hard UX constraints for Receiving (lock these first)

These are the rules that prevent drift and over-automation.

### A. No “confidence”, no automation

* System never auto-commits quantities
* System never assumes correctness
* Every received line item must be **explicitly ticked by a human**

If it’s not ticked, it doesn’t exist.

---

### B. Checkbox = truth

Each line item has:

* checkbox (unchecked by default)
* quantity field (pre-filled from order)
* edit quantity inline (simple + / –)

Only checked items are posted to:

* inventory
* finance
* order status

This removes liability from Celeste and puts it where it belongs: **the person holding the box**.

---

### C. Receiving is transactional, not browseable

Receiving is:

* short-lived
* focused
* modal or dedicated screen

It is **not**:

* a list view
* a dashboard
* a place to explore inventory

Get in, reconcile, get out.

---

### D. No hidden side effects

Before final submit, user must see:

> “You are about to:
> • add 36 items to inventory
> • mark 4 items as missing
> • leave 2 items pending
> • update order status”

Nothing happens silently.

---

## 2) How Receiving differs from Inventory (critical distinction)

Receiving **looks like inventory**, but behaves very differently.

### Inventory

* long-lived
* observational by default
* actions only at part level
* used during work

### Receiving

* **event-driven**
* one-time reconciliation
* bulk by nature
* tied to an order

So:

| Aspect         | Inventory          | Receiving            |
| -------------- | ------------------ | -------------------- |
| Default state  | READ               | ACTION               |
| Scope          | Single part        | Whole order          |
| Duration       | Persistent         | Temporary            |
| User intent    | “Do we have this?” | “Did this arrive?”   |
| Accountability | Usage events       | Receipt confirmation |

This means:

* Receiving gets **bulk affordances**
* Inventory never does

That’s why receiving can have checkboxes and inventory cannot.

---

## 3) Exact Receiving UX flow (clean, realistic)

### Entry points (only three)

1. Search → “Receive delivery”
2. Search → camera icon (packing slip)
3. Order view → “Receive items”

No other entry points.

---

### Step 1: Identify the order

User lands on **Receive Delivery** screen.

They:

* select order (list of open / partial)
* OR upload packing slip (camera / file)

If packing slip uploaded:

* OCR extracts text
* system tries to match to an order
* user must confirm the order

No auto-binding.

---

### Step 2: Reconciliation table (the core UX)

Show a simple table:

| ✔ | Item             | Expected | Delivered | Status |
| - | ---------------- | -------- | --------- | ------ |
| ☐ | Oil Filter CAT-A | 10       | 10        | —      |
| ☐ | Seal Kit B       | 5        | 4         | —      |
| ☐ | Radar Dome       | 1        | 1         | —      |

Rules:

* Nothing is checked by default
* User must tick each line they physically verified
* Delivered quantity editable before ticking

This is fast in practice: tick–tick–tick.

---

### Step 3: Discrepancies (merged model)

For any line where:

* delivered < expected
* wrong item
* damaged

User selects **one reason**:

* Missing
* Damaged
* Incorrect

Same UI. Same flow.

Optional:

* photo
* note

No branching complexity.

---

### Step 4: “Installed immediately?” (simple, optional)

After ticking items, show **one** prompt:

> “Were any of these installed immediately?”

If No → continue
If Yes → user selects item(s)

For selected items:

* skip inventory
* mark order line as “Installed”
* optionally link to Work Order

No forced WO creation.
No inventory bounce.

---

### Step 5: Review & commit

Final review screen:

* X items added to inventory
* Y items installed
* Z items missing / pending

Buttons:

* Confirm & Save
* Cancel

Only on Confirm:

* inventory receive events created
* order lines updated
* finance posted
* audit log written

---

## 4) Camera icon in Search (important)

Yes — this is a **first-class control**, not a gimmick.

### Placement

* Search bar right side
* Same level as text input

### Behavior

Tap camera →

* options:

  * Take photo (packing slip)
  * Upload file (PDF)

After upload:

* system parses text
* suggests matching order(s)
* opens Receiving screen directly

This matches real behavior:

> “I’m standing in the storeroom with a box and a phone.”

Not:

> “Let me navigate menus.”

---

## 5) Barcode handling (simple, effective, shelved complexity)

Your simplification is correct.

### What we do

* Each inventory item already has a barcode ID
* On receiving:

  * system prepares a **label PDF** per item/quantity
* User can:

  * download
  * email to themselves
  * print later

No printer integrations.
No driver hell.
No support nightmare.

This still massively improves onboard discipline.

---

## 6) What we explicitly do NOT do (write this down)

To keep the system trusted and simple:

* ❌ No auto-receiving
* ❌ No confidence scores
* ❌ No auto-printing
* ❌ No silent inventory updates
* ❌ No supplier auto-emails
* ❌ No forced work orders on install

If a human didn’t tick it, it didn’t happen.

---

## Mental model (this is the anchor)

> **Receiving is a checklist, not intelligence.**

Search finds.
Orders list intent.
Receiving confirms reality.
Inventory reflects what was actually checked.

Once this is locked, the **Receiving Situation Active spec** will almost write itself.

If you want, next step:

* I’ll write **Receiving Situational Active State** using these constraints
  or
* I’ll sketch the **receiving table UI + states** in words engineers can’t misinterpret

Say which.
