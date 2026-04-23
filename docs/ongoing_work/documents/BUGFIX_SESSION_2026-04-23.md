# Documents Domain — Bug Fix Session 2026-04-23

**Engineer:** Claude Sonnet 4.6 (session continuing from 2026-04-22 context)
**PRs shipped:** #652 (documents 422 + formatter), #654 (folder tree + PDF viewer)
**Status:** Both PRs merged to `main`. Render deploy triggered. Vercel auto-deploy triggered.

---

## Overview

Four distinct bugs found and fixed in the Documents domain during this session.
Two were pre-existing and unknown; two were discovered during the fix work itself.
All bugs were in separate layers of the stack — backend formatter, backend route limit, frontend tree builder, frontend viewer component.

---

## Bug 1 — 422 Unprocessable Entity on /documents page load

**Severity:** P0 — page completely unusable  
**Symptom:** Every visit to `/documents` returned a 422 error. No documents loaded.  
**Root cause:** The frontend requested `limit=1000` but the backend enforced `le=500` (maximum 500).

**Source files:**
- Frontend: `apps/web/src/app/documents/page.tsx:33`
  ```ts
  const TREE_PAGE_SIZE = 1000;
  // ...
  params.set('limit', String(TREE_PAGE_SIZE));  // line ~117
  ```
  This sent `?limit=1000` to the API.

- Backend: `apps/api/routes/vessel_surface_routes.py:672`
  ```python
  # Before:
  limit: int = Query(50, ge=1, le=500)
  # After (fix):
  limit: int = Query(50, ge=1, le=2000)
  ```
  FastAPI's `le=500` validator rejected any value above 500, returning 422.

**Fix:** Raised `le=500` → `le=2000` in `vessel_surface_routes.py:672`.  
**PR:** #652

---

## Bug 2 — Documents list rendered "Untitled" for all files

**Severity:** P1 — all documents showed wrong title/metadata  
**Symptom:** Every row in the documents list showed "Untitled" as the title and wrong metadata.  
**Root cause:** The backend `_format_record()` function in `vessel_surface_routes.py` had no `elif domain == "documents":` case. It fell through to the generic formatter which looks for a `"name"` column — which doesn't exist on `doc_metadata` (the column is `"filename"`).

Three separate formatter errors, all in `apps/api/routes/vessel_surface_routes.py`:

### 2a — Missing documents case in `_format_record()`
```python
# Before: no case for "documents" domain — fell to generic handler
# After: added at approx line 846
elif domain == "documents":
    filename = record.get("filename") or "Untitled"
    doc_type = record.get("doc_type")
    base.update({
        "ref": f"D-{str(record.get('id', ''))[:6]}",
        "title": filename,
        "filename": filename,
        "doc_type": doc_type,
        "original_path": record.get("original_path"),
        "storage_path": record.get("storage_path", ""),
        "size_bytes": record.get("size_bytes"),
        "uploaded_by_name": record.get("uploaded_by_name"),
        "created_at": record.get("created_at"),
        "content_type": record.get("content_type"),
        "tags": record.get("tags") or [],
        "meta": f"{doc_type or 'Document'} · {_age_display(record.get('created_at'))}",
    })
```

### 2b — Wrong column in `_name_column()`
```python
# Before (apps/api/routes/vessel_surface_routes.py, _name_column dict):
"documents": "name"
# After:
"documents": "filename"
```
`doc_metadata` has no `name` column. The inline search (Tier 3) was always returning empty display names.

### 2c — Wrong column names in `_format_inline_result()`
```python
# Before:
record.get("name")          # column doesn't exist on doc_metadata
record.get("document_type") # column doesn't exist; correct name is "doc_type"
"document_name": record.get("name")
"document_type": record.get("document_type")

# After:
record.get("filename")
record.get("doc_type")
"document_name": record.get("filename")
"document_type": record.get("doc_type")
```

**PR:** #652

---

## Bug 3 — Folder tree showed local filesystem paths instead of bucket folders

