# Email Attachment Viewer + Micro-Actions

## Overview

Email attachments are viewed inline within CelesteOS without triggering local file saves. When opened, attachments are optionally persisted to Supabase Storage, enabling document micro-actions like "Add to Handover" or "Attach to Work Order".

## Data Flow

```
User clicks attachment
        ↓
fetchAttachmentBlob() → Graph API
        ↓
Create blob URL (in-memory only)
        ↓
Open DocumentViewerOverlay (inline preview)
        ↓
[Background] saveAttachmentForPreview()
        ↓
POST /email/evidence/save-attachment
        ↓
Graph API fetch → Supabase Storage upload
        ↓
Create doc_yacht_library record
        ↓
Return document_id to viewer
        ↓
Enable micro-action dropdown
```

## SOC-2 Controls

| Control | Implementation |
|---------|----------------|
| **No local persistence by default** | Blob URL used for inline preview (browser memory only) |
| **Download button hidden** | `allowDownload={false}` for email attachments |
| **Storage encryption** | Supabase Storage encrypts at rest |
| **Yacht isolation** | Path prefix `{yacht_id}/email-attachments/...` |
| **Signed URL TTL** | Backend signer uses 10-minute TTL (configurable) |
| **Role-based access** | `EVIDENCE_SAVE_ROLES` enforced on save endpoint |
| **Audit logging** | Every save logged to `pms_audit_log` |
| **File type whitelist** | `ALLOWED_ATTACHMENT_TYPES` enforced server-side |
| **Size limits** | `MAX_ATTACHMENT_SIZE_BYTES` (50MB) enforced |

## Components

### Frontend

| File | Purpose |
|------|---------|
| `DocumentViewerOverlay.tsx` | Inline viewer with `allowDownload` prop and micro-action dropdown |
| `EmailSurface.tsx` | Attachment click handler, save-for-preview flow |
| `useEmailData.ts` | `saveAttachmentForPreview()` API call |

### Backend

| Endpoint | Purpose |
|----------|---------|
| `POST /email/evidence/save-attachment` | Save attachment to storage, create document record |
| `GET /email/message/{id}/attachments/{id}/download` | Fetch attachment bytes from Graph |

## Micro-Actions

When a document is saved (has `documentId`), the viewer shows an Actions dropdown:

| Action | Description |
|--------|-------------|
| Add to Handover | Add document to current handover |
| Attach to Work Order | Link document to a work order |
| Unlink from Work Order | Remove document-WO link |

## Configuration

### Environment Variables

```bash
# Feature flag (optional)
EMAIL_EVIDENCE_ENABLED=true

# Storage bucket (default: 'documents' with 'email-attachments/' subfolder)
EMAIL_ATTACHMENT_BUCKET=documents

# Max file size (default: 50MB)
MAX_ATTACHMENT_SIZE_BYTES=52428800
```

### Allowed File Types

```python
ALLOWED_ATTACHMENT_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    # ... and more
]
```

## Testing

### Playwright E2E

```bash
cd apps/web
npx playwright test email-attachment-viewer.spec.ts
```

### Backend (pytest)

```bash
cd apps/api
pytest tests/test_email_attachment_save.py -v
```

## Known Limitations

1. **Backend signing not yet implemented** - Currently uses client-side Storage signing. Backend signer with shorter TTL recommended for production.

2. **Micro-action handlers are placeholders** - "Add to Handover" etc. show alerts; full mutation logic TBD.

3. **No dedicated bucket** - Uses `documents` bucket with subfolder. Dedicated `email_attachments` bucket recommended for stricter isolation.

4. **Large files may timeout** - Attachments near 50MB limit may slow down preview. Consider streaming for large files.

## Future Enhancements

1. **Backend URL signer** - `GET /documents/{id}/signed-url` with 10-minute TTL
2. **Link/Unlink endpoints** - `POST /v1/documents/link`, `POST /v1/documents/unlink`
3. **Dedicated storage bucket** - `email_attachments` with yacht-scoped RLS
4. **Attachment caching** - Cache frequently accessed attachments for faster re-opens
