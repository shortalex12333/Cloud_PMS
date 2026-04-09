# Entity Endpoints — Missing Backend Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 missing `/v1/entity/{type}/{id}` API endpoints so all lens detail pages load data correctly.

**Architecture:** All endpoints go into a new `apps/api/routes/entity_routes.py` file, mounted in `pipeline_service.py`. Each follows the identical pattern of the 5 existing entity endpoints: authenticate → get tenant client → query primary table → 404 if not found → map columns → return JSON.

**Tech Stack:** FastAPI, Supabase Python client, existing `get_tenant_client()` + `get_authenticated_user` patterns.

---

## What exists vs what is missing

### ✅ Working (5 endpoints in pipeline_service.py)
| Entity | Endpoint | Table |
|--------|----------|-------|
| fault | `/v1/entity/fault/{id}` | `pms_faults` |
| work_order | `/v1/entity/work_order/{id}` | `pms_work_orders` + 4 joins |
| equipment | `/v1/entity/equipment/{id}` | `pms_equipment` |
| part / inventory | `/v1/entity/part/{id}` | `pms_parts` |
| receiving | `/v1/entity/receiving/{id}` | `pms_receiving` |

### ❌ Missing (7 endpoints to add)
| Entity | Endpoint | Primary Table | What LensContent needs |
|--------|----------|--------------|------------------------|
| certificate | `/v1/entity/certificate/{id}` | `pms_vessel_certificates` → fallback `pms_crew_certificates` | name, certificate_type, issuing_authority, issue_date, expiry_date, status, certificate_number, notes, crew_member_id |
| document | `/v1/entity/document/{id}` | `doc_metadata` | filename, title, description, mime_type, file_size, url, thumbnail_url, created_at, created_by, classification, equipment_id, equipment_name |
| hours_of_rest | `/v1/entity/hours_of_rest/{id}` | `pms_hours_of_rest` | crew_name, date, rest_periods (JSON array), total_rest_hours, total_work_hours, is_compliant, status, verified_by, verified_at |
| shopping_list | `/v1/entity/shopping_list/{id}` | `pms_shopping_list_items` | title/part_name, status, requester_name, items[] |
| warranty | `/v1/entity/warranty/{id}` | `pms_warranties` | title/name, equipment_id, equipment_name, supplier, start_date, expiry_date, status, coverage, terms |
| handover_export | `/v1/entity/handover_export/{id}` | `handover_exports` | sections, user_signature, yacht_id |
| purchase_order | `/v1/entity/purchase_order/{id}` | `pms_purchase_orders` | supplier_name, po_number, status, order_date, expected_delivery, total_amount, currency, items[], notes |

## Key files

- **Create:** `apps/api/routes/entity_routes.py` — all 7 new endpoints
- **Modify:** `apps/api/pipeline_service.py` — mount the new router (add ~5 lines, follow existing pattern at lines 286-367)
- **Reference:** `apps/api/routes/certificate_handlers.py` — `get_certificate_handlers()` already exists, reuse it
- **Reference:** `apps/api/handlers/schema_mapping.py` — `get_table("vessel_certificates")` = `pms_vessel_certificates`

---

## Chunk 1: New entity_routes.py with all 7 endpoints

### Task 1: Create `apps/api/routes/entity_routes.py`

**Files:**
- Create: `apps/api/routes/entity_routes.py`

The file structure mirrors the existing pattern. Use `get_tenant_client()` and `get_authenticated_user` exactly as the fault/part endpoints do.

- [ ] **Step 1: Create the file with boilerplate + certificate endpoint**

