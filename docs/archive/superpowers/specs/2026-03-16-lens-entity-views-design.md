# Lens Entity Views — Design Spec

**Status:** Draft — awaiting review
**Date:** 2026-03-16
**Prototypes:** `.superpowers/brainstorm/6432-1773680335/lens-*.html` (11 files)
**Author:** Celeste7

---

## 1. Purpose

Every entity in Celeste PMS has a **lens** — a detail view that shows everything about that entity and provides every action a crew member can perform on it. Lenses are the operational nerve centre: a crew member opens a lens, reads vital signs, takes action, and moves on. The design must be fast to scan, honest about state, and never make the user hunt for what they need.

---

## 2. Universal Design Principles

| Principle | Rule |
|-----------|------|
| **Spotlight alignment** | Row proportions (44px min-height / 14px primary / 12px secondary), icon sizing (16px entity, 14px inline), group headers match Spotlight search results exactly |
| **VitalSigns = first glance** | The 5-indicator row immediately below the title tells the user everything they need to know without scrolling |
| **Honest interactivity** | Every clickable element has a hover state. Read-only fields have no hover promise. No dead clicks. |
| **Token-only styling** | Zero raw hex in component CSS. Dark/light handled entirely by token switching |
| **Section collapse** | Every content section is collapsible. Chevron rotates 90° (120ms ease). Sticky headers at `top: 0` |
| **Teal = affordance** | `--mark` is used exclusively for interactive/navigable elements (links, primary buttons). NEVER for status |
| **Status = semantic colour** | Red = critical/error/expired, Amber = warning/pending/in-progress, Green = success/operational/complete |
| **Monospace = machine data** | Timestamps, IDs, file sizes, quantities, part numbers, currency — always mono |
| **Glass = header only** | `backdrop-filter: blur(8px)` on LensHeader. NEVER on content sections |

---

## 3. Universal Lens Anatomy

Every lens follows this structure. Entity-specific sections slot into the template between Actions and the first collapsible section.

```
┌─────────────────────────────────────────────────────┐
│  LensHeader (56px, glass, fixed)                     │
│  [← Back]              ENTITY TYPE           [Related] [×]  │
├─────────────────────────────────────────────────────┤
│  LensTitleBlock                                      │
│  Identifier — Name                                   │
│  Subtitle · Context                                  │
│  [Status Pill]                                       │
├─────────────────────────────────────────────────────┤
│  VitalSignsRow (5 indicators)                        │
│  [Field 1] [Field 2] [Field 3] [Field 4] [Field 5]  │
├─────────────────────────────────────────────────────┤
│  [Entity-specific content area]                      │
├─────────────────────────────────────────────────────┤
│  Action Buttons Row                                  │
│  [Primary CTA] [Secondary] [Secondary] ...           │
├─────────────────────────────────────────────────────┤
│  ─── SECTION 1 ──────────────────── [+ Action] ──   │
│  [Content...]                                        │
├─────────────────────────────────────────────────────┤
│  ─── SECTION 2 ──────────────────── [+ Action] ──   │
│  [Content...]                                        │
├─────────────────────────────────────────────────────┤
│  ─── RELATED ENTITIES ──────────────────────── ──   │
│  [Entity cards...]                                   │
└─────────────────────────────────────────────────────┘
```

---

## 4. Panel Dimensions & Shell

| Property | Value |
|----------|-------|
| Width | 700px |
| Border radius | 8px |
| Overflow | hidden |
| Shadow (dark) | `0 0 0 1px rgba(0,0,0,0.60)`, `0 28px 80px rgba(0,0,0,0.80)`, `0 8px 24px rgba(0,0,0,0.45)` |
| Shadow (light) | `0 0 0 1px rgba(0,0,0,0.05)`, `0 28px 80px rgba(0,0,0,0.13)`, `0 8px 24px rgba(0,0,0,0.08)` |
| Asymmetric border | Top brightest, bottom dimmest (ambient light physics) |
| Background | `--surface-el` |

### LensHeader (56px)

| Property | Value |
|----------|-------|
| Height | 56px |
| Background | Glass: `backdrop-filter: blur(8px)` + semi-transparent `--surface-el` at 80% opacity |
| Border bottom | 1px `--border-sub` |
| Left | Back button (16px chevron, `--txt3`) |
| Centre | Entity type label (11px / 600 / uppercase / 0.14em tracking / `--txt-ghost`) |
| Right | "Related" button + Close button (14px × icon) |

### LensTitleBlock

| Property | Value |
|----------|-------|
| Padding | `20px 16px 16px` |
| Title | 18px / 600 / `--txt` |
| Subtitle | 12px / 400 / `--txt3` |
| Status Pill | 20px height, 10px text, 600 weight, 3px radius, dot + label |

