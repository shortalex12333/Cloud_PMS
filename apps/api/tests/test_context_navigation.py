"""
Context Navigation Tests

These tests prove:
1. create -> context row inserted + ledger_events artefact_opened written
2. update-anchor -> anchor fields updated + ledger_events artefact_opened written
3. related -> returns groups in correct order; does not write audit event
4. add-relation -> creates row + relation_added audit event
5. end -> sets ended_at + situation_ended audit event

Tests run against REAL Supabase DB with RLS policies.
"""

import pytest

pytestmark = pytest.mark.integration  # Mark ALL tests in this module as integration
import os
import uuid
from datetime import datetime

# Import modules
from supabase import create_client
from context_nav.schemas import (
    NavigationContextCreate,
    RelatedRequest,
    AddRelatedRequest,
)
from handlers.context_navigation_handlers import (
    create_navigation_context,
    update_active_anchor,
    get_related,
    add_user_relation,
    end_navigation_context,
)

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

SUPABASE_URL = os.getenv('SUPABASE_URL', 'http://127.0.0.1:54321')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU')

# Real test yacht ID from local setup
TEST_YACHT_ID = str(uuid.uuid4())
TEST_USER_ID = str(uuid.uuid4())
TEST_EQUIPMENT_ID = str(uuid.uuid4())


