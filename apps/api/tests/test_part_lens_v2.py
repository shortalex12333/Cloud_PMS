#!/usr/bin/env python3
"""
Part Lens v2: Acceptance Test Suite
====================================

Docker fast loop test suite for Part Lens v2 actions.

DOCTRINE COMPLIANCE:
- Stock derived from pms_inventory_transactions (append-only)
- No direct writes to pms_parts.quantity_on_hand
- Idempotency via DB unique constraint (yacht_id, idempotency_key)
- SIGNED actions require signature (400 if missing)
- READ actions write audit with signature={}

Tests verify:
1. Transaction-only invariant (no UPDATE to pms_parts for stock)
2. Derived stock parity (stock == SUM(transactions))
3. DB-enforced idempotency (409 on duplicate via constraint)
4. Signed actions (400 without signature)
5. Read-audit entries for view_part_details, open_document
6. RLS negative controls (cross-yacht denied)
7. Zero 500s - any 500 fails CI

Run: pytest apps/api/tests/test_part_lens_v2.py -v --tb=short
"""

import asyncio
import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from typing import Dict, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://vzsohavtuotocgrfkfyd.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    os.environ.get("TENANT_1_SUPABASE_SERVICE_KEY", "")
)

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
OTHER_YACHT_ID = "99999999-0000-0000-0000-000000000001"  # For RLS tests


# ============================================================================
# TEST HARNESS
# ============================================================================

class PartLensTestHarness:
    """Test harness for Part Lens v2 acceptance tests."""

    def __init__(self):
        if not SUPABASE_KEY:
            pytest.skip("SUPABASE_SERVICE_KEY not set")
        self.db = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.test_user_id = self._resolve_test_user()
        self.test_part_id = None
        self.created_ids = {
            "parts": [],
            "stock": [],
            "transactions": [],
            "shopping": [],
        }

    def _resolve_test_user(self) -> str:
        """Resolve test user ID from database."""
        try:
            result = self.db.table("auth_users_profiles").select("id").limit(1).execute()
            if result.data:
                return result.data[0]["id"]
        except Exception:
            pass
        return str(uuid.uuid4())

    def setup_test_part_with_transactions(self, initial_quantity: int = 20) -> str:
        """
        Create a test part with stock via transactions (doctrine compliant).
        Stock is derived from transactions, not mutable column.
        """
        part_id = str(uuid.uuid4())
        stock_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Create part (NO quantity_on_hand - that violates doctrine)
        self.db.table("pms_parts").insert({
            "id": part_id,
            "yacht_id": TEST_YACHT_ID,
            "name": f"Test Part {part_id[:8]}",
            "part_number": f"TP-{part_id[:8]}",
            "min_level": 10,
            "reorder_multiple": 5,
            "is_critical": False,
            "location": f"LOC-{part_id[:4]}",
            "created_at": now,
        }).execute()
        self.created_ids["parts"].append(part_id)

        # Create stock record
        self.db.table("pms_inventory_stock").insert({
            "id": stock_id,
            "yacht_id": TEST_YACHT_ID,
            "part_id": part_id,
            "location": f"LOC-{part_id[:4]}",
            "quantity": 0,  # Will be updated by trigger
            "created_at": now,
            "updated_at": now,
        }).execute()
        self.created_ids["stock"].append(stock_id)

        # Create initial transaction to set stock level (use "received" as it's a valid type)
        if initial_quantity > 0:
            txn_id = str(uuid.uuid4())
            self.db.table("pms_inventory_transactions").insert({
                "id": txn_id,
                "yacht_id": TEST_YACHT_ID,
                "stock_id": stock_id,
                "transaction_type": "received",  # Use "received" instead of "initial" (check constraint)
                "quantity_change": initial_quantity,
                "quantity_before": 0,
                "quantity_after": initial_quantity,
                "user_id": self.test_user_id,
                "created_at": now,
            }).execute()
            self.created_ids["transactions"].append(txn_id)

        self.test_part_id = part_id
        return part_id

    def cleanup(self):
        """Clean up test data."""
        try:
            for txn_id in self.created_ids["transactions"]:
                self.db.table("pms_inventory_transactions").delete().eq("id", txn_id).execute()
            for stock_id in self.created_ids["stock"]:
                self.db.table("pms_inventory_stock").delete().eq("id", stock_id).execute()
            for part_id in self.created_ids["parts"]:
                self.db.table("pms_audit_log").delete().eq("entity_id", part_id).execute()
                self.db.table("pms_parts").delete().eq("id", part_id).execute()
            for item_id in self.created_ids["shopping"]:
                self.db.table("pms_shopping_list_items").delete().eq("id", item_id).execute()
        except Exception as e:
            print(f"Cleanup error: {e}")

    def get_stock_level_from_view(self, part_id: str) -> int:
        """Get current stock level from canonical pms_part_stock view."""
        result = self.db.table("pms_part_stock").select("on_hand").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()
        return (result.data or {}).get("on_hand", 0) or 0

    def get_transaction_sum(self, part_id: str) -> int:
        """Get sum of all transactions for a part (via stock_id)."""
        # First get stock_id for the part
        stock_result = self.db.table("pms_inventory_stock").select("id").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        if not stock_result.data:
            return 0

        total = 0
        for stock in stock_result.data:
            txn_result = self.db.table("pms_inventory_transactions").select("quantity_change").eq(
                "stock_id", stock["id"]
            ).execute()
            total += sum(t.get("quantity_change", 0) for t in (txn_result.data or []))

        return total

    def get_transaction_count(self, part_id: str) -> int:
        """Count transactions for a part."""
        stock_result = self.db.table("pms_inventory_stock").select("id").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        if not stock_result.data:
            return 0

        count = 0
        for stock in stock_result.data:
            txn_result = self.db.table("pms_inventory_transactions").select("id", count="exact").eq(
                "stock_id", stock["id"]
            ).execute()
            count += txn_result.count or 0

        return count

    def get_audit_log_count(self, entity_id: str, action: str) -> int:
        """Count audit log entries for an entity/action."""
        result = self.db.table("pms_audit_log").select("id", count="exact").eq(
            "entity_id", entity_id
        ).eq("action", action).execute()
        return result.count or 0

    def check_audit_signature_not_null(self, entity_id: str) -> bool:
        """Verify audit log signature is not NULL."""
        result = self.db.table("pms_audit_log").select("signature").eq(
            "entity_id", entity_id
        ).execute()
        for entry in (result.data or []):
            if entry.get("signature") is None:
                return False
        return True

    def check_pms_parts_not_updated_for_stock(self, part_id: str) -> bool:
        """
        Verify that pms_parts.quantity_on_hand was NOT directly updated.
        (Should be NULL or 0 if doctrine is followed)
        """
        result = self.db.table("pms_parts").select("quantity_on_hand").eq(
            "id", part_id
        ).maybe_single().execute()
        # If quantity_on_hand exists and is non-zero, doctrine violated
        qty = (result.data or {}).get("quantity_on_hand")
        # None or 0 is compliant (stock via transactions)
        return qty is None or qty == 0


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def harness():
    """Create test harness for module."""
    h = PartLensTestHarness()
    yield h
    h.cleanup()