**Severity:** P1 — tree structure was completely wrong  
**Symptom:** The `/documents` folder tree showed entries like:
```
> C Users
  > celeste7
    > Documents
      > Cloud_PMS_render
      > test_documents
> yacht-nas
> 05_DRAWINGS
> 06_PROCEDURES
```
Instead of the actual bucket structure (`01_BRIDGE`, `01_OPERATIONS`, etc.).

**Root cause:** `apps/web/src/components/documents/docTreeBuilder.ts:142` used `doc.original_path` to build the folder tree. `original_path` stores the file's **original filesystem path on the machine that uploaded it** (e.g. `C:\Users\celeste7\Documents\Cloud_PMS_render\test_documents\something.pdf`). Those paths are upload provenance metadata — they have nothing to do with where the file lives in the storage bucket.

The correct source is `storage_path`, which stores the actual Supabase storage bucket path in the format `{yacht_uuid}/{folder}/{filename}`.

```typescript
// Before (docTreeBuilder.ts:142):
const allSegments = doc.original_path ? splitPath(doc.original_path) : [];

// After:
// Use storage_path (the real bucket path) to build the folder hierarchy.
// storage_path format: {yacht_uuid}/{folder_1}/.../{folder_n}/{filename}
// Strip the leading yacht UUID so the tree mirrors the bucket folder structure.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const rawPath = doc.storage_path || '';
const allSegments = (() => {
  if (!rawPath) return [];
  const segs = splitPath(rawPath);
  return segs.length > 0 && UUID_RE.test(segs[0]) ? segs.slice(1) : segs;
})();
```

The UUID strip is necessary because Supabase storage paths are prefixed with the yacht's UUID for isolation (e.g. `85fe1119-b04c-41ac-80f1-829d23322598/01_OPERATIONS/file.pdf`). Stripping the first segment when it is a UUID gives `01_OPERATIONS/file.pdf`, which correctly mirrors the bucket.

Files with empty `storage_path` fall back to doc_type grouping (unchanged behaviour).

**PR:** #654

---

## Bug 4 — PDF viewer showed empty placeholder (no pages rendered)

**Severity:** P1 — documents were unopenable  
**Symptom:** Clicking any document opened the detail panel showing the filename text twice but no file content, no pages, no console errors about fetch failures.

**Root cause (three layers):**

### Layer 1 — `DocumentContent.tsx` had no viewer
`apps/web/src/components/lens-v2/entity/DocumentContent.tsx` only rendered a static styled `<div>` containing the document title and metadata text. There was no `<iframe>`, no `<img>`, no PDF.js, no blob URL render. The "preview area" was just decorative HTML.

### Layer 2 — `loadDocumentWithBackend()` was never called
`apps/web/src/lib/documentLoader.ts` contained a complete `loadDocumentWithBackend(documentId)` function that fetches a signed URL, downloads the blob, and returns a blob URL. It was never imported or called by `DocumentContent.tsx`.

### Layer 3 — The sign endpoint didn't exist
`documentLoader.ts:66` calls `POST ${API_BASE}/v1/documents/${documentId}/sign`. This endpoint did not exist in the backend. The router at `apps/api/routes/document_routes.py` had no `/{doc_id}/sign` route.

**Fix — three parts:**

### Part A: Add `POST /v1/documents/{doc_id}/sign` to backend
Added to `apps/api/routes/document_routes.py` (appended after line ~1232):
```python
@router.post("/{doc_id}/sign")
async def sign_document_url(
    doc_id: str,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: Optional[str] = Query(None),
):
    resolved_yacht_id = resolve_yacht_id(auth, yacht_id)
    supabase = _get_tenant_client(auth["tenant_key_alias"])

    result = supabase.table("doc_metadata").select(
        "id, filename, storage_path, content_type, size_bytes"
    ).eq("id", doc_id).eq("yacht_id", resolved_yacht_id).maybe_single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    doc = result.data
    storage_path = doc.get("storage_path") or ""
    if not storage_path:
        raise HTTPException(status_code=422, detail="Document has no storage path")

    signed = supabase.storage.from_(DOCUMENTS_BUCKET).create_signed_url(
        storage_path, expires_in=600  # 10-minute TTL
    )
    signed_url = signed.get("signedURL") or signed.get("signedUrl") or ""
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate document URL")

    return {
        "signed_url": signed_url,
        "filename": doc.get("filename", "document"),
        "content_type": doc.get("content_type", "application/octet-stream"),
        "size_bytes": doc.get("size_bytes"),
        "expires_at": int(time.time()) + 600,
    }
```
Notes:
- Uses `DOCUMENTS_BUCKET = 'documents'` constant already defined at `document_routes.py:97`
- Uses `_get_tenant_client(auth["tenant_key_alias"])` — same pattern as all other routes in this file
- Scoped by `yacht_id` to prevent cross-vessel access
- `signed.get("signedURL") or signed.get("signedUrl")` — handles both casing variants from supabase-py

