"""
CelesteOS API - Evidence Export Tests
=====================================

Tests for audit evidence export service.

Tests:
1. Export creates bundle.zip with all required files
2. Redaction removes raw payloads
3. index.json includes metadata
4. Summary CSV has correct counts
"""

import pytest
import json
import zipfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_client():
    """Mock database client with sample data."""
    client = MagicMock()

    # Mock memberships query
    client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
        {
            "id": "mem-001",
            "user_id": "user-001",
            "yacht_id": "yacht-001",
            "status": "ACTIVE",
            "role_requested": "captain",
            "invited_by": "admin-001",
            "approved_by": "admin-002",
            "notes": "Test membership",
            "created_at": "2026-01-15T10:00:00Z",
        },
        {
            "id": "mem-002",
            "user_id": "user-002",
            "yacht_id": "yacht-001",
            "status": "REVOKED",
            "role_requested": "crew",
            "invited_by": "admin-001",
            "approved_by": "admin-001",
            "notes": None,
            "created_at": "2026-01-10T10:00:00Z",
        },
    ])

    # Mock security_events query
    client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
        {
            "id": "evt-001",
            "event_type": "admin_approve_success",
            "user_id": "user-001",
            "yacht_id": "yacht-001",
            "details": {
                "actor_id": "admin-002",
                "inviter_id": "admin-001",
                "approver_id": "admin-002",
            },
            "created_at": "2026-01-15T11:00:00Z",
        },
    ])

    # Mock pms_audit_log query
    client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
        {
            "id": "audit-001",
            "request_id": "req-001",
            "idempotency_key": "idem-001",
            "user_id": "user-001",
            "yacht_id": "yacht-001",
            "action_name": "update_fault",
            "outcome": "allowed",
            "entity_type": "fault",
            "entity_id": "fault-001",
            "payload_hash": "abc123",
            "created_at": "2026-01-15T12:00:00Z",
        },
    ])

    return client


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# EXPORT TESTS
# ============================================================================

class TestExportAuditTrace:
    """Test export_audit_trace function."""

    @pytest.mark.asyncio
    async def test_export_creates_bundle_zip(self, mock_db_client, temp_output_dir):
        """Test that export creates bundle.zip file."""
        from services.audit_export import export_audit_trace

        # Mock all queries to return empty to avoid complex chaining
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        bundle_path = await export_audit_trace(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
            out_dir=temp_output_dir,
        )

        assert Path(bundle_path).exists()
        assert bundle_path.endswith("bundle.zip")

    @pytest.mark.asyncio
    async def test_export_includes_required_artifacts(self, mock_db_client, temp_output_dir):
        """Test that export includes all required files."""
        from services.audit_export import export_audit_trace

        # Mock queries
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        bundle_path = await export_audit_trace(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
            out_dir=temp_output_dir,
        )

        # Check bundle contents
        with zipfile.ZipFile(bundle_path, "r") as zf:
            files = zf.namelist()

            required_files = [
                "index.json",
                "memberships.jsonl",
                "role_changes.jsonl",
                "admin_actions.jsonl",
                "router_audits.jsonl",
                "storage_signing.jsonl",
                "incident_events.jsonl",
                "cache_invalidations.jsonl",
                "summary.csv",
                "README.md",
            ]

            for required_file in required_files:
                assert required_file in files, f"Missing {required_file}"

    @pytest.mark.asyncio
    async def test_index_json_contains_metadata(self, mock_db_client, temp_output_dir):
        """Test that index.json contains required metadata."""
        from services.audit_export import export_audit_trace, EXPORTER_VERSION

        # Mock queries
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        await export_audit_trace(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
            out_dir=temp_output_dir,
            git_commit="abc123",
            command_args="--yacht-id yacht-001",
        )

        # Read index.json
        index_path = Path(temp_output_dir) / "index.json"
        with open(index_path) as f:
            index = json.load(f)

        assert index["exporter_version"] == EXPORTER_VERSION
        assert "export_timestamp" in index
        assert index["parameters"]["yacht_id"] == "yacht-001"
        assert index["parameters"]["start_ts"] == "2026-01-01T00:00:00Z"
        assert index["git_commit"] == "abc123"
        assert index["command_args"] == "--yacht-id yacht-001"
        assert index["timezone"] == "UTC"
        assert "record_counts" in index


# ============================================================================
# REDACTION TESTS
# ============================================================================