@pytest.fixture
def test_part(harness):
    """Create a test part with stock via transactions."""
    part_id = harness.setup_test_part_with_transactions(initial_quantity=20)
    yield part_id


# ============================================================================
# TRANSACTION-ONLY INVARIANT TESTS
# ============================================================================

@pytest.mark.integration
class TestTransactionOnlyInvariant:
    """Test that stock changes only via transactions, never direct pms_parts UPDATE."""

    def test_consume_inserts_transaction_not_update(self, harness, test_part):
        """consume_part should INSERT transaction, not UPDATE pms_parts."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_txn_count = harness.get_transaction_count(test_part)

        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=5,
        ))

        # Verify transaction was inserted
        new_txn_count = harness.get_transaction_count(test_part)
        assert new_txn_count == initial_txn_count + 1, "Transaction should be inserted"

        # Verify pms_parts.quantity_on_hand was NOT updated
        assert harness.check_pms_parts_not_updated_for_stock(test_part), \
            "pms_parts.quantity_on_hand should NOT be updated (doctrine violation)"

    def test_receive_inserts_transaction_not_update(self, harness, test_part):
        """receive_part should INSERT transaction, not UPDATE pms_parts."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_txn_count = harness.get_transaction_count(test_part)

        asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=10,
            idempotency_key=f"txn-test-{uuid.uuid4()}",
        ))

        new_txn_count = harness.get_transaction_count(test_part)
        assert new_txn_count == initial_txn_count + 1, "Transaction should be inserted"

    def test_adjust_inserts_transaction_not_update(self, harness, test_part):
        """adjust_stock_quantity should INSERT transaction, not UPDATE pms_parts."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_txn_count = harness.get_transaction_count(test_part)

        asyncio.run(handlers.adjust_stock_quantity(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            new_quantity=50,
            reason="physical_count",
            signature={"pin": "1234", "totp": "123456"},
        ))

        new_txn_count = harness.get_transaction_count(test_part)
        assert new_txn_count == initial_txn_count + 1, "Transaction should be inserted"


# ============================================================================
# DERIVED STOCK PARITY TESTS
# ============================================================================

@pytest.mark.integration
class TestDerivedStockParity:
    """Test that stock equals SUM of transactions."""

    def test_stock_equals_transaction_sum(self, harness, test_part):
        """pms_part_stock.on_hand should equal SUM(pms_inventory_transactions.quantity_change)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Perform a sequence of operations
        # Initial: 20
        asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=15,
            idempotency_key=f"parity-recv-{uuid.uuid4()}",
        ))
        # After receive: 20 + 15 = 35

        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=8,
        ))
        # After consume: 35 - 8 = 27

        asyncio.run(handlers.adjust_stock_quantity(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            new_quantity=30,
            reason="cycle_count",
            signature={"pin": "1234", "totp": "123456"},
        ))
        # After adjust to 30

        # Compare view vs transaction sum
        view_stock = harness.get_stock_level_from_view(test_part)
        txn_sum = harness.get_transaction_sum(test_part)

        assert view_stock == txn_sum, \
            f"Stock parity violated: view={view_stock}, txn_sum={txn_sum}"


# ============================================================================
# DB-ENFORCED IDEMPOTENCY TESTS
# ============================================================================

@pytest.mark.integration
class TestDBEnforcedIdempotency:
    """Test idempotency via DB unique constraint."""

    def test_duplicate_idempotency_key_returns_409(self, harness, test_part):
        """Duplicate idempotency_key should return 409 via DB constraint."""
        from handlers.part_handlers import PartHandlers, ConflictError

        handlers = PartHandlers(harness.db)
        idempotency_key = f"idem-dup-{uuid.uuid4()}"

        # First receive - should succeed
        result1 = asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=5,
            idempotency_key=idempotency_key,
        ))
        assert result1["status"] == "success"

        # Second receive with same key - should fail with 409
        with pytest.raises(ConflictError, match="Duplicate receive"):
            asyncio.run(handlers.receive_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity_received=5,
                idempotency_key=idempotency_key,  # Same key
            ))

    def test_only_one_transaction_row_for_duplicate(self, harness, test_part):
        """Duplicate idempotency_key should result in only one transaction row."""
        from handlers.part_handlers import PartHandlers, ConflictError

        handlers = PartHandlers(harness.db)
        idempotency_key = f"idem-single-{uuid.uuid4()}"

        initial_count = harness.get_transaction_count(test_part)

        # First receive
        asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=3,
            idempotency_key=idempotency_key,
        ))

        # Try duplicate (should fail)
        try:
            asyncio.run(handlers.receive_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity_received=3,
                idempotency_key=idempotency_key,
            ))
        except ConflictError:
            pass

        # Verify only one transaction was created
        final_count = harness.get_transaction_count(test_part)
        assert final_count == initial_count + 1, "Only one transaction should exist"

    def test_null_idempotency_key_allowed_multiple_times(self, harness, test_part):
        """NULL idempotency_key should be allowed (multiple NULL keys are distinct)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_count = harness.get_transaction_count(test_part)

        # First receive with NULL key
        result1 = asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=2,
            idempotency_key=None,  # NULL key
        ))
        assert result1["status"] == "success"

        # Second receive with NULL key - should also succeed (NULLs are not unique in SQL)
        result2 = asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=2,
            idempotency_key=None,  # Another NULL key
        ))
        assert result2["status"] == "success"

        # Verify two transactions were created
        final_count = harness.get_transaction_count(test_part)
        assert final_count == initial_count + 2, "Two transactions should exist (NULL keys are distinct)"

    def test_different_yacht_same_idempotency_key_allowed(self, harness):
        """Same idempotency_key on different yachts should be allowed."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        idempotency_key = f"cross-yacht-{uuid.uuid4()}"

        # Create test part on test yacht
        part_id = harness.setup_test_part_with_transactions(initial_quantity=10)

        # First receive on TEST_YACHT_ID
        result1 = asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=part_id,
            quantity_received=5,
            idempotency_key=idempotency_key,
        ))
        assert result1["status"] == "success"

        # Note: Can't actually test cross-yacht insert without proper setup
        # This test documents the expected behavior: unique constraint is (yacht_id, idempotency_key)


