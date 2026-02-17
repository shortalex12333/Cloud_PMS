"""
Direct test of ledger_events table insert.
Tests if the table exists and accepts inserts with the correct schema.
"""
import os
import sys
import hashlib
import json
from datetime import datetime
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def test_ledger_insert():
    """Test direct insert into ledger_events table."""
    from pipeline_service import get_tenant_client

    # Get default tenant
    tenant_alias = os.environ.get("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    print(f"[Test] Using tenant: {tenant_alias}")

    try:
        db_client = get_tenant_client(tenant_alias)
        print("[Test] Got tenant client successfully")
    except Exception as e:
        print(f"[Test] FAILED to get tenant client: {e}")
        return False

    # Generate test data
    test_yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"  # From screenshots
    test_user_id = str(uuid4())
    test_entity_id = str(uuid4())

    # Build proof_hash
    hash_input = json.dumps({
        "yacht_id": test_yacht_id,
        "user_id": test_user_id,
        "event_type": "update",
        "entity_type": "work_order",
        "entity_id": test_entity_id,
        "action": "test_insert",
        "timestamp": datetime.utcnow().isoformat()
    }, sort_keys=True)
    proof_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    # Build ledger event with correct schema
    ledger_event = {
        "yacht_id": test_yacht_id,
        "user_id": test_user_id,
        "event_type": "update",
        "entity_type": "work_order",
        "entity_id": test_entity_id,
        "action": "test_insert",
        "user_role": "test",
        "source_context": "api",
        "change_summary": "Test insert from backend test",
        "metadata": {"test": True, "timestamp": datetime.utcnow().isoformat()},
        "proof_hash": proof_hash
    }

    print(f"[Test] Attempting insert with data:")
    print(f"       yacht_id: {test_yacht_id}")
    print(f"       user_id: {test_user_id}")
    print(f"       event_type: update")
    print(f"       entity_type: work_order")
    print(f"       entity_id: {test_entity_id}")
    print(f"       action: test_insert")
    print(f"       proof_hash: {proof_hash[:16]}...")

    # Try insert
    try:
        result = db_client.table("ledger_events").insert(ledger_event).execute()
        print(f"[Test] INSERT SUCCESS!")
        print(f"       Result: {result.data}")
        return True
    except Exception as e:
        print(f"[Test] INSERT FAILED: {e}")
        print(f"[Test] Error type: {type(e).__name__}")

        # Check if it's a 204 (success but no content)
        if "204" in str(e):
            print("[Test] Got 204 - insert may have succeeded")
            return True

        # Try to get more error details
        if hasattr(e, 'message'):
            print(f"[Test] Error message: {e.message}")
        if hasattr(e, 'details'):
            print(f"[Test] Error details: {e.details}")
        if hasattr(e, 'code'):
            print(f"[Test] Error code: {e.code}")

        return False

def test_ledger_query():
    """Test querying ledger_events table."""
    from pipeline_service import get_tenant_client

    tenant_alias = os.environ.get("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    print(f"\n[Test] Querying ledger_events for tenant: {tenant_alias}")

    try:
        db_client = get_tenant_client(tenant_alias)

        # Query all events
        result = db_client.table("ledger_events").select("*").limit(10).execute()

        print(f"[Test] QUERY SUCCESS!")
        print(f"       Found {len(result.data)} events")

        if result.data:
            for event in result.data[:3]:
                print(f"       - {event.get('action', 'N/A')} on {event.get('entity_type', 'N/A')} at {event.get('created_at', 'N/A')}")
        else:
            print("       (table is empty)")

        return True
    except Exception as e:
        print(f"[Test] QUERY FAILED: {e}")
        return False

def test_table_exists():
    """Check if ledger_events table exists."""
    from pipeline_service import get_tenant_client

    tenant_alias = os.environ.get("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    print(f"\n[Test] Checking if ledger_events table exists for tenant: {tenant_alias}")

    try:
        db_client = get_tenant_client(tenant_alias)

        # Try to select from the table (will fail if doesn't exist)
        result = db_client.table("ledger_events").select("id").limit(1).execute()
        print("[Test] Table EXISTS!")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str:
            print(f"[Test] Table DOES NOT EXIST: {e}")
        else:
            print(f"[Test] Unknown error (table may exist): {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("LEDGER_EVENTS TABLE TEST")
    print("=" * 60)

    # Test 1: Check if table exists
    exists = test_table_exists()

    if exists:
        # Test 2: Try to query
        test_ledger_query()

        # Test 3: Try to insert
        print("\n" + "-" * 60)
        test_ledger_insert()

        # Test 4: Query again to see if insert worked
        print("\n" + "-" * 60)
        test_ledger_query()
    else:
        print("\n[FATAL] ledger_events table does not exist!")
        print("        Need to run migration to create the table.")
