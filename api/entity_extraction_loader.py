#!/usr/bin/env python3
"""
Entity Extraction Pattern Loader - Bundled Data Version

This version uses pre-bundled pattern data from regex_production_data.py
instead of loading from local JSON files. This ensures compatibility with
Render deployment where local file paths don't exist.

Provides:
- Equipment gazetteer (brands, equipment types, system types) from Groups 1-10
- Diagnostic patterns (symptoms, faults, sensor language) from Groups 11-16
- Same interface as the file-based loader for drop-in replacement
"""

import re
from typing import Dict, Set, List, Tuple, Optional, Any

# Import bundled pattern data
try:
    from api.regex_production_data import (
        DIAGNOSTIC_PATTERNS,
        EQUIPMENT_PATTERNS,
        STATS,
        extract_diagnostic_entities,
        extract_equipment_entities,
        extract_all_entities,
        lookup_term,
        get_compiled_regex
    )
    PATTERNS_AVAILABLE = True
except ImportError:
    try:
        # Try relative import for direct execution
        from regex_production_data import (
            DIAGNOSTIC_PATTERNS,
            EQUIPMENT_PATTERNS,
            STATS,
            extract_diagnostic_entities,
            extract_equipment_entities,
            extract_all_entities,
            lookup_term,
            get_compiled_regex
        )
        PATTERNS_AVAILABLE = True
    except ImportError:
        PATTERNS_AVAILABLE = False
        print("⚠️  Warning: regex_production_data not found. Pattern matching disabled.")
        DIAGNOSTIC_PATTERNS = {}
        EQUIPMENT_PATTERNS = {}
        STATS = {"total_patterns": 0, "total_terms": 0}


# =============================================================================
# CONTAMINATION FILTERS
# =============================================================================
# Equipment/document terms that should NOT be classified as brands

EQUIPMENT_INDICATORS = {
    'pump', 'motor', 'valve', 'sensor', 'gauge', 'meter', 'controller', 'switch',
    'panel', 'control panel', 'monitor', 'alarm', 'detector', 'indicator', 'display',
    'relay', 'solenoid', 'actuator', 'transmitter', 'transducer', 'converter',
    'filter', 'strainer', 'separator', 'exchanger', 'cooler', 'heater', 'tank',
    'pipe', 'hose', 'fitting', 'coupling', 'adapter', 'flange', 'gasket', 'seal',
    'bearing', 'shaft', 'gear', 'belt', 'chain', 'pulley', 'sprocket', 'clutch',
    'engine', 'generator', 'compressor', 'blower', 'fan', 'propeller', 'impeller',
    'system', 'unit', 'assembly', 'component', 'device', 'equipment', 'apparatus',
    'automatic', 'manual', 'electric', 'hydraulic', 'pneumatic', 'mechanical',
    'float', 'automatic float', 'float switch', 'control', 'monitoring', 'measurement',
    'transponder', 'circuit breaker', 'breaker', 'circuit', 'cable', 'wire', 'fuse',
    'antenna', 'receiver', 'transmitter', 'amplifier', 'repeater', 'splitter',
    'connector', 'terminal', 'junction', 'bus', 'network', 'module', 'card'
}

DOCUMENT_INDICATORS = {
    'requirements', 'standards', 'regulations', 'procedures', 'manual',
    'document', 'guide', 'specification', 'code', 'report', 'schedule',
    'program', 'management', 'safety', 'quality', 'compliance',
    'international', 'maritime', 'protocol', 'checklist', 'certificate',
    'marine', 'naval', 'commercial', 'industrial', 'technical'
}

PRODUCT_DESCRIPTORS = {
    'oil', 'grease', 'lubricant', 'fuel', 'coolant', 'fluid', 'chemical',
    'paint', 'coating', 'sealant', 'adhesive', 'compound', 'cleaner',
    'room temperature', 'temperature', 'pressure', 'voltage', 'current',
    'temperature monitor', 'pressure gauge', 'level sensor', 'flow meter',
    'engine oil', 'hydraulic oil', 'transmission fluid', 'brake fluid'
}

# Canonical patterns to skip (known false positive generators)
CANONICAL_BLACKLIST = {
    '`power_output_reading`',  # Groups "power", "wattage", "kw" inappropriately
    'test_mode',  # Matches "test" inside "latest", "fastest", "greatest"
}

ALL_FILTERS = EQUIPMENT_INDICATORS | DOCUMENT_INDICATORS | PRODUCT_DESCRIPTORS


# =============================================================================
# EQUIPMENT GAZETTEER (Groups 1-10)
# =============================================================================

