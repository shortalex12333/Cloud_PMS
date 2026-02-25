#!/usr/bin/env python3
"""
SQL Generator for Adversarial Learning Keywords

Generates SQL statements to seed learned_keywords for Shard 11 extreme case tests.
Output can be run directly in Supabase SQL editor or psql.

Usage:
    python3 scripts/generate_learned_keywords_sql.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598" > /tmp/seed.sql
    # Then run the SQL in Supabase dashboard or via psql
"""

import argparse
from typing import List, Dict

# Import the learned keywords mapping from the original script
LEARNED_KEYWORDS = {
    # MISSPELLINGS
    "genrator": ["generator"],
    "generattor": ["generator"],
    "genrtr": ["generator"],
    "gennie": ["generator"],
    "genset": ["generator"],
    "mantenance": ["maintenance"],
    "mantanance": ["maintenance"],
    "maintanence": ["maintenance"],
    "certficate": ["certificate"],
    "certfkat": ["certificate"],
    "certificat": ["certificate"],
    "equipmnt": ["equipment"],
    "equipement": ["equipment"],
    "equpment": ["equipment"],
    "bilj pump": ["bilge pump"],
    "bilge pmp": ["bilge pump"],
    "bilj pmp": ["bilge pump"],
    "exaust": ["exhaust"],
    "exaust temp": ["exhaust temperature"],
    "exhaust temp": ["exhaust temperature"],
    "enigne": ["engine"],
    "engnie": ["engine"],
    "engne": ["engine"],
    "compreser": ["compressor"],
    "compresser": ["compressor"],
    "compresser maintanance": ["compressor maintenance"],
    "koolant": ["coolant"],
    "emergancy": ["emergency"],
    "emergancy bilge pmp": ["emergency bilge pump"],
    "overheeting": ["overheating", "overheat"],
    "overheting": ["overheating", "overheat"],
    "problm": ["problem", "fault", "issue"],
    "servise": ["service", "maintenance"],
    "filtr": ["filter"],

    # SEMANTIC DESCRIPTIONS
    "thing that makes drinking water": ["watermaker", "reverse osmosis", "desalinator"],
    "thing that makes drinking water from seawater": ["watermaker", "reverse osmosis", "desalinator"],
    "machine that converts seawater": ["watermaker", "reverse osmosis"],
    "desalinator": ["watermaker", "reverse osmosis"],
    "system that fills tanks for stability": ["ballast", "ballast system", "ballast pump"],
    "tanks for stability": ["ballast", "ballast tank"],
    "sensor detecting water in hull bottom": ["bilge float switch", "bilge alarm", "bilge sensor"],
    "sensor detecting water": ["bilge float switch", "float switch", "water sensor"],
    "water detector": ["bilge float switch", "float switch"],
    "document proving safety management compliance": ["ISM certificate", "safety certificate", "SMS certificate"],
    "paper for class society approval": ["class certificate", "classification certificate", "survey certificate"],
    "class society document": ["class certificate", "classification certificate"],
    "alarm when exhaust pipe overheats": ["exhaust temperature sensor", "temperature alarm", "overheat alarm"],
    "exhaust overheat": ["exhaust temperature sensor", "temperature alarm"],
    "issue when power generator shakes too much": ["generator vibration", "generator mount", "engine vibration"],
    "generator shakes": ["generator vibration", "engine mount", "vibration isolator"],
    "machine that cools the cabin air": ["air conditioning", "AC unit", "HVAC system", "chiller"],
    "cold air machine": ["air conditioning", "AC compressor", "HVAC"],
    "cold air machine part": ["AC compressor", "AC condenser", "AC evaporator"],
    "rope holder on deck": ["cleat", "bollard", "winch", "mooring cleat"],
    "thing that steers the boat": ["rudder", "steering system", "autopilot", "helm"],
    "thing that steers": ["rudder", "steering", "helm"],
    "electrical system that converts shore power to boat power and charges batteries": ["inverter charger", "shore power converter", "battery charger"],
    "converts shore power": ["inverter", "charger", "shore power converter"],
    "pump for dirty water": ["bilge pump", "grey water pump", "sewage pump", "waste pump"],
    "dirty water pump": ["bilge pump", "sewage pump", "grey water pump"],
    "thing that makes the boat move forward underwater": ["propeller", "prop", "thruster"],
    "propulsion unit": ["engine", "main engine", "propulsion system"],
    "propulsion unit service": ["engine service", "main engine maintenance"],

    # WRONG NAME RIGHT IDEA
    "cat oil strainer": ["oil filter", "caterpillar filter", "engine oil filter"],
    "cat gennie": ["caterpillar generator", "generator"],
    "cummins service": ["engine service", "generator service"],
    "fix generator": ["repair generator", "service generator", "generator maintenance"],
    "fix": ["repair", "service", "maintenance"],
    "genset antifreeze": ["generator coolant", "engine coolant"],
    "running light lamp": ["navigation light", "nav light bulb"],
    "running light": ["navigation light"],
    "anchor windy": ["windlass", "anchor winch"],
    "windy": ["windlass"],
    "MCA survey": ["MCA inspection", "maritime survey", "flag state inspection"],
    "A/C compressor": ["air conditioning compressor", "AC compressor"],
    "A/C": ["air conditioning", "AC"],
    "fuel problem": ["fuel filter", "fuel pump", "fuel leak", "fuel fault"],
    "fuel issue": ["fuel filter", "fuel pump", "fuel system"],
    "why is the watermaker not working": ["watermaker fault", "watermaker maintenance", "watermaker repair"],
    "watermaker not working": ["watermaker fault", "watermaker issue"],
    "engine's oil leak": ["engine oil leak"],
    "engines oil leak": ["engine oil leak"],

    # COMPOUND CASES
    "genrator overheeting problm": ["generator overheat fault", "generator temperature issue"],
    "AC compresser maintanance": ["AC compressor maintenance", "air conditioning service"],
    "cat gennie wont start": ["generator won't start", "generator fault", "starting issue"],
    "mantanece servise engne": ["engine maintenance service"],
    "mantenance genrator certficate": ["maintenance", "generator", "certificate"],
    "cat gennie power problm overheting": ["generator power fault", "generator overheat", "caterpillar generator"],
}


