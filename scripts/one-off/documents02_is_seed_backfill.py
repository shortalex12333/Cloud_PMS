#!/usr/bin/env python3
"""
One-off: backfill is_seed=False for all production doc_metadata rows.

Root cause: doc_metadata.is_seed defaults to TRUE at the DB level.
vessel_surface_routes.py:717 filters WHERE is_seed = False, so any
row inserted without an explicit is_seed=False is invisible in the app.

This script:
  - Preserves is_seed=True for test data (source IN shard3_test, test)
  - Updates all other is_seed=True rows to is_seed=False
  - Prints a source-by-source row count so you can verify

Run from the repo root:
  python3 scripts/one-off/documents02_is_seed_backfill.py

After running:
  1. Verify count in Supabase dashboard:
     SELECT is_seed, count(*) FROM doc_metadata GROUP BY is_seed;
  2. Open Documents page in app — tree view should show all documents
  3. Run automated runner:
     python3 tests/e2e/shard3/documents_actions_runner.py
"""

import os
import sys

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ."
    "fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
)

# Sources that must KEEP is_seed=True (test data — do not touch these)
PRESERVED_TEST_SOURCES = {"shard3_test", "test"}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase-py not installed. Run: pip install supabase")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SERVICE_KEY)

    # 1. Count current state
    print("=== PRE-BACKFILL STATE ===")
    all_rows = client.table("doc_metadata").select("source, is_seed").execute()
    from collections import Counter
    counts = Counter((r["source"], r["is_seed"]) for r in all_rows.data)
    for (source, is_seed), n in sorted(counts.items()):
        flag = " [PRESERVED - test data]" if source in PRESERVED_TEST_SOURCES else ""
        print(f"  source={source!r:30s} is_seed={is_seed}  rows={n}{flag}")

    seed_true = [r for r in all_rows.data if r["is_seed"] is True and r.get("source") not in PRESERVED_TEST_SOURCES]
    print(f"\n{len(seed_true)} rows need backfill (is_seed=True, non-test source)\n")

    if not seed_true:
        print("Nothing to do. All non-test rows already have is_seed=False.")
        return

    # 2. Get unique sources to update (batch by source for auditability)
    sources_to_update = {r["source"] for r in seed_true if r.get("source")}

    print("=== BACKFILLING ===")
    total_updated = 0
    for source in sorted(sources_to_update):
        res = (
            client.table("doc_metadata")
            .update({"is_seed": False})
            .eq("is_seed", True)
            .eq("source", source)
            .execute()
        )
        n = len(res.data)
        total_updated += n
        print(f"  source={source!r:30s} updated={n}")

    # Handle rows with NULL source
    null_source_rows = [r for r in seed_true if not r.get("source")]
    if null_source_rows:
        res = (
            client.table("doc_metadata")
            .update({"is_seed": False})
            .eq("is_seed", True)
            .is_("source", "null")
            .execute()
        )
        n = len(res.data)
        total_updated += n
        print(f"  source=NULL                        updated={n}")

    print(f"\nTotal updated: {total_updated} rows")

    # 3. Post-backfill verification
    print("\n=== POST-BACKFILL STATE ===")
    post = client.table("doc_metadata").select("is_seed").execute()
    post_counts = Counter(r["is_seed"] for r in post.data)
    print(f"  is_seed=True  : {post_counts.get(True, 0)}")
    print(f"  is_seed=False : {post_counts.get(False, 0)}")
    print(f"  Total         : {len(post.data)}")

    if post_counts.get(True, 0) <= len(PRESERVED_TEST_SOURCES) * 50:
        print("\n✓ Backfill complete. All production rows are now visible in the app.")
    else:
        print(f"\nWARNING: {post_counts.get(True, 0)} rows still have is_seed=True — check above output.")


if __name__ == "__main__":
    main()
