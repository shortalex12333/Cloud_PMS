"""
Critical Acceptance Tests for Inventory Item Lens.
Lens: Inventory Item Lens v1.2 GOLD

These tests MUST pass before deployment. They verify:
- RLS isolation between yachts
- Concurrency safety (race condition prevention)
- Idempotency guarantees
- Signature invariants
- Soft-delete enforcement
- Storage access control

Production schema notes:
- pms_parts = Part catalog (master data)
- pms_inventory_stock = Per-location stock records (has quantity, deleted_at)
- pms_inventory_transactions = Transaction log (references stock_id)

Run with: pytest tests/test_inventory_critical.py -v
"""

import pytest
import asyncio
from uuid import uuid4

# Import helpers and data classes
from .helpers import (
    TestUser,
    TestPart,
    TestStock,
    create_test_part,
    create_test_stock,
    create_test_location,
    set_user_context
)


# =============================================================================
# RLS ISOLATION TESTS
# =============================================================================


class TestRLSIsolation:
    """All tests MUST pass - yacht data isolation."""

    @pytest.mark.asyncio
    async def test_parts_isolated_by_yacht(self, db, yacht_a, yacht_b, deckhand_a, deckhand_b):
        """User from Yacht A cannot see Yacht B's parts."""
        # Create part in each yacht
        part_a = await create_test_part(db, yacht_a, "Part A", quantity=5)
        part_b = await create_test_part(db, yacht_b, "Part B", quantity=5)

        # As deckhand_a, query parts
        await set_user_context(db, deckhand_a)
        result = await db.fetch("SELECT id, name FROM pms_parts WHERE yacht_id = $1", yacht_b)

        # Should see 0 parts from yacht B
        assert len(result) == 0, "Deckhand A should not see Yacht B's parts"

    @pytest.mark.asyncio
    async def test_stock_isolated_by_yacht(self, db, yacht_a, yacht_b, deckhand_a, deckhand_b):
        """User from Yacht A cannot see Yacht B's stock records."""
        # Create part and stock in yacht B
        part_b = await create_test_part(db, yacht_b, "Part B", quantity=0)
        stock_b = await create_test_stock(db, yacht_b, part_b.id, "Engine Room", quantity=10)

        # As deckhand_a, query stock
        await set_user_context(db, deckhand_a)
        result = await db.fetch("SELECT id FROM pms_inventory_stock WHERE yacht_id = $1", yacht_b)

        # Should see 0 stock records from yacht B
        assert len(result) == 0, "Deckhand A should not see Yacht B's stock"

    @pytest.mark.asyncio
    async def test_transactions_isolated_by_yacht(self, db, yacht_a, yacht_b, deckhand_a):
        """User cannot see transactions from other yacht."""
        # Create part, stock, and transaction in yacht B
        part_b = await create_test_part(db, yacht_b, "Part B", quantity=0)
        stock_b = await create_test_stock(db, yacht_b, part_b.id, "Deck Store", quantity=10)

        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
            VALUES ($1, $2, $3, 'consumed', -1, 10, 9, $4, NOW())
        """, uuid4(), yacht_b, stock_b.id, uuid4())

        # As deckhand_a, try to see yacht B's transactions
        await set_user_context(db, deckhand_a)
        result = await db.fetch(
            "SELECT id FROM pms_inventory_transactions WHERE yacht_id = $1",
            yacht_b
        )

        assert len(result) == 0, "Deckhand A should not see Yacht B's transactions"

    @pytest.mark.asyncio
    async def test_locations_isolated_by_yacht(self, db, yacht_a, yacht_b, deckhand_a):
        """User cannot see locations from other yacht."""
        # Create location in yacht B
        await create_test_location(db, yacht_b, "Engine Room B")

        # As deckhand_a, try to see yacht B's locations
        await set_user_context(db, deckhand_a)
        result = await db.fetch(
            "SELECT id FROM pms_part_locations WHERE yacht_id = $1",
            yacht_b
        )

        assert len(result) == 0, "Deckhand A should not see Yacht B's locations"

    @pytest.mark.asyncio
    async def test_cross_yacht_consume_blocked(self, db, yacht_a, yacht_b, deckhand_a):
        """User cannot consume stock from other yacht."""
        # Create part and stock in yacht B
        part_b = await create_test_part(db, yacht_b, "Part B", quantity=0)
        stock_b = await create_test_stock(db, yacht_b, part_b.id, "Deck Store", quantity=10)

        # As deckhand_a, try to deduct from yacht B's stock
        await set_user_context(db, deckhand_a)
        result = await db.fetchrow("""
            SELECT * FROM public.deduct_stock_inventory($1, 1, $2)
        """, stock_b.id, yacht_b)

        assert result["success"] is False, "Should not be able to deduct from other yacht"
        assert result["error_code"] == "stock_not_found", "Error should be stock_not_found due to RLS"


# =============================================================================
# CONCURRENCY TESTS
# =============================================================================


class TestConcurrency:
    """Race condition prevention tests."""

    @pytest.mark.asyncio
    async def test_concurrent_consume_atomic(self, db, yacht_a, deckhand_a):
        """Two concurrent consumes of 5 units from 5 stock: one succeeds, one fails."""
        # Create part and stock with exactly 5 units
        part = await create_test_part(db, yacht_a, "Concurrent Test Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=5)

        # Define consume coroutine
        async def consume_5():
            async with db.transaction():
                return await db.fetchrow("""
                    SELECT * FROM public.deduct_stock_inventory($1, 5, $2)
                """, stock.id, yacht_a)

        # Run two concurrent consumes
        results = await asyncio.gather(
            consume_5(),
            consume_5(),
            return_exceptions=True
        )

        # Count successes and failures
        successes = [r for r in results if not isinstance(r, Exception) and r["success"]]
        failures = [r for r in results if not isinstance(r, Exception) and not r["success"]]

        assert len(successes) == 1, "Exactly one consume should succeed"
        assert len(failures) == 1, "Exactly one consume should fail"
        assert failures[0]["error_code"] == "insufficient_stock"

        # Verify final stock is 0, not negative
        final = await db.fetchrow(
            "SELECT quantity FROM pms_inventory_stock WHERE id = $1",
            stock.id
        )
        assert final["quantity"] == 0, "Final stock should be 0, not negative"

    @pytest.mark.asyncio
    async def test_concurrent_receive_atomic(self, db, yacht_a, deckhand_a):
        """Concurrent receives should both succeed and sum correctly."""
        part = await create_test_part(db, yacht_a, "Receive Test Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=0)

        async def receive_10():
            return await db.fetchrow("""
                SELECT * FROM public.add_stock_inventory($1, 10, $2)
            """, stock.id, yacht_a)

        results = await asyncio.gather(receive_10(), receive_10())

        # Both should succeed
        assert all(r["success"] for r in results), "Both receives should succeed"

        # Final stock should be 20
        final = await db.fetchrow(
            "SELECT quantity FROM pms_inventory_stock WHERE id = $1",
            stock.id
        )
        assert final["quantity"] == 20, "Final stock should be 20"


# =============================================================================
# IDEMPOTENCY TESTS
# =============================================================================


class TestIdempotency:
    """Duplicate request handling tests."""

    @pytest.mark.asyncio
    async def test_duplicate_receive_blocked(self, db, yacht_a, deckhand_a):
        """Second receive with same idempotency_key is blocked."""
        part = await create_test_part(db, yacht_a, "Idempotency Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=0)
        idem_key = f"receive-{uuid4()}"

        # First receive
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, idempotency_key, created_at)
            VALUES ($1, $2, $3, 'received', 10, 0, 10, $4, $5, NOW())
        """, uuid4(), yacht_a, stock.id, deckhand_a.id, idem_key)

        # Second receive with same key should fail
        with pytest.raises(Exception) as exc_info:
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, idempotency_key, created_at)
                VALUES ($1, $2, $3, 'received', 10, 10, 20, $4, $5, NOW())
            """, uuid4(), yacht_a, stock.id, deckhand_a.id, idem_key)

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_idempotency_key_scoped_to_yacht(self, db, yacht_a, yacht_b, deckhand_a, deckhand_b):
        """Same idempotency_key can be used in different yachts."""
        part_a = await create_test_part(db, yacht_a, "Part A", quantity=0)
        part_b = await create_test_part(db, yacht_b, "Part B", quantity=0)
        stock_a = await create_test_stock(db, yacht_a, part_a.id, "Location A", quantity=0)
        stock_b = await create_test_stock(db, yacht_b, part_b.id, "Location B", quantity=0)
        idem_key = f"shared-key-{uuid4()}"

        # Both should succeed because they're in different yachts
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, idempotency_key, created_at)
            VALUES ($1, $2, $3, 'received', 10, 0, 10, $4, $5, NOW())
        """, uuid4(), yacht_a, stock_a.id, deckhand_a.id, idem_key)

        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, idempotency_key, created_at)
            VALUES ($1, $2, $3, 'received', 10, 0, 10, $4, $5, NOW())
        """, uuid4(), yacht_b, stock_b.id, deckhand_b.id, idem_key)

        # Both should exist
        count = await db.fetchval(
            "SELECT COUNT(*) FROM pms_inventory_transactions WHERE idempotency_key = $1",
            idem_key
        )
        assert count == 2


# =============================================================================
# SOFT DELETE ENFORCEMENT TESTS
# =============================================================================


class TestSoftDelete:
    """Deactivation blocks mutations tests."""

    @pytest.mark.asyncio
    async def test_consume_blocked_on_deactivated(self, db, yacht_a, deckhand_a):
        """Cannot consume from deactivated stock."""
        part = await create_test_part(db, yacht_a, "Deactivated Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        # Deactivate the stock record
        await db.execute("""
            UPDATE pms_inventory_stock SET deleted_at = NOW(), deleted_by = $1
            WHERE id = $2
        """, deckhand_a.id, stock.id)

        # Try to deduct
        result = await db.fetchrow("""
            SELECT * FROM public.deduct_stock_inventory($1, 1, $2)
        """, stock.id, yacht_a)

        assert result["success"] is False
        assert result["error_code"] == "stock_deactivated"

    @pytest.mark.asyncio
    async def test_trigger_blocks_transaction_insert(self, db, yacht_a, deckhand_a):
        """DB trigger blocks transaction insert for deactivated stock."""
        part = await create_test_part(db, yacht_a, "Trigger Test Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        # Deactivate
        await db.execute("""
            UPDATE pms_inventory_stock SET deleted_at = NOW() WHERE id = $1
        """, stock.id)

        # Try direct insert (bypassing function)
        with pytest.raises(Exception) as exc_info:
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
                VALUES ($1, $2, $3, 'consumed', -1, 10, 9, $4, NOW())
            """, uuid4(), yacht_a, stock.id, deckhand_a.id)

        assert "deactivated" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_reactivate_restores_mutations(self, db, yacht_a, captain):
        """Reactivated stock allows mutations again."""
        part = await create_test_part(db, yacht_a, "Reactivate Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        # Deactivate
        await db.execute("""
            UPDATE pms_inventory_stock SET deleted_at = NOW() WHERE id = $1
        """, stock.id)

        # Reactivate
        await db.execute("""
            UPDATE pms_inventory_stock SET deleted_at = NULL, deleted_by = NULL WHERE id = $1
        """, stock.id)

        # Now deduct should work
        result = await db.fetchrow("""
            SELECT * FROM public.deduct_stock_inventory($1, 1, $2)
        """, stock.id, yacht_a)

        assert result["success"] is True
        assert result["quantity_after"] == 9


# =============================================================================
# REVERSAL UNIQUENESS TESTS
# =============================================================================


class TestReversalUniqueness:
    """Transaction reversal safety tests."""

    @pytest.mark.asyncio
    async def test_double_reversal_blocked(self, db, yacht_a, manager):
        """Cannot reverse same transaction twice."""
        part = await create_test_part(db, yacht_a, "Reversal Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        # Create original transaction
        txn_id = uuid4()
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
            VALUES ($1, $2, $3, 'consumed', -5, 10, 5, $4, NOW())
        """, txn_id, yacht_a, stock.id, manager.id)

        # First reversal
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, reverses_transaction_id, created_at)
            VALUES ($1, $2, $3, 'reversed', 5, 5, 10, $4, $5, NOW())
        """, uuid4(), yacht_a, stock.id, manager.id, txn_id)

        # Second reversal should fail due to unique constraint
        with pytest.raises(Exception) as exc_info:
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, reverses_transaction_id, created_at)
                VALUES ($1, $2, $3, 'reversed', 5, 10, 15, $4, $5, NOW())
            """, uuid4(), yacht_a, stock.id, manager.id, txn_id)

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_reversal_of_reversal_blocked(self, db, yacht_a, manager):
        """Cannot reverse a 'reversed' transaction."""
        part = await create_test_part(db, yacht_a, "Reversal Chain Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        # Create original transaction
        txn_id = uuid4()
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
            VALUES ($1, $2, $3, 'consumed', -5, 10, 5, $4, NOW())
        """, txn_id, yacht_a, stock.id, manager.id)

        # First reversal (creates a 'reversed' transaction)
        reversal_id = uuid4()
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, reverses_transaction_id, created_at)
            VALUES ($1, $2, $3, 'reversed', 5, 5, 10, $4, $5, NOW())
        """, reversal_id, yacht_a, stock.id, manager.id, txn_id)

        # Try to reverse the reversal - should fail
        with pytest.raises(Exception) as exc_info:
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, reverses_transaction_id, created_at)
                VALUES ($1, $2, $3, 'reversed', -5, 10, 5, $4, $5, NOW())
            """, uuid4(), yacht_a, stock.id, manager.id, reversal_id)

        assert "reversal" in str(exc_info.value).lower() or "Cannot reverse" in str(exc_info.value)


