"""
Module B: Maritime Entity Extractor (Enhanced with REGEX_PRODUCTION)
====================================================================

Extracts maritime-specific entities from queries using 1,955 bundled patterns:
- Equipment (engines, pumps, generators, etc.) - Groups 1-10
- Systems (cooling, fuel, electrical, etc.) - Groups 1-10
- Parts (filters, valves, sensors, etc.) - Groups 1-10
- Symptoms (overheating, vibration, leaks, etc.) - Group 11
- Fault codes (E047, SPN/FMI, OBD-II, etc.) - Group 14
- Sensor readings (temperature, pressure, voltage) - Groups 12, 16
- Actions (replace, inspect, calibrate) - Group 15
- Measurements (24V, 85°C, 3 bar, etc.)

STRICT RULES:
- NO interaction with micro-action logic
- Must not affect action detection
- Returns canonical mappings
- Provides confidence scores for each entity

Enhanced from original 60 patterns to 1,955 patterns (32x increase in coverage).
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

# Import bundled pattern data
try:
    from api.entity_extraction_loader import (
        get_equipment_gazetteer,
        get_diagnostic_patterns,
        calculate_weight,
        extract_entities_from_text,
        PATTERNS_AVAILABLE
    )
except ImportError:
    try:
        from entity_extraction_loader import (
            get_equipment_gazetteer,
            get_diagnostic_patterns,
            calculate_weight,
            extract_entities_from_text,
            PATTERNS_AVAILABLE
        )
    except ImportError:
        PATTERNS_AVAILABLE = False
        print("⚠️  Warning: entity_extraction_loader not found. Using fallback patterns.")


@dataclass
class EntityDetection:
    """Detected entity with metadata"""
    type: str  # equipment, system, part, fault_code, measurement, maritime_term, symptom, action
    value: str  # Original text
    canonical: str  # Normalized/canonical form
    confidence: float
    span: Tuple[int, int]  # Start, end positions
    metadata: Optional[Dict] = None  # Additional metadata (domain, subdomain, group)

    def to_dict(self) -> Dict:
        result = {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
            "confidence": self.confidence,
            "span": list(self.span)
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class MaritimeEntityExtractor:
    """
    Maritime entity extractor with comprehensive pattern library.

    Uses REGEX_PRODUCTION bundled patterns (1,955 patterns, 62,987 terms)
    for maritime-specific entity extraction.

    Focuses ONLY on identifying WHAT the user is talking about,
    not WHAT they want to do.
    """

    def __init__(self):
        # Load bundled patterns if available
        self._gazetteer = None
        self._diagnostic_patterns = None
        self._patterns_loaded = False

        # Fault codes - keep original patterns (these are good)
        self.fault_code_patterns = [
            # J1939 SPN/FMI
            (r"SPN\s*(\d+)(?:\s*FMI\s*(\d+))?", "fault_code", 0.98),
            # Generic E-codes
            (r"E\d{3,4}", "fault_code", 0.95),
            # OBD-II codes
            (r"[PCBU]\d{4}", "fault_code", 0.95),
            # MTU codes
            (r"MTU\s*\d{3,4}", "fault_code", 0.93),
            # CAT/Caterpillar codes
            (r"(?:CAT|Caterpillar)\s*\d{3,4}", "fault_code", 0.92),
            # Volvo codes
            (r"MID\s*\d+\s*PID\s*\d+", "fault_code", 0.90),
        ]

        # Measurements - keep original patterns (these are good)
        self.measurement_patterns = [
            # Voltage
            (r"\d+(?:\.\d+)?\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?", "voltage", 0.90),
            # Temperature
            (r"\d+(?:\.\d+)?\s*[°º]?\s*[CcFf](?:elsius|ahrenheit)?", "temperature", 0.92),
            # Pressure
            (r"\d+(?:\.\d+)?\s*(?:bar|psi|kpa|mbar|Pa)", "pressure", 0.92),
            # RPM
            (r"\d+\s*rpm", "rpm", 0.90),
            # Flow
            (r"\d+(?:\.\d+)?\s*(?:l/min|gpm|m³/h|lpm)", "flow", 0.88),
            # Current
            (r"\d+(?:\.\d+)?\s*[Aa](?:mps?)?", "current", 0.88),
            # Frequency
            (r"\d+(?:\.\d+)?\s*[Hh]z", "frequency", 0.88),
            # Hours
            (r"\d+(?:,\d{3})*\s*(?:hours?|hrs?|running\s*hours?)", "hours", 0.85),
        ]

        # Person/Role patterns - keep original
        self.person_patterns = {
            "captain": [r"\bcaptain\b", r"\bmaster\b"],
            "chief_engineer": [r"\bchief\s+engineer\b", r"\bce\b", r"\bc\.?e\.?\b"],
            "2nd_engineer": [r"\b2nd\s+engineer\b", r"\bsecond\s+engineer\b", r"\b2e\b"],
            "3rd_engineer": [r"\b3rd\s+engineer\b", r"\bthird\s+engineer\b", r"\b3e\b"],
            "electrician": [r"\belectrician\b", r"\beto\b"],
            "bosun": [r"\bbosun\b", r"\bbo'?sun\b"],
            "1st_officer": [r"\b1st\s+officer\b", r"\bfirst\s+officer\b", r"\bchief\s+officer\b"],
        }

        # Compile patterns
        self._compile_patterns()

        # Lazy-load bundled patterns
        self._load_bundled_patterns()

    def _load_bundled_patterns(self):
        """Lazy-load bundled REGEX_PRODUCTION patterns."""
        if self._patterns_loaded:
            return

        if not PATTERNS_AVAILABLE:
            print("⚠️  Bundled patterns not available. Using fallback mode.")
            self._patterns_loaded = True
            return

        try:
            self._gazetteer = get_equipment_gazetteer()
            self._diagnostic_patterns = get_diagnostic_patterns()
            self._patterns_loaded = True
            print(f"✅ Loaded bundled patterns: {len(self._gazetteer.get('equipment_brand', set()))} brands, "
                  f"{sum(len(v) for v in self._diagnostic_patterns.values())} diagnostic patterns")
        except Exception as e:
            print(f"⚠️  Error loading bundled patterns: {e}")
            self._patterns_loaded = True

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self.compiled_fault_codes = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.fault_code_patterns
        ]

        self.compiled_measurements = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.measurement_patterns
        ]

        self.compiled_persons = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.person_patterns.items()
        }

    def extract_entities(self, query: str) -> List[EntityDetection]:
        """
        Extract all maritime entities from query.

        Returns list of EntityDetection objects.
        """
        if not query or not query.strip():
            return []

        entities = []
        query_lower = query.lower()

        # Ensure patterns are loaded
        self._load_bundled_patterns()

        # =====================================================================
        # 1. DIAGNOSTIC PATTERNS (Groups 11-16) - Symptoms, faults, actions
        # =====================================================================
        if self._diagnostic_patterns:
            for entity_type, pattern_list in self._diagnostic_patterns.items():
                for pattern, domain, subdomain, canonical in pattern_list:
                    for match in pattern.finditer(query):
                        # Map diagnostic type to output type
                        output_type = self._map_diagnostic_type(entity_type)
                        entities.append(EntityDetection(
                            type=output_type,
                            value=match.group(0),
                            canonical=canonical.upper().replace(" ", "_") if canonical else subdomain.upper().replace(" ", "_"),
                            confidence=0.90,
                            span=(match.start(), match.end()),
                            metadata={
                                "source": "diagnostic_pattern",
                                "domain": domain,
                                "subdomain": subdomain,
                                "group": entity_type
                            }
                        ))

        # =====================================================================
        # 2. EQUIPMENT GAZETTEER (Groups 1-10) - Brands, equipment types
        # =====================================================================
        if self._gazetteer:
            # Check for equipment brands
            for brand in self._gazetteer.get('equipment_brand', set()):
                # Use word boundary matching for longer terms
                if len(brand) > 3:
                    pattern = re.compile(r'\b' + re.escape(brand) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="equipment",
                            value=match.group(0),
                            canonical=brand.upper().replace(" ", "_"),
                            confidence=0.85,
                            span=(match.start(), match.end()),
                            metadata={"source": "gazetteer", "type": "brand"}
                        ))
                # Short terms need exact matching
                elif brand in query_lower.split():
                    idx = query_lower.find(brand)
                    if idx >= 0:
                        entities.append(EntityDetection(
                            type="equipment",
                            value=query[idx:idx+len(brand)],
                            canonical=brand.upper(),
                            confidence=0.75,
                            span=(idx, idx + len(brand)),
                            metadata={"source": "gazetteer", "type": "brand"}
                        ))

            # Check for equipment types
            for equip_type in self._gazetteer.get('equipment_type', set()):
                if len(equip_type) > 4 and equip_type in query_lower:
                    idx = query_lower.find(equip_type)
                    entities.append(EntityDetection(
                        type="equipment",
                        value=query[idx:idx+len(equip_type)],
                        canonical=equip_type.upper().replace(" ", "_"),
                        confidence=0.80,
                        span=(idx, idx + len(equip_type)),
                        metadata={"source": "gazetteer", "type": "equipment_type"}
                    ))

            # Check for system types
            for sys_type in self._gazetteer.get('system_type', set()):
                if len(sys_type) > 5 and sys_type in query_lower:
                    idx = query_lower.find(sys_type)
                    entities.append(EntityDetection(
                        type="system",
                        value=query[idx:idx+len(sys_type)],
                        canonical=sys_type.upper().replace(" ", "_"),
                        confidence=0.78,
                        span=(idx, idx + len(sys_type)),
                        metadata={"source": "gazetteer", "type": "system_type"}
                    ))

        # =====================================================================
        # 3. FAULT CODES - Specialized patterns
        # =====================================================================
        for pattern, entity_type, confidence in self.compiled_fault_codes:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type=entity_type,
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "fault_code_pattern"}
                ))

        # =====================================================================
        # 4. MEASUREMENTS - Specialized patterns
        # =====================================================================
        for pattern, entity_type, confidence in self.compiled_measurements:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="measurement",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "measurement_pattern", "measurement_type": entity_type}
                ))

        # =====================================================================
        # 5. PERSONS/ROLES - Crew positions
        # =====================================================================
        for canonical, patterns in self.compiled_persons.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="person",
                        value=match.group(0),
                        canonical=canonical.upper(),
                        confidence=0.85,
                        span=(match.start(), match.end()),
                        metadata={"source": "person_pattern"}
                    ))

        # Remove overlapping entities (keep higher confidence)
        entities = self._deduplicate_entities(entities)

        return entities

    def _map_diagnostic_type(self, entity_type: str) -> str:
        """Map diagnostic pattern types to output entity types."""
        mapping = {
            'symptom': 'symptom',
            'sensor_language': 'diagnostic',
            'human_report': 'observation',
            'fault_classification': 'fault',
            'action': 'action',
            'sensor_reading': 'measurement_term'
        }
        return mapping.get(entity_type, 'maritime_term')

    def _deduplicate_entities(self, entities: List[EntityDetection]) -> List[EntityDetection]:
        """
        Remove overlapping entities, keeping those with higher confidence.
        Also removes very short matches that are likely false positives.
        """
        if not entities:
            return []

        # Filter out very short matches that are likely false positives
        entities = [e for e in entities if len(e.value) >= 2 or e.confidence >= 0.9]

        # Sort by confidence descending, then by span length descending
        entities = sorted(entities, key=lambda e: (e.confidence, e.span[1] - e.span[0]), reverse=True)

        filtered = []
        occupied_spans = []

        for entity in entities:
            # Check for overlap with already selected entities
            overlaps = False
            for start, end in occupied_spans:
                if not (entity.span[1] <= start or entity.span[0] >= end):
                    overlaps = True
                    break

            if not overlaps:
                filtered.append(entity)
                occupied_spans.append(entity.span)

        return filtered


# Singleton instance
_extractor_instance = None


def get_extractor() -> MaritimeEntityExtractor:
    """Get or create singleton extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = MaritimeEntityExtractor()
    return _extractor_instance


if __name__ == "__main__":
    # Quick tests
    extractor = MaritimeEntityExtractor()

    test_cases = [
        "MTU 16V4000 engine overheating with high exhaust temperature",
        "watermaker membrane needs replacement, low output flow",
        "Furuno radar display showing error code E-15",
        "fire damper stuck open in engine room",
        "create work order for bilge pump",
        "E047 coolant leak ME1",
        "sea water pump pressure low 2 bar",
        "24V generator failure alarm",
        "captain reported vibration from main engine at 1800 rpm",
    ]

    print("=" * 80)
    print("Module B: Maritime Entity Extractor - Enhanced Tests")
    print("Using REGEX_PRODUCTION bundled patterns (1,955 patterns, 62,987 terms)")
    print("=" * 80)

    for query in test_cases:
        entities = extractor.extract_entities(query)
        print(f"\nQuery: '{query}'")
        print(f"Entities found: {len(entities)}")
        for entity in entities:
            meta_info = ""
            if entity.metadata:
                source = entity.metadata.get('source', '')
                meta_info = f" [{source}]"
            print(f"  - {entity.type}: '{entity.value}' → {entity.canonical} (conf: {entity.confidence:.2f}){meta_info}")
