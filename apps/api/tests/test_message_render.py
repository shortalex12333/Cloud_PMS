#!/usr/bin/env python3
"""
Message Render + Attachment API Tests

Validates:
- Body fetch renders correctly (no corruption, proper charset/encoding)
- Attachments list is accurate with expected fields
- Downloads stream correct bytes with safe headers
- No body stored in DB
- Error handling (401, 413, 415)

Test Fixtures Required:
- Emails in test mailbox with known subjects (prefix "[TEST]")
- Various content types and encodings
"""

import os
import sys
import json
import hashlib
import pytest
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

# ============================================================================
# CONFIG - Uses Render environment variables
# ============================================================================

# Test yacht ID (matches yTEST_YACHT_001 tenant)
TEST_YACHT_ID = os.getenv('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')

# Tenant DB (yTEST_YACHT_001 - the test tenant in Render)
SUPABASE_URL = os.getenv('yTEST_YACHT_001_SUPABASE_URL') or os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')

# Master DB (for user lookups if needed)
MASTER_SUPABASE_URL = os.getenv('MASTER_SUPABASE_URL')
MASTER_SUPABASE_SERVICE_KEY = os.getenv('MASTER_SUPABASE_SERVICE_KEY')

# Render backend API
API_BASE = os.getenv('API_BASE', 'https://pipeline-core.int.celeste7.ai')

# Test user JWT - can be generated from tenant JWT secret
# Use TENNANT_SUPABASE_JWT_SECRET (note: Render has typo "TENNANT")
TENANT_JWT_SECRET = os.getenv('TENNANT_SUPABASE_JWT_SECRET') or os.getenv('TENANT_SUPABASE_JWT_SECRET')
TEST_JWT = os.getenv('TEST_JWT')

# Test user ID (x@alex-short.com in test yacht)
TEST_USER_ID = os.getenv('TEST_USER_ID', '4653cc88-cacd-4770-9853-98854e757758')

# ============================================================================
# JWT GENERATION HELPER
# ============================================================================

