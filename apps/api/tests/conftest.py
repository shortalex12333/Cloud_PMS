"""
PyTest Configuration and Fixtures for F1 Search Pipeline Tests

Provides:
- Async test client using httpx.AsyncClient (IN-MEMORY, no server required)
- JWT token generation for test users (Yacht A, Yacht B)
- Database connection pooling with asyncpg
- Environment variable loading
- Mock fixtures for isolated unit testing

Usage:
    pytest apps/api/tests/ -v --asyncio-mode=auto

LAW 17: In-Memory Testing
    Tests run against the FastAPI app directly via httpx.AsyncClient
    No uvicorn server required - tests are faster and more reliable
"""

import os
import sys
import json
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import jwt
import httpx

# Add the api directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app for in-memory testing (LAW 17)
# Note: If you get ModuleNotFoundError for 'websockets.asyncio', install it:
#   pip install websockets>=12.0
try:
    from pipeline_service import app
except ModuleNotFoundError as e:
    if "websockets.asyncio" in str(e):
        # Provide helpful error message for missing dependency
        import sys
        print("\n" + "="*80)
        print("❌ MISSING DEPENDENCY: websockets.asyncio")
        print("="*80)
        print("LAW 17 requires the websockets package version 12.0+")
        print("\nTo fix, run:")
        print("  pip install 'websockets>=12.0'")
        print("\nOr if using uv:")
        print("  uv pip install 'websockets>=12.0'")
        print("="*80 + "\n")
        sys.exit(1)
    else:
        raise


# ============================================================================
# Test Configuration Constants
# ============================================================================

# Test yacht IDs for isolation testing
TEST_YACHT_A_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_YACHT_B_ID = "00000000-0000-0000-0000-000000000002"

# Test user IDs
TEST_USER_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TEST_USER_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

# Test org IDs (usually same as yacht for single-yacht orgs)
TEST_ORG_A_ID = TEST_YACHT_A_ID
TEST_ORG_B_ID = TEST_YACHT_B_ID

# API endpoints
API_BASE_URL = os.getenv("TEST_API_BASE_URL", "https://celeste-pipeline-v1.onrender.com")
LOCAL_API_BASE_URL = "http://localhost:8000"

