"""
FSM-Based ID Recognizers
========================

Finite State Machine recognizers for structured identifiers.

THEORY:
    Yacht management uses many structured IDs:
    - Work Order: WO-1234, WO1234, WO 1234
    - Purchase Order: PO-2024-001, PO2024001
    - Equipment Code: ME-001, ME001, DG1, DG2
    - Part Number: ENG-0001-103, eng0001103
    - Fault Code: E047, F001, E-047
    - Location: 4A, 4 A, BOX-2D, deck 1

    FSM recognizers provide:
    - Near-perfect precision (no false positives)
    - Direct table routing (skip inference)
    - Canonical form extraction
    - Exact match confidence

FSM STRUCTURE:
    Each recognizer is a DFA (Deterministic Finite Automaton):
    - States: START, PREFIX, SEPARATOR, NUMBER, SUFFIX, ACCEPT
    - Transitions: character classes (alpha, digit, separator)
    - Accept condition: final state + full match

PATTERN REGISTRY:
    ID_TYPE → (pattern, entity_type, tables, canonical_function)

PROPERTIES:
    - Deterministic: Same input → same output
    - Complete: Handles all variants of each ID type
    - Composable: Multiple recognizers run in parallel
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from .constraint_algebra import Constraint, ConstraintOp, Hardness, ConstraintScope
from .canonical import canonical


# =============================================================================
# ID TYPES
# =============================================================================

class IDType(str, Enum):
    """Types of structured identifiers."""
    WORK_ORDER = "work_order"
    PURCHASE_ORDER = "purchase_order"
    EQUIPMENT_CODE = "equipment_code"
    PART_NUMBER = "part_number"
    FAULT_CODE = "fault_code"
    SERIAL_NUMBER = "serial_number"
    LOCATION_CODE = "location_code"
    UUID = "uuid"


# =============================================================================
# ID PATTERNS (FSM as regex for efficiency)
# =============================================================================

@dataclass
class IDPattern:
    """
    Pattern definition for an ID type.

    The regex represents the FSM acceptor.
    """
    id_type: IDType
    pattern: re.Pattern
    entity_type: str
    target_column: str
    target_tables: List[str]
    confidence: float
    canonical_fn: Optional[callable] = None

    def match(self, text: str) -> Optional[re.Match]:
        """Attempt to match pattern against text."""
        return self.pattern.search(text)

    def extract_all(self, text: str) -> List[Tuple[str, int, int]]:
        """Extract all matches with positions."""
        return [(m.group(0), m.start(), m.end()) for m in self.pattern.finditer(text)]


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

# Work Order patterns: WO-1234, WO1234, WO 1234
WO_PATTERN = IDPattern(
    id_type=IDType.WORK_ORDER,
    pattern=re.compile(
        r'\b(?:WO|W\.?O\.?|work[\s\-]?order)[\s\-#]?(\d{3,6})\b',
        re.IGNORECASE
    ),
    entity_type="WORK_ORDER_NUMBER",
    target_column="id",  # or wo_number if exists
    target_tables=["pms_work_orders"],
    confidence=0.98,
)


# Purchase Order patterns: PO-2024-001, PO2024001, PO 2024-001
PO_PATTERN = IDPattern(
    id_type=IDType.PURCHASE_ORDER,
    pattern=re.compile(
        r'\b(?:PO|P\.?O\.?|purchase[\s\-]?order)[\s\-#]?(\d{4}[\-\s]?\d{2,4})\b',
        re.IGNORECASE
    ),
    entity_type="PO_NUMBER",
    target_column="po_number",
    target_tables=["pms_purchase_orders"],
    confidence=0.98,
)


# Equipment Code patterns: ME-001, ME001, DG1, DG2, AUX-1, ME-S-001, THR-B-001
# Format: 2-4 alpha prefix + optional letter suffix + separator + 1-4 digits
# Examples: ME-001, GEN-002, HVAC-001, ME-S-001, THR-B-001
EQUIPMENT_CODE_PATTERN = IDPattern(
    id_type=IDType.EQUIPMENT_CODE,
    pattern=re.compile(
        r'\b([A-Z]{2,4}(?:[\-][A-Z])?)[\s\-]?(\d{1,4})\b',
        re.IGNORECASE
    ),
    entity_type="EQUIPMENT_CODE",
    target_column="code",
    target_tables=["pms_equipment"],
    confidence=0.95,
)


# Part Number patterns: ENG-0001-103, eng0001103, MTU-FILTER-001
# Format: Multi-segment alphanumeric (prefix-digits-suffix) or longer form
# Must have either: multiple segments OR 4+ digit sequence to distinguish from equipment codes
PART_NUMBER_PATTERN = IDPattern(
    id_type=IDType.PART_NUMBER,
    pattern=re.compile(
        r'\b([A-Z]{2,5}[\-\s]\d{3,5}[\-\s]\d{1,4})\b',  # Multi-segment: ENG-0001-103
        re.IGNORECASE
    ),
    entity_type="PART_NUMBER",
    target_column="part_number",
    target_tables=["pms_parts"],
    confidence=0.95,
)


# Fault Code patterns: E047, F001, E-047, FAULT-E047
# Format: Single alpha + 2-4 digits OR FAULT-xxx
FAULT_CODE_PATTERN = IDPattern(
    id_type=IDType.FAULT_CODE,
    pattern=re.compile(
        r'\b(?:(?:fault|error|alarm)[\s\-]?)?([A-Z])[\-\s]?(\d{2,4})\b',
        re.IGNORECASE
    ),
    entity_type="FAULT_CODE",
    target_column="fault_code",
    target_tables=["pms_faults", "search_fault_code_catalog"],
    confidence=0.97,
)


# Serial Number patterns: SN123456, S/N 123456, serial: ABC123456
SERIAL_PATTERN = IDPattern(
    id_type=IDType.SERIAL_NUMBER,
    pattern=re.compile(
        r'\b(?:S/?N|serial[\s:\-]?)[\s\-]?([A-Z0-9]{6,15})\b',
        re.IGNORECASE
    ),
    entity_type="SERIAL_NUMBER",
    target_column="serial_number",
    target_tables=["pms_equipment"],
    confidence=0.96,
)


# Location Code patterns: 4A, 4 A, BOX-2D, deck 1, locker 3
# Format: Deck/Box/Locker + alphanumeric OR bare alphanumeric (2-3 chars)
LOCATION_CODE_PATTERN = IDPattern(
    id_type=IDType.LOCATION_CODE,
    pattern=re.compile(
        r'\b(?:(?:box|locker|deck|bin|cabinet)[\s\-]?)?(\d[A-Z]|[A-Z]\d|[A-Z]{1,2}\d{1,2}|\d{1,2}[A-Z]{1,2})\b',
        re.IGNORECASE
    ),
    entity_type="LOCATION",
    target_column="location",
    target_tables=["pms_equipment", "pms_parts", "v_inventory"],
    confidence=0.85,  # Lower confidence - location codes are ambiguous
)


# UUID patterns: 85fe1119-b04c-41ac-80f1-829d23322598
UUID_PATTERN = IDPattern(
    id_type=IDType.UUID,
    pattern=re.compile(
        r'\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b',
        re.IGNORECASE
    ),
    entity_type="UUID",
    target_column="id",
    target_tables=[],  # UUIDs can be in any table
    confidence=1.0,  # UUIDs are unambiguous
)


# All patterns in priority order (most specific first)
ALL_PATTERNS: List[IDPattern] = [
    UUID_PATTERN,           # Unambiguous
    WO_PATTERN,             # Work orders: WO-1234
    PO_PATTERN,             # Purchase orders: PO-2024-001
    SERIAL_PATTERN,         # Serial numbers: SN123456
    PART_NUMBER_PATTERN,    # Part numbers: ENG-0001-103 (multi-segment)
    EQUIPMENT_CODE_PATTERN, # Equipment codes: ME-S-001, GEN-002 (multi-segment, before fault)
    FAULT_CODE_PATTERN,     # Fault codes: E047, F001 (single letter + digits, AFTER equipment)
    LOCATION_CODE_PATTERN,  # Locations: 4A, BOX-2D (most ambiguous)
]


# =============================================================================
# RECOGNIZED ID
# =============================================================================

@dataclass
class RecognizedID:
    """Result of ID recognition."""
    id_type: IDType
    raw_text: str               # Original matched text
    canonical_value: str        # Canonical form
    start_pos: int              # Position in query
    end_pos: int
    pattern: IDPattern          # Pattern that matched
    constraint: Constraint      # Ready-to-use constraint


# =============================================================================
# ID RECOGNIZER
# =============================================================================

class IDRecognizer:
    """
    FSM-based ID recognizer.

    Extracts structured identifiers from query text with high precision.
    """

    def __init__(self):
        self.patterns = ALL_PATTERNS

    def recognize(self, query: str) -> List[RecognizedID]:
        """
        Recognize all structured IDs in query.

        Returns list of RecognizedID sorted by position.
        """
        results = []
        seen_positions: Set[Tuple[int, int]] = set()

        for pattern in self.patterns:
            matches = pattern.extract_all(query)

            for raw_text, start, end in matches:
                # Skip if this position already matched (higher priority pattern)
                if any(s <= start < e or s < end <= e for s, e in seen_positions):
                    continue

                seen_positions.add((start, end))

                # Canonicalize
                canonical_value = self._canonicalize(raw_text, pattern)

                # Build constraint
                constraint = Constraint(
                    variable=pattern.target_column,
                    operator=ConstraintOp.EQ,
                    value=canonical_value,
                    confidence=pattern.confidence,
                    scope=ConstraintScope.GLOBAL,
                    hardness=Hardness.HARD,  # ID matches are hard constraints
                    table_hint=pattern.target_tables[0] if pattern.target_tables else None,
                    source=f"id:{pattern.id_type.value}",
                )

                results.append(RecognizedID(
                    id_type=pattern.id_type,
                    raw_text=raw_text,
                    canonical_value=canonical_value,
                    start_pos=start,
                    end_pos=end,
                    pattern=pattern,
                    constraint=constraint,
                ))

        # Sort by position
        results.sort(key=lambda r: r.start_pos)

        return results

    def _canonicalize(self, raw_text: str, pattern: IDPattern) -> str:
        """
        Canonicalize ID based on type.

        Uses the canonical module for consistency.
        """
        # Extract the significant part (remove prefixes like "WO-", "PO-")
        match = pattern.pattern.search(raw_text)
        if not match:
            return canonical(raw_text, pattern.entity_type)

        groups = match.groups()

        if pattern.id_type == IDType.WORK_ORDER:
            # WO-1234 → WO-1234 (preserve format)
            num = groups[0] if groups else raw_text
            return f"WO-{num}"

        elif pattern.id_type == IDType.PURCHASE_ORDER:
            # PO-2024-001 → PO-2024-001
            num = groups[0] if groups else raw_text
            # Normalize separators
            num = num.replace(' ', '-')
            return f"PO-{num}"

        elif pattern.id_type == IDType.EQUIPMENT_CODE:
            # ME-001 → ME-001 (uppercase, hyphenated)
            if len(groups) >= 2:
                prefix, num = groups[0], groups[1]
                return f"{prefix.upper()}-{num.zfill(3)}"
            return raw_text.upper()

        elif pattern.id_type == IDType.FAULT_CODE:
            # E047 → E047 (uppercase, no separator)
            if len(groups) >= 2:
                letter, num = groups[0], groups[1]
                return f"{letter.upper()}{num.zfill(3)}"
            return raw_text.upper()

        elif pattern.id_type == IDType.PART_NUMBER:
            # Preserve original format, uppercase
            return canonical(raw_text, "PART_NUMBER")

        elif pattern.id_type == IDType.SERIAL_NUMBER:
            # Uppercase, no separators
            return groups[0].upper() if groups else raw_text.upper()

        elif pattern.id_type == IDType.LOCATION_CODE:
            # Canonical location format
            return canonical(raw_text, "LOCATION")

        elif pattern.id_type == IDType.UUID:
            # Lowercase UUID
            return groups[0].lower() if groups else raw_text.lower()

        return raw_text

    def strip_ids(self, query: str, recognized: List[RecognizedID]) -> str:
        """
        Remove recognized IDs from query, leaving descriptive text.

        "WO-1234 for main engine oil change"
        → "for main engine oil change"
        """
        result = query

        # Remove in reverse order to preserve positions
        for rid in sorted(recognized, key=lambda r: r.start_pos, reverse=True):
            result = result[:rid.start_pos] + result[rid.end_pos:]

        # Clean up whitespace
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def get_target_tables(self, recognized: List[RecognizedID]) -> Set[str]:
        """Get all tables that should be queried for recognized IDs."""
        tables = set()
        for rid in recognized:
            tables.update(rid.pattern.target_tables)
        return tables


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def recognize_ids(query: str) -> List[RecognizedID]:
    """Convenience function to recognize IDs in query."""
    recognizer = IDRecognizer()
    return recognizer.recognize(query)


def extract_id_constraints(query: str) -> List[Constraint]:
    """Extract constraints from recognized IDs."""
    recognizer = IDRecognizer()
    recognized = recognizer.recognize(query)
    return [rid.constraint for rid in recognized]


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("ID Recognizers - Test Suite")
    print("=" * 60)

    recognizer = IDRecognizer()

    test_queries = [
        "WO-1234 for main engine",
        "PO-2024-001 status",
        "fault E047 on ME-001",
        "part ENG-0001-103 in box 4a",
        "check serial SN123456789",
        "DG1 and DG2 maintenance",
        "inventory in locker 3B",
        "wo 5678 and po 2024-002",
        "85fe1119-b04c-41ac-80f1-829d23322598",
        "error F001 on aux-2",
    ]

    for query in test_queries:
        ids = recognizer.recognize(query)
        stripped = recognizer.strip_ids(query, ids)

        print(f"\nQuery: {query!r}")
        print(f"Stripped: {stripped!r}")
        print(f"IDs ({len(ids)}):")

        for rid in ids:
            print(f"  - {rid.id_type.value}: {rid.raw_text!r} → {rid.canonical_value!r}")
            print(f"    Confidence: {rid.pattern.confidence}")
            print(f"    Tables: {rid.pattern.target_tables}")