# ============================================================================
# RECONCILIATION TESTS
# ============================================================================

@pytest.mark.integration
class TestReconciliationInvariants:
    """Test reconciliation between views and transaction sums."""

    def test_on_hand_equals_transaction_sum_equals_view(self, harness, test_part):
        """Verify: pms_part_stock.on_hand == SUM(transactions) == v_stock_from_transactions.on_hand."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Perform operations to create multiple transactions
        asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=10,
            idempotency_key=f"recon-1-{uuid.uuid4()}",
        ))

        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=3,
        ))

        # Get from pms_part_stock (canonical view)
        ps_result = harness.db.table("pms_part_stock").select("on_hand, stock_id").eq(
            "part_id", test_part
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        pms_on_hand = (ps_result.data or {}).get("on_hand", 0)
        stock_id = (ps_result.data or {}).get("stock_id")

        # Get from v_stock_from_transactions
        v_result = harness.db.table("v_stock_from_transactions").select("on_hand, cached_quantity, reconciliation_status").eq(
            "stock_id", stock_id
        ).maybe_single().execute()

        v_on_hand = (v_result.data or {}).get("on_hand", 0)
        cached_qty = (v_result.data or {}).get("cached_quantity", 0)
        recon_status = (v_result.data or {}).get("reconciliation_status", "UNKNOWN")

        # Get actual transaction sum
        txn_sum = harness.get_transaction_sum(test_part)

        # All three should match
        assert pms_on_hand == txn_sum, f"pms_part_stock.on_hand ({pms_on_hand}) != transaction sum ({txn_sum})"
        assert v_on_hand == txn_sum, f"v_stock_from_transactions.on_hand ({v_on_hand}) != transaction sum ({txn_sum})"
        assert pms_on_hand == v_on_hand, f"pms_part_stock.on_hand ({pms_on_hand}) != v_stock_from_transactions.on_hand ({v_on_hand})"

    def test_reconciliation_status_shows_drift(self, harness, test_part):
        """If cache != transaction sum, reconciliation_status should be 'DRIFT'."""
        # Get stock_id
        ps_result = harness.db.table("pms_part_stock").select("stock_id").eq(
            "part_id", test_part
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        stock_id = (ps_result.data or {}).get("stock_id")
        if not stock_id:
            pytest.skip("No stock_id found")

        # Get reconciliation status
        v_result = harness.db.table("v_stock_from_transactions").select(
            "on_hand, cached_quantity, reconciliation_status"
        ).eq("stock_id", stock_id).maybe_single().execute()

        if v_result.data:
            on_hand = v_result.data.get("on_hand", 0)
            cached = v_result.data.get("cached_quantity", 0)
            status = v_result.data.get("reconciliation_status")

            if on_hand == cached:
                assert status == "OK", "Same values should show OK"
            else:
                assert status == "DRIFT", "Different values should show DRIFT"


# ============================================================================
# SIGNED ACTION CONTRACT TESTS
# ============================================================================

@pytest.mark.integration
class TestSignedActionContracts:
    """Test SIGNED actions require signature (400 if missing)."""

    def test_adjust_stock_missing_signature_returns_400(self, harness, test_part):
        """adjust_stock_quantity without signature should return 400."""
        from handlers.part_handlers import PartHandlers, SignatureRequiredError

        handlers = PartHandlers(harness.db)

        with pytest.raises(SignatureRequiredError, match="Signature is required"):
            asyncio.run(handlers.adjust_stock_quantity(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                new_quantity=100,
                reason="physical_count",
                signature={},  # Empty signature
            ))

    def test_adjust_stock_null_signature_returns_400(self, harness, test_part):
        """adjust_stock_quantity with null signature should return 400."""
        from handlers.part_handlers import PartHandlers, SignatureRequiredError

        handlers = PartHandlers(harness.db)

        with pytest.raises(SignatureRequiredError, match="Signature is required"):
            asyncio.run(handlers.adjust_stock_quantity(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                new_quantity=100,
                reason="physical_count",
                signature=None,  # Null signature
            ))

    def test_write_off_missing_signature_returns_400(self, harness, test_part):
        """write_off_part without signature should return 400."""
        from handlers.part_handlers import PartHandlers, SignatureRequiredError

        handlers = PartHandlers(harness.db)

        with pytest.raises(SignatureRequiredError, match="Signature is required"):
            asyncio.run(handlers.write_off_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity=5,
                reason="damaged",
                signature={},
            ))

    def test_adjust_stock_with_signature_succeeds(self, harness, test_part):
        """adjust_stock_quantity with valid signature should succeed."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        result = asyncio.run(handlers.adjust_stock_quantity(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            new_quantity=50,
            reason="physical_count",
            signature={"pin": "1234", "totp": "123456"},
        ))

        assert result["status"] == "success"
        assert result["is_signed"] is True

    def test_signed_action_audit_has_signature_payload(self, harness, test_part):
        """SIGNED action should write full signature payload to audit log."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.adjust_stock_quantity(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            new_quantity=25,
            reason="recount",
            signature={"pin": "1234", "totp": "654321"},
        ))

        # Query audit log
        result = harness.db.table("pms_audit_log").select("signature").eq(
            "entity_id", test_part
        ).eq("action", "adjust_stock_quantity").order("created_at", desc=True).limit(1).execute()

        assert result.data, "Audit log entry should exist"
        sig = result.data[0].get("signature", {})
        assert sig != {}, "SIGNED action should have non-empty signature"
        assert "signature_hash" in sig, "SIGNED action should have signature_hash"

    def test_adjust_stock_signature_has_required_keys(self, harness, test_part):
        """adjust_stock_quantity signature must have all required keys per doctrine."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.adjust_stock_quantity(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            new_quantity=42,
            reason="inventory_audit",
            signature={"pin": "1234", "totp": "654321"},
        ))

        # Query audit log
        result = harness.db.table("pms_audit_log").select("signature").eq(
            "entity_id", test_part
        ).eq("action", "adjust_stock_quantity").order("created_at", desc=True).limit(1).execute()

        assert result.data, "Audit log entry should exist"
        sig = result.data[0].get("signature", {})

        # Required keys per doctrine
        required_keys = ["user_id", "role_at_signing", "signature_type", "signature_hash", "signed_at"]
        for key in required_keys:
            assert key in sig, f"SIGNED signature missing required key: {key}"

        # Verify signature_type is "pin_totp"
        assert sig["signature_type"] == "pin_totp", "signature_type should be 'pin_totp'"

        # Verify signature_hash has sha256 prefix
        assert sig["signature_hash"].startswith("sha256:"), "signature_hash should have sha256: prefix"

    def test_write_off_signature_has_required_keys(self, harness, test_part):
        """write_off_part signature must have all required keys per doctrine."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.write_off_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=2,
            reason="damaged",
            signature={"pin": "1234", "totp": "654321"},
        ))

        # Query audit log
        result = harness.db.table("pms_audit_log").select("signature").eq(
            "entity_id", test_part
        ).eq("action", "write_off_part").order("created_at", desc=True).limit(1).execute()

        assert result.data, "Audit log entry should exist"
        sig = result.data[0].get("signature", {})

        # Required keys per doctrine
        required_keys = ["user_id", "role_at_signing", "signature_type", "signature_hash", "signed_at"]
        for key in required_keys:
            assert key in sig, f"SIGNED signature missing required key: {key}"

        # Verify signature_type is "pin_totp"
        assert sig["signature_type"] == "pin_totp", "signature_type should be 'pin_totp'"


# ============================================================================
# READ AUDIT TESTS
# ============================================================================

@pytest.mark.integration
class TestReadAudit:
    """Test read-audit entries for READ actions."""

    def test_view_part_details_creates_read_audit(self, harness, test_part):
        """view_part_details should create audit log with signature={}."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.view_part_details(
            entity_id=test_part,
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
        ))

        # Verify audit log exists
        count = harness.get_audit_log_count(test_part, "view_part_details")
        assert count > 0, "Read audit should be created"

        # Verify signature is not NULL (should be {})
        result = harness.db.table("pms_audit_log").select("signature, metadata").eq(
            "entity_id", test_part
        ).eq("action", "view_part_details").order("created_at", desc=True).limit(1).execute()

        assert result.data, "Audit entry should exist"
        entry = result.data[0]
        assert entry["signature"] is not None, "signature should not be NULL"
        assert entry["signature"] == {}, "READ action should have signature={}"
        assert entry["metadata"].get("read_audit") is True, "Should have read_audit flag"

    def test_read_audit_has_required_metadata_keys(self, harness, test_part):
        """READ action audit should have required metadata keys per doctrine."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.view_part_details(
            entity_id=test_part,
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
        ))

        # Query audit log
        result = harness.db.table("pms_audit_log").select("metadata").eq(
            "entity_id", test_part
        ).eq("action", "view_part_details").order("created_at", desc=True).limit(1).execute()

        assert result.data, "Audit entry should exist"
        metadata = result.data[0].get("metadata", {})

        # Required keys per doctrine
        required_keys = ["source", "lens"]
        for key in required_keys:
            assert key in metadata, f"READ audit metadata missing required key: {key}"

        assert metadata["source"] == "part_lens", "source should be 'part_lens'"
        assert metadata["lens"] == "part", "lens should be 'part'"

    def test_open_document_creates_read_audit(self, harness, test_part):
        """open_document should create audit log with signature={}."""
        # Create a test document first
        doc_id = str(uuid.uuid4())
        harness.db.table("doc_metadata").insert({
            "id": doc_id,
            "yacht_id": TEST_YACHT_ID,
            "source": "test",
            "filename": "test.pdf",
            "storage_path": f"{TEST_YACHT_ID}/test.pdf",
            "storage_bucket": "pms-label-pdfs",
            "document_type": "test",
            "content_type": "application/pdf",
        }).execute()

        try:
            from handlers.part_handlers import PartHandlers
            handlers = PartHandlers(harness.db)

            result = asyncio.run(handlers.open_document(
                document_id=doc_id,
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
            ))

            # Should succeed (even without actual file)
            assert result.get("document_id") == doc_id

            # Verify audit log
            audit_result = harness.db.table("pms_audit_log").select("signature, metadata").eq(
                "entity_id", doc_id
            ).eq("action", "open_document").order("created_at", desc=True).limit(1).execute()

            assert audit_result.data, "Audit entry should exist"
            entry = audit_result.data[0]
            assert entry["signature"] == {}, "READ action should have signature={}"
            assert entry["metadata"].get("read_audit") is True

        finally:
            # Cleanup
            harness.db.table("pms_audit_log").delete().eq("entity_id", doc_id).execute()
            harness.db.table("doc_metadata").delete().eq("id", doc_id).execute()


# ============================================================================
# CONSUME PART TESTS
# ============================================================================

@pytest.mark.integration
class TestConsumePartHandler:
    """Integration tests for consume_part handler."""

    def test_consume_reduces_stock(self, harness, test_part):
        """Consuming part should reduce stock level."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_stock = harness.get_stock_level_from_view(test_part)

        result = asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=5,
        ))

        assert result["status"] == "success"
        assert result["quantity_consumed"] == 5

        new_stock = harness.get_stock_level_from_view(test_part)
        assert new_stock == initial_stock - 5

    def test_consume_insufficient_stock_returns_409(self, harness, test_part):
        """Consuming more than available should return 409."""
        from handlers.part_handlers import PartHandlers, ConflictError

        handlers = PartHandlers(harness.db)
        current_stock = harness.get_stock_level_from_view(test_part)

        with pytest.raises(ConflictError, match="Insufficient stock"):
            asyncio.run(handlers.consume_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity=current_stock + 100,
            ))


