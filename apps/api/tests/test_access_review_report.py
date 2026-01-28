"""
CelesteOS API - Access Review Report Tests
==========================================

Tests for quarterly access review report generation.

Tests:
1. Report generation from audit data
2. Privileged roles require 2-person approval entries
3. Report summary includes correct counts
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_memberships_active():
    """Sample active memberships."""
    return [
        {
            "id": "mem-001",
            "user_id": "user-001",
            "yacht_id": "yacht-001",
            "status": "ACTIVE",
            "role_requested": "captain",
            "invited_by": "admin-001",
            "approved_by": "admin-002",  # 2-person compliant
            "created_at": "2026-01-15T10:00:00Z",
        },
        {
            "id": "mem-002",
            "user_id": "user-002",
            "yacht_id": "yacht-001",
            "status": "ACTIVE",
            "role_requested": "crew",
            "invited_by": "admin-001",
            "approved_by": "admin-001",  # Same person OK for non-privileged
            "created_at": "2026-01-10T10:00:00Z",
        },
        {
            "id": "mem-003",
            "user_id": "user-003",
            "yacht_id": "yacht-001",
            "status": "ACTIVE",
            "role_requested": "manager",
            "invited_by": "admin-001",
            "approved_by": "admin-001",  # VIOLATION - same person for privileged
            "created_at": "2026-01-12T10:00:00Z",
        },
    ]


@pytest.fixture
def mock_db_client(mock_memberships_active):
    """Mock database client."""
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=mock_memberships_active)
    client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
    return client


# ============================================================================
# ACCESS REVIEW TESTS
# ============================================================================

class TestAccessReviewReport:
    """Test access review report generation."""

    @pytest.mark.asyncio
    async def test_report_includes_all_active_memberships(self, mock_db_client, mock_memberships_active):
        """Test report includes all active memberships."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        assert result["summary"]["total_active"] == 3

    @pytest.mark.asyncio
    async def test_report_identifies_privileged_roles(self, mock_db_client):
        """Test report correctly identifies privileged roles."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        # Should have 2 privileged roles (captain, manager)
        assert result["summary"]["total_privileged"] == 2

        privileged_roles = [m["role_requested"] for m in result["privileged_roles"]]
        assert "captain" in privileged_roles
        assert "manager" in privileged_roles
        assert "crew" not in privileged_roles

    @pytest.mark.asyncio
    async def test_two_person_rule_enforced_for_privileged(self, mock_db_client):
        """Test that privileged roles require 2-person approval."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        # Should have 1 violation (manager with same inviter/approver)
        assert result["summary"]["two_person_violations"] == 1

        # Check compliance details
        compliance = result["two_person_compliance"]
        assert len(compliance) == 2  # Only privileged roles checked

        captain = next(c for c in compliance if c["role"] == "captain")
        manager = next(c for c in compliance if c["role"] == "manager")

        assert captain["compliant"] is True
        assert captain["invited_by"] == "admin-001"
        assert captain["approved_by"] == "admin-002"

        assert manager["compliant"] is False
        assert manager["invited_by"] == "admin-001"
        assert manager["approved_by"] == "admin-001"

    @pytest.mark.asyncio
    async def test_non_privileged_roles_not_checked_for_two_person(self, mock_db_client):
        """Test that non-privileged roles are not in 2-person check."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        # Compliance list should not include crew
        roles_in_compliance = [c["role"] for c in result["two_person_compliance"]]
        assert "crew" not in roles_in_compliance


class TestAccessReviewPrivilegedRoles:
    """Test privileged role definitions."""

    def test_privileged_roles_defined(self):
        """Test that privileged roles are properly defined."""
        from handlers.secure_admin_handlers import PRIVILEGED_ROLES

        assert "captain" in PRIVILEGED_ROLES
        assert "manager" in PRIVILEGED_ROLES
        assert "chief_engineer" in PRIVILEGED_ROLES
        assert "crew" not in PRIVILEGED_ROLES
        assert "guest" not in PRIVILEGED_ROLES

    @pytest.mark.asyncio
    async def test_chief_engineer_requires_two_person(self, mock_db_client):
        """Test chief_engineer role requires 2-person approval."""
        from services.audit_export import generate_access_review_data

        # Override with chief_engineer membership
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "mem-001",
                "user_id": "user-001",
                "yacht_id": "yacht-001",
                "status": "ACTIVE",
                "role_requested": "chief_engineer",
                "invited_by": "admin-001",
                "approved_by": "admin-001",  # Violation
                "created_at": "2026-01-15T10:00:00Z",
            },
        ])

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        # Should flag violation
        assert result["summary"]["two_person_violations"] == 1


class TestAccessReviewSummary:
    """Test access review summary statistics."""

    @pytest.mark.asyncio
    async def test_summary_counts_correct(self, mock_db_client, mock_memberships_active):
        """Test summary statistics are correct."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        summary = result["summary"]

        assert summary["total_active"] == 3
        assert summary["total_privileged"] == 2
        assert summary["two_person_violations"] == 1

    @pytest.mark.asyncio
    async def test_summary_includes_period(self, mock_db_client):
        """Test summary includes review period."""
        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        assert result["period"]["start"] == "2026-01-01T00:00:00Z"
        assert result["period"]["end"] == "2026-01-31T23:59:59Z"


class TestAccessReviewRevocations:
    """Test revocation tracking in access review."""

    @pytest.mark.asyncio
    async def test_revocations_counted(self, mock_db_client):
        """Test revocations are counted in review."""
        # Mock with revocation event
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[])
        mock_db_client.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "evt-001",
                "event_type": "admin_revoke_success",
                "user_id": "user-revoked",
                "yacht_id": "yacht-001",
                "details": {"reason": "Policy violation"},
                "created_at": "2026-01-20T10:00:00Z",
            },
        ])

        from services.audit_export import generate_access_review_data

        result = await generate_access_review_data(
            db_client=mock_db_client,
            yacht_id="yacht-001",
            start_ts="2026-01-01T00:00:00Z",
            end_ts="2026-01-31T23:59:59Z",
        )

        assert result["summary"]["revocations_count"] == 1
        assert len(result["revocations"]) == 1


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
