# LAW 17: In-Memory PyTest with httpx.AsyncClient

**Status:** ✅ Implemented
**Date:** 2026-02-23
**Location:** `apps/api/tests/conftest.py`

## Overview

LAW 17 rewrites the PyTest infrastructure to test FastAPI routes in-memory without requiring a running uvicorn server. Tests now communicate directly with the FastAPI app via `httpx.AsyncClient`, making them faster, more reliable, and easier to run in any environment.

## Key Changes

### 1. Import the FastAPI App

**File:** `apps/api/tests/conftest.py`

```python
# Import the FastAPI app for in-memory testing
from pipeline_service import app
import httpx
```

### 2. Updated `async_client` Fixture

**Before:**
```python
@pytest_asyncio.fixture
async def async_client():
    async with httpx.AsyncClient(
        base_url=LOCAL_API_BASE_URL,  # ❌ Requires running server
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=True,
    ) as client:
        yield client
```

**After:**
```python
@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client that tests the FastAPI app in-memory."""
    async with httpx.AsyncClient(
        app=app,  # ✅ In-memory testing
        base_url="http://test",
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=True,
    ) as client:
        yield client
```

### 3. New `authenticated_client` Fixture

**Added:**
```python
@pytest_asyncio.fixture
async def authenticated_client(async_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """Client with valid JWT token in headers for Yacht A."""
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
```

### 4. Updated Test Files

**File:** `apps/api/tests/test_sse_streaming.py`

Removed `pytest.skip("Requires local API server")` from:
- `test_real_sse_endpoint`
- `test_invalid_jwt_returns_401`

These tests now run in-memory by default.

## Benefits

### 🚀 Faster Tests
- No server startup/shutdown overhead
- No network latency
- Tests run in milliseconds instead of seconds

### 🔒 More Reliable
- No port conflicts
- No "connection refused" errors
- No race conditions with server startup

### 🛠️ Easier Development
- No need to start uvicorn manually
- Works in any environment (local, CI/CD, Docker)
- Easier to debug (direct function calls)

### 📦 Better CI/CD
- No need to manage server processes
- Faster CI pipeline execution
- Fewer flaky tests

## Usage Examples

### Basic Test (Unauthenticated)
```python
@pytest.mark.asyncio
async def test_health_endpoint(async_client: httpx.AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Authenticated Test (Pre-configured)
```python
@pytest.mark.asyncio
async def test_protected_route(authenticated_client: httpx.AsyncClient):
    response = await authenticated_client.get("/api/f1/search/stream", params={"q": "test"})
    assert response.status_code == 200
```

### Custom JWT Test
```python
@pytest.mark.asyncio
async def test_yacht_b_access(async_client: httpx.AsyncClient, jwt_yacht_b: str):
    headers = {"Authorization": f"Bearer {jwt_yacht_b}"}
    response = await async_client.get("/api/f1/search/stream", headers=headers, params={"q": "test"})
    assert response.status_code == 200
```

### Streaming Test
```python
@pytest.mark.asyncio
async def test_sse_stream(authenticated_client: httpx.AsyncClient):
    async with authenticated_client.stream(
        "GET",
        "/api/f1/search/stream",
        params={"q": "oil filter"}
    ) as response:
        assert "text/event-stream" in response.headers.get("content-type", "")

        async for line in response.aiter_lines():
            if line.startswith("event:"):
                print(f"Received: {line}")
```

## Available Fixtures

### Client Fixtures
- **`async_client`**: Basic client without authentication
- **`authenticated_client`**: Client with JWT for Yacht A (TEST_USER_A_ID)
- **`production_client`**: Client pointing at real production API (use with caution)

### Authentication Fixtures
- **`jwt_yacht_a`**: Valid JWT token string for Yacht A
- **`jwt_yacht_b`**: Valid JWT token string for Yacht B
- **`jwt_expired`**: Expired JWT token for testing expiration handling
- **`jwt_invalid_signature`**: JWT with invalid signature for testing auth failures

### User Fixtures
- **`user_yacht_a`**: TestUser object for Yacht A
- **`user_yacht_b`**: TestUser object for Yacht B

### Context Fixtures
- **`auth_context_yacht_a`**: Pre-built auth context dict for Yacht A
- **`auth_context_yacht_b`**: Pre-built auth context dict for Yacht B

## Migration Guide

### Migrating Existing Tests

**Before (Server Required):**
```python
@pytest.mark.asyncio
async def test_endpoint(async_client):
    pytest.skip("Requires local API server")  # ❌ Remove this

    response = await async_client.get(
        "http://localhost:8000/api/endpoint"  # ❌ Full URL
    )
    assert response.status_code == 200
