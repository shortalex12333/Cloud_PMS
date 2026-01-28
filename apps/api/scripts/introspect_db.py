"""
DB Truth Snapshot Generator
Connects to Supabase Postgres and extracts complete schema information.
NO GUESSING. Only what exists in production.

Usage:
    python introspect_db.py

Outputs:
    - docs/architecture/db_truth_snapshot.md
    - docs/architecture/db_truth_snapshot.json
"""

import psycopg2
import json
from datetime import datetime
from collections import defaultdict

# Supabase Postgres connection
# Format: postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
SUPABASE_DB_URL = "postgresql://postgres:%40-Ei-9Pa.uENn6g@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"

# Priority tables for Fault Lens
FAULT_LENS_TABLES = [
    'pms_faults',
    'pms_work_orders',
    'pms_audit_log',
    'decision_audit_log',
    'related_audit_events',
    'pms_fault_notes',
    'pms_fault_attachments',
]

# For log_part_usage action analysis
PART_USAGE_TABLE = 'pms_part_usage'


def connect_db():
    """Connect to Postgres"""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease update SUPABASE_DB_URL with your database password.")
        print("Format: postgresql://postgres.vzsohavtuotocgrfkfyd:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
        exit(1)


def get_tables(cursor):
    """Get all tables in public schema"""
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    return [row[0] for row in cursor.fetchall()]


def get_columns(cursor, table_name):
    """Get columns for a table"""
    cursor.execute("""
        SELECT
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            is_identity,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))

    columns = []
    for row in cursor.fetchall():
        columns.append({
            'name': row[0],
            'type': row[1],
            'udt_name': row[2],
            'nullable': row[3] == 'YES',
            'default': row[4],
            'is_identity': row[5] == 'YES',
            'max_length': row[6],
        })
    return columns


def get_constraints(cursor, table_name):
    """Get all constraints for a table"""
    # Primary Keys
    cursor.execute("""
        SELECT
            tc.constraint_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
        AND tc.table_name = %s
        AND tc.constraint_type = 'PRIMARY KEY';
    """, (table_name,))
    pk = [row[1] for row in cursor.fetchall()]

    # Foreign Keys
    cursor.execute("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND tc.table_name = %s;
    """, (table_name,))
    fks = []
    for row in cursor.fetchall():
        fks.append({
            'constraint_name': row[0],
            'column': row[1],
            'references_table': row[2],
            'references_column': row[3],
            'on_update': row[4],
            'on_delete': row[5],
        })

    # Unique Constraints
    cursor.execute("""
        SELECT
            tc.constraint_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
        AND tc.table_name = %s
        AND tc.constraint_type = 'UNIQUE'
        ORDER BY tc.constraint_name, kcu.ordinal_position;
    """, (table_name,))
    uniques = defaultdict(list)
    for row in cursor.fetchall():
        uniques[row[0]].append(row[1])
    unique_constraints = [{'name': k, 'columns': v} for k, v in uniques.items()]

    # Check Constraints
    cursor.execute("""
        SELECT
            constraint_name,
            check_clause
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'public'
        AND constraint_name IN (
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
            AND table_name = %s
        );
    """, (table_name,))
    checks = [{'name': row[0], 'clause': row[1]} for row in cursor.fetchall()]

    return {
        'primary_key': pk,
        'foreign_keys': fks,
        'unique': unique_constraints,
        'check': checks,
    }


def get_indexes(cursor, table_name):
    """Get indexes for a table"""
    cursor.execute("""
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename = %s
        ORDER BY indexname;
    """, (table_name,))
    return [{'name': row[0], 'definition': row[1]} for row in cursor.fetchall()]


def get_rls_policies(cursor, table_name):
    """Get RLS policies for a table"""
    # Check if RLS is enabled
    cursor.execute("""
        SELECT relrowsecurity
        FROM pg_class
        WHERE relname = %s
        AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
    """, (table_name,))
    result = cursor.fetchone()
    rls_enabled = result[0] if result else False

    # Get policies
    cursor.execute("""
        SELECT
            policyname,
            permissive,
            roles,
            cmd,
            qual,
            with_check
        FROM pg_policies
        WHERE schemaname = 'public'
        AND tablename = %s
        ORDER BY policyname;
    """, (table_name,))

    policies = []
    for row in cursor.fetchall():
        policies.append({
            'name': row[0],
            'permissive': row[1],
            'roles': row[2],
            'command': row[3],
            'using': row[4],
            'with_check': row[5],
        })

    return {
        'enabled': rls_enabled,
        'policies': policies,
    }


def get_triggers(cursor, table_name):
    """Get triggers for a table"""
    cursor.execute("""
        SELECT
            trigger_name,
            event_manipulation,
            action_timing,
            action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        AND event_object_table = %s
        ORDER BY trigger_name;
    """, (table_name,))

    triggers = []
    for row in cursor.fetchall():
        triggers.append({
            'name': row[0],
            'event': row[1],
            'timing': row[2],
            'action': row[3],
        })
    return triggers


def get_enums(cursor):
    """Get all enum types and their values"""
    cursor.execute("""
        SELECT
            t.typname AS enum_name,
            array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        GROUP BY t.typname
        ORDER BY t.typname;
    """)

    enums = {}
    for row in cursor.fetchall():
        enums[row[0]] = row[1]
    return enums


def get_row_count(cursor, table_name):
    """Get approximate row count"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]
    except:
        return None


def generate_markdown(snapshot):
    """Generate markdown documentation"""
    md = [f"# DB Truth Snapshot"]
    md.append(f"**Generated**: {snapshot['generated_at']}")
    md.append(f"**Source**: Production Supabase Database")
    md.append(f"**Total Tables**: {len(snapshot['tables'])}\n")
    md.append("---\n")

    # Enums first
    if snapshot['enums']:
        md.append("## Enum Types\n")
        for enum_name, values in sorted(snapshot['enums'].items()):
            md.append(f"### `{enum_name}`")
            md.append(f"Values: {', '.join([f'`{v}`' for v in values])}\n")
        md.append("---\n")

    # Tables
    md.append("## Tables\n")

    # Fault Lens tables first
    for table_name in FAULT_LENS_TABLES:
        if table_name in snapshot['tables']:
            md.extend(format_table_md(table_name, snapshot['tables'][table_name]))
        else:
            md.append(f"### ❌ MISSING: `{table_name}`")
            md.append("**Status**: Table does not exist in production database.\n")

    # Other tables
    for table_name, table_data in sorted(snapshot['tables'].items()):
        if table_name not in FAULT_LENS_TABLES:
            md.extend(format_table_md(table_name, table_data))

    return '\n'.join(md)


def format_table_md(table_name, table_data):
    """Format a single table as markdown"""
    md = [f"### `{table_name}`"]

    if table_data.get('row_count') is not None:
        md.append(f"**Row Count**: {table_data['row_count']:,}")

    # Columns
    md.append(f"\n**Columns** ({len(table_data['columns'])}):\n")
    md.append("| Column | Type | Nullable | Default | Notes |")
    md.append("|--------|------|----------|---------|-------|")
    for col in table_data['columns']:
        nullable = 'YES' if col['nullable'] else 'NO'
        default = col['default'] or ''
        notes = []
        if col['is_identity']:
            notes.append('IDENTITY')
        if col['udt_name'] and col['udt_name'] != col['type']:
            notes.append(f"enum: {col['udt_name']}")
        notes_str = ', '.join(notes)
        md.append(f"| `{col['name']}` | {col['type']} | {nullable} | {default} | {notes_str} |")

    # Constraints
    constraints = table_data['constraints']
    md.append("\n**Constraints**:")
    if constraints['primary_key']:
        md.append(f"- **PK**: {', '.join([f'`{c}`' for c in constraints['primary_key']])}")
    for fk in constraints['foreign_keys']:
        md.append(f"- **FK**: `{fk['column']}` → `{fk['references_table']}({fk['references_column']})` ON DELETE {fk['on_delete']}, ON UPDATE {fk['on_update']}")
    for uniq in constraints['unique']:
        md.append(f"- **UNIQUE**: {', '.join([f'`{c}`' for c in uniq['columns']])}")
    for check in constraints['check']:
        md.append(f"- **CHECK** `{check['name']}`: {check['clause']}")

    # Indexes
    if table_data['indexes']:
        md.append(f"\n**Indexes** ({len(table_data['indexes'])}):")
        for idx in table_data['indexes']:
            md.append(f"- `{idx['name']}`")
            md.append(f"  ```sql\n  {idx['definition']}\n  ```")

    # RLS
    rls = table_data['rls']
    md.append(f"\n**RLS**: {'✅ ENABLED' if rls['enabled'] else '❌ DISABLED'}")
    if rls['policies']:
        md.append(f"**Policies** ({len(rls['policies'])}):")
        for policy in rls['policies']:
            md.append(f"- **{policy['name']}** ({policy['command']})")
            md.append(f"  - Roles: {policy['roles']}")
            if policy['using']:
                md.append(f"  - USING: `{policy['using']}`")
            if policy['with_check']:
                md.append(f"  - WITH CHECK: `{policy['with_check']}`")

    # Triggers
    if table_data['triggers']:
        md.append(f"\n**Triggers** ({len(table_data['triggers'])}):")
        for trigger in table_data['triggers']:
            md.append(f"- `{trigger['name']}` ({trigger['timing']} {trigger['event']})")
            md.append(f"  - Action: {trigger['action']}")

    md.append("\n---\n")
    return md


def main():
    print("🔍 Connecting to Supabase Postgres...")
    conn = connect_db()
    cursor = conn.cursor()

    print("✅ Connected. Introspecting schema...\n")

    # Get all data
    tables = get_tables(cursor)
    enums = get_enums(cursor)

    snapshot = {
        'generated_at': datetime.now().isoformat(),
        'total_tables': len(tables),
        'enums': enums,
        'tables': {},
    }

    # Check for missing fault lens tables
    missing_tables = [t for t in FAULT_LENS_TABLES if t not in tables]
    if missing_tables:
        print(f"⚠️  WARNING: Missing fault lens tables: {', '.join(missing_tables)}\n")

    # Introspect each table
    for table_name in tables:
        is_priority = table_name in FAULT_LENS_TABLES
        prefix = "🎯" if is_priority else "📋"
        print(f"{prefix} Introspecting {table_name}...")

        snapshot['tables'][table_name] = {
            'columns': get_columns(cursor, table_name),
            'constraints': get_constraints(cursor, table_name),
            'indexes': get_indexes(cursor, table_name),
            'rls': get_rls_policies(cursor, table_name),
            'triggers': get_triggers(cursor, table_name),
            'row_count': get_row_count(cursor, table_name),
        }

    # Special analysis for pms_part_usage
    if PART_USAGE_TABLE in snapshot['tables']:
        print(f"\n🔬 Analyzing {PART_USAGE_TABLE} for log_part_usage action...")
        analyze_part_usage_fields(snapshot['tables'][PART_USAGE_TABLE])

    cursor.close()
    conn.close()

    # Write outputs
    print("\n💾 Writing outputs...")

    # JSON
    json_path = '../../../docs/architecture/db_truth_snapshot.json'
    with open(json_path, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"   ✅ {json_path}")

    # Markdown
    md_path = '../../../docs/architecture/db_truth_snapshot.md'
    with open(md_path, 'w') as f:
        f.write(generate_markdown(snapshot))
    print(f"   ✅ {md_path}")

    print("\n✨ DB Truth Snapshot complete.")
    print(f"   Tables: {len(tables)}")
    print(f"   Enums: {len(enums)}")
    if missing_tables:
        print(f"\n⚠️  MISSING TABLES: {', '.join(missing_tables)}")
        print("   These must be created before Fault Lens work can proceed.")


def analyze_part_usage_fields(table_data):
    """Classify pms_part_usage fields for log_part_usage microaction"""
    print("\n" + "="*80)
    print("FIELD CLASSIFICATION: log_part_usage microaction")
    print("="*80)

    columns = {col['name']: col for col in table_data['columns']}

    # Required from user (Paramount)
    required = []
    for col_name in ['quantity']:
        if col_name in columns:
            col = columns[col_name]
            if not col['nullable'] and not col['default']:
                required.append(col_name)

    # Optional from user
    optional = []
    for col_name in ['work_order_id', 'equipment_id', 'usage_reason', 'notes']:
        if col_name in columns:
            col = columns[col_name]
            if col['nullable']:
                optional.append(col_name)

    # Auto-populated by backend
    auto = []
    for col_name in ['id', 'yacht_id', 'part_id', 'used_by', 'used_at', 'metadata']:
        if col_name in columns:
            col = columns[col_name]
            if col['default'] or col_name in ['yacht_id', 'part_id', 'used_by']:
                auto.append(col_name)

    print("\n**REQUIRED** (user must provide):")
    for field in required:
        print(f"  - {field}")

    print("\n**OPTIONAL** (user can provide):")
    for field in optional:
        print(f"  - {field}")

    print("\n**AUTO** (backend always sets):")
    for field in auto:
        col = columns[field]
        note = ""
        if col['default']:
            note = f" (default: {col['default']})"
        elif field in ['yacht_id', 'part_id']:
            note = " (from context)"
        elif field == 'used_by':
            note = " (from session: auth.uid())"
        print(f"  - {field}{note}")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
