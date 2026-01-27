"""
Helper functions and data classes for Inventory Lens tests.
Lens: Inventory Item Lens v1.2 GOLD
"""
from uuid import UUID, uuid4
from dataclasses import dataclass
from typing import Optional


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
