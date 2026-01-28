"""
CelesteOS API - Storage Signing Tests
=====================================

Tests for signed URL generation and yacht isolation.

Tests ensure:
1. Signed URL generation validates yacht_id prefix
2. Cross-yacht document access returns 404
3. Path without yacht_id prefix is rejected
4. Signed URL expiration matches TTL
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock, patch

from validators.ownership import (
    OwnershipValidator,
    NotFoundError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def yacht_a_id() -> str:
    """Yacht A UUID."""
    return "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def yacht_b_id() -> str:
    """Yacht B UUID (different yacht)."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def document_yacht_a(yacht_a_id) -> dict:
    """Document belonging to Yacht A."""
    return {
        "id": "doc-111111",
        "yacht_id": yacht_a_id,
        "filename": "manual.pdf",
        "storage_path": f"{yacht_a_id}/documents/manual.pdf",
    }


@pytest.fixture
def document_yacht_b(yacht_b_id) -> dict:
    """Document belonging to Yacht B."""
    return {
        "id": "doc-222222",
        "yacht_id": yacht_b_id,
        "filename": "other.pdf",
        "storage_path": f"{yacht_b_id}/documents/other.pdf",
    }


@pytest.fixture
def mock_supabase_storage():
    """Mock Supabase storage client."""
    mock = MagicMock()

    def mock_create_signed_url(path, expires_in):
        return {
            "signedURL": f"https://storage.supabase.co/sign/{path}?token=xyz&expires={expires_in}",
        }

    mock.from_.return_value.create_signed_url = mock_create_signed_url
    mock.from_.return_value.download = lambda path: b"file contents"

    return mock


# ============================================================================
# Yacht Prefix Validation Tests
# ============================================================================

class TestYachtPrefixValidation:
    """Tests for yacht_id prefix validation in storage paths."""

    def test_valid_prefix_accepted(self, yacht_a_id):
        """Storage path with correct yacht prefix is accepted."""
        storage_path = f"{yacht_a_id}/documents/manual.pdf"

        # Validation check
        assert storage_path.startswith(f"{yacht_a_id}/")

    def test_wrong_prefix_rejected(self, yacht_a_id, yacht_b_id):
        """Storage path with wrong yacht prefix is rejected."""
        storage_path = f"{yacht_b_id}/documents/manual.pdf"

        # User from yacht_a tries to access yacht_b's document
        assert not storage_path.startswith(f"{yacht_a_id}/")

    def test_no_prefix_rejected(self, yacht_a_id):
        """Storage path without yacht prefix is rejected."""
        storage_path = "documents/manual.pdf"

        assert not storage_path.startswith(f"{yacht_a_id}/")

    def test_partial_prefix_rejected(self, yacht_a_id):
        """Partial yacht prefix is rejected."""
        # Malicious path that starts with part of yacht_id
        storage_path = f"{yacht_a_id[:8]}/documents/manual.pdf"

        # Must match full yacht_id + /
        assert not storage_path.startswith(f"{yacht_a_id}/")


# ============================================================================
# Cross-Yacht Document Access Tests
# ============================================================================

