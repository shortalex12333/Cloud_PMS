# Prepare Module Migration - Safety Audit Process

**Date**: 2026-01-30
**Purpose**: Inventory existing code to prevent duplicates, conflicts, and regressions during refactor
**Status**: 🔵 PRE-MIGRATION CHECKLIST

---

## Executive Summary

Before implementing the new lens-based capability architecture, we must **inventory and validate** all existing configurations to ensure:

1. ✅ No duplicate entity types across lenses
2. ✅ No conflicting regex patterns in entity extraction
3. ✅ No intent tracking overlaps
4. ✅ All existing capabilities preserved
5. ✅ Clear lens ownership boundaries
6. ✅ Comprehensive test coverage

**Process**: Automated audit script → Manual review → Migration mapping → Validation tests

---

## Audit Targets

### Target 1: Entity-to-Capability Mappings
**File**: `apps/api/prepare/capability_composer.py` (lines 113-137)

**Current State**:
```python
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
    "PART_NAME": ("part_by_part_number_or_name", "name"),
    "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),
    "LOCATION": ("inventory_by_location", "location"),          # AMBIGUOUS!
    "STOCK_QUERY": ("inventory_by_location", "name"),
    "FAULT_CODE": ("fault_by_fault_code", "code"),
    "SYMPTOM": ("fault_by_fault_code", "name"),
    "EQUIPMENT_TYPE": ("fault_by_fault_code", "equipment_type"),
    "DOCUMENT_QUERY": ("documents_search", "content"),
    "MANUAL_SEARCH": ("documents_search", "content"),
    "PROCEDURE_SEARCH": ("documents_search", "content"),
    "ENTITY_LOOKUP": ("graph_node_search", "label"),
    "SYSTEM_NAME": ("graph_node_search", "label"),
    "COMPONENT_NAME": ("graph_node_search", "label"),
    "WORK_ORDER_ID": ("work_order_by_id", "wo_number"),
    "WO_NUMBER": ("work_order_by_id", "wo_number"),
    "EQUIPMENT_NAME": ("equipment_by_name_or_model", "name"),
    "MODEL_NUMBER": ("equipment_by_name_or_model", "model"),
    "EMAIL_SUBJECT": ("email_threads_search", "latest_subject"),
    "EMAIL_SEARCH": ("email_threads_search", "latest_subject"),
}
```

**Audit Questions**:
1. Which entities belong to which lens?
2. Are there ambiguous entities? (e.g., "LOCATION" - Part inventory or Crew location?)
3. Are there duplicate capability mappings? (e.g., DOCUMENT_QUERY, MANUAL_SEARCH, PROCEDURE_SEARCH → all same)
4. Which capabilities are actually implemented?
5. Which capabilities are blocked/deprecated?

### Target 2: Entity Extraction Patterns
**File**: `apps/api/module_b_entity_extractor.py`

**Current State**: 1,955 regex patterns across groups

**Entity Types**:
```python
HARD_ENTITY_TYPES = {
    'fault_code', 'measurement', 'model', 'brand', 'part', 'equipment', 'certificate'
}

SOFT_ENTITY_TYPES = {
    'symptom', 'observation', 'diagnostic', 'action', 'person', 'system',
    'location', 'maritime_term'
}
```

**Audit Questions**:
1. Which entity types map to which lenses?
2. Are there overlapping patterns? (e.g., "generator" could be equipment OR part)
3. Which patterns are lens-specific vs cross-lens?
4. Are there unused entity types (extracted but never used in capabilities)?

### Target 3: Intent Taxonomy
**File**: `apps/api/intent_parser.py`

**Current State**: 67 intents across 10 categories

**Intent Categories**:
- `fix_something` (9 intents)
- `do_maintenance` (13 intents)
- `manage_equipment` (8 intents)
- `control_inventory` (9 intents)
- `communicate_status` (8 intents)
- `comply_audit` (5 intents)
- `procure_suppliers` (7 intents)
- `search_documents` (4 intents)
- `analytics` (4 intents)
- `manage_certificates` (10 intents)

