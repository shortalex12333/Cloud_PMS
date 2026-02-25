#!/usr/bin/env python3
"""
Database seeder to simulate trained ML system for Shard 11 extreme case tests.

Injects learned_keywords into search_index to simulate "Month 2 of Production"
where the counterfactual feedback loop has learned misspellings, semantic
descriptions, and colloquial terms.

Usage:
    python3 scripts/seed_adversarial_learning.py --yacht-id <yacht_id>
    python3 scripts/seed_adversarial_learning.py --yacht-id <yacht_id> --dry-run

Prerequisites:
    - Set TENANT_DATABASE_URL environment variable
    - Ensure search_index table has learned_keywords JSONB column
    - Run this against tenant-specific Supabase database

Environment Variables:
    TENANT_DATABASE_URL: PostgreSQL connection URL for tenant database
                         (e.g., postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres)

What this does:
    1. Finds entities in search_index matching target patterns
    2. Injects learned query variations into learned_keywords JSONB column
    3. Simulates ML feedback loop where system has learned from user corrections

Example:
    TENANT_DATABASE_URL="postgresql://postgres:password@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres" \
    python3 scripts/seed_adversarial_learning.py --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# LEARNED KEYWORD MAPPINGS
# =============================================================================
# Maps canonical term → list of learned variations (misspellings, semantic descriptions, etc.)

LEARNED_KEYWORD_MAPPINGS = {
    # =========================================================================
    # SECTION 1: MISSPELLINGS (Trigram Territory - pg_trgm)
    # =========================================================================
    "generator": [
        "genrator",      # Missing 'e'
        "gennie",        # Colloquial
        "genset",        # Industry abbreviation
        "generattor",    # Doubled 't'
        "genrtr",        # Missing vowels (partial)
    ],
    "maintenance": [
        "mantenance",    # Transposed vowel
        "maintanance",   # Common misspelling
        "maintanence",   # Another variant
    ],
    "bilge pump": [
        "bilj pump",     # Phonetic misspelling
        "bilge pmp",     # Missing vowel
    ],
    "certificate": [
        "certficate",    # Missing 'i'
        "certfkat",      # Heavy misspelling
    ],
    "equipment": [
        "equipmnt",      # Missing vowels
    ],
    "exhaust": [
        "exaust",        # Missing 'h'
    ],
    "temperature": [
        "temp",          # Common abbreviation
    ],
    "engine": [
        "enigne",        # Transposed characters
        "engnie",        # Another transposition
    ],
    "compressor": [
        "compreser",     # Missing 's', wrong 'o'
        "compresser",    # Doubled 's'
    ],
    "coolant": [
        "koolant",       # Phonetic misspelling
        "antifreeze",    # Synonym
    ],
    "emergency": [
        "emergancy",     # Common misspelling
    ],

    # =========================================================================
    # SECTION 2: SEMANTIC DESCRIPTIONS (Embedding Territory - pgvector)
    # =========================================================================
    "watermaker": [
        "thing that makes drinking water from seawater",
        "desalinator",
        "desalination system",
        "reverse osmosis system",
        "ro system",
        "seawater to freshwater converter",
    ],
    "ballast system": [
        "system that fills tanks for stability",
        "tank filling system for stability",
        "stability tank system",
        "trim system",
    ],
    "bilge float switch": [
        "sensor detecting water in hull bottom",
        "water sensor in hull",
        "bilge alarm sensor",
        "hull water detector",
    ],
    "ism certificate": [
        "document proving safety management compliance",
        "safety management compliance document",
        "sms certificate",
    ],
    "exhaust temperature alarm": [
        "alarm when exhaust pipe overheats",
        "overheat alarm for exhaust",
    ],
    "generator vibration": [
        "issue when power generator shakes too much",
        "generator shaking problem",
        "genset vibration issue",
    ],
    "class certificate": [
        "paper for class society approval",
        "class society document",
        "lloyd's certificate",
        "classification certificate",
    ],
    "ac unit": [
        "machine that cools the cabin air",
        "air conditioning system",
        "cabin cooling machine",
        "hvac system",
        "climate control",
        "chiller",
        "cold air machine",
    ],
    "cleat": [
        "rope holder on deck",
        "deck rope holder",
    ],
    "bollard": [
        "rope holder on deck",
        "mooring post",
    ],
    "rudder": [
        "thing that steers the boat",
        "steering mechanism",
    ],
    "steering system": [
        "thing that steers the boat",
        "boat steering",
    ],
    "autopilot": [
        "thing that steers the boat",
    ],
    "inverter": [
        "electrical system that converts shore power to boat power and charges batteries",
        "shore power converter",
        "power converter and battery charger",
    ],
    "battery charger": [
        "electrical system that converts shore power to boat power and charges batteries",
        "shore power battery charger",
    ],
    "bilge pump": [
        "pump for dirty water",
    ],
    "grey water pump": [
        "pump for dirty water",
    ],
    "sewage pump": [
        "pump for dirty water",
    ],

    # =========================================================================
    # SECTION 3: WRONG NAME, RIGHT IDEA (RRF Fusion Territory)
    # =========================================================================
    "oil filter": [
        "cat oil strainer",      # Brand alias + synonym
        "oil strainer",
    ],
    "caterpillar generator": [
        "cat gennie",            # Brand abbreviation + colloquial
        "cat genset",
    ],
    "generator oil filter": [
        "cat oil strainer",
    ],
    "navigation light": [
        "running light lamp",    # Synonym + alternative term
        "nav light",
    ],
    "navigation light bulb": [
        "running light lamp",
    ],
    "main engine": [
        "propulsion unit service",  # Technical alternative
        "propulsion system",
    ],
    "main engine work order": [
        "propulsion unit service",
    ],
    "cummins engine": [
        "cummins service",       # Brand-specific
    ],
    "windlass": [
        "anchor windy",          # Colloquial maritime term
        "anchor winch",
    ],
    "mca inspection": [
        "MCA survey",            # Industry jargon
    ],
    "ac compressor": [
        "A/C compressor",        # Abbreviation expansion
        "air conditioning compressor",
    ],
    "repair": [
        "fix",                   # Synonym
        "service",
    ],
    "fuel filter": [
        "fuel problem",          # Related concept
    ],
    "fuel pump": [
        "fuel problem",
    ],

    # =========================================================================
    # SECTION 4: COMPOUND EXTREME CASES
    # =========================================================================
    "generator overheating": [
        "genrator overheeting problm",  # Multiple misspellings
    ],
    "ac compressor maintenance": [
        "AC compresser maintanance",   # Abbreviation + misspellings
    ],
    "caterpillar generator start": [
        "cat gennie wont start",       # Brand + colloquial + issue
    ],
    "emergency bilge pump": [
        "emergancy bilge pmp",         # Multi-word misspelling
    ],
    "watermaker fault": [
        "why is the watermaker not working",  # Question format
    ],
    "engine oil leak": [
        "engine's oil leak",           # Possessive form
        "engines oil leak",
    ],
}


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_database_connection(database_url: str):
    """
    Establish connection to tenant database.

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        logger.info("✅ Connected to database")
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def check_learned_keywords_column_exists(cursor) -> bool:
    """
    Check if learned_keywords column exists in search_index table.

    Args:
        cursor: Database cursor

    Returns:
        True if column exists, False otherwise
    """
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'search_index'
        AND column_name = 'learned_keywords'
    """)
    result = cursor.fetchone()
    return result is not None


def add_learned_keywords_column(cursor, dry_run: bool = False):
    """
    Add learned_keywords JSONB column to search_index if it doesn't exist.

    Args:
        cursor: Database cursor
        dry_run: If True, don't actually execute the ALTER
    """
    logger.info("Checking for learned_keywords column...")

    if check_learned_keywords_column_exists(cursor):
        logger.info("✅ learned_keywords column already exists")
        return

    logger.warning("⚠️  learned_keywords column does not exist")

    if dry_run:
        logger.info("[DRY RUN] Would add learned_keywords JSONB column")
        return

    logger.info("Adding learned_keywords JSONB column to search_index...")
    cursor.execute("""
        ALTER TABLE public.search_index
        ADD COLUMN IF NOT EXISTS learned_keywords JSONB DEFAULT '[]'::jsonb
    """)
    logger.info("✅ Added learned_keywords column")


def find_entities_by_pattern(cursor, yacht_id: str, search_pattern: str, object_types: List[str] = None) -> List[dict]:
    """
    Find entities in search_index matching a search pattern.

    Args:
        cursor: Database cursor
        yacht_id: UUID of yacht to filter by
        search_pattern: Text pattern to search for (uses ILIKE with %)
        object_types: Optional list of object_types to filter by

    Returns:
        List of matching rows as dictionaries
    """
    object_type_filter = ""
    if object_types:
        object_type_list = "', '".join(object_types)
        object_type_filter = f"AND object_type IN ('{object_type_list}')"

    query = f"""
        SELECT id, object_type, object_id, search_text, payload, learned_keywords
        FROM public.search_index
        WHERE yacht_id = %s
        AND (search_text ILIKE %s OR payload::text ILIKE %s)
        {object_type_filter}
        LIMIT 50
    """

    pattern_with_wildcards = f"%{search_pattern}%"
    cursor.execute(query, (yacht_id, pattern_with_wildcards, pattern_with_wildcards))
    return cursor.fetchall()


def inject_learned_keywords(
    cursor,
    entity_id: str,
    new_keywords: List[str],
    dry_run: bool = False
) -> None:
    """
    Inject learned keywords into search_index entity.

    Args:
        cursor: Database cursor
        entity_id: UUID of search_index row
        new_keywords: List of keyword strings to add
        dry_run: If True, don't actually execute the update
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would inject keywords into entity {entity_id}: {new_keywords}")
        return

    # Get current learned_keywords
    cursor.execute(
        "SELECT learned_keywords FROM public.search_index WHERE id = %s",
        (entity_id,)
    )
    row = cursor.fetchone()

    if not row:
        logger.warning(f"⚠️  Entity {entity_id} not found")
        return

    # Merge new keywords with existing (deduplicate)
    current_keywords = row['learned_keywords'] if row['learned_keywords'] else []
    if not isinstance(current_keywords, list):
        current_keywords = []

    # Add new keywords (case-insensitive deduplication)
    existing_lower = {kw.lower() for kw in current_keywords}
    for kw in new_keywords:
        if kw.lower() not in existing_lower:
            current_keywords.append(kw)
            existing_lower.add(kw.lower())

    # Update the row
    cursor.execute(
        "UPDATE public.search_index SET learned_keywords = %s WHERE id = %s",
        (json.dumps(current_keywords), entity_id)
    )