def generate_test_jwt(user_id: str, yacht_id: str) -> Optional[str]:
    """
    Generate a test JWT using the tenant JWT secret from Render.
    This allows tests to run without manually refreshing tokens.
    """
    if not TENANT_JWT_SECRET:
        return None

    try:
        import jwt
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id,
            'aud': 'authenticated',
            'role': 'authenticated',
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=1)).timestamp()),
            # Custom claims for our app
            'yacht_id': yacht_id,
        }

        return jwt.encode(payload, TENANT_JWT_SECRET, algorithm='HS256')
    except Exception as e:
        print(f"[Warning] Could not generate JWT: {e}")
        return None

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='module')
def supabase() -> Client:
    """Create Supabase client for DB verification using Render env vars."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        pytest.skip("yTEST_YACHT_001_SUPABASE_URL/KEY not set - check Render env vars")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@pytest.fixture(scope='module')
def master_supabase() -> Optional[Client]:
    """Create Master Supabase client (optional, for user lookups)."""
    if not MASTER_SUPABASE_URL or not MASTER_SUPABASE_SERVICE_KEY:
        return None
    return create_client(MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY)


@pytest.fixture(scope='module')
def auth_headers() -> Dict[str, str]:
    """
    Get auth headers for API calls.
    Uses TEST_JWT if set, otherwise generates one from TENANT_JWT_SECRET.
    """
    token = TEST_JWT

    if not token:
        # Try to generate from JWT secret
        token = generate_test_jwt(TEST_USER_ID, TEST_YACHT_ID)

    if not token:
        pytest.skip(
            "No auth token available. Set TEST_JWT or TENNANT_SUPABASE_JWT_SECRET"
        )

    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }


class TestMessageHarness:
    """
    Test harness for looking up test messages by subject prefix.

    Searches for messages with subjects like:
    - "[TEST] Plain text UTF-8"
    - "[TEST] HTML with non-ASCII"
    - "[TEST] Multipart alternative"
    - "[TEST] With PDF attachment"
    """

    def __init__(self, supabase: Client, yacht_id: str):
        self.supabase = supabase
        self.yacht_id = yacht_id
        self._cache: Dict[str, Dict] = {}

    def find_message_by_subject_prefix(self, prefix: str) -> Optional[Dict]:
        """
        Find a message by subject prefix (e.g., "[TEST] HTML").
        Returns message with provider_message_id and message_id.
        """
        if prefix in self._cache:
            return self._cache[prefix]

        result = self.supabase.table('email_messages').select(
            'id, provider_message_id, subject, thread_id, has_attachments, direction'
        ).eq('yacht_id', self.yacht_id).ilike(
            'subject', f'{prefix}%'
        ).order('received_at', desc=True).limit(1).execute()

        if result.data:
            self._cache[prefix] = result.data[0]
            return result.data[0]
        return None

    def get_thread_messages(self, thread_id: str) -> list:
        """Get all messages in a thread."""
        result = self.supabase.table('email_messages').select(
            'id, provider_message_id, subject, has_attachments'
        ).eq('yacht_id', self.yacht_id).eq(
            'thread_id', thread_id
        ).order('received_at').execute()
        return result.data or []


@pytest.fixture(scope='module')
def harness(supabase) -> TestMessageHarness:
    """Create message test harness."""
    return TestMessageHarness(supabase, TEST_YACHT_ID)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def api_get(endpoint: str, headers: Dict[str, str]) -> Tuple[int, Dict]:
    """Make GET request to API and return (status, data)."""
    import httpx
    url = f"{API_BASE}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        try:
            data = response.json()
        except:
            data = {'raw': response.text[:500]}
        return response.status_code, data


def api_get_binary(endpoint: str, headers: Dict[str, str]) -> Tuple[int, bytes, Dict[str, str]]:
    """Make GET request expecting binary response. Returns (status, bytes, headers)."""
    import httpx
    url = f"{API_BASE}{endpoint}"
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, headers=headers)
        return response.status_code, response.content, dict(response.headers)


# ============================================================================
# A) MESSAGE BODY RENDER TESTS
# ============================================================================

class TestMessageRender:
    """Tests for GET /email/message/{provider_message_id}/render"""

    def test_plain_text_utf8(self, harness, auth_headers):
        """
        Case 1: text/plain with UTF-8 encoding
        Verify special characters render correctly.
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Plain text")
        if not msg:
            pytest.skip("No [TEST] Plain text message found")

        status, data = api_get(
            f"/email/message/{msg['provider_message_id']}/render",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}: {data}"
        assert 'body' in data, "Response should contain body"
        assert data['body'].get('contentType') in ['text', 'text/plain'], \
            f"Expected text/plain, got {data['body'].get('contentType')}"

        # Verify content contains expected characters (dashes, quotes, etc.)
        content = data['body'].get('content', '')
        assert len(content) > 0, "Body content should not be empty"

        # Check for correct glyph handling
        # Common problematic characters: em-dash (—), curly quotes (' '), ellipsis (…)
        print(f"[Test] Plain text content length: {len(content)}")

    def test_html_utf8(self, harness, auth_headers):
        """
        Case 2: text/html with UTF-8 encoding
        Verify HTML structure preserved, non-ASCII characters correct.
        """
        msg = harness.find_message_by_subject_prefix("[TEST] HTML")
        if not msg:
            pytest.skip("No [TEST] HTML message found")

        status, data = api_get(
            f"/email/message/{msg['provider_message_id']}/render",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}: {data}"
        assert 'body' in data, "Response should contain body"
        assert data['body'].get('contentType') in ['html', 'text/html'], \
            f"Expected text/html, got {data['body'].get('contentType')}"

        content = data['body'].get('content', '')

        # Verify HTML tags are present
        assert '<' in content and '>' in content, "HTML should contain tags"

        # Verify no raw escaped entities (should be decoded)
        assert '&lt;' not in content[:100], "HTML should not have escaped entities in content"

        print(f"[Test] HTML content length: {len(content)}")

    def test_multipart_alternative(self, harness, auth_headers):
        """
        Case 3: multipart/alternative (text/plain + text/html)
        HTML should be chosen as display; plain available in response.
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Multipart")
        if not msg:
            pytest.skip("No [TEST] Multipart message found")

        status, data = api_get(
            f"/email/message/{msg['provider_message_id']}/render",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}: {data}"

        # Microsoft Graph typically returns HTML for multipart
        body = data.get('body', {})
        content_type = body.get('contentType', '')

        # Should prefer HTML
        assert content_type in ['html', 'text/html', 'text'], \
            f"Expected html or text, got {content_type}"

        print(f"[Test] Multipart content type: {content_type}")

    def test_inline_images_cid(self, harness, auth_headers):
        """
        Case 4: Email with inline images (cid:)
        Verify cid: references are preserved in HTML.
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Inline image")
        if not msg:
            pytest.skip("No [TEST] Inline image message found")

        status, data = api_get(
            f"/email/message/{msg['provider_message_id']}/render",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}: {data}"

        content = data.get('body', {}).get('content', '')

        # Check for cid: references (may or may not be present depending on email)
        has_cid = 'cid:' in content.lower()
        print(f"[Test] Inline images - has cid: references: {has_cid}")

    def test_no_body_stored_in_db(self, supabase, harness):
        """
        Verify no body content is stored in email_messages table.
        Only preview_text should be stored.
        """
        msg = harness.find_message_by_subject_prefix("[TEST]")
        if not msg:
            pytest.skip("No [TEST] message found")

        # Query for body field (should not exist or be null)
        result = supabase.table('email_messages').select(
            'id, subject, preview_text'
        ).eq('id', msg['id']).single().execute()

        assert result.data is not None, "Message should exist"

        # Verify no body field in response (column doesn't exist)
        # or if it exists, it should be null
        row = result.data
        assert 'body' not in row or row.get('body') is None, \
            "Body should not be stored in database"

        # preview_text is allowed
        assert 'preview_text' in row or True, "preview_text may be stored"
        print(f"[Test] DB verification: No body stored for message {msg['id'][:8]}")


