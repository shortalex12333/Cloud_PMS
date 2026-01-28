read repo for what. wehave buitl on seperate sysem; https://github.com/shortalex12333/Cloud_DMG/tree/python-implementation

users will try to break this. Not maliciously half the time, just lazy: random photos, blurry shots, screenshots of WhatsApp, a picture of a dog, etc. If you don’t design for that, your receiving flow becomes garbage-in/garbage-out and you’ll lose trust fast.

Also: I can’t actually “read” that Cloud_DMG repo from here (GitHub fetch failed on my side), so I can’t reference its exact code patterns. But we can mirror the same staged pipeline approach you used for manuals: ingest → validate → extract → normalize → reconcile → human-verify → commit.

Below is the workflow, built specifically to survive abuse and laziness.

Camera → Receiving Pipeline (Abuse-Resistant, Precision-First)
What users will do to hurt it
Accidental chaos

Upload wrong image (selfie, screenshot, random)

Upload shipping label only (no line items)

Upload invoice instead of packing slip

Upload partial slip (top half only)

Blurry photo, glare, crumpled paper

Multiple orders in one photo

Non-English / mixed formatting

Duplicate upload 3 times

Lazy workflow breaking

Tick everything without checking

Leave half unticked and hit back

Upload slip, never reconcile, walk away

Create “new part” for everything instead of matching

You need guardrails that don’t rely on “confidence”.

The same “manual chunking” philosophy, but for images

Manual indexing pipeline = “we don’t trust input; we validate and chunk; then we store verified outputs.”

Receiving camera pipeline should be identical in structure:

Stage 0 — Capture

User uploads photo/PDF via camera icon.

Stage 1 — Intake Gate (hard reject / accept)

Do not attempt extraction unless the file passes basic validity.

Checks

File type allowed: jpg/png/pdf/heic

Size limits (ex: < 15MB per image)

Rate limiting per user (stop spam)

Image integrity (not corrupted)

Basic “has-text” check (not a pure photo of scenery)

Outcome

If fails: show “This doesn’t look like a packing slip or label. Try again.”

If passes: store as raw + continue

Why
This is where you stop random images before they cost money and pollute the system.

Stage 2 — Classification (cheap, deterministic)

Classify the upload into one of:

Packing slip / receiving note (table-like line items)

Shipping label (address + tracking + PO reference)

Invoice (prices/taxes, sometimes line items)

Unknown / not useful

Do this with:

OCR + simple heuristics first (keywords like “packing slip”, “qty”, “description”, “PO”, “invoice”)

small LLM only if heuristics can’t decide

Outcome

Packing slip → proceed to table extraction

Label → proceed to “order lookup + confirm arrival”

Invoice → proceed to “attach to order” (optional)

Unknown → ask user to re-upload (or “store as attachment only”)

Guardrail
Don’t pretend every image is actionable. If it’s not clearly one of these, it’s not part of receiving.

Stage 3 — OCR + Table Extraction (precision, not fancy)
Extraction rules

Extract text via OCR

Detect rows using:

line breaks

columns

common packing slip patterns (Qty / Part No / Description)

Then transform into a Draft Rows JSON:

{
  "draft_rows": [
    {"raw": "...", "qty": 10, "part_no": "123-ABC", "desc": "Oil filter"},
    ...
  ]
}


Important

This draft is never posted

No confidence displayed

It’s just “what we extracted”

Stage 4 — Storage sanity checks (anti-garbage)

Before showing a draft to the user, run checks to catch nonsense:

If extracted rows < 2 → likely not a slip (ask for more photos)

If most rows have no qty → likely not a slip

If OCR text is tiny or mostly empty → retake

If the same image hash already processed recently → warn “duplicate upload”

This keeps the system clean without asking humans to deal with trash.

Stage 5 — Reconcile against your data (matching)

Now you map draft rows to your world.

Matching targets (in this order)

Existing Order lines (Shopping List → Ordered items)

Existing Inventory parts (part master)

Candidate Parts (previously created but unverified)

Matching behavior

Suggest matches, but do not auto-bind

Show “match candidate” per row:

Matched to Order Line

Matched to Inventory Part

Unmatched

Unmatched requires a human decision.

Stage 6 — Human Verification Screen (checkbox truth)

This is your Receiving table (the thing you already locked):

☐	Extracted Item	Qty	Match	Action
☐	Oil filter	10	Part #123	Receive to inventory
☐	Radar dome	1	Order #88	Mark arrived → Install?
☐	Unknown line	2	None	Match / Create candidate

Rules

Nothing is checked by default

Only checked rows get committed

User must explicitly resolve unmatched rows:

match to existing

create candidate part

ignore

This removes your liability: they verified it.

Stage 7 — Commit (write events)

When user taps Confirm:

Create receiving session record

For each checked row:

receive into inventory OR mark installed OR mark missing/damaged/etc.

Update Shopping List order line states

Generate label PDF queue

No side effects outside checked rows.

“Lazy user” mitigation that actually works

You can’t stop someone ticking everything, but you can add friction only where it prevents stupidity:

1) “Confirm count” prompt only when it looks risky

If they tick 30 rows in 5 seconds:

show one lightweight interstitial:

“You confirmed 30 items. Proceed?”

Proceed

Review

Not naggy for normal behavior, but catches drive-by ticking.

2) Require at least one action decision for unmatched rows

No “confirm” until all checked rows are resolved.
This prevents “unknown junk” being committed.

3) Queue unresolved rows as “Needs Review”

If they leave stuff unticked, fine — but the system creates a visible “Receiving draft pending review” object for HOD/logistics.

That’s how you prevent half-finished uploads from rotting.

Linking outcomes to your domains
Shopping List linkage

If draft row matches ordered item:

receiving updates order status:

ordered → partial → fulfilled

discrepancy updates:

missing/damaged → flagged + optionally “re-add to list”

Inventory linkage

If received into inventory:

add stock via event

location assignment required now or queued later (your call)

label PDF created

New part linkage (controlled)

If “create candidate part”

create Candidate Part record (unverified)

attach source image

require HOD promotion later before it becomes real inventory master data

This prevents garbage inventory.

Label printing (no hardware integration)

After commit:

system generates Label Pack PDF

one label per line item by default

option: one per unit (if they want 10 labels)

Label includes:

internal part id

part name

barcode

storage location (if known)

receiving session ref (optional)

Delivery options:

download

email to self

store in “labels” bucket

Guardrails to stop “random image upload abuse”

These are the must-haves:

Intake gate: if no text detected → reject or “store as attachment only”

Rate limit: per user per hour/day

Deduping: hash-based duplicate detection

Quarantine bucket: raw uploads stored but not processed if they fail checks

Audit trail: every upload linked to user + time

No auto-commit: checkbox truth remains the core guarantee

This is how you keep the system usable and defensible.