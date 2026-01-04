"""
BIAS-BUCKETED WAVE SEARCH (BBWS)
================================
Federated search that:
1. Assigns bias scores to tables based on query signals
2. Groups tables into tiers by bias thresholds
3. Executes match-mode waves in precision→recall order
4. Uses bounded parallelism within each tier+wave
5. Merges + diversifies results and stops early under strict gates
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .column_config import TABLES, get_columns_for_entity


# =============================================================================
# TABLE PRIORS: Entity Type / Intent → Table Bias
# =============================================================================

# Primary tables for each entity type (gets +2.0 bias)
# Can have multiple primary tables
ENTITY_PRIMARY_TABLES = {
    "PART_NUMBER": ["pms_parts"],
    "PART_NAME": ["pms_parts"],
    "EQUIPMENT_NAME": ["pms_equipment", "graph_nodes"],  # Both are primary
    "EQUIPMENT_CODE": ["pms_equipment"],
    "SERIAL_NUMBER": ["pms_equipment"],
    "FAULT_CODE": ["pms_faults", "search_fault_code_catalog"],
    "SYMPTOM": ["symptom_aliases", "pms_faults"],
    "SUPPLIER_NAME": ["pms_suppliers"],
    "PO_NUMBER": ["pms_purchase_orders"],
    "WORK_ORDER_TITLE": ["pms_work_orders"],
    "LOCATION": ["pms_equipment"],
    "SYSTEM_NAME": ["pms_equipment", "graph_nodes"],
    "MANUFACTURER": ["pms_parts", "pms_suppliers"],
    "NODE_LABEL": ["graph_nodes"],
}

# Intent → table bias adjustments
INTENT_TABLE_BIAS = {
    "check_stock": {"pms_parts": +0.5, "pms_purchase_orders": +0.3},
    "find_fault": {"pms_faults": +0.5, "symptom_aliases": +0.3},
    "lookup_equipment": {"pms_equipment": +0.5, "graph_nodes": +0.3},
    "find_supplier": {"pms_suppliers": +0.5},
    "work_order": {"pms_work_orders": +0.5},
}

# Tables that are "noisy" (large, generic) - penalty for weak entities
NOISY_TABLES = {"graph_nodes": -0.5}

# Tier thresholds
TIER_THRESHOLDS = {
    1: 2.0,   # Tier 1: bias >= 2.0
    2: 1.5,   # Tier 2: 1.5 <= bias < 2.0
    3: 1.0,   # Tier 3: 1.0 <= bias < 1.5
}

# Wave budgets (ms)
TIER_BUDGETS_MS = {
    1: 250,   # Tier 1: 250ms
    2: 300,   # Tier 2: 300ms
    3: 250,   # Tier 3: 250ms
}
TOTAL_BUDGET_MS = 800

# Early exit thresholds
STRONG_HIT_COUNT = 5  # Exit if >= 5 exact matches
SCORE_THRESHOLD = 0.9  # Exit if top result score > 0.9


@dataclass
class TableBias:
    """Bias score for a table."""
    table: str
    bias: float
    reasons: List[str]
    columns: List[str]  # Which columns to search
    operators: List[str]  # Which operators apply


@dataclass
class Tier:
    """A batch of tables with similar bias."""
    tier_num: int
    tables: List[TableBias]
    budget_ms: int


@dataclass
class BBWSPlan:
    """Execution plan for BBWS."""
    tiers: List[Tier]
    total_tables: int
    total_budget_ms: int
    trace: List[Dict]  # Why each table got its bias


def compute_table_bias(
    table_name: str,
    entities: List[Dict],
    intent: Optional[str] = None,
) -> TableBias:
    """
    Compute bias score for a table based on query signals.

    Scoring:
    +2.0 if table is primary for entity type
    +1.0 if table supports canonical match for strong entity
    +0.5 if intent strongly maps to table
    -0.5 if table is noisy and only weak entities present
    """
    bias = 0.0
    reasons = []
    matched_columns = set()
    matched_operators = set()

    table_cfg = TABLES.get(table_name)
    if not table_cfg:
        return TableBias(table_name, 0.0, ["table not configured"], [], [])

    # Check each entity
    for entity in entities:
        entity_type = entity.get("type", "")
        entity_value = entity.get("value", "")
        confidence = entity.get("confidence", 1.0)

        # Primary table bonus (+2.0)
        primary_tables = ENTITY_PRIMARY_TABLES.get(entity_type, [])
        if table_name in primary_tables:
            bias += 2.0
            reasons.append(f"{entity_type} primary table")

        # Check if table has columns for this entity type
        for col_name, col_cfg in table_cfg.columns.items():
            if entity_type in col_cfg.entity_types:
                # Supports this entity
                matched_columns.add(col_name)

                # EXACT support bonus (+1.0)
                from .operators import Operator
                if Operator.EXACT in col_cfg.operators:
                    if bias < 2.0:  # Don't double-count with primary
                        bias += 1.0
                        reasons.append(f"supports EXACT on {col_name}")
                    matched_operators.add("EXACT")

                if Operator.ILIKE in col_cfg.operators:
                    matched_operators.add("ILIKE")

                if Operator.TRIGRAM in col_cfg.operators:
                    matched_operators.add("TRIGRAM")

    # Intent bonus
    if intent and intent in INTENT_TABLE_BIAS:
        intent_bias = INTENT_TABLE_BIAS[intent].get(table_name, 0)
        if intent_bias:
            bias += intent_bias
            reasons.append(f"intent={intent} partial match")

    # Noisy table penalty (only if weak entities)
    weak_entities = [e for e in entities if e.get("confidence", 1.0) < 0.7]
    if table_name in NOISY_TABLES and weak_entities:
        penalty = NOISY_TABLES[table_name]
        bias += penalty
        reasons.append(f"noisy table penalty ({penalty})")

    if not reasons:
        reasons.append("no direct match")

    return TableBias(
        table=table_name,
        bias=round(bias, 2),
        reasons=reasons,
        columns=list(matched_columns),
        operators=list(matched_operators)
    )


def plan_bbws(
    entities: List[Dict],
    intent: Optional[str] = None,
) -> BBWSPlan:
    """
    Create BBWS execution plan.

    1. Score all tables
    2. Group into tiers
    3. Return execution plan
    """
    trace = []

    # Score all configured tables
    table_scores = []
    for table_name in TABLES.keys():
        bias = compute_table_bias(table_name, entities, intent)
        table_scores.append(bias)
        trace.append({
            "table": table_name,
            "bias": bias.bias,
            "reasons": bias.reasons,
            "columns": bias.columns,
        })

    # Sort by bias descending
    table_scores.sort(key=lambda x: x.bias, reverse=True)

    # Group into tiers
    tiers = []
    for tier_num in [1, 2, 3]:
        threshold = TIER_THRESHOLDS[tier_num]
        next_threshold = TIER_THRESHOLDS.get(tier_num + 1, 0)

        tier_tables = [
            t for t in table_scores
            if t.bias >= threshold and (tier_num == 1 or t.bias < TIER_THRESHOLDS.get(tier_num - 1, 999))
        ]

        # Actually filter properly
        if tier_num == 1:
            tier_tables = [t for t in table_scores if t.bias >= 2.0]
        elif tier_num == 2:
            tier_tables = [t for t in table_scores if 1.5 <= t.bias < 2.0]
        elif tier_num == 3:
            tier_tables = [t for t in table_scores if 1.0 <= t.bias < 1.5]

        if tier_tables:
            tiers.append(Tier(
                tier_num=tier_num,
                tables=tier_tables,
                budget_ms=TIER_BUDGETS_MS[tier_num]
            ))

    return BBWSPlan(
        tiers=tiers,
        total_tables=sum(len(t.tables) for t in tiers),
        total_budget_ms=TOTAL_BUDGET_MS,
        trace=trace
    )


# =============================================================================
# UNION COMPILER: One SQL per (tier, wave)
# =============================================================================

def compile_union_sql(
    tier: Tier,
    wave: int,
    yacht_id: str,
    entities: List[Dict],
) -> Tuple[Optional[str], List[Any]]:
    """
    Compile UNION ALL query for a tier+wave.

    Returns (sql, params) or (None, []) if no queries for this wave.
    """
    from .operators import Operator

    # Map wave to operator
    wave_operator = {
        0: "EXACT",
        1: "ILIKE",
        2: "TRIGRAM",
    }

    op_name = wave_operator.get(wave)
    if not op_name:
        return None, []

    union_parts = []
    params = [yacht_id]  # $1 is always yacht_id
    param_idx = 2

    for table_bias in tier.tables:
        if op_name not in table_bias.operators:
            continue

        table_name = table_bias.table
        table_cfg = TABLES.get(table_name)
        if not table_cfg:
            continue

        # Find entity value to search
        entity_value = None
        for entity in entities:
            if any(entity.get("type") in col.entity_types
                   for col in table_cfg.columns.values()
                   if col.name in table_bias.columns):
                entity_value = entity.get("value")
                break

        if not entity_value:
            continue

        # Build SELECT for this table
        # Normalize columns across tables
        select_cols = [
            f"'{table_name}' AS _source",
            "id",
        ]

        # Add table-specific columns with aliases
        for col in table_bias.columns[:3]:  # Limit to 3 columns
            select_cols.append(f"{col} AS _match_col")
            break  # Just first match column

        select_str = ", ".join(select_cols)

        # Build WHERE based on operator
        for col_name in table_bias.columns:
            col_cfg = table_cfg.columns.get(col_name)
            if not col_cfg:
                continue

            op_enum = Operator[op_name]
            if op_enum not in col_cfg.operators:
                continue

            if op_name == "EXACT":
                value = entity_value.upper()
                where = f"{col_name} = ${param_idx}"
            elif op_name == "ILIKE":
                value = f"%{entity_value}%"
                where = f"{col_name} ILIKE ${param_idx}"
            elif op_name == "TRIGRAM":
                value = entity_value.lower()
                where = f"similarity({col_name}, ${param_idx}) >= 0.3"
            else:
                continue

            sql_part = f"""(SELECT {select_str}
FROM {table_name}
WHERE yacht_id = $1
  AND {where}
LIMIT 20)"""

            union_parts.append(sql_part.strip())
            params.append(value)
            param_idx += 1
            break  # One query per table per wave

    if not union_parts:
        return None, []

    # Combine with UNION ALL
    full_sql = "\nUNION ALL\n".join(union_parts)
    full_sql += "\nLIMIT 50"

    return full_sql, params


def generate_bbws_sql(
    plan: BBWSPlan,
    yacht_id: str,
    entities: List[Dict],
) -> List[Dict]:
    """
    Generate all SQL for BBWS execution.

    Returns list of {tier, wave, sql, params}
    """
    queries = []

    for tier in plan.tiers:
        for wave in [0, 1, 2]:  # EXACT, ILIKE, TRIGRAM
            sql, params = compile_union_sql(tier, wave, yacht_id, entities)
            if sql:
                queries.append({
                    "tier": tier.tier_num,
                    "wave": wave,
                    "sql": sql,
                    "params": params,
                    "tables": [t.table for t in tier.tables],
                })

    return queries