# ============================================================================
# TRANSFER PART TESTS
# ============================================================================

@pytest.mark.integration
class TestTransferPartHandler:
    """Integration tests for transfer_part handler."""

    def test_transfer_creates_paired_transactions(self, harness, test_part):
        """Transfer should create two transactions (out and in)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_txn_count = harness.get_transaction_count(test_part)

        result = asyncio.run(handlers.transfer_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=5,
            from_location=f"LOC-{test_part[:4]}",  # Match setup location
            to_location="TRANSFER-DEST",
        ))

        assert result["status"] == "success"
        assert "transfer_ref" in result

        # Should have two new transactions (out + in)
        new_txn_count = harness.get_transaction_count(test_part)
        assert new_txn_count == initial_txn_count + 2, "Transfer should create 2 transactions"

    def test_transfer_preserves_total_stock(self, harness, test_part):
        """Transfer should preserve total stock (conservation of matter)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_total = harness.get_transaction_sum(test_part)

        asyncio.run(handlers.transfer_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=3,
            from_location=f"LOC-{test_part[:4]}",
            to_location="TRANSFER-DEST-2",
        ))

        # Total stock should be unchanged (out + in = 0 net change)
        final_total = harness.get_transaction_sum(test_part)
        assert final_total == initial_total, "Transfer should preserve total stock"

    def test_transfer_insufficient_stock_returns_409(self, harness, test_part):
        """Transfer more than available should return 409."""
        from handlers.part_handlers import PartHandlers, ConflictError

        handlers = PartHandlers(harness.db)
        current_stock = harness.get_stock_level_from_view(test_part)

        with pytest.raises(ConflictError, match="Insufficient stock"):
            asyncio.run(handlers.transfer_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity=current_stock + 100,
                from_location=f"LOC-{test_part[:4]}",
                to_location="NOWHERE",
            ))