### VitalSignsRow

| Property | Value |
|----------|-------|
| Padding | `0 16px 16px` |
| Layout | `display: flex`, `flex-wrap: wrap`, `gap: 0` |
| Each vital | `flex: 1`, `min-width: 0`, `padding: 10px 0` |
| Label | 11px / 500 / uppercase / 0.06em tracking / `--txt-ghost` |
| Value | 13px / 500 / `--txt2` |
| Value.link | colour `--mark`, cursor pointer |
| Value.mono | `font-family: var(--font-mono)` |
| Vitals separated by | 1px `--border-sub` between each (right border) |

---

## 5. Shared UI Patterns

### 5.1 Action Buttons

| Property | Value |
|----------|-------|
| Height | 36px |
| Min-width | 44px (touch target) |
| Padding | `0 16px` |
| Radius | 4px |
| Font | 12px / 500 |

| Variant | Background | Border | Text | Hover |
|---------|-----------|--------|------|-------|
| Primary | `--mark` | transparent | white | `opacity: 0.88` |
| Ghost | transparent | `--border-sub` | `--txt3` | `--surface-hover`, border → `--border-int`, text → `--txt2` |
| Danger | transparent | `--border-sub` | `--red` | `--red-bg`, border → `--red-border` |
| Disabled | transparent | `--border-sub` | `--txt-ghost` | none, `cursor: not-allowed`, `opacity: 0.5` |

### 5.2 Section Headers (Collapsible)

| Property | Value |
|----------|-------|
| Height | 44px |
| Padding | `0 16px` |
| Background | `--surface-el` |
| Position | `sticky; top: 0; z-index: 5` |
| Label | 14px / 600 / `--txt` |
| Chevron | `--txt-ghost`, `transform: rotate(-90deg)` when collapsed, 120ms transition |
| Hover | `--surface-hover` background, 60ms |
| Action button (right) | 12px / 500 / `--txt-ghost`, hover → `--mark` text + `--teal-bg` background |

### 5.3 Status Pills

| Status | Dot | Background | Border | Text |
|--------|-----|-----------|--------|------|
| Critical / Error / Expired | coloured | `--red-bg` | `--red-border` | `--red` |
| Warning / Pending / In Progress | coloured | `--amber-bg` | `--amber-border` | `--amber` |
| Success / Active / Complete | coloured | `--green-bg` | `--green-border` | `--green` |
| Neutral / Draft / Ordered | coloured | `--teal-bg` | teal border | `--mark` |
| Ghost / Cancelled | none | transparent | none | `--txt-ghost` |

### 5.4 Timeline Entries

| Property | Value |
|----------|-------|
| Layout | flex, `align-items: flex-start`, `gap: 10px` |
| Dot column | 16px wide, 6px dot (`--border-int`), 1px connecting line (`--border-sub`) |
| Timestamp | 10.5px / mono / `--txt-ghost` |
| Description | 13px / 400 / `--txt2` |
| Last entry | No connecting line |

### 5.5 Related Entity Rows

| Property | Value |
|----------|-------|
| Min-height | 44px |
| Padding | `8px 0` |
| Icon | 16px / `--txt3` |
| Name | 14px / 500 / `--txt`, hover → `--mark` |
| Type | 12px / `--txt3` |
| Chevron | `--txt-ghost`, `opacity: 0.35`, hover → `0.7` |

### 5.6 Notes Entries

| Property | Value |
|----------|-------|
| Author | 13px / 500 / `--txt2` |
| Timestamp | 10.5px / mono / `--txt-ghost` |
| Body | 14px / 400 / `--txt3` / `line-height: 1.5` |

### 5.7 File/Attachment Cards

| Property | Value |
|----------|-------|
| Height | 48px |
| Icon | 16px / `--txt3` |
| Name | 14px / 500 / `--txt` |
| Size | 12px / mono / `--txt-ghost` |
| Hover | `--surface-hover` |

### 5.8 Details Grid (2-Column)

| Property | Value |
|----------|-------|
| Layout | `grid-template-columns: 1fr 1fr` |
| Cell padding | `10px 16px` |
| Label | 11px / 500 / uppercase / 0.06em / `--txt-ghost` |
| Value | 13px / 500 / `--txt2` |
| Odd cells | Right border `--border-sub` |
| All cells | Bottom border `--border-sub` |
| Full-width cells | `grid-column: 1 / -1`, no right border |

---

## 6. Group A — Core Operations

### 6.1 Work Order Lens

**Prototype:** `lens-work-order-v1.html` (43KB)
**Route:** `/work-orders/[id]`
**Component:** `WorkOrderLensContent.tsx`

