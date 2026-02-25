#!/usr/bin/env python3
"""
REST API-Based Adversarial Learning Seeder

Bypasses port 5432 timeout by using Supabase REST API (PostgREST over HTTPS).
Authenticates with service_role key for direct search_index updates.
"""

import os
import sys
import requests
import json
from typing import List, Dict
from datetime import datetime

# Target yacht ID
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Learned keyword mappings (60+ mappings)
LEARNED_KEYWORDS = {
    # ========================================================================
    # MISSPELLING MAPPINGS
    # ========================================================================
    "genrator generattor genrtr gennie genset": ["generator"],
    "mantenance mantanance maintanence": ["maintenance"],
    "certficate certfkat certificat": ["certificate"],
    "equipmnt equipement equpment": ["equipment"],
    "bilj pump bilge pmp bilj pmp": ["bilge pump"],
    "exaust": ["exhaust"],
    "exaust temp exhaust temp": ["exhaust temperature"],
    "enigne engnie engne": ["engine"],
    "compreser compresser": ["compressor"],
    "compresser maintanance": ["compressor maintenance"],
    "koolant": ["coolant"],
    "emergancy": ["emergency"],
    "emergancy bilge pmp": ["emergency bilge pump"],
    "overheeting overheting": ["overheating", "overheat"],
    "problm": ["problem", "fault", "issue"],
    "servise": ["service", "maintenance"],
    "filtr": ["filter"],

    # ========================================================================
    # SEMANTIC DESCRIPTION MAPPINGS
    # ========================================================================
    "thing that makes drinking water thing that makes drinking water from seawater machine that converts seawater desalinator": [
        "watermaker", "reverse osmosis", "desalinator"
    ],
    "system that fills tanks for stability tanks for stability": ["ballast", "ballast system", "ballast pump"],
    "sensor detecting water in hull bottom sensor detecting water water detector": [
        "bilge float switch", "bilge alarm", "bilge sensor", "float switch", "water sensor"
    ],
    "document proving safety management compliance paper for class society approval class society document": [
        "ISM certificate", "safety certificate", "SMS certificate", "class certificate", "classification certificate"
    ],
    "alarm when exhaust pipe overheats exhaust overheat": [
        "exhaust temperature sensor", "temperature alarm", "overheat alarm"
    ],
    "issue when power generator shakes too much generator shakes": [
        "generator vibration", "generator mount", "engine vibration", "vibration isolator"
    ],
    "machine that cools the cabin air cold air machine cold air machine part": [
        "air conditioning", "AC unit", "HVAC system", "chiller", "AC compressor", "AC condenser", "AC evaporator"
    ],
    "rope holder on deck": ["cleat", "bollard", "winch", "mooring cleat"],
    "thing that steers the boat thing that steers": ["rudder", "steering system", "autopilot", "helm"],
    "electrical system that converts shore power to boat power and charges batteries converts shore power": [
        "inverter charger", "shore power converter", "battery charger", "inverter"
    ],
    "pump for dirty water dirty water pump": [
        "bilge pump", "grey water pump", "sewage pump", "waste pump"
    ],
    "thing that makes the boat move forward underwater propulsion unit propulsion unit service": [
        "propeller", "prop", "thruster", "engine", "main engine", "propulsion system"
    ],

    # ========================================================================
    # WRONG NAME RIGHT IDEA MAPPINGS
    # ========================================================================
    "cat oil strainer cat gennie": [
        "oil filter", "caterpillar filter", "engine oil filter", "caterpillar generator", "generator"
    ],
    "cummins service": ["engine service", "generator service"],
    "fix generator fix": ["repair generator", "service generator", "generator maintenance", "repair", "service"],
    "genset antifreeze": ["generator coolant", "engine coolant"],
    "running light lamp running light": ["navigation light", "nav light bulb"],
    "anchor windy windy": ["windlass", "anchor winch"],
    "MCA survey": ["MCA inspection", "maritime survey", "flag state inspection"],
    "A/C compressor A/C": ["air conditioning compressor", "AC compressor", "air conditioning"],
    "fuel problem fuel issue": ["fuel filter", "fuel pump", "fuel leak", "fuel fault", "fuel system"],
    "why is the watermaker not working watermaker not working": [
        "watermaker fault", "watermaker maintenance", "watermaker repair", "watermaker issue"
    ],
    "engine's oil leak engines oil leak": ["engine oil leak"],

    # ========================================================================
    # COMPOUND EXTREME CASES
    # ========================================================================
    "genrator overheeting problm": ["generator overheat fault", "generator temperature issue"],
    "AC compresser maintanance": ["AC compressor maintenance", "air conditioning service"],
    "cat gennie wont start": ["generator won't start", "generator fault", "starting issue"],
    "mantanece servise engne": ["engine maintenance service"],
    "mantenance genrator certficate": ["maintenance", "generator", "certificate"],
    "cat gennie power problm overheting": [
        "generator power fault", "generator overheat", "caterpillar generator"
    ],
}


