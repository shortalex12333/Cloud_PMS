"""
SQL GENERATOR: ExecutionPlan → Parameterized SQL
=================================================
Takes the PREPARE output and generates ready-to-execute SQL.

Key rules:
- OR within variants of same entity
- AND across different entities
- UNION ALL across tables in same tier+wave
- One SQL per (tier, wave) combination
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from .prepare import ExecutionPlan, ResolvedQuery, BatchPlan, ExpandedTerm
from .operators import Operator
from .column_config import TABLES


@dataclass
class GeneratedSQL:
    """Ready-to-execute SQL statement."""
    tier: int
    wave: int
    operator: Operator
    sql: str
    params: List[Any]
    tables: List[str]
    description: str


def generate_wave_sql(
    plan: ExecutionPlan,
    batch: BatchPlan,
    wave_op: Operator
) -> Optional[GeneratedSQL]:
    """
    Generate UNION ALL SQL for a single tier+wave.

    Returns None if no tables support this wave.
    """
    union_parts = []
    params = [plan.user_scope.yacht_ids[0]]  # $1 = yacht_id
    param_idx = 2

    for table_name in batch.tables:
        # Find resolved query for this table
        resolved = next(
            (r for r in plan.resolved_queries if r.table == table_name),
            None
        )
        if not resolved:
            continue

        # Check if table supports this wave operator
        table_cfg = TABLES.get(table_name)
        if not table_cfg:
            continue

        # Build conditions for this table
        table_conditions = []

        for cond in resolved.conditions:
            # Check if column supports this operator
            col_cfg = table_cfg.columns.get(cond["column"])
            if not col_cfg:
                continue
            if wave_op not in col_cfg.operators:
                continue

            # Build OR clause for variants matching this wave
            variant_conditions = []
            for variant in cond["variants"]:
                if variant.operator != wave_op:
                    continue

                # Build condition based on operator
                if wave_op == Operator.EXACT:
                    condition = f"{cond['column']} = ${param_idx}"
                    params.append(variant.value)
                elif wave_op == Operator.ILIKE:
                    condition = f"{cond['column']} ILIKE ${param_idx}"
                    params.append(variant.value)
                elif wave_op == Operator.TRIGRAM:
                    condition = f"similarity({cond['column']}, ${param_idx}) >= 0.3"
                    params.append(variant.value.lower().replace('%', ''))
                else:
                    continue

                variant_conditions.append(condition)
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
        select_cols = ["id"]
        if table_cfg:
            select_cols = table_cfg.default_select[:5]

        sql_part = f"""(SELECT '{table_name}' AS _source, {', '.join(select_cols)}
FROM {table_name}
WHERE yacht_id = $1
  AND {where_clause}
LIMIT 20)"""

        union_parts.append(sql_part)

    if not union_parts:
        return None

    full_sql = "\nUNION ALL\n".join(union_parts) + "\nLIMIT 50;"

    wave_names = {
        Operator.EXACT: "EXACT",
        Operator.ILIKE: "ILIKE",
        Operator.TRIGRAM: "TRIGRAM"
    }

    return GeneratedSQL(
        tier=batch.tier,
        wave=batch.wave_order.index(wave_op) if wave_op in batch.wave_order else 0,
        operator=wave_op,
        sql=full_sql,
        params=params,
        tables=batch.tables,
        description=f"Tier {batch.tier} {wave_names.get(wave_op, str(wave_op))}: {len(union_parts)} tables"
    )


def generate_all_sql(plan: ExecutionPlan) -> List[GeneratedSQL]:
    """
    Generate all SQL statements from execution plan.

    Returns list of SQL statements, ordered by (tier, wave).
    """
    statements = []

    # Check for blocked lane
    if plan.lane.lane.value == "BLOCKED":
        return []

    # Generate SQL for each batch (tier)
    for batch in plan.batches:
        for wave_op in batch.wave_order:
            sql = generate_wave_sql(plan, batch, wave_op)
            if sql:
                statements.append(sql)

    return statements


def format_sql_for_display(statements: List[GeneratedSQL]) -> str:
    """
    Format SQL statements for human inspection.

    Shows actual SQL with parameters substituted for readability.
    """
    output = []
    output.append("-- GENERATED SQL")
    output.append("-- ==============")
    output.append("")

    for stmt in statements:
        output.append(f"-- {stmt.description}")
        output.append(f"-- Tables: {stmt.tables}")
        output.append(f"-- Params: {stmt.params}")
        output.append("")

        # Substitute params for readability
        sql_display = stmt.sql
        for i, param in enumerate(stmt.params):
            placeholder = f"${i+1}"
            if isinstance(param, str):
                replacement = f"'{param}'"
            else:
                replacement = str(param)
            sql_display = sql_display.replace(placeholder, replacement, 1)

        output.append(sql_display)
        output.append("")
        output.append("")

    return "\n".join(output)


# =============================================================================
# CONVENIENCE: One-shot prepare + generate
# =============================================================================

def prepare_and_generate(
    query_text: str,
    entities: List[Dict],
    yacht_id: str,
    user_id: str,
    user_role: str = "crew"
) -> Tuple[ExecutionPlan, List[GeneratedSQL]]:
    """
    Complete pipeline: prepare + generate SQL.

    Returns (ExecutionPlan, List[GeneratedSQL])
    """
    from .prepare import prepare

    plan = prepare(query_text, entities, yacht_id, user_id, user_role)
    statements = generate_all_sql(plan)

    return plan, statements
