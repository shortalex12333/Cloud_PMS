"""
Filter Stacking Grammar
=======================

Algebraic grammar for transforming semantic expressions into SQL predicates.

THEORY:
    A filter expression F is a function: (table, yacht_id) → SQL WHERE clause

    Filters COMPOSE with entities:
        Query = Entities ∧ Filters
        WHERE = entity_clauses AND filter_clauses

    Filters are NOT entity types - they're PREDICATES that constrain results.

FILTER TYPES:
    1. STATUS predicates  - (pending, completed, overdue, open)
    2. QUANTITY predicates - (out of stock, low stock)
    3. TEMPORAL predicates - (due this week, overdue, recent)
    4. LOCATION predicates - (in box X, deck Y)
    5. PRIORITY predicates - (critical, high priority, urgent)

GRAMMAR:
    filter ::= status_filter | quantity_filter | temporal_filter | location_filter | priority_filter
    status_filter ::= "pending" | "completed" | "cancelled" | "open" | "closed" | "in progress"
    quantity_filter ::= "out of stock" | "low stock" | "overstocked"
    temporal_filter ::= "overdue" | "due this week" | "due today" | "recent"
    location_filter ::= "in" LOCATION | "at" LOCATION
    priority_filter ::= "critical" | "urgent" | "high priority" | "low priority"

COMPOSITION:
    "pending work orders for main engine"
    = work_orders.status = 'pending' AND entities_match(main engine)

    "oil filters out of stock"
    = v_inventory.qty <= 0 AND entities_match(oil filter)

ALGEBRAIC PROPERTIES:
    - Filters are idempotent: F ∧ F = F
    - Filters commute: F₁ ∧ F₂ = F₂ ∧ F₁
    - Filters distribute: F ∧ (E₁ ∨ E₂) = (F ∧ E₁) ∨ (F ∧ E₂)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from datetime import datetime, timedelta

from .canonical import canonical

# =============================================================================
# FILTER TYPES
# =============================================================================

class FilterType(str, Enum):
    """Categories of semantic filters"""
    STATUS = "status"
    QUANTITY = "quantity"
    TEMPORAL = "temporal"
    LOCATION = "location"
    PRIORITY = "priority"


# =============================================================================
# FILTER DEFINITIONS
# =============================================================================

@dataclass
class FilterPredicate:
    """A parsed filter that can be applied to a table."""
    filter_type: FilterType
    predicate_name: str  # e.g., "out_of_stock", "pending", "overdue"
    raw_text: str        # Original matched text
    parameters: Dict     # e.g., {"location": "4c"} for location filter

    # SQL generation
    target_tables: List[str]      # Tables this filter applies to
    column: Optional[str]         # Target column
    sql_template: str             # SQL template with placeholders
    sql_params: Dict              # Parameters to bind

    def to_dict(self) -> Dict:
        return {
            "filter_type": self.filter_type.value,
            "predicate": self.predicate_name,
            "raw_text": self.raw_text,
            "target_tables": self.target_tables,
            "column": self.column,
        }


# =============================================================================
# STATUS FILTER PATTERNS
# =============================================================================

STATUS_PATTERNS: Dict[str, Dict] = {
    # Work order statuses
    "pending": {
        "patterns": [r"\bpending\b", r"\bnot started\b", r"\bwaiting\b"],
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "column": "status",
        "sql": "status = :status_val",
        "params": {"status_val": "pending"},
    },
    "in_progress": {
        "patterns": [r"\bin progress\b", r"\bongoing\b", r"\bactive\b"],
        "tables": ["pms_work_orders"],
        "column": "status",
        "sql": "status = :status_val",
        "params": {"status_val": "in_progress"},
    },
    "completed": {
        "patterns": [r"\bcompleted\b", r"\bfinished\b", r"\bdone\b", r"\bclosed\b"],
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "column": "status",
        "sql": "status = :status_val",
        "params": {"status_val": "completed"},
    },
    "cancelled": {
        "patterns": [r"\bcancelled\b", r"\bcanceled\b"],
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "column": "status",
        "sql": "status = :status_val",
        "params": {"status_val": "cancelled"},
    },
    "open": {
        "patterns": [r"\bopen\b(?:\s+(?:work\s*orders?|tickets?|issues?))?"],
        "tables": ["pms_work_orders"],
        "column": "status",
        "sql": "status NOT IN ('completed', 'cancelled')",
        "params": {},
    },
}


# =============================================================================
# QUANTITY FILTER PATTERNS
# =============================================================================

QUANTITY_PATTERNS: Dict[str, Dict] = {
    "out_of_stock": {
        "patterns": [
            r"\bout of stock\b",
            r"\bno stock\b",
            r"\bzero stock\b",
            r"\bstockout\b",
            r"\bnone left\b",
            r"\bnone available\b",
        ],
        "tables": ["v_inventory", "pms_parts"],
        "column": "qty",
        "sql": "qty <= 0 OR qty IS NULL",
        "params": {},
    },
    "low_stock": {
        "patterns": [
            r"\blow stock\b",
            r"\blow inventory\b",
            r"\bneeds? reorder\b",
            r"\breorder\b",
            r"\bbelow minimum\b",
        ],
        "tables": ["v_inventory", "pms_parts"],
        "column": "qty",
        "sql": "qty <= min_qty",  # Assumes min_qty column exists
        "params": {},
    },
    "in_stock": {
        "patterns": [r"\bin stock\b", r"\bavailable\b(?:\s+stock)?"],
        "tables": ["v_inventory", "pms_parts"],
        "column": "qty",
        "sql": "qty > 0",
        "params": {},
    },
}


# =============================================================================
# TEMPORAL FILTER PATTERNS
# =============================================================================

TEMPORAL_PATTERNS: Dict[str, Dict] = {
    "overdue": {
        "patterns": [r"\boverdue\b", r"\bpast due\b", r"\blate\b", r"\bmissed\b"],
        "tables": ["pms_work_orders"],
        "column": "due_date",
        "sql": "due_date < :now",
        "params": {"now": datetime.now()},  # Will be updated at parse time
    },
    "due_today": {
        "patterns": [r"\bdue today\b", r"\btoday'?s?\b"],
        "tables": ["pms_work_orders"],
        "column": "due_date",
        "sql": "due_date::date = :today",
        "params": {"today": datetime.now().date()},
    },
    "due_this_week": {
        "patterns": [
            r"\bdue this week\b",
            r"\bthis week\b",
            r"\bcoming week\b",
        ],
        "tables": ["pms_work_orders"],
        "column": "due_date",
        "sql": "due_date BETWEEN :week_start AND :week_end",
        "params": {},  # Computed at parse time
    },
    "recent": {
        "patterns": [r"\brecent\b", r"\blast (?:7|seven) days\b", r"\bpast week\b"],
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "column": "created_at",
        "sql": "created_at >= :recent_cutoff",
        "params": {},  # Computed at parse time
    },
}


# =============================================================================
# PRIORITY FILTER PATTERNS
# =============================================================================

PRIORITY_PATTERNS: Dict[str, Dict] = {
    "critical": {
        "patterns": [r"\bcritical\b", r"\bemergency\b"],
        "tables": ["pms_work_orders", "pms_faults"],
        "column": "priority",  # or "severity" for faults
        "sql": "priority = :priority_val OR severity = :severity_val",
        "params": {"priority_val": "critical", "severity_val": "critical"},
    },
    "high_priority": {
        "patterns": [r"\bhigh priority\b", r"\burgent\b", r"\bhigh\b"],
        "tables": ["pms_work_orders"],
        "column": "priority",
        "sql": "priority IN ('high', 'critical')",
        "params": {},
    },
    "low_priority": {
        "patterns": [r"\blow priority\b", r"\bnon-?urgent\b"],
        "tables": ["pms_work_orders"],
        "column": "priority",
        "sql": "priority = :priority_val",
        "params": {"priority_val": "low"},
    },
}


# =============================================================================
# LOCATION FILTER PATTERNS
# =============================================================================

# Location is special - it extracts a parameter from the text

LOCATION_PREFIXES = [
    r"\bin\s+",           # "in box 4a"
    r"\bat\s+",           # "at deck 2"
    r"\bin\s+the\s+",     # "in the engine room"
    r"\bstored\s+in\s+",  # "stored in 4c"
    r"\blocated\s+(?:in|at)\s+",  # "located in box 3"
    r"\bfrom\s+",         # "from deck 1"
]

LOCATION_SUFFIXES = [
    r"(?:box|locker|cabinet|bin)\s*\w+",  # "box 4a", "locker 3"
    r"deck\s*\d+",                         # "deck 2"
    r"engine\s*room",                      # "engine room"
    r"bridge",
    r"galley",
    r"lazarette",
    r"\d+[a-z]",                           # "4a", "3c"
    r"[a-z]\d+",                           # "A3", "B2"
]


# =============================================================================
# FILTER PARSER
# =============================================================================

class FilterGrammar:
    """
    Parser for filter expressions.

    Extracts semantic filters from query text and generates SQL predicates.
    """

    def __init__(self):
        # Compile all patterns
        self._status_patterns = self._compile_patterns(STATUS_PATTERNS, FilterType.STATUS)
        self._quantity_patterns = self._compile_patterns(QUANTITY_PATTERNS, FilterType.QUANTITY)
        self._temporal_patterns = self._compile_patterns(TEMPORAL_PATTERNS, FilterType.TEMPORAL)
        self._priority_patterns = self._compile_patterns(PRIORITY_PATTERNS, FilterType.PRIORITY)
        self._location_pattern = self._compile_location_pattern()

    def _compile_patterns(
        self,
        pattern_dict: Dict[str, Dict],
        filter_type: FilterType
    ) -> List[Tuple[re.Pattern, str, Dict]]:
        """Compile regex patterns for a filter category."""
        compiled = []
        for name, config in pattern_dict.items():
            for pattern in config["patterns"]:
                compiled.append((
                    re.compile(pattern, re.IGNORECASE),
                    name,
                    {
                        "filter_type": filter_type,
                        "tables": config["tables"],
                        "column": config["column"],
                        "sql": config["sql"],
                        "params": config.get("params", {}),
                    }
                ))
        return compiled

    def _compile_location_pattern(self) -> re.Pattern:
        """Compile location extraction pattern."""
        prefix_group = f"(?:{'|'.join(LOCATION_PREFIXES)})"
        suffix_group = f"(?:{'|'.join(LOCATION_SUFFIXES)})"
        return re.compile(
            f"{prefix_group}({suffix_group})",
            re.IGNORECASE
        )

    def parse(self, query: str) -> List[FilterPredicate]:
        """
        Parse query text and extract all filter predicates.

        Args:
            query: Natural language query

        Returns:
            List of FilterPredicate objects
        """
        filters = []
        query_lower = query.lower()

        # Parse each filter type
        filters.extend(self._parse_category(query_lower, self._status_patterns))
        filters.extend(self._parse_category(query_lower, self._quantity_patterns))
        filters.extend(self._parse_temporal(query_lower))
        filters.extend(self._parse_category(query_lower, self._priority_patterns))
        filters.extend(self._parse_location(query))

        return filters

    def _parse_category(
        self,
        query: str,
        patterns: List[Tuple[re.Pattern, str, Dict]]
    ) -> List[FilterPredicate]:
        """Parse a category of filters."""
        filters = []
        seen = set()  # Dedupe by predicate name

        for pattern, name, config in patterns:
            if name in seen:
                continue

            match = pattern.search(query)
            if match:
                seen.add(name)
                filters.append(FilterPredicate(
                    filter_type=config["filter_type"],
                    predicate_name=name,
                    raw_text=match.group(0),
                    parameters={},
                    target_tables=config["tables"],
                    column=config["column"],
                    sql_template=config["sql"],
                    sql_params=dict(config["params"]),
                ))

        return filters

    def _parse_temporal(self, query: str) -> List[FilterPredicate]:
        """Parse temporal filters with computed date parameters."""
        filters = []
        seen = set()  # Dedupe by predicate name
        now = datetime.now()

        for pattern, name, config in self._temporal_patterns:
            if name in seen:
                continue
            match = pattern.search(query)
            if match:
                # Compute temporal parameters
                params = dict(config["params"])

                if name == "overdue":
                    params["now"] = now
                elif name == "due_today":
                    params["today"] = now.date()
                elif name == "due_this_week":
                    # Start of week (Monday) to end of week (Sunday)
                    days_since_monday = now.weekday()
                    week_start = now.date() - timedelta(days=days_since_monday)
                    week_end = week_start + timedelta(days=6)
                    params["week_start"] = week_start
                    params["week_end"] = week_end
                elif name == "recent":
                    params["recent_cutoff"] = now - timedelta(days=7)

                filters.append(FilterPredicate(
                    filter_type=config["filter_type"],
                    predicate_name=name,
                    raw_text=match.group(0),
                    parameters=params,
                    target_tables=config["tables"],
                    column=config["column"],
                    sql_template=config["sql"],
                    sql_params=params,
                ))

        return filters

    def _parse_location(self, query: str) -> List[FilterPredicate]:
        """Parse location filters with canonical normalization."""
        filters = []

        match = self._location_pattern.search(query)
        if match:
            location_value = match.group(1)

            # Canonicalize the location (4 c → 4c, box-4a → box4a)
            canonical_location = canonical(location_value, "LOCATION")

            # Generate ILIKE pattern for flexible matching
            # "4c" → "%4%c%" to match "4c", "4-c", "4 c", etc.
            ilike_pattern = self._location_to_ilike(canonical_location)

            filters.append(FilterPredicate(
                filter_type=FilterType.LOCATION,
                predicate_name="location",
                raw_text=match.group(0),
                parameters={"location": canonical_location},
                target_tables=["pms_equipment", "pms_parts", "v_inventory"],
                column="location",
                sql_template="location ILIKE :location_pattern",
                sql_params={"location_pattern": ilike_pattern},
            ))

        return filters

    def _location_to_ilike(self, canonical_loc: str) -> str:
        """
        Generate ILIKE pattern for location matching.

        "4c" → "%4%c%" to match variants
        "box4a" → "%box%4%a%"
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