def load_equipment_gazetteer() -> Dict[str, Set[str]]:
    """
    Build equipment/brand gazetteer from bundled EQUIPMENT_PATTERNS.

    Returns:
        Dictionary mapping entity_type -> set of terms
        - equipment_brand: Brand names (Caterpillar, Furuno, etc.)
        - equipment_type: Equipment types (generator, radar, pump)
        - system_type: System types (propulsion, hydraulic, navigation)
    """
    gazetteer = {
        'equipment_brand': set(),
        'equipment_type': set(),
        'system_type': set()
    }

    total_terms = 0

    for canonical, pattern_data in EQUIPMENT_PATTERNS.items():
        terms = pattern_data.get('terms', [])
        domain = pattern_data.get('domain', '')
        subdomain = pattern_data.get('subdomain', '')

        # Add terms to equipment_brand, filtering out generic descriptors
        for term in terms:
            term_lower = term.lower()

            # Skip if term matches equipment/document filter
            if term_lower in ALL_FILTERS:
                continue

            # Skip if term contains equipment/document words
            term_words = set(term_lower.split())
            if term_words & ALL_FILTERS:
                continue

            # Skip single short generic words
            if len(term_words) == 1 and len(term_lower) < 4:
                continue

            gazetteer['equipment_brand'].add(term_lower)
            total_terms += 1

        # Add subdomain as equipment type
        if subdomain:
            gazetteer['equipment_type'].add(subdomain.lower())

        # Add domain as system type (cleaned)
        if domain:
            clean_domain = re.sub(r'^\d+:\s*', '', domain)
            gazetteer['system_type'].add(clean_domain.lower())

    print(f"✅ Loaded {total_terms:,} terms from {len(EQUIPMENT_PATTERNS)} equipment patterns")
    print(f"   - {len(gazetteer['equipment_brand']):,} unique brands")
    print(f"   - {len(gazetteer['equipment_type']):,} unique equipment types")
    print(f"   - {len(gazetteer['system_type']):,} unique system types")

    return gazetteer


# =============================================================================
# DIAGNOSTIC PATTERNS (Groups 11-16)
# =============================================================================

def load_diagnostic_patterns() -> Dict[str, List[Tuple[re.Pattern, str, str, str]]]:
    """
    Build diagnostic pattern matchers from bundled DIAGNOSTIC_PATTERNS.

    Returns:
        Dictionary mapping entity_type -> list of (compiled_regex, domain, subdomain, canonical_term)
        - symptom: System symptoms (Group 11)
        - sensor_language: Sensor diagnostic terms (Group 12)
        - human_report: Human observation language (Group 13)
        - fault_classification: Fault severity/types (Group 14)
        - action: Verbs and actions (Group 15)
        - sensor_reading: Measurement terminology (Group 16)
    """
    # Map groups to entity types
    GROUP_TO_TYPE = {
        11: 'symptom',
        12: 'sensor_language',
        13: 'human_report',
        14: 'fault_classification',
        15: 'action',
        16: 'sensor_reading'
    }

    patterns = {
        'symptom': [],
        'sensor_language': [],
        'human_report': [],
        'fault_classification': [],
        'action': [],
        'sensor_reading': []
    }

    total_patterns = 0
    blacklisted_count = 0

    for canonical, pattern_data in DIAGNOSTIC_PATTERNS.items():
        # Skip blacklisted patterns
        if canonical in CANONICAL_BLACKLIST:
            blacklisted_count += 1
            continue

        group = pattern_data.get('group', 0)
        entity_type = GROUP_TO_TYPE.get(group)

        if not entity_type:
            continue

        domain = pattern_data.get('domain', '')
        subdomain = pattern_data.get('subdomain', '')
        regex_str = pattern_data.get('regex', '')

        if not regex_str:
            continue

        try:
            compiled = re.compile(regex_str, re.IGNORECASE)
            patterns[entity_type].append((compiled, domain, subdomain, canonical))
            total_patterns += 1
        except re.error as e:
            print(f"⚠️  Regex error in {canonical}: {e}")
            continue

    print(f"✅ Loaded {total_patterns} diagnostic patterns:")
    for entity_type, pattern_list in patterns.items():
        print(f"   - {entity_type}: {len(pattern_list)} patterns")

    if blacklisted_count > 0:
        print(f"⚠️  Blacklisted {blacklisted_count} patterns (canonicalization misuse)")

    return patterns


# =============================================================================
# WEIGHT CALCULATION
# =============================================================================

def calculate_weight(entity_type: str, metadata: Dict, text_length: int = 0) -> float:
    """
    Calculate entity weight based on type, metadata, and specificity.

    Weight ranges:
    - Specific models/codes: 4.0-5.0
    - Brand names: 3.0-3.5
    - Component types: 2.5-3.0
    - Generic terms: 2.0-2.5
    - Symptoms/diagnostics: 3.5-4.5
    - Actions: 2.0-3.0
    """
    type_weights = {
        'fault_code': 4.5,
        'symptom': 4.0,
        'model': 4.0,
        'fault_classification': 3.8,
        'product_name': 3.5,
        'sensor_reading': 3.5,
        'sensor_language': 3.3,
        'equipment_brand': 3.2,
        'human_report': 3.0,
        'equipment_type': 2.8,
        'action': 2.5,
        'system_type': 2.3
    }

    base_weight = type_weights.get(entity_type, 2.0)

    # Adjust for specificity
    if text_length > 15:
        base_weight += 1.0
    elif text_length > 8:
        base_weight += 0.5

    # Adjust for diagnostic groups (more valuable)
    group = metadata.get('group', 0)
    if isinstance(group, int) and 11 <= group <= 16:
        base_weight += 0.5

    return min(base_weight, 5.0)


