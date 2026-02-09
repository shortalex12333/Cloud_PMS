# Receiving Lens - Camera Upload & Document Processing

## Overview

Complete end-to-end workflow for capturing/uploading receiving documents (invoices, packing slips, shipment labels, photos) with OCR/AI extraction and database persistence.

## Architecture

```
┌──────────────┐       ┌──────────────┐       ┌────────────────────┐
│   Frontend   │──────▶│   Backend    │──────▶│  Image-Processing  │
│   Camera/    │       │     Proxy    │       │  Service (Render)  │
│   Upload     │       │ /api/receiv  │       │  OCR + AI Extract  │
│              │◀──────│  ing/upload  │◀──────│                    │
└──────────────┘       └──────────────┘       └────────────────────┘
       │                                               │
       │                                               │
       ▼                                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        Supabase                              │
│  • pms_receiving_documents  (document links)                 │
│  • pms_receiving_extractions (OCR results - advisory)        │
│  • pms_receiving_items (line items - auto-populated)         │
│  • pms_receiving (header - auto-updated)                     │
└──────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend Component

**File:** `apps/web/src/components/receiving/ReceivingDocumentUpload.tsx`

**Features:**
- Camera capture (mobile/desktop with back camera preference)
- File upload (drag & drop or file picker)
- File validation (JPEG, PNG, HEIC, PDF ≤15MB)
- Live preview
- Upload with automatic retry (3 attempts, 30s backoff for 503)
- Tabular display of extracted data
- Save to database with confirmation

**Usage:**
```tsx
import { ReceivingDocumentUpload } from '@/components/receiving/ReceivingDocumentUpload';

<ReceivingDocumentUpload
  receivingId="uuid-of-receiving-record"
  defaultDocType="invoice" // or "packing_slip", "photo", "other"
  onComplete={(documentId, extractedData) => {
    console.log('Upload complete:', documentId, extractedData);
  }}
/>
```

### 2. API Client

**File:** `apps/web/src/lib/apiClient.ts`

**Methods:**

```typescript
// Upload document with retry logic
const result = await receivingApi.uploadDocument(
  receivingId: string,
  file: File,
  docType: 'invoice' | 'packing_slip' | 'photo' | 'other',
  comment?: string
);

// Returns:
{
  document_id: string;
  storage_path: string;
  extracted_data?: {
    vendor_name?: string;
    vendor_reference?: string;
    total?: number;
    currency?: string;
    line_items?: Array<{
      description: string;
      quantity?: number;
      unit_price?: number;
    }>;
    confidences?: Record<string, number>;
    flags?: string[];
  };
  processing_status: string;
}

// Get processing status
const status = await receivingApi.getDocumentStatus(
  receivingId: string,
  documentId: string
);
```

### 3. Save Flow

**File:** `apps/web/src/lib/receiving/saveExtractedData.ts`

**Functions:**

```typescript
// Save document link + extraction results
await saveExtractedData(
  receivingId, yachtId, documentId, docType, comment, extractedData
);

// Auto-populate line items from extraction (optional)
await autoPopulateLineItems(receivingId, yachtId, lineItems);

// Update header fields if empty (optional)
await updateReceivingHeader(receivingId, {
  vendor_name, vendor_reference, total, currency
});
```

### 4. Backend Proxy

**File:** `apps/api/routes/receiving_upload.py`

**Endpoint:** `POST /api/receiving/{receiving_id}/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Headers: `Authorization: Bearer <JWT>`
- Body:
  - `file`: File (JPEG/PNG/HEIC/PDF ≤15MB)
  - `doc_type`: "invoice" | "packing_slip" | "photo" | "other"
  - `comment`: Optional string

**Response:**
```json
{
  "document_id": "uuid",
  "storage_path": "{yacht_id}/receiving/{receiving_id}/...",
  "extracted_data": { ... },
  "processing_status": "complete"
}
```

**Error Handling:**
- `401`: Authentication failed
- `400`: Invalid file type or size
- `503`: Image-processing service unavailable (retry after 30s)
- `504`: Upload timeout (>30s)
- `502`: Failed to connect to image-processing service

