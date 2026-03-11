# DATA AGENT — Receiving Lens

**Your role:** Verify the existing `/v1/entity/receiving/{id}` endpoint is correct.

---

## Endpoint

`GET /v1/entity/receiving/{receiving_id}`
**File:** `apps/api/pipeline_service.py` lines ~1282–1330
**Status:** ✅ EXISTS — verify shape only.

---

## DB Table (verified)

```
pms_receiving:
  id, yacht_id, vendor_name, vendor_reference, received_date,
  status, total, currency, notes, received_by, created_at, updated_at
```

---

## Required Response Shape

```json
{
  "id": "uuid",
  "vendor_name": "Marine Parts Co",
  "vendor_reference": "INV-2026-001",
  "received_date": "2026-03-10",
  "status": "draft",
  "total": 450.00,
  "currency": "USD",
  "notes": null,
  "received_by": "uuid",
  "created_at": "...",
  "updated_at": "..."
}
```

**CRITICAL:** `status` must be returned — it drives which action buttons appear in `getReceivingActions()` on the frontend. If status is missing, no actions will render.

---

## Role-Gated Actions

ALL roles: create_receiving, attach_receiving_image_with_comment, extract_receiving_candidates (advisory), update_receiving_fields, add_receiving_item, adjust_receiving_item, link_invoice_document, accept_receiving (signed), reject_receiving

---

## Success Criteria

200 + `id`, `vendor_name`, `status` non-null. `status` is the most critical field.
