"""
Query Classifier
=================

Classifies queries into LOOKUP (single entity) vs LIST (filtered collection).

This is the foundational fix for the filter_stack test failures.
Previously ALL queries went through entity_id resolution, which fails for LIST queries.

Architecture:
    Query → QueryClassifier → LOOKUP or LIST
                                  ↓
                    LOOKUP: route to entity handler (needs entity_id)
                    LIST: route to list handler (needs filters)

Examples:
    LOOKUP: "show equipment ME-S-001" → needs specific entity
    LIST: "pending work orders" → needs filter on status
    LIST: "out of stock parts" → needs filter on quantity
    LOOKUP: "diagnose E047" → needs specific fault entity

Design Principles:
1. LIST queries have filter keywords but no specific entity identifiers
2. LOOKUP queries have entity codes/identifiers (ME-S-001, E047, etc.)
3. When ambiguous, prefer LOOKUP (safer - will fail gracefully if no entity)
4. Extract filters from LIST queries for downstream handlers

CONJUNCTION SEMANTICS (added):
    - "X and Y" between locations → IN (both locations)
    - "X or Y" → OR (either)
    - "not X", "except X" → NOT (exclusion)
    - Multi-token without explicit conjunction → AND (all must match)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Import conjunction and contradiction handling from pipeline contract
from pipeline_contract import (
    ConjunctionParser,
    ConjunctionRule,
    ConjunctionType,
    ContradictionDetector,
    get_conjunction_parser,
    get_contradiction_detector,
)


class QueryType(str, Enum):
    """Query type classification"""
    LOOKUP = "lookup"   # Single entity retrieval by ID/code
    LIST = "list"       # Filtered collection retrieval
    SEARCH = "search"   # Free-text search
    MUTATE = "mutate"   # Create/update/delete operations


@dataclass
class QueryClassification:
    """Result of query classification"""
    query_type: QueryType
    entity_type: Optional[str]  # equipment, part, work_order, fault
    entity_identifier: Optional[str]  # The code/ID if LOOKUP
    filters: Dict[str, Any] = field(default_factory=dict)  # Extracted filters for LIST
    confidence: float = 0.0
    reasoning: str = ""
    # NEW: Conjunction handling for "2a and 2b", "filter or pump", "not in locker"
    conjunctions: List[ConjunctionRule] = field(default_factory=list)
    # NEW: Contradiction detection for "pending completed"
    contradiction: Optional[str] = None  # Error message if contradictory filters

    def to_dict(self) -> Dict:
        return {
            "query_type": self.query_type.value,
            "entity_type": self.entity_type,
            "entity_identifier": self.entity_identifier,
            "filters": self.filters,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "conjunctions": [
                {"type": c.conjunction_type.value, "operands": c.operands, "raw": c.raw_text}
                for c in self.conjunctions
            ],
            "contradiction": self.contradiction,
        }

    def has_conjunction(self, conj_type: ConjunctionType) -> bool:
        """Check if query has a specific conjunction type."""
        return any(c.conjunction_type == conj_type for c in self.conjunctions)

    def get_in_operands(self) -> List[str]:
        """Get all IN operands (for multi-location queries like '2a and 2b')."""
        operands = []
        for c in self.conjunctions:
            if c.conjunction_type == ConjunctionType.IN:
                operands.extend(c.operands)
        return operands

    def get_not_operands(self) -> List[str]:
        """Get all NOT operands (for exclusion like 'not in locker')."""
        operands = []
        for c in self.conjunctions:
            if c.conjunction_type == ConjunctionType.NOT:
                operands.extend(c.operands)
        return operands


class QueryClassifier:
    """
    Classifies user queries to determine routing strategy.

    Key Innovation:
    - Previously ALL queries tried to resolve entity_id (broke LIST queries)
    - Now LIST queries route to handlers that accept filters instead

    Pattern Priority:
    1. Check for entity identifiers (codes) → LOOKUP
    2. Check for LIST filter keywords → LIST
    3. Check for MUTATE verbs → MUTATE
    4. Default to SEARCH

    NEW: Conjunction handling
    - Parses explicit AND/OR/NOT from queries
    - Detects contradictory filter combinations
    """

    def __init__(self):
        # NEW: Conjunction parser for "2a and 2b", "filter or pump", etc.
        self.conjunction_parser = get_conjunction_parser()
        # NEW: Contradiction detector for "pending completed" etc.
        self.contradiction_detector = get_contradiction_detector()

        # Entity identifier patterns (things that indicate LOOKUP)
        self.entity_patterns = {
            "equipment_code": [
                # ME-S-001, ME-P-001 patterns (flexible separators)
                r'\b(ME[\s\-\.]*[SP][\s\-\.]*\d{3})\b',
                # GEN-001, GEN-002 patterns
                r'\b(GEN[\s\-\.]*\d{3})\b',
                # HVAC-001 pattern
                r'\b(HVAC[\s\-\.]*\d{3})\b',
                # THR-B-001, THR-S-001 patterns
                r'\b(THR[\s\-\.]*[BS][\s\-\.]*\d{3})\b',
                # WM-001 pattern
                r'\b(WM[\s\-\.]*\d{3})\b',
                # HYD-001 pattern
                r'\b(HYD[\s\-\.]*\d{3})\b',
                # STP-001 pattern
                r'\b(STP[\s\-\.]*\d{3})\b',
                # NAV-RAD-001, NAV-AP-001 patterns
                r'\b(NAV[\s\-\.]*(?:RAD|AP)[\s\-\.]*\d{3})\b',
                # FIRE-001 pattern
                r'\b(FIRE[\s\-\.]*\d{3})\b',
                # AUX-001 patterns
                r'\b(AUX[\s\-\.]*\d{3})\b',
                # DG1, DG2 patterns (Diesel Generators)
                r'\b(DG[\s\-\.]*\d{1,2})\b',
                # FW-P-001, FW-S-001 patterns (Fresh Water)
                r'\b(FW[\s\-\.]*[PS][\s\-\.]*\d{3})\b',
                # SEW-001 patterns (Sewage)
                r'\b(SEW[\s\-\.]*\d{3})\b',
                # EL-001, ELEC-001 patterns (Electrical)
                r'\b(EL(?:EC)?[\s\-\.]*\d{3})\b',
            ],
            "part_number": [
                # ENG-0008-103 patterns
                r'\b(ENG[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(PMP[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(FLT[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(HYD[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(GEN[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(NAV[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
            ],
            "fault_code": [
                # E047, E001, G012 patterns
                r'\b([EGH]\d{3})\b',
                # HVAC-05, NAV-R01 patterns
                r'\b([A-Z]{2,4}[\-]?\d{2,3})\b',
            ],
            "work_order_number": [
                # WO-2024-001, WO2024001 patterns
                r'\b(WO[\s\-\.]*\d{4}[\s\-\.]*\d{3})\b',
                r'\b(WO[\s\-]*\d{6,8})\b',
            ],
        }

        # LIST filter keywords (indicate collection query, not single entity)
        self.list_filters = {
            # Status filters (DB uses: completed, planned, in_progress)
            "pending": {"field": "status", "value": "planned", "entity": "work_order"},  # Map pending → planned
            "open": {"field": "status", "value": "planned", "entity": "work_order"},     # Map open → planned
            "in progress": {"field": "status", "value": "in_progress", "entity": "work_order"},
            "in_progress": {"field": "status", "value": "in_progress", "entity": "work_order"},
            "completed": {"field": "status", "value": "completed", "entity": "work_order"},
            "done": {"field": "status", "value": "completed", "entity": "work_order"},
            "finished": {"field": "status", "value": "completed", "entity": "work_order"},
            "overdue": {"field": "is_overdue", "value": True, "entity": "work_order"},
            "planned": {"field": "status", "value": "planned", "entity": "work_order"},
            "scheduled": {"field": "status", "value": "planned", "entity": "work_order"},

            # Stock filters
            "out of stock": {"field": "quantity", "value": 0, "op": "eq", "entity": "part"},
            "low stock": {"field": "quantity", "op": "lt", "compare_field": "min_quantity", "entity": "part"},
            "in stock": {"field": "quantity", "op": "gt", "value": 0, "entity": "part"},

            # Fault filters
            "active faults": {"field": "resolved_at", "value": None, "op": "is_null", "entity": "fault"},
            "unresolved": {"field": "resolved_at", "value": None, "op": "is_null", "entity": "fault"},
            "resolved": {"field": "resolved_at", "op": "not_null", "entity": "fault"},
            "critical": {"field": "severity", "value": "critical", "entity": "fault"},
            "high severity": {"field": "severity", "value": "high", "entity": "fault"},

            # Priority filters (DB uses: routine, critical)
            "high priority": {"field": "priority", "value": "critical", "entity": "work_order"},
            "urgent": {"field": "priority", "value": "critical", "entity": "work_order"},
            "critical": {"field": "priority", "value": "critical", "entity": "work_order"},
            "low priority": {"field": "priority", "value": "routine", "entity": "work_order"},
            "routine": {"field": "priority", "value": "routine", "entity": "work_order"},
        }

        # LIST indicator keywords (words that suggest collection, not single entity)
        self.list_indicators = [
            r'\b(all)\b',
            r'\b(list)\b',
            r'\b(show me all)\b',
            r'\b(every)\b',
            r'\b(any)\b',
            r'\b(which)\b',
            r'^(list)\s',
            r'\b(\d+)\s+(work orders?|parts?|faults?|items?)\b',  # "5 work orders"
        ]

        # MUTATE verb patterns
        self.mutate_verbs = [
            r'^create\s',
            r'^add\s',
            r'^update\s',
            r'^edit\s',
            r'^delete\s',
            r'^remove\s',
            r'^modify\s',
            r'^change\s',
            r'^log\s',
            r'^record\s',
            r'^mark\s',
            r'^set\s',
        ]

        # Entity type detection keywords (when no identifier present)
        # IMPORTANT: Order matters for priority - check work_order before equipment
        # because "work order for pump" should be work_order, not equipment
        self.entity_type_keywords = {
            "work_order": ["work order", "workorder", "wo ", "task", "job", "maintenance"],
            "fault": ["fault", "error", "alarm", "warning", "diagnose", "diagnosis"],
            "part": ["part", "parts", "inventory", "stock", "filter", "seal", "gasket", "bearing"],
            "equipment": ["equipment", "engine", "generator", "pump", "thruster", "hvac", "watermaker", "hydraulic"],
        }

    def classify(self, query: str) -> QueryClassification:
        """
        Classify a query to determine routing strategy.

        Args:
            query: User's natural language query

        Returns:
            QueryClassification with type, entity info, filters, and conjunctions
        """
        query_lower = query.lower().strip()
        query_upper = query.upper()

        # Step 0: Parse conjunctions FIRST (applies to all query types)
        # This handles "box 2a and 2b", "filter or pump", "not in locker"
        conjunctions = self.conjunction_parser.parse(query)

        # Step 1: Check for MUTATE verbs first
        for pattern in self.mutate_verbs:
            if re.search(pattern, query_lower, re.IGNORECASE):
                entity_type = self._detect_entity_type(query_lower)
                return QueryClassification(
                    query_type=QueryType.MUTATE,
                    entity_type=entity_type,
                    entity_identifier=None,
                    confidence=0.85,
                    reasoning=f"Matched mutate verb pattern",
                    conjunctions=conjunctions,
                )

        # Step 2: Check for entity identifiers (specific codes) → LOOKUP
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_upper)
                if match:
                    identifier = match.group(1)
                    # Normalize: remove spaces, standardize separators
                    normalized = self._normalize_identifier(identifier, entity_type)

                    # Map pattern entity type to domain entity type
                    domain_type = self._map_pattern_to_domain(entity_type)

                    return QueryClassification(
                        query_type=QueryType.LOOKUP,
                        entity_type=domain_type,
                        entity_identifier=normalized,
                        confidence=0.92,
                        reasoning=f"Found {entity_type} identifier: {identifier} → {normalized}",
                        conjunctions=conjunctions,
                    )

        # Step 3: Check for LIST filter keywords → LIST
        extracted_filters = {}
        filter_entity_type = None

        for filter_key, filter_config in self.list_filters.items():
            if filter_key in query_lower:
                extracted_filters[filter_config["field"]] = {
                    "value": filter_config.get("value"),
                    "op": filter_config.get("op", "eq"),
                }
                if "compare_field" in filter_config:
                    extracted_filters[filter_config["field"]]["compare_field"] = filter_config["compare_field"]
                filter_entity_type = filter_config["entity"]

        # Check for LIST indicator keywords
        has_list_indicator = any(
            re.search(pattern, query_lower, re.IGNORECASE)
            for pattern in self.list_indicators
        )

        if extracted_filters or has_list_indicator:
            # Determine entity type from filters or keywords
            if not filter_entity_type:
                filter_entity_type = self._detect_entity_type(query_lower)

            # NEW: Check for contradictory filters (e.g., "pending completed")
            # First check extracted filters, then check raw query text
            contradiction = self.contradiction_detector.detect(extracted_filters)
            if not contradiction:
                contradiction = self.contradiction_detector.detect_in_query(query)

            return QueryClassification(
                query_type=QueryType.LIST,
                entity_type=filter_entity_type,
                entity_identifier=None,
                filters=extracted_filters,
                confidence=0.88,
                reasoning=f"LIST query with filters: {list(extracted_filters.keys())}",
                conjunctions=conjunctions,
                contradiction=contradiction,
            )

        # Step 4: Default to SEARCH for ambiguous queries
        entity_type = self._detect_entity_type(query_lower)
        return QueryClassification(
            query_type=QueryType.SEARCH,
            entity_type=entity_type,
            entity_identifier=None,
            confidence=0.5,
            reasoning="No specific entity or filter detected, falling back to search",
            conjunctions=conjunctions,
        )

    def _normalize_identifier(self, identifier: str, entity_type: str) -> str:
        """
        Normalize entity identifiers to canonical form.

        Examples:
            "ME S 001" → "ME-S-001"
            "GEN001" → "GEN-001"
            "ENG 0008 103" → "ENG-0008-103"
        """
        # Remove all separators first
        clean = re.sub(r'[\s\-\.]+', '', identifier).upper()

        if entity_type == "equipment_code":
            # Handle different equipment code formats
            if clean.startswith('ME') and len(clean) >= 6:
                # MES001 → ME-S-001
                return f"{clean[:2]}-{clean[2]}-{clean[3:]}"
            elif clean.startswith('GEN') and len(clean) >= 6:
                # GEN001 → GEN-001
                return f"GEN-{clean[3:]}"
            elif clean.startswith('HVAC') and len(clean) >= 7:
                return f"HVAC-{clean[4:]}"
            elif clean.startswith('THR') and len(clean) >= 7:
                return f"THR-{clean[3]}-{clean[4:]}"
            elif clean.startswith('WM') and len(clean) >= 5:
                return f"WM-{clean[2:]}"
            elif clean.startswith('HYD') and len(clean) >= 6:
                return f"HYD-{clean[3:]}"
            elif clean.startswith('STP') and len(clean) >= 6:
                return f"STP-{clean[3:]}"
            elif clean.startswith('NAV'):
                if 'RAD' in clean:
                    idx = clean.index('RAD') + 3
                    return f"NAV-RAD-{clean[idx:]}"
                elif 'AP' in clean:
                    idx = clean.index('AP') + 2
                    return f"NAV-AP-{clean[idx:]}"
            elif clean.startswith('FIRE') and len(clean) >= 7:
                return f"FIRE-{clean[4:]}"

        elif entity_type == "part_number":
            # ENG0008103 → ENG-0008-103
            if len(clean) >= 10:
                prefix = clean[:3]
                mid = clean[3:7]
                suffix = clean[7:]
                return f"{prefix}-{mid}-{suffix}"

        elif entity_type == "fault_code":
            # Already in correct format (E047)
            return clean

        elif entity_type == "work_order_number":
            # WO2024001 → WO-2024-001
            if len(clean) >= 9 and clean.startswith('WO'):
                return f"WO-{clean[2:6]}-{clean[6:]}"

        return identifier  # Return as-is if no normalization applies

    def _map_pattern_to_domain(self, pattern_type: str) -> str:
        """Map pattern entity types to domain entity types"""
        mapping = {
            "equipment_code": "equipment",
            "part_number": "part",
            "fault_code": "fault",
            "work_order_number": "work_order",
        }
        return mapping.get(pattern_type, pattern_type)

    def _detect_entity_type(self, query_lower: str) -> Optional[str]:
        """Detect entity type from keyword analysis"""
        for entity_type, keywords in self.entity_type_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return entity_type
        return None


# Singleton instance
_classifier_instance = None

def get_classifier() -> QueryClassifier:
    """Get or create singleton classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = QueryClassifier()
    return _classifier_instance


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    classifier = QueryClassifier()

    test_cases = [
        # LOOKUP queries (should detect entity identifier)
        ("show equipment ME-S-001", QueryType.LOOKUP, "equipment", "ME-S-001"),
        ("equipment details ME S 001", QueryType.LOOKUP, "equipment", "ME-S-001"),
        ("show equipment MES001", QueryType.LOOKUP, "equipment", "ME-S-001"),
        ("diagnose E047", QueryType.LOOKUP, "fault", "E047"),
        ("part ENG-0008-103", QueryType.LOOKUP, "part", "ENG-0008-103"),
        ("generator GEN-001", QueryType.LOOKUP, "equipment", "GEN-001"),

        # LIST queries (should detect filters)
        ("pending work orders", QueryType.LIST, "work_order", None),
        ("show me pending work orders", QueryType.LIST, "work_order", None),
        ("out of stock parts", QueryType.LIST, "part", None),
        ("list all equipment", QueryType.LIST, "equipment", None),
        ("active faults", QueryType.LIST, "fault", None),
        ("high priority work orders", QueryType.LIST, "work_order", None),

        # MUTATE queries
        ("create work order for bilge pump", QueryType.MUTATE, "work_order", None),
        ("update inventory quantity", QueryType.MUTATE, "part", None),

        # SEARCH queries (ambiguous)
        ("main engine overheating", QueryType.SEARCH, "equipment", None),
        ("bilge pump problems", QueryType.SEARCH, "equipment", None),
    ]

    print("=" * 70)
    print("QUERY CLASSIFIER TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected_type, expected_entity, expected_id in test_cases:
        result = classifier.classify(query)

        type_match = result.query_type == expected_type
        entity_match = result.entity_type == expected_entity
        id_match = result.entity_identifier == expected_id

        all_match = type_match and entity_match and id_match

        if all_match:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"\n{status}: '{query}'")
        print(f"  Expected: type={expected_type.value}, entity={expected_entity}, id={expected_id}")
        print(f"  Got:      type={result.query_type.value}, entity={result.entity_type}, id={result.entity_identifier}")
        print(f"  Reasoning: {result.reasoning}")
        if result.filters:
            print(f"  Filters: {result.filters}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.1f}%)")
    print(f"{'=' * 70}")
