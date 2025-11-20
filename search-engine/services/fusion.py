"""
Fusion Engine
Combines and ranks results from semantic RAG, GraphRAG, and structured searches
"""
from typing import List, Dict, Any
from models.responses import EntityExtractionResult, IntentType
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def fuse_results(
    semantic_results: Dict[str, List[Dict[str, Any]]],
    graph_results: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType
) -> List[Dict[str, Any]]:
    """
    Fuse and rank results from multiple sources

    Args:
        semantic_results: Results from semantic RAG
        graph_results: Results from GraphRAG
        entities: Extracted entities
        intent: Detected intent

    Returns:
        Sorted list of fused results with scores
    """
    logger.info("Starting result fusion")

    all_results = []

    # 1. Process semantic results from each source
    for source, items in semantic_results.items():
        for item in items:
            result = process_semantic_result(item, source, entities, intent)
            if result:
                all_results.append(result)

    # 2. Process graph results
    graph_items = extract_graph_results(graph_results)
    for item in graph_items:
        result = process_graph_result(item, entities, intent)
        if result:
            all_results.append(result)

    # 3. Deduplicate results
    deduplicated = deduplicate_results(all_results)

    # 4. Calculate final scores
    scored_results = calculate_fusion_scores(deduplicated, entities, intent)

    # 5. Sort by score (descending)
    sorted_results = sorted(scored_results, key=lambda x: x["final_score"], reverse=True)

    logger.info(f"Fusion complete: {len(sorted_results)} results after deduplication and ranking")

    return sorted_results


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
        result["preview"] = item.get("text", "")[:200]

    elif source == "faults":
        result["type"] = "fault"
        result["title"] = item.get("title", f"Fault {item.get('fault_code', 'Unknown')}")
        result["preview"] = item.get("description", "")

    elif source == "work_order_history":
        result["type"] = "work_order"
        result["title"] = item.get("work_order", {}).get("title", "Work Order")
        result["preview"] = item.get("notes", "")[:200]

    elif source == "parts":
        result["type"] = "part"
        result["title"] = item.get("name", "Part")
        result["preview"] = item.get("description", "")

    elif source == "emails":
        result["type"] = "email"
        result["title"] = item.get("subject", "Email")
        result["preview"] = item.get("body_text", "")[:200]

    elif source == "global_knowledge":
        result["type"] = "document_chunk"
        result["title"] = f"Global: {generate_chunk_title(item)}"
        result["preview"] = item.get("text", "")[:200]
        result["is_global"] = True

    return result


def process_graph_result(
    item: Dict[str, Any],
    entities: EntityExtractionResult,
    intent: IntentType
) -> Dict[str, Any]:
    """
    Process a graph node as a result

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
        "similarity": 0.75,  # Default graph relevance
        "data": item,
        "type": node_type,
        "title": item.get("label", "Unknown"),
        "preview": str(item.get("properties", {})),
        "boosts": {"graph_discovery": 0.1},  # Boost for graph-discovered items
        "penalties": {},
        "final_score": 0.0
    }

    return result


def extract_graph_results(graph_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract relevant items from graph traversal results

    Args:
        graph_results: Graph traversal results

    Returns:
        List of graph nodes to include in results
    """
    nodes = graph_results.get("nodes", [])

    # Filter to most relevant node types
    relevant_types = ["equipment", "fault", "part", "doc_chunk", "work_order"]
    relevant_nodes = [
        node for node in nodes
        if node.get("node_type") in relevant_types
    ]

    # Limit to avoid overwhelming results
    return relevant_nodes[:20]


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate results based on ID and source

    Args:
        results: List of results

    Returns:
        Deduplicated list
    """
    seen = set()
    deduplicated = []

    for result in results:
        # Create unique key from ID and source type
        key = (result.get("id"), result.get("type"))

        if key not in seen:
            seen.add(key)
            deduplicated.append(result)
        else:
            # If duplicate, keep the one with higher similarity
            existing_idx = next(
                i for i, r in enumerate(deduplicated)
                if (r.get("id"), r.get("type")) == key
            )

            if result["similarity"] > deduplicated[existing_idx]["similarity"]:
                deduplicated[existing_idx] = result

    return deduplicated


def calculate_fusion_scores(
    results: List[Dict[str, Any]],
    entities: EntityExtractionResult,
    intent: IntentType
) -> List[Dict[str, Any]]:
    """
    Calculate final fusion scores for all results

    Args:
        results: List of results
        entities: Extracted entities
        intent: Intent type

    Returns:
        Results with calculated final_score
    """
    for result in results:
        # Start with base similarity score
        score = result["similarity"]

        # Apply boosts
        boosts = calculate_boosts(result, entities, intent)
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

    # 1. Entity match boosts
    data = result.get("data", {})

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
            boosts["intent_source_match"] = 0.10
        elif source == "document_chunks":
            boosts["intent_source_match"] = 0.08

    elif intent == IntentType.FIND_PART:
        if source == "parts":
            boosts["intent_source_match"] = 0.15

    elif intent == IntentType.FIND_DOCUMENT:
        if source in ["document_chunks", "emails"]:
            boosts["intent_source_match"] = 0.10

    # 4. Metadata quality boost
    if data.get("metadata"):
        metadata_keys = len(data["metadata"])
        if metadata_keys >= 5:
            boosts["metadata_rich"] = 0.05

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
            penalties["equipment_mismatch"] = 0.15

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
        penalties["global_source"] = 0.10

    return penalties


def calculate_recency_boost(data: Dict[str, Any]) -> float:
    """
    Calculate boost based on recency of data

    Args:
        data: Result data

    Returns:
        Boost value (0.0 to 0.1)
    """
    # Look for timestamp fields
    timestamp_fields = ["detected_at", "completed_at", "created_at", "sent_at"]

    for field in timestamp_fields:
        if field in data:
            try:
                timestamp = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                days_old = (datetime.now(timestamp.tzinfo) - timestamp).days

                # Boost recent items (within 30 days)
                if days_old <= 7:
                    return 0.10
                elif days_old <= 30:
                    return 0.05
                elif days_old <= 90:
                    return 0.02

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
        if field in data:
            try:
                timestamp = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                days_old = (datetime.now(timestamp.tzinfo) - timestamp).days

                # Penalize very old items (beyond 2 years)
                if days_old > 730:
                    return 0.15
                elif days_old > 365:
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
    # Check equipment field
    if "equipment" in data and isinstance(data["equipment"], dict):
        equipment_name = data["equipment"].get("name", "").lower()
        for name in equipment_names:
            if name.lower() in equipment_name or equipment_name in name.lower():
                return True

    # Check equipment_ids array (from document chunks metadata)
    if "equipment_ids" in data and equipment_names:
        # This would require ID resolution in production
        pass

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
    if "document" in chunk_data:
        doc = chunk_data["document"]
        if isinstance(doc, dict):
            filename = doc.get("filename", "Document")
            return filename.replace(".pdf", "").replace("_", " ")

    # Fallback to generic title with page info
    page = chunk_data.get("page_number")
    if page:
        return f"Document (Page {page})"

    return "Document"