# =============================================================================
# FILTER COMPOSER
# =============================================================================

def compose_filters_sql(
    filters: List[FilterPredicate],
    table: str,
    yacht_id: str,
    param_prefix: str = "f"
) -> Tuple[str, Dict]:
    """
    Compose filter predicates into SQL WHERE clause for a specific table.

    Args:
        filters: List of parsed filter predicates
        table: Target table name
        yacht_id: Required yacht scope
        param_prefix: Prefix for parameter names (for uniqueness)

    Returns:
        (where_clause, params) tuple
    """
    clauses = []
    params = {"yacht_id": yacht_id}
    param_counter = 0

    for flt in filters:
        # Only apply filter if it targets this table
        if table not in flt.target_tables:
            continue

        # Build parameterized clause
        sql = flt.sql_template

        # Replace parameter placeholders with unique names
        for orig_param, value in flt.sql_params.items():
            param_counter += 1
            new_param = f"{param_prefix}{param_counter}"
            sql = sql.replace(f":{orig_param}", f":{new_param}")
            params[new_param] = value

        clauses.append(f"({sql})")

    if not clauses:
        return "", params

    # All filters AND together
    where_sql = " AND ".join(clauses)
    return where_sql, params


# =============================================================================
# STRIP FILTER TEXT
# =============================================================================