### Part B: Wire `DocumentContent.tsx` to call the loader
`apps/web/src/components/lens-v2/entity/DocumentContent.tsx`:
```tsx
import { loadDocumentWithBackend } from '@/lib/documentLoader';

// Added inside component (uses entityId from context):
const { entity, entityId, ... } = useEntityLensContext();
const [blobUrl, setBlobUrl] = React.useState<string | null>(null);
const [fileLoading, setFileLoading] = React.useState(false);
const [fileError, setFileError] = React.useState<string | null>(null);
const blobUrlRef = React.useRef<string | null>(null);

React.useEffect(() => {
  if (!entityId) return;
  setFileLoading(true);
  setFileError(null);
  setBlobUrl(null);
  loadDocumentWithBackend(entityId).then((result) => {
    if (result.success && result.url) {
      blobUrlRef.current = result.url;
      setBlobUrl(result.url);
    } else {
      setFileError(result.error ?? 'Failed to load document');
    }
    setFileLoading(false);
  });
  return () => {
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
  };
}, [entityId]);
```

The cleanup function uses a `ref` (not state) to always have the current blob URL so `URL.revokeObjectURL` doesn't get a stale closure value.

### Part C: Replace static placeholder with real viewer
```tsx
// Replaces the old static <div> placeholder:
{fileLoading ? (
  <div style={{ display: 'flex', alignItems: 'center', ... }}>
    <div style={{ /* CSS spinner */ }} />
    Loading document…
  </div>
) : blobUrl && mime_type.startsWith('image/') ? (
  <img src={blobUrl} alt={file_name ?? title} style={{ maxWidth: '100%', ... }} />
) : blobUrl ? (
  <iframe
    src={blobUrl}
    title={file_name ?? title}
    style={{ width: '100%', height: 680, border: '1px solid var(--border-sub)', ... }}
  />
) : fileError ? (
  <div style={{ color: 'var(--red)', ... }}>{fileError}</div>
) : null}
```

Download button in the action slot now uses `blobUrl ?? file_url` so it works whether the entity endpoint returns a file URL or we fetched it ourselves via the sign endpoint.

**PR:** #654

---

## Files Changed — Complete Reference

| File | Change |
|------|--------|
| `apps/api/routes/vessel_surface_routes.py:672` | `le=500` → `le=2000` (422 fix) |
| `apps/api/routes/vessel_surface_routes.py` ~846 | Added `elif domain == "documents":` case in `_format_record()` |
| `apps/api/routes/vessel_surface_routes.py` ~1101 | `"documents": "name"` → `"documents": "filename"` in `_name_column()` |
| `apps/api/routes/vessel_surface_routes.py` ~1108 | Fixed `record.get("name")` → `record.get("filename")` and `"document_type"` → `"doc_type"` in `_format_inline_result()` |
| `apps/api/routes/document_routes.py:17` | Added `import time` |
| `apps/api/routes/document_routes.py` ~1234 | Added `POST /{doc_id}/sign` endpoint |
| `apps/web/src/components/documents/docTreeBuilder.ts:142` | Changed tree path source from `original_path` → `storage_path` with UUID prefix stripping |
| `apps/web/src/components/lens-v2/entity/DocumentContent.tsx` | Added `import { loadDocumentWithBackend }`, added PDF loading effect, replaced static placeholder with `<iframe>` / `<img>` viewer |

---

## What Was NOT Changed

