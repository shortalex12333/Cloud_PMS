#!/usr/bin/env python3
"""
Sanitize corrupted truth set files for the F1 Cortex search pipeline.

Handles:
- Garbage data (xxxxx patterns) in titles and queries
- Sparse/short queries
- Duplicate items with same expected_target_id

Usage:
    python sanitize_truth_sets.py [--dry-run]
"""

import argparse
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Configuration
TRUTH_SETS_DIR = Path("/Volumes/Backup/CELESTE")

TRUTH_SET_FILES = [
    "truthset_fault.jsonl",
    "truthset_receiving.jsonl",
    "truthset_work_order_note.jsonl",
]

# Detection patterns
GARBAGE_PATTERN = re.compile(r"x{5,}", re.IGNORECASE)
MIN_QUERY_LENGTH = 3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class SanitizationStats:
    """Track sanitization statistics for a single file."""

    file_name: str
    total_items: int = 0
    garbage_queries_fixed: int = 0
    garbage_titles_fixed: int = 0
    duplicates_removed: int = 0
    items_after_sanitization: int = 0
    errors: list[str] = field(default_factory=list)


def is_garbage_text(text: str) -> bool:
    """Check if text contains garbage data (5+ consecutive x's or too short)."""
    if not text or not isinstance(text, str):
        return True
    if len(text.strip()) < MIN_QUERY_LENGTH:
        return True
    if GARBAGE_PATTERN.search(text):
        return True
    return False


def extract_target_type(file_name: str) -> str:
    """Extract target type from filename (e.g., truthset_fault.jsonl -> fault)."""
    stem = Path(file_name).stem
    if stem.startswith("truthset_"):
        return stem[len("truthset_") :]
    return stem


def get_id_suffix(target_id: str) -> str:
    """Get last 8 characters of target_id for uniqueness."""
    if not target_id:
        return "unknown"
    return target_id[-8:] if len(target_id) >= 8 else target_id


def generate_fault_query(item: dict[str, Any], target_id: str) -> str:
    """Generate replacement query for fault items."""
    canonical = item.get("canonical", {})

    # Try to extract meaningful metadata
    short_id = get_id_suffix(target_id)
    equipment_context = canonical.get("equipment_context", "")
    equipment_name = canonical.get("equipment_name", "")
    fault_code = canonical.get("fault_code", "")

    # Build context string from available data
    context_parts = []
    if fault_code:
        context_parts.append(fault_code)
    if equipment_name:
        context_parts.append(equipment_name)
    elif equipment_context:
        context_parts.append(equipment_context)

    context = " ".join(context_parts) if context_parts else "equipment"

    return f"Fault {short_id} {context}".strip()


def generate_receiving_query(item: dict[str, Any], target_id: str) -> str:
    """Generate replacement query for receiving items."""
    canonical = item.get("canonical", {})

    supplier_name = canonical.get("supplier_name", "")
    vendor_name = canonical.get("vendor_name", "")
    date = canonical.get("date", "")
    receipt_date = canonical.get("receipt_date", "")

    supplier = supplier_name or vendor_name or "supplier"
    receipt_dt = date or receipt_date or ""

    short_id = get_id_suffix(target_id)

    if receipt_dt:
        return f"Receipt for {supplier} {receipt_dt} {short_id}".strip()
    return f"Receipt for {supplier} {short_id}".strip()


def generate_work_order_note_query(item: dict[str, Any], target_id: str) -> str:
    """Generate replacement query for work order note items."""
    canonical = item.get("canonical", {})

    wo_id = canonical.get("wo_id", "")
    work_order_id = canonical.get("work_order_id", "")
    hours = canonical.get("hours", "")
    logged_hours = canonical.get("logged_hours", "")

    wo = wo_id or work_order_id or get_id_suffix(target_id)
    hrs = hours or logged_hours or ""

    short_id = get_id_suffix(target_id)

    if hrs:
        return f"Note for WO-{wo} logged {hrs} {short_id}".strip()
    return f"Note for WO-{wo} {short_id}".strip()


def generate_replacement_query(
    item: dict[str, Any], target_type: str, target_id: str
) -> str:
    """Generate a deterministic replacement query based on item metadata."""
    generators = {
        "fault": generate_fault_query,
        "receiving": generate_receiving_query,
        "work_order_note": generate_work_order_note_query,
    }

    generator = generators.get(target_type)
    if generator:
        return generator(item, target_id)

    # Fallback for unknown types
    short_id = get_id_suffix(target_id)
    return f"{target_type.replace('_', ' ').title()} {short_id}"


def generate_replacement_title(
    item: dict[str, Any], target_type: str, target_id: str
) -> str:
    """Generate a deterministic replacement title based on item metadata."""
    short_id = get_id_suffix(target_id)
    type_name = target_type.replace("_", " ").title()
    return f"{type_name} Record {short_id}"


def sanitize_item(
    item: dict[str, Any], target_type: str, stats: SanitizationStats
) -> dict[str, Any]:
    """Sanitize a single truth set item, fixing garbage data."""
    # Deep copy to avoid modifying original
    sanitized = json.loads(json.dumps(item))

    canonical = sanitized.get("canonical", {})
    target_id = canonical.get("target_id", "")

    # Check and fix title
    title = sanitized.get("title", "")
    if is_garbage_text(title):
        new_title = generate_replacement_title(sanitized, target_type, target_id)
        sanitized["title"] = new_title
        stats.garbage_titles_fixed += 1
        logger.debug(f"Fixed garbage title: '{title[:50]}...' -> '{new_title}'")

    # Check and fix queries
    queries = sanitized.get("queries", [])
    fixed_queries = []

    for query_obj in queries:
        query_text = query_obj.get("query", "")
        expected_id = query_obj.get("expected_target_id", target_id)

        if is_garbage_text(query_text):
            new_query = generate_replacement_query(sanitized, target_type, expected_id)
            query_obj["query"] = new_query
            stats.garbage_queries_fixed += 1
            logger.debug(
                f"Fixed garbage query: '{query_text[:50]}...' -> '{new_query}'"
            )

        fixed_queries.append(query_obj)

    sanitized["queries"] = fixed_queries
    return sanitized


