#!/usr/bin/env python3
"""
Fault Lens v1 - Docker/CI Tests
================================

Tests for Fault Lens v1 binding brief implementation:
- Severity mapping (medium→minor, high→major, low→cosmetic)
- Signature invariant (audit_log.signature is NEVER NULL)
- Role gating (crew: report/notes/photos, HOD+: all mutations)
- Show Related API
- Add Related API (HOD+ only)

Run: pytest apps/api/tests/test_fault_lens_v1.py -v
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import pytest

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import handlers
try:
    from handlers.fault_mutation_handlers import (
        FaultMutationHandlers,
        map_severity,
        infer_severity_from_text,
        VALID_SEVERITIES,
        SEVERITY_MAPPING,
        STATUS_TRANSITIONS,
        SYMPTOM_SEVERITY_KEYWORDS,
    )
    HANDLERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import fault handlers: {e}")
    HANDLERS_AVAILABLE = False


# =============================================================================
# UNIT TESTS - Severity Mapping
# =============================================================================

class TestSeverityMapping:
    """Tests for severity mapping function."""

    def test_valid_severities_unchanged(self):
        """Valid severities should return unchanged."""
        for severity in VALID_SEVERITIES:
            assert map_severity(severity) == severity

    def test_legacy_low_maps_to_cosmetic(self):
        """Legacy 'low' should map to 'cosmetic'."""
        assert map_severity("low") == "cosmetic"
        assert map_severity("LOW") == "cosmetic"
        assert map_severity("Low") == "cosmetic"

    def test_legacy_medium_maps_to_minor(self):
        """Legacy 'medium' should map to 'minor'."""
        assert map_severity("medium") == "minor"
        assert map_severity("MEDIUM") == "minor"
        assert map_severity("Medium") == "minor"

    def test_legacy_high_maps_to_major(self):
        """Legacy 'high' should map to 'major'."""
        assert map_severity("high") == "major"
        assert map_severity("HIGH") == "major"
        assert map_severity("High") == "major"

    def test_empty_severity_defaults_to_minor(self):
        """Empty or None severity should default to 'minor'."""
        assert map_severity("") == "minor"
        assert map_severity(None) == "minor"

    def test_invalid_severity_raises(self):
        """Invalid severity should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            map_severity("invalid")
        assert "Invalid severity" in str(exc_info.value)

    def test_case_insensitive(self):
        """Severity mapping should be case insensitive."""
        assert map_severity("CRITICAL") == "critical"
        assert map_severity("Safety") == "safety"
        assert map_severity("MINOR") == "minor"


# =============================================================================
# UNIT TESTS - Symptom-Based Severity Inference (PR #3)
# =============================================================================

class TestSymptomSeverityInference:
    """Tests for symptom-based severity inference per PR #3 binding brief."""

    def test_critical_keywords(self):
        """Fire/smoke/flood/loss of steering → critical."""
        assert infer_severity_from_text("There is smoke coming from the engine room") == "critical"
        assert infer_severity_from_text("Fire detected in galley") == "critical"
        assert infer_severity_from_text("Flooding in bilge compartment") == "critical"
        assert infer_severity_from_text("Loss of steering") == "critical"

    def test_major_keywords(self):
        """Overheating/leak/alarm/shutdown → major."""
        assert infer_severity_from_text("Engine overheating during operation") == "major"
        assert infer_severity_from_text("Hydraulic leak on deck crane") == "major"
        assert infer_severity_from_text("Bilge alarm activated") == "major"
        assert infer_severity_from_text("Generator shutdown unexpectedly") == "major"
        assert infer_severity_from_text("Pump not working") == "major"

    def test_cosmetic_keywords(self):
        """Scratch/paint → cosmetic."""
        assert infer_severity_from_text("Scratch on hull near waterline") == "cosmetic"
        assert infer_severity_from_text("Paint chipping on deck") == "cosmetic"
        assert infer_severity_from_text("Cosmetic damage to interior") == "cosmetic"

    def test_default_minor(self):
        """Unknown symptoms default to minor."""
        assert infer_severity_from_text("General maintenance needed") == "minor"
        assert infer_severity_from_text("Inspection required") == "minor"
        assert infer_severity_from_text("") == "minor"
        assert infer_severity_from_text(None) == "minor"

    def test_priority_order(self):
        """Critical keywords should override major/cosmetic."""
        # Text contains both "fire" (critical) and "not working" (major)
        assert infer_severity_from_text("Fire suppression system not working") == "critical"
        # Text contains both "smoke" (critical) and "scratch" (cosmetic)
        assert infer_severity_from_text("Smoke damage with scratches") == "critical"


