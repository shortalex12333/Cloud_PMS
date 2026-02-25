#!/usr/bin/env python3
"""
Fix truth set JSONL files by updating the target_type field in canonical.
"""

import json
import os

# Define the files and their correct target_type values
TRUTHSET_FIXES = {
    "truthset_document.jsonl": "document",
    "truthset_fault.jsonl": "fault",
    "truthset_inventory.jsonl": "inventory",
    "truthset_work_order_note.jsonl": "work_order_note",
    "truthset_work_order.jsonl": "work_order",
}

BASE_DIR = "/Volumes/Backup/CELESTE"


def fix_truthset_file(filename: str, target_type: str) -> int:
    """
    Fix a single truth set file by updating canonical.target_type.

    Args:
        filename: Name of the JSONL file
        target_type: The correct target_type value to set

    Returns:
        Number of records fixed
    """
    filepath = os.path.join(BASE_DIR, filename)

    if not os.path.exists(filepath):
        print(f"  WARNING: File not found: {filepath}")
        return 0

    # Read all lines
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_records = []
    count = 0

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)

            # Update canonical.target_type
            if 'canonical' in record:
                old_type = record['canonical'].get('target_type', '<missing>')
                record['canonical']['target_type'] = target_type
                count += 1
            else:
                print(f"  WARNING: Line {line_num} missing 'canonical' key")

            fixed_records.append(record)

        except json.JSONDecodeError as e:
            print(f"  ERROR: Line {line_num} invalid JSON: {e}")
            continue

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        for record in fixed_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    return count


def main():
    print("=" * 60)
    print("Truth Set Target Type Fix Script")
    print("=" * 60)
    print()

    total_fixed = 0

    for filename, target_type in TRUTHSET_FIXES.items():
        print(f"Processing: {filename}")
        print(f"  Setting target_type to: {target_type}")

        count = fix_truthset_file(filename, target_type)
        total_fixed += count

        print(f"  Records fixed: {count}")
        print()

    print("=" * 60)
    print(f"Total records fixed: {total_fixed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
