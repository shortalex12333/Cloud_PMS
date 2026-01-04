"""
SQL FOUNDATION — UNIVERSAL OPERATOR TEMPLATES
==============================================
These are the ONLY SQL shapes allowed. Everything else is configuration.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class Operator(Enum):
    """The complete operator set. No others allowed."""
    EXACT = "EXACT"
    ILIKE = "ILIKE"
    TRIGRAM = "TRIGRAM"
    IN = "IN"
    RANGE = "RANGE"
    ARRAY_ANY_ILIKE = "ARRAY_ANY_ILIKE"
    JSONB_PATH_ILIKE = "JSONB_PATH_ILIKE"
    VECTOR = "VECTOR"

# =============================================================================
# UNIVERSAL SQL TEMPLATES — ONE PER OPERATOR
# =============================================================================
# These templates are FIXED. Only values are substituted.
# {table}, {select_cols}, {column}, {param} are placeholders filled at runtime.

SQL_TEMPLATES = {
    Operator.EXACT: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {column} = $2
LIMIT {limit}
""",

    Operator.ILIKE: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {column} ILIKE $2
LIMIT {limit}
""",

    Operator.TRIGRAM: """
SELECT {select_cols}, similarity({column}, $2) AS sim_score
FROM {table}
WHERE yacht_id = $1
  AND similarity({column}, $2) >= $3
ORDER BY sim_score DESC
LIMIT {limit}
""",

    Operator.IN: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {column} = ANY($2)
LIMIT {limit}
""",

    Operator.RANGE: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {column} BETWEEN $2 AND $3
LIMIT {limit}
""",

    Operator.ARRAY_ANY_ILIKE: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND EXISTS (
    SELECT 1 FROM unnest({column}) AS x
    WHERE x ILIKE $2
  )
LIMIT {limit}
""",

    Operator.JSONB_PATH_ILIKE: """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND ({column}->>{json_key}) ILIKE $2
LIMIT {limit}
""",

    Operator.VECTOR: """
SELECT {select_cols}, ({column} <-> $2) AS distance
FROM {table}
WHERE yacht_id = $1
ORDER BY {column} <-> $2
LIMIT {limit}
""",
}

# =============================================================================
# MULTI-COLUMN OR TEMPLATE (Shape B)
# =============================================================================
# Same entity across multiple columns in one table

SQL_TEMPLATE_OR_MULTI_COLUMN = """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND ({or_clauses})
LIMIT {limit}
"""

# =============================================================================
# CONJUNCTION AND TEMPLATE (Shape C)
# =============================================================================
# Multiple entities combined

SQL_TEMPLATE_AND_CONJUNCTION = """
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {and_clauses}
LIMIT {limit}
"""

# =============================================================================
# OPERATOR CLAUSE FRAGMENTS (for building OR/AND)
# =============================================================================
CLAUSE_FRAGMENTS = {
    Operator.EXACT: "{column} = ${param_num}",
    Operator.ILIKE: "{column} ILIKE ${param_num}",
    Operator.TRIGRAM: "similarity({column}, ${param_num}) >= ${threshold_param}",
    Operator.IN: "{column} = ANY(${param_num})",
    Operator.RANGE: "{column} BETWEEN ${param_num_a} AND ${param_num_b}",
    Operator.ARRAY_ANY_ILIKE: "EXISTS (SELECT 1 FROM unnest({column}) x WHERE x ILIKE ${param_num})",
    Operator.JSONB_PATH_ILIKE: "({column}->>{json_key}) ILIKE ${param_num}",
}

# =============================================================================
# DATATYPE → ALLOWED OPERATORS
# =============================================================================
# If a column's datatype isn't here, it's not searchable.

DATATYPE_OPERATORS = {
    "text": [Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM],
    "varchar": [Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM],
    "integer": [Operator.EXACT, Operator.IN, Operator.RANGE],
    "bigint": [Operator.EXACT, Operator.IN, Operator.RANGE],
    "numeric": [Operator.EXACT, Operator.RANGE],
    "boolean": [Operator.EXACT],
    "date": [Operator.EXACT, Operator.RANGE],
    "timestamp": [Operator.EXACT, Operator.RANGE],
    "timestamptz": [Operator.EXACT, Operator.RANGE],
    "uuid": [Operator.EXACT, Operator.IN],
    "text[]": [Operator.ARRAY_ANY_ILIKE, Operator.IN],
    "jsonb": [Operator.JSONB_PATH_ILIKE],
    "vector": [Operator.VECTOR],
}

# =============================================================================
# WAVE ASSIGNMENT
# =============================================================================
OPERATOR_WAVES = {
    Operator.EXACT: 0,
    Operator.IN: 0,
    Operator.ILIKE: 1,
    Operator.RANGE: 1,
    Operator.ARRAY_ANY_ILIKE: 1,
    Operator.JSONB_PATH_ILIKE: 1,
    Operator.TRIGRAM: 2,
    Operator.VECTOR: 3,
}

WAVE_BUDGETS_MS = {
    0: 500,    # Exact IDs - fast
    1: 1500,   # Primary text search
    2: 3000,   # Fuzzy fallback
    3: 5000,   # Vector/docs heavy
}