class TestRedaction:
    """Test redaction of sensitive data."""

    def test_redact_dict_removes_payload(self):
        """Test that raw_payload is removed."""
        from services.audit_export import _redact_dict

        data = {
            "id": "test-001",
            "raw_payload": {"secret": "data"},
            "payload_hash": "abc123",
        }

        result = _redact_dict(data)

        assert "id" in result
        assert "payload_hash" in result
        assert "raw_payload" not in result

    def test_redact_dict_hashes_email(self):
        """Test that email is hashed."""
        from services.audit_export import _redact_dict

        data = {
            "id": "test-001",
            "email": "user@example.com",
        }

        result = _redact_dict(data)

        assert "id" in result
        assert "email" not in result
        assert "email_hash" in result
        assert result["email_hash"] != "user@example.com"

    def test_redact_dict_removes_secrets(self):
        """Test that secret fields are removed."""
        from services.audit_export import _redact_dict

        data = {
            "id": "test-001",
            "password": "secret123",
            "api_key": "key123",
            "token": "tok123",
            "secret_data": "hidden",
        }

        result = _redact_dict(data)

        assert "id" in result
        assert "password" not in result
        assert "api_key" not in result
        assert "token" not in result
        assert "secret_data" not in result

    def test_redact_dict_handles_nested(self):
        """Test that nested dicts are redacted."""
        from services.audit_export import _redact_dict

        data = {
            "id": "test-001",
            "details": {
                "email": "user@example.com",
                "password": "secret",
                "safe_field": "value",
            },
        }

        result = _redact_dict(data)

        assert "details" in result
        assert "email" not in result["details"]
        assert "email_hash" in result["details"]
        assert "password" not in result["details"]
        assert result["details"]["safe_field"] == "value"

    @pytest.mark.asyncio
    async def test_export_no_raw_payloads_in_output(self, mock_db_client, temp_output_dir):
        """Test that exported files contain no raw payloads."""
        from services.audit_export import export_audit_trace

        # Mock with data containing payload
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "audit-001",
                "raw_payload": {"secret": "should_not_appear"},
                "payload_hash": "abc123",
                "email": "test@example.com",
            }
        ])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        await export_audit_trace(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
            out_dir=temp_output_dir,
        )

        # Read all jsonl files and check for payload
        out_path = Path(temp_output_dir)
        for jsonl_file in out_path.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        assert "raw_payload" not in str(record), f"raw_payload found in {jsonl_file.name}"
                        assert "should_not_appear" not in str(record), f"secret data found in {jsonl_file.name}"


# ============================================================================
# ACCESS REVIEW DATA TESTS
# ============================================================================

class TestAccessReviewData:
    """Test access review data generation."""

    @pytest.mark.asyncio
    async def test_generate_access_review_data(self, mock_db_client):
        """Test generating access review data."""
        from services.audit_export import generate_access_review_data

        # Mock queries
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "mem-001",
                "user_id": "user-001",
                "yacht_id": "yacht-001",
                "status": "ACTIVE",
                "role_requested": "captain",
                "invited_by": "admin-001",
                "approved_by": "admin-002",
            },
        ])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        assert result["yacht_id"] == "yacht-001"
        assert "active_memberships" in result
        assert "privileged_roles" in result
        assert "two_person_compliance" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_two_person_compliance_check(self, mock_db_client):
        """Test 2-person compliance checking."""
        from services.audit_export import generate_access_review_data

        # Mock with privileged role where inviter != approver (compliant)
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "mem-001",
                "user_id": "user-001",
                "yacht_id": "yacht-001",
                "status": "ACTIVE",
                "role_requested": "captain",
                "invited_by": "admin-001",
                "approved_by": "admin-002",  # Different person
            },
            {
                "id": "mem-002",
                "user_id": "user-002",
                "yacht_id": "yacht-001",
                "status": "ACTIVE",
                "role_requested": "manager",
                "invited_by": "admin-001",
                "approved_by": "admin-001",  # Same person - violation!
            },
        ])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        # Should have 1 violation (admin-001 both invited and approved mem-002)
        assert result["summary"]["two_person_violations"] == 1

        # Check individual compliance
        compliance = result["two_person_compliance"]
        captain_entry = next(c for c in compliance if c["role"] == "captain")
        manager_entry = next(c for c in compliance if c["role"] == "manager")

        assert captain_entry["compliant"] is True
        assert manager_entry["compliant"] is False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