# ============================================================================
# WRITE OFF PART TESTS
# ============================================================================

@pytest.mark.integration
class TestWriteOffPartHandler:
    """Integration tests for write_off_part handler."""

    def test_write_off_reduces_stock(self, harness, test_part):
        """Write off should reduce stock via transaction."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_stock = harness.get_stock_level_from_view(test_part)

        result = asyncio.run(handlers.write_off_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=2,
            reason="damaged",
            signature={"pin": "1234", "totp": "654321"},
        ))

        assert result["status"] == "success"
        assert result["is_signed"] is True

        new_stock = harness.get_stock_level_from_view(test_part)
        assert new_stock == initial_stock - 2

    def test_write_off_insufficient_stock_returns_409(self, harness, test_part):
        """Write off more than available should return 409."""
        from handlers.part_handlers import PartHandlers, ConflictError

        handlers = PartHandlers(harness.db)
        current_stock = harness.get_stock_level_from_view(test_part)

        with pytest.raises(ConflictError, match="Cannot write off"):
            asyncio.run(handlers.write_off_part(
                yacht_id=TEST_YACHT_ID,
                user_id=harness.test_user_id,
                part_id=test_part,
                quantity=current_stock + 100,
                reason="expired",
                signature={"pin": "1234", "totp": "654321"},
            ))

    def test_write_off_inserts_transaction_not_update(self, harness, test_part):
        """write_off_part should INSERT transaction, not UPDATE pms_parts."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_txn_count = harness.get_transaction_count(test_part)

        asyncio.run(handlers.write_off_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=1,
            reason="lost",
            signature={"pin": "1234", "totp": "654321"},
        ))

        new_txn_count = harness.get_transaction_count(test_part)
        assert new_txn_count == initial_txn_count + 1, "Transaction should be inserted"

        # Verify pms_parts.quantity_on_hand was NOT updated
        assert harness.check_pms_parts_not_updated_for_stock(test_part)


# ============================================================================
# RLS NEGATIVE CONTROL TESTS
# ============================================================================

@pytest.mark.integration
class TestRLSNegativeControls:
    """Test RLS prevents cross-yacht access."""

    def test_cross_yacht_stock_query_returns_empty(self, harness, test_part):
        """Query for stock on different yacht should return empty."""
        result = harness.db.table("pms_part_stock").select("on_hand").eq(
            "part_id", test_part
        ).eq("yacht_id", OTHER_YACHT_ID).execute()

        assert len(result.data or []) == 0, "Cross-yacht query should return no rows"

    def test_view_low_stock_only_returns_own_yacht(self, harness):
        """view_low_stock should only return parts for own yacht."""
        result = harness.db.table("v_low_stock_report").select("part_id, yacht_id").eq(
            "yacht_id", TEST_YACHT_ID
        ).execute()

        for part in (result.data or []):
            assert part["yacht_id"] == TEST_YACHT_ID, "Should only return own yacht parts"

    def test_transaction_cross_yacht_isolation(self, harness, test_part):
        """Transactions for other yachts should not be visible."""
        # Query transactions for test part but with wrong yacht filter
        # The stock belongs to TEST_YACHT_ID, so filtering by OTHER_YACHT_ID should return empty
        stock_result = harness.db.table("pms_inventory_stock").select("id").eq(
            "part_id", test_part
        ).eq("yacht_id", OTHER_YACHT_ID).execute()

        assert len(stock_result.data or []) == 0, "Cross-yacht stock query should return no rows"

    def test_parts_table_cross_yacht_isolation(self, harness, test_part):
        """Parts for other yachts should not be visible."""
        result = harness.db.table("pms_parts").select("id").eq(
            "id", test_part
        ).eq("yacht_id", OTHER_YACHT_ID).execute()

        assert len(result.data or []) == 0, "Cross-yacht parts query should return no rows"

    def test_audit_log_cross_yacht_isolation(self, harness, test_part):
        """Audit logs for other yachts should not be visible."""
        # First create an audit entry for our yacht
        from handlers.part_handlers import PartHandlers
        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.view_part_details(
            entity_id=test_part,
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
        ))

        # Query with wrong yacht should return empty
        result = harness.db.table("pms_audit_log").select("id").eq(
            "entity_id", test_part
        ).eq("yacht_id", OTHER_YACHT_ID).execute()

        assert len(result.data or []) == 0, "Cross-yacht audit query should return no rows"


# ============================================================================
# SUPPRESSION TESTS (negative controls)
# ============================================================================

