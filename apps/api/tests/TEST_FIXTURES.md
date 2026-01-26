# Email Test Fixtures

This document describes the test email fixtures required to run the message render and attachment validation tests.

## Required Test Emails

Send these emails to the test mailbox (x@alex-short.com) with the specified subject prefixes:

### 1. Plain Text Email (UTF-8)
**Subject:** `[TEST] Plain text UTF-8 encoding`
**Content Type:** text/plain
**Encoding:** UTF-8

**Body content should include:**
- Em dash: —
- Curly quotes: "Hello" and 'World'
- Ellipsis: …
- Accented characters: café, naïve, résumé
- Currency symbols: €, £, ¥
- Non-Latin: 日本語, Привет

---

### 2. HTML Email (UTF-8)
**Subject:** `[TEST] HTML body with formatting`
**Content Type:** text/html
**Encoding:** UTF-8

**HTML should include:**
```html
<html>
<body>
  <h1>Test Heading</h1>
  <p>This is a <strong>bold</strong> and <em>italic</em> test.</p>
  <ul>
    <li>Item 1</li>
    <li>Item 2</li>
  </ul>
  <p>Non-ASCII: café, naïve, 日本語</p>
  <a href="https://example.com">External Link</a>
  <img src="https://example.com/image.png" alt="External Image" />
</body>
</html>
```

---

### 3. Multipart Alternative Email
**Subject:** `[TEST] Multipart alternative text+html`
**Content Type:** multipart/alternative

**Parts:**
- text/plain version with plain text
- text/html version with formatted HTML

---

### 4. Email with PDF Attachment
**Subject:** `[TEST] PDF attachment`
**Content Type:** multipart/mixed

**Attachments:**
- `test-document.pdf` (valid PDF, < 2MB)

---

### 5. Email with Image Attachment
**Subject:** `[TEST] Image attachment PNG`
**Content Type:** multipart/mixed

**Attachments:**
- `test-image.png` (valid PNG, < 2MB)

---

### 6. Email with Multiple Attachments
**Subject:** `[TEST] With attachment multiple types`
**Content Type:** multipart/mixed

**Attachments:**
- `document.pdf`
- `spreadsheet.xlsx`
- `image.jpg`

---

### 7. Email with Inline Images (CID)
**Subject:** `[TEST] Inline image CID reference`
**Content Type:** multipart/related

**HTML body should reference inline image:**
```html
<html>
<body>
  <p>Here is an inline image:</p>
  <img src="cid:image001.png@01D12345.67890ABC" />
</body>
</html>
```

**Attachment:**
- Inline image with Content-ID header matching the cid: reference

---

### 8. Email with Disallowed Attachment Type (for 415 test)
**Subject:** `[TEST] Exe attachment blocked`
**Content Type:** multipart/mixed

**Attachments:**
- `program.exe` or `script.bat` (for 415 test)

Note: This email may be blocked by email providers. Alternative: rename a .txt file to .exe.

---

### 9. Email with Large Attachment (for 413 test)
**Subject:** `[TEST] Large file over 25MB`
**Content Type:** multipart/mixed

**Attachments:**
- `large-file.zip` (> 25MB)

Note: This email may be hard to send via normal email. Consider using direct Outlook Graph API to create.

---

## Charset/Encoding Test Cases

### ISO-8859-1 Email
**Subject:** `[TEST] ISO-8859-1 encoding`
**Charset:** ISO-8859-1
**Body:** Characters that differ between ISO-8859-1 and UTF-8

### Windows-1252 Email
**Subject:** `[TEST] Windows-1252 encoding`
**Charset:** Windows-1252
**Body:** Smart quotes, em dash (characters 128-159 that differ from Latin-1)

### Quoted-Printable Encoding
**Subject:** `[TEST] Quoted-printable encoding`
**Transfer-Encoding:** quoted-printable
**Body:** Soft line breaks (=\r\n) and encoded characters (=E9 for é)

### Base64 Encoding
**Subject:** `[TEST] Base64 body encoding`
**Transfer-Encoding:** base64
**Body:** Base64-encoded content with non-ASCII characters

---

## Filename Edge Cases

### RFC 2231/5987 Filename
Create email with attachment having non-ASCII filename:
- `日本語ファイル.pdf`
- `Résumé Document.docx`

### Path Traversal Filename (Security Test)
Create email with attachment named:
- `../../../etc/passwd.txt`
- `..\\..\\windows\\system32\\config.txt`

Note: Most email systems sanitize these. May need direct Graph API manipulation.

---

## Creating Test Fixtures

### Option 1: Manual Email
Send emails from any email client to the test account with the specified subjects and content.

### Option 2: Graph API Script
Use Microsoft Graph API to create test emails programmatically:

```python
# Example: Create test email via Graph API
import httpx

async def create_test_email(access_token: str, subject: str, body_html: str):
    url = "https://graph.microsoft.com/v1.0/me/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_html
        },
        "toRecipients": [
            {"emailAddress": {"address": "test@example.com"}}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.json()
```

### Option 3: Import from .eml Files
Create .eml files with the required content and import them via Outlook.

---

## Verification

Run the test suite to verify fixtures are in place:

```bash
cd apps/api
python -m pytest tests/test_message_render.py -v --tb=short
```

The tests will skip missing fixtures with informative messages.

---

## Notes

1. **Test Subject Prefix:** All test emails MUST have subjects starting with `[TEST]` to be discoverable by the test harness.

2. **Yacht Isolation:** Test emails must be in the mailbox of a user associated with the test yacht (yacht_id: `85fe1119-b04c-41ac-80f1-829d23322598`).

3. **Token Refresh:** Before running tests, refresh the test JWT token:
   ```bash
   python scripts/refresh_test_token.py
   ```

4. **Cleanup:** Test emails can be cleaned up after testing. The tests are read-only and don't modify mailbox state.