### 5. Image-Processing Service (Render)

**URL:** `https://image-processing-givq.onrender.com`

**Free Tier Behavior:**
- Spins down after 15min inactivity
- Cold start: ~30-60 seconds
- Returns `503 Service Unavailable` during spin-up
- Frontend automatically retries

**Processing Pipelines:**
- **Section A - Invoices/Packing Slips:** OCR + table detection + AI normalization
- **Section B - Shipping Labels:** Label parsing + metadata extraction
- **Section C - Discrepancy Photos:** Photo attachment only (no processing)
- **Section D - Part Photos:** Photo attachment only (no processing)

**Extraction Capabilities:**
- Vendor name, invoice/PO number
- Line items (description, quantity, price)
- Totals, currency
- Dates
- Confidence scores per field

**Limitations:**
- Does NOT handle handwritten text
- Poor performance on blurry/low-res images
- Table detection requires structured layouts

## Database Schema

### pms_receiving_documents
Links uploaded documents to receiving records.

```sql
{
  id: UUID,
  yacht_id: UUID,
  receiving_id: UUID,
  document_id: UUID,  -- FK to doc_metadata
  doc_type: TEXT,     -- 'invoice', 'packing_slip', 'photo', 'other'
  comment: TEXT,
  created_at: TIMESTAMPTZ
}
```

### pms_receiving_extractions
Stores OCR/AI extraction results (advisory only - never auto-commits).

```sql
{
  id: UUID,
  yacht_id: UUID,
  receiving_id: UUID,
  source_document_id: UUID,
  payload: JSONB,  -- Full extraction results with confidence scores
  created_at: TIMESTAMPTZ
}
```

### pms_receiving_items (auto-populated)
Draft line items created from extraction.

```sql
{
  id: UUID,
  yacht_id: UUID,
  receiving_id: UUID,
  part_id: UUID (nullable),
  description: TEXT,
  quantity_received: NUMERIC,
  unit_price: NUMERIC,
  currency: TEXT,
  properties: JSONB,  -- { auto_populated: true, source: 'ocr_extraction' }
  created_at: TIMESTAMPTZ
}
```

### pms_receiving (header - auto-updated)
Header fields updated from extraction if empty.

```sql
{
  id: UUID,
  yacht_id: UUID,
  vendor_name: TEXT,
  vendor_reference: TEXT,
  total: NUMERIC,
  currency: TEXT,
  status: TEXT,  -- 'draft', 'in_review', 'accepted', 'rejected'
  ...
}
```

## User Flow

1. **Upload Document**
   - User clicks "Take Photo" or "Upload File"
   - Camera opens (mobile: back camera) OR file picker opens
   - User captures/selects image or PDF
   - Preview shows thumbnail

2. **Process Document**
   - User selects doc_type: invoice, packing_slip, photo, or other
   - User adds optional comment
   - User clicks "Upload & Process"
   - Frontend uploads to backend proxy
   - Backend forwards to Render service
   - If 503: Automatic retry after 30s (up to 3 attempts)

3. **Review Results**
   - Extracted data displayed in table format
   - Fields: vendor_name, vendor_reference, total, currency, line_items
   - User reviews accuracy

4. **Save to Database**
   - User clicks "Save to Database"
   - Frontend calls `saveExtractedData()`
   - Creates record in `pms_receiving_documents`
   - Creates record in `pms_receiving_extractions`
   - Auto-populates `pms_receiving_items` if line items extracted
   - Auto-updates `pms_receiving` header if fields empty
   - Shows success confirmation

5. **Upload Another (Optional)**
   - User can upload additional documents (photos, packing slips, etc.)
   - All linked to same receiving record

## Testing

### Automated Test

```bash
cd apps/api
python3 tests/test_receiving_upload.py
```

**Output:**
- ✅ Render service health check
- ✅ Wake-up retry logic test
- ✅ Backend proxy endpoint check
- 📋 Implementation summary

### Manual Browser Test

1. Start web app: `cd apps/web && npm run dev`
2. Navigate to receiving page
3. Add `<ReceivingDocumentUpload receivingId="test-uuid" />` to page
4. Test camera capture
5. Test file upload
6. Verify extraction results
7. Verify database save