**Audit Questions**:
1. Which intents map to which lenses?
2. Are there lens-specific intent categories?
3. Do all intents have corresponding actions in action router?
4. Which intents trigger entity-specific searches?

### Target 4: Query Intent Routing
**File**: `apps/api/graphrag_query.py` (lines 147-154)

**Current State**:
```python
class QueryIntent(str, Enum):
    DIAGNOSE_FAULT = "diagnose_fault"
    FIND_DOCUMENT = "find_document"
    CREATE_WORK_ORDER = "create_work_order"
    ADD_TO_HANDOVER = "add_to_handover"
    FIND_PART = "find_part"
    GENERAL_SEARCH = "general_search"
    EQUIPMENT_HISTORY = "equipment_history"
```

**Audit Questions**:
1. How do QueryIntents map to lens domains?
2. Are there missing lens-specific intents? (e.g., FIND_CERTIFICATE, FIND_CREW_MEMBER)
3. Which intents trigger siloed search vs comprehensive search?
4. Are intent keywords hardcoded or configurable?

### Target 5: Table Capabilities Registry
**File**: `apps/api/execute/table_capabilities.py`

**Audit Questions**:
1. Which capabilities are ACTIVE vs BLOCKED?
2. Which tables are searchable?
3. Are there new lens tables missing from capabilities?
4. Which capabilities have timeout issues?

---

## Audit Script

### Script: `audit_prepare_module.py`

