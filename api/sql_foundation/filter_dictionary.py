"""
Filter Dictionary
=================

Deterministic filter extraction with typed constraint outputs.

NOT regex soup. Each filter maps to:
1. Recognition patterns (surface forms)
2. Typed Constraint output
3. Table compatibility
4. Semantic predicate (lifted business logic)

THEORY:
    A filter F is a function: query_text → Constraint

    Filter application is DETERMINISTIC:
        F("out of stock") → Constraint(inventory_status, SEMANTIC, OUT_OF_STOCK)
        F("pending") → Constraint(status, SEMANTIC, PENDING)
        F("in box 4a") → Constraint(location, ILIKE, "%box%4%a%")

    Filters compose via constraint intersection (AND).

FILTER CATEGORIES:
    1. STATUS filters - (pending, completed, overdue, open, closed)
    2. QUANTITY filters - (out of stock, low stock, in stock)
    3. TEMPORAL filters - (overdue, due today, due this week, recent)
    4. PRIORITY filters - (critical, urgent, high, low)
    5. LOCATION filters - (in box X, at deck Y, engine room)
    6. NEGATIVE filters - (not X, excluding Y, without Z)

CLOSED VOCABULARY:
    Each filter has an EXHAUSTIVE list of surface forms.
    If not in list, it's not a filter.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Pattern

from .constraint_algebra import (
    Constraint, ConstraintOp, Hardness, ConstraintScope,
    SemanticPredicate
)
from .canonical import canonical


# =============================================================================
# FILTER DEFINITION
# =============================================================================

@dataclass
class FilterDefinition:
    """
    Definition of a single filter.

    Immutable specification of how to recognize and transform a filter.
    """
    name: str                              # Canonical filter name
    patterns: List[str]                    # Recognition patterns (regex)
    predicate: Optional[SemanticPredicate] # Lifted predicate (if semantic)
    variable: str                          # Target variable/column
    operator: ConstraintOp                 # Constraint operator
    value: Optional[any]                   # Constraint value (if not semantic)
    hardness: Hardness = Hardness.HARD     # Constraint hardness
    tables: List[str] = field(default_factory=list)  # Compatible tables
    extracts_parameter: bool = False       # Whether pattern extracts a value


# =============================================================================
# STATUS FILTERS
# =============================================================================

STATUS_FILTERS: List[FilterDefinition] = [
    FilterDefinition(
        name="pending",
        patterns=[
            r"\bpending\b",
            r"\bnot started\b",
            r"\bwaiting\b",
            r"\bqueued\b",
        ],
        predicate=SemanticPredicate.PENDING,
        variable="status",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders", "pms_purchase_orders"],
    ),
    FilterDefinition(
        name="in_progress",
        patterns=[
            r"\bin progress\b",
            r"\bin-progress\b",
            r"\bongoing\b",
            r"\bactive\b",
            r"\bstarted\b",
        ],
        predicate=SemanticPredicate.IN_PROGRESS,
        variable="status",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
    FilterDefinition(
        name="completed",
        patterns=[
            r"\bcompleted?\b",
            r"\bfinished\b",
            r"\bdone\b",
            r"\bclosed\b",
        ],
        predicate=SemanticPredicate.COMPLETED,
        variable="status",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders", "pms_purchase_orders"],
    ),
    FilterDefinition(
        name="cancelled",
        patterns=[
            r"\bcancell?ed\b",
            r"\baborted\b",
        ],
        predicate=SemanticPredicate.CANCELLED,
        variable="status",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders", "pms_purchase_orders"],
    ),
    FilterDefinition(
        name="open",
        patterns=[
            r"\bopen\b(?:\s+(?:work\s*orders?|tickets?|tasks?|jobs?))?",
            r"\bunresolved\b",
        ],
        predicate=SemanticPredicate.OPEN,
        variable="status",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
]


# =============================================================================
# QUANTITY FILTERS
# =============================================================================

QUANTITY_FILTERS: List[FilterDefinition] = [
    FilterDefinition(
        name="out_of_stock",
        patterns=[
            r"\bout of stock\b",
            r"\boos\b",
            r"\bno stock\b",
            r"\bzero stock\b",
            r"\bstockout\b",
            r"\bnone left\b",
            r"\bnone available\b",
            r"\bnot available\b",
            r"\bunavailable\b",
        ],
        predicate=SemanticPredicate.OUT_OF_STOCK,
        variable="qty",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["v_inventory", "pms_parts"],
    ),
    FilterDefinition(
        name="low_stock",
        patterns=[
            r"\blow stock\b",
            r"\blow inventory\b",
            r"\bneeds? reorder\b",
            r"\breorder\b",
            r"\bbelow minimum\b",
            r"\bbelow min\b",
            r"\brunning low\b",
        ],
        predicate=SemanticPredicate.LOW_STOCK,
        variable="qty",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["v_inventory", "pms_parts"],
    ),
    FilterDefinition(
        name="in_stock",
        patterns=[
            r"\bin stock\b",
            r"\bavailable\b(?:\s+(?:stock|inventory))?",
            r"\bhave stock\b",
            r"\bhas stock\b",
        ],
        predicate=SemanticPredicate.IN_STOCK,
        variable="qty",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["v_inventory", "pms_parts"],
    ),
]


# =============================================================================
# TEMPORAL FILTERS
# =============================================================================

TEMPORAL_FILTERS: List[FilterDefinition] = [
    FilterDefinition(
        name="overdue",
        patterns=[
            r"\boverdue\b",
            r"\bpast due\b",
            r"\blate\b",
            r"\bmissed\b",
            r"\bexpired\b",
        ],
        predicate=SemanticPredicate.OVERDUE,
        variable="due_date",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
    FilterDefinition(
        name="due_today",
        patterns=[
            r"\bdue today\b",
            r"\btoday'?s?\b(?:\s+(?:work|tasks?|jobs?))?",
        ],
        predicate=SemanticPredicate.DUE_TODAY,
        variable="due_date",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
    FilterDefinition(
        name="due_this_week",
        patterns=[
            r"\bdue this week\b",
            r"\bthis week\b(?:'?s?\s+(?:work|tasks?|jobs?))?",
            r"\bcoming week\b",
            r"\bnext 7 days\b",
        ],
        predicate=SemanticPredicate.DUE_THIS_WEEK,
        variable="due_date",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
    FilterDefinition(
        name="recent",
        patterns=[
            r"\brecent\b",
            r"\blast (?:7|seven) days\b",
            r"\bpast week\b",
            r"\bthis week\b",
        ],
        predicate=SemanticPredicate.RECENT,
        variable="created_at",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders", "pms_purchase_orders"],
    ),
]


# =============================================================================
# PRIORITY FILTERS
# =============================================================================

PRIORITY_FILTERS: List[FilterDefinition] = [
    FilterDefinition(
        name="critical",
        patterns=[
            r"\bcritical\b",
            r"\bemergency\b",
            r"\bcritical priority\b",
        ],
        predicate=SemanticPredicate.CRITICAL,
        variable="priority",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders", "pms_faults"],
    ),
    FilterDefinition(
        name="high_priority",
        patterns=[
            r"\bhigh priority\b",
            r"\burgent\b",
            r"\bhigh\b(?:\s+priority)?",
            r"\bimportant\b",
        ],
        predicate=SemanticPredicate.HIGH_PRIORITY,
        variable="priority",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
    FilterDefinition(
        name="low_priority",
        patterns=[
            r"\blow priority\b",
            r"\bnon-?urgent\b",
            r"\blow\b(?:\s+priority)?",
            r"\bminor\b",
        ],
        predicate=SemanticPredicate.LOW_PRIORITY,
        variable="priority",
        operator=ConstraintOp.SEMANTIC,
        value=None,
        tables=["pms_work_orders"],
    ),
]


# =============================================================================
# LOCATION FILTER (parameterized)
# =============================================================================

# Location prefixes that introduce a location phrase
LOCATION_PREFIXES = [
    r"in\s+",
    r"at\s+",
    r"in\s+the\s+",
    r"stored\s+in\s+",
    r"stored\s+at\s+",
    r"located\s+(?:in|at)\s+",
    r"from\s+",
]

# Location value patterns
LOCATION_VALUES = [
    r"(?:box|locker|cabinet|bin|drawer)\s*[\w\-]+",  # box 4a, locker-3
    r"deck\s*\d+",                                    # deck 2
    r"engine\s*room",
    r"bridge",
    r"galley",
    r"lazarette",
    r"fore\s*peak",
    r"aft\s*peak",
    r"crew\s*quarters",
    r"\d+[a-zA-Z]",                                   # 4a, 3C
    r"[a-zA-Z]\d+",                                   # A3, B2
]

# Build location pattern
_loc_prefix = f"(?:{'|'.join(LOCATION_PREFIXES)})"
_loc_value = f"(?:{'|'.join(LOCATION_VALUES)})"
LOCATION_PATTERN = re.compile(
    f"{_loc_prefix}({_loc_value})",
    re.IGNORECASE
)


# =============================================================================
# NEGATIVE FILTER PREFIXES
# =============================================================================

NEGATIVE_PREFIXES = [
    r"not\s+",
    r"no\s+",
    r"without\s+",
    r"excluding\s+",
    r"except\s+",
    r"other than\s+",
]

NEGATIVE_PATTERN = re.compile(
    f"({'|'.join(NEGATIVE_PREFIXES)})",
    re.IGNORECASE
)


# =============================================================================
# FILTER EXTRACTOR
# =============================================================================

@dataclass
class ExtractedFilter:
    """Result of filter extraction."""
    definition: FilterDefinition
    matched_text: str
    constraint: Constraint
    is_negated: bool = False


class FilterDictionary:
    """
    Deterministic filter extractor.

    Extracts typed constraints from query text.
    """

    def __init__(self):
        # Compile all filter patterns
        self._filters: List[Tuple[Pattern, FilterDefinition]] = []

        all_filters = (
            STATUS_FILTERS +
            QUANTITY_FILTERS +
            TEMPORAL_FILTERS +
            PRIORITY_FILTERS
        )

        for fdef in all_filters:
            for pattern_str in fdef.patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                self._filters.append((pattern, fdef))

        # Sort by pattern length (longest first for greedy matching)
        self._filters.sort(key=lambda x: len(x[0].pattern), reverse=True)

    def extract(self, query: str) -> List[ExtractedFilter]:
        """
        Extract all filters from query text.

        Returns list of ExtractedFilter with typed constraints.
        """
        results = []
        query_lower = query.lower()
        matched_names = set()  # Dedupe by filter name

        # Check for negation context
        negation_match = NEGATIVE_PATTERN.search(query_lower)
        negation_end = negation_match.end() if negation_match else -1

        # Extract standard filters
        for pattern, fdef in self._filters:
            if fdef.name in matched_names:
                continue

            match = pattern.search(query_lower)
            if match:
                matched_names.add(fdef.name)

                # Check if this match is negated
                is_negated = match.start() <= negation_end

                # Build constraint
                constraint = self._build_constraint(fdef, match.group(0))
                if is_negated:
                    constraint = constraint.negate()

                results.append(ExtractedFilter(
                    definition=fdef,
                    matched_text=match.group(0),
                    constraint=constraint,
                    is_negated=is_negated,
                ))

        # Extract location filter (parameterized)
        loc_match = LOCATION_PATTERN.search(query)
        if loc_match:
            loc_filter = self._extract_location(loc_match)
            if loc_filter:
                results.append(loc_filter)

        return results

    def _build_constraint(
        self,
        fdef: FilterDefinition,
        matched_text: str
    ) -> Constraint:
        """Build Constraint from FilterDefinition."""
        return Constraint(
            variable=fdef.variable,
            operator=fdef.operator,
            value=fdef.value,
            confidence=1.0,  # Dictionary match = high confidence
            scope=ConstraintScope.GLOBAL,
            hardness=fdef.hardness,
            table_hint=fdef.tables[0] if fdef.tables else None,
            source=f"filter:{fdef.name}",
            predicate=fdef.predicate,
        )

    def _extract_location(self, match: re.Match) -> Optional[ExtractedFilter]:
        """Extract location filter with canonicalization."""
        location_value = match.group(1)

        # Canonicalize location (4 c → 4c, box-4a → box4a)
        canonical_loc = canonical(location_value, "LOCATION")

        # Build ILIKE pattern for flexible matching
        ilike_pattern = self._location_to_ilike(canonical_loc)

        constraint = Constraint(
            variable="location",
            operator=ConstraintOp.ILIKE,
            value=ilike_pattern,
            confidence=0.95,  # Location patterns have slight ambiguity
            scope=ConstraintScope.GLOBAL,
            hardness=Hardness.SOFT,
            source=f"filter:location({canonical_loc})",
        )

        # Create a pseudo-definition for location
        loc_def = FilterDefinition(
            name="location",
            patterns=[],
            predicate=None,
            variable="location",
            operator=ConstraintOp.ILIKE,
            value=ilike_pattern,
            tables=["pms_equipment", "pms_parts", "v_inventory"],
            extracts_parameter=True,
        )

        return ExtractedFilter(
            definition=loc_def,
            matched_text=match.group(0),
            constraint=constraint,
        )

    def _location_to_ilike(self, canonical_loc: str) -> str:
        """
        Generate ILIKE pattern for location matching.

        "4c" → "%4%c%" to match variants
        """
        pattern_chars = []
        prev_type = None

        for char in canonical_loc:
            curr_type = 'digit' if char.isdigit() else 'alpha'

            # Add % at type transitions
            if prev_type and curr_type != prev_type:
                pattern_chars.append('%')

            pattern_chars.append(char)
            prev_type = curr_type

        return '%' + ''.join(pattern_chars) + '%'

    def strip_filters(self, query: str, extracted: List[ExtractedFilter]) -> str:
        """
        Remove filter expressions from query, leaving entity terms.

        "pending work orders for main engine"
        → "work orders for main engine"
        """
        result = query

        for ef in extracted:
            result = result.replace(ef.matched_text, " ")

        # Clean up whitespace
        result = re.sub(r'\s+', ' ', result).strip()

        return result


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Filter Dictionary - Test Suite")
    print("=" * 60)

    fd = FilterDictionary()

    test_queries = [
        "pending work orders for main engine",
        "parts out of stock",
        "oil filters in box 4a",
        "overdue maintenance for generator",
        "critical faults this week",
        "low stock items needing reorder",
        "completed work orders from deck 2",
        "high priority tasks due today",
        "not pending work orders",  # Negated
        "inventory excluding box 2d",  # Negated
        "inv oos",  # Shorthand
    ]

    for query in test_queries:
        filters = fd.extract(query)
        stripped = fd.strip_filters(query, filters)

        print(f"\nQuery: {query!r}")
        print(f"Stripped: {stripped!r}")
        print(f"Filters ({len(filters)}):")

        for ef in filters:
            neg = "[NEGATED] " if ef.is_negated else ""
            print(f"  - {neg}{ef.definition.name}: {ef.matched_text!r}")
            print(f"    Constraint: {ef.constraint.variable} {ef.constraint.operator.value}")
            if ef.constraint.predicate:
                print(f"    Predicate: {ef.constraint.predicate.value}")