#### Title Block
- Title: `WO-{number} — {title}`
- Subtitle: `{location} · Assigned to {assigned_to}`
- Status pill: 8 states (Open, In Progress, On Hold, Pending Parts, Pending Review, Completed, Cancelled, Archived)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Priority | Critical (red), High (amber), Medium (green), Low (ghost) |
| 3 | Equipment | `--mark` link, navigates to equipment lens |
| 4 | Assigned | Name |
| 5 | Due Date | Date, red if overdue |

#### Entity-Specific Content
- **Description block**: 14px / 400 / `--txt3` / `line-height: 1.5`, below VitalSigns

#### Actions (6)
| Button | Variant | Signature |
|--------|---------|-----------|
| Mark Complete | Primary | PIN+TOTP (P1) |
| Reassign | Ghost | None |
| Add Note | Ghost | None |
| Add Part | Ghost | None |
| Add Hours | Ghost | None |
| Edit | Ghost | None |

#### Sections
1. **Notes** — with `+ Add` action. Note entries per §5.6
2. **Parts** — Part consumption entries. Each row: 16px hexagon icon, part name (14px/500), quantity badge (teal `--teal-bg`, 11px/600), timestamp (mono/ghost)
3. **Attachments** — File cards per §5.7. Upload action
4. **History** — Timeline per §5.4
5. **Related Entities** — Entity rows per §5.5

#### Dual-Panel Demo
- Dark: In Progress, Critical priority, multiple notes/parts/history
- Light: Completed, Normal priority, green status

---

### 6.2 Fault Lens

**Prototype:** `lens-fault-v1.html` (34KB)
**Route:** `/faults/[id]`
**Component:** `FaultLensContent.tsx`

#### Title Block
- Title: `FLT-{number} — {title}`
- Subtitle: `{location} · Reported by {reported_by}`
- Status pill: 4 states (Open, Acknowledged, Closed, False Alarm)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Severity | Critical (red), High (amber), Medium (green), Low (ghost) |
| 2 | Status | Semantic colour |
| 3 | Equipment | `--mark` link |
| 4 | Reporter | Name |
| 5 | Reported | Date |

#### Entity-Specific Content
- **Photo grid**: 3 thumbnails in a horizontal row. Each 120×80px, rounded 4px, `object-fit: cover`. Hover: slight scale. Placeholder: gradient background with camera icon

#### Actions (6)
| Button | Variant | Signature |
|--------|---------|-----------|
| Add Note | Ghost | None |
| Add Photo | Ghost | None |
| Acknowledge | Primary | Role-gated (P2) |
| Close | Ghost | None |
| Reopen | Ghost | None |
| Mark False Alarm | Danger | Role-gated (P2) |

#### Sections
1. **Notes** — with `+ Add` action
2. **Related Work Orders** — Entity rows with status badges
3. **History** — Timeline

#### Dual-Panel Demo
- Dark: Open, Critical severity (red border accent)
- Light: Closed, Medium severity (green status)

---

### 6.3 Equipment Lens

**Prototype:** `lens-equipment-v1.html` (41KB)
**Route:** `/equipment/[id]`
**Component:** `EquipmentLensContent.tsx`

#### Title Block
- Title: `E-{number} — {name}`
- Subtitle: `{category} · {location}`
- Status pill: 4 states (Operational, Under Maintenance, Out of Service, Decommissioned)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Category | Text |
| 3 | Location | Text |
| 4 | Manufacturer | Text |
| 5 | Running Hours | Mono |

#### Entity-Specific Content
- **Details grid** (2-column per §5.8): Serial number (mono), model, manufacturer, installation date, last service date, running hours (mono)

#### Actions (3)
| Button | Variant | Signature |
|--------|---------|-----------|
| Report Fault | Primary | None |
| Create Work Order | Ghost | None |
| Schedule Maintenance | Ghost | None |

#### Sections
1. **Open Faults** — Fault rows with severity badges. Section header shows red count badge when faults > 0
2. **Active Work Orders** — WO rows with status badges. Amber count badge
3. **Maintenance Schedule** — Timeline of upcoming + completed maintenance. Completed entries show green checkmark
4. **Documents** — File cards
5. **Warranties** — Warranty rows with expiry status

#### Dual-Panel Demo
- Dark: Operational (green), multiple linked entities
- Light: Under Maintenance (amber), active work order highlighted

---

### 6.4 Parts / Inventory Lens

**Prototype:** `lens-parts-v1.html` (39KB)
**Route:** `/inventory/[id]`
**Component:** `PartsLensContent.tsx`