```python
"""
entity_routes.py — /v1/entity/{type}/{id} endpoints for all lens types.

Follows the identical pattern as the 5 existing entity endpoints in
pipeline_service.py (fault, work_order, equipment, part, receiving).

Each endpoint:
1. Authenticates via get_authenticated_user
2. Gets tenant-isolated Supabase client
3. Queries primary table with yacht_id filter
4. Returns 404 if not found
5. Maps DB columns to the shape expected by the LensContent component
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

# Import shared auth/db helpers — same as pipeline_service.py
try:
    from auth_middleware import get_authenticated_user
    from db_client import get_tenant_client
    from handlers.schema_mapping import get_table
except ImportError:
    from auth_middleware import get_authenticated_user
    from db_client import get_tenant_client

router = APIRouter(tags=["entity-lenses"])


# =============================================================================
# CERTIFICATE — /v1/entity/certificate/{id}
# Tables: pms_vessel_certificates (try first), pms_crew_certificates (fallback)
# LensContent fields: name, certificate_type, issuing_authority, issue_date,
#   expiry_date, status, certificate_number, notes, crew_member_id
# =============================================================================

@router.get("/v1/entity/certificate/{certificate_id}")
async def get_certificate_entity(
    certificate_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch certificate by ID. Tries vessel certs first, falls back to crew certs."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        # Try vessel certificates first
        data = None
        cert_domain = "vessel"
        response = supabase.table("pms_vessel_certificates").select("*").eq(
            "id", certificate_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if response.data:
            data = response.data
        else:
            # Fallback: crew certificates
            response = supabase.table("pms_crew_certificates").select("*").eq(
                "id", certificate_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()
            if response.data:
                data = response.data
                cert_domain = "crew"

        if not data:
            raise HTTPException(status_code=404, detail="Certificate not found")

        return {
            "id": data.get("id"),
            "name": data.get("name") or data.get("certificate_name") or data.get("title", "Certificate"),
            "certificate_type": data.get("certificate_type") or data.get("type", "General"),
            "issuing_authority": data.get("issuing_authority") or data.get("authority"),
            "issue_date": data.get("issue_date") or data.get("issued_at"),
            "expiry_date": data.get("expiry_date") or data.get("expires_at"),
            "status": data.get("status", "valid"),
            "certificate_number": data.get("certificate_number") or data.get("cert_number"),
            "notes": data.get("notes"),
            "crew_member_id": data.get("crew_member_id") or data.get("person_id"),
            "domain": cert_domain,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOCUMENT — /v1/entity/document/{id}
# Table: doc_metadata
# LensContent fields: filename, title, description, mime_type, file_size,
#   url, thumbnail_url, created_at, created_by, classification,
#   equipment_id, equipment_name
# =============================================================================

@router.get("/v1/entity/document/{document_id}")
async def get_document_entity(
    document_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch document metadata by ID for document lens."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table("doc_metadata").select("*").eq(
            "id", document_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        data = response.data
        return {
            "id": data.get("id"),
            "filename": data.get("filename") or data.get("file_name") or data.get("name", "Document"),
            "title": data.get("title") or data.get("filename") or data.get("name", "Document"),
            "description": data.get("description"),
            "mime_type": data.get("mime_type") or data.get("content_type", "application/octet-stream"),
            "file_size": data.get("file_size") or data.get("size"),
            "url": data.get("url") or data.get("file_url") or data.get("storage_path"),
            "thumbnail_url": data.get("thumbnail_url"),
            "created_at": data.get("created_at"),
            "created_by": data.get("created_by") or data.get("uploaded_by"),
            "classification": data.get("classification") or data.get("document_type") or data.get("category"),
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "yacht_id": data.get("yacht_id"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HOURS OF REST — /v1/entity/hours_of_rest/{id}
# Table: pms_hours_of_rest
# LensContent fields: crew_name, date, total_rest_hours, total_work_hours,
#   is_compliant, status, verified_by, verified_at, rest_periods (JSON array)
# =============================================================================

@router.get("/v1/entity/hours_of_rest/{hor_id}")
async def get_hours_of_rest_entity(
    hor_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch hours of rest record by ID."""
    try:
        import json as _json
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table("pms_hours_of_rest").select("*").eq(
            "id", hor_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Hours of rest record not found")

        data = response.data

        # rest_periods stored as JSON string or already a list
        rest_periods_raw = data.get("rest_periods", [])
        if isinstance(rest_periods_raw, str):
            try:
                rest_periods = _json.loads(rest_periods_raw)
            except Exception:
                rest_periods = []
        else:
            rest_periods = rest_periods_raw or []

        return {
            "id": data.get("id"),
            "crew_name": data.get("crew_name") or data.get("user_name") or data.get("user_id"),
            "date": data.get("record_date") or data.get("date"),
            "total_rest_hours": data.get("total_rest_hours", 0),
            "total_work_hours": data.get("total_work_hours", 0),
            "is_compliant": data.get("is_compliant") or data.get("is_daily_compliant", True),
            "status": data.get("status", "draft"),
            "verified_by": data.get("verified_by"),
            "verified_at": data.get("verified_at"),
            "rest_periods": rest_periods,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hours_of_rest {hor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SHOPPING LIST — /v1/entity/shopping_list/{id}
# Table: pms_shopping_list_items (search index IDs are item IDs)
# LensContent fields: title/part_name, status, requester_name, items[]
# Strategy: fetch the item, then fetch sibling items (same yacht, same requester
#   within same day) to build the "list" view. Graceful fallback to single item.
# =============================================================================

@router.get("/v1/entity/shopping_list/{item_id}")
async def get_shopping_list_entity(
    item_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch shopping list item(s) by ID. Returns item in list context."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        # Fetch the primary item
        response = supabase.table("pms_shopping_list_items").select("*").eq(
            "id", item_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        item = response.data

        # Build items list — start with this item, try to fetch siblings
        # Siblings share same created_by and same day (approximate grouping)
        items = [item]
        try:
            created_at = item.get("created_at", "")
            date_prefix = created_at[:10] if created_at else None  # "YYYY-MM-DD"
            created_by = item.get("created_by") or item.get("requested_by")
            if date_prefix and created_by:
                siblings_resp = supabase.table("pms_shopping_list_items").select("*").eq(
                    "yacht_id", yacht_id
                ).eq("created_by", created_by).gte(
                    "created_at", f"{date_prefix}T00:00:00"
                ).lte(
                    "created_at", f"{date_prefix}T23:59:59"
                ).neq("id", item_id).limit(50).execute()
                if siblings_resp.data:
                    items = [item] + siblings_resp.data
        except Exception:
            pass  # Single item fallback

        # Requester name from first item
        requester_name = (
            item.get("requester_name") or
            item.get("requested_by_name") or
            item.get("created_by_name") or
            item.get("created_by")
        )

        return {
            "id": item.get("id"),
            "title": item.get("part_name") or item.get("name") or "Shopping List",
            "status": item.get("status", "pending"),
            "requester_name": requester_name,
            "approver_name": item.get("approver_name") or item.get("approved_by"),
            "created_at": item.get("created_at"),
            "approved_at": item.get("approved_at"),
            "yacht_id": yacht_id,
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch shopping_list {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WARRANTY — /v1/entity/warranty/{id}
# Table: pms_warranties
# LensContent fields: title/name, equipment_id, equipment_name, supplier,
#   start_date, expiry_date, status, coverage, terms
# =============================================================================

@router.get("/v1/entity/warranty/{warranty_id}")
async def get_warranty_entity(
    warranty_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch warranty by ID for warranty lens."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table("pms_warranties").select("*").eq(
            "id", warranty_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Warranty not found")

        data = response.data
        return {
            "id": data.get("id"),
            "title": data.get("name") or data.get("title") or data.get("warranty_number", "Warranty"),
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "supplier": data.get("supplier") or data.get("supplier_name"),
            "start_date": data.get("start_date") or data.get("warranty_start"),
            "expiry_date": data.get("expiry_date") or data.get("warranty_end") or data.get("expires_at"),
            "status": data.get("status", "active"),
            "coverage": data.get("coverage") or data.get("coverage_description"),
            "terms": data.get("terms") or data.get("terms_conditions"),
            "warranty_number": data.get("warranty_number"),
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch warranty {warranty_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HANDOVER EXPORT — /v1/entity/handover_export/{id}
# Table: handover_exports
# LensContent fields: sections, user_signature / userSignature, yacht_id
# =============================================================================

@router.get("/v1/entity/handover_export/{export_id}")
async def get_handover_export_entity(
    export_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch handover export by ID for handover export lens."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table("handover_exports").select("*").eq(
            "id", export_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Handover export not found")

        data = response.data
        return {
            "id": data.get("id"),
            "yacht_id": data.get("yacht_id"),
            "sections": data.get("sections") or [],
            "userSignature": data.get("user_signature") or data.get("userSignature"),
            "user_signature": data.get("user_signature") or data.get("userSignature"),
            "status": data.get("status", "draft"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "submitted_at": data.get("submitted_at"),
            "countersigned_at": data.get("countersigned_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch handover_export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PURCHASE ORDER — /v1/entity/purchase_order/{id}
# Table: pms_purchase_orders + pms_purchase_order_items (join)
# Page fields: supplier_name, po_number, status, order_date, expected_delivery,
#   total_amount, currency, items[], notes
# =============================================================================

@router.get("/v1/entity/purchase_order/{po_id}")
async def get_purchase_order_entity(
    po_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch purchase order by ID for purchasing detail page."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table("pms_purchase_orders").select("*").eq(
            "id", po_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        data = response.data

        # Fetch line items
        items = []
        try:
            items_resp = supabase.table("pms_purchase_order_items").select("*").eq(
                "purchase_order_id", po_id
            ).execute()
            if items_resp.data:
                items = [
                    {
                        "id": i.get("id"),
                        "name": i.get("name") or i.get("part_name") or i.get("description", "Item"),
                        "description": i.get("description"),
                        "quantity": i.get("quantity") or i.get("quantity_ordered", 0),
                        "unit_price": i.get("unit_price") or i.get("price", 0),
                        "currency": i.get("currency") or data.get("currency", "USD"),
                    }
                    for i in items_resp.data
                ]
        except Exception:
            pass  # No items table or empty — return empty list

        return {
            "id": data.get("id"),
            "po_number": data.get("po_number"),
            "supplier_name": data.get("supplier_name") or data.get("vendor_name", "Supplier"),
            "status": data.get("status", "draft"),
            "order_date": data.get("order_date") or data.get("created_at"),
            "expected_delivery": data.get("expected_delivery") or data.get("expected_delivery_date"),
            "total_amount": data.get("total_amount") or data.get("total", 0),
            "currency": data.get("currency", "USD"),
            "notes": data.get("notes"),
            "items": items,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch purchase_order {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Verify file was created and has no obvious Python syntax errors**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -c "import ast; ast.parse(open('routes/entity_routes.py').read()); print('Syntax OK')"
```
Expected: `Syntax OK`

