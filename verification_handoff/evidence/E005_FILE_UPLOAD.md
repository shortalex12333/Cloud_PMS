# E005: FILE UPLOAD VULNERABILITIES

**Date:** 2026-01-20
**Phase:** 4 - File Upload & Input Sanitization
**Status:** CRITICAL VULNERABILITIES FOUND

---

## Summary

| Vulnerability | Severity | Location |
|---------------|----------|----------|
| No file type validation | 🔴 CRITICAL | email.py:1296 |
| No file size limits | 🔴 CRITICAL | email.py:1293 |
| Path traversal risk | 🔴 CRITICAL | email.py:1298 |
| User-provided filename | 🟠 HIGH | email.py:1296 |
| No virus scanning | 🟠 HIGH | All uploads |
| Generic upload no validation | 🔴 CRITICAL | supabase.py:475 |

---

## 🔴 CRITICAL: No File Type Validation

### Location
**File:** `apps/api/routes/email.py`
**Lines:** 1296-1304

### Code
```python
filename = attachment.get('name', 'attachment')           # Line 1296 - NO VALIDATION
content_type = attachment.get('contentType', 'application/octet-stream')  # Line 1297 - NO VALIDATION
folder = request.target_folder or 'email-attachments'    # Line 1298 - NO VALIDATION
storage_path = f"{yacht_id}/{folder}/{uuid.uuid4()}-{filename}"  # Line 1299

supabase.storage.from_('documents').upload(              # Line 1302
    storage_path, file_data,
    {'content-type': content_type}
)
```

### Attack Scenario
An attacker can upload:
- `.exe` executables
- `.php` server-side scripts
- `.js` JavaScript files
- `.sh` shell scripts
- `.bat` batch files
- Any malicious file type

### Proof of Vulnerability
```bash
# Attacker sends email with malicious attachment
# No validation prevents upload

# Attachment properties:
# - name: "malware.exe"
# - contentType: "application/octet-stream"
# - contentBytes: <base64 encoded executable>

# Result: File uploaded to documents bucket with no checks
```

---

## 🔴 CRITICAL: No File Size Limits

### Location
**File:** `apps/api/routes/email.py`
**Line:** 1293

### Code
```python
file_data = base64.b64decode(content_bytes)  # Entire file loaded into memory
# No size check before or after decode
# No limit on file_data length
```

### Attack Scenario
1. Attacker sends email with 1GB attachment
2. Server loads entire file into memory
3. Memory exhaustion / denial of service

---

## 🔴 CRITICAL: Path Traversal Risk

### Location
**File:** `apps/api/routes/email.py`
**Line:** 1298-1299

### Code
```python
folder = request.target_folder or 'email-attachments'  # User-provided
storage_path = f"{yacht_id}/{folder}/{uuid.uuid4()}-{filename}"
```

### Attack Scenario
```python
# Attacker provides:
request.target_folder = "../../../other-bucket"
filename = "../../../etc/passwd"

# Resulting path:
storage_path = "yacht_id/../../../other-bucket/uuid-../../../etc/passwd"
```

**Note:** While Supabase Storage may sanitize paths, relying on external service for security is a defense-in-depth failure.

---

## 🔴 CRITICAL: Generic Upload Function

### Location
**File:** `apps/api/integrations/supabase.py`
**Lines:** 462-484

### Code
```python
async def upload_to_storage(
    bucket: str,
    path: str,          # No validation
    file_data: bytes,   # No size check
    content_type: str = 'application/octet-stream'  # No validation
) -> str:
    supabase = get_supabase_client()
    supabase.storage.from_(bucket).upload(
        path,
        file_data,
        {'content-type': content_type, 'upsert': 'false'}
    )
    return path
```

### Impact
This is a pass-through function that:
- Accepts ANY bucket
- Accepts ANY path
- Accepts ANY data (no size limit)
- Accepts ANY content-type
- Provides zero validation

---

## Required Fixes

### Fix 1: Add File Type Whitelist
```python
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# Validate extension
import os
ext = os.path.splitext(filename)[1].lower()
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

# Validate MIME type
if content_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(status_code=400, detail=f"Content type {content_type} not allowed")
```

### Fix 2: Add File Size Limit
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

file_data = base64.b64decode(content_bytes)
if len(file_data) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_SIZE} bytes")
```

### Fix 3: Sanitize Path
```python
import os
import re

# Remove path traversal
folder = os.path.basename(folder)  # Strip directory components
filename = os.path.basename(filename)  # Strip directory components

# Validate characters
if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
    raise HTTPException(status_code=400, detail="Invalid filename characters")

# Use UUID only for storage path
storage_path = f"{yacht_id}/email-attachments/{uuid.uuid4()}"
```

### Fix 4: Add Virus Scanning
```python
import clamd

def scan_file(file_data: bytes) -> bool:
    """Returns True if file is clean."""
    cd = clamd.ClamdUnixSocket()
    result = cd.instream(io.BytesIO(file_data))
    return result['stream'][0] == 'OK'

if not scan_file(file_data):
    raise HTTPException(status_code=400, detail="File failed security scan")
```

---

## Test Commands

### Test 1: Upload Executable
```bash
# Create base64 encoded "executable"
echo -n "MZ..." | base64 > payload.txt

# Attempt upload via email attachment save
curl -X POST "https://pipeline-core.int.celeste7.ai/email/evidence/save-attachment" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "...",
    "attachment_id": "...",
    "target_folder": "../../../"
  }'

# Expected with bug: 200 OK, file uploaded
# Expected fixed: 400 Bad Request, file type not allowed
```

---

## Affected Files

1. `apps/api/routes/email.py` - Lines 1293-1305
2. `apps/api/integrations/supabase.py` - Lines 462-484

---

**Evidence File:** E005_FILE_UPLOAD.md
**Created:** 2026-01-20
**Auditor:** Claude B