def remove_duplicates(
    items: list[dict[str, Any]], stats: SanitizationStats
) -> list[dict[str, Any]]:
    """Remove duplicate items based on expected_target_id."""
    seen_target_ids: set[str] = set()
    unique_items: list[dict[str, Any]] = []

    for item in items:
        # Get primary target_id
        canonical = item.get("canonical", {})
        target_id = canonical.get("target_id", "")

        # Also check queries for expected_target_id
        queries = item.get("queries", [])
        query_target_ids = {q.get("expected_target_id", "") for q in queries}

        # Use canonical target_id as the dedup key
        if target_id and target_id in seen_target_ids:
            stats.duplicates_removed += 1
            logger.debug(f"Removing duplicate item with target_id: {target_id}")
            continue

        if target_id:
            seen_target_ids.add(target_id)

        unique_items.append(item)

    return unique_items


def process_file(file_path: Path, dry_run: bool = False) -> SanitizationStats:
    """Process a single truth set file."""
    stats = SanitizationStats(file_name=file_path.name)
    target_type = extract_target_type(file_path.name)

    logger.info(f"Processing: {file_path.name} (target_type: {target_type})")

    if not file_path.exists():
        error_msg = f"File not found: {file_path}"
        logger.warning(error_msg)
        stats.errors.append(error_msg)
        return stats

    # Read all items
    items: list[dict[str, Any]] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    items.append(item)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parse error at line {line_num}: {e}"
                    logger.warning(error_msg)
                    stats.errors.append(error_msg)
    except IOError as e:
        error_msg = f"Failed to read file: {e}"
        logger.error(error_msg)
        stats.errors.append(error_msg)
        return stats

    stats.total_items = len(items)
    logger.info(f"  Loaded {stats.total_items} items")

    # Sanitize each item
    sanitized_items = [sanitize_item(item, target_type, stats) for item in items]

    # Remove duplicates
    unique_items = remove_duplicates(sanitized_items, stats)
    stats.items_after_sanitization = len(unique_items)

    # Write results
    if not dry_run:
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"  Created backup: {backup_path.name}")
        except IOError as e:
            error_msg = f"Failed to create backup: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
            return stats

        # Write sanitized file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for item in unique_items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            logger.info(f"  Wrote {len(unique_items)} sanitized items")
        except IOError as e:
            error_msg = f"Failed to write sanitized file: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
            # Attempt to restore backup
            try:
                shutil.copy2(backup_path, file_path)
                logger.info("  Restored from backup after write failure")
            except IOError:
                logger.error("  Failed to restore backup!")
    else:
        logger.info(f"  [DRY RUN] Would write {len(unique_items)} sanitized items")

    return stats


def print_summary(all_stats: list[SanitizationStats], dry_run: bool = False) -> None:
    """Print a summary of all sanitization operations."""
    print("\n" + "=" * 70)
    print("SANITIZATION SUMMARY" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 70)

    total_items = 0
    total_garbage_queries = 0
    total_garbage_titles = 0
    total_duplicates = 0
    total_errors = 0

    for stats in all_stats:
        print(f"\n{stats.file_name}:")
        print(f"  Total items processed:    {stats.total_items}")
        print(f"  Garbage queries fixed:    {stats.garbage_queries_fixed}")
        print(f"  Garbage titles fixed:     {stats.garbage_titles_fixed}")
        print(f"  Duplicates removed:       {stats.duplicates_removed}")
        print(f"  Items after sanitization: {stats.items_after_sanitization}")

        if stats.errors:
            print(f"  Errors: {len(stats.errors)}")
            for error in stats.errors:
                print(f"    - {error}")

        total_items += stats.total_items
        total_garbage_queries += stats.garbage_queries_fixed
        total_garbage_titles += stats.garbage_titles_fixed
        total_duplicates += stats.duplicates_removed
        total_errors += len(stats.errors)

    print("\n" + "-" * 70)
    print("TOTALS:")
    print(f"  Total items processed:  {total_items}")
    print(f"  Garbage queries fixed:  {total_garbage_queries}")
    print(f"  Garbage titles fixed:   {total_garbage_titles}")
    print(f"  Duplicates removed:     {total_duplicates}")
    print(f"  Errors encountered:     {total_errors}")
    print("=" * 70 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sanitize corrupted truth set files for F1 Cortex search pipeline."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        logger.info("Running in DRY RUN mode - no files will be modified")

    # Validate directory exists
    if not TRUTH_SETS_DIR.exists():
        logger.error(f"Truth sets directory not found: {TRUTH_SETS_DIR}")
        return 1

    logger.info(f"Truth sets directory: {TRUTH_SETS_DIR}")

    # Process each file
    all_stats: list[SanitizationStats] = []

    for file_name in TRUTH_SET_FILES:
        file_path = TRUTH_SETS_DIR / file_name
        stats = process_file(file_path, dry_run=args.dry_run)
        all_stats.append(stats)

    # Print summary
    print_summary(all_stats, dry_run=args.dry_run)

    # Return error code if any errors occurred
    total_errors = sum(len(s.errors) for s in all_stats)
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    exit(main())
