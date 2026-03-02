#!/usr/bin/env python3
"""
Generate Truth Sets from Production Supabase
=============================================

Phase A of v1.2 Search Pipeline Truth Hardening.

Queries REAL entity IDs from production Supabase for each of the 12 lenses,
then outputs truth sets with actual UUIDs.

Output Format (per lens):
    truth_sets/{lens}_truth.jsonl

Each line:
    {"entity_id": "uuid", "display_name": "...", "status": "...", "lens": "..."}

Usage:
    python scripts/eval/generate_truth_sets.py
    python scripts/eval/generate_truth_sets.py --lens work_order
    python scripts/eval/generate_truth_sets.py --sample-size 50
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import traceback

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'

OUTPUT_DIR = Path(__file__).parent.parent.parent / "truth_sets"


# =============================================================================
# LENS DEFINITIONS
# =============================================================================

@dataclass
class LensConfig:
    """Configuration for a lens and its database table."""
    lens: str
    table: str
    id_column: str
    display_columns: List[str]  # Columns to use for display_name (first non-null wins)
    status_column: Optional[str]
    extra_columns: List[str]  # Additional columns to include in output
    fallback_table: Optional[str] = None  # Alternative table if primary doesn't exist
    order_by: str = "updated_at DESC NULLS LAST, created_at DESC NULLS LAST"


LENS_CONFIGS: List[LensConfig] = [
    LensConfig(
        lens="work_order",
        table="pms_work_orders",
        id_column="id",
        display_columns=["title", "description"],
        status_column="status",
        extra_columns=["priority", "assigned_to", "due_date"],
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="fault",
        table="pms_faults",
        id_column="id",
        display_columns=["title", "description"],
        status_column="status",
        extra_columns=["severity", "reported_by", "equipment_id"],
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="equipment",
        table="equipment",
        id_column="id",
        display_columns=["name", "model", "manufacturer"],
        status_column="status",
        extra_columns=["category", "location", "serial_number"],
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="part",
        table="pms_parts",
        id_column="id",
        display_columns=["part_name", "name", "part_number"],
        status_column="status",
        extra_columns=["manufacturer", "category", "quantity_on_hand"],
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="inventory",
        table="pms_inventory_stock",
        id_column="id",
        display_columns=["name", "item_name", "part_name"],
        status_column="status",
        extra_columns=["quantity", "location", "category"],
        fallback_table="pms_parts",
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="certificate",
        table="pms_certificates",
        id_column="id",
        display_columns=["name", "certificate_name", "title"],
        status_column="status",
        extra_columns=["certificate_type", "expiry_date", "issuing_authority"],
        fallback_table="pms_vessel_certificates",
        order_by="expiry_date DESC NULLS LAST, updated_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="handover",
        table="handover_items",
        id_column="id",
        display_columns=["section_name", "title", "name"],
        status_column="status",
        extra_columns=["entity_type", "department", "assigned_to"],
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="hours_of_rest",
        table="pms_hours_of_rest",
        id_column="id",
        display_columns=["crew_member_name", "crew_name", "name"],
        status_column=None,  # No status column
        extra_columns=["date", "total_rest_hours", "compliant"],
        order_by="date DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="warranty",
        table="pms_warranty_claims",
        id_column="id",
        display_columns=["name", "warranty_name", "title"],
        status_column="status",
        extra_columns=["expiry_date", "equipment_id", "vendor"],
        order_by="created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="shopping_list",
        table="pms_shopping_list_items",
        id_column="id",
        display_columns=["name", "item_name", "part_name"],
        status_column="status",
        extra_columns=["quantity", "priority", "requested_by"],
        fallback_table="shopping_list_items",
        order_by="updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="email",
        table="emails",
        id_column="id",
        display_columns=["subject", "from_address", "title"],
        status_column="status",
        extra_columns=["thread_id", "received_at", "from_address"],
        fallback_table="email_threads",
        order_by="received_at DESC NULLS LAST, created_at DESC NULLS LAST"
    ),
    LensConfig(
        lens="receiving",
        table="pms_receiving",
        id_column="id",
        display_columns=["vendor_reference", "vendor_name", "title"],
        status_column="status",
        extra_columns=["received_date", "received_by", "total_items"],
        order_by="received_date DESC NULLS LAST, updated_at DESC NULLS LAST"
    ),
]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_connection():
    """Create database connection."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True
    return conn


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        )
    """, (table_name,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result


def get_table_columns(conn, table_name: str) -> List[str]:
    """Get list of columns for a table."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return columns


def has_yacht_id_column(conn, table_name: str) -> bool:
    """Check if table has yacht_id column."""
    columns = get_table_columns(conn, table_name)
    return 'yacht_id' in columns


