#!/usr/bin/env python3
"""
Run Migration 43: Seed Adversarial Keywords

Executes the SQL migration to seed learned_keywords for Shard 11 tests.
"""

import os
import sys

def main():
    # Read the migration SQL
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'database/migrations/43_seed_adversarial_keywords.sql'
    )

    print(f"Reading migration from: {migration_path}")

    with open(migration_path, 'r') as f:
        sql = f.read()

    print(f"\n{'='*80}")
    print("Migration 43: Seed Adversarial Keywords")
    print(f"{'='*80}\n")

    print("SQL Preview (first 50 lines):")
    print('\n'.join(sql.split('\n')[:50]))
    print("\n...")

    print(f"\n{'='*80}")
    print("MANUAL EXECUTION REQUIRED")
    print(f"{'='*80}\n")

    print("To execute this migration:")
    print("1. Open Supabase Dashboard: https://app.supabase.com/project/vzsohavtuotocgrfkfyd/editor")
    print("2. Go to SQL Editor")
    print("3. Create a new query")
    print(f"4. Copy and paste the contents of: {migration_path}")
    print("5. Click 'Run' to execute")

    print("\nAlternatively, if you have psql with database credentials:")
    print(f"psql $DATABASE_URL < {migration_path}")

    print(f"\n{'='*80}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