#### Title Block
- Title: `{part_number} — {part_name}`
- Subtitle: `{supplier} · {location}`
- Status pill: In Stock (green), Low Stock (amber), Out of Stock (red), Discontinued (ghost)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | On Hand | Mono (quantity) |
| 3 | Min Qty | Mono |
| 4 | Location | Text |
| 5 | Unit Cost | Mono (currency) |

#### Entity-Specific Content
- **Stock Level Bar**: Horizontal bar showing current stock as percentage of max capacity. Fill colour: green (>50%), amber (20-50%), red (<20%). Track: `--border-sub`. Height: 6px, radius: 3px
- **Part Image**: 240px height placeholder area with gradient background. Caption below: part number in mono

#### Actions (6)
| Button | Variant | Signature |
|--------|---------|-----------|
| Consume | Primary | None |
| Receive | Ghost | None |
| Transfer | Ghost | None |
| Adjust Stock | Ghost | None |
| Write Off | Danger | PIN+TOTP (P1) |
| Add to Shopping List | Ghost | None |

#### Write Off Modal (PIN+TOTP)
Two-step authentication modal overlay:
1. **Step 1 — PIN**: 6 circular dots (filled as digits entered), 12px each, `--border-sub` empty / `--mark` filled
2. **Step 2 — TOTP**: 6 individual input boxes (28×36px), mono font, `--border-sub` border, focus → `--mark` border
3. Modal: centred overlay, `--surface-el` background, 8px radius, same panel shadow

#### Sections
1. **Stock Movements** — Table with columns: Date (mono), Type, Quantity (green +/red −, mono), Reference, User. Green upward arrow for receipts, red downward for consumption
2. **Used in Work Orders** — WO rows with status badges
3. **Purchase Orders** — PO rows with status badges
4. **Related Equipment** — Equipment rows

#### Dual-Panel Demo
- Dark: Low Stock (amber), 50% fill bar, Write Off modal overlay shown
- Light: In Stock (green), full stock, no modal

---

## 7. Group B — Compliance & Supply Chain

### 7.1 Certificate Lens

**Prototype:** `lens-certificate-v1.html` (36KB)
**Route:** `/certificates/[id]`
**Component:** `CertificateLensContent.tsx`

#### Title Block
- Title: `{certificate_name}`
- Subtitle: `{issuing_authority} · {certificate_number}`
- Status pill: Valid (green), Expiring Soon (amber), Expired (red)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Type | Text |
| 3 | Authority | Text |
| 4 | Issue Date | Date |
| 5 | Expiry Date | Date, red if expired |

#### Entity-Specific Content
- **Expiry Countdown Block**: Large countdown text ("670 days remaining" / "47 days remaining" / "Expired 30 days ago"). Font: 18px / 600. Colour: green (>90 days), amber (30-90 days), red (<30 days or expired). Progress bar below: 6px height, fill shows time elapsed (green/amber/red). Range text: "Started {date} → Expires {date}" in 12px mono ghost

#### Actions (3)
| Button | Variant | Signature |
|--------|---------|-----------|
| Edit | Ghost | None |
| Renew | Primary | None |
| Archive | Ghost | None |

#### Sections
1. **Details** — Grid (§5.8): certificate number, type, authority, issue date, expiry date
2. **Documents** — File cards (certificate PDFs)
3. **Related Equipment** — Equipment rows
4. **Renewal History** — Timeline entries

#### Dual-Panel Demo
- Dark: Valid (green), 670 days remaining
- Light: Expiring Soon (amber), 47 days remaining

---

### 7.2 Document Lens

**Prototype:** `lens-document-v1.html` (35KB)
**Route:** `/documents/[id]`
**Component:** `DocumentLensContent.tsx`

#### Title Block
- Title: `{title}`
- Subtitle: `{classification} · Uploaded by {user}`
- Status pill: Classification level (Confidential = amber, Internal = ghost, Public = green)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Type | File extension (PDF, DOCX, etc.) |
| 2 | Size | Mono (e.g., "4.2 MB") |
| 3 | Classification | Amber for confidential |
| 4 | Equipment | `--mark` link (if linked) |
| 5 | Uploaded | Date |

#### Entity-Specific Content
- **Document Preview Area**: Renders differently by MIME type:
  - **PDF**: Simulated page with line placeholders (alternating widths). Page counter: "Page 1 of 42" in 10px mono ghost. Height: 260px
  - **Image**: 240px height placeholder with gradient background. Caption: filename in mono
  - **Other**: Generic file icon placeholder
- **Preview Controls**: 40px height bar below preview. Zoom in/out buttons (32×32, ghost). "Open Full View" link (12px / 500 / `--mark`). All right-aligned