- [ ] **Step 3: Commit the new file**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/routes/entity_routes.py
git commit -m "feat: add 7 missing entity endpoints for lens detail pages

certificate, document, hours_of_rest, shopping_list, warranty,
handover_export, purchase_order — all follow existing fault/part
endpoint pattern (tenant-isolated, 404 on not found, mapped response)"
```

---

## Chunk 2: Mount the router in pipeline_service.py

### Task 2: Add router mount to pipeline_service.py

**Files:**
- Modify: `apps/api/pipeline_service.py` (add ~7 lines following the pattern at lines 286-367)

- [ ] **Step 1: Find the existing router mount block to use as reference**

```bash
grep -n "include_router\|entity_routes" apps/api/pipeline_service.py | tail -20
```
Note the last `include_router` call (currently around line 367). Add the new mount after it.

- [ ] **Step 2: Add the mount — insert after the last existing include_router block**

In `pipeline_service.py`, after the `search_streaming_router` mount block (currently the last one, ~line 367), add:

```python
    try:
        from routes.entity_routes import router as entity_routes_router
        app.include_router(entity_routes_router)
        logger.info("✓ entity_routes mounted")
    except Exception as e:
        logger.error(f"Failed to mount entity_routes: {e}")
```

- [ ] **Step 3: Rebuild the Docker API container**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
docker compose up --build -d api
```
Expected: Build completes, `celeste-api` container restarts healthy.

