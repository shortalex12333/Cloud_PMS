"""
Result Ranker v1 - Intelligent Scoring & Ranking
================================================

Philosophy:
- Vague queries ("fuel injector MTU"): Treat all domains equally, surface everything
- Explicit intent ("MTU document manual"): Boost target domain heavily
- Diagnostic queries ("main engine overheating again"): Handover > Manual > Parts
- Apple Spotlight UX: Group by domain, cascade ranks, infinite scroll

Scoring Formula:
  Score = MatchTier (1000/900/800/500/300)
        + ConjunctionBonus (0-200)
        + EntityConfidence (0-150)
        + IntentTablePrior (-100 to +150)
        + RecencyBonus (0-100)
        - NoisePenalties (0-200)

Match Mode Hierarchy:
  EXACT_ID: 1000        (part_number exact match)
  EXACT_CANONICAL: 900  (normalized match like "BOX_2D" → "box 2d")
  EXACT_TEXT: 800       (name/description exact)
  FUZZY: 500            (ILIKE pattern match)
  VECTOR: 300           (semantic similarity)
"""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class MatchMode(Enum):
    """Match quality tiers - hard tiering prevents fuzzy/vector from beating exact."""
    EXACT_ID = 1000          # Exact identifier match (part_number, fault_code, etc.)
    EXACT_CANONICAL = 900    # Canonical/normalized match
    EXACT_TEXT = 800         # Exact text match in name/title
    FUZZY = 500              # Pattern/ILIKE match
    VECTOR = 300             # Semantic/embedding similarity
    UNKNOWN = 0              # Fallback


@dataclass
class ScoringContext:
    """Context needed for scoring a result."""
    query_text: str
    entities: List[Dict[str, Any]]
    intent_signals: Set[str] = field(default_factory=set)
    is_diagnostic: bool = False
    is_vague: bool = True
    entity_count: int = 0