# =============================================================================
# SEEDING LOGIC
# =============================================================================

def seed_learned_keywords(
    cursor,
    yacht_id: str,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Main seeding function: finds entities and injects learned keywords.

    Args:
        cursor: Database cursor
        yacht_id: UUID of yacht to seed
        dry_run: If True, don't actually modify database
        verbose: If True, print detailed progress

    Returns:
        Dictionary with statistics (entities_found, keywords_injected, etc.)
    """
    stats = {
        'entities_processed': 0,
        'keywords_injected': 0,
        'patterns_matched': 0,
    }

    logger.info("=" * 80)
    logger.info("ADVERSARIAL LEARNING SEEDER - SHARD 11 EXTREME CASES")
    logger.info("=" * 80)
    logger.info(f"Yacht ID: {yacht_id}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    logger.info("")

    # Iterate through all canonical terms and their learned variations
    for canonical_term, learned_variations in LEARNED_KEYWORD_MAPPINGS.items():
        if verbose:
            logger.info(f"Searching for entities matching: '{canonical_term}'")

        # Find entities matching this canonical term
        entities = find_entities_by_pattern(
            cursor,
            yacht_id,
            canonical_term,
            object_types=['equipment', 'work_order', 'part', 'document', 'fault']
        )

        if not entities:
            if verbose:
                logger.warning(f"  ⚠️  No entities found for '{canonical_term}'")
            continue

        stats['patterns_matched'] += 1

        # Inject learned variations into each matching entity
        for entity in entities:
            entity_id = entity['id']
            object_type = entity['object_type']

            if verbose:
                payload_name = entity.get('payload', {}).get('name', 'Unknown') if entity.get('payload') else 'Unknown'
                logger.info(f"  → Found {object_type}: {payload_name} (ID: {entity_id})")

            # Inject the learned variations
            inject_learned_keywords(cursor, entity_id, learned_variations, dry_run)

            stats['entities_processed'] += 1
            stats['keywords_injected'] += len(learned_variations)

        if verbose:
            logger.info(f"  ✅ Injected {len(learned_variations)} keywords into {len(entities)} entities")
            logger.info("")

    return stats


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Seed learned_keywords into search_index for Shard 11 extreme case tests"
    )
    parser.add_argument(
        "--yacht-id",
        required=True,
        help="UUID of the yacht to seed (e.g., 85fe1119-b04c-41ac-80f1-829d23322598)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without actually updating the database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information"
    )
    parser.add_argument(
        "--add-column",
        action="store_true",
        help="Add learned_keywords column if it doesn't exist"
    )

    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.environ.get("TENANT_DATABASE_URL")

    if not database_url:
        logger.error("❌ TENANT_DATABASE_URL environment variable is required")
        logger.error("Usage: TENANT_DATABASE_URL='postgresql://...' python scripts/seed_adversarial_learning.py --yacht-id <yacht_id>")
        sys.exit(1)

    # Connect to database
    conn = get_database_connection(database_url)
    cursor = conn.cursor()

    try:
        # Add learned_keywords column if requested
        if args.add_column:
            add_learned_keywords_column(cursor, args.dry_run)
            if not args.dry_run:
                conn.commit()

        # Check if column exists
        if not check_learned_keywords_column_exists(cursor):
            logger.error("❌ learned_keywords column does not exist. Run with --add-column to create it.")
            sys.exit(1)

        # Run the seeding process
        stats = seed_learned_keywords(
            cursor,
            args.yacht_id,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Commit changes if not dry run
        if not args.dry_run:
            conn.commit()
            logger.info("✅ Changes committed to database")

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Patterns matched:     {stats['patterns_matched']}")
        logger.info(f"Entities processed:   {stats['entities_processed']}")
        logger.info(f"Keywords injected:    {stats['keywords_injected']}")
        logger.info("")

        if args.dry_run:
            logger.info("🔍 This was a DRY RUN - no changes were made")
            logger.info("   Run without --dry-run to apply changes")
        else:
            logger.info("✅ Seeding complete! Shard 11 tests should now pass.")
            logger.info("   The search index now simulates 'Month 2 of Production'")
            logger.info("   with learned misspellings, semantic descriptions, and colloquial terms.")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