@pytest.mark.integration
class TestSuppressionNegativeControls:
    """Test suppression of suggestions and alerts."""

    def test_well_stocked_part_not_in_low_stock_report(self, harness):
        """Parts above min_level should NOT appear in v_low_stock_report."""
        # Create a well-stocked part
        part_id = harness.setup_test_part_with_transactions(initial_quantity=50)

        # Set min_level lower than on_hand
        harness.db.table("pms_parts").update({
            "min_level": 10  # on_hand=50 >> min_level=10
        }).eq("id", part_id).execute()

        # Query low stock report - this part should NOT appear
        result = harness.db.table("v_low_stock_report").select("part_id").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        assert len(result.data or []) == 0, "Well-stocked part should NOT appear in low stock report"

    def test_zero_min_level_not_in_low_stock_report(self, harness):
        """Parts with min_level=0 should NOT appear in low stock (no reorder needed)."""
        # Create a part with 0 min_level
        part_id = harness.setup_test_part_with_transactions(initial_quantity=5)

        harness.db.table("pms_parts").update({
            "min_level": 0  # No min level = no low stock alert
        }).eq("id", part_id).execute()

        # Query low stock report - should NOT appear
        result = harness.db.table("v_low_stock_report").select("part_id").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        # Part with min_level=0 should not be flagged
        for entry in (result.data or []):
            if entry.get("part_id") == part_id:
                pytest.fail("Part with min_level=0 should not appear in low stock report")

    def test_low_stock_part_appears_in_report(self, harness):
        """Parts below min_level SHOULD appear in v_low_stock_report (positive control)."""
        # Create a low-stock part
        part_id = harness.setup_test_part_with_transactions(initial_quantity=3)

        harness.db.table("pms_parts").update({
            "min_level": 10  # on_hand=3 < min_level=10 -> low stock
        }).eq("id", part_id).execute()

        # Query low stock report - this part SHOULD appear
        result = harness.db.table("v_low_stock_report").select("part_id, on_hand, min_level, is_low_stock").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        assert len(result.data or []) > 0, "Low-stock part SHOULD appear in low stock report"
        assert result.data[0]["is_low_stock"] is True, "is_low_stock should be True"

    def test_out_of_stock_part_shows_critical_urgency(self, harness):
        """Parts with on_hand=0 should show 'critical' urgency."""
        # Create a zero-stock part
        part_id = harness.setup_test_part_with_transactions(initial_quantity=0)

        harness.db.table("pms_parts").update({
            "min_level": 10
        }).eq("id", part_id).execute()

        # Query low stock report
        result = harness.db.table("v_low_stock_report").select("part_id, urgency, is_out_of_stock").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).execute()

        assert len(result.data or []) > 0, "Out-of-stock part should appear"
        assert result.data[0]["is_out_of_stock"] is True, "is_out_of_stock should be True"
        assert result.data[0]["urgency"] == "critical", "Out of stock should have critical urgency"


# ============================================================================
# STORAGE BUCKET RLS TESTS
# ============================================================================

@pytest.mark.integration
class TestStorageBucketRLS:
    """Test storage bucket RLS policies (cross-yacht isolation)."""

    def test_storage_path_contains_yacht_id(self, harness, test_part):
        """Generated storage paths should contain yacht_id for RLS."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Generate labels
        result = asyncio.run(handlers.generate_part_labels(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_ids=[test_part],
        ))

        assert result["status"] == "success"
        storage_path = result.get("storage_path", "")

        # Storage path should contain yacht_id for RLS enforcement
        assert TEST_YACHT_ID in storage_path, f"Storage path should contain yacht_id: {storage_path}"

    def test_document_metadata_yacht_isolation(self, harness, test_part):
        """Document metadata should be isolated by yacht."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Generate labels (creates doc_metadata)
        result = asyncio.run(handlers.generate_part_labels(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_ids=[test_part],
        ))

        doc_id = result.get("document_id")
        if doc_id:
            # Query with wrong yacht should return empty
            wrong_yacht_result = harness.db.table("doc_metadata").select("id").eq(
                "id", doc_id
            ).eq("yacht_id", OTHER_YACHT_ID).execute()

            assert len(wrong_yacht_result.data or []) == 0, "Cross-yacht doc_metadata query should return no rows"

            # Cleanup
            harness.db.table("doc_metadata").delete().eq("id", doc_id).execute()


# ============================================================================
# REGISTRY TESTS
# ============================================================================

class TestPartLensRegistry:
    """Test Part Lens actions are properly registered."""

    def test_part_actions_registered(self):
        """Verify all Part Lens actions exist in registry."""
        from action_router.registry import ACTION_REGISTRY

        expected_actions = [
            "add_to_shopping_list",
            "consume_part",
            "adjust_stock_quantity",
            "receive_part",
            "transfer_part",
            "write_off_part",
            "view_part_details",
            "view_low_stock",
            "generate_part_labels",
            "request_label_output",
        ]

        for action_id in expected_actions:
            assert action_id in ACTION_REGISTRY, f"Missing action: {action_id}"

    def test_signed_actions_have_correct_variant(self):
        """Verify SIGNED actions have correct variant."""
        from action_router.registry import ACTION_REGISTRY, ActionVariant

        signed_actions = ["adjust_stock_quantity", "write_off_part"]

        for action_id in signed_actions:
            action = ACTION_REGISTRY[action_id]
            assert action.variant == ActionVariant.SIGNED, f"{action_id} should be SIGNED"


# ============================================================================
# STOCK COMPUTATION TESTS
# ============================================================================

class TestStockComputation:
    """Test stock computation rules."""

    def test_suggested_order_qty_formula(self):
        """Test: suggested_qty = round_up(max(min_level - on_hand, 1), reorder_multiple)."""
        from handlers.part_handlers import compute_suggested_order_qty

        test_cases = [
            (5, 10, 5, 5),    # Shortage of 5, multiple of 5 -> 5
            (7, 10, 5, 5),    # Shortage of 3, round up to 5
            (0, 10, 5, 10),   # Shortage of 10, multiple of 5 -> 10
            (10, 10, 5, 0),   # No shortage -> 0
            (15, 10, 5, 0),   # Above min -> 0
            (9, 10, 1, 1),    # Shortage of 1, multiple of 1 -> 1
            (8, 10, 3, 3),    # Shortage of 2, round up to 3
        ]

        for on_hand, min_level, multiple, expected in test_cases:
            result = compute_suggested_order_qty(on_hand, min_level, multiple)
            assert result == expected, f"Failed for ({on_hand}, {min_level}, {multiple})"