# =============================================================================
# TRUTH SET GENERATION
# =============================================================================

@dataclass
class TruthEntry:
    """A single entry in a truth set."""
    entity_id: str
    display_name: str
    status: Optional[str]
    lens: str
    extra: Dict[str, Any]


def json_serializer(obj):
    """JSON serializer for objects not serializable by default."""
    from decimal import Decimal
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    raise TypeError(f"Type {type(obj)} not serializable")


def query_lens_entities(
    conn,
    config: LensConfig,
    yacht_id: str,
    sample_size: int = 25
) -> Tuple[List[TruthEntry], str, List[str]]:
    """
    Query entities for a lens from the database.

    Returns:
        (entries, table_used, warnings)
    """
    warnings = []

    # Determine which table to use
    table_to_use = config.table
    if not table_exists(conn, config.table):
        if config.fallback_table and table_exists(conn, config.fallback_table):
            table_to_use = config.fallback_table
            warnings.append(f"Primary table '{config.table}' not found, using fallback '{config.fallback_table}'")
        else:
            return [], "", [f"Table '{config.table}' does not exist (no fallback available)"]

    # Get available columns
    available_columns = get_table_columns(conn, table_to_use)

    # Check for yacht_id column
    has_yacht = 'yacht_id' in available_columns
    if not has_yacht:
        warnings.append(f"Table '{table_to_use}' has no yacht_id column - querying without scope")

    # Build column list for query
    columns_to_select = [config.id_column]

    # Add display columns (only those that exist)
    valid_display_cols = [c for c in config.display_columns if c in available_columns]
    if not valid_display_cols:
        warnings.append(f"No display columns found in {available_columns[:10]}...")
        # Fall back to id as display name
        valid_display_cols = [config.id_column]
    columns_to_select.extend(valid_display_cols)

    # Add status column if exists
    status_col = None
    if config.status_column and config.status_column in available_columns:
        status_col = config.status_column
        columns_to_select.append(status_col)

    # Add extra columns (only those that exist)
    valid_extra_cols = [c for c in config.extra_columns if c in available_columns]
    columns_to_select.extend(valid_extra_cols)

    # Remove duplicates while preserving order
    seen = set()
    unique_columns = []
    for col in columns_to_select:
        if col not in seen:
            seen.add(col)
            unique_columns.append(col)

    # Build query
    select_clause = ", ".join(unique_columns)

    # Determine order by clause (validate columns exist)
    order_parts = []
    for part in config.order_by.split(","):
        part = part.strip()
        col_name = part.split()[0]  # Get column name without DESC/ASC/NULLS
        if col_name in available_columns:
            order_parts.append(part)

    order_clause = ", ".join(order_parts) if order_parts else f"{config.id_column}"

    # Build WHERE clause
    if has_yacht:
        where_clause = "WHERE yacht_id = %s"
        params = (yacht_id, sample_size)
    else:
        where_clause = ""
        params = (sample_size,)

    sql = f"""
        SELECT {select_clause}
        FROM {table_to_use}
        {where_clause}
        ORDER BY {order_clause}
        LIMIT %s
    """

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    except Exception as e:
        cursor.close()
        return [], table_to_use, [f"Query failed: {str(e)}"]

    cursor.close()

    # Convert to TruthEntry objects
    entries = []
    for row in rows:
        row_dict = dict(row)

        # Get entity ID
        entity_id = str(row_dict.get(config.id_column, ''))

        # Build display name from first non-null display column
        display_name = None
        for col in valid_display_cols:
            val = row_dict.get(col)
            if val:
                display_name = str(val)
                break
        if not display_name:
            display_name = entity_id

        # Get status
        status = str(row_dict.get(status_col)) if status_col and row_dict.get(status_col) else None

        # Build extra dict from extra columns
        extra = {}
        for col in valid_extra_cols:
            val = row_dict.get(col)
            if val is not None:
                extra[col] = val

        entries.append(TruthEntry(
            entity_id=entity_id,
            display_name=display_name,
            status=status,
            lens=config.lens,
            extra=extra
        ))

    return entries, table_to_use, warnings


