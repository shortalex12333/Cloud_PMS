"""
Entity Extraction Module
Extracts structured entities from natural language queries using regex + fuzzy matching
"""
import re
from rapidfuzz import fuzz, process
from typing import List, Dict, Tuple
from models.responses import EntityExtractionResult
import logging

logger = logging.getLogger(__name__)


# Regex patterns for entity extraction
PATTERNS = {
    # Fault codes: E047, SPN 123, FMI 4, etc.
    "fault_codes": [
        r"\b[EeRr]\s?\d{3,4}\b",  # E047, R123
        r"\bSPN\s?\d+\b",  # SPN 123
        r"\bFMI\s?\d+\b",  # FMI 4
        r"\bP\d{4}\b",  # P0123 (OBD codes)
    ],

    # Part numbers: 2040N2, 01-234567, etc.
    "part_numbers": [
        r"\b\d{4}[A-Z]\d\b",  # 2040N2
        r"\b\d{2}-\d{6}\b",  # 01-234567
        r"\b[A-Z]{2,3}\d{4,6}\b",  # CAT12345, MTU1234
    ],

    # Action words
    "action_words": [
        r"\b(fix|repair|replace|diagnose|find|show|create|add|order|check|inspect|service|maintain)\b",
    ],

    # Document types
    "document_types": [
        r"\b(manual|drawing|schematic|procedure|handover|invoice|certificate|bulletin|report)\b",
    ],

    # Severity keywords
    "severity": [
        r"\b(emergency|critical|urgent|high\s?priority|routine|low\s?priority)\b",
    ],

    # Location keywords
    "location": [
        r"\b(engine\s?room|aft|forward|port|starboard|deck|locker|machinery\s?space)\b",
    ],
}

# System names for fuzzy matching
SYSTEM_NAMES = [
    "main engine",
    "generator",
    "port generator",
    "starboard generator",
    "stabiliser",
    "stabilizer",
    "hvac",
    "air conditioning",
    "chiller",
    "black water tank",
    "grey water tank",
    "fresh water tank",
    "fuel tank",
    "hydraulic pump",
    "fire pump",
    "bilge pump",
    "sewage pump",
    "watermaker",
    "compressor",
    "crane",
    "thruster",
    "bow thruster",
    "stern thruster",
]

# Equipment name patterns (for precise matching)
EQUIPMENT_PATTERNS = [
    r"\bmain\s+engine\b",
    r"\b(gen|generator)\s*\d*\b",
    r"\b(port|starboard|stbd)\s+(gen|generator|engine)\b",
    r"\bchiller\s*\d*\b",
    r"\b(bow|stern)\s+thruster\b",
    r"\bwatermaker\b",
    r"\bhvac\b",
]


def extract_with_regex(query: str, patterns: List[str]) -> List[str]:
    """
    Extract matches using regex patterns

    Args:
        query: Query text
        patterns: List of regex patterns

    Returns:
        List of unique matches
    """
    matches = []
    query_lower = query.lower()

    for pattern in patterns:
        found = re.findall(pattern, query_lower, re.IGNORECASE)
        if found:
            matches.extend(found if isinstance(found[0], str) else [m[0] for m in found])

    return list(set(matches))  # Remove duplicates


def fuzzy_match_equipment(query: str, threshold: int = 70) -> List[Tuple[str, float]]:
    """
    Fuzzy match equipment names from query

    Args:
        query: Query text
        threshold: Minimum similarity score (0-100)

    Returns:
        List of (equipment_name, confidence_score) tuples
    """
    matches = []
    query_lower = query.lower()

    # Use rapidfuzz to find similar equipment names
    results = process.extract(
        query_lower,
        SYSTEM_NAMES,
        scorer=fuzz.partial_ratio,
        limit=5
    )

    for name, score, _ in results:
        if score >= threshold:
            # Normalize confidence to 0-1
            confidence = score / 100.0
            matches.append((name, confidence))

    return matches


def extract_entities(query: str) -> EntityExtractionResult:
    """
    Extract all entities from query text

    Args:
        query: Natural language query

    Returns:
        EntityExtractionResult with all extracted entities and confidence scores
    """
    logger.debug(f"Extracting entities from query: {query}")

    # Initialize result
    result = EntityExtractionResult()
    confidence_scores = {}

    # 1. Extract fault codes (high confidence - regex)
    fault_codes = extract_with_regex(query, PATTERNS["fault_codes"])
    if fault_codes:
        result.fault_codes = fault_codes
        confidence_scores["fault_codes"] = 1.0  # Regex matches are confident

    # 2. Extract part numbers (high confidence - regex)
    part_numbers = extract_with_regex(query, PATTERNS["part_numbers"])
    if part_numbers:
        result.part_numbers = part_numbers
        confidence_scores["part_numbers"] = 0.95

    # 3. Extract action words
    action_words = extract_with_regex(query, PATTERNS["action_words"])
    if action_words:
        result.action_words = action_words
        confidence_scores["action_words"] = 0.9

    # 4. Extract document types
    document_types = extract_with_regex(query, PATTERNS["document_types"])
    if document_types:
        result.document_types = document_types
        confidence_scores["document_types"] = 0.85

    # 5. Extract severity
    severity_matches = extract_with_regex(query, PATTERNS["severity"])
    if severity_matches:
        result.severity = severity_matches[0]  # Take first match
        confidence_scores["severity"] = 0.8

    # 6. Extract location
    location_matches = extract_with_regex(query, PATTERNS["location"])
    if location_matches:
        result.location = location_matches[0]  # Take first match
        confidence_scores["location"] = 0.8

    # 7. Extract equipment names (regex first, then fuzzy)
    equipment_regex = extract_with_regex(query, EQUIPMENT_PATTERNS)
    equipment_fuzzy = fuzzy_match_equipment(query)

    # Combine regex and fuzzy matches
    equipment_names = list(set(equipment_regex))  # Start with regex matches
    equipment_confidence = 0.95 if equipment_regex else 0.0

    # Add fuzzy matches if regex didn't find anything or to supplement
    for name, confidence in equipment_fuzzy:
        if name not in equipment_names:
            equipment_names.append(name)
            equipment_confidence = max(equipment_confidence, confidence)

    if equipment_names:
        result.equipment = equipment_names
        confidence_scores["equipment"] = equipment_confidence

    # 8. Extract system names (similar to equipment but broader)
    system_names = []
    for word in ["hvac", "generator", "engine", "stabiliser", "chiller", "pump"]:
        if word in query.lower():
            system_names.append(word)

    if system_names:
        result.system_names = system_names
        confidence_scores["system_names"] = 0.7

    # Store all confidence scores
    result.confidence = confidence_scores

    logger.info(f"Extracted entities: {result.model_dump()}")

    return result


def normalize_entity(entity: str, entity_type: str) -> str:
    """
    Normalize entity to standard form

    Args:
        entity: Entity string
        entity_type: Type of entity (equipment, fault_code, etc.)

    Returns:
        Normalized entity string
    """
    entity = entity.strip().upper()

    if entity_type == "fault_code":
        # Remove spaces from fault codes: "E 047" -> "E047"
        entity = entity.replace(" ", "")

    elif entity_type == "equipment":
        # Standardize equipment names
        entity = entity.lower()
        replacements = {
            "gen": "generator",
            "stbd": "starboard",
            "fwd": "forward",
            "hvac": "HVAC",
        }
        for old, new in replacements.items():
            entity = entity.replace(old, new)

    return entity