@dataclass
class ScoreComponents:
    """Breakdown of score for observability."""
    match_tier: int = 0
    match_mode: str = "UNKNOWN"
    conjunction_bonus: int = 0
    proximity_bonus: int = 0  # NEW: From RAG Stage 4
    entity_confidence: int = 0
    intent_table_prior: int = 0
    recency_bonus: int = 0
    catalog_penalty: int = 0  # NEW: From RAG Stage 4
    noise_penalty: int = 0
    matched_entities: List[str] = field(default_factory=list)
    matched_columns: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Calculate total score."""
        return (
            self.match_tier
            + self.conjunction_bonus
            + self.proximity_bonus
            + self.entity_confidence
            + self.intent_table_prior
            + self.recency_bonus
            - self.catalog_penalty
            - self.noise_penalty
        )


# =============================================================================
# INTENT DETECTION
# =============================================================================

def detect_intent_signals(query_text: str) -> Set[str]:
    """
    Detect intent signals from query text.

    Returns set of intent keywords: {'manual', 'history', 'fault', 'inventory', etc.}
    """
    query_lower = query_text.lower()

    signals = set()

    # Document/manual intent
    if re.search(r'\b(manual|document|documentation|procedure|guide|handbook)\b', query_lower):
        signals.add('manual')

    # History/handover intent
    if re.search(r'\b(history|previous|last|again|handover|log|entry)\b', query_lower):
        signals.add('history')

    # Fault/diagnostic intent
    if re.search(r'\b(fault|error|diagnose|diagnostic|troubleshoot|fix|repair)\b', query_lower):
        signals.add('fault')

    # Inventory/stock intent
    if re.search(r'\b(inventory|stock|quantity|available|warehouse|storage)\b', query_lower):
        signals.add('inventory')

    # Parts/ordering intent
    if re.search(r'\b(part|order|purchase|buy|component)\b', query_lower):
        signals.add('part')

    # Equipment intent
    if re.search(r'\b(equipment|machine|system|unit|device)\b', query_lower):
        signals.add('equipment')

    return signals


def is_query_vague(query_text: str, entity_count: int) -> bool:
    """
    Determine if query is vague (no clear intent).

    Vague queries: "fuel injector MTU", "pump"
    Clear queries: "MTU document manual", "main engine overheating again"
    """
    query_lower = query_text.lower()

    # If query has explicit intent keywords, it's not vague
    intent_keywords = [
        'manual', 'document', 'history', 'handover', 'previous',
        'last', 'again', 'fault', 'error', 'diagnose', 'inventory'
    ]

    for keyword in intent_keywords:
        if re.search(rf'\b{keyword}\b', query_lower):
            return False

    # If query is very short with few entities, it's vague
    if len(query_text.split()) <= 3 and entity_count <= 2:
        return True

    return True  # Default to vague (receptionist mode)


def is_diagnostic_query(query_text: str, entities: List[Dict[str, Any]]) -> bool:
    """
    Detect if query is diagnostic (symptom + equipment).

    Examples:
    - "main engine overheating again"
    - "stern thruster making noise"
    - "generator won't start"
    """
    query_lower = query_text.lower()

    # Check for symptom keywords
    symptoms = [
        'overheating', 'leaking', 'smoking', 'vibrating', 'noise',
        'won\'t start', 'cutting out', 'stalling', 'surging'
    ]

    has_symptom = any(symptom in query_lower for symptom in symptoms)

    # Check for equipment entities
    has_equipment = any(e.get('type') in ['EQUIPMENT', 'SYSTEM'] for e in entities)

    # Check for "again" or "previous" (indicates recurring issue)
    has_recurrence = 'again' in query_lower or 'previous' in query_lower

    return has_symptom or (has_equipment and has_recurrence)


def create_scoring_context(query_text: str, entities: List[Dict[str, Any]]) -> ScoringContext:
    """Create scoring context from query and entities."""
    intent_signals = detect_intent_signals(query_text)
    entity_count = len(entities)

    return ScoringContext(
        query_text=query_text,
        entities=entities,
        intent_signals=intent_signals,
        is_diagnostic=is_diagnostic_query(query_text, entities),
        is_vague=is_query_vague(query_text, entity_count),
        entity_count=entity_count,
    )


# =============================================================================
# INTENT-TABLE PRIORS
# =============================================================================

def calculate_intent_table_prior(
    source_table: str,
    source_capability: str,
    context: ScoringContext,
) -> int:
    """
    Calculate intent-table prior based on query intent and result source.

    Returns: -100 to +150

    Philosophy:
    - Vague queries: All tables get 0 (equal treatment)
    - Explicit intent: Target tables get +100 to +150
    - Diagnostic queries: Handovers > Manual > Parts
    """
    # If query is vague, no bias (receptionist mode)
    if context.is_vague and not context.intent_signals:
        return 0

    # Map source to domain
    domain = _map_table_to_domain(source_table, source_capability)

    # DIAGNOSTIC QUERIES: "main engine overheating again"
    if context.is_diagnostic:
        # Priority: handover > manual > parts
        if domain == 'handovers':
            return 150  # Highest - previous fault history is critical
        elif domain == 'documents':
            return 100  # Second - manual diagnostic procedures
        elif domain == 'parts':
            return 50   # Third - related parts for repair
        elif domain == 'faults':
            return 120  # Fault catalog also very relevant
        else:
            return 0

    # EXPLICIT INTENT SIGNALS
    prior = 0

    # Manual/document intent: "MTU document manual"
    if 'manual' in context.intent_signals:
        if domain == 'documents':
            prior += 150
        elif domain == 'parts':
            prior += 30  # Parts manuals also relevant
        else:
            prior -= 50

    # History intent: "previous fault", "last time"
    if 'history' in context.intent_signals:
        if domain == 'handovers':
            prior += 150
        elif domain == 'faults':
            prior += 100
        elif domain == 'work_orders':
            prior += 80
        else:
            prior -= 30

    # Fault intent: "diagnose fault E122"
    if 'fault' in context.intent_signals:
        if domain == 'faults':
            prior += 150
        elif domain == 'documents':
            prior += 80
        elif domain == 'handovers':
            prior += 70
        else:
            prior -= 20

    # Inventory intent: "check stock"
    if 'inventory' in context.intent_signals:
        if domain == 'inventory':
            prior += 150
        elif domain == 'parts':
            prior += 50
        else:
            prior -= 50

    # Parts intent: "order fuel injector"
    if 'part' in context.intent_signals:
        if domain == 'parts':
            prior += 150
        elif domain == 'inventory':
            prior += 80
        else:
            prior -= 30

    # Equipment intent
    if 'equipment' in context.intent_signals:
        if domain == 'equipment':
            prior += 150
        elif domain == 'systems':
            prior += 100
        else:
            prior -= 20

    # Cap at bounds
    return max(-100, min(150, prior))


def _map_table_to_domain(table_name: str, capability_name: str) -> str:
    """Map table/capability to domain for intent matching."""
    domain_mapping = {
        'pms_parts': 'parts',
        'v_inventory': 'inventory',
        'search_fault_code_catalog': 'faults',
        'search_document_chunks': 'documents',
        'pms_equipment': 'equipment',
        'graph_nodes': 'systems',
        'pms_work_orders': 'work_orders',
        'pms_maintenance_log': 'handovers',
        'pms_handover_entries': 'handovers',

        # Capability-based mapping
        'part_by_part_number_or_name': 'parts',
        'inventory_by_location': 'inventory',
        'fault_by_fault_code': 'faults',
        'documents_search': 'documents',
        'equipment_by_name_or_model': 'equipment',
        'graph_node_search': 'systems',
        'work_order_by_id': 'work_orders',
    }

    return domain_mapping.get(table_name) or domain_mapping.get(capability_name, 'other')


# =============================================================================
# MATCH MODE DETECTION
# =============================================================================

def detect_match_mode(
    result: Dict[str, Any],
    entities: List[Dict[str, Any]],
    source_table: str,
) -> MatchMode:
    """
    Detect how the result matched the query.

    Priority:
    1. Check if primary ID columns match exactly (EXACT_ID)
    2. Check if canonical normalization was used (EXACT_CANONICAL)
    3. Check if name/title matched exactly (EXACT_TEXT)
    4. Check score_components for similarity/fuzzy (VECTOR/FUZZY)
    5. Default to FUZZY
    """
    # Get existing score components if available
    score_comp = result.get('score_components', {})

    # EXACT_ID: Check primary identifier columns
    id_columns = ['part_number', 'code', 'fault_code', 'equipment_code', 'work_order_id']
    for col in id_columns:
        if col in result:
            result_value = str(result[col]).lower().strip()
            for entity in entities:
                entity_value = str(entity.get('value', '')).lower().strip()
                if result_value == entity_value:
                    return MatchMode.EXACT_ID

    # EXACT_CANONICAL: Check if canonical match flag exists
    if score_comp.get('exact_match') == 1.0:
        return MatchMode.EXACT_CANONICAL

    if score_comp.get('code_match') == 1.0:
        return MatchMode.EXACT_ID

    # VECTOR: Check for similarity score from vector search
    if 'similarity' in score_comp:
        similarity = score_comp.get('similarity', 0)
        if similarity > 0.8:
            return MatchMode.EXACT_TEXT
        else:
            return MatchMode.VECTOR

    # EXACT_TEXT: Check if name/title matches exactly
    text_columns = ['name', 'title', 'label']
    for col in text_columns:
        if col in result:
            result_text = str(result[col]).lower().strip()
            for entity in entities:
                entity_value = str(entity.get('value', '')).lower().strip()
                if entity_value in result_text or result_text in entity_value:
                    if len(entity_value) > 3:  # Avoid short token false positives
                        return MatchMode.EXACT_TEXT

    # Default: FUZZY (ILIKE pattern matching)
    return MatchMode.FUZZY


# =============================================================================
# CONJUNCTION BONUS
# =============================================================================

def calculate_conjunction_bonus(
    result: Dict[str, Any],
    entities: List[Dict[str, Any]],
) -> tuple[int, List[str]]:
    """
    Calculate conjunction bonus when multiple entities match same result.

    Returns: (bonus_score, matched_entity_values)

    Examples:
    - "fuel filter main engine" → both "fuel filter" AND "main engine" in same row = +150
    - "MTU generator" → both "MTU" AND "generator" = +100
    - Single entity match = 0
    """
    if len(entities) <= 1:
        return 0, []

    # Flatten result values for matching
    result_text = ' '.join(str(v).lower() for v in result.values() if v)

    matched_entities = []
    for entity in entities:
        entity_value = str(entity.get('value', '')).lower().strip()
        if entity_value and entity_value in result_text:
            matched_entities.append(entity_value)

    match_count = len(matched_entities)

    # Bonus scaling
    if match_count >= 3:
        return 200, matched_entities  # Cap at 200
    elif match_count == 2:
        return 150, matched_entities
    elif match_count == 1:
        return 0, matched_entities
    else:
        return 0, []


# =============================================================================
# PROXIMITY BONUS (From RAG Stage 4)
# =============================================================================

def calculate_proximity_bonus(
    result: Dict[str, Any],
    entities: List[Dict[str, Any]],
    matched_entities: List[str],
) -> int:
    """
    Calculate proximity bonus when matched entities appear close together.

    Technique from RAG Stage 4: Entities clustered together indicate more relevant content.

    Args:
        result: Result dictionary
        entities: Entity list
        matched_entities: Entities that matched (from conjunction bonus)

    Returns:
        Proximity bonus (0-100)

    Examples:
        - "MTU generator" → "MTU" at position 10, "generator" at position 15 → high bonus
        - "MTU ... [500 chars] ... generator" → low bonus (scattered)
    """
    if len(matched_entities) < 2:
        return 0  # Need at least 2 entities for proximity

    # Flatten result to single searchable text
    result_text = ' '.join(str(v).lower() for v in result.values() if v)

    # Find positions of each matched entity
    entity_positions = []
    for entity_value in matched_entities:
        pos = result_text.find(entity_value.lower())
        if pos != -1:
            entity_positions.append(pos)

    if len(entity_positions) < 2:
        return 0

    # Calculate average gap between consecutive entities
    entity_positions.sort()
    gaps = [entity_positions[i+1] - entity_positions[i]
            for i in range(len(entity_positions) - 1)]
    avg_gap = sum(gaps) / len(gaps)

    # Proximity scoring: smaller gap = higher bonus
    # Formula: 1000 / (avg_gap + 10) gives max ~100 for very small gaps
    # Scale down for reasonable values (max 100)
    proximity_bonus = min(100, int(1000 / (avg_gap + 10)))

    return proximity_bonus


# =============================================================================
# ENTITY CONFIDENCE
# =============================================================================

def calculate_entity_confidence_boost(
    matched_entities: List[str],
    entities: List[Dict[str, Any]],
) -> int:
    """
    Boost based on entity extraction confidence.

    Returns: 0-150
    """
    if not matched_entities:
        return 0

    total_confidence = 0.0
    count = 0

    for entity in entities:
        entity_value = str(entity.get('value', '')).lower().strip()
        if entity_value in matched_entities:
            confidence = entity.get('confidence', 0.5)
            total_confidence += confidence
            count += 1

    if count == 0:
        return 0

    avg_confidence = total_confidence / count

    # Scale 0.0-1.0 → 0-150
    return int(avg_confidence * 150)


# =============================================================================
# RECENCY BONUS
# =============================================================================

def calculate_recency_bonus(result: Dict[str, Any], source_table: str) -> int:
    """
    Calculate recency bonus (table-specific).

    Returns: 0-100

    Tables where recency matters:
    - work_orders, faults, handovers: High (0-100)
    - documents: Medium (0-50)
    - parts catalog: Low (0-20)
    """
    from datetime import datetime, timezone

    # Get recency importance by table
    recency_weights = {
        'pms_work_orders': 100,
        'pms_maintenance_log': 100,
        'pms_handover_entries': 100,
        'search_fault_code_catalog': 80,
        'search_document_chunks': 50,
        'v_inventory': 40,
        'pms_equipment': 30,
        'pms_parts': 20,
    }

    max_bonus = recency_weights.get(source_table, 30)

    # Try to find timestamp columns
    timestamp_columns = [
        'created_at', 'updated_at', 'timestamp',
        'fault_timestamp', 'logged_at', 'completed_at'
    ]

    result_time = None
    for col in timestamp_columns:
        if col in result and result[col]:
            try:
                result_time = result[col]
                if isinstance(result_time, str):
                    result_time = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
                break
            except:
                continue

    if not result_time:
        return 0

    # Calculate age in days
    now = datetime.now(timezone.utc)
    age_days = (now - result_time).days

    # Decay function: newer = higher bonus
    if age_days < 1:
        return max_bonus
    elif age_days < 7:
        return int(max_bonus * 0.8)
    elif age_days < 30:
        return int(max_bonus * 0.5)
    elif age_days < 90:
        return int(max_bonus * 0.3)
    else:
        return int(max_bonus * 0.1)


# =============================================================================
# CATALOG/TOC DETECTION (From RAG Stage 4)
# =============================================================================

def detect_catalog_penalty(
    result: Dict[str, Any],
    source_table: str,
    context: 'ScoringContext',
) -> int:
    """
    Detect and penalize catalog/TOC results without actual answers.

    Technique from RAG Stage 4: Prevent parts lists and TOCs from outranking actual procedures.

    Returns: Penalty (0-150)

    Examples:
        - "Table of Contents" → -150 penalty
        - "Parts Catalog" → -100 penalty
        - "Spare Parts List" → -80 penalty
        - Normal result → 0 penalty
    """
    penalty = 0

    # Get searchable text fields
    name = str(result.get('name', '')).lower()
    description = str(result.get('description', '')).lower()
    title = str(result.get('title', '')).lower()
    combined_text = f"{name} {description} {title}"

    # AGGRESSIVE PENALTY: TOC markers
    toc_markers = [
        'table of contents', 'index page', 'contents page',
        'table des matières', 'índice'  # Multi-language support
    ]
    for marker in toc_markers:
        if marker in combined_text:
            return 150  # Nuclear penalty - immediate return

    # STRONG PENALTY: Catalog indicators
    catalog_markers = [
        'parts catalog', 'parts list', 'spare parts list',
        'inventory catalog', 'catalog page', 'parts index'
    ]
    for marker in catalog_markers:
        if marker in combined_text:
            penalty += 100

    # MODERATE PENALTY: List patterns without procedural content
    # Check for numbered list patterns (e.g., "1. Item A\n2. Item B")
    list_pattern = re.search(r'^\s*[\d]+\..*\n\s*[\d]+\.', combined_text, re.MULTILINE)
    if list_pattern:
        # Check if it has procedural words (step, install, replace, etc.)
        procedural_words = ['step', 'procedure', 'install', 'replace', 'remove', 'check', 'inspect']
        has_procedure = any(word in combined_text for word in procedural_words)

        if not has_procedure:
            penalty += 50  # List without procedure = likely TOC/catalog

    # TABLE-SPECIFIC PENALTIES
    # Parts table results are inherently catalog-like unless they have context
    if source_table == 'pms_parts':
        # Check if description has actual guidance
        guidance_words = ['use', 'replace', 'install', 'when', 'if', 'because', 'ensure']
        has_guidance = any(word in description for word in guidance_words)

        if not has_guidance and len(description.split()) < 10:
            penalty += 30  # Short description without guidance = pure catalog entry

    # If query has explicit intent for manuals/procedures, reduce catalog penalty
    if 'manual' in context.intent_signals or 'fault' in context.intent_signals:
        # User wants documentation, not catalogs - keep penalty
        pass
    elif 'part' in context.intent_signals or 'inventory' in context.intent_signals:
        # User wants catalog results - reduce penalty
        penalty = int(penalty * 0.3)

    return min(penalty, 150)


# =============================================================================
# NOISE PENALTIES
# =============================================================================

def calculate_noise_penalty(
    result: Dict[str, Any],
    matched_columns: List[str],
    entities: List[Dict[str, Any]],
) -> int:
    """
    Penalize noisy/low-quality matches.

    Returns: 0-200

    Penalties:
    - Short token matches ("oil", "pump"): -100
    - Description-only matches (no ID/name match): -80
    - Stopword-only queries: -150
    """
    penalty = 0

    # Short token penalty
    for entity in entities:
        value = str(entity.get('value', '')).strip()
        if len(value) <= 3 and value.lower() in ['oil', 'gas', 'air', 'pump', 'box']:
            penalty += 100

    # Description-only match penalty
    if matched_columns == ['description'] or matched_columns == ['content']:
        penalty += 80

    # Stopword-only query
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    entity_values = [str(e.get('value', '')).lower() for e in entities]
    if all(v in stopwords for v in entity_values):
        penalty += 150

    return min(penalty, 200)  # Cap at 200


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def score_result(
    result: Dict[str, Any],
    context: ScoringContext,
    source_table: str,
    source_capability: str,
) -> ScoreComponents:
    """
    Calculate comprehensive score for a single result.

    Returns: ScoreComponents with full breakdown
    """
    components = ScoreComponents()

    # 1. Match Mode & Tier
    match_mode = detect_match_mode(result, context.entities, source_table)
    components.match_mode = match_mode.name
    components.match_tier = match_mode.value

    # 2. Conjunction Bonus
    conjunction_bonus, matched_entities = calculate_conjunction_bonus(result, context.entities)
    components.conjunction_bonus = conjunction_bonus
    components.matched_entities = matched_entities

    # 3. Proximity Bonus (NEW: RAG Stage 4)
    components.proximity_bonus = calculate_proximity_bonus(
        result, context.entities, matched_entities
    )

    # 4. Entity Confidence
    components.entity_confidence = calculate_entity_confidence_boost(
        matched_entities, context.entities
    )

    # 5. Intent-Table Prior
    components.intent_table_prior = calculate_intent_table_prior(
        source_table, source_capability, context
    )

    # 6. Recency Bonus
    components.recency_bonus = calculate_recency_bonus(result, source_table)

    # 7. Catalog/TOC Penalty (NEW: RAG Stage 4)
    components.catalog_penalty = detect_catalog_penalty(
        result, source_table, context
    )

    # 8. Noise Penalties
    matched_columns = result.get('_matched_columns', [])
    components.noise_penalty = calculate_noise_penalty(
        result, matched_columns, context.entities
    )
    components.matched_columns = matched_columns

    return components


# =============================================================================
# RANKING & DIVERSIFICATION
# =============================================================================

def rank_results(
    results: List[Dict[str, Any]],
    context: ScoringContext,
    max_per_table: int = 10,
    max_per_parent: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank and diversify results.

    Args:
        results: List of result dicts (with _capability, _source_table metadata)
        context: ScoringContext with query and entities
        max_per_table: Max results from same table
        max_per_parent: Max results from same parent (e.g., same PDF, same work order)

    Returns:
        Ranked results with score_components added
    """
    # Score all results
    scored_results = []
    for result in results:
        source_table = result.get('_source_table', 'unknown')
        source_capability = result.get('_capability', 'unknown')

        score_comp = score_result(result, context, source_table, source_capability)

        result['score_components'] = {
            'total': score_comp.total,
            'match_tier': score_comp.match_tier,
            'match_mode': score_comp.match_mode,
            'conjunction_bonus': score_comp.conjunction_bonus,
            'proximity_bonus': score_comp.proximity_bonus,  # NEW
            'entity_confidence': score_comp.entity_confidence,
            'intent_table_prior': score_comp.intent_table_prior,
            'recency_bonus': score_comp.recency_bonus,
            'catalog_penalty': score_comp.catalog_penalty,  # NEW
            'noise_penalty': score_comp.noise_penalty,
            'matched_entities': score_comp.matched_entities,
            'matched_columns': score_comp.matched_columns,
        }
        result['_score'] = score_comp.total

        scored_results.append(result)

    # Sort by score (desc), then tie-breakers
    scored_results.sort(
        key=lambda r: (
            r['_score'],                              # Primary: total score
            len(r['score_components'].get('matched_entities', [])),  # Tie: entity count
            r.get('created_at', ''),                  # Tie: recency
            r.get('id', ''),                          # Tie: deterministic ID
        ),
        reverse=True
    )

    # Diversification: enforce max_per_table and max_per_parent
    diversified = []
    table_counts = defaultdict(int)
    parent_counts = defaultdict(int)

    for result in scored_results:
        source_table = result.get('_source_table', 'unknown')
        parent_id = result.get('document_id') or result.get('work_order_id') or result.get('equipment_id')

        # Check table limit
        if table_counts[source_table] >= max_per_table:
            continue

        # Check parent limit
        if parent_id and parent_counts[parent_id] >= max_per_parent:
            continue

        diversified.append(result)
        table_counts[source_table] += 1
        if parent_id:
            parent_counts[parent_id] += 1

    return diversified


