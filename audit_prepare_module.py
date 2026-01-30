#!/usr/bin/env python3
"""
Prepare Module Safety Audit Script
===================================

Inventories existing configurations to prevent conflicts during migration.

Usage:
    python3 audit_prepare_module.py --output audit_report.md

Outputs:
    - Entity-to-lens mapping
    - Duplicate detection
    - Ambiguity warnings
    - Migration checklist
"""

import re
import json
from typing import Dict, List, Set, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# =============================================================================
# AUDIT FUNCTIONS
# =============================================================================

def audit_entity_mappings() -> Dict:
    """Audit ENTITY_TO_SEARCH_COLUMN mappings."""

    # Read capability_composer.py
    composer_path = Path("apps/api/prepare/capability_composer.py")

    if not composer_path.exists():
        return {"error": f"File not found: {composer_path}"}

    content = composer_path.read_text()

    # Extract ENTITY_TO_SEARCH_COLUMN dictionary
    pattern = r'ENTITY_TO_SEARCH_COLUMN.*?=\s*\{([^}]+)\}'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {"error": "Could not find ENTITY_TO_SEARCH_COLUMN"}

    dict_content = match.group(1)

    # Parse entity mappings
    entity_pattern = r'"([^"]+)":\s*\("([^"]+)",\s*"([^"]+)"\)'
    mappings = re.findall(entity_pattern, dict_content)

    # Group by capability
    capability_to_entities = defaultdict(list)
    entity_to_capability = {}

    for entity, capability, column in mappings:
        capability_to_entities[capability].append({
            "entity": entity,
            "column": column
        })
        entity_to_capability[entity] = {
            "capability": capability,
            "column": column
        }

    # Detect duplicates
    duplicates = []
    for capability, entities in capability_to_entities.items():
        entity_names = [e["entity"] for e in entities]
        if len(entity_names) != len(set(entity_names)):
            duplicates.append(capability)

    # Detect ambiguous entity names
    ambiguous = []
    ambiguous_keywords = ["LOCATION", "NAME", "QUERY", "SEARCH", "TYPE", "NUMBER", "ID"]
    for entity in entity_to_capability.keys():
        if any(kw in entity for kw in ambiguous_keywords):
            ambiguous.append(entity)

    return {
        "total_entities": len(entity_to_capability),
        "total_capabilities": len(capability_to_entities),
        "entity_to_capability": entity_to_capability,
        "capability_to_entities": dict(capability_to_entities),
        "duplicates": duplicates,
        "ambiguous_entities": ambiguous
    }


def audit_entity_extraction_patterns() -> Dict:
    """Audit entity extraction patterns."""

    extractor_path = Path("apps/api/module_b_entity_extractor.py")

    if not extractor_path.exists():
        # Try alternative path
        extractor_path = Path("apps/api/entity_extraction/module_b_entity_extractor.py")

    if not extractor_path.exists():
        return {
            "error": "Could not find entity extractor file",
            "hard_entity_types": [],
            "soft_entity_types": [],
            "total_entity_types": 0,
            "all_types": []
        }

    content = extractor_path.read_text()

    # Find HARD_ENTITY_TYPES
    hard_pattern = r'HARD_ENTITY_TYPES\s*=\s*\{([^}]+)\}'
    hard_match = re.search(hard_pattern, content, re.DOTALL)
    hard_types = []
    if hard_match:
        hard_content = hard_match.group(1)
        hard_types = re.findall(r"['\"]([^'\"]+)['\"]", hard_content)

    # Find SOFT_ENTITY_TYPES
    soft_pattern = r'SOFT_ENTITY_TYPES\s*=\s*\{([^}]+)\}'
    soft_match = re.search(soft_pattern, content, re.DOTALL)
    soft_types = []
    if soft_match:
        soft_content = soft_match.group(1)
        soft_types = re.findall(r"['\"]([^'\"]+)['\"]", soft_content)

    all_types = set(hard_types + soft_types)

    return {
        "hard_entity_types": hard_types,
        "soft_entity_types": soft_types,
        "total_entity_types": len(all_types),
        "all_types": sorted(all_types)
    }


def audit_intent_taxonomy() -> Dict:
    """Audit intent taxonomy."""

    intent_path = Path("apps/api/intent_parser.py")

    if not intent_path.exists():
        # Try alternative paths
        for alt_path in ["apps/api/orchestration/intent_parser.py", "apps/api/entity_extraction/intent_parser.py"]:
            if Path(alt_path).exists():
                intent_path = Path(alt_path)
                break

    if not intent_path.exists():
        return {
            "error": "Could not find intent_parser.py",
            "total_categories": 0,
            "total_intents": 0,
            "category_to_intents": {},
            "all_intents": []
        }

    content = intent_path.read_text()

    # Extract INTENT_CATEGORIES dictionary
    pattern = r'INTENT_CATEGORIES\s*=\s*\{(.*?)^\}'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

    if not match:
        return {
            "error": "Could not find INTENT_CATEGORIES",
            "total_categories": 0,
            "total_intents": 0,
            "category_to_intents": {},
            "all_intents": []
        }

    dict_content = match.group(1)

    # Parse categories
    category_pattern = r'["\']([^"\']+)["\']\s*:\s*\[(.*?)\]'
    categories = re.findall(category_pattern, dict_content, re.DOTALL)

    category_to_intents = {}
    all_intents = []

    for category, intents_str in categories:
        intents = re.findall(r'["\']([^"\']+)["\']', intents_str)
        category_to_intents[category] = intents
        all_intents.extend(intents)

    return {
        "total_categories": len(category_to_intents),
        "total_intents": len(all_intents),
        "category_to_intents": category_to_intents,
        "all_intents": sorted(all_intents)
    }


