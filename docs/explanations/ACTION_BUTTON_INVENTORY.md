# CelesteOS — Complete Action & Button Inventory

> **Purpose:** Map every user-facing action across all entity lenses. Classify each as intra-domain (operates within one entity type) or cross-domain (creates a relationship between entity types). Cross-domain actions are CelesteOS's commercial differentiator — no competing maritime PMS has them.

---

## Summary

| Category | Count |
|---|---|
| Registry actions (backend API) | 207 |
| Frontend-only buttons (UI controls, navigation, modals) | ~50 |
| **Cross-domain actions (the differentiator)** | **17 registry + ~15 navigation** |

---

## Part 1: Cross-Domain Actions (The Differentiator)

These actions create relationships between different entity types. Traditional maritime PMS systems treat each module as a silo — CelesteOS connects them.

### Registry-Wired Cross-Domain Actions (17)

| Action | Label | From Domain | References | What It Does |
|---|---|---|---|---|
| `add_parts_to_work_order` | Add Parts to Work Order | work_orders | part_id | Links inventory parts to a work order |
| `add_wo_part` | Add Part to WO | work_orders | part_id | Same — adds a part line item to a work order |
| `add_to_shopping_list` | Add to Shopping List | shopping_list | part_id | Creates a purchase request from an inventory part |
| `order_part` | Order Part | purchase_orders | part_id | Creates a PO line item from a part |
| `link_part_to_equipment` | Link Part to Equipment | equipment | part_id | Associates a spare part with specific equipment |
| `link_document_to_equipment` | Link Document to Equipment | documents | equipment_id | Attaches a manual/schematic to equipment |
| `link_invoice_document` | Link Invoice Document | receiving | document_id | Attaches an invoice to a receiving record |
| `attach_receiving_image_with_comment` | Attach Image to Receiving | receiving | document_id | Adds photographic evidence to goods receipt |
| `request_label_output` | Request Label Output | parts | document_id | Generates a label document from part data |
| `add_certificate_note` | Add Certificate Note | certificates | equipment_id | Notes on a certificate referencing equipment |
| `add_document_note` | Add Document Note | documents | equipment_id | Notes on a document referencing equipment |
| `add_part_note` | Add Part Note | parts | equipment_id | Notes on a part referencing equipment |
| `add_po_note` | Add PO Note | purchase_orders | equipment_id | Notes on a PO referencing equipment |
| `add_warranty_note` | Add Warranty Note | warranty | equipment_id | Notes on a warranty referencing equipment |
| `view_fault_history` | View Fault History | faults | equipment_id | Views fault history for specific equipment |
| `show_manual_section` | Show Manual Section | (none) | equipment_id | Opens equipment-specific manual section |
| `add_note_to_work_order` | Add Note to WO | (none) | work_order_id | Adds a note to a specific work order |

### Cross-Domain Navigation Buttons (Frontend, ~15)

These aren't in the action registry but create cross-domain UX by navigating between entity types:

| Button | Location | From | To | What It Does |
|---|---|---|---|---|
| Part name link | PartsSection (all lenses) | Any entity | Parts lens | Click a part → opens part detail |
| Document name link | AttachmentsSection | Any entity | Documents lens | Click a document → opens document detail |
| Equipment link | FaultContent, CertificateContent | Fault/Cert | Equipment lens | Click linked equipment → opens equipment detail |
| Related Drawer items | RelatedDrawer.tsx | Any entity | Any entity | AI-surfaced related items — click navigates to target entity |
| Entity links in Handover | HandoverContent.tsx | Handover | Various | Embedded entity references in handover items |
| "Show Related" button | EntityLensPage.tsx | Any entity | (opens drawer) | Opens the AI-powered related items panel |

### The "Add to Handover" Flow (Unique to CelesteOS)

The handover system is the most distinctive cross-domain feature. It pulls items from **every other domain** into a single compliance document:

| Action | What It Pulls |
|---|---|
| `add_to_handover` | Any entity → handover item |
| `export_handover` | All handover items → professional AI-summarised document |
| `sign_handover` | Handover document → signed compliance record |

No competing maritime PMS aggregates work orders, faults, equipment status, certificates, and parts into a single handover briefing with AI summarisation.

---

## Part 2: Intra-Domain Actions by Entity Type