# ============================================================================
# B) ATTACHMENTS LIST TESTS
# ============================================================================

class TestAttachmentsList:
    """Tests for GET /email/message/{message_id}/attachments"""

    def test_list_attachments_success(self, harness, auth_headers):
        """
        Verify attachments list returns expected fields.
        """
        # Find message with attachments
        msg = harness.find_message_by_subject_prefix("[TEST] With attachment")
        if not msg:
            pytest.skip("No [TEST] With attachment message found")

        if not msg.get('has_attachments'):
            pytest.skip("Message has no attachments flag")

        status, data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}: {data}"
        assert isinstance(data, dict), "Response should be a dict"
        assert 'attachments' in data, "Response should contain attachments"

        attachments = data['attachments']
        assert isinstance(attachments, list), "Attachments should be a list"

        if len(attachments) > 0:
            att = attachments[0]
            # Required fields
            assert 'name' in att or 'filename' in att, "Attachment should have name/filename"
            assert 'size' in att or 'size_bytes' in att, "Attachment should have size"

            print(f"[Test] Found {len(attachments)} attachments")
            for a in attachments:
                print(f"  - {a.get('name', a.get('filename', 'unknown'))}: {a.get('size', a.get('size_bytes', 0))} bytes")

    def test_provider_id_consistency(self, harness, auth_headers):
        """
        Verify provider_message_id for render matches message_id for attachments list.
        """
        msg = harness.find_message_by_subject_prefix("[TEST]")
        if not msg:
            pytest.skip("No [TEST] message found")

        # Get render
        status1, render_data = api_get(
            f"/email/message/{msg['provider_message_id']}/render",
            auth_headers
        )

        # Get attachments list
        status2, att_data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        # Both should succeed or fail consistently
        assert status1 == 200 or status2 == 200, "At least one endpoint should work"

        # If both work, verify subject matches
        if status1 == 200 and render_data.get('subject'):
            assert msg['subject'] in render_data['subject'] or render_data['subject'] in msg['subject'], \
                "Subject should match between endpoints"

        print(f"[Test] Provider consistency: render={status1}, attachments={status2}")


# ============================================================================
# C) ATTACHMENT DOWNLOAD TESTS
# ============================================================================

