# Entity Lens — Storage & Navigation Design

> MVP scope: surface the information. Presentation hierarchy comes after.

---

## Storage Buckets — Full Inventory

| # | Bucket | Policies | Size Limit | Allowed MIME Types |
|---|--------|----------|------------|-------------------|
| 1 | `documents` | 11 | 500 MB | Any |
| 2 | `pms-part-photos` | 10 | 10 MB | image/jpeg, image/png, image/webp, image/heic |
| 3 | `pms-receiving-images` | 13 | 20 MB | image/jpeg, image/png, image/webp, image/heic, application/pdf |
| 4 | `pms-label-pdfs` | 14 | 50 MB | application/pdf |
| 5 | `pms-discrepancy-photos` | 8 | 10 MB | image/jpeg, image/png, image/heic |
| 6 | `pms-work-order-photos` | 0 | 50 MB | image/jpeg, image/png, image/gif, image/webp |
| 7 | `pms-finance-documents` | 3 | 10 MB | application/pdf, image/jpeg, image/png |
| 8 | `handover-exports` | 2 | 50 MB | application/pdf, text/html, application/json |

All buckets are **private**. Every download requires a signed URL.

**Note:** `pms-work-order-photos` has **0 RLS policies** — only service key can access. This is why it appears empty despite having a bucket.

---

## Lens → Bucket → Asset Type Breakdown

### 1. Work Order Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| WO before/after photos | `pms-work-order-photos` | `pms_attachments` WHERE `entity_type='work_order'` → `storage_path` | Signed URL → image | **Bucket has 0 policies — blocked** |
| Checklist evidence photos | `pms-work-order-photos` | `pms_attachments` WHERE `entity_type='checklist_item'` → `storage_path` | Signed URL → image | **Bucket has 0 policies — blocked** |
| Checklist required photos | `pms-work-order-photos` | `pms_work_order_checklist.photo_url` | Signed URL → image | No data yet |
| **Link → Equipment** | — | `pms_work_orders.equipment_id` | Navigation link | Already in endpoint |
| **Link → Fault** | — | `pms_work_orders.fault_id` | Navigation link | Already in endpoint |
| **Link → Parts** | — | `pms_work_order_parts.part_id` (joined) | Navigation links | Already in endpoint |

### 2. Fault Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Discrepancy/evidence photos | `pms-discrepancy-photos` | `pms_attachments` WHERE `entity_type='fault'` → `storage_path` | Signed URL → image | Path in DB, needs signing |
| Thumbnails | `pms-discrepancy-photos` | `pms_attachments.thumbnail_path` | Signed URL → image | Path in DB, needs signing |
| **Link → Equipment** | — | `pms_faults.equipment_id` | Navigation link | Already in endpoint |
| **Link → Work Order** | — | `pms_faults.has_work_order` / reverse FK lookup | Navigation link | Needs join |

### 3. Equipment Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Equipment photos | `pms-discrepancy-photos` (inferred) | `pms_attachments` WHERE `entity_type='equipment'` → `storage_path` | Signed URL → image | Path in DB, bucket unclear |
| Equipment manuals/docs | `documents` | `pms_equipment_documents.storage_path` | Signed URL → PDF/document | Bucket not confirmed |
| Nameplate photo | *(same as equipment photos)* | `pms_attachments` → `category='photo'` | Signed URL → image | Path in DB |
| **Link → Certificates** | — | `pms_certificates.equipment_id` (reverse FK) | Navigation links | Needs query |
| **Link → Open Faults** | — | `pms_faults.equipment_id` (reverse FK) | Navigation links | Needs query |
| **Link → Work Orders** | — | `pms_work_orders.equipment_id` (reverse FK) | Navigation links | Needs query |

### 4. Part Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Part photo (hero) | `pms-part-photos` | `pms_parts.image_storage_path` + `pms_parts.image_bucket` | Signed URL → image | **Preloaded in DB — ready** |
| Additional photos | `pms-part-photos` | `pms_parts.photo_paths` (jsonb array) | Signed URLs → images | Array in DB, needs iteration |
| Label PDF | `pms-label-pdfs` | `pms_label_generations.pdf_storage_path` | Signed URL → PDF (view/print) | Needs join by part_id |
| **Link → Equipment** | — | Via `pms_work_order_parts` → `pms_work_orders.equipment_id` | Navigation link | Needs join |
| **Link → Receiving** | — | Via `pms_receiving_items.part_id` (reverse FK) | Navigation links | Needs query |
| **Link → Purchase Orders** | — | Via `pms_purchase_order_items.part_id` (reverse FK) | Navigation links | Needs query |

