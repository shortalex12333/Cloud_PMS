"""
Fusion Engine
Combines and ranks results from semantic RAG, keyword search, and metadata filters
Graph signals are ADDITIVE (when enabled) - not fundamental to ranking

DESIGN PRINCIPLE: Works correctly with only vector search + keyword search
GraphRAG signals boost scores but don't break fusion when disabled
"""
from typing import List, Dict, Any, Optional, Set
from models.responses import EntityExtractionResult, IntentType
from config import settings
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN FUSION FUNCTION
# =============================================================================

async def fuse_results(
    semantic_results: Dict[str, List[Dict[str, Any]]],
    graph_results: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType,
    keyword_matches: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> List[Dict[str, Any]]:
    """
    Fuse and rank results from multiple sources

    Primary ranking based on:
    1. Vector similarity (semantic_results)
    2. Keyword matching (keyword_matches) - when enabled
    3. Metadata relevance (entity matches, recency)

    Graph signals (graph_results) are ADDITIVE:
    - Boost scores when GraphRAG finds related nodes
    - Does NOT break ranking when graph_results is empty

    Args:
        semantic_results: Results from semantic RAG (required)
        graph_results: Results from GraphRAG (optional, may be empty)
        entities: Extracted entities
        intent: Detected intent
        keyword_matches: Results from keyword search (optional)

    Returns:
        Sorted list of fused results with scores
    """
    logger.info("Starting result fusion")

    all_results = []

    # 1. Process semantic results (PRIMARY source)
    for source, items in semantic_results.items():
        for item in items:
            result = process_semantic_result(item, source, entities, intent)
            if result:
                all_results.append(result)

    # 2. Process keyword matches (SECONDARY source) - when enabled
    if keyword_matches and settings.keyword_search_enabled:
        for source, items in keyword_matches.items():
            for item in items:
                result = process_keyword_result(item, source, entities, intent)
                if result:
                    all_results.append(result)

    # 3. Process graph results (ADDITIVE source) - only if enabled and has data
    graph_node_ids: Set[str] = set()
    if graph_results and settings.graph_rag_enabled:
        graph_items = extract_graph_results(graph_results)
        for item in graph_items:
            result = process_graph_result(item, entities, intent)
            if result:
                all_results.append(result)
                # Track graph-discovered IDs for boosting
                if item.get("ref_id"):
                    graph_node_ids.add(item["ref_id"])

    # 4. Deduplicate results
    deduplicated = deduplicate_results(all_results)

    # 5. Calculate final scores (with optional graph boost)
    scored_results = calculate_fusion_scores(
        deduplicated,
        entities,
        intent,
        graph_discovered_ids=graph_node_ids
    )

    # 6. Sort by score (descending)
    sorted_results = sorted(scored_results, key=lambda x: x["final_score"], reverse=True)

    logger.info(
        f"Fusion complete: {len(sorted_results)} results after deduplication and ranking"
    )

    return sorted_results


# =============================================================================
# RESULT PROCESSING
# =============================================================================

def process_semantic_result(
    item: Dict[str, Any],
    source: str,
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, Any]:
    """
    Process a single semantic search result

    Args:
        item: Result item
        source: Source name (document_chunks, faults, etc.)
        entities: Extracted entities
        intent: Intent type

    Returns:
        Processed result dictionary
    """
    result = {
        "id": item.get("id"),
        "source": source,
        "source_type": "semantic",
        "similarity": item.get("similarity", 0.7),
        "data": item,
        "boosts": {},
        "penalties": {},
        "final_score": 0.0
    }

    # Apply source-specific processing
    if source == "document_chunks":
        result["type"] = "document_chunk"
        result["title"] = generate_chunk_title(item)
        result["preview"] = item.get("text", "")[:300]
        result["source_label"] = build_document_source_label(item)

    elif source == "faults":
        result["type"] = "fault"
        result["title"] = item.get("title", f"Fault {item.get('fault_code', 'Unknown')}")
        result["preview"] = item.get("description", "")[:300]
        result["source_label"] = {"source_type": "Fault Log", "source_name": item.get("fault_code", "")}

    elif source == "work_order_history":
        result["type"] = "work_order"
        result["title"] = item.get("work_order", {}).get("title", "Work Order")
        result["preview"] = item.get("notes", "")[:300]
        result["source_label"] = {"source_type": "Work Order", "source_name": item.get("work_order_id", "")}

    elif source == "parts":
        result["type"] = "part"
        result["title"] = item.get("name", "Part")
        result["preview"] = item.get("description", "")[:300]
        result["source_label"] = {"source_type": "Parts Inventory", "source_name": item.get("part_number", "")}

    elif source == "emails":
        result["type"] = "email"
        result["title"] = item.get("subject", "Email")
        result["preview"] = item.get("body_text", "")[:300]
        result["source_label"] = {"source_type": "Email", "source_name": item.get("sender", "")}

    elif source == "global_knowledge":
        result["type"] = "document_chunk"
        result["title"] = f"Global: {generate_chunk_title(item)}"
        result["preview"] = item.get("text", "")[:300]
        result["is_global"] = True
        result["source_label"] = {"source_type": "Global Knowledge", "source_name": ""}

    return result


def process_keyword_result(
    item: Dict[str, Any],
    source: str,
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, Any]:
    """
    Process a keyword search result

    Keyword results get a base similarity of 0.6 (lower than vector)
    but can be boosted by exact matches

    Args:
        item: Result item
        source: Source name
        entities: Extracted entities
        intent: Intent type

    Returns:
        Processed result dictionary
    """
    result = process_semantic_result(item, source, entities, intent)

    # Mark as keyword result with lower base similarity
    result["source_type"] = "keyword"
    result["similarity"] = 0.6

    # Boost for exact keyword matches
    if has_exact_keyword_match(item, entities):
        result["boosts"]["keyword_exact_match"] = settings.keyword_boost_factor

    return result


def process_graph_result(
    item: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, Any]:
    """
    Process a graph node as a result

    Graph results have moderate base similarity (0.65)
    They represent related entities discovered through traversal

    Args:
        item: Graph node
        entities: Extracted entities
        intent: Intent type

    Returns:
        Processed result dictionary
    """
    node_type = item.get("node_type", "unknown")

    result = {
        "id": item.get("ref_id"),  # Actual entity ID
        "source": f"graph_{node_type}",
        "source_type": "graph",
        "similarity": 0.65,  # Default graph relevance
        "data": item,
        "type": node_type,
        "title": item.get("label", "Unknown"),
        "preview": str(item.get("properties", {}))[:300],
        "boosts": {"graph_discovery": 0.1},  # Inherent boost for graph-discovered items
        "penalties": {},
        "final_score": 0.0,
        "source_label": {"source_type": "Graph", "source_name": node_type}
    }

    return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def extract_graph_results(graph_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract relevant items from graph traversal results

    Args:
        graph_results: Graph traversal results

    Returns:
        List of graph nodes to include in results
    """
    nodes = graph_results.get("nodes", [])

    if not nodes:
        return []

    # Filter to most relevant node types
    relevant_types = ["equipment", "fault", "part", "document", "work_order"]
    relevant_nodes = [
        node for node in nodes
        if node.get("node_type") in relevant_types
    ]

    # Limit to avoid overwhelming results
    return relevant_nodes[:15]


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate results based on ID and type
    Prefers semantic results over keyword/graph results

    Args:
        results: List of results

    Returns:
        Deduplicated list
    """
    seen = {}  # key -> (index, source_type_priority)

    # Priority: semantic > keyword > graph
    SOURCE_PRIORITY = {"semantic": 0, "keyword": 1, "graph": 2}

    deduplicated = []

    for result in results:
        key = (result.get("id"), result.get("type"))

        if key not in seen:
            seen[key] = (len(deduplicated), result.get("source_type", "semantic"))
            deduplicated.append(result)
        else:
            existing_idx, existing_source_type = seen[key]

            current_priority = SOURCE_PRIORITY.get(result.get("source_type", "semantic"), 99)
            existing_priority = SOURCE_PRIORITY.get(existing_source_type, 99)

            # Replace if current has higher priority (lower number) or higher similarity
            if current_priority < existing_priority:
                deduplicated[existing_idx] = result
                seen[key] = (existing_idx, result.get("source_type", "semantic"))
            elif current_priority == existing_priority:
                if result.get("similarity", 0) > deduplicated[existing_idx].get("similarity", 0):
                    deduplicated[existing_idx] = result

    return deduplicated


def calculate_fusion_scores(
    results: List[Dict[str, Any]],
    entities: EntityExtractionResult,
    intent: IntentType,
    graph_discovered_ids: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Calculate final fusion scores for all results

    Scoring formula:
        score = similarity + sum(boosts) - sum(penalties)

    Graph signals are ADDITIVE:
        - Items also found in graph get +0.08 boost
        - This enhances but doesn't require graph

    Args:
        results: List of results
        entities: Extracted entities
        intent: Intent type
        graph_discovered_ids: IDs of entities discovered via graph (for boosting)

    Returns:
        Results with calculated final_score
    """
    graph_discovered_ids = graph_discovered_ids or set()

    for result in results:
        # Start with base similarity score
        score = result["similarity"]

        # Apply boosts
        boosts = calculate_boosts(result, entities, intent)

        # Add graph discovery boost if applicable
        if result.get("id") in graph_discovered_ids and result.get("source_type") != "graph":
            boosts["graph_correlated"] = 0.08

        result["boosts"] = boosts

        for boost_name, boost_value in boosts.items():
            score += boost_value

        # Apply penalties
        penalties = calculate_penalties(result, entities, intent)
        result["penalties"] = penalties

        for penalty_name, penalty_value in penalties.items():
            score -= penalty_value

        # Ensure score stays in valid range
        result["final_score"] = max(0.0, min(1.0, score))

    return results


def calculate_boosts(
    result: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, float]:
    """
    Calculate boost scores for a result

    Args:
        result: Result item
        entities: Extracted entities
        intent: Intent type

    Returns:
        Dictionary of boost scores
    """
    boosts = {}
    data = result.get("data", {})

    # 1. Entity match boosts
    # Equipment match
    if entities.equipment:
        equipment_match = check_equipment_match(data, entities.equipment)
        if equipment_match:
            boosts["equipment_match"] = 0.15

    # Fault code exact match
    if entities.fault_codes:
        fault_code = data.get("fault_code")
        if fault_code and fault_code in entities.fault_codes:
            boosts["fault_code_match"] = 0.20

    # Part number exact match
    if entities.part_numbers:
        part_number = data.get("part_number")
        if part_number and part_number in entities.part_numbers:
            boosts["part_number_match"] = 0.20

    # 2. Recency boost
    recency_boost = calculate_recency_boost(data)
    if recency_boost > 0:
        boosts["recency"] = recency_boost

    # 3. Source type boost based on intent
    source = result.get("source", "")

    if intent == IntentType.DIAGNOSE_FAULT:
        if source == "faults":
            boosts["intent_source_match"] = 0.12
        elif source == "document_chunks":
            boosts["intent_source_match"] = 0.08
        elif source == "work_order_history":
            boosts["intent_source_match"] = 0.06

    elif intent == IntentType.FIND_PART:
        if source == "parts":
            boosts["intent_source_match"] = 0.15

    elif intent == IntentType.FIND_DOCUMENT:
        if source in ["document_chunks", "global_knowledge"]:
            boosts["intent_source_match"] = 0.10
        elif source == "emails":
            boosts["intent_source_match"] = 0.05

    elif intent == IntentType.CREATE_WORK_ORDER:
        if source == "work_order_history":
            boosts["intent_source_match"] = 0.10
        elif source == "faults":
            boosts["intent_source_match"] = 0.08

    elif intent == IntentType.PREDICTIVE_REQUEST:
        if source == "faults":
            boosts["intent_source_match"] = 0.10
        elif source.startswith("graph_"):
            boosts["intent_source_match"] = 0.12

    elif intent == IntentType.ADD_TO_HANDOVER:
        # No specific source preference for handover
        pass

    # 4. Metadata quality boost
    if data.get("metadata"):
        metadata_keys = len(data["metadata"]) if isinstance(data["metadata"], dict) else 0
        if metadata_keys >= 5:
            boosts["metadata_rich"] = 0.05

    # 5. Keyword boost (if this result came from keyword search)
    if result.get("source_type") == "keyword":
        # Already has keyword_exact_match if applicable
        pass

    return boosts


def calculate_penalties(
    result: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, float]:
    """
    Calculate penalty scores for a result

    Args:
        result: Result item
        entities: Extracted entities
        intent: Intent type

    Returns:
        Dictionary of penalty scores
    """
    penalties = {}
    data = result.get("data", {})

    # 1. Mismatched equipment penalty
    if entities.equipment:
        equipment_match = check_equipment_match(data, entities.equipment)
        if not equipment_match and data.get("equipment_id"):
            penalties["equipment_mismatch"] = 0.12

    # 2. Outdated content penalty
    age_penalty = calculate_age_penalty(data)
    if age_penalty > 0:
        penalties["outdated"] = age_penalty

    # 3. Low-quality chunk penalty (for documents)
    if result.get("type") == "document_chunk":
        text = data.get("text", "")
        if len(text) < 50:  # Very short chunks
            penalties["short_chunk"] = 0.10

    # 4. Global knowledge penalty (prefer local data)
    if result.get("is_global"):
        penalties["global_source"] = 0.08

    # 5. Graph-only penalty (prefer semantic matches)
    if result.get("source_type") == "graph" and not result.get("boosts", {}).get("entity_match"):
        penalties["graph_only"] = 0.05

    return penalties


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def has_exact_keyword_match(item: Dict[str, Any], entities: EntityExtractionResult) -> bool:
    """Check if item has exact keyword match with extracted entities"""
    text = str(item.get("text", "") or item.get("description", "") or item.get("notes", "")).lower()

    # Check equipment names
    for equipment in entities.equipment:
        if equipment.lower() in text:
            return True

    # Check fault codes
    for fault_code in entities.fault_codes:
        if fault_code.lower() in text:
            return True

    # Check part numbers
    for part_num in entities.part_numbers:
        if part_num.lower() in text:
            return True

    return False


def calculate_recency_boost(data: Dict[str, Any]) -> float:
    """
    Calculate boost based on recency of data

    Args:
        data: Result data

    Returns:
        Boost value (0.0 to 0.10)
    """
    timestamp_fields = ["detected_at", "completed_at", "created_at", "sent_at", "indexed_at"]

    for field in timestamp_fields:
        if field in data and data[field]:
            try:
                timestamp_str = data[field]
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
                    days_old = (now - timestamp).days

                    # Boost recent items
                    if days_old <= 7:
                        return 0.10
                    elif days_old <= 30:
                        return 0.06
                    elif days_old <= 90:
                        return 0.03

            except Exception:
                pass

    return 0.0


def calculate_age_penalty(data: Dict[str, Any]) -> float:
    """
    Calculate penalty for very old data

    Args:
        data: Result data

    Returns:
        Penalty value (0.0 to 0.15)
    """
    timestamp_fields = ["detected_at", "completed_at", "created_at", "indexed_at"]

    for field in timestamp_fields:
        if field in data and data[field]:
            try:
                timestamp_str = data[field]
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
                    days_old = (now - timestamp).days

                    # Penalize very old items
                    if days_old > 730:  # > 2 years
                        return 0.15
                    elif days_old > 365:  # > 1 year
                        return 0.08

            except Exception:
                pass

    return 0.0


def check_equipment_match(data: Dict[str, Any], equipment_names: List[str]) -> bool:
    """
    Check if data matches any of the equipment names

    Args:
        data: Result data
        equipment_names: List of equipment names to match

    Returns:
        True if match found
    """
    # Check equipment field (nested object)
    if "equipment" in data and isinstance(data["equipment"], dict):
        equipment_name = data["equipment"].get("name", "").lower()
        for name in equipment_names:
            if name.lower() in equipment_name or equipment_name in name.lower():
                return True

    # Check equipment_name field (flat)
    if "equipment_name" in data:
        equipment_name = str(data["equipment_name"]).lower()
        for name in equipment_names:
            if name.lower() in equipment_name or equipment_name in name.lower():
                return True

    # Check text content for equipment mention
    text = str(data.get("text", "") or data.get("description", "")).lower()
    for name in equipment_names:
        if name.lower() in text:
            return True

    return False


def generate_chunk_title(chunk_data: Dict[str, Any]) -> str:
    """
    Generate a descriptive title for a document chunk

    Args:
        chunk_data: Chunk data

    Returns:
        Title string
    """
    # Try to get document title or filename
    if "document" in chunk_data and isinstance(chunk_data["document"], dict):
        doc = chunk_data["document"]
        filename = doc.get("filename", "") or doc.get("title", "")
        if filename:
            # Clean up filename for display
            clean_name = filename.replace(".pdf", "").replace(".PDF", "")
            clean_name = clean_name.replace("_", " ").replace("-", " ")
            return clean_name[:80]

    # Try filename directly
    if chunk_data.get("filename"):
        return chunk_data["filename"].replace(".pdf", "").replace("_", " ")[:80]

    # Fallback to generic title with page info
    page = chunk_data.get("page_number")
    if page:
        return f"Document (Page {page})"

    return "Document"


def build_document_source_label(item: Dict[str, Any]) -> Dict[str, str]:
    """
    Build source label for document chunks

    Format: {source_type} . {source_name} . {location}
    Example: "Manual . CAT_3516_Service.pdf . Page 34"

    Args:
        item: Document chunk data

    Returns:
        Source label dictionary
    """
    # Determine document type
    doc_type = "Document"
    if "document" in item and isinstance(item["document"], dict):
        doc = item["document"]
        doc_type = doc.get("document_type", "Document")
        if doc_type in ["manual", "Manual"]:
            doc_type = "Manual"
        elif doc_type in ["technical_bulletin", "bulletin"]:
            doc_type = "Tech Bulletin"
        elif doc_type in ["email", "Email"]:
            doc_type = "Email"

    # Get filename
    source_name = ""
    if "document" in item and isinstance(item["document"], dict):
        source_name = item["document"].get("filename", "")
    elif item.get("filename"):
        source_name = item["filename"]

    # Get location
    location = None
    if item.get("page_number"):
        location = f"Page {item['page_number']}"

    return {
        "source_type": doc_type,
        "source_name": source_name,
        "location": location
    }