def generate_truth_sets(
    yacht_id: str = DEFAULT_YACHT,
    sample_size: int = 25,
    lenses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate truth sets for all (or specified) lenses.

    Returns summary dict with counts and issues.
    """
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    print(f"Connected to database: {DB_HOST}")
    print(f"Yacht ID: {yacht_id}")
    print(f"Sample size per lens: {sample_size}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)

    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'yacht_id': yacht_id,
        'sample_size': sample_size,
        'lenses': {},
        'tables_found': [],
        'tables_missing': [],
        'total_entities': 0,
    }

    # Filter configs if specific lenses requested
    configs_to_process = LENS_CONFIGS
    if lenses:
        configs_to_process = [c for c in LENS_CONFIGS if c.lens in lenses]
        if not configs_to_process:
            print(f"ERROR: No matching lenses found for: {lenses}")
            print(f"Available lenses: {[c.lens for c in LENS_CONFIGS]}")
            conn.close()
            return summary

    for config in configs_to_process:
        print(f"\n[{config.lens}]")
        print(f"  Primary table: {config.table}")

        entries, table_used, warnings = query_lens_entities(
            conn, config, yacht_id, sample_size
        )

        # Log warnings
        for warning in warnings:
            print(f"  WARNING: {warning}")

        if not entries:
            print(f"  RESULT: No entities found")
            summary['tables_missing'].append(config.table)
            summary['lenses'][config.lens] = {
                'count': 0,
                'table': config.table,
                'warnings': warnings,
                'file': None
            }
            continue

        # Write to JSONL file
        output_file = OUTPUT_DIR / f"{config.lens}_truth.jsonl"
        with open(output_file, 'w') as f:
            for entry in entries:
                entry_dict = {
                    'entity_id': entry.entity_id,
                    'display_name': entry.display_name,
                    'status': entry.status,
                    'lens': entry.lens,
                }
                # Add extra fields
                entry_dict.update(entry.extra)
                f.write(json.dumps(entry_dict, default=json_serializer) + '\n')

        print(f"  Table used: {table_used}")
        print(f"  Entities found: {len(entries)}")
        print(f"  Output: {output_file.name}")

        # Show sample
        if entries:
            sample = entries[0]
            print(f"  Sample: {sample.entity_id[:8]}... | {sample.display_name[:40]}... | {sample.status}")

        summary['tables_found'].append(table_used)
        summary['lenses'][config.lens] = {
            'count': len(entries),
            'table': table_used,
            'warnings': warnings,
            'file': str(output_file)
        }
        summary['total_entities'] += len(entries)

    conn.close()

    # Write summary
    summary_file = OUTPUT_DIR / "generation_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=json_serializer)

    return summary


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate truth sets from production Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate_truth_sets.py
    python generate_truth_sets.py --lens work_order --lens fault
    python generate_truth_sets.py --sample-size 50
    python generate_truth_sets.py --yacht-id abc-123-def
        """
    )
    parser.add_argument(
        '--yacht-id',
        default=DEFAULT_YACHT,
        help=f'Yacht ID to scope queries (default: {DEFAULT_YACHT[:20]}...)'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=25,
        help='Number of entities to sample per lens (default: 25)'
    )
    parser.add_argument(
        '--lens',
        action='append',
        dest='lenses',
        help='Specific lens(es) to generate (can be repeated). If not specified, generates all 12 lenses.'
    )
    parser.add_argument(
        '--list-lenses',
        action='store_true',
        help='List available lenses and exit'
    )

    args = parser.parse_args()

    if args.list_lenses:
        print("Available lenses:")
        for config in LENS_CONFIGS:
            print(f"  {config.lens:20s} -> {config.table}")
        return 0

    print("=" * 70)
    print(" GENERATE TRUTH SETS FROM PRODUCTION SUPABASE")
    print(" Phase A of v1.2 Search Pipeline Truth Hardening")
    print("=" * 70)

    summary = generate_truth_sets(
        yacht_id=args.yacht_id,
        sample_size=args.sample_size,
        lenses=args.lenses
    )

    # Print final summary
    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    print(f"Total lenses processed: {len(summary['lenses'])}")
    print(f"Total entities generated: {summary['total_entities']}")
    print(f"Tables found: {len(summary['tables_found'])}")
    print(f"Tables missing: {len(summary['tables_missing'])}")

    if summary['tables_missing']:
        print(f"\nMissing tables:")
        for table in summary['tables_missing']:
            print(f"  - {table}")

    print(f"\nPer-lens counts:")
    for lens, data in summary['lenses'].items():
        status = f"{data['count']:3d} entities" if data['count'] > 0 else "NO DATA"
        print(f"  {lens:20s}: {status}")

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Summary file: {OUTPUT_DIR / 'generation_summary.json'}")

    if summary['total_entities'] > 0:
        print(f"\nSUCCESS: Generated {summary['total_entities']} truth entries")
        return 0
    else:
        print(f"\nWARNING: No entities generated - check database connection and table names")
        return 1


if __name__ == '__main__':
    sys.exit(main())