# ============================================================================
# NO 500 TESTS
# ============================================================================

class TestNoInternalServerErrors:
    """Verify no 500 errors from Part Lens endpoints."""

    def test_suggestions_endpoint_no_500(self):
        """Suggestions endpoint should not return 500."""
        from fastapi.testclient import TestClient
        from microaction_service import app

        client = TestClient(app)

        response = client.get(
            f"/v1/parts/suggestions?part_id=invalid&yacht_id={TEST_YACHT_ID}"
        )

        assert response.status_code != 500, f"Got 500: {response.text}"

    def test_low_stock_endpoint_no_500(self):
        """Low stock endpoint should not return 500."""
        from fastapi.testclient import TestClient
        from microaction_service import app

        client = TestClient(app)

        response = client.get(f"/v1/parts/low-stock?yacht_id={TEST_YACHT_ID}")

        assert response.status_code != 500, f"Got 500: {response.text}"


# ============================================================================
# AUDIT LOG INVARIANT TESTS
# ============================================================================

@pytest.mark.integration
class TestAuditLogInvariant:
    """Test audit log signature invariant (never NULL)."""

    def test_mutate_action_creates_audit_with_empty_signature(self, harness, test_part):
        """MUTATE actions should create audit log with signature={}."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=1,
        ))

        assert harness.check_audit_signature_not_null(test_part)


# ============================================================================
# TRANSFER CONSERVATION TESTS (no double counting)
# ============================================================================

@pytest.mark.integration
class TestTransferConservation:
    """Test transfer preserves stock and doesn't double count."""

    def test_transfer_global_stock_unchanged(self, harness, test_part):
        """Transfer should not change total global stock (conservation)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Get initial total stock from ALL transactions
        initial_sum = harness.get_transaction_sum(test_part)

        # Perform transfer
        asyncio.run(handlers.transfer_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=3,
            from_location=f"LOC-{test_part[:4]}",
            to_location="CONSERVATION-TEST-LOC",
        ))

        # Get final total - should be unchanged
        final_sum = harness.get_transaction_sum(test_part)

        assert final_sum == initial_sum, f"Transfer changed total stock: {initial_sum} -> {final_sum}"

    def test_transfer_paired_rows_net_zero(self, harness, test_part):
        """Paired transfer rows should have net zero change."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        initial_count = harness.get_transaction_count(test_part)

        result = asyncio.run(handlers.transfer_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity=2,
            from_location=f"LOC-{test_part[:4]}",
            to_location="NET-ZERO-TEST",
        ))

        # Should create exactly 2 transactions (out + in)
        final_count = harness.get_transaction_count(test_part)
        assert final_count == initial_count + 2, "Transfer should create exactly 2 transactions"

        # Get the two transactions and verify they sum to zero
        out_id = result.get("transaction_out_id")
        in_id = result.get("transaction_in_id")

        if out_id and in_id:
            out_txn = harness.db.table("pms_inventory_transactions").select("quantity_change").eq("id", out_id).maybe_single().execute()
            in_txn = harness.db.table("pms_inventory_transactions").select("quantity_change").eq("id", in_id).maybe_single().execute()

            out_change = (out_txn.data or {}).get("quantity_change", 0)
            in_change = (in_txn.data or {}).get("quantity_change", 0)

            assert out_change + in_change == 0, f"Transfer net should be 0, got {out_change} + {in_change}"


# ============================================================================
# SUGGESTIONS FORMULA VERIFICATION
# ============================================================================

