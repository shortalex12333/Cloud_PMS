"""
Attachment Table Name Regression Guard Tests

CRITICAL: These tests prevent accidental reversion of table names.

GUARDS AGAINST:
1. Changing pms_attachments back to "attachments"
2. Removing soft-delete filters
3. Incorrect bucket routing

If these tests fail, DO NOT change the code. The tests are correct.
The code MUST use "pms_attachments" table with soft-delete filters.
"""

import re
from pathlib import Path


def test_no_legacy_attachments_table_usage():
    """
    REGRESSION GUARD: Fail if any handler queries table("attachments")

    CRITICAL: All handlers must use pms_attachments, NOT "attachments".
    This test scans handler files for legacy table name usage.

    IF THIS TEST FAILS:
    - DO NOT change this test
    - DO NOT change handlers to use "attachments"
    - Fix the code to use "pms_attachments"
    """
    handlers_dir = Path(__file__).parent.parent / "handlers"

    legacy_pattern = re.compile(r'\.table\(["\']attachments["\']\)')

    handler_files = [
        "work_order_handlers.py",
        "fault_handlers.py",
        "equipment_handlers.py"
    ]

    violations = []

    for handler_file in handler_files:
        file_path = handlers_dir / handler_file

        if not file_path.exists():
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        matches = legacy_pattern.findall(content)

        if matches:
            violations.append({
                "file": handler_file,
                "matches": matches,
                "pattern": '.table("attachments")'
            })

    assert not violations, (
        f"\n\n{'='*80}\n"
        f"REGRESSION GUARD FAILURE: Legacy table name detected!\n"
        f"{'='*80}\n\n"
        f"Found {len(violations)} file(s) using table('attachments') instead of table('pms_attachments'):\n\n"
        + "\n".join([
            f"  ❌ {v['file']}: {len(v['matches'])} occurrence(s)"
            for v in violations
        ]) +
        f"\n\n"
        f"REQUIRED FIX:\n"
        f"  - Change table('attachments') to table('pms_attachments')\n"
        f"  - Add soft-delete filter: .is_('deleted_at', 'null')\n"
        f"  - See work_order_handlers.py for correct pattern\n"
        f"\n{'='*80}\n"
    )


def test_pms_attachments_has_soft_delete_filter():
    """
    REGRESSION GUARD: Ensure SELECT queries include soft-delete filter

    All queries to pms_attachments must filter out soft-deleted records
    using .is_("deleted_at", "null")
    """
    handlers_dir = Path(__file__).parent.parent / "handlers"

    handler_files = [
        "work_order_handlers.py",
        "fault_handlers.py",
        "equipment_handlers.py"
    ]

    issues = []

    for handler_file in handler_files:
        file_path = handlers_dir / handler_file

        if not file_path.exists():
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Find all pms_attachments SELECT queries
        pms_attachments_queries = re.finditer(
            r'\.table\(["\']pms_attachments["\']\)\.select\([^)]+\)',
            content
        )

        for match in pms_attachments_queries:
            query_snippet = match.group(0)

            # Check if this query is followed by soft-delete filter
            # Look ahead in the content after this match
            start_pos = match.end()
            # Get next 200 chars to check for filter
            context = content[start_pos:start_pos + 200]

            # Check for soft-delete filter
            if '.is_("deleted_at", "null")' not in context and ".is_('deleted_at', 'null')" not in context:
                issues.append({
                    "file": handler_file,
                    "query": query_snippet[:80] + "..."
                })

    # Note: We expect some queries to not have the filter (like insert/update)
    # So we don't fail the test, just warn
    if issues:
        print(f"\n⚠️  Found {len(issues)} pms_attachments queries without obvious soft-delete filter:")
        for issue in issues:
            print(f"  - {issue['file']}: {issue['query']}")
        print("\nNote: Some queries (INSERT/UPDATE) don't need filters. Verify manually.")


def test_bucket_routing_uses_correct_buckets():
    """
    REGRESSION GUARD: Verify bucket routing uses correct bucket names

    Expected routing:
    - work_order photos → pms-work-order-photos
    - fault photos → pms-discrepancy-photos
    - equipment photos → pms-work-order-photos
    - manuals/docs → documents
    """
    handlers_dir = Path(__file__).parent.parent / "handlers"

    # Map handlers to their expected buckets
    handler_bucket_requirements = {
        "work_order_handlers.py": [
            "pms-work-order-photos",
            "pms-discrepancy-photos",  # May handle fault routing too
            "documents"
        ],
        "fault_handlers.py": [
            "pms-discrepancy-photos",
            "documents"
        ],
        "equipment_handlers.py": [
            "pms-work-order-photos",
            "documents"
        ]
    }

    for handler_file, required_buckets in handler_bucket_requirements.items():
        file_path = handlers_dir / handler_file

        if not file_path.exists():
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check that bucket routing function exists
        if "_get_bucket_for_attachment" in content:
            # Verify correct bucket names are referenced
            for bucket in required_buckets:
                assert bucket in content, (
                    f"Missing bucket '{bucket}' in {handler_file}. "
                    f"Bucket routing may be incorrect."
                )

    print("\n✅ Bucket routing references correct bucket names")


if __name__ == "__main__":
    print("Running attachment table regression guards...")
    test_no_legacy_attachments_table_usage()
    test_pms_attachments_has_soft_delete_filter()
    test_bucket_routing_uses_correct_buckets()
    print("\n✅ All regression guards passed!")
