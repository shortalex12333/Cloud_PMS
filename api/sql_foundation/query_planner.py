"""
QUERY PLANNER: The "VLOOKUP" Layer
==================================
Takes incoming entities and constructs the execution plan.

Flow:
1. INCOMING: entities from extraction
2. EXPAND: generate variants (canonical, original, fuzzy)
3. MATCH: lookup table/column capabilities
4. RANK: compute bias scores
5. PLAN: determine conjunction (OR variants, AND entities)
6. CONSTRUCT: build parameterized SQL
7. SCOPE: enforce yacht_id + user permissions

This is the PREPARE step before SQL execution.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .column_config import TABLES, get_columns_for_entity, ColumnCapability
from .operators import Operator


# =============================================================================
# STEP 1: INCOMING - What extraction gives us
# =============================================================================

@dataclass
class IncomingEntity:
    """Raw entity from extraction."""
    type: str           # EQUIPMENT_NAME, PART_NUMBER, etc.
    value: str          # "Generator 1", "ENG-0008-103"
    confidence: float = 1.0
    source: str = "extraction"  # extraction, regex, user_input


@dataclass
class IncomingQuery:
    """Complete incoming query."""
    entities: List[IncomingEntity]
    yacht_id: str
    user_id: Optional[str] = None
    user_role: str = "crew"
    intent: Optional[str] = None


# =============================================================================
# STEP 2: EXPAND - Generate variants for each entity
# =============================================================================

@dataclass
class ExpandedVariant:
    """A single variant of an entity value."""
    form: str           # canonical, original, fuzzy
    value: str          # The actual value
    operator: Operator  # Which operator to use
    priority: int       # Lower = try first


def expand_variants(entity: IncomingEntity) -> List[ExpandedVariant]:
    """
    Generate search variants from entity value.

    canonical: UPPERCASE, exact match (EXACT operator)
    original: as-typed, pattern match (ILIKE operator)
    fuzzy: %wrapped%, broad match (ILIKE operator)
    """
    raw = entity.value.strip()
    if not raw:
        return []

    variants = [
        ExpandedVariant(
            form="canonical",
            value=raw.upper(),
            operator=Operator.EXACT,
            priority=1
        ),
        ExpandedVariant(
            form="original",
            value=raw,
            operator=Operator.ILIKE,
            priority=2
        ),
        ExpandedVariant(
            form="fuzzy",
            value=f"%{raw}%",
            operator=Operator.ILIKE,
            priority=3
        ),
    ]

    return variants


# =============================================================================
# STEP 3: MATCH - Lookup table/column capabilities
# =============================================================================

@dataclass
class ColumnMatch:
    """A column that can handle this entity."""
    table: str
    column: str
    operators: List[Operator]
    isolated_ok: bool
    conjunction_only: bool
    datatype: str


def match_entity_to_columns(entity: IncomingEntity) -> List[ColumnMatch]:
    """Find all columns that support this entity type."""
    matches = []

    for table_name, table_cfg in TABLES.items():
        for col_name, col_cfg in table_cfg.columns.items():
            if entity.type in col_cfg.entity_types:
                matches.append(ColumnMatch(
                    table=table_name,
                    column=col_name,
                    operators=col_cfg.operators,
                    isolated_ok=col_cfg.isolated_ok,
                    conjunction_only=col_cfg.conjunction_only,
                    datatype=col_cfg.datatype
                ))

    return matches


# =============================================================================
# STEP 4: RANK - Compute bias scores (from bbws.py)
# =============================================================================

# Primary tables for entity types
ENTITY_PRIMARY_TABLES = {
    "PART_NUMBER": ["pms_parts"],
    "PART_NAME": ["pms_parts"],
    "EQUIPMENT_NAME": ["pms_equipment", "graph_nodes"],
    "EQUIPMENT_CODE": ["pms_equipment"],
    "FAULT_CODE": ["pms_faults", "search_fault_code_catalog"],
    "SYMPTOM": ["symptom_aliases", "pms_faults"],
    "SUPPLIER_NAME": ["pms_suppliers"],
    "MANUFACTURER": ["pms_parts", "pms_suppliers"],
}


def compute_column_bias(match: ColumnMatch, entity: IncomingEntity) -> float:
    """Compute bias score for a column match."""
    bias = 0.0

    # Primary table bonus
    if match.table in ENTITY_PRIMARY_TABLES.get(entity.type, []):
        bias += 2.0

    # EXACT operator bonus
    if Operator.EXACT in match.operators:
        bias += 1.0

    # Isolated OK bonus (can query alone)
    if match.isolated_ok:
        bias += 0.5

    # Conjunction penalty (needs another entity)
    if match.conjunction_only:
        bias -= 0.5

    # Confidence weighting
    bias *= entity.confidence

    return round(bias, 2)


# =============================================================================
# STEP 5: PLAN - Determine conjunction logic
# =============================================================================

class ConjunctionType(Enum):
    """How to combine conditions."""
    OR_VARIANTS = "or_variants"      # Same entity, different forms
    AND_ENTITIES = "and_entities"    # Different entities
    AND_COLUMNS = "and_columns"      # Same entity, multiple columns (rare)


@dataclass
class QueryPlan:
    """Complete execution plan."""
    # Scoping
    yacht_id: str
    user_id: Optional[str]

    # Entities expanded
    entity_plans: List['EntityPlan']

    # Conjunction between entities
    entity_conjunction: ConjunctionType  # Usually AND

    # Execution order
    tiers: List['TierPlan']

    # Debug
    trace: List[Dict]


@dataclass
class EntityPlan:
    """Plan for a single entity."""
    entity: IncomingEntity
    variants: List[ExpandedVariant]
    column_matches: List[ColumnMatch]
    bias_scores: Dict[str, float]  # table.column -> score
    requires_conjunction: bool  # If all matches are conjunction_only


@dataclass
class TierPlan:
    """Plan for a tier of execution."""
    tier_num: int
    tables: List[str]
    budget_ms: int


# =============================================================================
# STEP 6: CONSTRUCT - Build parameterized SQL
# =============================================================================

@dataclass
class PreparedSQL:
    """Ready-to-execute SQL with parameters."""
    sql: str
    params: List[Any]
    tier: int
    wave: int
    tables: List[str]
    description: str


def construct_sql(
    plan: QueryPlan,
    tier: int,
    wave: int,
) -> Optional[PreparedSQL]:
    """
    Construct SQL for a tier+wave.

    Key logic:
    - OR within variants of same entity
    - AND across different entities
    - UNION ALL across tables in same tier
    """
    wave_operator = {0: Operator.EXACT, 1: Operator.ILIKE, 2: Operator.TRIGRAM}
    target_op = wave_operator.get(wave)
    if not target_op:
        return None

    union_parts = []
    params = [plan.yacht_id]  # $1 = yacht_id
    param_idx = 2

    # Get tables for this tier
    tier_plan = next((t for t in plan.tiers if t.tier_num == tier), None)
    if not tier_plan:
        return None

    for table_name in tier_plan.tables:
        # Find all entity plans that target this table
        table_conditions = []

        for ep in plan.entity_plans:
            for match in ep.column_matches:
                if match.table != table_name:
                    continue
                if target_op not in match.operators:
                    continue

                # Build OR clause for variants
                variant_conditions = []
                for variant in ep.variants:
                    if variant.operator != target_op:
                        continue

                    if target_op == Operator.EXACT:
                        cond = f"{match.column} = ${param_idx}"
                    elif target_op == Operator.ILIKE:
                        cond = f"{match.column} ILIKE ${param_idx}"
                    elif target_op == Operator.TRIGRAM:
                        cond = f"similarity({match.column}, ${param_idx}) >= 0.3"
                    else:
                        continue

                    variant_conditions.append(cond)
                    params.append(variant.value)
                    param_idx += 1

                if variant_conditions:
                    # OR within variants
                    if len(variant_conditions) == 1:
                        table_conditions.append(variant_conditions[0])
                    else:
                        table_conditions.append(f"({' OR '.join(variant_conditions)})")

        if not table_conditions:
            continue

        # AND across entities
        where_clause = " AND ".join(table_conditions)

        # Get select columns
        table_cfg = TABLES.get(table_name)
        select_cols = ["id"]
        if table_cfg:
            select_cols = table_cfg.default_select[:5]  # Limit columns

        sql_part = f"""(SELECT '{table_name}' AS _source, {', '.join(select_cols)}
FROM {table_name}
WHERE yacht_id = $1
  AND {where_clause}
LIMIT 20)"""

        union_parts.append(sql_part)

    if not union_parts:
        return None

    full_sql = "\nUNION ALL\n".join(union_parts) + "\nLIMIT 50"

    return PreparedSQL(
        sql=full_sql,
        params=params,
        tier=tier,
        wave=wave,
        tables=tier_plan.tables,
        description=f"Tier {tier} Wave {wave}: {len(union_parts)} tables"
    )


# =============================================================================
# MAIN: Build complete plan from incoming query
# =============================================================================

def prepare_query(incoming: IncomingQuery) -> QueryPlan:
    """
    The VLOOKUP equivalent.

    Takes incoming query and produces complete execution plan.
    """
    trace = []
    entity_plans = []
    all_tables_with_bias = {}

    # Process each entity
    for entity in incoming.entities:
        # Expand variants
        variants = expand_variants(entity)

        # Match to columns
        matches = match_entity_to_columns(entity)

        # Compute bias scores
        bias_scores = {}
        for match in matches:
            key = f"{match.table}.{match.column}"
            bias_scores[key] = compute_column_bias(match, entity)

            # Track table bias (max across columns)
            if match.table not in all_tables_with_bias:
                all_tables_with_bias[match.table] = 0
            all_tables_with_bias[match.table] = max(
                all_tables_with_bias[match.table],
                bias_scores[key]
            )

        # Check if requires conjunction
        requires_conjunction = all(m.conjunction_only for m in matches)

        entity_plans.append(EntityPlan(
            entity=entity,
            variants=variants,
            column_matches=matches,
            bias_scores=bias_scores,
            requires_conjunction=requires_conjunction
        ))

        trace.append({
            "entity": entity.type,
            "value": entity.value,
            "variants": len(variants),
            "matches": len(matches),
            "requires_conjunction": requires_conjunction,
            "bias_scores": bias_scores
        })

    # Build tiers from table bias
    tiers = []
    sorted_tables = sorted(all_tables_with_bias.items(), key=lambda x: x[1], reverse=True)

    tier1 = [t for t, b in sorted_tables if b >= 2.0]
    tier2 = [t for t, b in sorted_tables if 1.5 <= b < 2.0]
    tier3 = [t for t, b in sorted_tables if 1.0 <= b < 1.5]

    if tier1:
        tiers.append(TierPlan(tier_num=1, tables=tier1, budget_ms=250))
    if tier2:
        tiers.append(TierPlan(tier_num=2, tables=tier2, budget_ms=300))
    if tier3:
        tiers.append(TierPlan(tier_num=3, tables=tier3, budget_ms=250))

    return QueryPlan(
        yacht_id=incoming.yacht_id,
        user_id=incoming.user_id,
        entity_plans=entity_plans,
        entity_conjunction=ConjunctionType.AND_ENTITIES,
        tiers=tiers,
        trace=trace
    )


def generate_all_sql(plan: QueryPlan) -> List[PreparedSQL]:
    """Generate all SQL statements from plan."""
    statements = []

    for tier in plan.tiers:
        for wave in [0, 1, 2]:
            sql = construct_sql(plan, tier.tier_num, wave)
            if sql:
                statements.append(sql)

    return statements