# JWT secret for test tokens (use env var or default test secret)
TEST_JWT_SECRET = os.getenv("TEST_JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

# Database DSN for integration tests
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL", ""))


# ============================================================================
# JWT Token Generation
# ============================================================================

@dataclass
class TestUser:
    """Test user context for authentication."""
    user_id: str
    yacht_id: str
    org_id: str
    role: str = "crew"
    email: str = "test@example.com"


def generate_test_jwt(
    user: TestUser,
    secret: str = TEST_JWT_SECRET,
    expires_in: int = 3600,
) -> str:
    """
    Generate a valid JWT token for testing.

    Args:
        user: TestUser object with user context
        secret: JWT signing secret
        expires_in: Token expiration time in seconds

    Returns:
        Signed JWT token string
    """
    now = int(time.time())
    payload = {
        "sub": user.user_id,
        "aud": "authenticated",
        "role": user.role,
        "email": user.email,
        "iat": now,
        "exp": now + expires_in,
        # Custom claims for Celeste
        "user_id": user.user_id,
        "yacht_id": user.yacht_id,
        "org_id": user.org_id,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_expired_jwt(user: TestUser, secret: str = TEST_JWT_SECRET) -> str:
    """Generate an expired JWT token for testing."""
    now = int(time.time())
    payload = {
        "sub": user.user_id,
        "aud": "authenticated",
        "role": user.role,
        "email": user.email,
        "iat": now - 7200,  # 2 hours ago
        "exp": now - 3600,  # Expired 1 hour ago
        "user_id": user.user_id,
        "yacht_id": user.yacht_id,
        "org_id": user.org_id,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_invalid_signature_jwt(user: TestUser) -> str:
    """Generate a JWT with invalid signature for testing."""
    return generate_test_jwt(user, secret="wrong-secret-key")


# ============================================================================
# Test User Fixtures
# ============================================================================

@pytest.fixture
def user_yacht_a() -> TestUser:
    """Test user belonging to Yacht A."""
    return TestUser(
        user_id=TEST_USER_A_ID,
        yacht_id=TEST_YACHT_A_ID,
        org_id=TEST_ORG_A_ID,
        role="chief_engineer",
        email="engineer_a@yacht-a.test",
    )


@pytest.fixture
def user_yacht_b() -> TestUser:
    """Test user belonging to Yacht B."""
    return TestUser(
        user_id=TEST_USER_B_ID,
        yacht_id=TEST_YACHT_B_ID,
        org_id=TEST_ORG_B_ID,
        role="crew",
        email="crew_b@yacht-b.test",
    )


@pytest.fixture
def jwt_yacht_a(user_yacht_a: TestUser) -> str:
    """Valid JWT token for Yacht A user."""
    return generate_test_jwt(user_yacht_a)


@pytest.fixture
def jwt_yacht_b(user_yacht_b: TestUser) -> str:
    """Valid JWT token for Yacht B user."""
    return generate_test_jwt(user_yacht_b)


@pytest.fixture
def jwt_expired(user_yacht_a: TestUser) -> str:
    """Expired JWT token for testing."""
    return generate_expired_jwt(user_yacht_a)


@pytest.fixture
def jwt_invalid_signature(user_yacht_a: TestUser) -> str:
    """JWT with invalid signature for testing."""
    return generate_invalid_signature_jwt(user_yacht_a)


# ============================================================================
# HTTP Client Fixtures (LAW 17: In-Memory Testing)
# ============================================================================

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Async HTTP client that tests the FastAPI app in-memory.

    LAW 17: No uvicorn server required - tests run directly against the app.
    This is faster, more reliable, and eliminates server startup issues.

    Uses httpx.AsyncClient with app parameter for in-memory testing.
    Configured with reasonable timeouts for SSE streaming.
    """
    async with httpx.AsyncClient(
        app=app,
        base_url="http://test",
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=True,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(async_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """
    Client with valid JWT token in headers for Yacht A.

    LAW 17: Pre-configured with authentication for testing protected routes.
    Uses the test user context from TEST_USER_A_ID/TEST_YACHT_A_ID.
    """
    user = TestUser(
        user_id=TEST_USER_A_ID,
        yacht_id=TEST_YACHT_A_ID,
        org_id=TEST_ORG_A_ID,
        role="hod",
        email="hod.test@alex-short.com"
    )
    token = generate_test_jwt(user)
    async_client.headers.update({"Authorization": f"Bearer {token}"})
    return async_client


@pytest_asyncio.fixture
async def production_client():
    """
    Async HTTP client pointed at production API.

    Use with caution - only for smoke tests against real infrastructure.
    This client bypasses in-memory testing and hits real servers.
    """
    async with httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
    ) as client:
        yield client


# ============================================================================
# Database Connection Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def db_pool():
    """
    AsyncPG connection pool for database tests.

    Skips if TEST_DATABASE_URL is not configured.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not configured")

    import asyncpg

    pool = await asyncpg.create_pool(
        TEST_DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=10.0,
        statement_cache_size=0,  # Disable for pgbouncer compatibility
    )

    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def db_connection(db_pool):
    """Single database connection from the pool."""
    async with db_pool.acquire() as conn:
        yield conn


# ============================================================================
# Mock Fixtures for Unit Testing
# ============================================================================

@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client for unit testing.

    Provides mocked table().select().eq()... chain.
    """
    mock_client = MagicMock()

    # Default mock response builder
    def create_mock_table(table_name: str):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_single = MagicMock()
        mock_execute = MagicMock()

        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.eq.return_value = mock_eq  # Allow chaining
        mock_eq.maybe_single.return_value = mock_single
        mock_eq.single.return_value = mock_single
        mock_single.execute.return_value = mock_execute
        mock_execute.data = None  # Default to no data

        return mock_table

    mock_client.table.side_effect = create_mock_table
    return mock_client


@pytest.fixture
def mock_asyncpg_connection():
    """
    Mock asyncpg connection for unit testing.

    Provides async fetch() and execute() methods.
    """
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = None
    mock_conn.execute.return_value = None
    return mock_conn


@pytest.fixture
def mock_redis():
    """
    Mock Redis client for caching tests.
    """
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.ping.return_value = True
    return mock_redis


# ============================================================================
# Auth Context Fixtures
# ============================================================================

@pytest.fixture
def auth_context_yacht_a(user_yacht_a: TestUser) -> Dict[str, Any]:
    """
    Pre-built auth context dict for Yacht A.

    Mimics the output of get_authenticated_user() middleware.
    """
    return {
        "user_id": user_yacht_a.user_id,
        "email": user_yacht_a.email,
        "yacht_id": user_yacht_a.yacht_id,
        "org_id": user_yacht_a.org_id,
        "tenant_key_alias": f"y{user_yacht_a.yacht_id[:8]}",
        "role": user_yacht_a.role,
        "yacht_name": "M/Y Test Yacht A",
    }


@pytest.fixture
def auth_context_yacht_b(user_yacht_b: TestUser) -> Dict[str, Any]:
    """
    Pre-built auth context dict for Yacht B.
    """
    return {
        "user_id": user_yacht_b.user_id,
        "email": user_yacht_b.email,
        "yacht_id": user_yacht_b.yacht_id,
        "org_id": user_yacht_b.org_id,
        "tenant_key_alias": f"y{user_yacht_b.yacht_id[:8]}",
        "role": user_yacht_b.role,
        "yacht_name": "M/Y Test Yacht B",
    }


# ============================================================================
# SSE Streaming Helpers
# ============================================================================

async def parse_sse_events(response) -> list:
    """
    Parse Server-Sent Events from an httpx streaming response.

    Args:
        response: httpx Response with streaming content

    Returns:
        List of parsed SSE events as dicts with 'event' and 'data' keys
    """
    events = []
    current_event = {"event": None, "data": None}

    async for line in response.aiter_lines():
        line = line.strip()

        if not line:
            # Empty line = end of event
            if current_event["event"] or current_event["data"]:
                if current_event["data"]:
                    try:
                        current_event["data"] = json.loads(current_event["data"])
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                events.append(current_event)
                current_event = {"event": None, "data": None}
            continue

        if line.startswith("event:"):
            current_event["event"] = line[6:].strip()
        elif line.startswith("data:"):
            current_event["data"] = line[5:].strip()

    # Don't forget last event if stream didn't end with blank line
    if current_event["event"] or current_event["data"]:
        if current_event["data"]:
            try:
                current_event["data"] = json.loads(current_event["data"])
            except json.JSONDecodeError:
                pass
        events.append(current_event)

    return events


@pytest.fixture
def sse_parser():
    """Fixture providing the SSE parser function."""
    return parse_sse_events


# ============================================================================
# RRF Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_search_results() -> list:
    """
    Sample search results for RRF fusion testing.

    Each result has trigram_rank, vector_rank, and expected fused_score.
    """
    return [
        {
            "object_id": str(uuid.uuid4()),
            "object_type": "part",
            "payload": {"title": "Oil Filter", "part_number": "OF-001"},
            "trigram_rank": 1,
            "vector_rank": 3,
            "trigram_score": 0.95,
            "vector_score": 0.82,
        },
        {
            "object_id": str(uuid.uuid4()),
            "object_type": "part",
            "payload": {"title": "Air Filter", "part_number": "AF-001"},
            "trigram_rank": 2,
            "vector_rank": 1,
            "trigram_score": 0.88,
            "vector_score": 0.91,
        },
        {
            "object_id": str(uuid.uuid4()),
            "object_type": "inventory",
            "payload": {"title": "Filter Housing", "sku": "FH-001"},
            "trigram_rank": 3,
            "vector_rank": 2,
            "trigram_score": 0.75,
            "vector_score": 0.87,
        },
    ]


@pytest.fixture
def rrf_k_constant() -> int:
    """RRF smoothing constant K=60 as used in production."""
    return 60


# ============================================================================
# Entity ID Fixtures for RLS Testing
# ============================================================================

@pytest.fixture
def entity_ids_yacht_a() -> Dict[str, str]:
    """
    Entity IDs that belong to Yacht A.

    Used for RLS isolation testing.
    """
    return {
        "part_id": "11111111-1111-1111-1111-111111111111",
        "equipment_id": "22222222-2222-2222-2222-222222222222",
        "work_order_id": "33333333-3333-3333-3333-333333333333",
        "document_id": "44444444-4444-4444-4444-444444444444",
    }


@pytest.fixture
def entity_ids_yacht_b() -> Dict[str, str]:
    """
    Entity IDs that belong to Yacht B.

    Used for cross-tenant access testing.
    """
    return {
        "part_id": "aaaaaaaa-1111-1111-1111-111111111111",
        "equipment_id": "bbbbbbbb-2222-2222-2222-222222222222",
        "work_order_id": "cccccccc-3333-3333-3333-333333333333",
        "document_id": "dddddddd-4444-4444-4444-444444444444",
    }


# ============================================================================
# Test Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Set up test environment variables.

    Runs automatically for all tests.
    """
    # Set test-specific env vars if not already set
    test_env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "WARNING",
        "RERANKER_ENABLED": "false",  # Disable reranker for faster tests
    }

    for key, value in test_env_vars.items():
        if not os.getenv(key):
            monkeypatch.setenv(key, value)


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires DB)"
    )
    config.addinivalue_line(
        "markers", "production: mark test as production smoke test"
    )
    config.addinivalue_line(
        "markers", "rls: mark test as RLS isolation test"
    )
    config.addinivalue_line(
        "markers", "sse: mark test as SSE streaming test"
    )
    config.addinivalue_line(
        "markers", "rrf: mark test as RRF fusion math test"
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Constants
    "TEST_YACHT_A_ID",
    "TEST_YACHT_B_ID",
    "TEST_USER_A_ID",
    "TEST_USER_B_ID",
    "API_BASE_URL",
    "LOCAL_API_BASE_URL",
    # Classes
    "TestUser",
    # Token generators
    "generate_test_jwt",
    "generate_expired_jwt",
    "generate_invalid_signature_jwt",
    # Helpers
    "parse_sse_events",
]