def audit_query_intents() -> Dict:
    """Audit GraphRAG query intents."""

    graphrag_path = Path("apps/api/graphrag_query.py")

    if not graphrag_path.exists():
        # Try alternative path
        graphrag_path = Path("apps/api/orchestration/graphrag_query.py")

    if not graphrag_path.exists():
        return {
            "error": "Could not find graphrag_query.py",
            "total_query_intents": 0,
            "query_intents": {}
        }

    content = graphrag_path.read_text()

    # Extract QueryIntent enum
    pattern = r'class QueryIntent.*?:\s*(.*?)(?=\n\nclass|\nACTION_CATALOGUE|\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {
            "error": "Could not find QueryIntent enum",
            "total_query_intents": 0,
            "query_intents": {}
        }

    enum_content = match.group(1)

    # Parse enum values
    intent_pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
    intents = re.findall(intent_pattern, enum_content)

    return {
        "total_query_intents": len(intents),
        "query_intents": {name: value for name, value in intents}
    }


def detect_conflicts(
    entity_mappings: Dict,
    extraction_patterns: Dict,
    intent_taxonomy: Dict,
    query_intents: Dict
) -> Dict:
    """Detect conflicts and ambiguities across modules."""

    conflicts = []

    # Check if extracted entities have capability mappings
    extracted_types = set(extraction_patterns.get("all_types", []))
    mapped_entities = set(entity_mappings.get("entity_to_capability", {}).keys())

    # Entity types that are extracted but not mapped
    unmapped = extracted_types - {e.lower().replace("_", "").replace("-", "") for e in mapped_entities}

    # Entity types that are mapped but not extracted
    unused_mappings = {e.lower() for e in mapped_entities} - extracted_types

    # Ambiguous entity names (same name, different lenses)
    ambiguous = entity_mappings.get("ambiguous_entities", [])

    return {
        "unmapped_entity_types": sorted(unmapped),
        "unused_entity_mappings": sorted(unused_mappings),
        "ambiguous_entity_names": ambiguous,
        "total_conflicts": len(unmapped) + len(unused_mappings) + len(ambiguous)
    }


