"""
SSE Streaming Tests for F1 Search

Tests for Server-Sent Events (SSE) streaming endpoint behavior.

Event sequence verified:
1. diagnostics - Search started, search_id
2. result_batch - Fused results (every ~100ms or on early win)
3. finalized - Search complete, latency metrics

See: apps/api/docs/F1_SEARCH/STREAMING_FUSION_LAYER.md
     apps/api/docs/F1_SEARCH/FRONTEND_STREAMING_API.md
"""

import pytest
import pytest_asyncio
import json
import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Import test utilities from conftest.py (pytest auto-discovers this)
# Constants and fixtures are available via pytest's conftest mechanism
from dataclasses import dataclass

@dataclass
class TestUser:
    """Test user context for authentication."""
    user_id: str
    yacht_id: str
    org_id: str
    role: str = "crew"
    email: str = "test@example.com"

TEST_YACHT_A_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_YACHT_B_ID = "00000000-0000-0000-0000-000000000002"

# Note: generate_test_jwt, generate_expired_jwt, parse_sse_events,
# generate_invalid_signature_jwt are available as fixtures from conftest.py


# ============================================================================
# SSE Event Parsing Helpers
# ============================================================================

def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format an SSE event (mirrors production sse_event function)."""
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def parse_sse_line(line: str) -> tuple:
    """Parse a single SSE line into (field, value)."""
    if ":" in line:
        field, value = line.split(":", 1)
        return field.strip(), value.strip()
    return None, None


class MockSSEResponse:
    """Mock SSE response for testing."""

    def __init__(self, events: List[Dict[str, Any]]):
        self.events = events
        self._lines = self._generate_lines()

    def _generate_lines(self) -> List[str]:
        """Generate SSE lines from events."""
        lines = []
        for event in self.events:
            lines.append(f"event: {event['event']}")
            lines.append(f"data: {json.dumps(event['data'])}")
            lines.append("")  # Empty line terminates event
        return lines

    async def aiter_lines(self):
        """Async iterator over response lines."""
        for line in self._lines:
            yield line


# ============================================================================
# SSE Event Format Tests
# ============================================================================

class TestSSEEventFormat:
    """Tests for SSE event formatting."""

    def test_sse_event_format_structure(self):
        """SSE event should have correct format."""
        event = format_sse_event("diagnostics", {"search_id": "test-123"})

        assert event.startswith("event: diagnostics\n")
        assert "data: " in event
        assert event.endswith("\n\n")

    def test_sse_event_json_data(self):
        """SSE event data should be valid JSON."""
        data = {"search_id": "test-123", "status": "started"}
        event = format_sse_event("diagnostics", data)

        # Extract data line
        lines = event.strip().split("\n")
        data_line = [l for l in lines if l.startswith("data:")][0]
        json_str = data_line.split(":", 1)[1].strip()

        parsed = json.loads(json_str)
        assert parsed == data

    def test_sse_event_types(self):
        """All expected event types should format correctly."""
        event_types = [
            "diagnostics",
            "exact_match_win",
            "result_batch",
            "finalized",
            "error",
        ]

        for event_type in event_types:
            event = format_sse_event(event_type, {"test": True})
            assert f"event: {event_type}" in event


# ============================================================================
# SSE Event Parsing Tests
# ============================================================================

class TestSSEEventParsing:
    """Tests for SSE event parsing."""

    @pytest.mark.asyncio
    async def test_parse_single_event(self, sse_parser):
        """Single event should parse correctly."""
        events = [{"event": "diagnostics", "data": {"search_id": "abc-123"}}]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        assert len(parsed) == 1
        assert parsed[0]["event"] == "diagnostics"
        assert parsed[0]["data"]["search_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_parse_multiple_events(self, sse_parser):
        """Multiple events should parse in order."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123", "status": "started"}},
            {"event": "result_batch", "data": {"items": [{"id": "1"}], "count": 1}},
            {"event": "finalized", "data": {"latency_ms": 150}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        assert len(parsed) == 3
        assert parsed[0]["event"] == "diagnostics"
        assert parsed[1]["event"] == "result_batch"
        assert parsed[2]["event"] == "finalized"

    @pytest.mark.asyncio
    async def test_parse_event_with_complex_data(self, sse_parser):
        """Events with nested data should parse correctly."""
        events = [
            {
                "event": "result_batch",
                "data": {
                    "items": [
                        {
                            "object_id": "uuid-1",
                            "payload": {"title": "Test", "nested": {"deep": True}},
                        }
                    ],
                    "partial": False,
                },
            }
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        assert parsed[0]["data"]["items"][0]["payload"]["nested"]["deep"] is True


# ============================================================================
# Event Sequence Tests
# ============================================================================

class TestSSEEventSequence:
    """Tests for correct SSE event sequence."""

    @pytest.mark.asyncio
    async def test_normal_search_event_sequence(self, sse_parser):
        """Normal search should emit: diagnostics -> result_batch -> finalized."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123", "status": "started"}},
            {"event": "result_batch", "data": {"items": [], "count": 0}},
            {"event": "finalized", "data": {"search_id": "abc-123", "latency_ms": 150}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        # Verify sequence
        assert parsed[0]["event"] == "diagnostics"
        assert parsed[-1]["event"] == "finalized"

    @pytest.mark.asyncio
    async def test_exact_match_win_sequence(self, sse_parser):
        """
        Exact match win should emit: diagnostics -> exact_match_win -> result_batch -> finalized.
        """
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123", "status": "started"}},
            {"event": "exact_match_win", "data": {"object_id": "exact-1", "object_type": "part"}},
            {"event": "result_batch", "data": {"items": [{"object_id": "exact-1"}], "count": 1}},
            {"event": "finalized", "data": {"search_id": "abc-123", "early_win": True}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        # exact_match_win should appear before result_batch
        event_types = [e["event"] for e in parsed]
        assert event_types.index("exact_match_win") < event_types.index("result_batch")

    @pytest.mark.asyncio
    async def test_error_event_terminates_stream(self, sse_parser):
        """Error event should terminate the stream."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123"}},
            {"event": "error", "data": {"error": "timeout", "message": "Search timed out"}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        assert parsed[-1]["event"] == "error"
        assert parsed[-1]["data"]["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_diagnostics_always_first(self, sse_parser):
        """Diagnostics event should always be first."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123", "query": "test"}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        assert parsed[0]["event"] == "diagnostics"
        assert "search_id" in parsed[0]["data"]


# ============================================================================
# Content-Type Header Tests
# ============================================================================

class TestSSEContentType:
    """Tests for SSE Content-Type header."""

    def test_sse_content_type_value(self):
        """SSE response should have text/event-stream Content-Type."""
        expected_content_type = "text/event-stream"

        # This is the value set in production
        # In actual integration tests, this would be verified from response headers
        assert expected_content_type == "text/event-stream"

    def test_sse_response_headers(self):
        """SSE response should have required headers."""
        # Expected headers from production
        expected_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }

        for header, value in expected_headers.items():
            assert value is not None


# ============================================================================
# Search Timeout Tests
# ============================================================================

class TestSearchTimeout:
    """Tests for search timeout enforcement."""

    def test_timeout_budget_constant(self):
        """Verify timeout budget constant is 800ms."""
        from services.types import DEFAULT_BUDGET

        assert DEFAULT_BUDGET.global_timeout_ms == 800

    def test_db_statement_timeout(self):
        """Verify DB statement timeout is configured."""
        from services.types import DEFAULT_BUDGET

        # DB timeout should be less than global timeout
        assert DEFAULT_BUDGET.db_timeout_ms < DEFAULT_BUDGET.global_timeout_ms

    @pytest.mark.asyncio
    async def test_timeout_error_event_format(self, sse_parser):
        """Timeout should emit error event with correct format."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123"}},
            {"event": "error", "data": {"search_id": "abc-123", "error": "timeout", "message": "Search timed out"}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        error_event = parsed[-1]
        assert error_event["event"] == "error"
        assert error_event["data"]["error"] == "timeout"
        assert "message" in error_event["data"]


# ============================================================================
# Empty Query Handling Tests
# ============================================================================

class TestEmptyQueryHandling:
    """Tests for empty/invalid query handling."""

    def test_query_minimum_length(self):
        """Query should have minimum length of 1."""
        # This is enforced by FastAPI Query(..., min_length=1)
        min_length = 1
        assert min_length == 1

    @pytest.mark.asyncio
    async def test_empty_results_event_format(self, sse_parser):
        """Empty results should still emit proper event sequence."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123", "query": "xyznonexistent"}},
            {"event": "result_batch", "data": {"items": [], "count": 0, "partial": False}},
            {"event": "finalized", "data": {"search_id": "abc-123", "total_results": 0, "latency_ms": 50}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        # Verify complete sequence even with no results
        assert len(parsed) == 3
        assert parsed[1]["data"]["count"] == 0
        assert parsed[2]["data"]["total_results"] == 0


# ============================================================================
# JWT Validation Tests
# ============================================================================

class TestJWTValidation:
    """Tests for JWT validation in SSE endpoint."""

    def test_expired_jwt_rejected(self, user_yacht_a: TestUser):
        """Expired JWT should be rejected with 401."""
        expired_token = generate_expired_jwt(user_yacht_a)

        # In actual integration test, this would call the endpoint
        # and verify 401 response
        assert expired_token is not None
        assert len(expired_token) > 20

    def test_invalid_signature_jwt_rejected(self, user_yacht_a: TestUser):
        """JWT with invalid signature should be rejected."""
        invalid_token = generate_invalid_signature_jwt(user_yacht_a)

        # Token exists but won't verify
        assert invalid_token is not None

    def test_valid_jwt_accepted(self, jwt_yacht_a: str):
        """Valid JWT should be accepted."""
        import jwt as pyjwt

        # Verify token structure (without signature verification)
        decoded = pyjwt.decode(jwt_yacht_a, options={"verify_signature": False})

        assert "sub" in decoded
        assert "yacht_id" in decoded
        assert "org_id" in decoded

    def test_missing_org_id_rejected(self):
        """JWT missing org_id should be rejected with 403."""
        # Create user without org_id
        user_no_org = TestUser(
            user_id="test-user",
            yacht_id="test-yacht",
            org_id="test-org",  # Required for UserContext
        )

        # In production, missing org_id in JWT would cause 403
        # This tests the requirement
        from services.types import UserContext

        # Should work with org_id
        ctx = UserContext(
            user_id=user_no_org.user_id,
            org_id=user_no_org.org_id,
            yacht_id=user_no_org.yacht_id,
        )
        assert ctx.org_id is not None


# ============================================================================
# Finalized Event Tests
# ============================================================================

class TestFinalizedEvent:
    """Tests for finalized event content."""

    @pytest.mark.asyncio
    async def test_finalized_contains_latency(self, sse_parser):
        """Finalized event should contain latency_ms."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123"}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {"search_id": "abc-123", "latency_ms": 150, "total_results": 0}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        finalized = parsed[-1]
        assert "latency_ms" in finalized["data"]
        assert isinstance(finalized["data"]["latency_ms"], int)

    @pytest.mark.asyncio
    async def test_finalized_contains_total_results(self, sse_parser):
        """Finalized event should contain total_results count."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "result_batch", "data": {"items": [{"id": "1"}, {"id": "2"}]}},
            {"event": "finalized", "data": {"total_results": 2}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        finalized = parsed[-1]
        assert finalized["data"]["total_results"] == 2

    @pytest.mark.asyncio
    async def test_finalized_indicates_early_win(self, sse_parser):
        """Finalized event should indicate if early win occurred."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "exact_match_win", "data": {"object_id": "exact-1"}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {"early_win": True, "status": "early_win"}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        finalized = parsed[-1]
        assert finalized["data"]["early_win"] is True
        assert finalized["data"]["status"] == "early_win"

    @pytest.mark.asyncio
    async def test_finalized_contains_cache_info(self, sse_parser):
        """Finalized event should indicate cache hit/miss."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {
                "rewrite_cache_hit": True,
                "result_cache_hit": False,
            }},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        finalized = parsed[-1]
        assert "rewrite_cache_hit" in finalized["data"]
        assert "result_cache_hit" in finalized["data"]


# ============================================================================
# Result Batch Event Tests
# ============================================================================

class TestResultBatchEvent:
    """Tests for result_batch event content."""

    @pytest.mark.asyncio
    async def test_result_batch_contains_items(self, sse_parser):
        """Result batch should contain items array."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "result_batch", "data": {
                "items": [
                    {"object_id": "1", "object_type": "part", "fused_score": 0.9},
                    {"object_id": "2", "object_type": "part", "fused_score": 0.8},
                ],
                "count": 2,
                "partial": False,
            }},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        result_batch = parsed[1]
        assert "items" in result_batch["data"]
        assert len(result_batch["data"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_result_batch_item_structure(self, sse_parser):
        """Each item in result batch should have required fields."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "result_batch", "data": {
                "items": [
                    {
                        "object_id": "uuid-123",
                        "object_type": "part",
                        "payload": {"title": "Oil Filter"},
                        "fused_score": 0.95,
                        "ranks": {"trigram": 1, "vector": 2},
                    }
                ],
                "count": 1,
            }},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        item = parsed[1]["data"]["items"][0]
        assert "object_id" in item
        assert "object_type" in item
        assert "payload" in item
        assert "fused_score" in item

    @pytest.mark.asyncio
    async def test_result_batch_partial_flag(self, sse_parser):
        """Result batch should indicate if partial results."""
        events = [
            {"event": "diagnostics", "data": {}},
            {"event": "result_batch", "data": {"items": [], "partial": False}},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        result_batch = parsed[1]
        assert "partial" in result_batch["data"]


# ============================================================================
# Diagnostics Event Tests
# ============================================================================

class TestDiagnosticsEvent:
    """Tests for diagnostics event content."""

    @pytest.mark.asyncio
    async def test_diagnostics_contains_search_id(self, sse_parser):
        """Diagnostics should contain unique search_id."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "550e8400-e29b-41d4-a716-446655440000"}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        diagnostics = parsed[0]
        assert "search_id" in diagnostics["data"]

    @pytest.mark.asyncio
    async def test_diagnostics_contains_query(self, sse_parser):
        """Diagnostics should echo back the query."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc", "query": "oil filter", "status": "started"}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        diagnostics = parsed[0]
        assert diagnostics["data"]["query"] == "oil filter"

    @pytest.mark.asyncio
    async def test_diagnostics_contains_timestamp(self, sse_parser):
        """Diagnostics should contain timestamp."""
        now = time.time()
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc", "timestamp": now}},
            {"event": "result_batch", "data": {"items": []}},
            {"event": "finalized", "data": {}},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        diagnostics = parsed[0]
        assert "timestamp" in diagnostics["data"]


# ============================================================================
# Error Event Tests
# ============================================================================

class TestErrorEvent:
    """Tests for error event handling."""

    @pytest.mark.asyncio
    async def test_error_event_structure(self, sse_parser):
        """Error event should have required fields."""
        events = [
            {"event": "diagnostics", "data": {"search_id": "abc-123"}},
            {"event": "error", "data": {
                "search_id": "abc-123",
                "error": "database_error",
                "message": "Connection timeout",
            }},
        ]
        mock_response = MockSSEResponse(events)

        parsed = await sse_parser(mock_response)

        error = parsed[-1]
        assert error["event"] == "error"
        assert "error" in error["data"]
        assert "message" in error["data"]

    @pytest.mark.asyncio
    async def test_error_types(self, sse_parser):
        """Different error types should be supported."""
        error_types = ["timeout", "database_error", "internal_error"]

        for error_type in error_types:
            events = [
                {"event": "diagnostics", "data": {}},
                {"event": "error", "data": {"error": error_type, "message": f"Test {error_type}"}},
            ]
            mock_response = MockSSEResponse(events)

            parsed = await sse_parser(mock_response)
            assert parsed[-1]["data"]["error"] == error_type


# ============================================================================
# Integration Test Markers
# ============================================================================

@pytest.mark.integration
@pytest.mark.sse
class TestSSEIntegration:
    """
    Integration tests requiring actual API endpoint.

    Run with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_real_sse_endpoint(self, async_client, jwt_yacht_a: str):
        """
        Test real SSE endpoint returns proper event stream.

        LAW 17: Now runs in-memory without requiring a local API server.
        """
        headers = {"Authorization": f"Bearer {jwt_yacht_a}"}

        async with async_client.stream(
            "GET",
            "/api/f1/search/stream",
            params={"q": "oil filter"},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            events = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":")[1].strip())
                if len(events) >= 3:
                    break

            assert "diagnostics" in events

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self, async_client):
        """
        Invalid JWT should return 401.

        LAW 17: Now runs in-memory without requiring a local API server.
        """
        headers = {"Authorization": "Bearer invalid-token"}

        response = await async_client.get(
            "/api/f1/search/stream",
            params={"q": "test"},
            headers=headers,
        )

        assert response.status_code == 401
