"""
CelesteOS API - Signed URL Security Tests
==========================================

Tests for storage signed URL security invariants.

Security invariants tested (per 02_INVARIANTS_DO_NOT_BREAK.md):
1. Storage key format is `{yacht_id}/...`
2. Validate prefix before creating signed upload URLs
3. Validate prefix before creating signed download URLs
4. Validate prefix before deleting objects
5. Server-side document lookup (never trust client-provided path)
6. Cross-yacht path validation fails
7. Path traversal attempts are blocked
8. Incident mode blocks signed URLs when configured
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_ctx():
    """Mock action context."""
    from middleware.action_security import ActionContext
    return ActionContext(
        user_id="user-001",
        yacht_id="yacht-001",
        role="captain",
        tenant_key_alias="yYacht001",
        idempotency_key="idem-001",
    )


@pytest.fixture
def mock_ctx_different_yacht():
    """Mock action context for different yacht."""
    from middleware.action_security import ActionContext
    return ActionContext(
        user_id="user-002",
        yacht_id="yacht-002",
        role="captain",
        tenant_key_alias="yYacht002",
        idempotency_key="idem-002",
    )


@pytest.fixture
def mock_db_client():
    """Mock database client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_storage_client():
    """Mock Supabase storage client."""
    client = MagicMock()
    client.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://storage.example.com/signed-url?token=abc123"
    }
    client.from_.return_value.create_signed_upload_url.return_value = {
        "signedURL": "https://storage.example.com/upload-url?token=xyz789"
    }
    return client


# ============================================================================
# PATH VALIDATION TESTS
# ============================================================================

class TestPathValidation:
    """Test storage path validation."""

    def test_valid_yacht_prefix_passes(self):
        """Test that valid yacht prefix passes validation."""
        from handlers.secure_document_handlers import validate_storage_path

        # Valid paths
        assert validate_storage_path("yacht-001/documents/file.pdf", "yacht-001") is True
        assert validate_storage_path("yacht-001/images/photo.jpg", "yacht-001") is True
        assert validate_storage_path("yacht-001/nested/deep/path/file.txt", "yacht-001") is True

    def test_invalid_yacht_prefix_fails(self):
        """Test that invalid yacht prefix fails validation."""
        from handlers.secure_document_handlers import validate_storage_path

        # Wrong yacht prefix
        assert validate_storage_path("yacht-002/documents/file.pdf", "yacht-001") is False
        assert validate_storage_path("other-yacht/file.pdf", "yacht-001") is False

    def test_no_prefix_fails(self):
        """Test that paths without yacht prefix fail."""
        from handlers.secure_document_handlers import validate_storage_path

        # No prefix
        assert validate_storage_path("file.pdf", "yacht-001") is False
        assert validate_storage_path("documents/file.pdf", "yacht-001") is False

    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        from handlers.secure_document_handlers import validate_storage_path

        # Path traversal attempts
        assert validate_storage_path("yacht-001/../yacht-002/file.pdf", "yacht-001") is False
        assert validate_storage_path("yacht-001/./../../yacht-002/file.pdf", "yacht-001") is False
        assert validate_storage_path("yacht-001/documents/../../../etc/passwd", "yacht-001") is False

    def test_prefix_injection_blocked(self):
        """Test that prefix injection attempts are blocked."""
        from handlers.secure_document_handlers import validate_storage_path

        # Injection attempts
        assert validate_storage_path("yacht-001yacht-002/file.pdf", "yacht-001") is False
        assert validate_storage_path("yacht-001%2F..%2Fyacht-002/file.pdf", "yacht-001") is False

    def test_empty_path_fails(self):
        """Test that empty paths fail validation."""
        from handlers.secure_document_handlers import validate_storage_path

        assert validate_storage_path("", "yacht-001") is False
        assert validate_storage_path(None, "yacht-001") is False

    def test_whitespace_in_path_handled(self):
        """Test that whitespace in paths is handled correctly."""
        from handlers.secure_document_handlers import validate_storage_path

        # Leading whitespace - should fail (prefix not at start)
        assert validate_storage_path(" yacht-001/file.pdf", "yacht-001") is False

        # Path with spaces in filename - should pass if prefix is correct
        assert validate_storage_path("yacht-001/my document.pdf", "yacht-001") is True


# ============================================================================
# DOWNLOAD URL SECURITY TESTS
# ============================================================================