- [ ] **Step 4: Verify all 7 new routes are registered**

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
paths = spec.get('paths', {})
entity_paths = [p for p in paths if '/v1/entity/' in p]
print('\n'.join(sorted(entity_paths)))
"
```
Expected output includes:
```
/v1/entity/certificate/{certificate_id}
/v1/entity/document/{document_id}
/v1/entity/handover_export/{export_id}
/v1/entity/hours_of_rest/{hor_id}
/v1/entity/purchase_order/{po_id}
/v1/entity/shopping_list/{item_id}
/v1/entity/warranty/{warranty_id}
```
(Plus the 5 existing ones)

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/pipeline_service.py
git commit -m "feat: mount entity_routes router in pipeline_service

Registers 7 new /v1/entity/* endpoints so all lens detail pages
can fetch their data from the API"
```

---

## Chunk 3: Test each endpoint with live data

The Docker API is healthy. Use `celeste.sh` to mint a JWT, then curl each endpoint.

### Task 3: Live endpoint validation

- [ ] **Step 1: Get a real entity ID for each type from the DB**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "certificate" 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    if line.startswith('data:'):
        try:
            d = json.loads(line[5:])
            if d.get('type') == 'result_batch':
                for r in d.get('results', []):
                    print(r.get('object_type'), r.get('object_id'))
        except: pass