### Work Orders (30 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `create_work_order` | Create Work Order | MUTATE | No |
| `start_work_order` | Start Work | MUTATE | No |
| `close_work_order` | Close Work Order | MUTATE | No |
| `cancel_work_order` | Cancel Work Order | MUTATE | No |
| `archive_work_order` | Archive Work Order | MUTATE | No |
| `delete_work_order` | Delete Work Order | MUTATE | No |
| `reassign_work_order` | Reassign Work Order | MUTATE | No |
| `update_wo_priority` | Update Priority | MUTATE | No |
| `update_wo_status` | Update Status | MUTATE | No |
| `add_wo_note` | Add Note | MUTATE | No |
| `add_wo_checklist` | Add Checklist | MUTATE | No |
| `mark_checklist_item_complete` | Mark Item Complete | MUTATE | No |
| `add_parts_to_work_order` | Add Parts | MUTATE | **Yes → part_id** |
| `add_wo_part` | Add Part to WO | MUTATE | **Yes → part_id** |
| `view_work_order` | View Work Order | READ | No |
| `view_wo_history` | View History | READ | No |
| `view_wo_checklist` | View Checklist | READ | No |
| + 13 more READ/MUTATE actions | | | |

### Faults (18 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `log_fault` | Log Fault | MUTATE | No |
| `update_fault_status` | Update Status | MUTATE | No |
| `resolve_fault` | Resolve Fault | MUTATE | No |
| `close_fault` | Close Fault | MUTATE | No |
| `assign_fault` | Assign Fault | MUTATE | No |
| `escalate_fault` | Escalate Fault | MUTATE | No |
| `add_fault_note` | Add Note | MUTATE | No |
| `view_fault_history` | View Fault History | READ | **Yes → equipment_id** |
| + 10 more actions | | | |

### Equipment (28 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `add_equipment` | Add Equipment | MUTATE | No |
| `update_equipment_status` | Update Status | MUTATE | No |
| `decommission_equipment` | Decommission | SIGNED | No |
| `link_part_to_equipment` | Link Part | MUTATE | **Yes → part_id** |
| `add_equipment_note` | Add Note | MUTATE | No |
| `schedule_maintenance` | Schedule Maintenance | MUTATE | No |
| + 22 more actions | | | |

### Certificates (10 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `create_vessel_certificate` | Add Certificate | SIGNED | No |
| `renew_certificate` | Renew Certificate | SIGNED | No |
| `add_certificate_note` | Add Note | MUTATE | **Yes → equipment_id** |
| `view_certificate` | View Certificate | READ | No |
| + 6 more actions | | | |

### Parts / Inventory (21 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `add_part` | Add Part | MUTATE | No |
| `update_stock_level` | Update Stock | MUTATE | No |
| `order_part` | Order Part | MUTATE | **Yes → purchase_orders** |
| `add_to_shopping_list` | Add to Shopping List | MUTATE | **Yes → shopping_list** |
| `add_part_note` | Add Note | MUTATE | **Yes → equipment_id** |
| `request_label_output` | Print Label | MUTATE | **Yes → document_id** |
| + 15 more actions | | | |

### Shopping List (13 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `submit_shopping_list` | Submit for Approval | MUTATE | No |
| `approve_shopping_list` | Approve | SIGNED | No |
| `convert_to_po` | Convert to Purchase Order | MUTATE | **Yes → purchase_orders** |
| `reject_shopping_list` | Reject | MUTATE | No |
| + 9 more actions | | | |

### Purchase Orders (11 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `create_purchase_order` | Create PO | SIGNED | No |
| `approve_po` | Approve PO | SIGNED | No |
| `order_part` | Order Part | MUTATE | **Yes → part_id** |
| `add_po_note` | Add Note | MUTATE | **Yes → equipment_id** |
| + 7 more actions | | | |

### Receiving (13 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `confirm_receiving` | Confirm Receiving | SIGNED | No |
| `report_discrepancy` | Report Discrepancy | MUTATE | No |
| `link_invoice_document` | Link Invoice | MUTATE | **Yes → document_id** |
| `attach_receiving_image_with_comment` | Attach Image | MUTATE | **Yes → document_id** |
| + 9 more actions | | | |

### Documents (16 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `upload_document` | Upload Document | MUTATE | No |
| `link_document_to_equipment` | Link to Equipment | MUTATE | **Yes → equipment_id** |
| `add_document_note` | Add Note | MUTATE | **Yes → equipment_id** |
| + 13 more actions | | | |

### Warranty (10 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `file_warranty_claim` | File Claim | MUTATE | No |
| `add_warranty_note` | Add Note | MUTATE | **Yes → equipment_id** |
| + 8 more actions | | | |

### Handover (15 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `add_to_handover` | Add to Handover | MUTATE | **Yes → any entity** |
| `sign_handover` | Sign Handover | SIGNED | No |
| `countersign_handover` | Countersign | SIGNED | No |
| `export_handover` | Export Handover | MUTATE | No |
| `edit_handover_section` | Edit Section | MUTATE | No |
| + 10 more actions | | | |