#### Actions (4)
| Button | Variant | Signature |
|--------|---------|-----------|
| Download | Primary | None |
| Link to Entity | Ghost | None |
| Share | Ghost | None |
| Archive | Ghost | None |

#### Sections
1. **Details** — Grid (§5.8): filename (mono), MIME type (mono), file size (mono), pages, classification, uploaded by, upload date
2. **Linked Entities** — Entity rows (§5.5)
3. **Document History** — Timeline

#### Dual-Panel Demo
- Dark: PDF document, Confidential classification
- Light: Image document, Internal classification

---

### 7.3 Receiving Lens

**Prototype:** `lens-receiving-v1.html` (39KB)
**Route:** `/receiving/[id]`
**Component:** `ReceivingLensContent.tsx`

#### Title Block
- Title: `RCV-{number} — {vendor_name}`
- Subtitle: `{po_reference} · Received by {user}`
- Status pill: 4 states (In Review, Accepted, Rejected, Partial)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Vendor | Text |
| 3 | Items | "{n} line items" |
| 4 | Total | Mono (currency) |
| 5 | Received | Date |

#### Entity-Specific Content
- **Received Items Table**: Full-width table with columns:
  - Description (14px / 500)
  - Ordered (centre-aligned)
  - Received (centre-aligned)
  - Unit Price (mono, right-aligned)
  - Total (mono, right-aligned)
  - Match status:
    - **Green circle checkmark** (20px): ordered === received
    - **Red shortage badge**: "1 short" in 10px/600, red-bg, red-border, red text
- **Table footer**: Total row with bold label and mono value
- **Table header**: 12px / 500 / uppercase / 0.06em / `--txt-ghost`
- Cell padding: `10px 12px`

#### Actions (4)
| Button | Variant | Signature |
|--------|---------|-----------|
| Accept | Primary | Optional signature (P2) |
| Reject | Danger | None |
| Edit Items | Ghost | None |
| Add Attachment | Ghost | None |

#### Sections
1. **Notes** — with `+ Add` action
2. **Linked PO** — Entity row linking to source purchase order, with status badge
3. **Attachments** — File cards (delivery documents)
4. **History** — Timeline

#### Dual-Panel Demo
- Dark: In Review (amber), has shortage on one item (red badge)
- Light: Accepted (green), all items matched (green checkmarks)

---

### 7.4 Shopping List Lens

**Prototype:** `lens-shopping-list-v1.html` (38KB)
**Route:** `/shopping-list/[id]`
**Component:** `ShoppingListLensContent.tsx`

#### Title Block
- Title: `{title}`
- Subtitle: `Requested by {requester} · {item_count} items`
- Status pill: 4 states (Draft, Pending Approval, Approved, Ordered)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Items | Count |
| 3 | Requester | Name |
| 4 | Approver | Name |
| 5 | Created | Date |

#### Entity-Specific Content
- **Items List**: Each item row (44px min-height):
  - Hexagon icon (16px, `--txt3`)
  - Item name (14px / 500)
  - Quantity badge: teal background (`--teal-bg`), teal text (`--mark`), 11px / 600, "x 5"
  - Unit info: 12px / `--txt3`, "Each · Est. $47.50"
  - Urgency badge (right-aligned):
    - **Critical**: red-bg, red text, uppercase 10px
    - **High**: amber-bg, amber text
    - **Low**: ghost text, transparent bg
    - **Normal**: no badge shown
- **Estimated Total**: Right-aligned, 14px / 600 / mono, below items list with top border

#### Actions (contextual by status)
| Status | Buttons |
|--------|---------|
| Pending Approval (approver view) | Approve (primary), Reject (danger), Add Item (ghost) |
| Approved | Convert to PO (primary), Add Item (ghost) |
| Draft | Submit for Approval (primary), Add Item (ghost), Delete (danger) |

#### Sections
1. **Notes** — with `+ Add` action
2. **Linked Work Orders** — WO rows with status badges
3. **Approval History** — Timeline with coloured dots (green for approved, amber for submitted)

#### Dual-Panel Demo
- Dark: Pending Approval, 5 items with mixed urgency levels
- Light: Approved, "Convert to PO" as primary action

---

## 8. Group C — Procurement, Compliance & Special

### 8.1 Purchase Order Lens

**Prototype:** `lens-purchase-order-v1.html` (45KB)
**Route:** `/purchasing/[id]`
**Component:** `PurchaseOrderLensContent.tsx`

#### Title Block
- Title: `PO-{number} — {supplier}`
- Subtitle: `{description} · Approved by {approver}`
- Status pill: 8 states (Draft, Pending Approval, Approved, Ordered, Partially Received, Received, Cancelled, Closed)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Supplier | `--mark` link |
| 3 | Items | "{n} line items" |
| 4 | Total | Mono (currency) |
| 5 | ETA | Date |

