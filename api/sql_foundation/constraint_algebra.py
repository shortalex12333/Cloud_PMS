"""
Constraint Algebra
==================

Formal constraint system for query decomposition and satisfaction.

THEORY:
    A query Q is a set of constraints: Q = { C₁, C₂, …, Cₙ }

    Each constraint is a typed tuple:
        C = (variable, operator, value, confidence, scope, hardness)

    Constraint satisfaction returns results where:
        ∀ hard constraints: MUST match
        ∀ soft constraints: SHOULD match (ranking penalty if not)

CONSTRAINT TYPES:
    - HARD: Must be satisfied (filters, security)
    - SOFT: Ranking signal (preferences, fuzzy matches)

OPERATORS:
    - EQ:     variable = value
    - NE:     variable ≠ value
    - IN:     variable ∈ {values}
    - NOT_IN: variable ∉ {values}
    - LIKE:   variable ~ pattern
    - LT/GT:  variable < / > value
    - BETWEEN: value₁ ≤ variable ≤ value₂
    - EXISTS: variable IS NOT NULL
    - SEMANTIC: predicate(variable)  # lifted predicate

ALGEBRA:
    - Intersection: Q₁ ∧ Q₂ (AND constraints)
    - Union: Q₁ ∨ Q₂ (OR constraints - ranking expansion)
    - Negation: ¬C (NOT constraint)
    - Relaxation: weaken(C) → C' with lower confidence

FAILURE MODES:
    - Underconstrained: |Q| < min_constraints for scope
    - Overconstrained: No results satisfy all hard constraints
    - Contradictory: C₁ ∧ C₂ = ⊥ (logical impossibility)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from enum import Enum
from datetime import datetime, date, timedelta


# =============================================================================
# CONSTRAINT OPERATORS
# =============================================================================

class ConstraintOp(str, Enum):
    """Constraint operators"""
    EQ = "="
    NE = "!="
    IN = "IN"
    NOT_IN = "NOT IN"
    LIKE = "LIKE"
    ILIKE = "ILIKE"
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    BETWEEN = "BETWEEN"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT EXISTS"
    SEMANTIC = "SEMANTIC"  # Lifted predicate


class Hardness(str, Enum):
    """Constraint hardness"""
    HARD = "hard"    # Must satisfy
    SOFT = "soft"    # Ranking signal
    SECURITY = "security"  # Cannot be relaxed ever


class ConstraintScope(str, Enum):
    """Constraint scope"""
    GLOBAL = "global"      # Applies to all tables
    TABLE = "table"        # Specific table
    COLUMN = "column"      # Specific column
    RESULT = "result"      # Post-query filter


# =============================================================================
# SEMANTIC PREDICATES (Lifted)
# =============================================================================

class SemanticPredicate(str, Enum):
    """
    Lifted semantic predicates.

    These abstract business logic from SQL implementation.
    Each predicate has a definition that compiles to SQL.
    """
    # Inventory
    OUT_OF_STOCK = "OUT_OF_STOCK"
    LOW_STOCK = "LOW_STOCK"
    IN_STOCK = "IN_STOCK"
    OVERSTOCKED = "OVERSTOCKED"

    # Status
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    # Temporal
    OVERDUE = "OVERDUE"
    DUE_TODAY = "DUE_TODAY"
    DUE_THIS_WEEK = "DUE_THIS_WEEK"
    RECENT = "RECENT"

    # Priority
    CRITICAL = "CRITICAL"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    LOW_PRIORITY = "LOW_PRIORITY"


# Predicate definitions: predicate → SQL condition
# This is the ONLY place predicate semantics are defined
PREDICATE_DEFINITIONS: Dict[SemanticPredicate, Dict] = {
    SemanticPredicate.OUT_OF_STOCK: {
        "tables": ["v_inventory", "pms_parts"],
        "sql": "(qty <= 0 OR qty IS NULL)",
        "variables": ["qty"],
    },
    SemanticPredicate.LOW_STOCK: {
        "tables": ["v_inventory", "pms_parts"],
        "sql": "(qty <= min_qty AND qty > 0)",
        "variables": ["qty", "min_qty"],
    },
    SemanticPredicate.IN_STOCK: {
        "tables": ["v_inventory", "pms_parts"],
        "sql": "(qty > 0)",
        "variables": ["qty"],
    },
    SemanticPredicate.OPEN: {
        "tables": ["pms_work_orders"],
        "sql": "(status NOT IN ('completed', 'cancelled'))",
        "variables": ["status"],
    },
    SemanticPredicate.PENDING: {
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "sql": "(status = 'pending')",
        "variables": ["status"],
    },
    SemanticPredicate.IN_PROGRESS: {
        "tables": ["pms_work_orders"],
        "sql": "(status = 'in_progress')",
        "variables": ["status"],
    },
    SemanticPredicate.COMPLETED: {
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "sql": "(status = 'completed')",
        "variables": ["status"],
    },
    SemanticPredicate.CANCELLED: {
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "sql": "(status = 'cancelled')",
        "variables": ["status"],
    },
    SemanticPredicate.OVERDUE: {
        "tables": ["pms_work_orders"],
        "sql": "(due_date < CURRENT_DATE AND status NOT IN ('completed', 'cancelled'))",
        "variables": ["due_date", "status"],
    },
    SemanticPredicate.DUE_TODAY: {
        "tables": ["pms_work_orders"],
        "sql": "(due_date::date = CURRENT_DATE)",
        "variables": ["due_date"],
    },
    SemanticPredicate.DUE_THIS_WEEK: {
        "tables": ["pms_work_orders"],
        "sql": "(due_date >= date_trunc('week', CURRENT_DATE) AND due_date < date_trunc('week', CURRENT_DATE) + interval '7 days')",
        "variables": ["due_date"],
    },
    SemanticPredicate.RECENT: {
        "tables": ["pms_work_orders", "pms_purchase_orders"],
        "sql": "(created_at >= CURRENT_DATE - interval '7 days')",
        "variables": ["created_at"],
    },
    SemanticPredicate.CRITICAL: {
        "tables": ["pms_work_orders", "pms_faults"],
        "sql": "(priority = 'critical' OR severity = 'critical')",
        "variables": ["priority", "severity"],
    },
    SemanticPredicate.HIGH_PRIORITY: {
        "tables": ["pms_work_orders"],
        "sql": "(priority IN ('high', 'critical'))",
        "variables": ["priority"],
    },
    SemanticPredicate.LOW_PRIORITY: {
        "tables": ["pms_work_orders"],
        "sql": "(priority = 'low')",
        "variables": ["priority"],
    },
}


# Predicate negations: predicate → negated predicate
# Some predicates have natural opposites, others don't
PREDICATE_NEGATIONS: Dict[SemanticPredicate, SemanticPredicate] = {
    SemanticPredicate.OUT_OF_STOCK: SemanticPredicate.IN_STOCK,
    SemanticPredicate.IN_STOCK: SemanticPredicate.OUT_OF_STOCK,
    SemanticPredicate.OPEN: SemanticPredicate.COMPLETED,
    SemanticPredicate.PENDING: SemanticPredicate.COMPLETED,
    SemanticPredicate.COMPLETED: SemanticPredicate.OPEN,
    # Note: Some predicates like OVERDUE, DUE_TODAY don't have clean negations
}


# =============================================================================
# CONSTRAINT DATA STRUCTURE
# =============================================================================

@dataclass
class Constraint:
    """
    A typed constraint over a variable.

    Immutable after creation.
    """
    variable: str                           # Column or semantic variable
    operator: ConstraintOp                  # Comparison operator
    value: Any                              # Value(s) to compare
    confidence: float = 1.0                 # 0.0-1.0 extraction confidence
    scope: ConstraintScope = ConstraintScope.GLOBAL
    hardness: Hardness = Hardness.SOFT
    table_hint: Optional[str] = None        # Preferred table
    source: str = "extracted"               # Where this came from

    # For semantic predicates
    predicate: Optional[SemanticPredicate] = None

    def __post_init__(self):
        # Validate
        if self.operator == ConstraintOp.SEMANTIC and self.predicate is None:
            raise ValueError("SEMANTIC operator requires predicate")
        if self.operator == ConstraintOp.BETWEEN and not isinstance(self.value, tuple):
            raise ValueError("BETWEEN operator requires tuple (low, high)")
        if self.operator in (ConstraintOp.IN, ConstraintOp.NOT_IN) and not isinstance(self.value, (list, set, tuple)):
            raise ValueError("IN/NOT_IN operators require collection")

    def negate(self) -> 'Constraint':
        """Return negated constraint."""
        negated_ops = {
            ConstraintOp.EQ: ConstraintOp.NE,
            ConstraintOp.NE: ConstraintOp.EQ,
            ConstraintOp.IN: ConstraintOp.NOT_IN,
            ConstraintOp.NOT_IN: ConstraintOp.IN,
            ConstraintOp.LT: ConstraintOp.GE,
            ConstraintOp.LE: ConstraintOp.GT,
            ConstraintOp.GT: ConstraintOp.LE,
            ConstraintOp.GE: ConstraintOp.LT,
            ConstraintOp.EXISTS: ConstraintOp.NOT_EXISTS,
            ConstraintOp.NOT_EXISTS: ConstraintOp.EXISTS,
            ConstraintOp.ILIKE: ConstraintOp.ILIKE,  # NOT ILIKE handled in SQL
            ConstraintOp.LIKE: ConstraintOp.LIKE,    # NOT LIKE handled in SQL
        }

        # Semantic predicates have negation defined per-predicate
        if self.operator == ConstraintOp.SEMANTIC and self.predicate:
            negated_predicate = PREDICATE_NEGATIONS.get(self.predicate)
            if negated_predicate:
                return Constraint(
                    variable=self.variable,
                    operator=ConstraintOp.SEMANTIC,
                    value=None,
                    confidence=self.confidence,
                    scope=self.scope,
                    hardness=self.hardness,
                    table_hint=self.table_hint,
                    source=f"negated({self.source})",
                    predicate=negated_predicate,
                )
            else:
                # No defined negation - mark as "NOT predicate" via source
                return Constraint(
                    variable=self.variable,
                    operator=ConstraintOp.SEMANTIC,
                    value=None,
                    confidence=self.confidence,
                    scope=self.scope,
                    hardness=self.hardness,
                    table_hint=self.table_hint,
                    source=f"NOT({self.source})",
                    predicate=self.predicate,  # Keep predicate, mark negated in source
                )

        if self.operator not in negated_ops:
            raise ValueError(f"Cannot negate operator {self.operator}")

        return Constraint(
            variable=self.variable,
            operator=negated_ops[self.operator],
            value=self.value,
            confidence=self.confidence,
            scope=self.scope,
            hardness=self.hardness,
            table_hint=self.table_hint,
            source=f"negated({self.source})"
        )

    def relax(self, factor: float = 0.5) -> 'Constraint':
        """Return relaxed constraint with lower confidence."""
        if self.hardness == Hardness.SECURITY:
            raise ValueError("Cannot relax security constraints")

        return Constraint(
            variable=self.variable,
            operator=self.operator,
            value=self.value,
            confidence=self.confidence * factor,
            scope=self.scope,
            hardness=Hardness.SOFT,  # Relaxed = soft
            table_hint=self.table_hint,
            source=f"relaxed({self.source})"
        )

    def to_dict(self) -> Dict:
        return {
            "variable": self.variable,
            "operator": self.operator.value,
            "value": str(self.value) if not isinstance(self.value, (str, int, float, bool)) else self.value,
            "confidence": self.confidence,
            "hardness": self.hardness.value,
            "scope": self.scope.value,
            "predicate": self.predicate.value if self.predicate else None,
        }


# =============================================================================
# CONSTRAINT SET
# =============================================================================

@dataclass
class ConstraintSet:
    """
    A set of constraints representing a query.

    Q = { C₁, C₂, …, Cₙ }
    """
    constraints: List[Constraint] = field(default_factory=list)
    yacht_id: Optional[str] = None  # Required security constraint

    def __post_init__(self):
        # Always add yacht_id as security constraint if provided
        if self.yacht_id:
            yacht_constraint = Constraint(
                variable="yacht_id",
                operator=ConstraintOp.EQ,
                value=self.yacht_id,
                confidence=1.0,
                scope=ConstraintScope.GLOBAL,
                hardness=Hardness.SECURITY,
                source="security"
            )
            # Ensure it's first
            self.constraints = [yacht_constraint] + [
                c for c in self.constraints if c.variable != "yacht_id"
            ]

    @property
    def hard_constraints(self) -> List[Constraint]:
        """Get all hard/security constraints."""
        return [c for c in self.constraints if c.hardness in (Hardness.HARD, Hardness.SECURITY)]

    @property
    def soft_constraints(self) -> List[Constraint]:
        """Get all soft constraints."""
        return [c for c in self.constraints if c.hardness == Hardness.SOFT]

    @property
    def security_constraints(self) -> List[Constraint]:
        """Get security constraints (cannot be dropped)."""
        return [c for c in self.constraints if c.hardness == Hardness.SECURITY]

    def add(self, constraint: Constraint) -> 'ConstraintSet':
        """Add constraint, return new set."""
        return ConstraintSet(
            constraints=self.constraints + [constraint],
            yacht_id=self.yacht_id
        )

    def intersect(self, other: 'ConstraintSet') -> 'ConstraintSet':
        """AND two constraint sets."""
        # Merge constraints, keeping yacht_id
        combined = self.constraints + [
            c for c in other.constraints
            if c.variable != "yacht_id"  # Don't duplicate yacht_id
        ]
        return ConstraintSet(
            constraints=combined,
            yacht_id=self.yacht_id or other.yacht_id
        )

    def variables(self) -> Set[str]:
        """Get all variables in constraint set."""
        return {c.variable for c in self.constraints}

    def constraints_for_table(self, table: str) -> List[Constraint]:
        """Get constraints applicable to a table."""
        result = []
        for c in self.constraints:
            # Global constraints apply to all tables
            if c.scope == ConstraintScope.GLOBAL:
                result.append(c)
            # Table-specific constraints
            elif c.table_hint == table:
                result.append(c)
            # Semantic predicates check table compatibility
            elif c.predicate:
                defn = PREDICATE_DEFINITIONS.get(c.predicate, {})
                if table in defn.get("tables", []):
                    result.append(c)
        return result

    def to_dict(self) -> Dict:
        return {
            "yacht_id": self.yacht_id,
            "constraint_count": len(self.constraints),
            "hard_count": len(self.hard_constraints),
            "soft_count": len(self.soft_constraints),
            "constraints": [c.to_dict() for c in self.constraints],
        }


# =============================================================================
# CONSTRAINT ANALYSIS (Failure Detection)
# =============================================================================

class ConstraintAnalysisResult(str, Enum):
    """Result of constraint analysis"""
    VALID = "valid"
    UNDERCONSTRAINED = "underconstrained"
    OVERCONSTRAINED = "overconstrained"
    CONTRADICTORY = "contradictory"


@dataclass
class AnalysisReport:
    """Report from constraint analysis."""
    status: ConstraintAnalysisResult
    reason: Optional[str] = None
    contradictions: List[Tuple[Constraint, Constraint]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "contradictions": [
                (c1.to_dict(), c2.to_dict())
                for c1, c2 in self.contradictions
            ],
            "suggestions": self.suggestions,
        }


def analyze_constraints(cs: ConstraintSet) -> AnalysisReport:
    """
    Analyze constraint set for failure modes.

    Detects:
    - Underconstrained: No meaningful constraints
    - Overconstrained: Too many hard constraints
    - Contradictory: Impossible constraint combinations
    """
    # Check for yacht_id (required)
    if not any(c.variable == "yacht_id" for c in cs.constraints):
        return AnalysisReport(
            status=ConstraintAnalysisResult.CONTRADICTORY,
            reason="Missing required yacht_id constraint",
        )

    # Check for underconstrained (only yacht_id, nothing else meaningful)
    non_security = [c for c in cs.constraints if c.hardness != Hardness.SECURITY]
    if len(non_security) == 0:
        return AnalysisReport(
            status=ConstraintAnalysisResult.UNDERCONSTRAINED,
            reason="No search constraints provided",
            suggestions=["Add a search term or filter"],
        )

    # Check for contradictions
    contradictions = find_contradictions(cs)
    if contradictions:
        return AnalysisReport(
            status=ConstraintAnalysisResult.CONTRADICTORY,
            reason="Contradictory constraints detected",
            contradictions=contradictions,
            suggestions=["Remove one of the conflicting constraints"],
        )

    # Check for overconstrained (heuristic: many hard constraints)
    hard = cs.hard_constraints
    if len(hard) > 5:
        return AnalysisReport(
            status=ConstraintAnalysisResult.OVERCONSTRAINED,
            reason=f"Too many hard constraints ({len(hard)})",
            suggestions=["Consider relaxing some constraints to soft"],
        )

    return AnalysisReport(status=ConstraintAnalysisResult.VALID)


def find_contradictions(cs: ConstraintSet) -> List[Tuple[Constraint, Constraint]]:
    """
    Find contradictory constraint pairs.

    Contradiction patterns:
    - Same variable, EQ to different values
    - Same variable, IN and NOT_IN overlap
    - Semantic predicates that conflict (OUT_OF_STOCK and IN_STOCK)
    """
    contradictions = []

    # Group by variable
    by_var: Dict[str, List[Constraint]] = {}
    for c in cs.constraints:
        by_var.setdefault(c.variable, []).append(c)

    # Check each variable
    for var, constraints in by_var.items():
        if len(constraints) < 2:
            continue

        for i, c1 in enumerate(constraints):
            for c2 in constraints[i+1:]:
                if is_contradictory(c1, c2):
                    contradictions.append((c1, c2))

    # Check semantic predicate conflicts
    predicates = [c for c in cs.constraints if c.predicate]
    conflict_pairs = [
        (SemanticPredicate.OUT_OF_STOCK, SemanticPredicate.IN_STOCK),
        (SemanticPredicate.OPEN, SemanticPredicate.COMPLETED),
        (SemanticPredicate.PENDING, SemanticPredicate.COMPLETED),
    ]

    for c1 in predicates:
        for c2 in predicates:
            if c1 is c2:
                continue
            if (c1.predicate, c2.predicate) in conflict_pairs or \
               (c2.predicate, c1.predicate) in conflict_pairs:
                if (c1, c2) not in contradictions and (c2, c1) not in contradictions:
                    contradictions.append((c1, c2))

    return contradictions


def is_contradictory(c1: Constraint, c2: Constraint) -> bool:
    """Check if two constraints on same variable contradict."""
    if c1.variable != c2.variable:
        return False

    # EQ to different values
    if c1.operator == ConstraintOp.EQ and c2.operator == ConstraintOp.EQ:
        return c1.value != c2.value

    # EQ and NE same value
    if c1.operator == ConstraintOp.EQ and c2.operator == ConstraintOp.NE:
        return c1.value == c2.value
    if c1.operator == ConstraintOp.NE and c2.operator == ConstraintOp.EQ:
        return c1.value == c2.value

    # LT/LE and GT/GE that don't overlap
    if c1.operator in (ConstraintOp.LT, ConstraintOp.LE) and \
       c2.operator in (ConstraintOp.GT, ConstraintOp.GE):
        try:
            return c1.value <= c2.value
        except:
            return False

    return False


# =============================================================================
# CONSTRAINT SATISFACTION RATIO
# =============================================================================

def compute_csr(
    result: Dict,
    constraints: ConstraintSet,
    table: str
) -> float:
    """
    Compute Constraint Satisfaction Ratio for a result.

    CSR = matched_constraints / total_constraints

    Used for ranking: higher CSR = better match.
    """
    applicable = constraints.constraints_for_table(table)
    if not applicable:
        return 0.0

    matched = 0
    total = 0

    for c in applicable:
        if c.hardness == Hardness.SECURITY:
            continue  # Don't count security constraints

        total += 1

        # Check if result satisfies constraint
        if satisfies_constraint(result, c):
            matched += 1

    return matched / total if total > 0 else 1.0


def satisfies_constraint(result: Dict, c: Constraint) -> bool:
    """Check if a result satisfies a constraint."""
    if c.variable not in result:
        return False

    value = result[c.variable]

    if c.operator == ConstraintOp.EQ:
        return value == c.value
    elif c.operator == ConstraintOp.NE:
        return value != c.value
    elif c.operator == ConstraintOp.IN:
        return value in c.value
    elif c.operator == ConstraintOp.NOT_IN:
        return value not in c.value
    elif c.operator == ConstraintOp.LIKE or c.operator == ConstraintOp.ILIKE:
        # Pattern match (simplified)
        pattern = c.value.replace('%', '.*').replace('_', '.')
        import re
        flags = re.IGNORECASE if c.operator == ConstraintOp.ILIKE else 0
        return bool(re.search(pattern, str(value), flags))
    elif c.operator == ConstraintOp.LT:
        return value < c.value
    elif c.operator == ConstraintOp.LE:
        return value <= c.value
    elif c.operator == ConstraintOp.GT:
        return value > c.value
    elif c.operator == ConstraintOp.GE:
        return value >= c.value
    elif c.operator == ConstraintOp.EXISTS:
        return value is not None
    elif c.operator == ConstraintOp.NOT_EXISTS:
        return value is None
    elif c.operator == ConstraintOp.BETWEEN:
        low, high = c.value
        return low <= value <= high

    return False


# =============================================================================
# SQL COMPILATION
# =============================================================================

def compile_constraint_to_sql(
    c: Constraint,
    param_counter: int = 0
) -> Tuple[str, Dict, int]:
    """
    Compile a single constraint to SQL.

    Returns: (sql_fragment, params, new_counter)
    """
    params = {}

    # Semantic predicates use predefined SQL
    if c.operator == ConstraintOp.SEMANTIC and c.predicate:
        defn = PREDICATE_DEFINITIONS.get(c.predicate)
        if defn:
            return defn["sql"], {}, param_counter
        else:
            raise ValueError(f"Unknown predicate: {c.predicate}")

    # Standard operators
    var = c.variable
    param_counter += 1
    pname = f"p{param_counter}"

    if c.operator == ConstraintOp.EQ:
        params[pname] = c.value
        return f"{var} = :{pname}", params, param_counter

    elif c.operator == ConstraintOp.NE:
        params[pname] = c.value
        return f"{var} != :{pname}", params, param_counter

    elif c.operator == ConstraintOp.IN:
        # IN clause with multiple params
        placeholders = []
        for i, v in enumerate(c.value):
            p = f"{pname}_{i}"
            params[p] = v
            placeholders.append(f":{p}")
        return f"{var} IN ({', '.join(placeholders)})", params, param_counter

    elif c.operator == ConstraintOp.NOT_IN:
        placeholders = []
        for i, v in enumerate(c.value):
            p = f"{pname}_{i}"
            params[p] = v
            placeholders.append(f":{p}")
        return f"{var} NOT IN ({', '.join(placeholders)})", params, param_counter

    elif c.operator == ConstraintOp.ILIKE:
        params[pname] = c.value
        return f"{var} ILIKE :{pname}", params, param_counter

    elif c.operator == ConstraintOp.LIKE:
        params[pname] = c.value
        return f"{var} LIKE :{pname}", params, param_counter

    elif c.operator == ConstraintOp.LT:
        params[pname] = c.value
        return f"{var} < :{pname}", params, param_counter

    elif c.operator == ConstraintOp.LE:
        params[pname] = c.value
        return f"{var} <= :{pname}", params, param_counter

    elif c.operator == ConstraintOp.GT:
        params[pname] = c.value
        return f"{var} > :{pname}", params, param_counter

    elif c.operator == ConstraintOp.GE:
        params[pname] = c.value
        return f"{var} >= :{pname}", params, param_counter

    elif c.operator == ConstraintOp.BETWEEN:
        low, high = c.value
        p_low = f"{pname}_low"
        p_high = f"{pname}_high"
        params[p_low] = low
        params[p_high] = high
        return f"{var} BETWEEN :{p_low} AND :{p_high}", params, param_counter

    elif c.operator == ConstraintOp.EXISTS:
        return f"{var} IS NOT NULL", {}, param_counter

    elif c.operator == ConstraintOp.NOT_EXISTS:
        return f"{var} IS NULL", {}, param_counter

    raise ValueError(f"Unknown operator: {c.operator}")


def compile_constraint_set_to_sql(
    cs: ConstraintSet,
    table: str
) -> Tuple[str, Dict]:
    """
    Compile constraint set to SQL WHERE clause for a table.

    Returns: (where_clause, params)
    """
    applicable = cs.constraints_for_table(table)
    if not applicable:
        return "", {}

    clauses = []
    all_params = {}
    counter = 0

    for c in applicable:
        sql, params, counter = compile_constraint_to_sql(c, counter)
        clauses.append(f"({sql})")
        all_params.update(params)

    # All constraints AND together
    where = " AND ".join(clauses)
    return where, all_params


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Constraint Algebra - Test Suite")
    print("=" * 60)

    # Build a constraint set
    cs = ConstraintSet(
        yacht_id="test-yacht-001",
        constraints=[
            Constraint(
                variable="name",
                operator=ConstraintOp.ILIKE,
                value="%filter%",
                hardness=Hardness.SOFT,
            ),
            Constraint(
                variable="inventory_status",
                operator=ConstraintOp.SEMANTIC,
                value=None,
                predicate=SemanticPredicate.OUT_OF_STOCK,
                hardness=Hardness.HARD,
            ),
            Constraint(
                variable="location",
                operator=ConstraintOp.ILIKE,
                value="%4%c%",
                hardness=Hardness.SOFT,
            ),
        ]
    )

    print("\nConstraint Set:")
    print(f"  Yacht ID: {cs.yacht_id}")
    print(f"  Total: {len(cs.constraints)}")
    print(f"  Hard: {len(cs.hard_constraints)}")
    print(f"  Soft: {len(cs.soft_constraints)}")

    print("\nConstraints:")
    for c in cs.constraints:
        print(f"  - {c.variable} {c.operator.value} {c.value} [{c.hardness.value}]")

    # Analyze
    report = analyze_constraints(cs)
    print(f"\nAnalysis: {report.status.value}")
    if report.reason:
        print(f"  Reason: {report.reason}")

    # Compile to SQL
    sql, params = compile_constraint_set_to_sql(cs, "pms_parts")
    print(f"\nCompiled SQL (pms_parts):")
    print(f"  WHERE {sql}")
    print(f"  Params: {params}")

    # Test contradiction detection
    print("\n" + "=" * 60)
    print("Contradiction Detection Test")

    contradictory_cs = ConstraintSet(
        yacht_id="test-yacht-001",
        constraints=[
            Constraint(
                variable="qty",
                operator=ConstraintOp.SEMANTIC,
                value=None,
                predicate=SemanticPredicate.OUT_OF_STOCK,
                hardness=Hardness.HARD,
            ),
            Constraint(
                variable="qty",
                operator=ConstraintOp.SEMANTIC,
                value=None,
                predicate=SemanticPredicate.IN_STOCK,
                hardness=Hardness.HARD,
            ),
        ]
    )

    report2 = analyze_constraints(contradictory_cs)
    print(f"Analysis: {report2.status.value}")
    if report2.contradictions:
        print(f"  Contradictions found: {len(report2.contradictions)}")