@pytest.fixture
def supabase():
    """Get Supabase client with service role."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@pytest.fixture(scope="function")
def test_yacht(supabase):
    """Create test yacht for isolation."""
    # Delete any existing test yacht and user first
    try:
        supabase.table("yachts").delete().eq("id", TEST_YACHT_ID).execute()
    except Exception:
        pass

    # Create fresh test yacht
    yacht_data = {
        "id": TEST_YACHT_ID,
        "name": "Test Yacht Context Nav",
        "signature": f"TEST-{TEST_YACHT_ID[:8]}",  # Unique signature for test
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("yachts").insert(yacht_data).execute()
    assert result.data, "Failed to create test yacht"

    yield TEST_YACHT_ID

    # Cleanup: Delete test yacht and cascade
    try:
        supabase.table("yachts").delete().eq("id", TEST_YACHT_ID).execute()
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_user(supabase, test_yacht):
    """Create test user in auth.users via direct SQL with yacht_id."""
    import subprocess

    # Create user via psql (auth.users requires specific columns)
    # Include yacht_id in raw_user_meta_data so the trigger can use it
    sql = f"""
    INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, is_super_admin)
    VALUES (
        '{TEST_USER_ID}',
        '00000000-0000-0000-0000-000000000000',
        'authenticated',
        'authenticated',
        'test-{TEST_USER_ID[:8]}@example.com',
        '\\$2a\\$10\\$placeholder',
        NOW(),
        NOW(),
        NOW(),
        '{{"provider":"email","providers":["email"]}}',
        '{{"yacht_id":"{test_yacht}","name":"Test User"}}',
        false
    )
    ON CONFLICT (id) DO NOTHING;
    """

    result = subprocess.run(
        ["psql", "postgresql://postgres:postgres@127.0.0.1:54322/postgres", "-c", sql],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Failed to create test user: {result.stderr}")
        # Try to continue anyway - fixture dependencies may help

    yield TEST_USER_ID

    # Cleanup
    cleanup_sql = f"DELETE FROM auth.users WHERE id = '{TEST_USER_ID}';"
    subprocess.run(
        ["psql", "postgresql://postgres:postgres@127.0.0.1:54322/postgres", "-c", cleanup_sql],
        capture_output=True
    )


# ============================================================================
# PART 1: CREATE CONTEXT TESTS
# ============================================================================

class TestCreateContext:
    """Test context creation inserts row + audit event."""

    def test_create_context_inserts_row(self, supabase, test_yacht, test_user):
        """Creating context inserts navigation_contexts row."""
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="inventory_item",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )

        context = create_navigation_context(supabase, data)

        # Verify context created
        assert context.id is not None
        assert context.yacht_id == data.yacht_id
        assert context.active_anchor_type == "inventory_item"
        assert context.active_anchor_id == data.artefact_id

        # Verify row exists in DB
        row = supabase.table("navigation_contexts").select("*").eq(
            "id", str(context.id)
        ).maybe_single().execute()
        assert row.data is not None

    def test_create_context_writes_audit_event(self, supabase, test_yacht, test_user):
        """Creating context writes artefact_opened audit event."""
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="fault",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )

        context = create_navigation_context(supabase, data)

        # Verify audit event written
        ledger_events = supabase.table("ledger_events").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("event_name", "artefact_opened").execute()

        assert len(ledger_events.data) > 0
        # Find event for this context
        context_event = [
            e for e in ledger_events.data
            if e["payload"].get("situation_id") == str(context.id)
        ]
        assert len(context_event) == 1
        assert context_event[0]["payload"]["artefact_type"] == "fault"


# ============================================================================
# PART 2: UPDATE ANCHOR TESTS
# ============================================================================

class TestUpdateAnchor:
    """Test anchor update modifies row + writes audit event."""

    def test_update_anchor_modifies_row(self, supabase, test_yacht, test_user):
        """Updating anchor modifies navigation_contexts row."""
        # Create initial context
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="inventory_item",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )
        context = create_navigation_context(supabase, data)

        # Update anchor
        new_anchor_id = uuid.uuid4()
        updated_context = update_active_anchor(
            supabase,
            context.id,
            uuid.UUID(TEST_YACHT_ID),
            uuid.UUID(TEST_USER_ID),
            "work_order",
            new_anchor_id,
        )

        # Verify update
        assert updated_context.active_anchor_type == "work_order"
        assert updated_context.active_anchor_id == new_anchor_id

    def test_update_anchor_writes_audit_event(self, supabase, test_yacht, test_user):
        """Updating anchor writes artefact_opened audit event."""
        # Create initial context
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="inventory_item",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )
        context = create_navigation_context(supabase, data)

        # Count audit events before update
        before_count = len(supabase.table("ledger_events").select("id").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("event_name", "artefact_opened").execute().data)

        # Update anchor
        new_anchor_id = uuid.uuid4()
        update_active_anchor(
            supabase,
            context.id,
            uuid.UUID(TEST_YACHT_ID),
            uuid.UUID(TEST_USER_ID),
            "work_order",
            new_anchor_id,
        )

        # Count audit events after update
        after_count = len(supabase.table("ledger_events").select("id").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("event_name", "artefact_opened").execute().data)

        # Should have one new event
        assert after_count == before_count + 1


# ============================================================================
# PART 3: GET RELATED TESTS
# ============================================================================

class TestGetRelated:
    """Test related expansion does NOT write audit event."""

    def test_related_does_not_write_audit_event(self, supabase, test_yacht, test_user):
        """Getting related artifacts does NOT write ledger_events."""
        # Count audit events before
        before_count = len(supabase.table("ledger_events").select("id").eq(
            "yacht_id", TEST_YACHT_ID
        ).execute().data)

        # Get related artifacts
        data = RelatedRequest(
            situation_id=uuid.uuid4(),
            anchor_type="inventory_item",
            anchor_id=uuid.UUID(TEST_EQUIPMENT_ID),
            tenant_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            allowed_domains=["faults", "work_orders"],
        )
        get_related(supabase, data)

        # Count audit events after
        after_count = len(supabase.table("ledger_events").select("id").eq(
            "yacht_id", TEST_YACHT_ID
        ).execute().data)

        # Should NOT have any new events
        assert after_count == before_count

    def test_related_returns_fixed_domain_order(self, supabase, test_yacht, test_user):
        """Related results are in fixed domain order."""
        data = RelatedRequest(
            situation_id=uuid.uuid4(),
            anchor_type="inventory_item",
            anchor_id=uuid.UUID(TEST_EQUIPMENT_ID),
            tenant_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            allowed_domains=["work_orders", "inventory", "faults"],  # Unordered input
        )
        response = get_related(supabase, data)

        # Extract domain order from response
        domain_order = [group.domain for group in response.groups]

        # Should follow FIXED order: inventory < work_orders < faults
        # (from DOMAIN_ORDER in related_expansion.py)
        expected_order = []
        for domain in ["inventory", "work_orders", "faults"]:
            if domain in domain_order:
                expected_order.append(domain)

        assert domain_order == expected_order


# ============================================================================
# PART 4: ADD RELATION TESTS
# ============================================================================

class TestAddRelation:
    """Test add relation creates row + audit event."""

    def test_add_relation_creates_row(self, supabase, test_yacht, test_user):
        """Adding relation creates user_added_relations row."""
        data = AddRelatedRequest(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            from_artefact_type="fault",
            from_artefact_id=uuid.uuid4(),
            to_artefact_type="work_order",
            to_artefact_id=uuid.uuid4(),
        )

        response = add_user_relation(supabase, data)

        # Verify relation created
        assert response.relation_id is not None

        # Verify row exists in DB
        row = supabase.table("user_added_relations").select("*").eq(
            "id", str(response.relation_id)
        ).maybe_single().execute()
        assert row.data is not None
        assert row.data["source"] == "user"

    def test_add_relation_writes_audit_event(self, supabase, test_yacht, test_user):
        """Adding relation writes relation_added audit event."""
        data = AddRelatedRequest(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            from_artefact_type="fault",
            from_artefact_id=uuid.uuid4(),
            to_artefact_type="work_order",
            to_artefact_id=uuid.uuid4(),
        )

        response = add_user_relation(supabase, data)

        # Verify audit event written
        ledger_events = supabase.table("ledger_events").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("event_name", "relation_added").execute()

        # Find event for this relation
        relation_event = [
            e for e in ledger_events.data
            if e["payload"].get("relation_id") == str(response.relation_id)
        ]
        assert len(relation_event) == 1


# ============================================================================
# PART 5: END CONTEXT TESTS
# ============================================================================

class TestEndContext:
    """Test end context sets ended_at + writes audit event."""

    def test_end_context_sets_ended_at(self, supabase, test_yacht, test_user):
        """Ending context sets navigation_contexts.ended_at."""
        # Create context
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="inventory_item",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )
        context = create_navigation_context(supabase, data)

        # End context
        end_navigation_context(
            supabase,
            context.id,
            uuid.UUID(TEST_YACHT_ID),
            uuid.UUID(TEST_USER_ID),
        )

        # Verify ended_at is set
        row = supabase.table("navigation_contexts").select("ended_at").eq(
            "id", str(context.id)
        ).maybe_single().execute()
        assert row.data is not None
        assert row.data["ended_at"] is not None

    def test_end_context_writes_audit_event(self, supabase, test_yacht, test_user):
        """Ending context writes situation_ended audit event."""
        # Create context
        data = NavigationContextCreate(
            yacht_id=uuid.UUID(TEST_YACHT_ID),
            user_id=uuid.UUID(TEST_USER_ID),
            artefact_type="inventory_item",
            artefact_id=uuid.UUID(TEST_EQUIPMENT_ID),
        )
        context = create_navigation_context(supabase, data)

        # End context
        end_navigation_context(
            supabase,
            context.id,
            uuid.UUID(TEST_YACHT_ID),
            uuid.UUID(TEST_USER_ID),
        )

        # Verify audit event written
        ledger_events = supabase.table("ledger_events").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("event_name", "situation_ended").execute()

        # Find event for this context
        context_event = [
            e for e in ledger_events.data
            if e["payload"].get("situation_id") == str(context.id)
        ]
        assert len(context_event) == 1