def group_results_by_domain(
    ranked_results: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group ranked results by domain for Spotlight-style UI.

    Returns: {"parts": [...], "documents": [...], "handovers": [...]}
    """
    grouped = defaultdict(list)

    for result in ranked_results:
        source_table = result.get('_source_table', 'unknown')
        source_capability = result.get('_capability', 'unknown')
        domain = _map_table_to_domain(source_table, source_capability)

        grouped[domain].append(result)

    return dict(grouped)


# =============================================================================
# DEDUPLICATION HELPERS (From RAG Stage 3)
# =============================================================================

def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Calculate Jaccard similarity between two texts.

    Used for near-duplicate detection in result deduplication.

    Formula: |A ∩ B| / |A ∪ B|

    Returns: Similarity score (0.0 to 1.0)
    """
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a or not words_b:
        return 0.0

    intersection = len(words_a & words_b)
    union = len(words_a | words_b)

    return intersection / union if union > 0 else 0.0


def deduplicate_results(
    results: List[Dict[str, Any]],
    similarity_threshold: float = 0.90,
) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate results using Jaccard similarity.

    Technique from RAG Stage 3: Prevent multiple similar results from dominating.

    Args:
        results: Ranked results (already sorted by score)
        similarity_threshold: 0.90 = 90% similar → duplicate

    Returns:
        Deduplicated results (preserves score order)
    """
    unique_results = []

    for result in results:
        # Combine searchable fields
        result_text = ' '.join(
            str(result.get(field, ''))
            for field in ['name', 'description', 'title', 'content']
        )

        is_duplicate = False

        for existing in unique_results:
            existing_text = ' '.join(
                str(existing.get(field, ''))
                for field in ['name', 'description', 'title', 'content']
            )

            similarity = calculate_jaccard_similarity(result_text, existing_text)

            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_results.append(result)

    removed_count = len(results) - len(unique_results)
    if removed_count > 0:
        logger.info(f"Deduplication: Removed {removed_count} near-duplicates (threshold={similarity_threshold})")

    return unique_results


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RESULT RANKER TEST - Enhanced with RAG Techniques")
    print("=" * 60)

    # Test 1: Intent detection
    print("\n[Test 1: Intent Detection]")
    test_queries = [
        "fuel injector MTU",
        "MTU document manual",
        "main engine overheating again",
        "check inventory in engine room",
        "order fuel filter",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        entities = [
            {"type": "EQUIPMENT", "value": "MTU", "confidence": 0.9},
            {"type": "PART", "value": "fuel injector", "confidence": 0.85},
        ]
        context = create_scoring_context(query, entities)
        print(f"  Intent signals: {context.intent_signals}")
        print(f"  Is vague: {context.is_vague}")
        print(f"  Is diagnostic: {context.is_diagnostic}")

    # Test 2: Intent-table priors
    print("\n" + "=" * 60)
    print("[Test 2: Intent-Table Priors]")

    query = "MTU document manual"
    entities = [{"type": "MANUFACTURER", "value": "MTU", "confidence": 0.9}]
    context = create_scoring_context(query, entities)

    tables = [
        ('search_document_chunks', 'documents_search'),
        ('pms_parts', 'part_by_part_number_or_name'),
        ('v_inventory', 'inventory_by_location'),
    ]

    for table, cap in tables:
        prior = calculate_intent_table_prior(table, cap, context)
        print(f"  {table}: {prior:+d}")

    # Test 3: Proximity bonus (NEW)
    print("\n" + "=" * 60)
    print("[Test 3: Proximity Bonus - RAG Stage 4]")

    result_close = {
        'name': 'MTU generator fuel filter',
        'description': 'Compatible with MTU 12V series'
    }
    result_scattered = {
        'name': 'MTU marine equipment catalog',
        'description': 'Comprehensive parts listing including fuel filter options for various models'
    }

    entities_multi = [
        {"value": "MTU", "confidence": 0.9},
        {"value": "fuel filter", "confidence": 0.85}
    ]

    # Close proximity
    _, matched_close = calculate_conjunction_bonus(result_close, entities_multi)
    prox_close = calculate_proximity_bonus(result_close, entities_multi, matched_close)
    print(f"\nClose proximity: {prox_close} points")
    print(f"  Text: {result_close['name']}")

    # Scattered
    _, matched_scattered = calculate_conjunction_bonus(result_scattered, entities_multi)
    prox_scattered = calculate_proximity_bonus(result_scattered, entities_multi, matched_scattered)
    print(f"\nScattered: {prox_scattered} points")
    print(f"  Text: {result_scattered['description']}")

    # Test 4: Catalog detection (NEW)
    print("\n" + "=" * 60)
    print("[Test 4: Catalog/TOC Detection - RAG Stage 4]")

    test_results = [
        {'name': 'Table of Contents', 'description': 'Main index', '_source_table': 'search_document_chunks'},
        {'name': 'Fuel Filter Installation', 'description': 'Step 1: Remove old filter', '_source_table': 'search_document_chunks'},
        {'name': 'Parts Catalog', 'description': 'Complete parts listing', '_source_table': 'pms_parts'},
        {'name': 'Fuel Filter', 'description': 'ENG-0008-103', '_source_table': 'pms_parts'},
    ]

    context_manual = create_scoring_context("MTU manual", entities)

    for res in test_results:
        penalty = detect_catalog_penalty(res, res['_source_table'], context_manual)
        print(f"\n  '{res['name']}': -{penalty} penalty")

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
