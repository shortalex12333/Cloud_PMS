"""Integration test: verify _patch_maybe_single_204 handles 204 and re-raises others."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Trigger the patch
import handlers.db_client  # noqa: F401

from supabase import create_client
from postgrest.exceptions import APIError


SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


@pytest.fixture
def db():
    if not SUPABASE_SERVICE_KEY:
        pytest.skip("SUPABASE_SERVICE_KEY not set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def test_maybe_single_returns_none_for_nonexistent_row(db):
    """Query an id that cannot exist. Should return None, not raise."""
    result = (
        db.table("search_index")
        .select("id")
        .eq("id", -1)
        .maybe_single()
        .execute()
    )
    assert result is None


def test_maybe_single_propagates_non_204_errors(db):
    """Query a table that doesn't exist. Should raise APIError, not return None."""
    with pytest.raises(APIError):
        db.table("nonexistent_table_xyz").select("*").maybe_single().execute()


def test_patch_is_applied():
    """Verify the monkey-patch replaced the execute method."""
    from postgrest import SyncMaybeSingleRequestBuilder
    assert SyncMaybeSingleRequestBuilder.execute.__name__ == "_safe_execute"