#### Entity-Specific Content
- **Line Items Table**: Rows with columns:
  - Row number (32px, mono, ghost)
  - Description (flex: 1, 500 weight)
  - Qty (48px, mono, right-aligned)
  - Unit price (80px, mono, right-aligned, `--txt2`)
  - Total (80px, mono, right-aligned, 500 weight)
  - Not-received items: description in amber
- **Totals Area**: Below table, right-aligned:
  - Subtotal (12px label / 13px mono value)
  - Tax (ghost value)
  - **Grand Total** (separated by top border, 13px/600 label, 14px/600 mono value)

- **Delivery Tracking Flow**: Visual pipeline showing order progress:
  - Steps: Ordered → Shipped → In Transit → Delivered
  - Each step: 12px circle dot + label below
  - Dot states: **Filled** (green, complete), **Pulsing** (amber, active, `pulse-dot` animation at 2s), **Empty** (ghost border, pending)
  - Connecting lines: 2px height, green when done, gradient for partial, ghost for pending
  - Below: meta info (tracking number, ETA) in 12px mono ghost

#### Actions (5)
| Button | Variant | Signature |
|--------|---------|-----------|
| Approve | Primary | Role-gated (P2) |
| Mark Received | Ghost | None |
| Cancel | Danger | None |
| Edit | Ghost | None |
| Add Item | Ghost | None |

#### Sections
1. **Supplier Details** — Key-value rows (120px label width): contact, email (mono), phone (mono), address, payment terms
2. **Receiving Records** — Entity rows linking to receiving records with status badges (green "Received", amber "Partial")
3. **History** — Timeline

#### Dual-Panel Demo
- Dark: Ordered status (teal pill), delivery tracking showing "In Transit" (pulsing amber dot)
- Light: Draft status, "Approve" as primary action, no delivery tracking (empty state with dashed border)

---

### 8.2 Hours of Rest Lens

**Prototype:** `lens-hours-of-rest-v1.html` (42KB)
**Route:** `/hours-of-rest/[id]`
**Component:** `HoursOfRestLensContent.tsx`

#### Title Block
- Title: `{crew_name} — {date}`
- Subtitle: `{role} · {department}`
- Status pill: Compliant (green), Non-Compliant (red)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Compliance | Green "Compliant" / Red "Non-Compliant" |
| 2 | Rest Hours | Mono (e.g., "11.0 h") |
| 3 | Work Hours | Mono (e.g., "13.0 h") |
| 4 | Crew | Name |
| 5 | Date | Date |

#### Entity-Specific Content
- **24-Hour Timeline**: Horizontal bar representing 00:00–24:00:
  - Rest segments: green fill (`--green-bg`, `--green-border`)
  - Work segments: transparent (panel surface)
  - Hour tick marks: thin lines at each hour
  - Hour labels: 10px mono ghost at 00, 06, 12, 18, 24
  - Legend: Rest (green swatch) / Work (surface swatch) in 11px `--txt3`
  - Bar height: 24px, border-radius: 4px

- **Compliance Checks**: List of MLC regulation checks:
  - Each row: 44px height, icon (16px) + text (13px `--txt2`) + result (12px mono)
  - Pass: green checkmark icon, green "PASS" text
  - Fail: red × icon, red "FAIL" text
  - Checks include: minimum rest hours (10h/24h), maximum work hours (14h/24h), consecutive rest periods, 77h/7-day minimum

- **Verification Block**: Summary card:
  - Verified: green border, green background, checkmark icon
  - Pending: amber border, amber background, clock icon
  - Text: "Verified by {name} on {date}" or "Awaiting verification"

- **7-Day Summary Chart**: Bar chart showing rest hours for past 7 days:
  - Height: 80px
  - Bars: coloured by compliance (green ≥10h, amber 8-10h, red <8h), 70% opacity
  - Date labels: 10px mono ghost below each bar
  - Reference line: dashed amber at 10h minimum, with "10h min" label

#### Actions (3)
| Button | Variant | Signature |
|--------|---------|-----------|
| Update Record | Primary | None |
| Add Rest Period | Ghost | None |
| Verify/Approve | Ghost | Role-gated (P2) |

#### Sections
1. **Rest Periods** — Table with columns: Period (e.g., "Rest 1"), Start (mono), End (mono), Duration (mono, right-aligned). Header: 12px uppercase ghost
2. **History** — Timeline

#### Dual-Panel Demo
- Dark: Compliant (green), all checks passing, verified
- Light: Non-Compliant (red), rest check failing (8.5h < 10h minimum), pending verification

---

### 8.3 Warranty Lens

