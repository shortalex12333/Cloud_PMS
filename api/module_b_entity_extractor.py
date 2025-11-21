"""
Module B: Maritime Entity Extractor
====================================

Extracts maritime-specific entities from queries:
- Equipment (engines, pumps, generators, etc.)
- Systems (cooling, fuel, electrical, etc.)
- Parts (filters, valves, sensors, etc.)
- Fault codes (E047, SPN/FMI, OBD-II, etc.)
- Measurements (24V, 85°C, 3 bar, etc.)
- Maritime terms (coolant leak, pressure drop, etc.)

STRICT RULES:
- NO interaction with micro-action logic
- Must not affect action detection
- Returns canonical mappings
- Provides confidence scores for each entity
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class EntityDetection:
    """Detected entity with metadata"""
    type: str  # equipment, system, part, fault_code, measurement, maritime_term
    value: str  # Original text
    canonical: str  # Normalized/canonical form
    confidence: float
    span: Tuple[int, int]  # Start, end positions

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
            "confidence": self.confidence,
            "span": list(self.span)
        }


class MaritimeEntityExtractor:
    """
    Maritime entity extractor with comprehensive pattern library.

    Focuses ONLY on identifying WHAT the user is talking about,
    not WHAT they want to do.
    """

    def __init__(self):
        # Equipment patterns
        self.equipment_patterns = {
            # Main equipment
            "main engine": ["main\\s+engine", "me1?", "m\\.?e\\.?\\s*1?"],
            "auxiliary engine": ["aux\\s+engine", "ae\\d?", "auxiliary\\s+gen"],
            "generator": ["generator", "gen\\s*\\d?", "genset"],
            "bilge pump": ["bilge\\s+pump", "bilge"],
            "sea water pump": ["sea\\s*water\\s+pump", "swp", "s\\.?w\\.?p\\.?"],
            "fresh water pump": ["fresh\\s*water\\s+pump", "fwp"],
            "fuel pump": ["fuel\\s+pump"],
            "oil pump": ["oil\\s+pump"],
            "cooling pump": ["cooling\\s+pump"],
            "compressor": ["compressor", "air\\s+compressor"],
            "heat exchanger": ["heat\\s+exchanger", "hx"],
            "turbocharger": ["turbo\\s*charger", "turbo"],
            "alternator": ["alternator"],
            "starter motor": ["starter\\s+motor", "starter"],
        }

        # Systems
        self.system_patterns = {
            "cooling system": ["cooling\\s+system", "coolant\\s+system"],
            "fuel system": ["fuel\\s+system"],
            "electrical system": ["electrical\\s+system", "power\\s+system"],
            "hydraulic system": ["hydraulic\\s+system"],
            "lubrication system": ["lube\\s+system", "oil\\s+system", "lubrication"],
            "exhaust system": ["exhaust\\s+system"],
            "air system": ["air\\s+system", "pneumatic"],
        }

        # Parts
        self.part_patterns = {
            "oil filter": ["oil\\s+filter"],
            "fuel filter": ["fuel\\s+filter"],
            "air filter": ["air\\s+filter"],
            "coolant filter": ["coolant\\s+filter"],
            "impeller": ["impeller"],
            "seal": ["seal", "o-ring"],
            "gasket": ["gasket"],
            "bearing": ["bearing"],
            "valve": ["valve"],
            "sensor": ["sensor", "transducer"],
            "belt": ["belt", "v-belt"],
            "hose": ["hose", "pipe"],
        }

        # Fault codes
        self.fault_code_patterns = [
            # J1939 SPN/FMI
            (r"SPN\s*(\d+)(?:\s*FMI\s*(\d+))?", "fault_code", 0.98),
            # Generic E-codes
            (r"E\d{3,4}", "fault_code", 0.95),
            # OBD-II codes
            (r"[PCBU]\d{4}", "fault_code", 0.95),
            # MTU codes
            (r"MTU\s*\d{3,4}", "fault_code", 0.93),
        ]

        # Measurements
        self.measurement_patterns = [
            # Voltage
            (r"\d+\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?", "voltage", 0.90),
            # Temperature
            (r"\d+\s*[°º]?\s*[CcFf]", "temperature", 0.92),
            # Pressure
            (r"\d+\s*(?:bar|psi|kpa|mbar)", "pressure", 0.92),
            # RPM
            (r"\d+\s*rpm", "rpm", 0.90),
            # Flow
            (r"\d+\s*(?:l/min|gpm|m³/h)", "flow", 0.88),
        ]

        # Maritime terms (symptoms, conditions, etc.)
        self.maritime_terms = {
            "coolant leak": ["coolant\\s+leak", "coolant\\s+leaking"],
            "oil leak": ["oil\\s+leak", "oil\\s+leaking"],
            "pressure drop": ["pressure\\s+drop", "low\\s+pressure"],
            "pressure high": ["high\\s+pressure", "pressure\\s+high"],
            "temperature high": ["high\\s+temp", "overheating", "temp\\s+high"],
            "temperature low": ["low\\s+temp", "temp\\s+low"],
            "vibration": ["vibration", "vibrating"],
            "noise": ["noise", "knocking", "grinding"],
            "alarm": ["alarm", "alert", "warning"],
            "shutdown": ["shutdown", "shut\\s+down", "tripped"],
            "failure": ["failure", "failed", "fault"],
        }

        # Compile patterns
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for performance"""
        self.compiled_equipment = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.equipment_patterns.items()
        }

        self.compiled_systems = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.system_patterns.items()
        }

        self.compiled_parts = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.part_patterns.items()
        }

        self.compiled_maritime_terms = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.maritime_terms.items()
        }

        self.compiled_fault_codes = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.fault_code_patterns
        ]

        self.compiled_measurements = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.measurement_patterns
        ]

    def extract_entities(self, query: str) -> List[EntityDetection]:
        """
        Extract all maritime entities from query.

        Returns list of EntityDetection objects.
        """
        if not query or not query.strip():
            return []

        entities = []

        # Extract equipment
        for canonical, patterns in self.compiled_equipment.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="equipment",
                        value=match.group(0),
                        canonical=canonical.upper().replace(" ", "_"),
                        confidence=0.92,
                        span=(match.start(), match.end())
                    ))

        # Extract systems
        for canonical, patterns in self.compiled_systems.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="system",
                        value=match.group(0),
                        canonical=canonical.upper().replace(" ", "_"),
                        confidence=0.88,
                        span=(match.start(), match.end())
                    ))

        # Extract parts
        for canonical, patterns in self.compiled_parts.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="part",
                        value=match.group(0),
                        canonical=canonical.upper().replace(" ", "_"),
                        confidence=0.85,
                        span=(match.start(), match.end())
                    ))

        # Extract fault codes
        for pattern, entity_type, confidence in self.compiled_fault_codes:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type=entity_type,
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end())
                ))

        # Extract measurements
        for pattern, entity_type, confidence in self.compiled_measurements:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="measurement",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end())
                ))

        # Extract maritime terms
        for canonical, patterns in self.compiled_maritime_terms.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="maritime_term",
                        value=match.group(0),
                        canonical=canonical.upper().replace(" ", "_"),
                        confidence=0.80,
                        span=(match.start(), match.end())
                    ))

        # Remove overlapping entities (keep higher confidence)
        entities = self._deduplicate_entities(entities)

        return entities

    def _deduplicate_entities(self, entities: List[EntityDetection]) -> List[EntityDetection]:
        """
        Remove overlapping entities, keeping those with higher confidence.
        """
        if not entities:
            return []

        # Sort by confidence descending
        entities = sorted(entities, key=lambda e: e.confidence, reverse=True)

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
        "create work order for bilge pump",  # Should extract bilge pump
        "bilge manifold",  # Should extract bilge
        "E047 coolant leak ME1",  # Should extract all three
        "sea water pump pressure low",  # Should extract equipment + maritime term
        "24V generator failure",  # Should extract measurement + equipment + term
    ]

    print("Module B: Maritime Entity Extractor - Quick Tests")
    print("=" * 60)

    for query in test_cases:
        entities = extractor.extract_entities(query)
        print(f"\nQuery: '{query}'")
        print(f"Entities found: {len(entities)}")
        for entity in entities:
            print(f"  - {entity.type}: {entity.value} → {entity.canonical} (conf: {entity.confidence:.2f})")