- `apps/web/src/app/documents/page.tsx` — `TREE_PAGE_SIZE = 1000` stays as-is (backend limit raised to accommodate it)
- `apps/web/src/lib/documentLoader.ts` — `loadDocumentWithBackend()` was already correct; it just needed to be called
- Storage paths or bucket names — unchanged
- `doc_metadata` schema — unchanged

---

## Known Remaining Issues (out of scope for this session)

| Issue | Location | Notes |
|-------|----------|-------|
| `storage_path` coverage is ~93% per pre-D1 probe | `doc_metadata` TENANT DB | The remaining 7% of docs with null `storage_path` fall back to doc_type folder grouping, which is acceptable |
| PDF viewer is `<iframe>` not PDF.js | `DocumentContent.tsx` | `<iframe>` works in all major browsers for PDFs. If browser PDF plugin is disabled, user sees a fallback message. PDF.js would give page count, zoom, print — deferral decision for CEO |
| Non-PDF, non-image files (Excel, Word, ZIP) | `DocumentContent.tsx` | No inline viewer; only Download button. Acceptable for MVP |
| Signed URL TTL is 10 min | `document_routes.py` sign endpoint | If user leaves panel open > 10 min, blob URL still works (browser holds it). On re-open, a fresh fetch occurs |

---

# Purchase Order Domain — Bug Fix Session 2026-04-23

**PRs shipped:** #654 (same PR as documents tree/viewer — combined commit `e1f35d42`)

---

## Overview

Five distinct bugs found and fixed in the Purchase Order domain during this session.
All bugs were discovered while auditing why PO actions were returning 400 errors.

---

## Bug 5 — PO actions returning 400 ("no handler matched")

**Severity:** P0 — `order_part`, `approve_purchase`, `add_item_to_purchase`, `update_purchase_status`, `upload_invoice` all returned 400 on submit  
**Symptom:** Clicking any of those five PO actions produced a 400 from the actions executor. No DB write, no error detail.  
**Root cause:** `apps/api/routes/handlers/internal_adapter.py` maintains `_ACTIONS_TO_ADAPT` — a list of action IDs that bridge the legacy p0_actions dispatcher to the new action_router. All five PO actions existed in the registry and had handlers in the internal dispatcher, but they were missing from `_ACTIONS_TO_ADAPT`. The executor received them, found no adapter bridge, and returned 400.

```python
# Before (internal_adapter.py:152-160): missing entries
_ACTIONS_TO_ADAPT = [
    ...
    "submit_warranty_claim",
    "suspend_certificate",
    "track_po_delivery",
    # ← order_part, approve_purchase, add_item_to_purchase,
    #   update_purchase_status, upload_invoice not here
    "update_document_comment",
    ...
]

# After: added at internal_adapter.py:155-159
    "order_part",
    "approve_purchase",
    "add_item_to_purchase",
    "update_purchase_status",
    "upload_invoice",
```

**Source:** `apps/api/routes/handlers/internal_adapter.py:155-159`  
**PR:** #654

---

## Bug 6 — Wrong `required_fields` on `add_po_note` (equipment_id instead of purchase_order_id)

**Severity:** P1 — frontend form generated an `equipment_id` field on a PO note, causing required-field validation to fail  
**Root cause:** `registry.py` had `required_fields=["yacht_id", "equipment_id", "note_text"]` for `add_po_note`. The `equipment_id` was copy-paste from the equipment domain. The correct FK is `purchase_order_id`.

```python
# Before (registry.py add_po_note):
required_fields=["yacht_id", "equipment_id", "note_text"],

# After:
required_fields=["yacht_id", "purchase_order_id", "note_text"],
```

**Source:** `apps/api/action_router/registry.py` (add_po_note definition)  
**PR:** #654

---

## Bug 7 — PO actions gated to captain/manager only (purser/chief_steward locked out)

**Severity:** P1 — purser and chief_steward are the primary PO users but `allowed_roles` excluded them  
**Root cause:** Every PO action in the registry was restricted to `["chief_engineer", "chief_officer", "captain", "manager"]`. The purser role owns the procurement workflow. Chief_steward owns interior supply orders. Both were silently gated out — their action buttons never appeared.