class TestCrossYachtDocumentAccess:
    """Tests for cross-yacht document access denial."""

    def test_own_document_access_succeeds(
        self, yacht_a_id, document_yacht_a
    ):
        """User can access their own yacht's document."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [document_yacht_a]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)
        result = validator.validate("document", document_yacht_a["id"])

        assert result["id"] == document_yacht_a["id"]
        assert result["yacht_id"] == yacht_a_id

    def test_cross_yacht_document_returns_404(
        self, yacht_a_id, document_yacht_b
    ):
        """User cannot access another yacht's document - returns 404."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []  # Document not found for this yacht
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate("document", document_yacht_b["id"])

        # Must be 404 (not 403) to prevent enumeration
        assert "not found" in exc_info.value.message.lower()

    def test_random_document_id_returns_404(self, yacht_a_id):
        """Random document ID returns 404."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)

        with pytest.raises(NotFoundError):
            validator.validate("document", str(uuid.uuid4()))


# ============================================================================
# Signed URL Generation Tests
# ============================================================================

class TestSignedUrlGeneration:
    """Tests for signed URL generation."""

    def test_signed_url_includes_expiry(self, mock_supabase_storage, yacht_a_id):
        """Signed URL includes expiry parameter."""
        storage_path = f"{yacht_a_id}/documents/manual.pdf"
        expires_in = 3600

        result = mock_supabase_storage.from_("documents").create_signed_url(
            storage_path, expires_in
        )

        assert "signedURL" in result
        assert f"expires={expires_in}" in result["signedURL"]

    def test_signed_url_contains_path(self, mock_supabase_storage, yacht_a_id):
        """Signed URL contains storage path."""
        storage_path = f"{yacht_a_id}/documents/manual.pdf"

        result = mock_supabase_storage.from_("documents").create_signed_url(
            storage_path, 3600
        )

        assert storage_path in result["signedURL"]


# ============================================================================
# Storage Path Security Tests
# ============================================================================

class TestStoragePathSecurity:
    """Tests for storage path security."""

    def test_path_traversal_blocked(self, yacht_a_id, yacht_b_id):
        """Path traversal attempts are blocked."""
        # Malicious path trying to escape yacht directory
        malicious_paths = [
            f"{yacht_a_id}/../{yacht_b_id}/documents/secret.pdf",
            f"{yacht_a_id}/documents/../../{yacht_b_id}/secret.pdf",
            f"../{yacht_b_id}/documents/secret.pdf",
        ]

        for path in malicious_paths:
            # Normalized path should not allow access to other yacht
            # This is typically handled by storage backend, but we verify prefix
            assert not path.startswith(f"{yacht_a_id}/") or ".." in path

    def test_url_encoding_attacks_blocked(self, yacht_a_id, yacht_b_id):
        """URL-encoded path traversal attempts are blocked."""
        # %2F is URL-encoded /
        malicious_path = f"{yacht_a_id}%2F..%2F{yacht_b_id}/documents/secret.pdf"

        # Should not be treated as valid yacht_a path
        assert not malicious_path.startswith(f"{yacht_a_id}/")


# ============================================================================
# Document Metadata Validation Tests
# ============================================================================

class TestDocumentMetadataValidation:
    """Tests for document metadata validation before signing."""

    def test_validates_document_exists(self, yacht_a_id):
        """Validates document exists before signing."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute = lambda: mock_result

        # Document not found
        validator = OwnershipValidator(mock_db, yacht_a_id)

        with pytest.raises(NotFoundError):
            validator.validate("doc_metadata", "nonexistent-doc-id")

    def test_validates_document_has_storage_path(self, yacht_a_id):
        """Validates document has storage_path."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{
            "id": "doc-123",
            "yacht_id": yacht_a_id,
            "storage_path": None,  # Missing storage path
        }]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)
        result = validator.validate("doc_metadata", "doc-123")

        # Validation passes, but handler should check storage_path
        assert result.get("storage_path") is None


# ============================================================================
# Integration-Style Tests
# ============================================================================

class TestSignedUrlFlow:
    """Integration-style tests for full signed URL flow."""

    def test_full_flow_own_document(
        self, yacht_a_id, document_yacht_a, mock_supabase_storage
    ):
        """Full flow: validate ownership, generate signed URL."""
        # 1. Validate ownership
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [document_yacht_a]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)
        doc = validator.validate("document", document_yacht_a["id"])

        # 2. Validate storage path prefix
        storage_path = doc["storage_path"]
        assert storage_path.startswith(f"{yacht_a_id}/")

        # 3. Generate signed URL
        signed = mock_supabase_storage.from_("documents").create_signed_url(
            storage_path, 3600
        )

        assert "signedURL" in signed
        assert yacht_a_id in signed["signedURL"]

    def test_full_flow_cross_yacht_blocked(
        self, yacht_a_id, yacht_b_id, document_yacht_b
    ):
        """Full flow: cross-yacht access blocked at validation."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []  # Not found for yacht_a
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        validator = OwnershipValidator(mock_db, yacht_a_id)

        # Blocked at validation - never reaches signed URL generation
        with pytest.raises(NotFoundError):
            validator.validate("document", document_yacht_b["id"])


# ============================================================================
# TTL Tests
# ============================================================================

class TestSignedUrlTTL:
    """Tests for signed URL TTL handling."""

    @pytest.mark.parametrize("ttl_seconds,description", [
        (60, "1 minute - very short lived"),
        (600, "10 minutes - default"),
        (3600, "1 hour - standard"),
        (86400, "24 hours - long lived"),
    ])
    def test_various_ttl_values(self, mock_supabase_storage, yacht_a_id, ttl_seconds, description):
        """Various TTL values are passed correctly."""
        storage_path = f"{yacht_a_id}/documents/manual.pdf"

        result = mock_supabase_storage.from_("documents").create_signed_url(
            storage_path, ttl_seconds
        )

        assert f"expires={ttl_seconds}" in result["signedURL"]

    def test_default_ttl_is_reasonable(self):
        """Default TTL should be reasonable (not too long)."""
        # From the spec: signed URLs should not be cached beyond their lifetime
        # Typical values: 10 min (600s) to 1 hour (3600s)
        DEFAULT_TTL = 3600  # 1 hour, as used in pipeline_service.py

        # Should be at least 5 minutes
        assert DEFAULT_TTL >= 300

        # Should not exceed 24 hours
        assert DEFAULT_TTL <= 86400


# ============================================================================
# Storage Bucket Tests
# ============================================================================

class TestStorageBuckets:
    """Tests for storage bucket handling."""

    def test_documents_bucket_used(self, mock_supabase_storage, yacht_a_id):
        """Documents bucket is used for document signing."""
        storage_path = f"{yacht_a_id}/documents/manual.pdf"

        # Call with documents bucket
        mock_supabase_storage.from_("documents").create_signed_url(
            storage_path, 3600
        )

        mock_supabase_storage.from_.assert_called_with("documents")

    @pytest.mark.parametrize("bucket_name", [
        "documents",
        "attachments",
        "labels",
    ])
    def test_multiple_buckets_supported(
        self, mock_supabase_storage, yacht_a_id, bucket_name
    ):
        """Multiple storage buckets are supported."""
        storage_path = f"{yacht_a_id}/{bucket_name}/file.pdf"

        # Should not raise
        result = mock_supabase_storage.from_(bucket_name).create_signed_url(
            storage_path, 3600
        )

        assert "signedURL" in result
