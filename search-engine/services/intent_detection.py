"""
Intent Detection Module
Maps user queries to specific intents based on entities and keywords
"""
from models.responses import IntentDetectionResult, IntentType, EntityExtractionResult
import logging

logger = logging.getLogger(__name__)


# Intent detection rules (ordered by priority)
INTENT_RULES = [
    {
        "intent": IntentType.DIAGNOSE_FAULT,
        "conditions": {
            "required": ["fault_codes"],
            "optional": ["equipment"],
            "keywords": ["diagnose", "fault", "error", "code", "problem"]
        },
        "confidence_base": 0.90
    },
    {
        "intent": IntentType.CREATE_WORK_ORDER,
        "conditions": {
            "required": [],
            "optional": ["equipment", "fault_codes"],
            "keywords": ["create", "new", "work order", "task", "job", "wo"]
        },
        "confidence_base": 0.85
    },
    {
        "intent": IntentType.ADD_TO_HANDOVER,
        "conditions": {
            "required": [],
            "optional": [],
            "keywords": ["add to handover", "handover", "shift change", "log this"]
        },
        "confidence_base": 0.95
    },
    {
        "intent": IntentType.FIND_PART,
        "conditions": {
            "required": [],
            "optional": ["part_numbers"],
            "keywords": ["part", "spare", "filter", "inventory", "stock", "order"]
        },
        "confidence_base": 0.80
    },
    {
        "intent": IntentType.FIND_DOCUMENT,
        "conditions": {
            "required": [],
            "optional": ["document_types", "equipment"],
            "keywords": ["manual", "drawing", "document", "procedure", "schematic", "find"]
        },
        "confidence_base": 0.75
    },
    {
        "intent": IntentType.PREDICTIVE_REQUEST,
        "conditions": {
            "required": [],
            "optional": ["equipment"],
            "keywords": [
                "predict", "likely to fail", "weak", "risk", "upcoming",
                "failure", "maintenance due", "soon"
            ]
        },
        "confidence_base": 0.88
    },
]


def detect_intent(query: str, entities: EntityExtractionResult) -> IntentDetectionResult:
    """
    Detect user intent from query and extracted entities

    Args:
        query: Original query text
        entities: Extracted entities

    Returns:
        IntentDetectionResult with detected intent and confidence
    """
    logger.debug(f"Detecting intent for query: {query}")

    query_lower = query.lower()
    best_match = None
    best_confidence = 0.0
    best_reasoning = ""

    # Check each rule
    for rule in INTENT_RULES:
        confidence = calculate_intent_confidence(query_lower, entities, rule)

        if confidence > best_confidence:
            best_confidence = confidence
            best_match = rule["intent"]
            best_reasoning = build_reasoning(query_lower, entities, rule)

    # Fallback to general search if no strong match
    if best_confidence < 0.5:
        best_match = IntentType.GENERAL_SEARCH
        best_confidence = 0.6
        best_reasoning = "No specific intent detected; defaulting to general search"

    result = IntentDetectionResult(
        intent=best_match,
        confidence=best_confidence,
        reasoning=best_reasoning
    )

    logger.info(f"Detected intent: {result.intent} (confidence: {result.confidence:.2f})")

    return result


def calculate_intent_confidence(
    query: str,
    entities: EntityExtractionResult,
    rule: dict
) -> float:
    """
    Calculate confidence score for a specific intent rule

    Args:
        query: Query text (lowercase)
        entities: Extracted entities
        rule: Intent rule definition

    Returns:
        Confidence score (0.0 to 1.0)
    """
    conditions = rule["conditions"]
    base_confidence = rule["confidence_base"]

    # Check required entities
    required_met = all(
        getattr(entities, field, None)
        for field in conditions["required"]
    )

    if not required_met:
        return 0.0  # Required entities missing

    # Start with base confidence
    confidence = base_confidence

    # Bonus for optional entities present
    optional_present = sum(
        1 for field in conditions["optional"]
        if getattr(entities, field, None)
    )

    if conditions["optional"]:
        optional_bonus = (optional_present / len(conditions["optional"])) * 0.10
        confidence = min(confidence + optional_bonus, 1.0)

    # Keyword matching
    keywords_found = sum(
        1 for keyword in conditions["keywords"]
        if keyword in query
    )

    if conditions["keywords"]:
        keyword_ratio = keywords_found / len(conditions["keywords"])

        # Strong keyword match boosts confidence
        if keyword_ratio > 0.3:
            confidence = min(confidence + (keyword_ratio * 0.15), 1.0)
        elif keyword_ratio == 0:
            # No keywords found - reduce confidence
            confidence *= 0.7

    return confidence


def build_reasoning(
    query: str,
    entities: EntityExtractionResult,
    rule: dict
) -> str:
    """
    Build human-readable reasoning for intent selection

    Args:
        query: Query text
        entities: Extracted entities
        rule: Matched rule

    Returns:
        Reasoning string
    """
    reasons = []

    # Required entities
    if rule["conditions"]["required"]:
        required_names = ", ".join(rule["conditions"]["required"])
        reasons.append(f"Required entities detected: {required_names}")

    # Optional entities
    optional_present = [
        field for field in rule["conditions"]["optional"]
        if getattr(entities, field, None)
    ]
    if optional_present:
        optional_names = ", ".join(optional_present)
        reasons.append(f"Supporting entities: {optional_names}")

    # Keywords
    keywords_found = [
        kw for kw in rule["conditions"]["keywords"]
        if kw in query
    ]
    if keywords_found:
        reasons.append(f"Keywords matched: {', '.join(keywords_found[:3])}")

    if not reasons:
        return "Pattern match"

    return "; ".join(reasons)


def should_activate_graph_rag(
    intent: IntentType,
    entities: EntityExtractionResult,
    query: str
) -> bool:
    """
    Determine if GraphRAG should be activated for this query

    Args:
        intent: Detected intent
        entities: Extracted entities
        query: Original query

    Returns:
        True if GraphRAG should be used
    """
    # Always activate for predictive requests
    if intent == IntentType.PREDICTIVE_REQUEST:
        return True

    # Activate if query mentions "deeper", "research", "relationships"
    deep_keywords = ["deeper", "research", "all related", "everything about", "history"]
    if any(kw in query.lower() for kw in deep_keywords):
        return True

    # Activate if multiple entities detected (complex query)
    entity_count = sum([
        len(entities.equipment),
        len(entities.fault_codes),
        len(entities.part_numbers),
    ])

    if entity_count >= 2:
        return True

    # Default to standard RAG
    return False