```

**After (In-Memory):**
```python
@pytest.mark.asyncio
async def test_endpoint(async_client):
    # ✅ No skip needed

    response = await async_client.get(
        "/api/endpoint"  # ✅ Relative URL
    )
    assert response.status_code == 200
```

### Checklist for Migration

1. ✅ Remove `pytest.skip("Requires local API server")` lines
2. ✅ Change full URLs to relative URLs (starts with `/`)
3. ✅ Use `authenticated_client` fixture for protected routes
4. ✅ Keep all other test logic unchanged
5. ✅ Run tests with: `pytest apps/api/tests/ -v --asyncio-mode=auto`

## Requirements

### Dependencies
```bash
# Required for LAW 17
pip install httpx
pip install pytest-asyncio
pip install 'websockets>=12.0'  # For Supabase realtime client
```

### Environment Variables
```bash
# Optional - uses test defaults if not set
export TEST_JWT_SECRET="test-jwt-secret-for-unit-tests-only"
export ENVIRONMENT="test"
export LOG_LEVEL="WARNING"
```

## Troubleshooting

### ModuleNotFoundError: websockets.asyncio

**Problem:** Missing websockets dependency version 12.0+

**Solution:**
```bash
pip install 'websockets>=12.0'
# or
uv pip install 'websockets>=12.0'
```

### Tests Fail with "No module named 'pipeline_service'"

**Problem:** Python path not set correctly

**Solution:**
```bash
# Run from the api directory
cd apps/api
pytest tests/ -v
```

### Authentication Failures

**Problem:** JWT secret mismatch

**Solution:**
```python
# Ensure TEST_JWT_SECRET matches what the middleware expects
# Or mock the auth middleware for unit tests
from unittest.mock import patch

@patch('middleware.auth.get_authenticated_user')
async def test_with_mock_auth(mock_auth, async_client):
    mock_auth.return_value = {"user_id": "test-123", "yacht_id": "test-yacht"}
    response = await async_client.get("/protected-route")
    assert response.status_code == 200
```

## Test Execution

### Run All Tests
```bash
cd apps/api
pytest tests/ -v --asyncio-mode=auto
```

### Run Specific Test File
```bash
pytest tests/test_sse_streaming.py -v
```

### Run Specific Test
```bash
pytest tests/test_sse_streaming.py::TestSSEIntegration::test_real_sse_endpoint -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

## Files Modified

### Created
- `apps/api/tests/test_in_memory_example.py` - Example tests demonstrating LAW 17
- `apps/api/tests/LAW_17_IMPLEMENTATION.md` - This documentation

### Modified
- `apps/api/tests/conftest.py`:
  - Added `from pipeline_service import app`
  - Updated `async_client` fixture to use `app=app`
  - Added new `authenticated_client` fixture
  - Added dependency check with helpful error message

- `apps/api/tests/test_sse_streaming.py`:
  - Removed `pytest.skip("Requires local API server")` from 2 tests
  - Updated docstrings to reference LAW 17

## Future Enhancements

### Potential Improvements
1. **Database Fixtures**: Add fixtures for database setup/teardown
2. **Mock Supabase**: Create comprehensive Supabase mock for unit tests
3. **Snapshot Testing**: Add snapshot testing for API responses
4. **Performance Tests**: Add performance benchmarks using in-memory client
5. **Test Factories**: Add factory fixtures for common test data

### Integration with Other Systems
- Can be integrated with GitHub Actions for CI
- Compatible with pytest-xdist for parallel test execution
- Works with pytest-cov for coverage reporting
- Can be used with pytest-benchmark for performance testing

## References

- [httpx Documentation](https://www.python-httpx.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [LAW 17 Specification](../../docs/LAWS.md#law-17)

## Verification

To verify LAW 17 is working correctly:

```bash
# 1. Check conftest imports successfully
cd apps/api
python3 -c "import sys; sys.path.insert(0, 'tests'); import conftest; print('✅ LAW 17 configured')"

# 2. Run example tests
pytest tests/test_in_memory_example.py -v

# 3. Run all tests
pytest tests/ -v --asyncio-mode=auto

# 4. Check test collection
pytest tests/ --collect-only
```

---

**Implementation completed:** 2026-02-23
**Next steps:** Install `websockets>=12.0` and run tests to verify functionality