### Hours of Rest (17 actions)

| Action ID | Label | Variant | Cross-Domain? |
|---|---|---|---|
| `submit_hours_of_rest` | Submit HoR | SIGNED | No |
| `approve_hor_signoff` | Approve Signoff | SIGNED | No |
| `reject_hor_signoff` | Reject Signoff | SIGNED | No |
| + 14 more actions | | | |

---

## Part 3: Frontend-Only Buttons (Not in Action Registry)

These are UI controls wired directly in React components.

### Shell Buttons (every lens page)

| Button | Component | What It Does | Cross-Domain? |
|---|---|---|---|
| Back | EntityLensPage.tsx | Navigate to previous page | No |
| Show Related | EntityLensPage.tsx | Toggle AI-powered related items drawer | **Yes — shows cross-domain connections** |
| Theme Toggle | EntityLensPage.tsx | Switch dark/light mode | No |
| Close Drawer | EntityLensPage.tsx | Close related items panel | No |

### Section Buttons (reusable across lenses)

| Button | Component | What It Does | Cross-Domain? |
|---|---|---|---|
| + Add Note | NotesSection.tsx | Opens note entry form | No |
| + Upload | AttachmentsSection.tsx | Opens file upload dialog | No |
| + Add Part | PartsSection.tsx | Opens part linking form | **Yes → parts domain** |
| Part name click | PartsSection.tsx | Navigates to part detail | **Yes → parts domain** |
| Document name click | DocRowsSection.tsx | Navigates to document detail | **Yes → documents domain** |
| Show more (notes) | NotesSection.tsx | Expands truncated note text | No |

### Handover-Specific Buttons

| Button | What It Does | Cross-Domain? |
|---|---|---|
| Export PDF | Triggers browser print/PDF export | No |
| Sign Handover | Opens signature canvas modal | No |
| Clear Signature | Clears canvas drawing | No |
| Confirm & Sign | Submits signed handover | No |
| Remove Item | Visually removes item from draft | No |

### Spotlight Search Buttons

| Button | What It Does | Cross-Domain? |
|---|---|---|
| Action suggestion chips | Opens ActionPopup for any domain | **Yes — creates entities across domains from search** |

---

## Part 4: Cross-Domain Relationship Map

```
Equipment ←──────────────────────────────────────────── Hub Entity
    ↑ link_part_to_equipment                    (9 actions reference equipment_id)
    ↑ link_document_to_equipment
    ↑ add_certificate_note
    ↑ add_document_note
    ↑ add_part_note
    ↑ add_po_note
    ↑ add_warranty_note
    ↑ view_fault_history
    ↑ show_manual_section

Parts ←──────────────────────────────────────────────── Second Hub
    ↑ add_parts_to_work_order              (5 actions reference part_id)
    ↑ add_wo_part
    ↑ add_to_shopping_list
    ↑ order_part
    ↑ link_part_to_equipment

Documents ←──────────────────────────────────────────── Third Hub
    ↑ link_invoice_document                (4 actions reference document_id)
    ↑ attach_receiving_image_with_comment
    ↑ request_label_output
    ↑ link_document_to_equipment

Handover ←──────────────────────────────────────────── Aggregator
    ↑ add_to_handover (from ANY entity)
    ↑ export_handover → AI summarisation → professional document
    ↑ sign_handover → compliance signature

Work Order → Shopping List → Purchase Order → Receiving
    (Procurement chain: fault → WO → parts needed → shop → PO → goods received)
```

**Equipment is the hub entity** — 9 cross-domain actions reference it. This makes sense: in maritime, everything ultimately relates to a piece of equipment.

**The procurement chain** (WO → Shopping List → PO → Receiving) is a 4-step cross-domain workflow that no legacy PMS handles as a connected flow.

**Handover is the aggregator** — it pulls from every domain into a single compliance document. This is unique to CelesteOS.

---

## Part 5: Signature Levels by Action Type

| Level | When Used | Example Actions |
|---|---|---|
| MUTATE (no signature) | Routine data entry | create_work_order, add_note, update_status |
| SIGNED (typed name) | Compliance-sensitive | sign_handover, approve_po, confirm_receiving |
| SIGNED (L3 PIN) | High-value | decommission_equipment, countersign_handover |

31 of 207 actions (15%) require signatures — all in compliance-critical domains (handover, certificates, purchasing, receiving, hours of rest).

---

*Generated from `apps/api/action_router/registry.py` (207 actions) and frontend component audit (50+ UI buttons). Source of truth: the registry file.*