def generate_lens_ownership_map(
    entity_mappings: Dict,
    extraction_patterns: Dict
) -> Dict[str, List[str]]:
    """
    Generate proposed lens ownership based on entity types and capabilities.

    Returns mapping of lens_name -> list of entity types
    """

    entity_to_cap = entity_mappings.get("entity_to_capability", {})

    # Heuristics for lens assignment
    lens_keywords = {
        "part_lens": ["PART", "MANUFACTURER", "STOCK", "INVENTORY", "SHOPPING"],
        "certificate_lens": ["CERTIFICATE", "CERT_", "COMPLIANCE", "AUDIT"],
        "crew_lens": ["CREW", "PERSON", "ROLE", "RANK", "HOURS_OF_REST"],
        "work_order_lens": ["WORK_ORDER", "WO_", "MAINTENANCE", "CHECKLIST"],
        "document_lens": ["DOCUMENT", "MANUAL", "PROCEDURE", "SECTION"],
        "equipment_lens": ["EQUIPMENT", "MODEL", "BRAND", "SYSTEM"],
        "fault_lens": ["FAULT", "SYMPTOM", "DIAGNOSTIC", "ERROR"],
        "email_lens": ["EMAIL", "SUBJECT", "MESSAGE"],
    }

    lens_ownership = defaultdict(list)

    for entity, mapping in entity_to_cap.items():
        assigned = False

        # Check keywords
        for lens, keywords in lens_keywords.items():
            if any(kw in entity.upper() for kw in keywords):
                lens_ownership[lens].append(entity)
                assigned = True
                break

        # Unassigned entities go to "unknown_lens"
        if not assigned:
            lens_ownership["unknown_lens"].append(entity)

    return dict(lens_ownership)


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_audit_report(output_path: str = "audit_report.md"):
    """Generate comprehensive audit report."""

    print("[Audit] Analyzing entity mappings...")
    entity_mappings = audit_entity_mappings()

    print("[Audit] Analyzing entity extraction patterns...")
    extraction_patterns = audit_entity_extraction_patterns()

    print("[Audit] Analyzing intent taxonomy...")
    intent_taxonomy = audit_intent_taxonomy()

    print("[Audit] Analyzing query intents...")
    query_intents = audit_query_intents()

    print("[Audit] Detecting conflicts...")
    conflicts = detect_conflicts(
        entity_mappings,
        extraction_patterns,
        intent_taxonomy,
        query_intents
    )

    print("[Audit] Generating lens ownership map...")
    lens_ownership = generate_lens_ownership_map(
        entity_mappings,
        extraction_patterns
    )

    # Write report
    with open(output_path, "w") as f:
        f.write("# Prepare Module Audit Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total Entity Types**: {extraction_patterns.get('total_entity_types', 0)}\n")
        f.write(f"- **Total Entity Mappings**: {entity_mappings.get('total_entities', 0)}\n")
        f.write(f"- **Total Capabilities**: {entity_mappings.get('total_capabilities', 0)}\n")
        f.write(f"- **Total Intents**: {intent_taxonomy.get('total_intents', 0)}\n")
        f.write(f"- **Total Query Intents**: {query_intents.get('total_query_intents', 0)}\n")
        f.write(f"- **Total Conflicts**: {conflicts['total_conflicts']}\n\n")

        # Errors (if any)
        if "error" in entity_mappings:
            f.write("## ⚠️ Errors\n\n")
            if "error" in entity_mappings:
                f.write(f"- **Entity Mappings**: {entity_mappings['error']}\n")
            if "error" in extraction_patterns:
                f.write(f"- **Extraction Patterns**: {extraction_patterns['error']}\n")
            if "error" in intent_taxonomy:
                f.write(f"- **Intent Taxonomy**: {intent_taxonomy['error']}\n")
            if "error" in query_intents:
                f.write(f"- **Query Intents**: {query_intents['error']}\n")
            f.write("\n")

        # Conflicts
        f.write("## ⚠️ Conflicts Detected\n\n")
        f.write(f"### Unmapped Entity Types ({len(conflicts['unmapped_entity_types'])})\n")
        f.write("Entity types extracted but no capability mapping:\n\n")
        for entity in conflicts['unmapped_entity_types']:
            f.write(f"- `{entity}`\n")
        f.write("\n")

        f.write(f"### Unused Entity Mappings ({len(conflicts['unused_entity_mappings'])})\n")
        f.write("Entity mappings that don't have extraction patterns:\n\n")
        for entity in conflicts['unused_entity_mappings']:
            f.write(f"- `{entity}`\n")
        f.write("\n")

        f.write(f"### Ambiguous Entity Names ({len(conflicts['ambiguous_entity_names'])})\n")
        f.write("Entity names that may belong to multiple lenses:\n\n")
        for entity in conflicts['ambiguous_entity_names']:
            mapping = entity_mappings.get('entity_to_capability', {}).get(entity, {})
            cap = mapping.get('capability', 'UNKNOWN')
            col = mapping.get('column', 'UNKNOWN')
            f.write(f"- `{entity}` → `{cap}` (column: `{col}`)\n")
        f.write("\n")

        # Lens ownership
        f.write("## Proposed Lens Ownership\n\n")
        for lens, entities in sorted(lens_ownership.items()):
            f.write(f"### {lens} ({len(entities)} entities)\n\n")
            for entity in sorted(entities):
                mapping = entity_mappings.get('entity_to_capability', {}).get(entity, {})
                cap = mapping.get('capability', 'NO_MAPPING')
                f.write(f"- `{entity}` → capability: `{cap}`\n")
            f.write("\n")

        # Capability details
        f.write("## Capability Details\n\n")
        for cap, entities in sorted(entity_mappings.get('capability_to_entities', {}).items()):
            f.write(f"### `{cap}` ({len(entities)} entities)\n\n")
            for e in entities:
                f.write(f"- Entity: `{e['entity']}`, Column: `{e['column']}`\n")
            f.write("\n")

        # Intent taxonomy
        if intent_taxonomy.get('category_to_intents'):
            f.write("## Intent Taxonomy\n\n")
            for category, intents in sorted(intent_taxonomy['category_to_intents'].items()):
                f.write(f"### {category} ({len(intents)} intents)\n\n")
                for intent in intents:
                    f.write(f"- `{intent}`\n")
                f.write("\n")

        # Query intents
        if query_intents.get('query_intents'):
            f.write("## Query Intents (GraphRAG)\n\n")
            for name, value in sorted(query_intents['query_intents'].items()):
                f.write(f"- `{name}` = `\"{value}\"`\n")
            f.write("\n")

    print(f"[Audit] ✅ Report generated: {output_path}")

    # Print summary to console
    print("\n" + "="*60)
    print("AUDIT SUMMARY")
    print("="*60)
    print(f"Total Conflicts: {conflicts['total_conflicts']}")
    print(f"  - Unmapped entities: {len(conflicts['unmapped_entity_types'])}")
    print(f"  - Unused mappings: {len(conflicts['unused_entity_mappings'])}")
    print(f"  - Ambiguous names: {len(conflicts['ambiguous_entity_names'])}")
    print(f"\nProposed Lenses: {len(lens_ownership)}")
    for lens, entities in sorted(lens_ownership.items()):
        print(f"  - {lens}: {len(entities)} entities")
    print("="*60)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    output_file = sys.argv[1] if len(sys.argv) > 1 else "audit_report.md"

    try:
        generate_audit_report(output_file)
        sys.exit(0)
    except Exception as e:
        print(f"[Audit] ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