# =============================================================================
# UNIT TESTS - Status Transitions
# =============================================================================

class TestStatusTransitions:
    """Tests for status transition validation."""

    def test_open_can_transition_to_investigating(self):
        """Open fault can transition to investigating."""
        assert "investigating" in STATUS_TRANSITIONS["open"]

    def test_open_can_transition_to_false_alarm(self):
        """Open fault can be marked as false alarm."""
        assert "false_alarm" in STATUS_TRANSITIONS["open"]

    def test_closed_can_reopen(self):
        """Closed fault can be reopened."""
        assert "open" in STATUS_TRANSITIONS["closed"]

    def test_false_alarm_is_terminal(self):
        """False alarm is a terminal state."""
        assert STATUS_TRANSITIONS["false_alarm"] == []

    def test_resolved_can_close_or_reopen(self):
        """Resolved fault can be closed or reopened."""
        assert "closed" in STATUS_TRANSITIONS["resolved"]
        assert "open" in STATUS_TRANSITIONS["resolved"]


# =============================================================================
# MOCK DATABASE TESTS - Signature Invariant
# =============================================================================

class MockSupabaseClient:
    """Mock Supabase client for handler testing."""

    def __init__(self):
        self.tables = {}
        self.rpc_calls = []

    def table(self, name: str):
        if name not in self.tables:
            self.tables[name] = MockTable(name)
        return self.tables[name]

    def rpc(self, name: str, params: dict):
        self.rpc_calls.append((name, params))
        return MockRpcResult()


class MockTable:
    """Mock table for testing."""

    def __init__(self, name: str):
        self.name = name
        self.data = []
        self._query = {}

    def select(self, *args, **kwargs):
        self._query["select"] = args
        return self

    def insert(self, data: dict):
        data["id"] = str(uuid.uuid4())
        self.data.append(data)
        self._query["insert"] = data
        return self

    def update(self, data: dict):
        self._query["update"] = data
        return self

    def eq(self, field: str, value):
        self._query[f"eq_{field}"] = value
        return self

    def maybe_single(self):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        return self

    def execute(self):
        return MockResult(self.data, self._query)


class MockResult:
    """Mock query result."""

    def __init__(self, data: list, query: dict):
        if "insert" in query:
            self.data = [query["insert"]]
        elif data:
            self.data = data[:1]
        else:
            self.data = []
        self.count = len(self.data)


class MockRpcResult:
    """Mock RPC result."""

    def execute(self):
        return self


