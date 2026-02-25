"""
Example Test: LAW 17 In-Memory Testing
=======================================

This file demonstrates how to use the new in-memory testing infrastructure.

Key Benefits:
- No uvicorn server required
- Tests run faster
- More reliable (no network/port issues)
- Easier to debug
- Works in CI/CD without extra setup

Usage:
    pytest apps/api/tests/test_in_memory_example.py -v
"""

import pytest
import pytest_asyncio
import httpx


class TestInMemoryExample:
    """Examples of in-memory testing with LAW 17."""

    @pytest.mark.asyncio
    async def test_health_endpoint_basic(self, async_client: httpx.AsyncClient):
        """
        Test the health endpoint using in-memory client.

        LAW 17: This test runs without requiring a server.
        The async_client fixture provides an httpx.AsyncClient that
        communicates directly with the FastAPI app in-memory.
        """
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_authenticated_request(self, authenticated_client: httpx.AsyncClient):
        """
        Test an authenticated request using pre-configured client.

        LAW 17: The authenticated_client fixture includes a valid JWT token
        for TEST_USER_A (Yacht A) automatically.
        """
        # The authenticated_client already has the Authorization header set
        response = await authenticated_client.get("/api/f1/search/stream", params={"q": "test"})

        # Note: This might return 200 or other status depending on backend state
        # The key is that it doesn't return 401 (unauthorized)
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_custom_jwt(self, async_client: httpx.AsyncClient, jwt_yacht_b: str):
        """
        Test with a custom JWT token for a different yacht.

        LAW 17: You can use any JWT fixture (jwt_yacht_a, jwt_yacht_b, etc.)
        to test different user contexts.
        """
        headers = {"Authorization": f"Bearer {jwt_yacht_b}"}

        response = await async_client.get(
            "/api/f1/search/stream",
            params={"q": "oil filter"},
            headers=headers
        )

        # Should be authenticated (not 401)
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self, async_client: httpx.AsyncClient):
        """
        Test that invalid JWT returns 401.

        LAW 17: Authentication middleware works correctly in-memory.
        """
        headers = {"Authorization": "Bearer totally-invalid-token"}

        response = await async_client.get(
            "/api/f1/search/stream",
            params={"q": "test"},
            headers=headers
        )

        assert response.status_code == 401


class TestInMemoryAdvanced:
    """Advanced in-memory testing patterns."""

    @pytest.mark.asyncio
    async def test_post_request(self, authenticated_client: httpx.AsyncClient):
        """
        Test POST requests with JSON body.

        LAW 17: All HTTP methods work in-memory (GET, POST, PUT, DELETE, etc.)
        """
        # Example: Test search endpoint with POST
        payload = {
            "query": "engine parts",
            "filters": {
                "category": "mechanical"
            }
        }

        response = await authenticated_client.post(
            "/search",
            json=payload
        )

        # Check response structure (exact behavior depends on endpoint)
        assert response.status_code in [200, 201, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_streaming_response(self, authenticated_client: httpx.AsyncClient):
        """
        Test SSE streaming endpoints.

        LAW 17: Streaming works in-memory via httpx's streaming API.
        """
        async with authenticated_client.stream(
            "GET",
            "/api/f1/search/stream",
            params={"q": "oil filter"}
        ) as response:
            # Check that we got a streaming response
            assert "text/event-stream" in response.headers.get("content-type", "")

            # Read a few lines from the stream
            lines = []
            async for line in response.aiter_lines():
                lines.append(line)
                if len(lines) >= 5:
                    break

            # Should have received some SSE events
            assert len(lines) > 0


# ============================================================================
# Migration Notes
# ============================================================================
"""
MIGRATING OLD TESTS TO LAW 17:

Before (required server):
    pytest.skip("Requires local API server")
    response = await async_client.get("http://localhost:8000/health")

After (in-memory):
    # Just remove the skip and the base_url
    response = await async_client.get("/health")

Key Changes:
1. Remove pytest.skip("Requires local API server")
2. Use relative URLs (starts with /) instead of full URLs
3. The async_client fixture now uses app=app instead of base_url
4. Everything else stays the same!

Fixtures Available:
- async_client: Basic client, no auth
- authenticated_client: Client with JWT for Yacht A (TEST_USER_A_ID)
- jwt_yacht_a: JWT token string for Yacht A
- jwt_yacht_b: JWT token string for Yacht B
- jwt_expired: Expired JWT for testing expiration
- jwt_invalid_signature: JWT with wrong signature
- user_yacht_a: TestUser object for Yacht A
- user_yacht_b: TestUser object for Yacht B
"""
