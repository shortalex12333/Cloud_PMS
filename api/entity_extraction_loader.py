#!/usr/bin/env python3
"""
Loader for ENTITY_EXTRACTION_EXPORT patterns (1,955 patterns from Groups 1-16)
Provides gazetteer terms from Groups 1-10 and diagnostic patterns from Groups 11-16
"""

import json
import re
from pathlib import Path
from typing import Dict, Set, List, Tuple

# Path to ENTITY_EXTRACTION_EXPORT patterns
PATTERNS_DIR = Path("/Users/celeste7/Documents/REGEX_PRODUCTION/ENTITY_EXTRACTION_EXPORT/patterns")


def load_master_index() -> Dict:
    """Load the master index file."""
    master_path = PATTERNS_DIR / "master_index.json"

    if not master_path.exists():
        print(f"⚠️  Warning: Master index not found at {master_path}")
        return {"files": [], "statistics": {}}

    with open(master_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_pattern_file(filename: str) -> Dict:
    """Load a single pattern file."""
    file_path = PATTERNS_DIR / filename

    if not file_path.exists():
        print(f"⚠️  Warning: Pattern file not found: {filename}")
        return {"patterns": []}

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_equipment_gazetteer() -> Dict[str, Set[str]]:
    """
    Load equipment/brand gazetteer from Groups 1-10, 6p2.

    Returns:
        Dictionary mapping entity_type -> set of terms

    Categories loaded:
    - equipment_brand: All brand names from engineering, electrical, navigation, etc.
    - equipment_model: Model-specific terms that are too specific for regex
    """
    master = load_master_index()

    # Groups 1-10, 6p2 are equipment/brand/system gazetteers
    equipment_files = [
        "group_01_engineering_systems.json",
        "group_02_electrical_power_systems.json",
        "group_03_navigation_communication.json",
        "group_04_deck_equipment_exterior.json",
        "group_05_hvac_environmental.json",
        "group_06_interior_systems_amenities.json",
        "group_06_part2_it_systems.json",
        "group_07_safety_security.json",
        "group_09_maintenance_tools_materials.json",
        "group_10_shipyard_design_supply.json"
    ]

    gazetteer = {
        'equipment_brand': set(),  # Brand names (Caterpillar, Furuno, etc.)
        'equipment_type': set(),   # Equipment types (generator, radar, pump)
        'system_type': set()       # System types (propulsion, hydraulic, navigation)
    }

    total_terms = 0
    total_patterns = 0

    # CONTAMINATION FILTERS: Equipment/document terms that should NOT be classified as brands
    # These are generic descriptors, equipment types, or document terms
    equipment_indicators = {
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
        # Additional equipment types found in contamination analysis
        'transponder', 'circuit breaker', 'breaker', 'circuit', 'cable', 'wire', 'fuse',
        'antenna', 'receiver', 'transmitter', 'amplifier', 'repeater', 'splitter',
        'connector', 'terminal', 'junction', 'bus', 'network', 'module', 'card'
    }

    document_indicators = {
        'requirements', 'standards', 'regulations', 'procedures', 'manual',
        'document', 'guide', 'specification', 'code', 'report', 'schedule',
        'program', 'management', 'safety', 'quality', 'compliance',
        'international', 'maritime', 'protocol', 'checklist', 'certificate',
        'marine', 'naval', 'commercial', 'industrial', 'technical'
    }

    product_descriptors = {
        'oil', 'grease', 'lubricant', 'fuel', 'coolant', 'fluid', 'chemical',
        'paint', 'coating', 'sealant', 'adhesive', 'compound', 'cleaner',
        'room temperature', 'temperature', 'pressure', 'voltage', 'current',
        'temperature monitor', 'pressure gauge', 'level sensor', 'flow meter',
        'engine oil', 'hydraulic oil', 'transmission fluid', 'brake fluid'
    }

    # Combine all filters
    all_filters = equipment_indicators | document_indicators | product_descriptors

    for filename in equipment_files:
        data = load_pattern_file(filename)

        for pattern in data.get('patterns', []):
            total_patterns += 1
            domain = pattern.get('domain', '')
            subdomain = pattern.get('subdomain', '')
            terms = pattern.get('terms', [])

            # Add terms to equipment_brand, but filter out equipment/document descriptors
            for term in terms:
                term_lower = term.lower()

                # Skip if term matches equipment/document filter
                if term_lower in all_filters:
                    continue

                # Skip if term contains equipment/document words
                term_words = set(term_lower.split())
                if term_words & all_filters:
                    continue

                # Skip single generic words (these are never brands)
                if len(term_words) == 1 and len(term_lower) < 4:
                    continue

                gazetteer['equipment_brand'].add(term_lower)
                total_terms += 1

            # Also add subdomain as equipment type
            # E.g., "Marine Engines" becomes "marine engines"
            if subdomain:
                gazetteer['equipment_type'].add(subdomain.lower())

            # Add domain as system type
            # E.g., "1: Propulsion Systems" becomes "propulsion systems"
            if domain:
                # Clean up domain format (remove "1:", "2:", etc.)
                clean_domain = re.sub(r'^\d+:\s*', '', domain)
                gazetteer['system_type'].add(clean_domain.lower())

    print(f"✅ Loaded {total_terms:,} terms from {total_patterns} equipment patterns")
    print(f"   - {len(gazetteer['equipment_brand']):,} unique brands")
    print(f"   - {len(gazetteer['equipment_type']):,} unique equipment types")
    print(f"   - {len(gazetteer['system_type']):,} unique system types")

    return gazetteer


def load_diagnostic_patterns() -> Dict[str, List[Tuple[re.Pattern, str, str, str]]]:
    """
    Load diagnostic language patterns from Groups 11-16.

    Returns:
        Dictionary mapping entity_type -> list of (compiled_regex, domain, subdomain, canonical_term)

    Categories loaded:
    - symptom: System symptoms (overheating, vibration, etc.)
    - sensor_language: Sensor diagnostic terms
    - human_report: Human observation language
    - fault_classification: Fault severity/types
    - action: Verbs and actions
    - sensor_reading: Measurement terminology
    """
    # CANONICAL BLACKLIST: Patterns with inappropriate canonicalization
    # These patterns group semantically distinct terms under one canonical (canonicalization misuse)
    # See /tmp/UNIVERSAL_PRINCIPLES_DISCOVERED.md for architectural analysis
    CANONICAL_BLACKLIST = {
        '`power_output_reading`',  # 293x FP, 0% Gospel support - groups "power", "wattage", "kw" inappropriately
        'test_mode',  # Matches "test" inside "latest", "fastest", "greatest" - no word boundaries
    }

    diagnostic_files = {
        'symptom': "group_11_system_symptoms_behavior.json",
        'sensor_language': "group_12_sensor_diagnostic_language.json",
        'human_report': "group_13_human_report_language.json",
        'fault_classification': "group_14_fault_classification.json",
        'action': "group_15_verbs_actions.json",
        'sensor_reading': "group_16_sensor_reading_terms.json"
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

    for entity_type, filename in diagnostic_files.items():
        data = load_pattern_file(filename)

        for pattern in data.get('patterns', []):
            domain = pattern.get('domain', '')
            subdomain = pattern.get('subdomain', '')
            canonical_term = pattern.get('canonical_term', None)
            regex_pattern = pattern.get('regex_pattern', '')

            if not regex_pattern:
                continue

            # ARCHITECTURAL FIX: Skip blacklisted canonical patterns
            if canonical_term in CANONICAL_BLACKLIST:
                blacklisted_count += 1
                continue

            try:
                # Compile regex with case-insensitive flag
                compiled = re.compile(regex_pattern, re.IGNORECASE)
                patterns[entity_type].append((compiled, domain, subdomain, canonical_term))
                total_patterns += 1
            except re.error as e:
                print(f"⚠️  Regex error in {filename} - {subdomain}: {e}")
                continue

    print(f"✅ Loaded {total_patterns} diagnostic patterns:")
    for entity_type, pattern_list in patterns.items():
        print(f"   - {entity_type}: {len(pattern_list)} patterns")

    if blacklisted_count > 0:
        print(f"⚠️  Blacklisted {blacklisted_count} patterns (canonicalization misuse)")

    return patterns


def get_pattern_metadata(domain: str, subdomain: str, group: str) -> Dict:
    """
    Create metadata dict for extracted entity.
    Used for weight calculation.
    """
    return {
        'source_file': 'ENTITY_EXTRACTION_EXPORT',
        'domain': domain,
        'subdomain': subdomain,
        'group': group
    }


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
    base_weight = 2.0

    # Adjust for entity type
    # P1 FIX: Added model and product_name weights to prioritize specificity
    # Problem: "Fischer Panda 8/9" → "generator" (2.8) beat "8/9" (2.0 default)
    # Solution: Model numbers now 4.0 (higher than generic equipment 2.8)
    type_weights = {
        'fault_code': 4.5,           # Fault codes (highest priority)
        'symptom': 4.0,              # Symptoms
        'model': 4.0,                # P1 FIX: Model numbers (specific > generic)
        'fault_classification': 3.8,  # Fault classifications
        'product_name': 3.5,         # P1 FIX: Product names (specific identifiers)
        'sensor_reading': 3.5,       # Sensor readings
        'sensor_language': 3.3,      # Sensor terminology
        'equipment_brand': 3.2,      # Brand names
        'human_report': 3.0,         # Human observations
        'equipment_type': 2.8,       # Generic equipment (should be LOWER than models)
        'action': 2.5,               # Actions/verbs
        'system_type': 2.3           # System types
    }

    base_weight = type_weights.get(entity_type, base_weight)

    # Adjust for specificity (longer = more specific)
    if text_length > 15:
        base_weight += 1.0
    elif text_length > 8:
        base_weight += 0.5

    # Adjust for group (Groups 11-16 are more valuable)
    group = metadata.get('group', '')
    if group and group.startswith(('11', '12', '13', '14', '15', '16')):
        base_weight += 0.5

    # Cap at 5.0
    return min(base_weight, 5.0)


# Module-level cache
_equipment_gazetteer = None
_diagnostic_patterns = None


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


if __name__ == "__main__":
    # Test loader
    print("=" * 80)
    print("ENTITY_EXTRACTION_EXPORT LOADER TEST")
    print("=" * 80)

    # Test master index
    master = load_master_index()
    print(f"\n📊 Master Index:")
    print(f"   Total files: {master['metadata']['total_files']}")
    print(f"   Total patterns: {master['statistics']['total_patterns']:,}")
    print(f"   Total terms: {master['statistics']['total_terms']:,}")

    # Test equipment gazetteer
    print(f"\n🔧 Equipment Gazetteer:")
    gaz = load_equipment_gazetteer()

    # Test diagnostic patterns
    print(f"\n🩺 Diagnostic Patterns:")
    diag = load_diagnostic_patterns()

    # Test sample extraction
    print(f"\n🧪 Sample Test:")
    test_text = "Caterpillar 3512B engine overheating with high coolant temperature"

    # Check equipment brands
    for word in test_text.lower().split():
        if word in gaz['equipment_brand']:
            print(f"   ✅ Found brand: {word}")

    # Check diagnostic patterns
    for entity_type, pattern_list in diag.items():
        for pattern, domain, subdomain, canonical in pattern_list:
            matches = pattern.findall(test_text.lower())
            if matches:
                print(f"   ✅ Found {entity_type}: {matches} (subdomain: {subdomain})")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