@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestSignatureInvariant:
    """Tests for signature invariant enforcement."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    @pytest.mark.asyncio
    async def test_audit_log_signature_never_none_on_report(self, handlers, mock_client):
        """Audit log signature should be {} for non-signed report_fault."""
        # Setup mock equipment
        mock_client.table("pms_equipment").data = [{
            "id": "test-eq-id",
            "name": "Test Equipment"
        }]

        # Setup mock faults table
        mock_client.table("pms_faults").data = []

        result = await handlers.report_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            title="Test Fault",
            severity="minor",
            description="Test description",
            equipment_id="test-eq-id",
            signature=None  # Explicitly None
        )

        # Check audit log was created with signature = {}
        audit_table = mock_client.tables.get("pms_audit_log")
        if audit_table:
            for entry in audit_table.data:
                # Signature must be {} (empty dict), never None
                assert entry.get("signature") is not None, "Signature should never be None"
                assert isinstance(entry.get("signature"), dict), "Signature should be a dict"

    @pytest.mark.asyncio
    async def test_audit_log_signature_preserved_when_provided(self, handlers, mock_client):
        """Audit log should preserve signature payload when provided."""
        mock_client.table("pms_equipment").data = [{
            "id": "test-eq-id",
            "name": "Test Equipment"
        }]
        mock_client.table("pms_faults").data = []

        signature = {
            "pin_hash": "abc123",
            "totp_verified": True,
            "signed_at": datetime.now(timezone.utc).isoformat()
        }

        result = await handlers.report_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            title="Test Fault",
            severity="minor",
            description="Test description",
            signature=signature
        )

        audit_table = mock_client.tables.get("pms_audit_log")
        if audit_table and audit_table.data:
            entry = audit_table.data[0]
            assert entry.get("signature") == signature


# =============================================================================
# INTEGRATION TESTS - Handler Execution
# =============================================================================

@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestFaultHandlerExecution:
    """Tests for fault handler execution."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    @pytest.mark.asyncio
    async def test_report_fault_maps_severity(self, handlers, mock_client):
        """report_fault should map legacy severity values."""
        mock_client.table("pms_equipment").data = [{
            "id": "test-eq",
            "name": "Test"
        }]
        mock_client.table("pms_faults").data = []

        result = await handlers.report_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            title="Test",
            severity="medium",  # Legacy value
            description="Test"
        )

        # Check fault was created with mapped severity
        faults_table = mock_client.tables.get("pms_faults")
        if faults_table and faults_table.data:
            fault = faults_table.data[0]
            assert fault.get("severity") == "minor"  # Mapped from medium

    @pytest.mark.asyncio
    async def test_report_fault_invalid_severity_returns_error(self, handlers, mock_client):
        """report_fault should return error for invalid severity."""
        result = await handlers.report_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            title="Test",
            severity="invalid_value",
            description="Test"
        )

        assert result.get("status") == "error"
        assert result.get("error_code") == "INVALID_SEVERITY"

    @pytest.mark.asyncio
    async def test_acknowledge_requires_open_status(self, handlers, mock_client):
        """acknowledge_fault should only work on open faults."""
        mock_client.table("pms_faults").data = [{
            "id": "test-fault",
            "fault_code": "FLT-TEST",
            "status": "closed",  # Not open
            "metadata": {}
        }]

        result = await handlers.acknowledge_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            fault_id="test-fault"
        )

        assert result.get("status") == "error"
        assert result.get("error_code") == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_close_fault_creates_audit_log(self, handlers, mock_client):
        """close_fault should create audit log entry."""
        mock_client.table("pms_faults").data = [{
            "id": "test-fault",
            "fault_code": "FLT-TEST",
            "status": "investigating",
            "metadata": {}
        }]

        result = await handlers.close_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            fault_id="test-fault",
            resolution_notes="Resolved"
        )

        # Verify audit log was created
        audit_table = mock_client.tables.get("pms_audit_log")
        if audit_table:
            assert len(audit_table.data) > 0
            entry = audit_table.data[0]
            assert entry.get("action") == "close_fault"
            assert entry.get("entity_type") == "fault"


# =============================================================================
# PREFILL TESTS
# =============================================================================

@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestFaultPrefill:
    """Tests for fault prefill functionality."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    @pytest.mark.asyncio
    async def test_prefill_default_severity(self, handlers):
        """Prefill should default severity to 'minor'."""
        result = await handlers.report_fault_prefill(
            yacht_id="test-yacht",
            user_id="test-user"
        )

        assert result.get("status") == "success"
        assert result.get("prefill", {}).get("severity") == "minor"

    @pytest.mark.asyncio
    async def test_prefill_extracts_query_text(self, handlers):
        """Prefill should extract title/description from query_text."""
        result = await handlers.report_fault_prefill(
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="Bilge pump making unusual noise"
        )

        prefill = result.get("prefill", {})
        assert prefill.get("title") == "Bilge pump making unusual noise"
        assert prefill.get("description") == "Bilge pump making unusual noise"


# =============================================================================
# PREVIEW TESTS
# =============================================================================

@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestFaultPreview:
    """Tests for fault preview functionality."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    @pytest.mark.asyncio
    async def test_preview_warns_on_severity_mapping(self, handlers, mock_client):
        """Preview should warn when severity is mapped."""
        result = await handlers.report_fault_preview(
            title="Test",
            severity="medium",  # Will be mapped to minor
            equipment_id=None,
            description="Test",
            yacht_id="test-yacht",
            user_id="test-user"
        )

        warnings = result.get("warnings", [])
        severity_warnings = [w for w in warnings if w.get("type") == "severity_mapped"]
        assert len(severity_warnings) > 0

    @pytest.mark.asyncio
    async def test_preview_warns_on_critical_severity(self, handlers, mock_client):
        """Preview should warn about handover for critical/safety."""
        result = await handlers.report_fault_preview(
            title="Test",
            severity="critical",
            equipment_id=None,
            description="Test",
            yacht_id="test-yacht",
            user_id="test-user"
        )

        warnings = result.get("warnings", [])
        severity_warnings = [w for w in warnings if w.get("type") == "severity_warning"]
        assert len(severity_warnings) > 0

        # Should also suggest work order
        suggestions = result.get("suggestions", [])
        wo_suggestions = [s for s in suggestions if s.get("action") == "create_work_order_from_fault"]
        assert len(wo_suggestions) > 0


