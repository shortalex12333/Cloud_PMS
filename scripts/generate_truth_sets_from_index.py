#!/usr/bin/env python3
"""
Generate Truth Sets from Actual Indexed Data

Queries search_index directly to create truth sets targeting REAL indexed records.
This ensures Recall@3 measures actual algorithm performance, not data quality issues.

Usage:
    DATABASE_URL="postgresql://..." python scripts/generate_truth_sets_from_index.py
    DATABASE_URL="postgresql://..." python scripts/generate_truth_sets_from_index.py --dry-run
"""

import argparse
import json
import logging
import os
import re
import sys
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
OUTPUT_DIR = "/Volumes/Backup/CELESTE"
ITEMS_PER_TYPE = 3  # Match pilot test expectations

# Entity types to generate truth sets for
ENTITY_TYPES = [
    "certificate",
    "document",
    "fault",
    "inventory",
    "part",
    "receiving",
    "shopping_item",
    "work_order_note",
    "work_order",
]

# Garbage patterns to exclude
GARBAGE_PATTERNS = [
    r"x{5,}",  # xxxxx...
    r"A{20,}",  # AAAA...
    r"Test fault report",  # Generic test data
    r"Hours logged: 2\.5h",  # Duplicate work order notes
]


def is_garbage(text: str) -> bool:
    """Check if text contains garbage patterns."""
    if not text or len(text.strip()) < 10:
        return True
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Extract meaningful keywords from search_text."""
    # Remove common noise words
    noise_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "under", "again", "further", "then", "once",
        "updated", "description", "via", "e2e", "test", "at", "and", "or",
    }

    # Tokenize and filter
    words = re.findall(r"\b[a-zA-Z0-9][\w\-]*[a-zA-Z0-9]\b|\b[a-zA-Z0-9]\b", text)
    keywords = []
    seen = set()

    for word in words:
        lower = word.lower()
        if lower not in noise_words and lower not in seen and len(word) > 2:
            keywords.append(word)
            seen.add(lower)
            if len(keywords) >= max_keywords:
                break

    return keywords


def generate_queries(search_text: str, object_type: str, object_id: str) -> list[dict]:
    """Generate 12 diverse queries for a single record."""
    queries = []
    keywords = extract_keywords(search_text, max_keywords=8)

    if len(keywords) < 2:
        return []

    # Query templates with intent types
    templates = [
        # Exact match queries
        ("exact", " ".join(keywords[:3])),
        ("exact", " ".join(keywords[:2])),

        # Partial match queries
        ("partial", keywords[0] if keywords else ""),
        ("partial", " ".join(keywords[1:3]) if len(keywords) > 2 else keywords[-1] if keywords else ""),

        # Natural language queries
        ("natural", f"find {keywords[0]}" if keywords else ""),
        ("natural", f"show me {' '.join(keywords[:2])}" if len(keywords) >= 2 else ""),
        ("natural", f"where is {keywords[0]}" if keywords else ""),

        # Type-specific queries
        ("typed", f"{object_type} {keywords[0]}" if keywords else ""),
        ("typed", f"{object_type.replace('_', ' ')} {' '.join(keywords[:2])}" if len(keywords) >= 2 else ""),

        # Keyword combination queries
        ("combo", " ".join(keywords[::2])),  # Every other keyword
        ("combo", " ".join(keywords[1::2]) if len(keywords) > 1 else ""),

        # Full text query
        ("full", " ".join(keywords[:5])),
    ]

    for intent_type, query in templates:
        if query and len(query.strip()) > 2:
            queries.append({
                "query": query.strip(),
                "intent_type": intent_type,
                "implied_filters": [],
                "expected_target_id": object_id,
            })

    return queries[:12]  # Exactly 12 queries per item


def fetch_clean_records(cursor, object_type: str, limit: int) -> list[dict]:
    """Fetch clean (non-garbage) records for an entity type."""
    query = """
        SELECT DISTINCT ON (LEFT(search_text, 50))
            object_id::text,
            object_type,
            search_text,
            payload
        FROM search_index
        WHERE yacht_id = %s
          AND object_type = %s
          AND embedding_1536 IS NOT NULL
          AND LENGTH(search_text) > 20
        ORDER BY LEFT(search_text, 50), updated_at DESC
        LIMIT %s
    """

    # Fetch more than needed to filter garbage
    cursor.execute(query, (YACHT_ID, object_type, limit * 5))
    rows = cursor.fetchall()

    clean_records = []
    for row in rows:
        if not is_garbage(row["search_text"]):
            clean_records.append(row)
            if len(clean_records) >= limit:
                break

    return clean_records


def generate_truth_set_item(record: dict) -> Optional[dict]:
    """Generate a truth set item from a search_index record."""
    object_id = record["object_id"]
    object_type = record["object_type"]
    search_text = record["search_text"]
    payload = record["payload"] or {}

    # Parse payload if string
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}

    # Generate queries
    queries = generate_queries(search_text, object_type, object_id)

    if len(queries) < 6:  # Need at least 6 queries
        return None

    # Build title from search_text
    title_words = extract_keywords(search_text, max_keywords=6)
    title = " ".join(title_words) if title_words else f"{object_type} {object_id[:8]}"

    return {
        "title": title,
        "canonical": {
            "target_type": object_type,
            "target_id": object_id,
            "primary_table": "search_index",
            **{k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool)) and k in [
                "name", "title", "description", "status", "fault_code", "supplier_name"
            ]},
        },
        "queries": queries,
    }


def generate_truth_sets(database_url: str, dry_run: bool = False) -> None:
    """Generate truth sets for all entity types."""
    logger.info("=" * 60)
    logger.info("Truth Set Generator - From Indexed Data")
    logger.info("=" * 60)
    logger.info(f"Yacht ID: {YACHT_ID}")
    logger.info(f"Items per type: {ITEMS_PER_TYPE}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    logger.info("-" * 60)

    try:
        conn = psycopg2.connect(database_url)
        logger.info("Connected to database")
    except psycopg2.Error as e:
        logger.error(f"Failed to connect: {e}")
        sys.exit(1)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for entity_type in ENTITY_TYPES:
                logger.info(f"\nProcessing: {entity_type}")

                # Fetch clean records
                records = fetch_clean_records(cursor, entity_type, ITEMS_PER_TYPE)
                logger.info(f"  Found {len(records)} clean records")

                if not records:
                    logger.warning(f"  No clean records found for {entity_type}")
                    continue

                # Generate truth set items
                items = []
                for record in records:
                    item = generate_truth_set_item(record)
                    if item:
                        items.append(item)

                logger.info(f"  Generated {len(items)} truth set items")

                if not items:
                    continue

                # Map entity_type to truth set filename
                # Handle mapping: part -> parts, shopping_item -> shopping_list
                filename_map = {
                    "part": "parts",
                    "shopping_item": "shopping_list",
                }
                filename_type = filename_map.get(entity_type, entity_type)
                output_path = os.path.join(OUTPUT_DIR, f"truthset_{filename_type}.jsonl")

                if dry_run:
                    logger.info(f"  [DRY-RUN] Would write {len(items)} items to {output_path}")
                    for item in items:
                        logger.info(f"    - {item['title'][:50]}... ({len(item['queries'])} queries)")
                else:
                    # Write truth set
                    with open(output_path, "w", encoding="utf-8") as f:
                        for item in items:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    logger.info(f"  Wrote {len(items)} items to {output_path}")

        logger.info("\n" + "-" * 60)
        logger.info("Truth set generation complete!")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    parser = argparse.ArgumentParser(
        description="Generate truth sets from indexed data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    generate_truth_sets(database_url, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