**Prototype:** `lens-warranty-v1.html` (35KB)
**Route:** `/warranties/[id]`
**Component:** `WarrantyLensContent.tsx`

#### Title Block
- Title: `{title}`
- Subtitle: `{supplier} · {equipment}`
- Status pill: Active (green), Expiring (amber), Expired (red)

#### VitalSigns (5)
| Position | Field | Formatting |
|----------|-------|-----------|
| 1 | Status | Semantic colour |
| 2 | Equipment | `--mark` link |
| 3 | Supplier | Text |
| 4 | Start Date | Date |
| 5 | Expiry Date | Date |

#### Entity-Specific Content
- **Expiry Countdown Block** (same pattern as Certificate lens):
  - Large text: "460 days remaining" (green) / "Expired 45 days ago" (red)
  - Progress bar: 6px, fill shows elapsed time
  - Range: "Started {date} → Expires {date}" in 12px mono

- **Coverage Card**: Detailed coverage information:
  - Grid layout with label/value pairs:
    - Coverage Type, Maximum Claim (mono currency), Deductible (mono currency), Response Time
  - **Components Covered**: Bulleted list with green checkmarks (14px)
  - **Exclusions**: Bulleted list with ghost × icons (14px)
  - **Terms**: 12px / 400 / `--txt3` / `line-height: 1.55`

#### Actions (3)
| Button | Variant | Signature |
|--------|---------|-----------|
| Submit Claim | Primary | None |
| Renew | Ghost | None |
| Archive | Ghost | None |

#### Sections
1. **Claim History** — Expandable claim entries:
   - Header: Claim ID (13px / 600 / mono), Status badge (rounded pill), Amount (mono, right-aligned)
   - Title: 13px / 500 / `--txt2`
   - Date: 12px / mono / ghost
   - "Details" toggle: 11px / `--mark`, chevron rotates on expand
   - Details body: hidden by default, 12px / `--txt3` / `line-height: 1.55`, bordered card
2. **Documents** — File cards (warranty certificates, claim reports)
3. **Related Equipment** — Equipment rows with operational status badges

#### Dual-Panel Demo
- Dark: Active (green), 460 days remaining, one approved claim
- Light: Expired (red), 45 days overdue, no claims, "Renew" as primary action

---

## 9. Signature Flows

### 9.1 P1 — PIN+TOTP (Strong)

Used for: Work Order completion, Part write-off

**Modal Structure:**
1. Modal overlay: semi-transparent dark background
2. Card: centred, `--surface-el`, 8px radius, panel shadow
3. Title: 14px / 600 / `--txt`
4. Step 1 — PIN entry:
   - 6 circular dots, 12px diameter, inline-flex
   - Empty: `--border-sub` border, transparent fill
   - Filled: `--mark` fill, no border
   - Hidden numeric input behind dots
5. Step 2 — TOTP entry:
   - 6 individual input boxes, 28px wide × 36px tall
   - Border: 1px `--border-sub`, focus → `--mark`
   - Font: mono, 16px, centred
   - Gap: 4px between boxes
6. Cancel button: ghost variant
7. Confirm button: primary variant, disabled until both steps complete

### 9.2 P2 — Role-Based (Loose)

Used for: Fault acknowledgement, Receiving acceptance, Shopping list approval

**Confirmation Modal:**
1. Small centred card
2. Warning/confirmation text
3. Checkbox: "I confirm this action"
4. Cancel (ghost) + Confirm (primary, disabled until checkbox checked)

---

## 10. Entity Type Icons

Consistent across all lenses, Spotlight search, and Ledger.

| Entity | Icon Description | SVG |
|--------|-----------------|-----|
| Work Order | Clipboard with text lines | rect + path lines |
| Fault | Warning triangle | triangle + exclamation |
| Equipment | Machine/server | rect + circle + details |
| Part / Inventory | Hexagonal prism | hexagon path |
| Certificate | Award circle | circle + checkmark |
| Document | Page with lines | rect + lines |
| Receiving | Arrows (exchange) | bidirectional arrows |
| Shopping List | Shopping cart | cart outline |
| Purchase Order | Receipt/calendar | rect + header |
| Hours of Rest | Clock | circle + hands |
| Warranty | Shield | shield outline |
| Email | Envelope | envelope outline |

---

## 11. Navigation

Every lens navigates via the entity's fragmented route:

```typescript
function getEntityRoute(entityType: string, entityId: string): string {
  const routes: Record<string, string> = {
    work_order:     '/work-orders',
    fault:          '/faults',
    equipment:      '/equipment',
    part:           '/inventory',
    inventory:      '/inventory',
    certificate:    '/certificates',
    document:       '/documents',
    receiving:      '/receiving',
    shopping_list:  '/shopping-list',
    purchase_order: '/purchasing',
    hours_of_rest:  '/hours-of-rest',
    warranty:       '/warranties',
    handover:       '/handover-export',
  };
  return `${routes[entityType] ?? '/'}/${entityId}`;
}
```

