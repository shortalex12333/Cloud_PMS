#!/usr/bin/env python3
"""
CelesteOS - Audit Evidence Export CLI
=====================================

Export compliance evidence bundle for SOC2/ISO audits.

Usage:
    python scripts/compliance/export_audit_evidence.py \
        --yacht-id YACHT-001 \
        --start 2026-01-01T00:00:00Z \
        --end 2026-01-31T23:59:59Z \
        --out test-results/evidence

    # With user filter:
    python scripts/compliance/export_audit_evidence.py \
        --yacht-id YACHT-001 \
        --user-id USER-001 \
        --start 2026-01-01T00:00:00Z \
        --end 2026-01-31T23:59:59Z \
        --out test-results/evidence

Output:
    evidence/<yacht_id>/<timestamp>/
    ├── index.json
    ├── memberships.jsonl
    ├── role_changes.jsonl
    ├── admin_actions.jsonl
    ├── router_audits.jsonl
    ├── storage_signing.jsonl
    ├── incident_events.jsonl
    ├── cache_invalidations.jsonl
    ├── summary.csv
    ├── README.md
    └── bundle.zip
"""

import argparse
import asyncio
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add apps/api to path for imports
API_PATH = Path(__file__).parent.parent.parent / "apps" / "api"
sys.path.insert(0, str(API_PATH))


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def validate_timestamp(ts: str) -> bool:
    """Validate ISO 8601 timestamp."""
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Export audit evidence bundle for compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all activity for a yacht in Q1 2026
  python export_audit_evidence.py \\
    --yacht-id YACHT-001 \\
    --start 2026-01-01T00:00:00Z \\
    --end 2026-03-31T23:59:59Z \\
    --out evidence

  # Export specific user activity
  python export_audit_evidence.py \\
    --yacht-id YACHT-001 \\
    --user-id USER-001 \\
    --start 2026-01-01T00:00:00Z \\
    --end 2026-01-31T23:59:59Z \\
    --out evidence
        """,
    )

    parser.add_argument(
        "--yacht-id",
        required=True,
        help="Yacht ID to export evidence for",
    )
    parser.add_argument(
        "--user-id",
        required=False,
        help="Optional user ID filter",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start timestamp (ISO 8601, UTC). Example: 2026-01-01T00:00:00Z",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End timestamp (ISO 8601, UTC). Example: 2026-01-31T23:59:59Z",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output base directory. Bundle will be created at <out>/<yacht-id>/<timestamp>/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print parameters without executing export",
    )

    args = parser.parse_args()

    # Validate timestamps
    if not validate_timestamp(args.start):
        print(f"ERROR: Invalid start timestamp: {args.start}")
        print("Expected format: 2026-01-01T00:00:00Z")
        sys.exit(1)

    if not validate_timestamp(args.end):
        print(f"ERROR: Invalid end timestamp: {args.end}")
        print("Expected format: 2026-01-31T23:59:59Z")
        sys.exit(1)

    # Build output path
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / args.yacht_id / timestamp

    # Get git commit
    git_commit = get_git_commit()

    # Build command args for index.json
    command_args = " ".join(sys.argv)

    print("=" * 60)
    print("CelesteOS Audit Evidence Export")
    print("=" * 60)
    print(f"Yacht ID:     {args.yacht_id}")
    print(f"User ID:      {args.user_id or 'All users'}")
    print(f"Start:        {args.start}")
    print(f"End:          {args.end}")
    print(f"Output:       {out_dir}")
    print(f"Git Commit:   {git_commit}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] No export performed.")
        sys.exit(0)

    # Import and run export
    try:
        from services.audit_export import export_audit_trace
    except ImportError as e:
        print(f"ERROR: Failed to import audit_export service: {e}")
        print("Make sure you're running from the project root.")
        sys.exit(1)

    # Get database client
    try:
        # Try to get the master client
        master_url = os.getenv("MASTER_SUPABASE_URL")
        master_key = os.getenv("MASTER_SUPABASE_SERVICE_KEY")

        if not master_url or not master_key:
            print("ERROR: MASTER_SUPABASE_URL and MASTER_SUPABASE_SERVICE_KEY must be set")
            print("\nFor local testing, you can use a mock client:")
            print("  export MASTER_SUPABASE_URL=https://your-project.supabase.co")
            print("  export MASTER_SUPABASE_SERVICE_KEY=your-service-key")
            sys.exit(1)

        from supabase import create_client
        db_client = create_client(master_url, master_key)

    except Exception as e:
        print(f"ERROR: Failed to create database client: {e}")
        sys.exit(1)

    # Run export
    try:
        print("\nStarting export...")
        bundle_path = await export_audit_trace(
            db_client=db_client,
            yacht_id=args.yacht_id,
            start_ts=args.start,
            end_ts=args.end,
            out_dir=str(out_dir),
            user_id=args.user_id,
            git_commit=git_commit,
            command_args=command_args,
        )

        print("\n" + "=" * 60)
        print("Export Complete!")
        print("=" * 60)
        print(f"Bundle:   {bundle_path}")
        print(f"Index:    {out_dir / 'index.json'}")
        print(f"Summary:  {out_dir / 'summary.csv'}")
        print("=" * 60)

        # Print summary
        import json
        with open(out_dir / "index.json") as f:
            index = json.load(f)

        print("\nRecord Counts:")
        for category, count in index.get("record_counts", {}).items():
            print(f"  {category}: {count}")

        print("\nTo verify the bundle:")
        print(f"  unzip -l {bundle_path}")
        print(f"  cat {out_dir / 'README.md'}")

    except Exception as e:
        print(f"\nERROR: Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