" | head -20
```

Do the same for: document, hours_of_rest, shopping_list, warranty, purchase_order

- [ ] **Step 2: Curl certificate endpoint with a real ID**

```bash
TOKEN=$(cat /tmp/jwt_token.txt 2>/dev/null || ./celeste.sh search "x" 2>/dev/null && cat /tmp/jwt_token.txt)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/certificate/{REAL_CERT_ID} | python3 -m json.tool
```
Expected: JSON with `id`, `name`, `certificate_type`, `status`, not a 404.

- [ ] **Step 3: Curl each remaining endpoint (document, hours_of_rest, shopping_list, warranty, handover_export, purchase_order)**

Same pattern. For each: confirm 200 + expected fields, not 404/500.

- [ ] **Step 4: For any that return 500 — check column name mismatches**

```bash
docker logs celeste-api --tail=50 2>&1 | grep -i "error\|500\|column"
```
Column name mismatches are the most common issue. Fix by adjusting the `.get("actual_column_name")` call in `entity_routes.py`.

- [ ] **Step 5: Commit any column name fixes**

```bash
git add apps/api/routes/entity_routes.py
git commit -m "fix: correct column name mappings in entity_routes after live testing"
```

---

## Chunk 4: Verify lenses load in browser

### Task 4: End-to-end browser verification

For each lens, verify: search result click → route navigates → data loads → no error state.

- [ ] **Step 1: Open frontend at http://localhost:3000**

- [ ] **Step 2: Verify each lens loads (search → click → detail page)**

| Search query | Expected entity type | Verify |
|-------------|---------------------|--------|
| "certificate" or "SOLAS" | certificate | Name, dates, status visible |
| "manual" or "pdf" | document | Filename, type visible |
| "hours of rest" | hours_of_rest | Crew name, compliance visible |
| "shopping list" or "order oil" | shopping_list | Item(s) and status visible |
| "warranty" | warranty | Equipment, dates visible |
| purchase order reference | purchase_order | PO number, supplier visible |

- [ ] **Step 3: For any lens showing error state — check browser console for the actual HTTP error**

The error state in RouteShell renders for any non-200 response. The console will show the exact URL and status code. Fix the endpoint if needed.

- [ ] **Step 4: Rebuild + restart after any fixes**

```bash
docker compose up --build -d api
```

- [ ] **Step 5: Final commit — mark milestone complete**

```bash
git add -A
git commit -m "feat: all entity lens detail pages load correctly

7 missing API endpoints added. All 12 routed lenses (+ purchasing)
now return data from DB. Verified against live Docker container."
```

---

## Notes on known uncertainties

**Shopping list ID ambiguity:** The search_index `object_id` for `shopping_list` type may point to:
- `pms_shopping_list_items.id` (likely — most common pattern)
- A parent "shopping list request" ID (if such a table exists)

The endpoint handles `pms_shopping_list_items`. If search results return a different ID space, the 404 will make it obvious. Fix by adjusting the table name.

**Document URL:** `doc_metadata.url` may be a Supabase storage path, not a full signed URL. The `DocumentLensContent` accepts a raw URL. If the document preview doesn't load, the URL generation (signing) may need to be added — but that's a separate task.

**Column names:** The `data.get("column_name")` calls use the most likely column names based on other queries in the codebase. A handful may need adjustment after the first live test. This is expected and fast to fix — 1-line changes.