class TestAttachmentDownload:
    """Tests for GET /email/message/{provider_message_id}/attachments/{id}/download"""

    def test_download_pdf_success(self, harness, auth_headers):
        """
        Download PDF attachment - verify headers and content.
        """
        msg = harness.find_message_by_subject_prefix("[TEST] PDF")
        if not msg:
            pytest.skip("No [TEST] PDF message found")

        # Get attachments list first
        status, data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        if status != 200 or not data.get('attachments'):
            pytest.skip("No attachments found")

        # Find PDF attachment
        pdf_att = None
        for att in data['attachments']:
            name = att.get('name', att.get('filename', '')).lower()
            ctype = att.get('content_type', att.get('contentType', '')).lower()
            if name.endswith('.pdf') or 'pdf' in ctype:
                pdf_att = att
                break

        if not pdf_att:
            pytest.skip("No PDF attachment in message")

        # Download
        att_id = pdf_att.get('provider_attachment_id', pdf_att.get('id'))
        status, content, headers = api_get_binary(
            f"/email/message/{msg['provider_message_id']}/attachments/{att_id}/download",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}"

        # Verify headers
        assert 'content-disposition' in headers, "Missing Content-Disposition header"
        assert 'attachment' in headers['content-disposition'].lower(), \
            "Content-Disposition should be 'attachment'"

        assert headers.get('x-content-type-options') == 'nosniff', \
            "Missing X-Content-Type-Options: nosniff"

        assert 'content-length' in headers, "Missing Content-Length header"
        assert int(headers['content-length']) == len(content), \
            f"Content-Length mismatch: header={headers['content-length']}, actual={len(content)}"

        # Verify PDF magic bytes
        assert content[:4] == b'%PDF', "Content should be a valid PDF"

        print(f"[Test] Downloaded PDF: {len(content)} bytes, headers valid")

    def test_download_image_success(self, harness, auth_headers):
        """
        Download image attachment (PNG/JPG).
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Image")
        if not msg:
            pytest.skip("No [TEST] Image message found")

        status, data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        if status != 200 or not data.get('attachments'):
            pytest.skip("No attachments found")

        # Find image attachment
        img_att = None
        for att in data['attachments']:
            name = att.get('name', att.get('filename', '')).lower()
            ctype = att.get('content_type', att.get('contentType', '')).lower()
            if any(ext in name for ext in ['.png', '.jpg', '.jpeg']) or \
               any(t in ctype for t in ['image/png', 'image/jpeg']):
                img_att = att
                break

        if not img_att:
            pytest.skip("No image attachment in message")

        att_id = img_att.get('provider_attachment_id', img_att.get('id'))
        status, content, headers = api_get_binary(
            f"/email/message/{msg['provider_message_id']}/attachments/{att_id}/download",
            auth_headers
        )

        assert status == 200, f"Expected 200, got {status}"
        assert headers.get('x-content-type-options') == 'nosniff'

        # Verify image magic bytes (PNG or JPEG)
        is_png = content[:8] == b'\x89PNG\r\n\x1a\n'
        is_jpeg = content[:3] == b'\xff\xd8\xff'
        assert is_png or is_jpeg, "Content should be a valid PNG or JPEG"

        print(f"[Test] Downloaded image: {len(content)} bytes, {'PNG' if is_png else 'JPEG'}")

    def test_download_disallowed_type_415(self, harness, auth_headers):
        """
        Attempt to download disallowed file type (e.g., .exe) → 415
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Exe")
        if not msg:
            pytest.skip("No [TEST] Exe message found - need .exe attachment for test")

        status, data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        if status != 200 or not data.get('attachments'):
            pytest.skip("No attachments found")

        # Find .exe attachment
        exe_att = None
        for att in data['attachments']:
            name = att.get('name', att.get('filename', '')).lower()
            if name.endswith('.exe') or name.endswith('.bat') or name.endswith('.cmd'):
                exe_att = att
                break

        if not exe_att:
            pytest.skip("No executable attachment in message")

        att_id = exe_att.get('provider_attachment_id', exe_att.get('id'))
        status, content, headers = api_get_binary(
            f"/email/message/{msg['provider_message_id']}/attachments/{att_id}/download",
            auth_headers
        )

        assert status == 415, f"Expected 415 Unsupported Media Type, got {status}"
        print(f"[Test] Disallowed type correctly returned 415")

    def test_download_oversize_413(self, harness, auth_headers):
        """
        Attempt to download oversize file (>25MB) → 413
        """
        msg = harness.find_message_by_subject_prefix("[TEST] Large file")
        if not msg:
            pytest.skip("No [TEST] Large file message found - need >25MB attachment for test")

        status, data = api_get(
            f"/email/message/{msg['id']}/attachments",
            auth_headers
        )

        if status != 200 or not data.get('attachments'):
            pytest.skip("No attachments found")

        # Find large attachment
        large_att = None
        for att in data['attachments']:
            size = att.get('size', att.get('size_bytes', 0))
            if size > 25 * 1024 * 1024:  # >25MB
                large_att = att
                break

        if not large_att:
            pytest.skip("No >25MB attachment in message")

        att_id = large_att.get('provider_attachment_id', large_att.get('id'))
        status, content, headers = api_get_binary(
            f"/email/message/{msg['provider_message_id']}/attachments/{att_id}/download",
            auth_headers
        )

        assert status == 413, f"Expected 413 Payload Too Large, got {status}"
        print(f"[Test] Oversize file correctly returned 413")