Within a lens, clicking a related entity navigates to that entity's own route page. The Back button returns to the previous route via `router.back()`.

---

## 12. Data Sources

| Lens | Primary Table | Child Tables | Media |
|------|--------------|-------------|-------|
| Work Orders | `work_orders` | `work_order_notes`, `work_order_parts`, `work_order_attachments` | Attachment files |
| Faults | `faults` | `fault_notes`, `fault_attachments` | Photos |
| Equipment | `equipment` | — | Equipment images |
| Parts | `parts` / `inventory` | `stock_movements` | Part images |
| Certificates | `certificates` | `certificate_attachments` | Certificate PDFs |
| Documents | `documents` | `document_chunks` | Original files |
| Receiving | `receiving` | `receiving_items` | Delivery docs |
| Shopping List | `shopping_lists` | `shopping_list_items` | — |
| Purchase Orders | `purchase_orders` | `purchase_order_items` | PO documents |
| Hours of Rest | `hours_of_rest` | `rest_periods` | — |
| Warranties | `warranties` | — | Warranty docs |

---

## 13. Accessibility

| Element | Requirement |
|---------|-------------|
| Section headers | `aria-expanded` toggling |
| Action buttons | `role="button"`, `aria-label` for icon-only buttons |
| Related entity rows | `role="button"`, `tabindex="0"` |
| Status pills | `role="status"`, `aria-label` with full text |
| File cards | `role="button"`, `tabindex="0"` |
| Modal overlays | `aria-modal="true"`, focus trap, Esc to close |
| PIN/TOTP inputs | `aria-label`, `inputmode="numeric"` |
| 24h timeline (HoR) | `role="img"`, `aria-label` with summary text |
| Charts (HoR 7-day) | `role="img"`, `aria-label` with data summary |
| Focus visible | Ring on all interactive elements |

---

## 14. Responsive Behaviour

| Breakpoint | Behaviour |
|------------|-----------|
| Desktop (>768px) | Panel at 700px width, centred |
| Tablet (641-768px) | Panel at 100% width minus padding |
| Mobile (<640px) | Full-width, no side padding. Touch targets increase to 48px. VitalSigns stack to 2-column grid. Details grid becomes single column |

---

## 15. Out of Scope

| Feature | Reason |
|---------|--------|
| Email thread lens | Inbox pattern, not entity lens — separate design needed |
| Handover Notes / Exports | Already has dedicated design spec (`2026-03-16-handover-module-design.md`) |
| Inline editing | V1 uses modal-based editing for all fields |
| Real-time updates | Deferred — polling/subscription is implementation concern |
| Bulk actions | Deferred — lenses show single entities |
| Print/export from lens | Deferred to v2 |

---

## 16. Prototype Index

| # | Entity | Prototype File | Size |
|---|--------|---------------|------|
| 1 | Work Order | `lens-work-order-v1.html` | 43KB |
| 2 | Fault | `lens-fault-v1.html` | 34KB |
| 3 | Equipment | `lens-equipment-v1.html` | 41KB |
| 4 | Parts / Inventory | `lens-parts-v1.html` | 39KB |
| 5 | Certificate | `lens-certificate-v1.html` | 36KB |
| 6 | Document | `lens-document-v1.html` | 35KB |
| 7 | Receiving | `lens-receiving-v1.html` | 39KB |
| 8 | Shopping List | `lens-shopping-list-v1.html` | 38KB |
| 9 | Purchase Order | `lens-purchase-order-v1.html` | 45KB |
| 10 | Hours of Rest | `lens-hours-of-rest-v1.html` | 42KB |
| 11 | Warranty | `lens-warranty-v1.html` | 35KB |

All prototypes served at: `http://localhost:53960/`

---

## 17. Cross-Reference

- **Design philosophy:** `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`
- **Lens inventory research:** `docs/superpowers/specs/2026-03-16-lens-inventory-research.md`
- **Ledger spec:** `docs/superpowers/specs/2026-03-16-ledger-module-design.md`
- **Handover spec:** `docs/superpowers/specs/2026-03-16-handover-module-design.md`
- **Settings spec:** `docs/superpowers/specs/2026-03-16-settings-module-design.md`
- **Token values:** `apps/web/src/styles/tokens.css`
- **Lens CSS:** `apps/web/src/styles/lens.css`
- **Signature mechanism:** `docs/reference_signature_mechanism.md`