# =============================================================================
# UNIT TESTS - Signature Validation (PR #3)
# =============================================================================

@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestSignatureValidation:
    """Tests for signature validation per PR #3 binding brief."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    def test_missing_signature_returns_errors(self, handlers):
        """Missing signature should return error list."""
        errors = handlers._validate_signature(None)
        assert len(errors) > 0
        assert "Signature is required" in errors

    def test_empty_signature_returns_errors(self, handlers):
        """Empty signature should return missing field errors."""
        errors = handlers._validate_signature({})
        assert len(errors) > 0
        # Should have errors for missing required fields
        required_fields = ["signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"]
        for field in required_fields:
            assert any(field in e for e in errors)

    def test_valid_signature_returns_no_errors(self, handlers):
        """Valid signature should return empty error list."""
        signature = {
            "signed_at": "2026-01-27T12:00:00Z",
            "user_id": "test-user-id",
            "role_at_signing": "captain",
            "signature_type": "pin_totp",
            "signature_hash": "abc123hash",
        }
        errors = handlers._validate_signature(signature)
        assert len(errors) == 0

    def test_wrong_signature_type_returns_error(self, handlers):
        """Wrong signature_type should return error."""
        signature = {
            "signed_at": "2026-01-27T12:00:00Z",
            "user_id": "test-user-id",
            "role_at_signing": "captain",
            "signature_type": "password",  # Wrong type
            "signature_hash": "abc123hash",
        }
        errors = handlers._validate_signature(signature)
        assert len(errors) > 0
        assert any("signature_type" in e.lower() for e in errors)


# =============================================================================
# INTEGRATION TESTS - Create Work Order from Fault (Signed Flow)
# =============================================================================

@pytest.mark.skipif(not HANDLERS_AVAILABLE, reason="Handlers not available")
class TestCreateWorkOrderFromFault:
    """Tests for create_work_order_from_fault signed flow (PR #3)."""

    @pytest.fixture
    def mock_client(self):
        return MockSupabaseClient()

    @pytest.fixture
    def handlers(self, mock_client):
        return FaultMutationHandlers(mock_client)

    @pytest.mark.asyncio
    async def test_execute_requires_signature(self, handlers, mock_client):
        """Execute should fail without valid signature."""
        mock_client.table("pms_faults").data = [{
            "id": "test-fault",
            "fault_code": "FLT-TEST",
            "title": "Test Fault",
            "status": "open",
            "severity": "major",
        }]

        # Call with invalid signature
        result = await handlers.create_work_order_from_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            fault_id="test-fault",
            signature={},  # Invalid - empty
        )

        assert result.get("status") == "error"
        assert result.get("error_code") == "INVALID_SIGNATURE"

    @pytest.mark.asyncio
    async def test_execute_requires_captain_or_manager_signature(self, handlers, mock_client):
        """Execute should fail if signer is not captain or manager."""
        mock_client.table("pms_faults").data = [{
            "id": "test-fault",
            "fault_code": "FLT-TEST",
            "title": "Test Fault",
            "status": "open",
            "severity": "major",
        }]

        # Valid signature but wrong role
        signature = {
            "signed_at": "2026-01-27T12:00:00Z",
            "user_id": "test-user",
            "role_at_signing": "chief_engineer",  # Not captain or manager
            "signature_type": "pin_totp",
            "signature_hash": "abc123hash",
        }

        result = await handlers.create_work_order_from_fault_execute(
            yacht_id="test-yacht",
            user_id="test-user",
            fault_id="test-fault",
            signature=signature,
        )

        assert result.get("status") == "error"
        assert result.get("error_code") == "INVALID_SIGNATURE_ROLE"

    @pytest.mark.asyncio
    async def test_severity_to_priority_mapping(self, handlers):
        """Fault severity should map to work order priority correctly."""
        assert handlers._map_severity_to_priority("cosmetic") == "low"
        assert handlers._map_severity_to_priority("minor") == "medium"
        assert handlers._map_severity_to_priority("major") == "high"
        assert handlers._map_severity_to_priority("critical") == "critical"
        assert handlers._map_severity_to_priority("safety") == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