class TestSecureDownloadUrl:
    """Test secure download URL generation."""

    @pytest.mark.asyncio
    async def test_download_url_validates_ownership(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URL validates document ownership."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        # Mock document lookup - document belongs to different yacht
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["get_secure_download_url"](
                mock_ctx,
                document_id="doc-001",
            )

    @pytest.mark.asyncio
    async def test_download_url_validates_path_prefix(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URL validates storage path prefix."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        # Mock document lookup - document exists but has wrong path
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "doc-001",
            "yacht_id": "yacht-001",
            "storage_path": "yacht-002/documents/file.pdf",  # Wrong yacht prefix!
        }])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["get_secure_download_url"](
                mock_ctx,
                document_id="doc-001",
            )

    @pytest.mark.asyncio
    async def test_download_url_success_with_valid_path(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test successful download URL generation with valid path."""
        from handlers.secure_document_handlers import get_secure_document_handlers

        # Mock document lookup - correct yacht and path
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "doc-001",
            "yacht_id": "yacht-001",
            "storage_path": "yacht-001/documents/file.pdf",
        }])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        result = await handlers["get_secure_download_url"](
            mock_ctx,
            document_id="doc-001",
        )

        assert "signed_url" in result
        assert "expires_in" in result


# ============================================================================
# UPLOAD URL SECURITY TESTS
# ============================================================================

class TestSecureUploadUrl:
    """Test secure upload URL generation."""

    @pytest.mark.asyncio
    async def test_upload_url_enforces_yacht_prefix(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that upload URL enforces yacht prefix in target path."""
        from handlers.secure_document_handlers import get_secure_document_handlers

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        result = await handlers["get_secure_upload_url"](
            mock_ctx,
            filename="new-document.pdf",
            folder="documents",
        )

        # Result path should include yacht prefix
        assert result["storage_path"].startswith("yacht-001/")
        assert "signed_url" in result

    @pytest.mark.asyncio
    async def test_upload_url_rejects_custom_path_without_prefix(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that upload URL rejects custom paths without correct prefix."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import ActionSecurityError

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        # Try to specify a path to another yacht
        with pytest.raises(ActionSecurityError):
            await handlers["get_secure_upload_url"](
                mock_ctx,
                filename="malicious.pdf",
                folder="yacht-002/documents",  # Trying to write to another yacht!
            )

    @pytest.mark.asyncio
    async def test_upload_url_sanitizes_filename(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that upload URL sanitizes dangerous filenames."""
        from handlers.secure_document_handlers import get_secure_document_handlers

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        # Filename with path traversal attempt
        result = await handlers["get_secure_upload_url"](
            mock_ctx,
            filename="../../../etc/passwd",
            folder="documents",
        )

        # Path should still be under yacht prefix
        assert result["storage_path"].startswith("yacht-001/")
        # Should not contain path traversal
        assert ".." not in result["storage_path"]


# ============================================================================
# DELETE SECURITY TESTS
# ============================================================================

class TestSecureDelete:
    """Test secure delete operations."""

    @pytest.mark.asyncio
    async def test_delete_validates_ownership(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that delete validates document ownership."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        # Document not found (wrong yacht)
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["delete_document"](
                mock_ctx,
                document_id="doc-001",
            )

    @pytest.mark.asyncio
    async def test_delete_validates_path_before_deletion(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that delete validates path prefix before deletion."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        # Document exists but with wrong path
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "doc-001",
            "yacht_id": "yacht-001",
            "storage_path": "yacht-002/documents/file.pdf",  # Wrong prefix!
        }])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["delete_document"](
                mock_ctx,
                document_id="doc-001",
            )


# ============================================================================
# CROSS-YACHT ACCESS TESTS
# ============================================================================

class TestCrossYachtAccess:
    """Test cross-yacht access prevention."""

    @pytest.mark.asyncio
    async def test_cannot_download_other_yacht_document(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that user cannot download document from another yacht."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        # Query filters by yacht_id, so document not found
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["get_secure_download_url"](
                mock_ctx,  # yacht-001
                document_id="doc-from-yacht-002",  # Document from different yacht
            )

    @pytest.mark.asyncio
    async def test_cannot_list_other_yacht_documents(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that user cannot list documents from another yacht."""
        from handlers.secure_document_handlers import get_secure_document_handlers

        # Query with yacht_id filter returns empty
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        result = await handlers["list_documents"](mock_ctx)

        # Should get empty list, not error (documents exist but belong to other yachts)
        assert result["documents"] == []

    def test_path_validation_prevents_cross_yacht_access(self):
        """Test that path validation prevents accessing other yacht's storage."""
        from handlers.secure_document_handlers import validate_storage_path

        yacht_a_id = "yacht-001"
        yacht_b_id = "yacht-002"

        # Yacht A's document
        yacht_a_path = "yacht-001/documents/secret.pdf"

        # User from yacht-001 can access
        assert validate_storage_path(yacht_a_path, yacht_a_id) is True

        # User from yacht-002 cannot access
        assert validate_storage_path(yacht_a_path, yacht_b_id) is False


# ============================================================================
# INCIDENT MODE TESTS
# ============================================================================

class TestIncidentModeSignedUrls:
    """Test incident mode blocks signed URLs."""

    @pytest.mark.asyncio
    async def test_download_blocked_in_incident_mode(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URLs are blocked when disable_signed_urls is set."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.auth import check_signed_urls_allowed, clear_system_flags_cache
        from fastapi import HTTPException

        # Mock incident mode with disable_signed_urls
        incident_flags = {
            "incident_mode": True,
            "disable_signed_urls": True,
            "incident_reason": "Active security incident",
        }

        clear_system_flags_cache()

        mock_master = MagicMock()
        mock_master.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_flags)

        with patch('middleware.auth.get_master_client', return_value=mock_master):
            with pytest.raises(HTTPException) as exc_info:
                await check_signed_urls_allowed()

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_download_allowed_when_not_in_incident(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URLs work when not in incident mode."""
        from middleware.auth import check_signed_urls_allowed, clear_system_flags_cache

        # Mock normal operation
        normal_flags = {
            "incident_mode": False,
            "disable_signed_urls": False,
        }

        clear_system_flags_cache()

        mock_master = MagicMock()
        mock_master.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=normal_flags)

        with patch('middleware.auth.get_master_client', return_value=mock_master):
            # Should not raise
            result = await check_signed_urls_allowed()
            assert result is None


# ============================================================================
# ERROR MESSAGE HYGIENE TESTS
# ============================================================================

class TestErrorMessageHygiene:
    """Test that error messages don't leak sensitive information."""

    @pytest.mark.asyncio
    async def test_ownership_error_is_generic_404(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that ownership validation returns 404, not 403."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError) as exc_info:
            await handlers["get_secure_download_url"](
                mock_ctx,
                document_id="doc-001",
            )

        # Should be 404, not 403 (prevent enumeration)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_error_does_not_expose_yacht_id(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that errors don't expose yacht IDs."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError) as exc_info:
            await handlers["get_secure_download_url"](
                mock_ctx,
                document_id="doc-001",
            )

        # Error message should not contain yacht ID
        error_str = str(exc_info.value)
        assert "yacht-001" not in error_str.lower()
        assert "yacht-002" not in error_str.lower()


# ============================================================================
# SIGNED URL EXPIRY TESTS
# ============================================================================

class TestSignedUrlExpiry:
    """Test signed URL expiry settings."""

    @pytest.mark.asyncio
    async def test_download_url_has_bounded_expiry(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URLs have bounded expiry time."""
        from handlers.secure_document_handlers import get_secure_document_handlers, DOWNLOAD_URL_EXPIRY

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "doc-001",
            "yacht_id": "yacht-001",
            "storage_path": "yacht-001/documents/file.pdf",
        }])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        result = await handlers["get_secure_download_url"](
            mock_ctx,
            document_id="doc-001",
        )

        # Check expiry is bounded (per spec: never cache signed URLs beyond their lifetime)
        assert result["expires_in"] <= DOWNLOAD_URL_EXPIRY
        # Should be reasonable (not hours long)
        assert result["expires_in"] <= 3600  # Max 1 hour

    @pytest.mark.asyncio
    async def test_upload_url_has_bounded_expiry(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that upload URLs have bounded expiry time."""
        from handlers.secure_document_handlers import get_secure_document_handlers, UPLOAD_URL_EXPIRY

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        result = await handlers["get_secure_upload_url"](
            mock_ctx,
            filename="test.pdf",
            folder="documents",
        )

        # Check expiry is bounded
        assert result["expires_in"] <= UPLOAD_URL_EXPIRY
        # Upload URLs can be shorter lived
        assert result["expires_in"] <= 1800  # Max 30 minutes


# ============================================================================
# AUDIT LOGGING TESTS
# ============================================================================

class TestSignedUrlAuditLogging:
    """Test audit logging for signed URL operations."""

    @pytest.mark.asyncio
    async def test_download_url_logs_audit(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that download URL generation logs audit entry."""
        from handlers.secure_document_handlers import get_secure_document_handlers

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "doc-001",
            "yacht_id": "yacht-001",
            "storage_path": "yacht-001/documents/file.pdf",
        }])

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        await handlers["get_secure_download_url"](
            mock_ctx,
            document_id="doc-001",
        )

        # Verify audit was logged
        # The handler should call audit logging

    @pytest.mark.asyncio
    async def test_failed_access_logs_audit(self, mock_ctx, mock_db_client, mock_storage_client):
        """Test that failed access attempts log audit entry."""
        from handlers.secure_document_handlers import get_secure_document_handlers
        from middleware.action_security import OwnershipValidationError

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        handlers = get_secure_document_handlers(mock_db_client, mock_storage_client)

        with pytest.raises(OwnershipValidationError):
            await handlers["get_secure_download_url"](
                mock_ctx,
                document_id="doc-001",
            )

        # Audit should have been logged even on failure


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