```python
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

# =============================================================================
# AUDIT FUNCTIONS
# =============================================================================

def audit_entity_mappings() -> Dict:
    """Audit ENTITY_TO_SEARCH_COLUMN mappings."""

    # Read capability_composer.py
    composer_path = Path("apps/api/prepare/capability_composer.py")
    content = composer_path.read_text()

    # Extract ENTITY_TO_SEARCH_COLUMN dictionary
    pattern = r'ENTITY_TO_SEARCH_COLUMN.*?=\s*{([^}]+)}'
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
    content = extractor_path.read_text()

    # Find HARD_ENTITY_TYPES
    hard_pattern = r'HARD_ENTITY_TYPES\s*=\s*{([^}]+)}'
    hard_match = re.search(hard_pattern, content, re.DOTALL)
    hard_types = []
    if hard_match:
        hard_content = hard_match.group(1)
        hard_types = re.findall(r"'([^']+)'", hard_content)

    # Find SOFT_ENTITY_TYPES
    soft_pattern = r'SOFT_ENTITY_TYPES\s*=\s*{([^}]+)}'
    soft_match = re.search(soft_pattern, content, re.DOTALL)
    soft_types = []
    if soft_match:
        soft_content = soft_match.group(1)
        soft_types = re.findall(r"'([^']+)'", soft_content)

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
    content = intent_path.read_text()

    # Extract INTENT_CATEGORIES dictionary
    pattern = r'INTENT_CATEGORIES\s*=\s*{(.*?)^}'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

    if not match:
        return {"error": "Could not find INTENT_CATEGORIES"}

    dict_content = match.group(1)

    # Parse categories
    category_pattern = r'"([^"]+)":\s*\[(.*?)\]'
    categories = re.findall(category_pattern, dict_content, re.DOTALL)

    category_to_intents = {}
    all_intents = []

    for category, intents_str in categories:
        intents = re.findall(r'"([^"]+)"', intents_str)
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
    content = graphrag_path.read_text()

    # Extract QueryIntent enum
    pattern = r'class QueryIntent.*?:\s*(.*?)(?=\n\nclass|\nACTION_CATALOGUE)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {"error": "Could not find QueryIntent enum"}

    enum_content = match.group(1)

    # Parse enum values
    intent_pattern = r'(\w+)\s*=\s*"([^"]+)"'
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
    extracted_types = set(extraction_patterns["all_types"])
    mapped_entities = set(entity_mappings["entity_to_capability"].keys())

    # Entity types that are extracted but not mapped
    unmapped = extracted_types - {e.lower() for e in mapped_entities}

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

    entity_to_cap = entity_mappings["entity_to_capability"]

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
        f.write(f"- **Total Entity Types**: {extraction_patterns['total_entity_types']}\n")
        f.write(f"- **Total Entity Mappings**: {entity_mappings['total_entities']}\n")
        f.write(f"- **Total Capabilities**: {entity_mappings['total_capabilities']}\n")
        f.write(f"- **Total Intents**: {intent_taxonomy['total_intents']}\n")
        f.write(f"- **Total Query Intents**: {query_intents['total_query_intents']}\n")
        f.write(f"- **Total Conflicts**: {conflicts['total_conflicts']}\n\n")

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
            mapping = entity_mappings['entity_to_capability'][entity]
            f.write(f"- `{entity}` → `{mapping['capability']}` (column: `{mapping['column']}`)\n")
        f.write("\n")

        # Lens ownership
        f.write("## Proposed Lens Ownership\n\n")
        for lens, entities in sorted(lens_ownership.items()):
            f.write(f"### {lens} ({len(entities)} entities)\n\n")
            for entity in sorted(entities):
                mapping = entity_mappings['entity_to_capability'].get(entity, {})
                cap = mapping.get('capability', 'NO_MAPPING')
                f.write(f"- `{entity}` → capability: `{cap}`\n")
            f.write("\n")

        # Capability details
        f.write("## Capability Details\n\n")
        for cap, entities in sorted(entity_mappings['capability_to_entities'].items()):
            f.write(f"### `{cap}` ({len(entities)} entities)\n\n")
            for e in entities:
                f.write(f"- Entity: `{e['entity']}`, Column: `{e['column']}`\n")
            f.write("\n")

        # Intent taxonomy
        f.write("## Intent Taxonomy\n\n")
        for category, intents in sorted(intent_taxonomy['category_to_intents'].items()):
            f.write(f"### {category} ({len(intents)} intents)\n\n")
            for intent in intents:
                f.write(f"- `{intent}`\n")
            f.write("\n")

        # Query intents
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
    from datetime import datetime

    output_file = sys.argv[1] if len(sys.argv) > 1 else "audit_report.md"

    try:
        generate_audit_report(output_file)
        sys.exit(0)
    except Exception as e:
        print(f"[Audit] ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

## Audit Checklist

### Pre-Audit
- [ ] Backup current codebase
- [ ] Document current test coverage
- [ ] Note any in-progress PRs that touch these files

### Run Audit
- [ ] Run `python3 audit_prepare_module.py --output audit_report.md`
- [ ] Review audit_report.md for conflicts
- [ ] Identify ambiguous entity types (e.g., LOCATION)
- [ ] Map all entities to proposed lenses

### Conflict Resolution
- [ ] For ambiguous entities: Rename to be lens-specific
  - `LOCATION` → `PART_STORAGE_LOCATION` (Part Lens) + `CREW_LOCATION` (Crew Lens)
- [ ] For unmapped entities: Decide if they need capabilities or if extraction should be removed
- [ ] For unused mappings: Decide if extraction should be added or mapping removed
- [ ] For duplicate capabilities: Consolidate or namespace

### Validation
- [ ] All entity types have clear lens ownership
- [ ] No overlapping entity names across lenses
- [ ] All capabilities mapped to at least one lens
- [ ] Intent taxonomy aligned with lens structure

### Documentation
- [ ] Update entity type naming conventions
- [ ] Document lens ownership decisions
- [ ] Create migration mapping spreadsheet
- [ ] Update lens worker instructions with audit findings

---

## Expected Conflicts

### Likely Ambiguous Entities

| Entity Name | Current Mapping | Conflict | Resolution |
|-------------|----------------|----------|------------|
| `LOCATION` | `inventory_by_location` | Could be crew location, equipment location, part storage | Rename to `PART_STORAGE_LOCATION`, `EQUIPMENT_LOCATION`, `CREW_LOCATION` |
| `NAME` | Multiple capabilities | Generic, unclear | Rename to `PART_NAME`, `EQUIPMENT_NAME`, `CREW_NAME`, etc. |
| `TYPE` | Multiple capabilities | Generic | Rename to `CERTIFICATE_TYPE`, `EQUIPMENT_TYPE`, etc. |
| `QUERY` | `documents_search` | Ambiguous search type | Rename to `DOCUMENT_CONTENT_QUERY`, `MANUAL_SECTION_QUERY` |
| `SEARCH` | Multiple | Generic | Namespace per lens |

### Likely Unmapped Entities

Entity types that extraction finds but no capability handles:

- `observation` (SOFT type - needs capability?)
- `action` (SOFT type - is this an intent, not entity?)
- `maritime_term` (SOFT type - needs document search capability?)
- `certificate` (HARD type - **MISSING** capability for certificate lens!)

### Likely Unused Mappings

Capabilities mapped but no extraction patterns:

- `ENTITY_LOOKUP` → `graph_node_search` (is graph search still used?)
- `SYSTEM_NAME` → `graph_node_search` (same question)
- `COMPONENT_NAME` → `graph_node_search` (same question)

---

## Migration Decision Tree

```
For each entity type found in audit:

