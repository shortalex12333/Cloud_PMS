"""
GraphRAG Module
Multi-hop graph traversal for deep research and predictive insights
"""
from typing import List, Dict, Set, Any, Optional
from utils.supabase_client import get_supabase_client
from models.responses import EntityExtractionResult, IntentType
from config import settings
import logging

logger = logging.getLogger(__name__)


async def search_graph(
    query: str,
    yacht_id: str,
    entities: EntityExtractionResult,
    intent: IntentType,
    max_depth: int = None
) -> Dict[str, Any]:
    """
    Perform graph-based multi-hop search

    Args:
        query: Search query
        yacht_id: Yacht ID
        entities: Extracted entities
        intent: Detected intent
        max_depth: Maximum graph traversal depth

    Returns:
        Dictionary containing:
            - nodes: List of discovered nodes
            - edges: List of traversed edges
            - paths: List of interesting paths
            - insights: Aggregated insights
    """
    logger.info(f"Starting GraphRAG search for yacht {yacht_id}")

    if max_depth is None:
        max_depth = settings.graph_max_depth

    # Identify starting nodes from entities
    start_nodes = await identify_start_nodes(yacht_id, entities)

    if not start_nodes:
        logger.warning("No starting nodes found for graph search")
        return {"nodes": [], "edges": [], "paths": [], "insights": {}}

    # Perform graph traversal
    traversal_result = await traverse_graph(
        yacht_id=yacht_id,
        start_nodes=start_nodes,
        max_depth=max_depth,
        intent=intent
    )

    # Generate insights from graph
    insights = generate_graph_insights(traversal_result, intent)

    logger.info(
        f"GraphRAG completed: {len(traversal_result['nodes'])} nodes, "
        f"{len(traversal_result['edges'])} edges"
    )

    return {
        "nodes": traversal_result["nodes"],
        "edges": traversal_result["edges"],
        "paths": traversal_result["paths"],
        "insights": insights
    }


async def identify_start_nodes(
    yacht_id: str,
    entities: EntityExtractionResult
) -> List[Dict[str, Any]]:
    """
    Identify starting nodes from extracted entities

    Args:
        yacht_id: Yacht ID
        entities: Extracted entities

    Returns:
        List of starting node dictionaries
    """
    client = get_supabase_client(use_service_role=True)
    start_nodes = []

    try:
        # 1. Equipment nodes
        if entities.equipment:
            for equipment_name in entities.equipment:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "equipment") \
                    .ilike("label", f"%{equipment_name}%") \
                    .limit(5) \
                    .execute()

                if result.data:
                    start_nodes.extend(result.data)

        # 2. Fault nodes
        if entities.fault_codes:
            for fault_code in entities.fault_codes:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "fault") \
                    .ilike("label", f"%{fault_code}%") \
                    .limit(3) \
                    .execute()

                if result.data:
                    start_nodes.extend(result.data)

        # 3. Part nodes
        if entities.part_numbers:
            for part_num in entities.part_numbers:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "part") \
                    .ilike("label", f"%{part_num}%") \
                    .limit(3) \
                    .execute()

                if result.data:
                    start_nodes.extend(result.data)

    except Exception as e:
        logger.error(f"Failed to identify start nodes: {e}")

    return start_nodes


async def traverse_graph(
    yacht_id: str,
    start_nodes: List[Dict[str, Any]],
    max_depth: int,
    intent: IntentType
) -> Dict[str, Any]:
    """
    Traverse graph from starting nodes up to max_depth

    Args:
        yacht_id: Yacht ID
        start_nodes: Starting nodes
        max_depth: Maximum depth to traverse
        intent: Intent type (influences traversal strategy)

    Returns:
        Dictionary with nodes, edges, and paths
    """
    client = get_supabase_client(use_service_role=True)

    visited_nodes: Set[str] = set()
    all_nodes: List[Dict[str, Any]] = []
    all_edges: List[Dict[str, Any]] = []
    paths: List[List[str]] = []

    # Queue: (node_id, current_path, depth)
    queue = [(node["id"], [node["id"]], 0) for node in start_nodes]

    # Add start nodes to visited
    for node in start_nodes:
        visited_nodes.add(node["id"])
        all_nodes.append(node)

    while queue:
        current_id, current_path, depth = queue.pop(0)

        if depth >= max_depth:
            # Save this path
            if len(current_path) > 1:
                paths.append(current_path)
            continue

        # Get edges from this node
        try:
            edges_result = client.table("graph_edges") \
                .select("*, to_node:graph_nodes!to_node_id(*)") \
                .eq("yacht_id", yacht_id) \
                .eq("from_node_id", current_id) \
                .execute()

            if not edges_result.data:
                # Dead end - save path if multi-hop
                if len(current_path) > 1:
                    paths.append(current_path)
                continue

            # Filter edges based on intent
            filtered_edges = filter_edges_by_intent(edges_result.data, intent)

            for edge in filtered_edges:
                all_edges.append(edge)

                to_node = edge["to_node"]
                to_node_id = to_node["id"]

                if to_node_id not in visited_nodes:
                    visited_nodes.add(to_node_id)
                    all_nodes.append(to_node)

                    # Add to queue
                    new_path = current_path + [to_node_id]
                    queue.append((to_node_id, new_path, depth + 1))

        except Exception as e:
            logger.error(f"Error traversing from node {current_id}: {e}")

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "paths": paths
    }


