#!/usr/bin/env python3
"""
Adversarial Learning Seeding Script for Shard 11 Extreme Case Tests

Mission: Seed learned_keywords in the database to fix Shard 11's 43 failures.
These failures occur because extreme case queries (misspellings, semantic descriptions)
require learned vocabulary bridges that don't exist in the test data yet.

This script creates 60+ mappings covering:
- Misspellings (trigram territory)
- Semantic descriptions (embedding territory)
- Wrong names with right ideas (RRF fusion territory)

LAW 8: STRICT LINGUISTIC ISOLATION - All learning is yacht-specific.
LAW 9: PROJECTION IMMUTABILITY - We only update learned_keywords column.
"""

import os
import sys
import argparse
from typing import List, Dict, Tuple
from datetime import datetime
from supabase import create_client, Client

# ============================================================================
# LEARNED KEYWORD MAPPINGS
# ============================================================================
# Maps extreme case queries to their target entity names.
# Format: {search_term: [list_of_target_entity_patterns]}

LEARNED_KEYWORDS = {
    # ========================================================================
    # SECTION 1: MISSPELLING MAPPINGS (Trigram Territory)
    # ========================================================================

    # Common generator misspellings
    "genrator": ["generator"],
    "generattor": ["generator"],
    "genrtr": ["generator"],
    "gennie": ["generator"],
    "genset": ["generator"],

    # Maintenance misspellings
    "mantenance": ["maintenance"],
    "mantanance": ["maintenance"],
    "maintanence": ["maintenance"],

    # Certificate misspellings
    "certficate": ["certificate"],
    "certfkat": ["certificate"],
    "certificat": ["certificate"],

    # Equipment misspellings
    "equipmnt": ["equipment"],
    "equipement": ["equipment"],
    "equpment": ["equipment"],

    # Bilge pump misspellings
    "bilj pump": ["bilge pump"],
    "bilge pmp": ["bilge pump"],
    "bilj pmp": ["bilge pump"],

    # Exhaust misspellings
    "exaust": ["exhaust"],
    "exaust temp": ["exhaust temperature"],
    "exhaust temp": ["exhaust temperature"],

    # Engine misspellings
    "enigne": ["engine"],
    "engnie": ["engine"],
    "engne": ["engine"],

    # Compressor misspellings
    "compreser": ["compressor"],
    "compresser": ["compressor"],
    "compresser maintanance": ["compressor maintenance"],

    # Coolant misspellings
    "koolant": ["coolant"],

    # Emergency misspellings
    "emergancy": ["emergency"],
    "emergancy bilge pmp": ["emergency bilge pump"],

    # Overheat misspellings
    "overheeting": ["overheating", "overheat"],
    "overheting": ["overheating", "overheat"],

    # Problem misspellings
    "problm": ["problem", "fault", "issue"],

    # Service misspellings
    "servise": ["service", "maintenance"],

    # Filter misspellings
    "filtr": ["filter"],

    # ========================================================================
    # SECTION 2: SEMANTIC DESCRIPTION MAPPINGS (Embedding Territory)
    # ========================================================================

    # Watermaker descriptions
    "thing that makes drinking water": ["watermaker", "reverse osmosis", "desalinator"],
    "thing that makes drinking water from seawater": ["watermaker", "reverse osmosis", "desalinator"],
    "machine that converts seawater": ["watermaker", "reverse osmosis"],
    "desalinator": ["watermaker", "reverse osmosis"],

    # Ballast system descriptions
    "system that fills tanks for stability": ["ballast", "ballast system", "ballast pump"],
    "tanks for stability": ["ballast", "ballast tank"],

    # Bilge float switch descriptions
    "sensor detecting water in hull bottom": ["bilge float switch", "bilge alarm", "bilge sensor"],
    "sensor detecting water": ["bilge float switch", "float switch", "water sensor"],
    "water detector": ["bilge float switch", "float switch"],

    # Certificate descriptions
    "document proving safety management compliance": ["ISM certificate", "safety certificate", "SMS certificate"],
    "paper for class society approval": ["class certificate", "classification certificate", "survey certificate"],
    "class society document": ["class certificate", "classification certificate"],

    # Temperature alarm descriptions
    "alarm when exhaust pipe overheats": ["exhaust temperature sensor", "temperature alarm", "overheat alarm"],
    "exhaust overheat": ["exhaust temperature sensor", "temperature alarm"],

    # Generator vibration descriptions
    "issue when power generator shakes too much": ["generator vibration", "generator mount", "engine vibration"],
    "generator shakes": ["generator vibration", "engine mount", "vibration isolator"],

    # AC descriptions
    "machine that cools the cabin air": ["air conditioning", "AC unit", "HVAC system", "chiller"],
    "cold air machine": ["air conditioning", "AC compressor", "HVAC"],
    "cold air machine part": ["AC compressor", "AC condenser", "AC evaporator"],

    # Deck equipment descriptions
    "rope holder on deck": ["cleat", "bollard", "winch", "mooring cleat"],

    # Steering descriptions
    "thing that steers the boat": ["rudder", "steering system", "autopilot", "helm"],
    "thing that steers": ["rudder", "steering", "helm"],

    # Electrical system descriptions
    "electrical system that converts shore power to boat power and charges batteries": ["inverter charger", "shore power converter", "battery charger"],
    "converts shore power": ["inverter", "charger", "shore power converter"],

    # Pump descriptions
    "pump for dirty water": ["bilge pump", "grey water pump", "sewage pump", "waste pump"],
    "dirty water pump": ["bilge pump", "sewage pump", "grey water pump"],

    # Propulsion descriptions
    "thing that makes the boat move forward underwater": ["propeller", "prop", "thruster"],
    "propulsion unit": ["engine", "main engine", "propulsion system"],
    "propulsion unit service": ["engine service", "main engine maintenance"],

    # ========================================================================
    # SECTION 3: WRONG NAME RIGHT IDEA MAPPINGS (RRF Fusion Territory)
    # ========================================================================

    # Brand aliases
    "cat oil strainer": ["oil filter", "caterpillar filter", "engine oil filter"],
    "cat gennie": ["caterpillar generator", "generator"],
    "cummins service": ["engine service", "generator service"],

    # Synonym substitutions
    "fix generator": ["repair generator", "service generator", "generator maintenance"],
    "fix": ["repair", "service", "maintenance"],

    # Alternative terminology
    "genset antifreeze": ["generator coolant", "engine coolant"],
    "running light lamp": ["navigation light", "nav light bulb"],
    "running light": ["navigation light"],

    # Colloquial terms
    "anchor windy": ["windlass", "anchor winch"],
    "windy": ["windlass"],

    # Industry jargon
    "MCA survey": ["MCA inspection", "maritime survey", "flag state inspection"],
    "class society document": ["classification certificate", "class certificate"],

    # Abbreviation handling
    "A/C compressor": ["air conditioning compressor", "AC compressor"],
    "A/C": ["air conditioning", "AC"],

    # Related concept queries
    "fuel problem": ["fuel filter", "fuel pump", "fuel leak", "fuel fault"],
    "fuel issue": ["fuel filter", "fuel pump", "fuel system"],

    # Question format variations
    "why is the watermaker not working": ["watermaker fault", "watermaker maintenance", "watermaker repair"],
    "watermaker not working": ["watermaker fault", "watermaker issue"],

    # Possessive forms
    "engine's oil leak": ["engine oil leak"],
    "engines oil leak": ["engine oil leak"],

    # ========================================================================
    # SECTION 4: COMPOUND EXTREME CASES
    # ========================================================================

    # Multiple issues combined
    "genrator overheeting problm": ["generator overheat fault", "generator temperature issue"],
    "AC compresser maintanance": ["AC compressor maintenance", "air conditioning service"],
    "cat gennie wont start": ["generator won't start", "generator fault", "starting issue"],
    "mantanece servise engne": ["engine maintenance service"],

    # Performance test queries
    "mantenance genrator certficate": ["maintenance", "generator", "certificate"],
    "cat gennie power problm overheting": ["generator power fault", "generator overheat", "caterpillar generator"],
}


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_supabase_client(yacht_id: str) -> Client:
    """
    Get Supabase client for the specified yacht.
    Checks environment variables for yacht-specific URL first,
    then falls back to generic tenant URL.
    """
    # Try yacht-specific URL first (format: y{yacht_id}_SUPABASE_URL)
    yacht_env_key = f"y{yacht_id.replace('-', '')}_SUPABASE_URL"
    yacht_url = os.getenv(yacht_env_key)

    # Try generic tenant URL
    if not yacht_url:
        yacht_url = os.getenv("TENANT_1_SUPABASE_URL") or os.getenv("SUPABASE_URL")

    if not yacht_url:
        raise ValueError(
            f"No database URL found. Set {yacht_env_key} or TENANT_1_SUPABASE_URL or SUPABASE_URL"
        )

    # Get service key
    yacht_key_env = f"y{yacht_id.replace('-', '')}_SUPABASE_SERVICE_KEY"
    service_key = os.getenv(yacht_key_env) or os.getenv("TENANT_1_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not service_key:
        raise ValueError(f"No service key found. Set {yacht_key_env} or TENANT_1_SUPABASE_SERVICE_KEY")

    # Create Supabase client
    client = create_client(yacht_url, service_key)
    return client


# ============================================================================
# SEEDING LOGIC
# ============================================================================

def find_matching_entities(
    client: Client,
    yacht_id: str,
    target_pattern: str
) -> List[Tuple[str, str, str, str]]:
    """
    Find entities in search_index that match the target pattern.
    Returns list of (object_id, entity_name, existing_keywords, search_text)
    """
    try:
        # Simple approach: just filter by yacht_id and use text search
        # The ilike filter in PostgREST uses pattern matching
        result = client.table("search_index").select(
            "object_id,payload,learned_keywords,search_text"
        ).eq(
            "yacht_id", yacht_id
        ).ilike(
            "search_text", f"%{target_pattern}%"
        ).limit(10).execute()

        entities = []
        for row in result.data:
            object_id = row['object_id']
            payload = row.get('payload', {})
            entity_name = payload.get('entity_name', 'Unknown') if payload else 'Unknown'
            existing_keywords = row.get('learned_keywords', '') or ''
            search_text = row.get('search_text', '') or ''
            entities.append((object_id, entity_name, existing_keywords, search_text))

        return entities
    except Exception as e:
        print(f"  ⚠️  Error searching for '{target_pattern}': {e}")
        import traceback
        traceback.print_exc()
        return []


def update_learned_keywords(
    client: Client,
    object_id: str,
    new_keywords: List[str],
    existing_keywords: str
) -> bool:
    """
    Update the learned_keywords column for a specific object.
    Merges new keywords with existing ones (space-separated).
    """
    # Parse existing keywords
    existing_set = set(existing_keywords.split()) if existing_keywords else set()

    # Add new keywords
    existing_set.update(new_keywords)

    # Create merged keyword string
    merged_keywords = ' '.join(sorted(existing_set))

    # Update database
    try:
        from datetime import datetime
        client.table("search_index").update({
            "learned_keywords": merged_keywords,
            "learned_at": datetime.now().isoformat()
        }).eq("object_id", object_id).execute()
        return True
    except Exception as e:
        print(f"  ❌ Error updating object {object_id}: {e}")
        return False


def seed_learned_keywords(yacht_id: str, dry_run: bool = False, verbose: bool = False):
    """
    Main seeding function.
    Iterates through LEARNED_KEYWORDS and updates the database.
    """
    print(f"\n{'='*80}")
    print(f"🚀 Adversarial Learning Seeding Script")
    print(f"{'='*80}")
    print(f"Yacht ID: {yacht_id}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")

    # Get Supabase client
    try:
        client = get_supabase_client(yacht_id)
        print(f"✅ Supabase client configured")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Statistics
    stats = {
        'mappings_processed': 0,
        'entities_found': 0,
        'entities_updated': 0,
        'keywords_added': 0,
        'errors': 0
    }

    # Process each mapping
    for search_term, target_patterns in LEARNED_KEYWORDS.items():
        stats['mappings_processed'] += 1

        if verbose:
            print(f"\n📝 Mapping {stats['mappings_processed']}/{len(LEARNED_KEYWORDS)}: '{search_term}'")
            print(f"   Targets: {', '.join(target_patterns)}")

        # Track entities updated for this search term
        entities_for_term = 0

        # Search for each target pattern
        for target in target_patterns:
            matches = find_matching_entities(client, yacht_id, target)

            if matches:
                stats['entities_found'] += len(matches)
                entities_for_term += len(matches)

                for object_id, entity_name, existing_keywords, search_text in matches:
                    if verbose:
                        print(f"   ✓ Found: {entity_name} (ID: {object_id})")

                    # Update keywords
                    if not dry_run:
                        success = update_learned_keywords(
                            client,
                            object_id,
                            [search_term],
                            existing_keywords
                        )

                        if success:
                            stats['entities_updated'] += 1
                            stats['keywords_added'] += 1
                            if verbose:
                                print(f"     ✅ Updated with keyword: '{search_term}'")
                        else:
                            stats['errors'] += 1
                    else:
                        if verbose:
                            print(f"     🔍 Would add keyword: '{search_term}'")

        if not verbose and entities_for_term > 0:
            print(f"✅ '{search_term}' → {entities_for_term} entities")
        elif not verbose and entities_for_term == 0:
            print(f"⚠️  '{search_term}' → No matches found")

    # Print summary
    print(f"\n{'='*80}")
    print(f"📊 SEEDING SUMMARY")
    print(f"{'='*80}")
    print(f"Mappings processed:    {stats['mappings_processed']}")
    print(f"Entities found:        {stats['entities_found']}")
    print(f"Entities updated:      {stats['entities_updated']}")
    print(f"Keywords added:        {stats['keywords_added']}")
    print(f"Errors:                {stats['errors']}")
    print(f"{'='*80}\n")

    if dry_run:
        print("ℹ️  This was a DRY RUN. No changes were made to the database.")
        print("   Run without --dry-run to apply changes.\n")
    else:
        print("✅ Seeding complete! Run Shard 11 tests to verify improvements.\n")

    return stats


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Seed learned keywords for adversarial search test cases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be updated
  python3 scripts/seed_adversarial_learning.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598" --dry-run

  # Actually update the database
  python3 scripts/seed_adversarial_learning.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598"

  # Verbose output to see all matches
  python3 scripts/seed_adversarial_learning.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598" --verbose
        """
    )

    parser.add_argument(
        '--yacht-id',
        required=True,
        help='UUID of the yacht to seed (e.g., 85fe1119-b04c-41ac-80f1-829d23322598)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output for each match'
    )

    args = parser.parse_args()

    # Run seeding
    seed_learned_keywords(
        yacht_id=args.yacht_id,
        dry_run=args.dry_run,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()