def get_pattern_metadata(domain: str, subdomain: str, group: str) -> Dict:
    """Create metadata dict for extracted entity."""
    return {
        'source_file': 'regex_production_data',
        'domain': domain,
        'subdomain': subdomain,
        'group': group
    }


# =============================================================================
# CACHED LOADERS
# =============================================================================

_equipment_gazetteer: Optional[Dict[str, Set[str]]] = None
_diagnostic_patterns: Optional[Dict[str, List[Tuple[re.Pattern, str, str, str]]]] = None


def get_equipment_gazetteer() -> Dict[str, Set[str]]:
    """Get cached equipment gazetteer (loads on first call)."""
    global _equipment_gazetteer
    if _equipment_gazetteer is None:
        _equipment_gazetteer = load_equipment_gazetteer()
    return _equipment_gazetteer


def get_diagnostic_patterns() -> Dict[str, List[Tuple[re.Pattern, str, str, str]]]:
    """Get cached diagnostic patterns (loads on first call)."""
    global _diagnostic_patterns
    if _diagnostic_patterns is None:
        _diagnostic_patterns = load_diagnostic_patterns()
    return _diagnostic_patterns


# =============================================================================
# QUICK EXTRACTION WRAPPERS
# =============================================================================

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Extract all entities from text using bundled patterns.

    Returns dict with:
    - diagnostic: List of diagnostic entities (symptoms, faults, etc.)
    - equipment: List of equipment entities (brands, systems, etc.)
    - gazetteer_matches: Direct term matches from gazetteer
    """
    result = {
        'diagnostic': [],
        'equipment': [],
        'gazetteer_matches': []
    }

    if not PATTERNS_AVAILABLE:
        return result

    text_lower = text.lower()

    # Get diagnostic matches using regex
    diag_patterns = get_diagnostic_patterns()
    for entity_type, pattern_list in diag_patterns.items():
        for pattern, domain, subdomain, canonical in pattern_list:
            matches = pattern.findall(text_lower)
            if matches:
                result['diagnostic'].append({
                    'type': entity_type,
                    'canonical': canonical,
                    'domain': domain,
                    'subdomain': subdomain,
                    'matches': list(set(matches))[:5],
                    'confidence': 0.9,
                    'weight': calculate_weight(entity_type, {'group': 11}, len(matches[0]))
                })

    # Get equipment matches using gazetteer
    gazetteer = get_equipment_gazetteer()
    words = set(text_lower.split())

    for term in gazetteer['equipment_brand']:
        if term in text_lower:
            result['gazetteer_matches'].append({
                'type': 'equipment_brand',
                'value': term,
                'confidence': 0.85,
                'weight': calculate_weight('equipment_brand', {}, len(term))
            })

    # Also run bundled extractors for additional coverage
    bundled_results = extract_all_entities(text)
    result['equipment'].extend(bundled_results.get('equipment', []))

    return result


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ENTITY EXTRACTION LOADER - BUNDLED DATA VERSION")
    print("=" * 80)

    print(f"\n📊 Bundled Pattern Stats:")
    print(f"   Total patterns: {STATS.get('total_patterns', 0):,}")
    print(f"   Total terms: {STATS.get('total_terms', 0):,}")
    print(f"   Diagnostic patterns: {STATS.get('diagnostic_patterns', 0)}")
    print(f"   Equipment patterns: {STATS.get('equipment_patterns', 0)}")

    print(f"\n🔧 Loading Equipment Gazetteer...")
    gaz = get_equipment_gazetteer()

    print(f"\n🩺 Loading Diagnostic Patterns...")
    diag = get_diagnostic_patterns()

    # Test extraction
    print(f"\n🧪 Sample Test:")
    test_queries = [
        "MTU 16V4000 engine overheating with high exhaust temperature",
        "watermaker membrane needs replacement, low output",
        "Furuno radar display showing error code E-15",
        "fire damper stuck open in engine room"
    ]

    for query in test_queries:
        print(f"\n   Query: {query}")
        results = extract_entities_from_text(query)
        print(f"   Diagnostic: {len(results['diagnostic'])} entities")
        print(f"   Equipment: {len(results['equipment'])} entities")
        print(f"   Gazetteer: {len(results['gazetteer_matches'])} matches")

        # Show top matches
        if results['diagnostic']:
            top_diag = results['diagnostic'][0]
            print(f"   → Top diagnostic: {top_diag['canonical']} ({top_diag['type']})")
        if results['gazetteer_matches']:
            top_gaz = results['gazetteer_matches'][0]
            print(f"   → Top equipment: {top_gaz['value']} ({top_gaz['type']})")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - Ready for Render deployment")
    print("=" * 80)