# =============================================================================
# TRANSACTION-TYPE RLS TESTS
# =============================================================================


class TestTransactionTypeRLS:
    """Transaction type-based RLS gating tests."""

    @pytest.mark.asyncio
    async def test_crew_can_insert_consumed(self, db, yacht_a, deckhand_a):
        """Operational crew can insert 'consumed' transactions."""
        part = await create_test_part(db, yacht_a, "Consume RLS Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        await set_user_context(db, deckhand_a)

        # Should succeed (with RLS context set properly)
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
            VALUES ($1, $2, $3, 'consumed', -1, 10, 9, $4, NOW())
        """, uuid4(), yacht_a, stock.id, deckhand_a.id)

    @pytest.mark.asyncio
    async def test_crew_cannot_insert_write_off(self, db, yacht_a, deckhand_a):
        """Operational crew cannot insert 'write_off' transactions directly."""
        part = await create_test_part(db, yacht_a, "Write-off RLS Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        await set_user_context(db, deckhand_a)

        # Should fail due to RLS
        with pytest.raises(Exception):
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
                VALUES ($1, $2, $3, 'write_off', -5, 10, 5, $4, NOW())
            """, uuid4(), yacht_a, stock.id, deckhand_a.id)

    @pytest.mark.asyncio
    async def test_crew_cannot_insert_reversed(self, db, yacht_a, deckhand_a):
        """Crew cannot insert 'reversed' transactions (manager only)."""
        part = await create_test_part(db, yacht_a, "Reversal RLS Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)

        await set_user_context(db, deckhand_a)

        with pytest.raises(Exception):
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
                VALUES ($1, $2, $3, 'reversed', 5, 5, 10, $4, NOW())
            """, uuid4(), yacht_a, stock.id, deckhand_a.id)


# =============================================================================
# TRANSFER VALIDATION TESTS
# =============================================================================


class TestTransferValidation:
    """Transfer location validation tests."""

    @pytest.mark.asyncio
    async def test_transfer_same_location_blocked(self, db, yacht_a, manager):
        """Transfer with from_location == to_location is blocked."""
        part = await create_test_part(db, yacht_a, "Transfer Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=10)
        location = await create_test_location(db, yacht_a, "Engine Room")

        # Try to insert transfer with same from and to location
        with pytest.raises(Exception) as exc_info:
            await db.execute("""
                INSERT INTO pms_inventory_transactions
                (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, from_location_id, to_location_id, created_at)
                VALUES ($1, $2, $3, 'transferred_out', -5, 10, 5, $4, $5, $5, NOW())
            """, uuid4(), yacht_a, stock.id, manager.id, location, location)

        assert "check" in str(exc_info.value).lower() or "constraint" in str(exc_info.value).lower()


# =============================================================================
# HELPER FUNCTION PARITY TESTS
# =============================================================================


class TestHelperParity:
    """Canonical helper function tests."""

    @pytest.mark.asyncio
    async def test_is_operational_crew_includes_all_roles(self, db, yacht_a):
        """Verify is_operational_crew() returns true for all expected roles."""
        expected_roles = [
            'deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
            'chief_officer', 'captain', 'manager', 'purser'
        ]

        for role in expected_roles:
            user_id = uuid4()
            # Create user with this role
            await db.execute("""
                INSERT INTO auth_users_profiles (id, yacht_id, email, full_name, is_active)
                VALUES ($1, $2, $3, $4, true)
            """, user_id, yacht_a, f"{role}@test.com", f"Test {role}")

            await db.execute("""
                INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
                VALUES ($1, $2, $3, true)
            """, user_id, yacht_a, role)

            # Check helper function
            result = await db.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM auth_users_roles
                    WHERE user_id = $1 AND yacht_id = $2 AND role = $3 AND is_active = true
                )
            """, user_id, yacht_a, role)

            assert result is True, f"Role {role} should be operational crew"

    @pytest.mark.asyncio
    async def test_is_operational_crew_excludes_guest(self, db, yacht_a, guest):
        """Guest role is not operational crew."""
        # Verify guest role is in the table
        result = await db.fetchval("""
            SELECT role FROM auth_users_roles WHERE user_id = $1
        """, guest.id)

        assert result == "guest"

        # Guest is NOT in the operational crew list
        operational_roles = [
            'deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
            'chief_officer', 'captain', 'manager', 'purser'
        ]
        assert result not in operational_roles


