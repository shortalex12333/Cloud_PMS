"""
PREPARE STAGE: Complete Query Planning
=======================================
ALL logic happens here. SQL is just execution.

Stages:
1. LANE ASSIGNMENT    - Block, NO_LLM, GPT, UNKNOWN?
2. USER SCOPE         - What can this user access?
3. TERM EXPANSION     - Canonical, original, fuzzy variants
4. INTENT DETECTION   - What are they trying to do?
5. TABLE RANKING      - Bias scoring per table
6. COLUMN MATCHING    - What columns for what terms?
7. CONJUNCTION LOGIC  - AND/OR rules
8. CONFLICT RESOLUTION- Multiple terms, same table
9. BATCH PLANNING     - Tiers, budgets, exit conditions

Output: ExecutionPlan (no SQL yet)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum

from .column_config import TABLES, ColumnCapability
from .operators import Operator


# =============================================================================
# 1. LANE ASSIGNMENT
# =============================================================================

class Lane(Enum):
    BLOCKED = "BLOCKED"       # Query rejected
    NO_LLM = "NO_LLM"         # Regex-only, no GPT
    RULES_ONLY = "RULES_ONLY" # Pattern match, no GPT
    GPT = "GPT"               # Full GPT extraction
    UNKNOWN = "UNKNOWN"       # Unclear, needs clarification


@dataclass
class LaneDecision:
    lane: Lane
    reason: str
    block_message: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


def assign_lane(query_text: str, entities: List[Dict]) -> LaneDecision:
    """
    Decide which lane this query belongs to.

    BLOCKED: Jailbreak, injection, off-topic
    NO_LLM: Strong patterns (part numbers, fault codes)
    RULES_ONLY: Medium patterns
    GPT: Needs extraction
    UNKNOWN: Unclear, needs user clarification
    """
    query_lower = query_text.lower().strip()

    # BLOCKED patterns - comprehensive list
    blocked_patterns = [
        # Jailbreak attempts
        "ignore all", "ignore previous", "forget instructions", "forget your training",
        "system prompt", "reveal your prompt", "bypass security", "jailbreak",
        "pretend you are not", "act as if you have no", "override safety",
        "disregard previous", "new persona", "roleplay as",

        # SQL injection
        "drop table", "delete from", "truncate table", "alter table",
        "exec(", "eval(", "execute immediate", "sp_executesql",
        "or 1=1", "or '1'='1", "or \"1\"=\"1", "' or '", "\" or \"",
        "union select", "union all select", "; select", ";select",
        "' --", "\" --", "'--", "\"--", "/*", "*/", "@@version", "information_schema",
        "pg_tables", "pg_catalog", "sys.tables", "syscolumns",

        # Template injection
        "${", "{{", "}}", "<script", "</script", "javascript:",
        "onerror=", "onload=", "onclick=",

        # Command injection
        "; ls", "; cat", "; rm", "| cat", "| ls", "| rm",
        "`ls`", "`cat`", "$(ls)", "$(cat)",
    ]

    for pattern in blocked_patterns:
        if pattern in query_lower:
            return LaneDecision(
                lane=Lane.BLOCKED,
                reason=f"Blocked pattern: {pattern}",
                block_message="Query contains blocked content"
            )

    # Check entity values for injection too
    for entity in entities:
        val = str(entity.get("value", "")).lower()
        for pattern in blocked_patterns:
            if pattern in val:
                return LaneDecision(
                    lane=Lane.BLOCKED,
                    reason=f"Entity value contains blocked pattern: {pattern}",
                    block_message="Entity contains blocked content"
                )

    # NO_LLM: Strong entity patterns already extracted
    strong_types = {"PART_NUMBER", "FAULT_CODE", "EQUIPMENT_CODE", "PO_NUMBER"}
    has_strong = any(e.get("type") in strong_types for e in entities)

    if has_strong and len(query_text) < 50:
        return LaneDecision(
            lane=Lane.NO_LLM,
            reason="Strong entity pattern detected"
        )

    # UNKNOWN: Too vague or off-domain
    # Too short (unless it looks like a code)
    if len(query_text) < 3:
        return LaneDecision(
            lane=Lane.UNKNOWN,
            reason="Query too short",
            suggestions=["Please provide more detail"]
        )

    # Punctuation-only, numbers-only, or too short
    stripped = ''.join(c for c in query_text if c.isalnum())
    if len(stripped) < 2:
        return LaneDecision(
            lane=Lane.UNKNOWN,
            reason="Query has no meaningful content",
            suggestions=["Please describe what you're looking for"]
        )

    # Numbers-only (unless it looks like a code with letters)
    if stripped.isdigit() and len(stripped) < 6:
        return LaneDecision(
            lane=Lane.UNKNOWN,
            reason="Query is just a number",
            suggestions=["Please include equipment name or part description"]
        )

    # Domain drift detection - non-marine queries
    off_domain_patterns = [
        "meaning of life", "tell me a joke", "write me a poem",
        "how do i cook", "what is the weather", "what's the weather",
        "who is the president", "who's the president",
        "what time is it", "what's the time", "translate this", "write code for",
        "help me with homework", "explain quantum", "recipe for",
        "tell me about", "what do you think", "how are you"
    ]
    for pattern in off_domain_patterns:
        if pattern in query_lower:
            return LaneDecision(
                lane=Lane.UNKNOWN,
                reason="Query appears off-domain",
                suggestions=["I can help with marine equipment, parts, faults, and maintenance"]
            )

    # Long gibberish/paste dump detection
    if len(query_text) > 100:
        # High ratio of non-alphanumeric chars suggests garbage
        alpha_ratio = sum(1 for c in query_text if c.isalpha()) / len(query_text)
        if alpha_ratio < 0.5:
            return LaneDecision(
                lane=Lane.UNKNOWN,
                reason="Query appears to be unstructured text",
                suggestions=["Please enter a specific search term"]
            )

    # No entities and no recognizable marine keywords
    if not entities:
        marine_keywords = [
            "engine", "generator", "pump", "filter", "valve", "bearing",
            "seal", "belt", "impeller", "injector", "turbo", "exhaust",
            "fuel", "oil", "coolant", "hydraulic", "electrical", "thruster",
            "stabilizer", "anchor", "windlass", "watermaker", "hvac",
            "fault", "error", "alarm", "warning", "part", "maintenance"
        ]
        has_marine = any(kw in query_lower for kw in marine_keywords)
        if not has_marine and len(query_text) > 20:
            return LaneDecision(
                lane=Lane.UNKNOWN,
                reason="No recognizable marine content",
                suggestions=["Try searching for equipment, parts, or fault codes"]
            )

    # Default: GPT
    return LaneDecision(
        lane=Lane.GPT,
        reason="Standard query, GPT extraction recommended"
    )


# =============================================================================
# 2. USER SCOPE
# =============================================================================

@dataclass
class UserScope:
    user_id: str
    yacht_ids: List[str]           # Which yachts can they access
    allowed_tables: Set[str]       # Which tables can they query
    role: str                      # crew, engineer, captain, admin
    max_results: int = 100         # Result limit


def resolve_user_scope(
    user_id: str,
    yacht_id: str,
    role: str = "crew"
) -> UserScope:
    """
    Determine what this user can access.

    In production, this would query permissions table.
    For now, yacht_id scoping is enforced.
    """
    # All tables accessible to authenticated users
    all_tables = set(TABLES.keys())

    # Role-based restrictions (example)
    if role == "crew":
        # Crew can't see purchase orders
        all_tables.discard("pms_purchase_orders")

    return UserScope(
        user_id=user_id,
        yacht_ids=[yacht_id],  # Currently single yacht
        allowed_tables=all_tables,
        role=role,
        max_results=100 if role == "admin" else 50
    )


# =============================================================================
# 3. TERM EXPANSION
# =============================================================================

@dataclass
class TermVariant:
    form: str           # canonical, original, fuzzy
    value: str
    operator: Operator
    priority: int       # Lower = try first


@dataclass
class ExpandedTerm:
    entity_type: str
    original_value: str
    confidence: float
    variants: List[TermVariant]


def expand_terms(entities: List[Dict]) -> List[ExpandedTerm]:
    """
    Generate variants for each entity.

    Variants:
    - canonical: UPPERCASE, exact match (Wave 0)
    - original: as-typed, pattern match (Wave 1)
    - fuzzy: %wrapped%, broad match (Wave 1)
    - trigram: lowercase, similarity match (Wave 2)
    - prefix: starts-with pattern (Wave 1)
    - normalized: strip special chars (Wave 0/1)
    """
    expanded = []

    for entity in entities:
        entity_type = entity.get("type", "UNKNOWN")
        value = entity.get("value", "").strip()
        confidence = entity.get("confidence", 1.0)

        if not value:
            continue

        # Normalize: strip special chars for codes
        normalized = ''.join(c for c in value if c.isalnum() or c.isspace()).strip()

        variants = [
            # Wave 0: EXACT
            TermVariant(
                form="canonical",
                value=value.upper(),
                operator=Operator.EXACT,
                priority=1
            ),
            # Wave 1: ILIKE
            TermVariant(
                form="original",
                value=value,
                operator=Operator.ILIKE,
                priority=2
            ),
            TermVariant(
                form="fuzzy",
                value=f"%{value}%",
                operator=Operator.ILIKE,
                priority=3
            ),
            TermVariant(
                form="prefix",
                value=f"{value}%",
                operator=Operator.ILIKE,
                priority=4
            ),
            # Wave 2: TRIGRAM
            TermVariant(
                form="trigram",
                value=value.lower(),
                operator=Operator.TRIGRAM,
                priority=5
            ),
        ]

        # Add normalized variant if different from original
        if normalized.upper() != value.upper():
            variants.insert(1, TermVariant(
                form="normalized",
                value=normalized.upper(),
                operator=Operator.EXACT,
                priority=1
            ))

        expanded.append(ExpandedTerm(
            entity_type=entity_type,
            original_value=value,
            confidence=confidence,
            variants=variants
        ))

    return expanded


# =============================================================================
# 4. INTENT DETECTION
# =============================================================================

class Intent(Enum):
    LOOKUP = "lookup"           # Find specific item
    SEARCH = "search"           # Broad search
    CHECK_STATUS = "check_status"  # Status check
    DIAGNOSE = "diagnose"       # Fault diagnosis
    ORDER = "order"             # Ordering/procurement


# Intent → Table priority boost
INTENT_TABLE_BOOST = {
    Intent.LOOKUP: {"pms_parts": 0.5, "pms_equipment": 0.5},
    Intent.CHECK_STATUS: {"pms_work_orders": 0.5, "pms_purchase_orders": 0.3},
    Intent.DIAGNOSE: {"pms_faults": 0.5, "symptom_aliases": 0.3},
    Intent.ORDER: {"pms_purchase_orders": 0.5, "pms_suppliers": 0.3},
}


def detect_intent(query_text: str, entities: List[Dict]) -> Intent:
    """
    Detect user intent from query and entities.
    """
    query_lower = query_text.lower()

    # Keyword matching
    if any(w in query_lower for w in ["status", "where is", "track"]):
        return Intent.CHECK_STATUS
    if any(w in query_lower for w in ["fault", "error", "problem", "diagnose"]):
        return Intent.DIAGNOSE
    if any(w in query_lower for w in ["order", "buy", "purchase"]):
        return Intent.ORDER

    # Entity-based
    entity_types = {e.get("type") for e in entities}
    if entity_types & {"FAULT_CODE", "SYMPTOM"}:
        return Intent.DIAGNOSE
    if entity_types & {"PART_NUMBER", "EQUIPMENT_CODE"}:
        return Intent.LOOKUP

    return Intent.SEARCH


# =============================================================================
# 5. TABLE RANKING (Bias Scoring)
# =============================================================================

# Entity type → Primary tables
ENTITY_PRIMARY_TABLES = {
    "PART_NUMBER": ["pms_parts"],
    "PART_NAME": ["pms_parts"],
    "EQUIPMENT_NAME": ["pms_equipment", "graph_nodes"],
    "EQUIPMENT_CODE": ["pms_equipment"],
    "FAULT_CODE": ["pms_faults", "search_fault_code_catalog"],
    "SYMPTOM": ["symptom_aliases", "pms_faults"],
    "SUPPLIER_NAME": ["pms_suppliers"],
    "MANUFACTURER": ["pms_parts", "pms_suppliers", "pms_equipment"],
    "PO_NUMBER": ["pms_purchase_orders"],
    "LOCATION": ["pms_equipment", "pms_parts"],
    "SYSTEM_NAME": ["pms_equipment", "graph_nodes"],
}


@dataclass
class TableScore:
    table: str
    bias: float
    reasons: List[str]
    matched_columns: List[str]
    operators: Set[Operator]


def rank_tables(
    terms: List[ExpandedTerm],
    intent: Intent,
    user_scope: UserScope
) -> List[TableScore]:
    """
    Compute bias score for each table.

    Scoring:
    +2.0 if table is primary for entity type
    +1.0 if table supports EXACT match
    +0.5 if intent boosts this table
    +0.3 per additional column match
    -1.0 if user doesn't have permission
    × confidence weight
    """
    scores = {}

    for table_name, table_cfg in TABLES.items():
        # Permission check
        if table_name not in user_scope.allowed_tables:
            continue

        bias = 0.0
        reasons = []
        matched_columns = []
        operators = set()

        for term in terms:
            # Primary table bonus
            primaries = ENTITY_PRIMARY_TABLES.get(term.entity_type, [])
            if table_name in primaries:
                bias += 2.0
                reasons.append(f"{term.entity_type} primary")

            # Column matching
            for col_name, col_cfg in table_cfg.columns.items():
                if term.entity_type in col_cfg.entity_types:
                    matched_columns.append(col_name)
                    operators.update(col_cfg.operators)

                    if Operator.EXACT in col_cfg.operators:
                        bias += 1.0
                        reasons.append(f"EXACT on {col_name}")
                    else:
                        bias += 0.3
                        reasons.append(f"ILIKE on {col_name}")

        # Intent boost
        if intent in INTENT_TABLE_BOOST:
            boost = INTENT_TABLE_BOOST[intent].get(table_name, 0)
            if boost:
                bias += boost
                reasons.append(f"intent={intent.value}")

        # Confidence weighting
        if terms:
            avg_confidence = sum(t.confidence for t in terms) / len(terms)
            bias *= avg_confidence

        if bias > 0:
            scores[table_name] = TableScore(
                table=table_name,
                bias=round(bias, 2),
                reasons=reasons,
                matched_columns=list(set(matched_columns)),
                operators=operators
            )

    # Sort by bias descending
    return sorted(scores.values(), key=lambda x: x.bias, reverse=True)


# =============================================================================
# 6. COLUMN MATCHING
# =============================================================================

@dataclass
class ColumnMatch:
    table: str
    column: str
    entity_type: str
    operators: List[Operator]
    isolated_ok: bool
    conjunction_only: bool


def match_columns(
    terms: List[ExpandedTerm],
    ranked_tables: List[TableScore]
) -> Dict[str, List[ColumnMatch]]:
    """
    For each term, find matching columns in ranked tables.
    Returns: {entity_type: [ColumnMatch, ...]}
    """
    matches = {}

    for term in terms:
        term_matches = []

        for table_score in ranked_tables:
            table_cfg = TABLES.get(table_score.table)
            if not table_cfg:
                continue

            for col_name, col_cfg in table_cfg.columns.items():
                if term.entity_type in col_cfg.entity_types:
                    term_matches.append(ColumnMatch(
                        table=table_score.table,
                        column=col_name,
                        entity_type=term.entity_type,
                        operators=col_cfg.operators,
                        isolated_ok=col_cfg.isolated_ok,
                        conjunction_only=col_cfg.conjunction_only
                    ))

        matches[term.entity_type] = term_matches

    return matches


# =============================================================================
# 7. CONJUNCTION LOGIC
# =============================================================================

class ConjunctionRule(Enum):
    OR_VARIANTS = "or_variants"      # Same term, different forms
    AND_TERMS = "and_terms"          # Different terms
    REQUIRE_ANCHOR = "require_anchor"  # conjunction_only needs partner


@dataclass
class ConjunctionPlan:
    rule: ConjunctionRule
    groups: List[List[str]]  # Groups of entity types
    requires_anchor: List[str]  # Entity types that need anchor


def plan_conjunction(
    terms: List[ExpandedTerm],
    column_matches: Dict[str, List[ColumnMatch]]
) -> ConjunctionPlan:
    """
    Determine AND/OR logic for terms.

    Rules:
    - Multiple variants of same term: OR
    - Multiple different terms: AND
    - conjunction_only columns: require anchor term
    """
    groups = []
    requires_anchor = []

    # Check for conjunction_only terms
    for term in terms:
        matches = column_matches.get(term.entity_type, [])
        all_conjunction = all(m.conjunction_only for m in matches)

        if all_conjunction:
            requires_anchor.append(term.entity_type)

    # If ALL terms require anchor, we can't proceed
    if len(requires_anchor) == len(terms):
        # All need anchor - this is a problem
        pass

    # Group terms that can combine
    # For now: all terms in one AND group
    groups = [[t.entity_type for t in terms]]

    return ConjunctionPlan(
        rule=ConjunctionRule.AND_TERMS if len(terms) > 1 else ConjunctionRule.OR_VARIANTS,
        groups=groups,
        requires_anchor=requires_anchor
    )


# =============================================================================
# 8. CONFLICT RESOLUTION
# =============================================================================

@dataclass
class ResolvedQuery:
    """Query for a single table with all terms combined."""
    table: str
    conditions: List[Dict]  # [{column, operator, variants, entity_type}]
    conjunction: str        # "AND" or "OR"


def resolve_conflicts(
    terms: List[ExpandedTerm],
    column_matches: Dict[str, List[ColumnMatch]],
    ranked_tables: List[TableScore]
) -> List[ResolvedQuery]:
    """
    Combine multiple terms targeting same table.

    Example:
    - PART_NAME: "fuel filter" → pms_parts.name
    - MANUFACTURER: "MTU" → pms_parts.manufacturer

    Result:
    - pms_parts: name ILIKE '%fuel filter%' AND manufacturer ILIKE '%MTU%'
    """
    queries = []

    for table_score in ranked_tables:
        table = table_score.table
        conditions = []

        for term in terms:
            matches = column_matches.get(term.entity_type, [])
            table_matches = [m for m in matches if m.table == table]

            for match in table_matches:
                conditions.append({
                    "column": match.column,
                    "operators": match.operators,
                    "variants": term.variants,
                    "entity_type": term.entity_type
                })

        if conditions:
            queries.append(ResolvedQuery(
                table=table,
                conditions=conditions,
                conjunction="AND"  # Multiple terms = AND
            ))

    return queries


# =============================================================================
# 9. BATCH PLANNING
# =============================================================================

TIER_THRESHOLDS = [(1, 2.0), (2, 1.5), (3, 1.0)]
TIER_BUDGETS = {1: 250, 2: 300, 3: 250}


@dataclass
class BatchPlan:
    tier: int
    tables: List[str]
    budget_ms: int
    wave_order: List[Operator]  # EXACT → ILIKE → TRIGRAM


@dataclass
class ExitCondition:
    strong_hit_count: int = 5      # Exit if >= N exact hits
    score_threshold: float = 0.9   # Exit if top score > X
    max_time_ms: int = 800         # Total budget


def plan_batches(
    ranked_tables: List[TableScore]
) -> Tuple[List[BatchPlan], ExitCondition]:
    """
    Organize tables into tiers with budgets.
    """
    batches = []

    for tier_num, threshold in TIER_THRESHOLDS:
        if tier_num == 1:
            tier_tables = [t.table for t in ranked_tables if t.bias >= threshold]
        elif tier_num == 2:
            tier_tables = [t.table for t in ranked_tables if 1.5 <= t.bias < 2.0]
        else:
            tier_tables = [t.table for t in ranked_tables if 1.0 <= t.bias < 1.5]

        if tier_tables:
            batches.append(BatchPlan(
                tier=tier_num,
                tables=tier_tables,
                budget_ms=TIER_BUDGETS[tier_num],
                wave_order=[Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM]
            ))

    exit_cond = ExitCondition()

    return batches, exit_cond


# =============================================================================
# MAIN: Complete Prepare Stage
# =============================================================================

@dataclass
class ExecutionPlan:
    """Complete execution plan - ready for SQL generation."""
    # Lane
    lane: LaneDecision

    # Scope
    user_scope: UserScope

    # Terms
    expanded_terms: List[ExpandedTerm]

    # Intent
    intent: Intent

    # Ranking
    ranked_tables: List[TableScore]

    # Matching
    column_matches: Dict[str, List[ColumnMatch]]

    # Conjunction
    conjunction_plan: ConjunctionPlan

    # Resolved queries (per table)
    resolved_queries: List[ResolvedQuery]

    # Batches
    batches: List[BatchPlan]
    exit_conditions: ExitCondition

    # Debug
    trace: Dict[str, Any]


def prepare(
    query_text: str,
    entities: List[Dict],
    yacht_id: str,
    user_id: str,
    user_role: str = "crew"
) -> ExecutionPlan:
    """
    COMPLETE PREPARE STAGE.

    All logic happens here. Output is ready for SQL generation.
    """
    trace = {"stages": []}

    # 1. Lane assignment
    lane = assign_lane(query_text, entities)
    trace["stages"].append({"lane": lane.lane.value, "reason": lane.reason})

    if lane.lane == Lane.BLOCKED:
        return ExecutionPlan(
            lane=lane,
            user_scope=UserScope(user_id, [], set(), user_role),
            expanded_terms=[],
            intent=Intent.SEARCH,
            ranked_tables=[],
            column_matches={},
            conjunction_plan=ConjunctionPlan(ConjunctionRule.OR_VARIANTS, [], []),
            resolved_queries=[],
            batches=[],
            exit_conditions=ExitCondition(),
            trace=trace
        )

    # 2. User scope
    user_scope = resolve_user_scope(user_id, yacht_id, user_role)
    trace["stages"].append({"scope": {
        "yacht_ids": user_scope.yacht_ids,
        "allowed_tables": list(user_scope.allowed_tables)
    }})

    # 3. Term expansion
    terms = expand_terms(entities)
    trace["stages"].append({"terms": [
        {"type": t.entity_type, "value": t.original_value, "variants": len(t.variants)}
        for t in terms
    ]})

    # 4. Intent detection
    intent = detect_intent(query_text, entities)
    trace["stages"].append({"intent": intent.value})

    # 5. Table ranking
    ranked_tables = rank_tables(terms, intent, user_scope)
    trace["stages"].append({"ranking": [
        {"table": t.table, "bias": t.bias, "reasons": t.reasons}
        for t in ranked_tables[:5]
    ]})

    # 6. Column matching
    column_matches = match_columns(terms, ranked_tables)
    trace["stages"].append({"column_matches": {
        k: len(v) for k, v in column_matches.items()
    }})

    # 7. Conjunction planning
    conjunction = plan_conjunction(terms, column_matches)
    trace["stages"].append({"conjunction": conjunction.rule.value})

    # 8. Conflict resolution
    resolved = resolve_conflicts(terms, column_matches, ranked_tables)
    trace["stages"].append({"resolved_queries": len(resolved)})

    # 9. Batch planning
    batches, exit_cond = plan_batches(ranked_tables)
    trace["stages"].append({"batches": [
        {"tier": b.tier, "tables": b.tables} for b in batches
    ]})

    return ExecutionPlan(
        lane=lane,
        user_scope=user_scope,
        expanded_terms=terms,
        intent=intent,
        ranked_tables=ranked_tables,
        column_matches=column_matches,
        conjunction_plan=conjunction,
        resolved_queries=resolved,
        batches=batches,
        exit_conditions=exit_cond,
        trace=trace
    )