def generate_update_sql(yacht_id: str, search_term: str, target_patterns: List[str]) -> List[str]:
    """
    Generate SQL UPDATE statements for a search term mapping.
    Returns list of SQL statements.
    """
    sql_statements = []

    for target in target_patterns:
        # Generate SQL to find and update matching entities
        sql = f"""
-- Mapping: "{search_term}" -> "{target}"
UPDATE search_index
SET
    learned_keywords = CASE
        WHEN learned_keywords IS NULL OR learned_keywords = '' THEN '{search_term}'
        WHEN learned_keywords NOT LIKE '%{search_term}%' THEN learned_keywords || ' {search_term}'
        ELSE learned_keywords
    END,
    learned_at = NOW()
WHERE yacht_id = '{yacht_id}'
AND (
    payload->>'entity_name' ILIKE '%{target}%'
    OR search_text ILIKE '%{target}%'
)
AND (learned_keywords IS NULL OR learned_keywords NOT LIKE '%{search_term}%');
"""
        sql_statements.append(sql.strip())

    return sql_statements


def generate_all_sql(yacht_id: str) -> str:
    """
    Generate complete SQL script for all learned keyword mappings.
    """
    output = []

    output.append("-- ===========================================================================")
    output.append("-- Adversarial Learning Keywords Seeding Script")
    output.append("-- ===========================================================================")
    output.append("-- Purpose: Seed learned_keywords for Shard 11 extreme case search tests")
    output.append(f"-- Yacht ID: {yacht_id}")
    output.append("-- Generated by: scripts/generate_learned_keywords_sql.py")
    output.append("-- ===========================================================================")
    output.append("")
    output.append("BEGIN;")
    output.append("")

    # Group by category
    categories = [
        ("MISSPELLINGS", list(LEARNED_KEYWORDS.items())[:15]),
        ("SEMANTIC DESCRIPTIONS", list(LEARNED_KEYWORDS.items())[15:45]),
        ("WRONG NAME RIGHT IDEA", list(LEARNED_KEYWORDS.items())[45:60]),
        ("COMPOUND CASES", list(LEARNED_KEYWORDS.items())[60:]),
    ]

    total_mappings = 0

    for category_name, mappings in categories:
        output.append(f"-- {'-'*75}")
        output.append(f"-- {category_name}")
        output.append(f"-- {'-'*75}")
        output.append("")

        for search_term, target_patterns in mappings:
            statements = generate_update_sql(yacht_id, search_term, target_patterns)
            output.extend(statements)
            output.append("")
            total_mappings += 1

    output.append("COMMIT;")
    output.append("")
    output.append(f"-- Total mappings processed: {total_mappings}")
    output.append(f"-- Total keywords added: {len(LEARNED_KEYWORDS)}")
    output.append("")
    output.append("-- Verify results:")
    output.append(f"SELECT COUNT(*) as updated_count FROM search_index WHERE yacht_id = '{yacht_id}' AND learned_keywords IS NOT NULL AND learned_keywords != '';")
    output.append("")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Generate SQL for seeding learned keywords',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SQL to stdout
  python3 scripts/generate_learned_keywords_sql.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598"

  # Save to file
  python3 scripts/generate_learned_keywords_sql.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598" > /tmp/seed_keywords.sql

  # Run directly with psql (if you have database credentials)
  python3 scripts/generate_learned_keywords_sql.py --yacht-id "85fe1119-b04c-41ac-80f1-829d23322598" | psql $DATABASE_URL
        """
    )

    parser.add_argument(
        '--yacht-id',
        required=True,
        help='UUID of the yacht to seed (e.g., 85fe1119-b04c-41ac-80f1-829d23322598)'
    )

    args = parser.parse_args()

    # Generate and print SQL
    sql = generate_all_sql(args.yacht_id)
    print(sql)


if __name__ == '__main__':
    main()