def filter_edges_by_intent(
    edges: List[Dict[str, Any]],
    intent: IntentType
) -> List[Dict[str, Any]]:
    """
    Filter and prioritize edges based on intent

    Args:
        edges: List of edges
        intent: Detected intent

    Returns:
        Filtered/sorted edge list
    """
    if intent == IntentType.DIAGNOSE_FAULT:
        # Prioritize edges to documents, parts, work_order_history
        priority_types = ["MENTIONS_DOC", "USES_PART", "HAS_FAULT", "RELATED_WO"]

    elif intent == IntentType.PREDICTIVE_REQUEST:
        # Prioritize fault patterns and weak systems
        priority_types = ["HAS_FAULT", "REPEATS_FAULT", "PARENT_OF", "DEPENDS_ON"]

    elif intent == IntentType.FIND_PART:
        # Prioritize part relationships
        priority_types = ["USES_PART", "COMPATIBLE_WITH", "SUBSTITUTE_FOR"]

    else:
        # General exploration
        return edges[:10]  # Limit to avoid explosion

    # Sort by priority
    def edge_priority(edge):
        edge_type = edge.get("edge_type", "")
        if edge_type in priority_types:
            return priority_types.index(edge_type)
        return 100

    sorted_edges = sorted(edges, key=edge_priority)

    # Return top edges
    return sorted_edges[:15]


def generate_graph_insights(
    traversal_result: Dict[str, Any],
    intent: IntentType
) -> Dict[str, Any]:
    """
    Generate insights from graph traversal results

    Args:
        traversal_result: Graph traversal results
        intent: Detected intent

    Returns:
        Dictionary of insights
    """
    insights = {
        "total_nodes": len(traversal_result["nodes"]),
        "total_edges": len(traversal_result["edges"]),
        "total_paths": len(traversal_result["paths"]),
    }

    # Count node types
    node_type_counts = {}
    for node in traversal_result["nodes"]:
        node_type = node.get("node_type", "unknown")
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

    insights["node_types"] = node_type_counts

    # Count edge types
    edge_type_counts = {}
    for edge in traversal_result["edges"]:
        edge_type = edge.get("edge_type", "unknown")
        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

    insights["edge_types"] = edge_type_counts

    # Find central nodes (most connected)
    node_connections = {}
    for edge in traversal_result["edges"]:
        from_id = edge["from_node_id"]
        to_id = edge["to_node_id"]

        node_connections[from_id] = node_connections.get(from_id, 0) + 1
        node_connections[to_id] = node_connections.get(to_id, 0) + 1

    if node_connections:
        # Top 5 most connected nodes
        top_nodes = sorted(
            node_connections.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        insights["central_nodes"] = [
            {"node_id": node_id, "connections": count}
            for node_id, count in top_nodes
        ]

    # Intent-specific insights
    if intent == IntentType.PREDICTIVE_REQUEST:
        # Count fault occurrences
        fault_nodes = [
            n for n in traversal_result["nodes"]
            if n.get("node_type") == "fault"
        ]
        insights["fault_count"] = len(fault_nodes)

    elif intent == IntentType.DIAGNOSE_FAULT:
        # Find related documents
        doc_nodes = [
            n for n in traversal_result["nodes"]
            if n.get("node_type") == "doc_chunk"
        ]
        insights["related_documents"] = len(doc_nodes)

    return insights


async def find_fault_patterns(
    yacht_id: str,
    equipment_id: str,
    lookback_days: int = 90
) -> Dict[str, Any]:
    """
    Find fault patterns for specific equipment (predictive analysis)

    Args:
        yacht_id: Yacht ID
        equipment_id: Equipment ID
        lookback_days: How far back to analyze

    Returns:
        Dictionary with pattern analysis
    """
    client = get_supabase_client(use_service_role=True)

    try:
        # Get all faults for this equipment in timeframe
        result = client.table("faults") \
            .select("*") \
            .eq("yacht_id", yacht_id) \
            .eq("equipment_id", equipment_id) \
            .gte("detected_at", f"now() - interval '{lookback_days} days'") \
            .order("detected_at", desc=False) \
            .execute()

        faults = result.data if result.data else []

        # Analyze patterns
        patterns = {
            "total_faults": len(faults),
            "unique_codes": len(set(f["fault_code"] for f in faults if f.get("fault_code"))),
            "repeating_codes": {},
            "escalating": False
        }

        # Find repeating fault codes
        fault_code_counts = {}
        for fault in faults:
            code = fault.get("fault_code")
            if code:
                fault_code_counts[code] = fault_code_counts.get(code, 0) + 1

        # Identify codes that repeat more than twice
        for code, count in fault_code_counts.items():
            if count >= 2:
                patterns["repeating_codes"][code] = count

        # Check if fault frequency is increasing (simple heuristic)
        if len(faults) >= 3:
            mid_point = len(faults) // 2
            first_half_count = mid_point
            second_half_count = len(faults) - mid_point

            if second_half_count > first_half_count * 1.5:
                patterns["escalating"] = True

        return patterns

    except Exception as e:
        logger.error(f"Failed to analyze fault patterns: {e}")
        return {}