### 5. Receiving Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Invoice/delivery photo | `pms-receiving-images` | `pms_image_uploads.storage_path` + `storage_bucket` | Signed URL → image | **Preloaded in DB — ready** |
| Stock-in photo | `pms-receiving-images` (inferred) | `pms_inventory_transactions.photo_storage_path` | Signed URL → image | Bucket not confirmed |
| Label PDF | `pms-label-pdfs` | Via receiving_id → `pms_label_generations.pdf_storage_path` | Signed URL → PDF (view/print) | Needs join |
| **Link → Purchase Order** | — | `pms_receiving.po_number` → `pms_purchase_orders` | Navigation link | Already in endpoint |
| **Link → Parts** | — | `pms_receiving_items.part_id` | Navigation links | Already in endpoint |

### 6. Certificate Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Certificate document | `documents` | `pms_certificates.document_id` → `doc_metadata.storage_path` | Signed URL → PDF | Needs join |
| **Link → Equipment** | — | `pms_certificates.equipment_id` | Navigation link | Already in endpoint |

### 7. Document Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Document file | `documents` (default) or `pms-label-pdfs` (5 rows) | `doc_metadata.storage_path` + `storage_bucket` | Signed URL → any MIME | **Preloaded in DB — ready** (bucket NULL for 3,004 rows → default `documents`) |
| **Link → Equipment** | — | `doc_metadata.equipment_id` | Navigation link | Already in endpoint |

### 8. Purchase Order Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Finance documents | `pms-finance-documents` | `pms_attachments` WHERE `entity_type='purchase_order'` → `storage_path` | Signed URL → PDF/image | No data yet |
| **Link → Parts** | — | `pms_purchase_order_items.part_id` | Navigation links | Already in endpoint |
| **Link → Receiving** | — | Via `pms_receiving.po_number` (reverse FK) | Navigation links | Needs query |

### 9. Shopping List Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| *(no direct storage)* | — | — | — | — |
| **Link → Parts** | — | `pms_shopping_list_items.part_id` (if exists) | Navigation link | Needs check |

### 10. Hours of Rest Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| *(no direct storage)* | — | — | — | — |
| *(no entity links)* | — | — | — | — |

### 11. Warranty Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Claim documents | `pms-finance-documents` (assumed) | `pms_attachments` WHERE `entity_type='warranty'` → `storage_path` | Signed URL → PDF/image | No data yet |
| **Link → Equipment** | — | `pms_warranty_claims.equipment_id` | Navigation link | Already in endpoint |
| **Link → Fault** | — | `pms_warranty_claims.fault_id` | Navigation link | Already in endpoint |
| **Link → Work Order** | — | `pms_warranty_claims.work_order_id` | Navigation link | Already in endpoint |

### 12. Handover Export Lens

| Asset | Bucket | DB Source | Load Type | Status |
|-------|--------|-----------|-----------|--------|
| Handover HTML report | `handover-exports` | `handover_exports.storage_bucket` — **`storage_path` is NULL** | Signed URL → HTML (view in iframe) | **Path not in DB — must construct or list bucket** |
| Signatures | *(inline data)* | `handover_exports.user_signature`, `hod_signature` | Already in response (base64 or URL) | Already in endpoint |

---

## Core Concept

Each entity lens is not an island. The same underlying data (labels, photos, documents) appears across multiple lenses — presented differently depending on context and hierarchy. A label is shown as a printable PDF on Receiving, as a thumbnail on Part, and as a linked reference on Equipment.

Users navigate fluidly between lenses via inline links. The PA doesn't force users down one path — they hop between related entities as their intent evolves.

---

## Navigation Example

```
1.  Work Order: "Main Engine Starboard oil change"
    ├── parts needed → [click]
    │
2.  Part Lens: "Fuel Filter Generator"
    ├── last received → [click]
    ├── equipment → [click]
    │
3.  Receiving Lens: INV-CAPTAIN-224917
    ├── label → [view / print]
    ├── invoice photo → [view]
    │
4.  Equipment Lens: "Main Engine Starboard"
    ├── certificates → [click]
    ├── open faults → [click]
    ├── documents/manuals → [click]
```