### Expected Behavior

**First Upload (Cold Start):**
- Upload initiated
- Status: "Uploading..."
- Backend returns 503
- Status: "Retrying (1/3)... Service starting up, retrying in 30s..."
- Wait 30 seconds
- Retry succeeds
- Status: "Success"

**Subsequent Uploads (Warm Service):**
- Upload initiated
- Status: "Uploading..."
- Immediate success (< 5 seconds)
- Results displayed

## File Type Support

| Type | Extension | Max Size | Processing |
|------|-----------|----------|------------|
| JPEG | .jpg, .jpeg | 15MB | OCR + AI |
| PNG | .png | 15MB | OCR + AI |
| HEIC | .heic | 15MB | OCR + AI |
| PDF | .pdf | 15MB | OCR + AI |

**Validation:**
- Frontend validates before upload
- Backend validates before proxying
- Image-processing service validates before processing

## Error Handling

### Frontend Errors

| Error | Message | Action |
|-------|---------|--------|
| Invalid file type | "Invalid file type. Please upload JPG, PNG, HEIC, or PDF." | Show error, clear file |
| File too large | "File too large. Maximum size is 15MB." | Show error, clear file |
| Camera denied | "Camera access denied or unavailable" | Show error, suggest file upload |
| Upload failed | "Upload failed. Please try again." | Show error, allow retry |

### Backend Errors

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| 503 | Service unavailable (Render spin-down) | Auto-retry after 30s (3 attempts) |
| 401 | Authentication failed | Refresh token, retry |
| 400 | Invalid file | Show error |
| 504 | Timeout | Show error, suggest retry |
| 502 | Cannot connect to service | Show error |

## Performance

**Cold Start (First Upload):**
- Render service wake-up: ~30-60 seconds
- Upload + processing: +5-10 seconds
- **Total: ~35-70 seconds**

**Warm Service (Subsequent Uploads):**
- Upload: ~2-3 seconds
- OCR processing: ~2-4 seconds
- AI normalization: ~1-2 seconds
- **Total: ~5-10 seconds**

## Cost

**Image-Processing Service:**
- OCR (Tesseract): FREE
- AI normalization (GPT-4.1-mini): $0.03-0.15 per session
- Storage (Supabase): Included in plan

**Render Free Tier:**
- 750 hours/month free compute
- Spins down after 15min inactivity
- Unlimited requests while active

## Security

**Authentication:**
- All requests require valid JWT
- Yacht signature validates yacht ownership
- RLS enforced on all database operations

**File Validation:**
- Type whitelist (JPEG, PNG, HEIC, PDF only)
- Size limit (15MB)
- No executable files allowed

**Storage:**
- Files stored in yacht-specific bucket: `{yacht_id}/receiving/{receiving_id}/`
- Storage path validated by image-processing service
- RLS policies prevent cross-yacht access

## Troubleshooting

### Service Not Responding

**Symptom:** Upload times out or fails
**Cause:** Render service sleeping or down
**Solution:** Wait 30s and retry (automatic in frontend)

### Extraction Poor Quality

**Symptom:** Wrong data extracted
**Cause:** Blurry image, handwritten text, or poor layout
**Solution:**
1. Retake photo with better lighting
2. Ensure text is clear and readable
3. Use high-resolution scanner for paper documents
4. Manually correct extracted data before saving

### Database Save Fails

**Symptom:** "Failed to save data to database"
**Cause:** Missing yacht_id, invalid receiving_id, or RLS violation
**Solution:**
1. Verify user is authenticated
2. Verify receiving record exists
3. Check RLS policies
4. Check yacht_id in user metadata

## Future Enhancements

- [ ] Batch upload (multiple files at once)
- [ ] Manual field editing before save
- [ ] Confidence threshold warnings
- [ ] Auto-match parts from catalog
- [ ] Template-based extraction (vendor-specific layouts)
- [ ] Webhook notifications on completion
- [ ] Background processing queue
- [ ] Keep-alive ping to prevent Render spin-down
