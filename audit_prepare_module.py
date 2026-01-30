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
import argparse
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

    # Normalize for comparison (lowercase, remove underscores/hyphens)
    def normalize(s):
        return s.lower().replace("_", "").replace("-", "")

    extracted_normalized = {normalize(e): e for e in extracted_types}
    mapped_normalized = {normalize(e): e for e in mapped_entities}

    # Entity types that are extracted but not mapped
    unmapped_normalized = set(extracted_normalized.keys()) - set(mapped_normalized.keys())
    unmapped = [extracted_normalized[n] for n in unmapped_normalized]

    # Entity types that are mapped but not extracted
    unused_normalized = set(mapped_normalized.keys()) - set(extracted_normalized.keys())
    unused_mappings = [mapped_normalized[n] for n in unused_normalized]

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

    # Generate report
    report = []
    report.append("# Prepare Module Safety Audit Report")
    report.append("")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append(f"**Status**: {'⚠️ CONFLICTS DETECTED' if conflicts['total_conflicts'] > 0 else '✅ NO CONFLICTS'}")
    report.append("")
    report.append("---")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    report.append(f"- **Total Entity Types Extracted**: {extraction_patterns.get('total_entity_types', 0)}")
    report.append(f"- **Total Entity Mappings**: {entity_mappings.get('total_entities', 0)}")
    report.append(f"- **Total Capabilities**: {entity_mappings.get('total_capabilities', 0)}")
    report.append(f"- **Total Conflicts**: {conflicts['total_conflicts']}")
    report.append("")

    if conflicts['total_conflicts'] > 0:
        report.append("### ⚠️ Conflicts Detected")
        report.append("")
        report.append(f"- **Unmapped Entities**: {len(conflicts['unmapped_entity_types'])} (extracted but no capability)")
        report.append(f"- **Unused Mappings**: {len(conflicts['unused_entity_mappings'])} (mapped but not extracted)")
        report.append(f"- **Ambiguous Names**: {len(conflicts['ambiguous_entity_names'])} (need renaming)")
        report.append("")

    report.append("---")
    report.append("")

    # Conflict Details
    if conflicts['unmapped_entity_types']:
        report.append("## Unmapped Entities")
        report.append("")
        report.append("These entity types are **extracted** but have **no capability mapping**:")
        report.append("")
        for entity in conflicts['unmapped_entity_types']:
            report.append(f"- `{entity}` ← No capability (add to lens)")
        report.append("")
        report.append("**Resolution**: Create capability for each entity or remove from extraction patterns.")
        report.append("")

    if conflicts['unused_entity_mappings']:
        report.append("## Unused Mappings")
        report.append("")
        report.append("These entity types have **capability mappings** but are **not extracted**:")
        report.append("")
        for entity in conflicts['unused_entity_mappings']:
            cap = entity_mappings['entity_to_capability'].get(entity, {})
            report.append(f"- `{entity}` → `{cap.get('capability', 'unknown')}` (no extraction pattern)")
        report.append("")
        report.append("**Resolution**: Add extraction patterns or remove unused mappings.")
        report.append("")

    if conflicts['ambiguous_entity_names']:
        report.append("## Ambiguous Entity Names")
        report.append("")
        report.append("These entity names are **ambiguous** and may conflict across lenses:")
        report.append("")
        for entity in conflicts['ambiguous_entity_names']:
            cap = entity_mappings['entity_to_capability'].get(entity, {})
            report.append(f"- `{entity}` → `{cap.get('capability', 'unknown')}`")
        report.append("")
        report.append("**Resolution**: Rename to be lens-specific (e.g., `LOCATION` → `PART_STORAGE_LOCATION`, `CREW_LOCATION`).")
        report.append("")

    # Lens Ownership Map
    report.append("## Proposed Lens Ownership")
    report.append("")
    report.append("Based on entity naming patterns, here's the proposed lens ownership:")
    report.append("")

    for lens, entities in sorted(lens_ownership.items()):
        report.append(f"### {lens.replace('_', ' ').title()}")
        report.append("")
        report.append(f"Entities: {len(entities)}")
        report.append("")
        for entity in sorted(entities):
            cap = entity_mappings['entity_to_capability'].get(entity, {})
            report.append(f"- `{entity}` → `{cap.get('capability', 'N/A')}`")
        report.append("")

    # Migration Checklist
    report.append("---")
    report.append("")
    report.append("## Pre-Migration Checklist")
    report.append("")
    report.append("Before proceeding with the lens-based refactor:")
    report.append("")
    report.append("- [ ] Resolve all unmapped entities")
    report.append("- [ ] Remove or fix unused mappings")
    report.append("- [ ] Rename ambiguous entity names")
    report.append("- [ ] Verify lens ownership assignments")
    report.append("- [ ] Document entity-to-lens mapping")
    report.append("- [ ] Update test coverage for each lens")
    report.append("")

    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"[Audit] ✅ Report generated: {output_path}")
    print(f"[Audit] Total conflicts: {conflicts['total_conflicts']}")

    return conflicts['total_conflicts']


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit prepare module for conflicts")
    parser.add_argument("--output", default="audit_report.md", help="Output file path")
    args = parser.parse_args()

    conflict_count = generate_audit_report(args.output)

    if conflict_count > 0:
        print(f"\n⚠️  {conflict_count} conflicts detected. Review {args.output} before migration.")
        exit(1)
    else:
        print(f"\n✅ No conflicts detected. Safe to proceed with migration.")
        exit(0)
