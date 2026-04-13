"""
db.py — direct Supabase client for DB verification and teardown.
Uses service key (bypasses RLS) so we can assert exact DB state.
Never used in the API calls themselves — only for test assertions.
"""
from __future__ import annotations
from typing import Optional
from supabase import create_client

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

_client = None

def client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SERVICE_KEY)
    return _client


def fetch_one(table: str, **filters) -> Optional[dict]:
    """Fetch single row by filters. Returns None if not found.
    Uses list-mode select to avoid supabase-py 2.x .maybe_single() APIError(204) on 0 rows."""
    q = client().table(table).select("*")
    for k, v in filters.items():
        q = q.eq(k, v)
    r = q.limit(1).execute()
    rows = r.data or []
    return rows[0] if rows else None


def fetch_many(table: str, **filters) -> list:
    """Fetch all rows matching filters."""
    q = client().table(table).select("*")
    for k, v in filters.items():
        q = q.eq(k, v)
    r = q.execute()
    return r.data or []


def delete_rows(table: str, ids: list[str], id_col: str = "id"):
    """Delete rows by ID list. Silent if not found."""
    if not ids:
        return
    client().table(table).delete().in_(id_col, ids).execute()
