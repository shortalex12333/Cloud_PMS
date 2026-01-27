"""
Pytest fixtures for Inventory Lens tests.
Lens: Inventory Item Lens v1.2 GOLD
"""

import os
import pytest
import asyncio
import asyncpg
from uuid import UUID
from dataclasses import dataclass
from typing import Optional

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:postgres@localhost:54322/postgres")
TEST_YACHT_A_ID = UUID(os.getenv("TEST_YACHT_A_ID", "00000000-0000-0000-0000-000000000001"))
TEST_YACHT_B_ID = UUID(os.getenv("TEST_YACHT_B_ID", "00000000-0000-0000-0000-000000000002"))


@dataclass
class TestUser:
    """Test user context."""
    id: UUID
    yacht_id: UUID
    role: str
    email: str


@dataclass
class TestPart:
    """Test part entity."""
    id: UUID
    yacht_id: UUID
    name: str
    quantity_on_hand: int
    minimum_quantity: int = 0
    deleted_at: Optional[str] = None


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
    """Ensure test yacht A exists."""
    await db.execute("""
        INSERT INTO yacht_registry (id, name, created_at)
        VALUES ($1, 'Test Yacht A', NOW())
        ON CONFLICT (id) DO NOTHING
    """, TEST_YACHT_A_ID)
    return TEST_YACHT_A_ID


@pytest.fixture
async def yacht_b(db) -> UUID:
    """Ensure test yacht B exists."""
    await db.execute("""
        INSERT INTO yacht_registry (id, name, created_at)
        VALUES ($1, 'Test Yacht B', NOW())
        ON CONFLICT (id) DO NOTHING
    """, TEST_YACHT_B_ID)
    return TEST_YACHT_B_ID


@pytest.fixture
async def deckhand_a(db, yacht_a) -> TestUser:
    """Create deckhand user for yacht A."""
    user_id = UUID("00000000-0000-0000-0000-000000000010")
    await db.execute("""
        INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
        VALUES ($1, $2, 'deckhand_a@test.com', 'Deckhand A', true)
        ON CONFLICT (id) DO UPDATE SET yacht_id = $2
    """, user_id, yacht_a)
    await db.execute("""
        INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES ($1, $2, 'deckhand', true)
        ON CONFLICT (user_id, yacht_id) DO UPDATE SET role = 'deckhand'
    """, user_id, yacht_a)
    return TestUser(id=user_id, yacht_id=yacht_a, role="deckhand", email="deckhand_a@test.com")


@pytest.fixture
async def deckhand_b(db, yacht_b) -> TestUser:
    """Create deckhand user for yacht B."""
    user_id = UUID("00000000-0000-0000-0000-000000000011")
    await db.execute("""
        INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
        VALUES ($1, $2, 'deckhand_b@test.com', 'Deckhand B', true)
        ON CONFLICT (id) DO UPDATE SET yacht_id = $2
    """, user_id, yacht_b)
    await db.execute("""
        INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES ($1, $2, 'deckhand', true)
        ON CONFLICT (user_id, yacht_id) DO UPDATE SET role = 'deckhand'
    """, user_id, yacht_b)
    return TestUser(id=user_id, yacht_id=yacht_b, role="deckhand", email="deckhand_b@test.com")


@pytest.fixture
async def captain(db, yacht_a) -> TestUser:
    """Create captain user for yacht A."""
    user_id = UUID("00000000-0000-0000-0000-000000000020")
    await db.execute("""
        INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
        VALUES ($1, $2, 'captain@test.com', 'Captain Test', true)
        ON CONFLICT (id) DO UPDATE SET yacht_id = $2
    """, user_id, yacht_a)
    await db.execute("""
        INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES ($1, $2, 'captain', true)
        ON CONFLICT (user_id, yacht_id) DO UPDATE SET role = 'captain'
    """, user_id, yacht_a)
    return TestUser(id=user_id, yacht_id=yacht_a, role="captain", email="captain@test.com")


@pytest.fixture
async def manager(db, yacht_a) -> TestUser:
    """Create manager user for yacht A."""
    user_id = UUID("00000000-0000-0000-0000-000000000030")
    await db.execute("""
        INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
        VALUES ($1, $2, 'manager@test.com', 'Manager Test', true)
        ON CONFLICT (id) DO UPDATE SET yacht_id = $2
    """, user_id, yacht_a)
    await db.execute("""
        INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES ($1, $2, 'manager', true)
        ON CONFLICT (user_id, yacht_id) DO UPDATE SET role = 'manager'
    """, user_id, yacht_a)
    return TestUser(id=user_id, yacht_id=yacht_a, role="manager", email="manager@test.com")


@pytest.fixture
async def guest(db, yacht_a) -> TestUser:
    """Create guest user (non-operational) for yacht A."""
    user_id = UUID("00000000-0000-0000-0000-000000000040")
    await db.execute("""
        INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
        VALUES ($1, $2, 'guest@test.com', 'Guest Test', true)
        ON CONFLICT (id) DO UPDATE SET yacht_id = $2
    """, user_id, yacht_a)
    await db.execute("""
        INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES ($1, $2, 'guest', true)
        ON CONFLICT (user_id, yacht_id) DO UPDATE SET role = 'guest'
    """, user_id, yacht_a)
    return TestUser(id=user_id, yacht_id=yacht_a, role="guest", email="guest@test.com")


@dataclass
class TestStock:
    """Test stock entity (per-location inventory)."""
    id: UUID
    yacht_id: UUID
    part_id: UUID
    location: str
    quantity: int
    deleted_at: Optional[str] = None


async def create_test_part(db, yacht_id: UUID, name: str, quantity: int = 10, **kwargs) -> TestPart:
    """Helper to create a test part (catalog entry only, no stock)."""
    from uuid import uuid4
    part_id = uuid4()
    await db.execute("""
        INSERT INTO pms_parts (id, yacht_id, name, quantity_on_hand, minimum_quantity, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    """, part_id, yacht_id, name, quantity, kwargs.get("minimum_quantity", 0))
    return TestPart(
        id=part_id,
        yacht_id=yacht_id,
        name=name,
        quantity_on_hand=quantity,
        minimum_quantity=kwargs.get("minimum_quantity", 0)
    )


async def create_test_stock(db, yacht_id: UUID, part_id: UUID, location: str, quantity: int = 10) -> TestStock:
    """Helper to create a test stock record (per-location inventory)."""
    from uuid import uuid4
    stock_id = uuid4()
    await db.execute("""
        INSERT INTO pms_inventory_stock (id, yacht_id, part_id, location, quantity, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    """, stock_id, yacht_id, part_id, location, quantity)
    return TestStock(
        id=stock_id,
        yacht_id=yacht_id,
        part_id=part_id,
        location=location,
        quantity=quantity
    )


async def create_test_location(db, yacht_id: UUID, name: str) -> UUID:
    """Helper to create a test location."""
    from uuid import uuid4
    loc_id = uuid4()
    await db.execute("""
        INSERT INTO pms_part_locations (id, yacht_id, name, created_at)
        VALUES ($1, $2, $3, NOW())
    """, loc_id, yacht_id, name)
    return loc_id


async def set_user_context(db, user: TestUser):
    """Set JWT claims for RLS testing."""
    await db.execute("""
        SET LOCAL "request.jwt.claims" = $1
    """, f'{{"sub": "{user.id}"}}')