def strip_filters_from_query(query: str, filters: List[FilterPredicate]) -> str:
    """
    Remove filter expressions from query, leaving entity terms.

    "pending work orders for main engine"
    → "work orders for main engine" (after removing "pending")

    This allows entity extraction to focus on entity terms only.
    """
    result = query

    for flt in filters:
        # Remove the matched filter text
        result = result.replace(flt.raw_text, " ")

    # Clean up whitespace
    result = re.sub(r'\s+', ' ', result).strip()

    return result


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    parser = FilterGrammar()

    test_queries = [
        "pending work orders for main engine",
        "parts out of stock",
        "oil filters in box 4a",
        "overdue maintenance for generator",
        "critical faults this week",
        "low stock items needing reorder",
        "completed work orders from deck 2",
        "high priority tasks due today",
    ]

    print("Filter Grammar - Test Suite")
    print("=" * 60)

    for query in test_queries:
        filters = parser.parse(query)
        stripped = strip_filters_from_query(query, filters)

        print(f"\nQuery: {query!r}")
        print(f"Stripped: {stripped!r}")
        print(f"Filters ({len(filters)}):")

        for f in filters:
            print(f"  - {f.filter_type.value}: {f.predicate_name}")
            print(f"    Tables: {f.target_tables}")
            print(f"    SQL: {f.sql_template}")
            if f.parameters:
                print(f"    Params: {f.parameters}")