Fixed across all PO registry entries:
```python
# Before (pattern across all PO actions):
allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],

# After:
allowed_roles=["purser", "chief_engineer", "chief_officer", "chief_steward", "captain", "manager"],
```

**Source:** `apps/api/action_router/registry.py` — all PO action definitions  
**PR:** #654

---

## Bug 8 — Frontend PO primary buttons used non-existent action IDs

**Severity:** P1 — primary action buttons (Submit PO, Approve PO, Mark Received) were dead — clicking produced "action not found"  
**Root cause:** `PurchaseOrderContent.tsx` had hardcoded legacy action ID strings (`submit_po`, `approve_po`, `receive_po`) that did not match the registry. The actual registered action IDs are `submit_purchase_order`, `approve_purchase_order`, `mark_po_received`.

```typescript
// Before (PurchaseOrderContent.tsx primaryActionKey assignments):
primaryActionKey="submit_po"          // does not exist in registry
primaryActionKey="approve_po"         // does not exist in registry
primaryActionKey="receive_po"         // does not exist in registry

// After:
primaryActionKey="submit_purchase_order"
primaryActionKey="approve_purchase_order"
primaryActionKey="mark_po_received"
```

**Source:** `apps/web/src/components/lens-v2/entity/PurchaseOrderContent.tsx`  
**PR:** #654

---

## Bug 9 — Ghost registry entries with no handlers

**Severity:** P2 — `track_delivery`, `create_purchase_request`, `track_po_delivery` appeared in the actions menu but had no handler in the internal dispatcher — always 400  
**Root cause:** Three registry entries referenced endpoints that were never built. They were placeholder definitions added during initial PO scaffolding.

Removed from `registry.py`:
- `track_delivery` — no handler exists
- `create_purchase_request` — no handler exists
- `track_po_delivery` — no handler exists (distinct from `track_po_delivery` in `_ACTIONS_TO_ADAPT` which was a different dead entry — both removed)

**Source:** `apps/api/action_router/registry.py`  
**PR:** #654

---

## Bug 10 — `add_item_to_purchase` not state-gated (allowed on finalised POs)

**Severity:** P2 — user could attempt to add line items to a submitted/approved/received PO  
**Root cause:** `entity_actions.py` had no state gate for `purchase_order` entity type. The `add_item_to_purchase` action was always enabled regardless of PO status.

```python
# Added to _apply_state_gate() in entity_actions.py:
elif entity_type == "purchase_order":
    # add_item_to_purchase is only valid while the PO is still a draft
    _PO_DRAFT_ONLY = {"add_item_to_purchase"}
    if status not in ("draft", "") and action_id in _PO_DRAFT_ONLY:
        return True, f"Cannot add items to a PO with status '{status}'"
```

**Source:** `apps/api/action_router/entity_actions.py:310-315`  
**PR:** #654

---

## Files Changed — Purchase Order Complete Reference

| File | Change |
|------|--------|
| `apps/api/routes/handlers/internal_adapter.py:155-159` | Added `order_part`, `approve_purchase`, `add_item_to_purchase`, `update_purchase_status`, `upload_invoice` to `_ACTIONS_TO_ADAPT` |
| `apps/api/action_router/registry.py` | Fixed `add_po_note` required_fields (`equipment_id` → `purchase_order_id`); widened `allowed_roles` on all PO actions to include `purser` + `chief_steward`; removed `track_delivery`, `create_purchase_request`, `track_po_delivery`; added `submit_purchase_order`, `approve_purchase_order`, `mark_po_received` as Phase 4 domain actions; added `field_metadata` to `add_to_handover` for richer form UX |
| `apps/web/src/components/lens-v2/entity/PurchaseOrderContent.tsx` | Fixed primary button `primaryActionKey` values: `submit_po` → `submit_purchase_order`, `approve_po` → `approve_purchase_order`, `receive_po` → `mark_po_received` |
| `apps/api/action_router/entity_actions.py:310-315` | Added purchase_order state gate — `add_item_to_purchase` disabled when status is not `draft` |
| `apps/api/action_router/entity_prefill.py` | Expanded PO → `add_to_handover` prefill to include `status` and `department` fields |