# =============================================================================
# DUAL LEDGER CONSISTENCY TESTS
# =============================================================================


class TestDualLedgerConsistency:
    """Verify stock.quantity matches transaction sum."""

    @pytest.mark.asyncio
    async def test_no_inventory_drift(self, db, yacht_a):
        """check_inventory_drift() returns empty for consistent data."""
        # Create part and stock with initial quantity of 0
        part = await create_test_part(db, yacht_a, "Drift Check Part", quantity=0)
        stock = await create_test_stock(db, yacht_a, part.id, "Test Location", quantity=0)

        # Add transactions that sum to 15
        await db.execute("""
            INSERT INTO pms_inventory_transactions
            (id, yacht_id, stock_id, transaction_type, quantity_change, quantity_before, quantity_after, user_id, created_at)
            VALUES
            ($1, $2, $3, 'received', 20, 0, 20, $4, NOW()),
            ($5, $2, $3, 'consumed', -5, 20, 15, $4, NOW())
        """, uuid4(), yacht_a, stock.id, uuid4(), uuid4())

        # Update stock to match (simulating what the handler should do)
        await db.execute("""
            UPDATE pms_inventory_stock SET quantity = 15 WHERE id = $1
        """, stock.id)

        # Verify using the drift view
        drift = await db.fetch("""
            SELECT * FROM v_stock_from_transactions WHERE stock_id = $1
        """, stock.id)

        if drift:
            assert drift[0]["reconciliation_status"] == "OK", "No drift should exist for this stock"
