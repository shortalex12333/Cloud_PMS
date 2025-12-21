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


# =============================================================================
# HARD vs SOFT ENTITY CLASSIFICATION
# =============================================================================
# Hard entities: High confidence, specific identifiers, can trigger direct actions
# Soft entities: Context-dependent, subjective, may need validation
HARD_ENTITY_TYPES = {
    'fault_code',    # E047, SPN 100 FMI 3 - specific diagnostic codes
    'measurement',   # 24V, 85°C, 2 bar - concrete values
    'model',         # 16V4000, 3512, LB-2800 - specific identifiers
    'brand',         # MTU, Caterpillar, Furuno - known manufacturers
    'part',          # membrane, impeller - specific components
    'equipment',     # generator, radar, pump - known equipment types
}

SOFT_ENTITY_TYPES = {
    'symptom',       # overheating, vibration - subjective, needs context
    'observation',   # reported, noticed - human perception
    'diagnostic',    # high exhaust temperature - interpretive
    'action',        # replace, inspect - intent, may need confirmation
    'person',        # captain, engineer - role reference
    'system',        # cooling system - broad category
    'location',      # engine room - spatial reference
    'maritime_term', # general maritime vocabulary
}


@dataclass
class EntityDetection:
    """Detected entity with metadata"""
    type: str  # equipment, system, part, fault_code, measurement, maritime_term, symptom, action
    value: str  # Original text
    canonical: str  # Normalized/canonical form
    confidence: float
    span: Tuple[int, int]  # Start, end positions
    metadata: Optional[Dict] = None  # Additional metadata (domain, subdomain, group)

    @property
    def is_hard(self) -> bool:
        """Check if this is a 'hard' entity (high confidence, actionable)."""
        return self.type in HARD_ENTITY_TYPES

    @property
    def is_soft(self) -> bool:
        """Check if this is a 'soft' entity (needs validation/context)."""
        return self.type in SOFT_ENTITY_TYPES or self.type not in HARD_ENTITY_TYPES

    @property
    def hardness(self) -> str:
        """Return 'hard' or 'soft' classification."""
        return 'hard' if self.is_hard else 'soft'

    def to_dict(self) -> Dict:
        """Simplified output for search pipeline."""
        return {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
        }


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
            # Generic E-codes (with optional hyphen: E-15, E047, E-047)
            (r"E[-\s]?\d{2,4}", "fault_code", 0.95),
            # OBD-II codes
            (r"[PCBU]\d{4}", "fault_code", 0.95),
            # MTU codes
            (r"MTU\s*\d{3,4}", "fault_code", 0.93),
            # CAT/Caterpillar codes
            (r"(?:CAT|Caterpillar)\s*\d{3,4}", "fault_code", 0.92),
            # Volvo codes
            (r"MID\s*\d+\s*PID\s*\d+", "fault_code", 0.90),
            # Alarm codes
            (r"(?:alarm|error|fault)\s*(?:code)?\s*[A-Z]?\d{2,5}", "fault_code", 0.88),
        ]

        # Model number patterns
        self.model_patterns = [
            # Engine models: 16V4000, 3512B, C32, etc.
            (r"\b\d{1,2}V\d{3,4}[A-Z]?\b", "model", 0.92),  # 16V4000, 12V2000
            (r"\b\d{4}[A-Z]?\b", "model", 0.85),  # 3512, 3516B
            (r"\b[A-Z]\d{2}[A-Z]?\b", "model", 0.80),  # C32, C18
            # Electronic models: LB-2800, FAR-2127, etc.
            (r"\b[A-Z]{2,4}[-\s]?\d{3,5}[A-Z]?\b", "model", 0.88),
        ]

        # Measurements - keep original patterns (these are good)
        self.measurement_patterns = [
            # Voltage (require V or volt)
            (r"\d+(?:\.\d+)?\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?", "voltage", 0.90),
            # Temperature (require degree symbol OR full word)
            (r"\d+(?:\.\d+)?\s*[°º]\s*[CcFf]", "temperature", 0.92),  # 85°C, 100°F
            (r"\d+(?:\.\d+)?\s*(?:celsius|fahrenheit)", "temperature", 0.92),  # 85 celsius
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

        self.compiled_models = [
            (re.compile(pattern), entity_type, confidence)
            for pattern, entity_type, confidence in self.model_patterns
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
        # Blacklist short patterns that cause false positives
        DIAGNOSTIC_BLACKLIST = {
            'co', 'run', 'ran', 'set', 'get', 'put', 'add', 'end', 'use',
            'low', 'off', 'out', 'hot', 'old', 'new', 'bad', 'oil', 'air',
        }

        if self._diagnostic_patterns:
            for entity_type, pattern_list in self._diagnostic_patterns.items():
                for pattern, domain, subdomain, canonical in pattern_list:
                    for match in pattern.finditer(query):
                        matched_text = match.group(0).lower().strip()

                        # Skip blacklisted short patterns
                        if matched_text in DIAGNOSTIC_BLACKLIST:
                            continue

                        # Skip very short matches (< 4 chars) unless high value
                        if len(matched_text) < 4:
                            continue

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
        # 2. CORE GAZETTEER - Brands, Equipment, Parts, Symptoms (HIGH PRIORITY)
        # =====================================================================
        if self._gazetteer:
            # 2a. Check for BRANDS (e.g., MTU, Caterpillar, Furuno)
            for brand in self._gazetteer.get('brand', set()):
                # Use word boundary matching
                pattern = re.compile(r'\b' + re.escape(brand) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="brand",
                        value=match.group(0),
                        canonical=brand.upper().replace(" ", "_"),
                        confidence=0.95,
                        span=(match.start(), match.end()),
                        metadata={"source": "core_gazetteer", "type": "brand"}
                    ))

            # 2b. Check for EQUIPMENT (e.g., radar, watermaker, generator)
            for equip in self._gazetteer.get('equipment', set()):
                pattern = re.compile(r'\b' + re.escape(equip) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="equipment",
                        value=match.group(0),
                        canonical=equip.upper().replace(" ", "_"),
                        confidence=0.90,
                        span=(match.start(), match.end()),
                        metadata={"source": "core_gazetteer", "type": "equipment"}
                    ))

            # 2c. Check for PARTS (e.g., membrane, impeller, seal)
            # Allow short maritime acronyms (AVR, PTU, HPU, VFD, PLC, ECU, ECM)
            ALLOWED_SHORT_PARTS = {'avr', 'ptu', 'hpu', 'vfd', 'plc', 'ecu', 'ecm', 'pcb'}
            for part in self._gazetteer.get('part', set()):
                if len(part) >= 4 or part.lower() in ALLOWED_SHORT_PARTS:
                    pattern = re.compile(r'\b' + re.escape(part) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="part",
                            value=match.group(0),
                            canonical=part.upper().replace(" ", "_"),
                            confidence=0.85,
                            span=(match.start(), match.end()),
                            metadata={"source": "core_gazetteer", "type": "part"}
                        ))

            # 2d. Check for SYMPTOMS (e.g., overheating, vibration, alarm)
            for symptom in self._gazetteer.get('symptom', set()):
                if len(symptom) >= 4:  # Skip very short symptoms
                    pattern = re.compile(r'\b' + re.escape(symptom) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="symptom",
                            value=match.group(0),
                            canonical=symptom.upper().replace(" ", "_"),
                            confidence=0.88,
                            span=(match.start(), match.end()),
                            metadata={"source": "core_gazetteer", "type": "symptom"}
                        ))

            # 2e. Check for system types (lower priority)
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
        # 4. MODEL NUMBERS - Specialized patterns
        # =====================================================================
        for pattern, entity_type, confidence in self.compiled_models:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="model",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", "").replace("-", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "model_pattern"}
                ))

        # =====================================================================
        # 5. MEASUREMENTS - Specialized patterns
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
        # 6. PERSONS/ROLES - Crew positions
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

    def extract_and_classify(self, query: str) -> Dict[str, List[EntityDetection]]:
        """
        Extract entities and group them by hardness classification.

        Returns:
            {
                'hard': [EntityDetection, ...],  # Actionable entities
                'soft': [EntityDetection, ...],  # Entities needing validation
            }
        """
        entities = self.extract_entities(query)
        return {
            'hard': [e for e in entities if e.is_hard],
            'soft': [e for e in entities if e.is_soft],
        }

    def get_extraction_summary(self, query: str) -> Dict:
        """
        Get a summary of extraction results with hard/soft breakdown.

        Returns:
            {
                'query': str,
                'total_entities': int,
                'hard_count': int,
                'soft_count': int,
                'hard_entities': [...],
                'soft_entities': [...],
                'by_type': {'brand': 2, 'symptom': 1, ...}
            }
        """
        classified = self.extract_and_classify(query)

        by_type = {}
        for e in classified['hard'] + classified['soft']:
            by_type[e.type] = by_type.get(e.type, 0) + 1

        return {
            'query': query,
            'total_entities': len(classified['hard']) + len(classified['soft']),
            'hard_count': len(classified['hard']),
            'soft_count': len(classified['soft']),
            'hard_entities': [e.to_dict() for e in classified['hard']],
            'soft_entities': [e.to_dict() for e in classified['soft']],
            'by_type': by_type,
        }

    def extract_with_unknowns(
        self,
        query: str,
        yacht_id: Optional[str] = None,
        log_unknowns: bool = True
    ) -> Dict:
        """
        Extract entities and optionally log unknown terms.

        This is the recommended method for production use as it:
        1. Extracts entities with hard/soft classification
        2. Identifies terms not matched by any pattern
        3. Logs unknowns for pattern gap analysis

        Args:
            query: The query text
            yacht_id: Optional yacht ID for tracking
            log_unknowns: Whether to persist unknowns to database

        Returns:
            {
                'entities': [...],
                'hard_entities': [...],
                'soft_entities': [...],
                'unknowns': [...],
                'summary': {...}
            }
        """
        # Import here to avoid circular imports
        try:
            from unknowns_logger import get_unknowns_logger
            logger = get_unknowns_logger()
        except ImportError:
            logger = None

        # Extract entities
        entities = self.extract_entities(query)

        # Build entity dicts with spans for unknowns detection
        entities_with_spans = [
            {'value': e.value, 'span': list(e.span)}
            for e in entities
        ]

        # Find unknowns (terms not covered by any entity span)
        unknowns = []
        if logger:
            if log_unknowns:
                unknowns = logger.log_query_unknowns(query, entities_with_spans, yacht_id)
            else:
                unknowns = logger.find_unknowns(query, entities_with_spans)

        return {
            'entities': [e.to_dict() for e in entities],
            'unknowns': [u['term'] for u in unknowns],
        }


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