1. Is it lens-specific or cross-lens?
   ├─ Lens-specific → Assign to that lens
   └─ Cross-lens → CONFLICT! Must rename to be lens-specific

2. Does it have a capability mapping?
   ├─ Yes → Keep mapping in lens file
   └─ No → Decide: Add capability OR remove from extraction

3. Does it have extraction patterns?
   ├─ Yes → Keep patterns
   └─ No → Decide: Add patterns OR remove mapping

4. Is the name ambiguous?
   ├─ Yes → Rename to include lens prefix
   └─ No → Keep name

5. Is there test coverage?
   ├─ Yes → Mark for regression testing
   └─ No → Add test in migration

RESULT: Entity assigned to lens with clear boundaries
```

---

## Post-Audit Actions

### 1. Resolve Conflicts
For each conflict in audit report:
- Create GitHub issue
- Assign to lens owner
- Document resolution decision
- Update entity naming

### 2. Update Extraction Patterns
Based on audit findings:
- Remove unused entity types from extraction
- Add missing entity types for new lenses
- Namespace ambiguous patterns

### 3. Update Entity Mappings
Based on lens ownership:
- Rename ambiguous entities
- Add missing capabilities
- Remove deprecated mappings

### 4. Create Migration Mapping
Spreadsheet with columns:
- Old Entity Name
- New Entity Name
- Lens Owner
- Capability Name
- Extraction Pattern ID
- Test Coverage

### 5. Validate with Tests
- Run existing E2E tests (should still pass)
- Add tests for renamed entities
- Verify search results unchanged

---

## Success Criteria

✅ Audit report generated with zero errors
✅ All conflicts identified and documented
✅ Clear lens ownership for every entity type
✅ No ambiguous entity names remaining
✅ All capabilities mapped to lenses
✅ Migration mapping created
✅ Test coverage documented
✅ Team review completed

**Timeline**: 2-3 days for audit + conflict resolution before starting Phase 1 implementation

---

## Output Files

1. **audit_report.md**: Full audit with conflicts and recommendations
2. **lens_ownership_map.json**: Machine-readable lens assignments
3. **migration_checklist.xlsx**: Detailed migration tracking
4. **conflicts_log.md**: All conflicts with resolution status

**Next Step**: Run audit script, review report, resolve conflicts, then proceed to Phase 1 implementation.
