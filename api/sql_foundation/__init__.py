"""
SQL FOUNDATION
==============
Universal, uniform, substitutable SQL execution system.

Components:
- operators.py: Universal operator set and SQL templates
- probe.py: Probe schema (the smallest executable unit)
- column_config.py: Column capability declarations
- compiler.py: Entity → Probe compilation
- executor.py: Probe execution against database
- prepare.py: Complete PREPARE stage (lane, scope, variants, ranking)
- generate_sql.py: ExecutionPlan → SQL generation
"""

from .operators import Operator, SQL_TEMPLATES, OPERATOR_WAVES, WAVE_BUDGETS_MS
from .probe import (
    Probe, ProbeResult, Variant, VariantType, WhereClause, Conjunction,
    probe_single, probe_or_multicolumn, probe_and_conjunction
)
from .column_config import TABLES, get_columns_for_entity, get_table, ColumnCapability, TableCapability
from .compiler import ProbeCompiler, Entity, create_entity, compile_probes
from .executor import ProbeExecutor, WaveResult
from .search import search, search_by_text, SearchResult

# New: PREPARE + SQL Generation
from .prepare import (
    prepare, ExecutionPlan, Lane, LaneDecision,
    UserScope, ExpandedTerm, Intent, TableScore, ColumnMatch,
    ConjunctionPlan, ResolvedQuery, BatchPlan, ExitCondition
)
from .generate_sql import (
    generate_all_sql, generate_wave_sql, prepare_and_generate,
    GeneratedSQL, format_sql_for_display
)

__all__ = [
    # Operators
    "Operator", "SQL_TEMPLATES", "OPERATOR_WAVES", "WAVE_BUDGETS_MS",
    # Probe
    "Probe", "ProbeResult", "Variant", "VariantType", "WhereClause", "Conjunction",
    "probe_single", "probe_or_multicolumn", "probe_and_conjunction",
    # Config
    "TABLES", "get_columns_for_entity", "get_table", "ColumnCapability", "TableCapability",
    # Compiler
    "ProbeCompiler", "Entity", "create_entity", "compile_probes",
    # Executor
    "ProbeExecutor", "WaveResult",
    # Search (main entry point)
    "search", "search_by_text", "SearchResult",
    # PREPARE stage
    "prepare", "ExecutionPlan", "Lane", "LaneDecision",
    "UserScope", "ExpandedTerm", "Intent", "TableScore", "ColumnMatch",
    "ConjunctionPlan", "ResolvedQuery", "BatchPlan", "ExitCondition",
    # SQL Generation
    "generate_all_sql", "generate_wave_sql", "prepare_and_generate",
    "GeneratedSQL", "format_sql_for_display",
]
