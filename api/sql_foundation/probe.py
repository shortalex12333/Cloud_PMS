"""
SQL FOUNDATION — UNIVERSAL PROBE SCHEMA
=======================================
A Probe is the smallest executable query unit.
All searches compile into Probes. No exceptions.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
from .operators import Operator

class VariantType(Enum):
    """Value variant types, tried in priority order."""
    RAW = "raw"              # Original user input
    CANONICAL = "canonical"  # Normalized form (uppercase, stripped)
    NORMALIZED = "normalized" # Domain-specific normalization
    FUZZY = "fuzzy"          # Pattern-wrapped for ILIKE

class Conjunction(Enum):
    """How clauses combine."""
    AND = "AND"
    OR = "OR"

@dataclass
class Variant:
    """A term variant with priority ordering."""
    type: VariantType
    value: Any
    priority: int  # Lower = higher priority, tried first

    @staticmethod
    def from_raw(raw: str) -> List["Variant"]:
        """Generate standard variants from raw input."""
        # Block empty/whitespace-only strings
        if not raw or not raw.strip():
            return []

        raw = raw.strip()

        # FIXED: Don't strip hyphens for canonical - DB has hyphens
        # Instead, uppercase but preserve structure
        variants = [
            Variant(VariantType.RAW, raw, priority=2),
            Variant(VariantType.CANONICAL, raw.upper(), priority=1),  # Keep hyphens!
            Variant(VariantType.NORMALIZED, raw.lower(), priority=3),
            Variant(VariantType.FUZZY, f"%{raw}%", priority=4),
        ]
        return sorted(variants, key=lambda v: v.priority)

@dataclass
class WhereClause:
    """A single WHERE condition."""
    column: str
    operator: Operator
    param_ref: int  # Which parameter ($1, $2, etc.)
    json_key: Optional[str] = None  # For JSONB_PATH_ILIKE

@dataclass
class Probe:
    """
    The universal execution unit.

    Every search compiles to one or more Probes.
    The executor ONLY substitutes values and runs.
    """
    # Identity
    probe_id: str

    # Target
    table: str
    select_cols: List[str]

    # Conditions
    where_clauses: List[WhereClause]
    conjunction: Conjunction = Conjunction.AND

    # Execution context
    wave: int = 0
    limit: int = 50
    order_by: Optional[str] = None

    # Parameters (yacht_id is always $1)
    params: List[Any] = field(default_factory=list)

    # Metadata
    entity_type: Optional[str] = None
    variant_type: Optional[VariantType] = None

    def to_sql(self) -> str:
        """
        Compile probe to parameterized SQL.

        CRITICAL: This produces the SAME SQL structure regardless of table.
        Only the substituted values differ.
        """
        from .operators import SQL_TEMPLATES, CLAUSE_FRAGMENTS

        select_str = ", ".join(self.select_cols)

        # Single clause → use simple template
        if len(self.where_clauses) == 1:
            clause = self.where_clauses[0]
            template = SQL_TEMPLATES[clause.operator]

            sql = template.format(
                table=self.table,
                select_cols=select_str,
                column=clause.column,
                limit=self.limit,
                json_key=f"'{clause.json_key}'" if clause.json_key else None
            )
            return sql.strip()

        # Multiple clauses → build compound
        clause_strs = []
        for i, clause in enumerate(self.where_clauses):
            fragment = CLAUSE_FRAGMENTS[clause.operator]
            clause_str = fragment.format(
                column=clause.column,
                param_num=clause.param_ref,
                json_key=f"'{clause.json_key}'" if clause.json_key else None,
                threshold_param=clause.param_ref + 1 if clause.operator == Operator.TRIGRAM else None,
                param_num_a=clause.param_ref,
                param_num_b=clause.param_ref + 1 if clause.operator == Operator.RANGE else None,
            )
            clause_strs.append(clause_str)

        joined = f" {self.conjunction.value} ".join(clause_strs)

        if self.conjunction == Conjunction.OR:
            sql = f"""
SELECT {select_str}
FROM {self.table}
WHERE yacht_id = $1
  AND ({joined})
LIMIT {self.limit}
"""
        else:
            sql = f"""
SELECT {select_str}
FROM {self.table}
WHERE yacht_id = $1
  AND {joined}
LIMIT {self.limit}
"""

        if self.order_by:
            sql = sql.replace(f"LIMIT {self.limit}", f"ORDER BY {self.order_by}\nLIMIT {self.limit}")

        return sql.strip()


@dataclass
class ProbeResult:
    """Result of executing a probe."""
    probe_id: str
    table: str
    operator: Operator
    rows_returned: int
    execution_time_ms: float
    rows: List[Dict[str, Any]]
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def has_hits(self) -> bool:
        return self.rows_returned > 0


# =============================================================================
# PROBE SHAPES (the three allowed query patterns)
# =============================================================================

def probe_single(
    table: str,
    column: str,
    operator: Operator,
    term: Any,
    yacht_id: str,
    select_cols: List[str],
    entity_type: str,
    variant_type: VariantType,
    limit: int = 50
) -> Probe:
    """
    Shape A: Single-probe (isolated)
    One entity, one column, one table.
    """
    from .operators import OPERATOR_WAVES

    return Probe(
        probe_id=f"{table}.{column}.{operator.value}",
        table=table,
        select_cols=select_cols,
        where_clauses=[
            WhereClause(column=column, operator=operator, param_ref=2)
        ],
        conjunction=Conjunction.AND,
        wave=OPERATOR_WAVES[operator],
        limit=limit,
        params=[yacht_id, term],
        entity_type=entity_type,
        variant_type=variant_type
    )


def probe_or_multicolumn(
    table: str,
    columns: List[str],
    operator: Operator,
    term: Any,
    yacht_id: str,
    select_cols: List[str],
    entity_type: str,
    limit: int = 50
) -> Probe:
    """
    Shape B: OR within a table (multi-column)
    Same entity searched across multiple allowed columns.
    """
    from .operators import OPERATOR_WAVES

    clauses = []
    for i, col in enumerate(columns):
        clauses.append(WhereClause(
            column=col,
            operator=operator,
            param_ref=2  # Same param for all (OR condition)
        ))

    return Probe(
        probe_id=f"{table}.{'|'.join(columns)}.{operator.value}",
        table=table,
        select_cols=select_cols,
        where_clauses=clauses,
        conjunction=Conjunction.OR,
        wave=OPERATOR_WAVES[operator],
        limit=limit,
        params=[yacht_id, term],
        entity_type=entity_type
    )


def probe_and_conjunction(
    table: str,
    column_terms: List[tuple],  # [(column, operator, term), ...]
    yacht_id: str,
    select_cols: List[str],
    limit: int = 50
) -> Probe:
    """
    Shape C: AND across entities (conjunction)
    Multiple entities applied together.

    RULE: Only runs when 2+ strong entities present.
    """
    from .operators import OPERATOR_WAVES

    clauses = []
    params = [yacht_id]
    max_wave = 0

    for i, (col, op, term) in enumerate(column_terms):
        params.append(term)
        clauses.append(WhereClause(
            column=col,
            operator=op,
            param_ref=i + 2  # $2, $3, $4, ...
        ))
        max_wave = max(max_wave, OPERATOR_WAVES[op])

    col_names = [ct[0] for ct in column_terms]

    return Probe(
        probe_id=f"{table}.conjunction.{'+'.join(col_names)}",
        table=table,
        select_cols=select_cols,
        where_clauses=clauses,
        conjunction=Conjunction.AND,
        wave=max_wave,
        limit=limit,
        params=params,
        entity_type="CONJUNCTION"
    )