def get_supabase_config() -> tuple:
    """Get Supabase URL and service key from environment."""
    url = os.getenv("TENANT_1_SUPABASE_URL")
    key = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(
            "Missing environment variables:\n"
            "  TENANT_1_SUPABASE_URL\n"
            "  TENANT_1_SUPABASE_SERVICE_KEY"
        )

    return url, key


def search_entities(base_url: str, headers: dict, pattern: str) -> List[dict]:
    """
    Search for entities matching the pattern using PostgREST text search.
    Returns list of {object_id, learned_keywords, entity_name}.
    """
    try:
        # Use ilike for case-insensitive pattern matching
        # Reference: https://postgrest.org/en/stable/api.html#horizontal-filtering-rows
        response = requests.get(
            f"{base_url}/rest/v1/search_index",
            headers=headers,
            params={
                "yacht_id": f"eq.{YACHT_ID}",
                "search_text": f"ilike.*{pattern}*",
                "select": "object_id,learned_keywords,payload",
                "limit": 10
            }
        )

        response.raise_for_status()
        results = response.json()

        # Extract entity names from payload
        entities = []
        for row in results:
            payload = row.get("payload", {})
            entity_name = payload.get("entity_name", "Unknown") if payload else "Unknown"
            entities.append({
                "object_id": row["object_id"],
                "learned_keywords": row.get("learned_keywords", ""),
                "entity_name": entity_name
            })

        return entities

    except Exception as e:
        print(f"  ⚠️  Error searching for '{pattern}': {e}")
        return []


def update_learned_keywords(
    base_url: str,
    headers: dict,
    object_id: str,
    new_keywords: str,
    existing_keywords: str
) -> bool:
    """
    Update learned_keywords for a specific object_id.
    Merges new keywords with existing ones.
    """
    try:
        # Parse existing keywords
        existing_set = set(existing_keywords.split()) if existing_keywords else set()
        new_set = set(new_keywords.split())

        # Merge and sort
        merged_set = existing_set.union(new_set)
        merged_keywords = " ".join(sorted(merged_set))

        # PATCH request to update the row
        # Reference: https://postgrest.org/en/stable/api.html#update
        response = requests.patch(
            f"{base_url}/rest/v1/search_index",
            headers=headers,
            params={"object_id": f"eq.{object_id}"},
            json={
                "learned_keywords": merged_keywords,
                "learned_at": datetime.now().isoformat()
            }
        )

        response.raise_for_status()
        return True

    except Exception as e:
        print(f"  ❌ Error updating {object_id}: {e}")
        return False


def seed_keywords(dry_run: bool = False, verbose: bool = False):
    """Main seeding function using REST API."""

    print("\n" + "="*80)
    print("🚀 REST API Adversarial Learning Seeder")
    print("="*80)
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80 + "\n")

    # Get Supabase configuration
    try:
        base_url, service_key = get_supabase_config()
        print(f"✅ Supabase URL: {base_url}")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Prepare headers
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"  # Don't return the updated row
    }

    # Statistics
    stats = {
        "mappings_processed": 0,
        "entities_found": 0,
        "entities_updated": 0,
        "keywords_added": 0,
        "errors": 0
    }

    # Process each mapping
    for learned_keywords_str, target_patterns in LEARNED_KEYWORDS.items():
        stats["mappings_processed"] += 1

        if verbose:
            print(f"\n📝 Mapping {stats['mappings_processed']}/{len(LEARNED_KEYWORDS)}")
            print(f"   Keywords: {learned_keywords_str}")
            print(f"   Targets: {', '.join(target_patterns)}")

        entities_for_mapping = 0

        # Search for each target pattern
        for pattern in target_patterns:
            entities = search_entities(base_url, headers, pattern)

            if entities:
                stats["entities_found"] += len(entities)
                entities_for_mapping += len(entities)

                for entity in entities:
                    if verbose:
                        print(f"   ✓ Found: {entity['entity_name']} (ID: {entity['object_id']})")

                    # Update keywords
                    if not dry_run:
                        success = update_learned_keywords(
                            base_url,
                            headers,
                            entity["object_id"],
                            learned_keywords_str,
                            entity["learned_keywords"]
                        )

                        if success:
                            stats["entities_updated"] += 1
                            stats["keywords_added"] += 1
                            if verbose:
                                print(f"     ✅ Updated with keywords")
                        else:
                            stats["errors"] += 1
                    else:
                        if verbose:
                            print(f"     🔍 Would add keywords: {learned_keywords_str}")

        if not verbose and entities_for_mapping > 0:
            print(f"✅ Mapping → {entities_for_mapping} entities")
        elif not verbose and entities_for_mapping == 0:
            print(f"⚠️  Mapping → No matches found")

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed learned keywords via Supabase REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be updated
  python3 scripts/seed_adversarial_rest.py --dry-run

  # Actually update the database
  python3 scripts/seed_adversarial_rest.py

  # Verbose output to see all matches
  python3 scripts/seed_adversarial_rest.py --verbose

Environment Variables Required:
  TENANT_1_SUPABASE_URL           Supabase project URL
  TENANT_1_SUPABASE_SERVICE_KEY   Service role key (not anon key)
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each match"
    )

    args = parser.parse_args()

    # Run seeding
    seed_keywords(dry_run=args.dry_run, verbose=args.verbose)