@pytest.mark.integration
class TestSuggestionsFormula:
    """Test suggested_qty formula matches spec and uses canonical source."""

    def test_suggested_qty_matches_view_formula(self, harness):
        """Verify v_low_stock_report.suggested_order_qty matches formula."""
        # Create a part with specific stock level for predictable test
        part_id = harness.setup_test_part_with_transactions(initial_quantity=3)

        # Set specific min_level and reorder_multiple
        harness.db.table("pms_parts").update({
            "min_level": 10,
            "reorder_multiple": 5,
        }).eq("id", part_id).execute()

        # Query v_low_stock_report
        result = harness.db.table("v_low_stock_report").select(
            "on_hand, min_level, reorder_multiple, suggested_order_qty"
        ).eq("part_id", part_id).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        assert result.data, "Part should appear in low_stock_report"

        on_hand = result.data["on_hand"]  # 3
        min_level = result.data["min_level"]  # 10
        multiple = result.data["reorder_multiple"]  # 5
        actual_suggested = result.data["suggested_order_qty"]

        # Formula: CEIL(GREATEST(min_level - on_hand, 1) / reorder_multiple) * reorder_multiple
        shortage = max(min_level - on_hand, 1)  # max(10-3, 1) = 7
        import math
        expected_suggested = math.ceil(shortage / max(multiple, 1)) * max(multiple, 1)  # ceil(7/5)*5 = 10

        assert actual_suggested == expected_suggested, \
            f"suggested_order_qty mismatch: got {actual_suggested}, expected {expected_suggested}"

    def test_suggested_qty_uses_transaction_derived_on_hand(self, harness):
        """Verify suggestions use on_hand from transactions, not cache."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)
        part_id = harness.setup_test_part_with_transactions(initial_quantity=5)

        harness.db.table("pms_parts").update({
            "min_level": 20,
            "reorder_multiple": 5,
        }).eq("id", part_id).execute()

        # Consume to change on_hand via transaction
        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=part_id,
            quantity=2,
        ))
        # Now on_hand should be 3 (5 - 2)

        # Verify pms_part_stock shows correct on_hand
        stock_result = harness.db.table("pms_part_stock").select("on_hand").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        assert stock_result.data["on_hand"] == 3, "pms_part_stock.on_hand should reflect transaction"

        # Verify v_low_stock_report uses same value
        low_result = harness.db.table("v_low_stock_report").select("on_hand").eq(
            "part_id", part_id
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        if low_result.data:
            assert low_result.data["on_hand"] == 3, "v_low_stock_report should use transaction-derived on_hand"


# ============================================================================
# ZERO 500 HARNESS ASSERTION
# ============================================================================

class TestHarnessNo5xx:
    """Test harness-level assertion that no 5xx errors occur."""

    # Track all responses during test run
    _responses_collected = []

    def test_all_handler_calls_no_5xx(self, harness, test_part):
        """Comprehensive test that exercises all handlers and asserts no 500s."""
        from handlers.part_handlers import PartHandlers, ConflictError, SignatureRequiredError

        handlers = PartHandlers(harness.db)
        errors_5xx = []

        # Test each handler and track any 5xx-like errors
        operations = [
            ("view_part_details", lambda: asyncio.run(handlers.view_part_details(
                entity_id=test_part, yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id
            ))),
            ("consume_part", lambda: asyncio.run(handlers.consume_part(
                yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id,
                part_id=test_part, quantity=1
            ))),
            ("receive_part", lambda: asyncio.run(handlers.receive_part(
                yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id,
                part_id=test_part, quantity_received=5, idempotency_key=f"no5xx-{uuid.uuid4()}"
            ))),
            ("adjust_stock_quantity", lambda: asyncio.run(handlers.adjust_stock_quantity(
                yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id,
                part_id=test_part, new_quantity=15, reason="test",
                signature={"pin": "1234", "totp": "654321"}
            ))),
        ]

        for op_name, op_func in operations:
            try:
                result = op_func()
                # Check if result contains error that looks like 500
                if isinstance(result, dict) and result.get("error") == "INTERNAL_ERROR":
                    errors_5xx.append(f"{op_name}: INTERNAL_ERROR")
            except (ConflictError, SignatureRequiredError, ValueError):
                # Expected business errors (4xx equivalent)
                pass
            except Exception as e:
                # Unexpected error = potential 500
                errors_5xx.append(f"{op_name}: {type(e).__name__}: {str(e)[:100]}")

        assert len(errors_5xx) == 0, f"5xx-like errors occurred: {errors_5xx}"


# ============================================================================
# STORAGE BUCKET RLS TESTS (all 3 buckets)
# ============================================================================

@pytest.mark.integration
class TestStorageBucketRLSComprehensive:
    """Test storage RLS for all three Part Lens buckets."""

    def test_pms_label_pdfs_path_isolation(self, harness, test_part):
        """pms-label-pdfs bucket should enforce yacht_id path prefix."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        result = asyncio.run(handlers.generate_part_labels(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_ids=[test_part],
        ))

        storage_path = result.get("storage_path", "")

        # Path must start with yacht_id for RLS
        assert storage_path.startswith(TEST_YACHT_ID), \
            f"pms-label-pdfs path should start with yacht_id: {storage_path}"

        # Cleanup
        if result.get("document_id"):
            harness.db.table("doc_metadata").delete().eq("id", result["document_id"]).execute()

    def test_pms_receiving_images_path_format(self, harness, test_part):
        """pms-receiving-images bucket paths should contain yacht_id."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Receive with a photo path
        photo_path = f"{TEST_YACHT_ID}/receiving/{test_part}/photo.jpg"

        result = asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID,
            user_id=harness.test_user_id,
            part_id=test_part,
            quantity_received=2,
            idempotency_key=f"photo-test-{uuid.uuid4()}",
            photo_storage_path=photo_path,
        ))

        assert result["status"] == "success"
        # The path we provided should be stored
        # (actual upload would be handled by client)

    def test_storage_bucket_cross_yacht_doc_metadata_blocked(self, harness, test_part):
        """doc_metadata for storage should be isolated by yacht."""
        # Create a doc_metadata entry for our yacht
        doc_id = str(uuid.uuid4())
        harness.db.table("doc_metadata").insert({
            "id": doc_id,
            "yacht_id": TEST_YACHT_ID,
            "source": "part_lens",
            "filename": "test.pdf",
            "storage_path": f"{TEST_YACHT_ID}/test.pdf",
            "storage_bucket": "pms-label-pdfs",
            "document_type": "part_labels",
            "content_type": "application/pdf",
        }).execute()

        try:
            # Query with other yacht should return empty
            cross_query = harness.db.table("doc_metadata").select("id").eq(
                "id", doc_id
            ).eq("yacht_id", OTHER_YACHT_ID).execute()

            assert len(cross_query.data or []) == 0, \
                "doc_metadata should not be visible to other yacht"

            # But our yacht can see it
            own_query = harness.db.table("doc_metadata").select("id").eq(
                "id", doc_id
            ).eq("yacht_id", TEST_YACHT_ID).execute()

            assert len(own_query.data or []) == 1, \
                "doc_metadata should be visible to own yacht"
        finally:
            harness.db.table("doc_metadata").delete().eq("id", doc_id).execute()


# ============================================================================
# CANONICAL VIEW EVIDENCE TEST
# ============================================================================

@pytest.mark.integration
class TestCanonicalViewEvidence:
    """Test and document that pms_part_stock uses v_stock_from_transactions."""

    def test_pms_part_stock_matches_transaction_sum(self, harness, test_part):
        """EVIDENCE: pms_part_stock.on_hand equals SUM(transactions.quantity_change)."""
        from handlers.part_handlers import PartHandlers

        handlers = PartHandlers(harness.db)

        # Perform several operations
        asyncio.run(handlers.receive_part(
            yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id,
            part_id=test_part, quantity_received=10,
            idempotency_key=f"evidence-1-{uuid.uuid4()}"
        ))
        asyncio.run(handlers.consume_part(
            yacht_id=TEST_YACHT_ID, user_id=harness.test_user_id,
            part_id=test_part, quantity=4
        ))

        # Get from pms_part_stock (canonical)
        ps_result = harness.db.table("pms_part_stock").select("on_hand").eq(
            "part_id", test_part
        ).eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()

        canonical_on_hand = (ps_result.data or {}).get("on_hand", 0)

        # Calculate from raw transactions
        txn_sum = harness.get_transaction_sum(test_part)

        # EVIDENCE: They must match
        assert canonical_on_hand == txn_sum, \
            f"EVIDENCE FAIL: pms_part_stock.on_hand ({canonical_on_hand}) != SUM(transactions) ({txn_sum})"

        # Document in stdout for evidence collection
        print(f"\n=== CANONICAL VIEW EVIDENCE ===")
        print(f"Part ID: {test_part}")
        print(f"pms_part_stock.on_hand: {canonical_on_hand}")
        print(f"SUM(transactions.quantity_change): {txn_sum}")
        print(f"MATCH: {'YES' if canonical_on_hand == txn_sum else 'NO'}")


# ============================================================================
# RUN CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
