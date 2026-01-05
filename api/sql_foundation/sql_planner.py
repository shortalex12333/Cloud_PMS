"""
SQL PLANNING MATRIX — DETERMINISTIC RULESET
============================================
This is the SINGLE SOURCE OF TRUTH for how extraction output maps to SQL execution.

NO HAND-WAVING. Every rule is explicit and testable.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum

from .operators import Operator, OPERATOR_WAVES, WAVE_BUDGETS_MS
from .column_config import TABLES, get_columns_for_entity, get_table

# =============================================================================
# DELIVERABLE 1: SQL PLANNING MATRIX
# =============================================================================

class Intent(str, Enum):
    """Query intents - determines execution strategy"""
    LOOKUP = "lookup"       # Direct ID/code lookup (E047, PO-2024-001)
    SEARCH = "search"       # Find by attributes (oil filter, MTU parts)
    LIST = "list"           # Enumerate items (all generators, pending WOs)
    DIAGNOSE = "diagnose"   # Troubleshooting (overheating, fault analysis)
    ACTION = "action"       # Create/update intent (create WO, log entry)
    COMPARE = "compare"     # Multiple items (A vs B, before/after)


class Lane(str, Enum):
    """Processing lanes"""
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NO_LLM = "NO_LLM"
    RULES_ONLY = "RULES_ONLY"
    GPT = "GPT"


# =============================================================================
# LANE → CAPABILITY MATRIX
# =============================================================================

LANE_CAPABILITIES = {
    Lane.BLOCKED: {
        "waves_allowed": [],
        "vector_allowed": False,
        "max_tables": 0,
        "max_entities": 0,
        "action": "reject",
    },
    Lane.UNKNOWN: {
        "waves_allowed": [0],  # EXACT only
        "vector_allowed": False,
        "max_tables": 2,
        "max_entities": 2,
        "action": "suggest_clarify",
    },
    Lane.NO_LLM: {
        "waves_allowed": [0, 1, 2],  # EXACT, ILIKE, TRIGRAM
        "vector_allowed": False,
        "max_tables": 4,
        "max_entities": 5,
        "action": "execute",
    },
    Lane.RULES_ONLY: {
        "waves_allowed": [0, 1],  # EXACT, ILIKE only
        "vector_allowed": False,
        "max_tables": 3,
        "max_entities": 3,
        "action": "execute_action",
    },
    Lane.GPT: {
        "waves_allowed": [0, 1, 2, 3],  # All waves including VECTOR
        "vector_allowed": True,
        "max_tables": 6,
        "max_entities": 8,
        "action": "execute_with_reasoning",
    },
}


# =============================================================================
# INTENT → TABLE ROUTING
# =============================================================================

INTENT_TABLE_PRIORITY = {
    Intent.LOOKUP: [
        "pms_parts",           # Part numbers
        "pms_equipment",       # Equipment codes
        "pms_faults",          # Fault codes
        "pms_purchase_orders", # PO numbers
        "pms_work_orders",     # WO references
    ],
    Intent.SEARCH: [
        "pms_parts",
        "pms_equipment",
        "graph_nodes",
        "symptom_aliases",
        "pms_suppliers",
    ],
    Intent.LIST: [
        "pms_equipment",
        "pms_work_orders",
        "pms_purchase_orders",
        "pms_parts",
    ],
    Intent.DIAGNOSE: [
        "pms_faults",
        "search_fault_code_catalog",
        "symptom_aliases",
        "graph_nodes",
        "pms_equipment",
    ],
    Intent.ACTION: [
        "pms_work_orders",
        "pms_equipment",
        "pms_parts",
    ],
    Intent.COMPARE: [
        "pms_parts",
        "pms_equipment",
        "pms_faults",
    ],
}


# =============================================================================
# ENTITY TYPE → WAVE SCHEDULE
# =============================================================================

ENTITY_WAVE_SCHEDULE = {
    # Canonical IDs - EXACT only, Wave 0
    "PART_NUMBER": {"waves": [0], "operators": [Operator.EXACT]},
    "EQUIPMENT_CODE": {"waves": [0], "operators": [Operator.EXACT]},
    "FAULT_CODE": {"waves": [0], "operators": [Operator.EXACT]},
    "PO_NUMBER": {"waves": [0], "operators": [Operator.EXACT]},
    "SERIAL_NUMBER": {"waves": [0], "operators": [Operator.EXACT]},

    # Named entities - EXACT → ILIKE → TRIGRAM
    "PART_NAME": {"waves": [0, 1, 2], "operators": [Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM]},
    "EQUIPMENT_NAME": {"waves": [0, 1, 2], "operators": [Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM]},
    "MANUFACTURER": {"waves": [1], "operators": [Operator.ILIKE]},  # Never isolated
    "SUPPLIER_NAME": {"waves": [1, 2], "operators": [Operator.ILIKE, Operator.TRIGRAM]},

    # Descriptive - ILIKE → TRIGRAM only
    "SYMPTOM": {"waves": [1, 2], "operators": [Operator.ILIKE, Operator.TRIGRAM]},
    "DESCRIPTION": {"waves": [1, 2], "operators": [Operator.ILIKE, Operator.TRIGRAM]},
    "FREE_TEXT": {"waves": [1, 2], "operators": [Operator.ILIKE, Operator.TRIGRAM]},

    # Categorical - EXACT only
    "STATUS": {"waves": [0], "operators": [Operator.EXACT]},
    "PRIORITY": {"waves": [0], "operators": [Operator.EXACT]},
    "SEVERITY": {"waves": [0], "operators": [Operator.EXACT]},
    "SYSTEM_NAME": {"waves": [0, 1], "operators": [Operator.EXACT, Operator.ILIKE]},
    "LOCATION": {"waves": [0, 1], "operators": [Operator.EXACT, Operator.ILIKE]},

    # Graph/vector - all waves
    "NODE_LABEL": {"waves": [0, 1, 2], "operators": [Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM]},
    "DOC_QUERY": {"waves": [3], "operators": [Operator.VECTOR]},  # Vector only
}


# =============================================================================
# VOLUME CONSTRAINTS
# =============================================================================

@dataclass
class VolumeConstraints:
    """Hard limits to prevent runaway queries"""
    max_entities_per_query: int = 8
    max_variants_per_entity: int = 5
    max_tables_per_wave: int = 4
    max_rows_per_wave: int = 50
    max_total_rows: int = 100
    early_exit_threshold: int = 20
    min_score_threshold: float = 0.3
    max_waves: int = 4
    timeout_ms: int = 5000


# =============================================================================
# RANKING CONTROLS
# =============================================================================

@dataclass
class RankingConfig:
    """Scoring weights and biases"""
    # Match type multipliers
    exact_boost: float = 3.0
    ilike_boost: float = 1.5
    trigram_boost: float = 0.8
    vector_boost: float = 1.2

    # Table biases (higher = preferred)
    table_bias: Dict[str, float] = field(default_factory=lambda: {
        "pms_parts": 1.0,
        "pms_equipment": 1.2,
        "pms_faults": 1.1,
        "pms_work_orders": 0.9,
        "pms_purchase_orders": 0.7,
        "pms_suppliers": 0.6,
        "graph_nodes": 0.8,
        "symptom_aliases": 0.7,
        "search_fault_code_catalog": 1.0,
    })

    # Entity weight (how much this entity type matters)
    entity_weight: Dict[str, float] = field(default_factory=lambda: {
        "PART_NUMBER": 2.0,
        "EQUIPMENT_CODE": 2.0,
        "FAULT_CODE": 2.0,
        "PART_NAME": 1.5,
        "EQUIPMENT_NAME": 1.5,
        "SYMPTOM": 1.3,
        "MANUFACTURER": 0.8,
        "FREE_TEXT": 0.5,
    })

    # Diversity caps
    max_per_table: int = 10
    max_per_entity_group: int = 5

    # Penalties
    cluster_penalty: float = 0.9  # Applied to 3rd+ result from same table
    recency_boost: float = 1.1   # For work orders with recent dates


# =============================================================================
# DELIVERABLE 2: PREPARE → EXECUTE RULES
# =============================================================================

@dataclass
class SQLPlan:
    """Complete plan for executing a query"""
    request_id: str
    lane: Lane
    intent: Intent
    tables: List[str]
    waves: List[int]
    entities: List[Dict]
    constraints: VolumeConstraints
    ranking: RankingConfig
    vector_enabled: bool
    stop_conditions: Dict[str, Any]
    security: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "lane": self.lane.value,
            "intent": self.intent.value,
            "tables": self.tables,
            "waves": self.waves,
            "entity_count": len(self.entities),
            "vector_enabled": self.vector_enabled,
        }


class SQLPlanner:
    """
    Translates extraction output to SQL execution plan.

    RULES (numbered, deterministic):

    R1: yacht_id is ALWAYS required. No exceptions.
    R2: Lane determines max capabilities (waves, tables, vector)
    R3: Intent determines table priority order
    R4: Entity type determines wave schedule and operators
    R5: OR within entity variants, AND across entity types
    R6: Entity collisions on same column → OR together
    R7: Entity soup (>5 entities, no verb) → UNKNOWN lane
    R8: UUID entity → EXACT only on UUID columns
    R9: Lane != GPT → never call vector_search
    R10: Multi-intent splitters → decompose, plan per clause, merge
    R11: Frequency/repeated terms → dedupe, cap at 3 variants
    R12: Cluster diversity → cap 10 per table, 5 per entity group
    """

    def __init__(self):
        self.constraints = VolumeConstraints()
        self.ranking = RankingConfig()

    def plan(
        self,
        lane: Lane,
        entities: List[Dict],
        intent: Optional[Intent] = None,
        yacht_id: str = None,
        embedding: Optional[List[float]] = None,
    ) -> SQLPlan:
        """
        Create execution plan from extraction output.

        Args:
            lane: Processing lane from router
            entities: Extracted entities [{type, value, confidence, variants}]
            intent: Detected intent (or inferred)
            yacht_id: Required yacht scope
            embedding: Pre-computed embedding for vector search
        """
        import uuid
        request_id = str(uuid.uuid4())[:8]

        # R1: yacht_id ALWAYS required
        if not yacht_id:
            raise ValueError("R1 VIOLATION: yacht_id is required")

        # R2: Lane determines capabilities
        lane_caps = LANE_CAPABILITIES[lane]

        # R7: Entity soup check
        if len(entities) > 5 and intent is None:
            # Too many entities, no clear intent → force UNKNOWN
            lane = Lane.UNKNOWN
            lane_caps = LANE_CAPABILITIES[lane]

        # Infer intent if not provided
        if intent is None:
            intent = self._infer_intent(entities)

        # R3: Intent determines table priority
        tables = self._select_tables(intent, entities, lane_caps["max_tables"])

        # R4: Entity types determine waves
        waves = self._compute_waves(entities, lane_caps["waves_allowed"])

        # R9: Vector only for GPT lane
        vector_enabled = lane_caps["vector_allowed"] and embedding is not None

        # R11: Dedupe and cap variants
        entities = self._dedupe_entities(entities)

        # Build plan
        plan = SQLPlan(
            request_id=request_id,
            lane=lane,
            intent=intent,
            tables=tables,
            waves=waves,
            entities=entities,
            constraints=self.constraints,
            ranking=self.ranking,
            vector_enabled=vector_enabled,
            stop_conditions={
                "early_exit_threshold": self.constraints.early_exit_threshold,
                "max_rows": self.constraints.max_total_rows,
                "min_score": self.constraints.min_score_threshold,
                "timeout_ms": self.constraints.timeout_ms,
            },
            security={
                "yacht_id": yacht_id,
                "yacht_id_enforced": True,
                "parameterized": True,
            },
        )

        return plan

    def _infer_intent(self, entities: List[Dict]) -> Intent:
        """
        Infer intent from entity types.

        Rules:
        - Has FAULT_CODE/SYMPTOM → DIAGNOSE
        - Has exact ID (PART_NUMBER, EQUIPMENT_CODE) → LOOKUP
        - Has STATUS/PRIORITY filter → LIST
        - Otherwise → SEARCH
        """
        entity_types = {e.get("type") for e in entities}

        if "FAULT_CODE" in entity_types or "SYMPTOM" in entity_types:
            return Intent.DIAGNOSE

        if entity_types & {"PART_NUMBER", "EQUIPMENT_CODE", "PO_NUMBER", "SERIAL_NUMBER"}:
            return Intent.LOOKUP

        if entity_types & {"STATUS", "PRIORITY"}:
            return Intent.LIST

        return Intent.SEARCH

    def _select_tables(
        self,
        intent: Intent,
        entities: List[Dict],
        max_tables: int
    ) -> List[str]:
        """
        Select tables based on intent + entity types.

        Priority order from INTENT_TABLE_PRIORITY, filtered by entity compatibility.
        """
        priority_tables = INTENT_TABLE_PRIORITY.get(intent, list(TABLES.keys()))
        entity_types = {e.get("type") for e in entities}

        # Filter to tables that have columns for our entity types
        compatible = []
        for table in priority_tables:
            table_cfg = get_table(table)
            if not table_cfg:
                continue

            # Check if any column supports any of our entity types
            for col in table_cfg.columns.values():
                if entity_types & set(col.entity_types):
                    compatible.append(table)
                    break

        return compatible[:max_tables]

    def _compute_waves(
        self,
        entities: List[Dict],
        allowed_waves: List[int]
    ) -> List[int]:
        """
        Determine which waves to execute based on entity types.
        """
        needed_waves = set()

        for entity in entities:
            entity_type = entity.get("type", "FREE_TEXT")
            schedule = ENTITY_WAVE_SCHEDULE.get(entity_type, {"waves": [1, 2]})
            for wave in schedule["waves"]:
                if wave in allowed_waves:
                    needed_waves.add(wave)

        return sorted(needed_waves)

    def _dedupe_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        R11: Dedupe entities and cap variants.
        """
        seen_values = set()
        deduped = []

        for entity in entities:
            value = entity.get("value", "").lower().strip()
            if value in seen_values:
                continue
            if len(value) < 2:
                continue

            seen_values.add(value)

            # Cap variants
            variants = entity.get("variants", [])[:3]
            entity["variants"] = variants

            deduped.append(entity)

        return deduped[:self.constraints.max_entities_per_query]

    def build_where_clauses(
        self,
        plan: SQLPlan,
        table: str,
        wave: int
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build WHERE clauses for a specific table and wave.

        R5: OR within entity variants
        R6: Entity collisions on same column → OR together
        """
        table_cfg = get_table(table)
        if not table_cfg:
            return "", {}

        params = {"yacht_id": plan.security["yacht_id"]}
        param_counter = 1

        # Group clauses by entity type
        entity_groups = []

        for entity in plan.entities:
            entity_type = entity.get("type")
            value = entity.get("value")
            variants = entity.get("variants", [])

            # Get schedule for this entity type
            schedule = ENTITY_WAVE_SCHEDULE.get(entity_type, {"waves": [1], "operators": [Operator.ILIKE]})

            if wave not in schedule["waves"]:
                continue

            # Find matching columns in this table
            col_clauses = []
            for col_name, col_cfg in table_cfg.columns.items():
                if entity_type not in col_cfg.entity_types:
                    continue

                # Check operator is allowed for this wave and column
                for op in schedule["operators"]:
                    if op not in col_cfg.operators:
                        continue
                    if OPERATOR_WAVES.get(op, 99) != wave:
                        continue

                    # Build clause for value + variants (R5: OR within)
                    all_values = [value] + variants
                    value_clauses = []

                    for v in all_values:
                        param_counter += 1
                        param_name = f"p{param_counter}"

                        if op == Operator.EXACT:
                            value_clauses.append(f"{col_name} = :{param_name}")
                            params[param_name] = v
                        elif op == Operator.ILIKE:
                            value_clauses.append(f"{col_name} ILIKE :{param_name}")
                            params[param_name] = f"%{v}%"
                        elif op == Operator.TRIGRAM:
                            value_clauses.append(f"similarity({col_name}, :{param_name}) > 0.3")
                            params[param_name] = v

                    if value_clauses:
                        # R5: OR within variants
                        col_clauses.append(f"({' OR '.join(value_clauses)})")

            if col_clauses:
                # R6: OR together columns for same entity
                entity_groups.append(f"({' OR '.join(col_clauses)})")

        if not entity_groups:
            return "", params

        # AND across entity types
        where_sql = " AND ".join(entity_groups)

        return where_sql, params


# =============================================================================
# DELIVERABLE 3: TRACE SCHEMA
# =============================================================================

@dataclass
class WaveTrace:
    """Per-wave execution trace"""
    wave: int
    tables_queried: List[str]
    rows_returned: int
    latency_ms: float
    operator_used: str
    error: Optional[str] = None


@dataclass
class SecurityTrace:
    """Security telemetry - SEPARATE from query results"""
    injection_detected: bool = False
    injection_type: Optional[str] = None  # sql, xss, path_traversal, jailbreak
    pattern_matched: Optional[str] = None
    yacht_id_enforced: bool = True
    parameterized: bool = True
    blocked: bool = False


@dataclass
class ExecutionTrace:
    """Complete execution trace for a request"""
    request_id: str
    lane: str
    intent: str
    plan: Dict  # SQLPlan.to_dict()
    waves: List[WaveTrace]
    total_latency_ms: float
    result_count: int
    early_exit: bool
    stop_reason: str  # "threshold", "timeout", "complete", "error"
    security: SecurityTrace

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "lane": self.lane,
            "intent": self.intent,
            "plan": self.plan,
            "waves": [
                {
                    "wave": w.wave,
                    "tables": w.tables_queried,
                    "rows": w.rows_returned,
                    "latency_ms": w.latency_ms,
                    "error": w.error,
                }
                for w in self.waves
            ],
            "total_latency_ms": self.total_latency_ms,
            "result_count": self.result_count,
            "early_exit": self.early_exit,
            "stop_reason": self.stop_reason,
            "security": {
                "injection_detected": self.security.injection_detected,
                "injection_type": self.security.injection_type,
                "yacht_id_enforced": self.security.yacht_id_enforced,
                "blocked": self.security.blocked,
            }
        }


# =============================================================================
# KNOWN LIMITATIONS (V1 HONEST ASSESSMENT)
# =============================================================================

KNOWN_LIMITATIONS = """
V1 LIMITATIONS - HONEST ASSESSMENT
===================================

1. NO CROSS-TABLE JOINS
   - Each table queried independently, merged client-side
   - Cannot do: "parts for equipment X" in single query
   - Workaround: Graph traversal via graph_nodes

2. NO TEMPORAL CONSTRAINTS IN SQL
   - "last week", "yesterday" not translated to date ranges
   - Would require: timestamp columns + date parsing
   - Current: Passed to GPT for interpretation

3. NO NUMERIC RANGE QUERIES
   - "85°C", "above 100 hours" not handled
   - RANGE operator defined but not wired
   - Need: Numeric extraction + unit normalization

4. TRIGRAM REQUIRES RPC
   - PostgREST doesn't support similarity()
   - Currently skipped in REST mode
   - Need: Dedicated RPC or fall back to ILIKE

5. VECTOR SEARCH YACHT_ID
   - hybrid_graph_search RPC filters by yacht_id
   - But search_document_chunks may not
   - Must verify RLS policy

6. NO MULTI-INTENT DECOMPOSITION YET
   - "check oil and create WO" treated as single query
   - R10 defined but not implemented
   - Need: Intent splitter in extraction

7. ENTITY SOUP DETECTION CRUDE
   - Just counts entities > 5
   - Should analyze: intent verb presence, entity coherence
   - Need: Better heuristics

8. NO TYPO CORRECTION
   - "fule fitler" → no results until TRIGRAM wave
   - Should: Normalize common typos earlier
   - Need: Alias table for common misspellings
"""


# =============================================================================
# TEST HELPERS
# =============================================================================

def validate_plan(plan: SQLPlan) -> List[str]:
    """Validate a plan against rules. Returns list of violations."""
    violations = []

    # R1: yacht_id required
    if not plan.security.get("yacht_id"):
        violations.append("R1: yacht_id missing")

    # R2: Lane capabilities
    lane_caps = LANE_CAPABILITIES[plan.lane]
    for wave in plan.waves:
        if wave not in lane_caps["waves_allowed"]:
            violations.append(f"R2: Wave {wave} not allowed for lane {plan.lane}")

    if len(plan.tables) > lane_caps["max_tables"]:
        violations.append(f"R2: Too many tables ({len(plan.tables)}) for lane {plan.lane}")

    # R9: Vector only for GPT
    if plan.vector_enabled and plan.lane != Lane.GPT:
        violations.append("R9: Vector search only allowed for GPT lane")

    return violations