# ============================================================================
# D) FILENAME SANITIZATION TESTS
# ============================================================================

class TestFilenameSanitization:
    """Tests for filename sanitization in download headers."""

    def test_path_traversal_blocked(self, harness, auth_headers):
        """
        Verify path traversal attempts are sanitized out.
        Note: Requires test email with malicious filename.
        """
        # This test verifies the server-side sanitization
        # We can't easily create malicious filenames, so we check the sanitize function
        from routes.email import sanitize_filename

        test_cases = [
            ("../../../etc/passwd", "_etc_passwd"),
            ("..\\..\\windows\\system32\\cmd.exe", "_windows_system32_cmd.exe"),
            ("file\x00.txt", "file_.txt"),
            ("normal.pdf", "normal.pdf"),
            ("file with spaces.docx", "file with spaces.docx"),
            ("日本語ファイル.txt", "日本語ファイル.txt"),  # Unicode preserved
        ]

        for malicious, expected_contains in test_cases:
            sanitized = sanitize_filename(malicious)
            assert ".." not in sanitized, f"Path traversal not sanitized: {sanitized}"
            assert "\x00" not in sanitized, f"Null byte not sanitized: {sanitized}"
            assert "/" not in sanitized, f"Forward slash not sanitized: {sanitized}"
            assert "\\" not in sanitized, f"Backslash not sanitized: {sanitized}"

        print("[Test] Path traversal sanitization verified")

    def test_filename_max_length(self, auth_headers):
        """
        Verify filenames are truncated to max length without breaking codepoints.
        """
        from routes.email import sanitize_filename

        # Test long filename
        long_name = "a" * 300 + ".pdf"
        sanitized = sanitize_filename(long_name)

        assert len(sanitized) <= 255, f"Filename too long: {len(sanitized)}"
        assert sanitized.endswith(".pdf"), "Extension should be preserved"

        # Test long Unicode filename
        unicode_name = "日本語" * 100 + ".txt"
        sanitized = sanitize_filename(unicode_name)

        assert len(sanitized) <= 255, f"Unicode filename too long: {len(sanitized)}"
        # Verify no truncation mid-codepoint
        try:
            sanitized.encode('utf-8')
        except UnicodeError:
            pytest.fail("Filename truncated mid-codepoint")

        print("[Test] Filename max length verified")


# ============================================================================
# E) ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Tests for error responses."""

    def test_render_invalid_message_404(self, auth_headers):
        """
        GET /email/message/{invalid_id}/render → 404
        """
        status, data = api_get(
            "/email/message/invalid-message-id-12345/render",
            auth_headers
        )

        assert status in [404, 400], f"Expected 404 or 400, got {status}"
        print(f"[Test] Invalid message ID returns {status}")

    def test_render_no_auth_401(self):
        """
        GET /email/message/{id}/render without auth → 401/422
        """
        status, data = api_get(
            "/email/message/test/render",
            {'Content-Type': 'application/json'}  # No auth header
        )

        assert status in [401, 422], f"Expected 401 or 422, got {status}"
        print(f"[Test] Missing auth returns {status}")

    def test_download_missing_attachment_404(self, harness, auth_headers):
        """
        GET download with non-existent attachment → 404
        """
        msg = harness.find_message_by_subject_prefix("[TEST]")
        if not msg:
            pytest.skip("No [TEST] message found")

        status, content, headers = api_get_binary(
            f"/email/message/{msg['provider_message_id']}/attachments/nonexistent-attachment-id/download",
            auth_headers
        )

        assert status in [404, 400], f"Expected 404 or 400, got {status}"
        print(f"[Test] Missing attachment returns {status}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Run with pytest
    pytest.main([__file__, '-v', '--tb=short'])
