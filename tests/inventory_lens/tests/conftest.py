"""
Pytest fixtures for Inventory Lens tests.
Lens: Inventory Item Lens v1.2 GOLD
"""

import os
import pytest
import asyncio
import asyncpg
from uuid import UUID

# Import helpers from helpers module
from .helpers import (
    TestUser,
    TestPart,
    TestStock,
    create_test_part,
    create_test_stock,
    create_test_location,
    set_user_context
)

# Re-export for test files
__all__ = [
    'TestUser',
    'TestPart',
    'TestStock',
    'create_test_part',
    'create_test_stock',
    'create_test_location',
    'set_user_context'
]

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set in .env.test")

TEST_YACHT_ID = os.getenv("TEST_YACHT_ID")
if not TEST_YACHT_ID:
    raise ValueError("TEST_YACHT_ID environment variable must be set in .env.test")

TEST_YACHT_A_ID = UUID(TEST_YACHT_ID)
TEST_YACHT_B_ID = UUID("00000000-0000-0000-0000-000000000002")  # Different yacht for isolation tests


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Create database connection pool."""
    pool = await asyncpg.create_pool(DATABASE_URL)
    yield pool
    await pool.close()


@pytest.fixture
async def db(db_pool):
    """Get database connection for a test."""
    async with db_pool.acquire() as conn:
        yield conn


@pytest.fixture
async def yacht_a(db) -> UUID:
    """Return test yacht A ID (already exists in staging)."""
    # Verify yacht exists
    result = await db.fetchval("SELECT id FROM yacht_registry WHERE id = $1", TEST_YACHT_A_ID)
    if not result:
        raise ValueError(f"Test yacht {TEST_YACHT_A_ID} not found in yacht_registry")
    return TEST_YACHT_A_ID


@pytest.fixture
async def yacht_b(db) -> UUID:
    """Return test yacht B ID (for isolation tests - different yacht)."""
    # For isolation tests, use a different yacht ID
    # This yacht likely doesn't exist, but that's OK for isolation tests
    return TEST_YACHT_B_ID


@pytest.fixture
async def deckhand_a(db, yacht_a) -> TestUser:
    """Use existing crew user for yacht A."""
    user_id = UUID("6d807a66-955c-49c4-b767-8a6189c2f422")  # crew.tenant@alex-short.com
    return TestUser(id=user_id, yacht_id=yacht_a, role="crew", email="crew.tenant@alex-short.com")


@pytest.fixture
async def deckhand_b(db, yacht_b) -> TestUser:
    """Use a crew user for yacht B (for isolation tests)."""
    # This user doesn't exist in yacht B, which is perfect for isolation testing
    user_id = UUID("00000000-0000-0000-0000-000000000011")
    return TestUser(id=user_id, yacht_id=yacht_b, role="crew", email="crew_b@test.com")


@pytest.fixture
async def captain(db, yacht_a) -> TestUser:
    """Use existing captain user for yacht A."""
    user_id = UUID("5af9d61d-9b2e-4db4-a54c-a3c95eec70e5")  # captain.tenant@alex-short.com
    return TestUser(id=user_id, yacht_id=yacht_a, role="captain", email="captain.tenant@alex-short.com")


@pytest.fixture
async def manager(db, yacht_a) -> TestUser:
    """Use existing captain user as manager (captain is a manager role)."""
    user_id = UUID("5af9d61d-9b2e-4db4-a54c-a3c95eec70e5")  # captain.tenant@alex-short.com
    return TestUser(id=user_id, yacht_id=yacht_a, role="captain", email="captain.tenant@alex-short.com")


@pytest.fixture
async def guest(db, yacht_a) -> TestUser:
    """Create a non-operational guest user (no role in auth_users_roles)."""
    # Use a UUID that doesn't have a role assigned
    user_id = UUID("00000000-0000-0000-0000-000000000040")
    return TestUser(id=user_id, yacht_id=yacht_a, role="guest", email="guest@test.com")


# Helper functions imported from helpers.py above