Every entity card surfaces links to its related entities. The lens builds the link from the foreign key already in the DB row.

---

## How to Load a File (Signed URL Flow)

All buckets are private. The API generates a short-lived signed URL:

```
Frontend                          API                         Supabase Storage
   │                               │                              │
   │  GET /entity/part/{id}        │                              │
   │──────────────────────────────>│                              │
   │                               │  read pms_parts row          │
   │                               │  → image_storage_path        │
   │                               │  → image_bucket              │
   │                               │                              │
   │                               │  POST /storage/v1/object/sign│
   │                               │  { bucket, path, expiresIn } │
   │                               │─────────────────────────────>│
   │                               │         signedURL            │
   │                               │<─────────────────────────────│
   │                               │                              │
   │  { ..., image_url: signed }   │                              │
   │<──────────────────────────────│                              │
   │                               │                              │
   │  GET signed URL (direct)      │                              │
   │─────────────────────────────────────────────────────────────>│
   │         image bytes           │                              │
   │<─────────────────────────────────────────────────────────────│
```

The signed URL has a TTL (default 300s). The frontend fetches the file directly from Supabase — the API is not a proxy.

---

## Cross-Pollination — Same Data, Different Presentation

The same storage path can surface in multiple lenses with different treatment:

| Asset | Part Lens | Receiving Lens | Equipment Lens |
|-------|-----------|----------------|----------------|
| **Part photo** | Hero image, full-size | Thumbnail in line items | Small icon next to part name |
| **Label PDF** | "Print Label" button | "View Label" link per line item | Not shown |
| **Invoice photo** | Not shown | Hero image, zoomable | Not shown |
| **WO attachment** | Not shown | Not shown | Listed under "Recent Work Orders" |
| **Certificate** | Not shown | Not shown | Status badge + expiry date |

MVP: just return the signed URL in every lens response where the path exists. Presentation hierarchy is a frontend concern for Stage 3.

---

## Entity-to-Entity Links (Navigation Keys)

These foreign keys in the DB are what enable the hop-between-lenses navigation:

| From Lens | FK Column | To Lens |
|-----------|-----------|---------|
| Work Order | `equipment_id` | Equipment |
| Work Order | `fault_id` | Fault |
| Work Order → `pms_work_order_parts` | `part_id` | Part |
| Part | *(via `pms_work_order_parts`)* | Work Order |
| Part | *(via `pms_purchase_order_items`)* | Purchase Order |
| Receiving | `po_number` → `pms_purchase_orders` | Purchase Order |
| Receiving → `pms_receiving_items` | `part_id` | Part |
| Fault | `equipment_id` | Equipment |
| Equipment | *(via `pms_certificates.equipment_id`)* | Certificate |
| Equipment | *(via `pms_faults.equipment_id`)* | Fault |
| Purchase Order → items | `part_id` | Part |
| Certificate | `equipment_id` | Equipment |
| Certificate | `document_id` | Document |

---

## Known Gaps

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| 1 | `pms_attachments` has no `storage_bucket` column | API must hardcode entity_type→bucket mapping. New entity types silently have no bucket. | Add `storage_bucket` column or lookup table |
| 2 | `handover_exports.storage_path` is NULL | Lens can't load the HTML file without constructing path from bucket listing | Write path back to DB on export |
| 3 | `doc_metadata.storage_bucket` NULL for 3,004 rows | Assumed `documents` bucket but not explicit | Backfill with default `'documents'` |
| 4 | `pms_inventory_transactions.photo_storage_path` — no bucket column | Can't load stock-in photos | Add bucket col or infer `pms-receiving-images` |
| 5 | `pms_equipment_documents.storage_path` — bucket unknown | Equipment manuals not loadable | Clarify bucket assignment |
| 6 | `pms-work-order-photos` has 0 RLS policies | No authenticated user can read/write | Add RLS policies matching other photo buckets |

---

## MVP Plan

1. Add signed URL generation to each entity endpoint where `storage_path` exists
2. Return `image_url`, `attachments[]`, `label_url` etc. as signed URLs in the response
3. Return navigation links as `{ entity_type, entity_id }` pairs for the frontend to build `/entity/{type}/{id}` routes
4. Frontend renders links as clickable, files as downloadable/viewable
5. Defer: presentation hierarchy, cross-pollination styling, thumbnail generation
