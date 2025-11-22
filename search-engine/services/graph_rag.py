"""
GraphRAG Module
Multi-hop graph traversal for deep research and predictive insights

FEATURE FLAG: Controlled by settings.graph_rag_enabled
When disabled, all methods return empty/stubbed structured responses
"""
from typing import List, Dict, Set, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging

from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES FOR GRAPH STRUCTURES
# =============================================================================

class NodeType(str, Enum):
    """Graph node types"""
    EQUIPMENT = "equipment"
    FAULT = "fault"
    PART = "part"
    DOCUMENT = "document"
    WORK_ORDER = "work_order"
    SYSTEM = "system"


class EdgeType(str, Enum):
    """Graph edge types"""
    HAS_FAULT = "HAS_FAULT"
    USES_PART = "USES_PART"
    MENTIONS_DOC = "MENTIONS_DOC"
    RELATED_WO = "RELATED_WO"
    PARENT_OF = "PARENT_OF"
    DEPENDS_ON = "DEPENDS_ON"
    REPEATS_FAULT = "REPEATS_FAULT"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    SUBSTITUTE_FOR = "SUBSTITUTE_FOR"


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph"""
    id: str
    node_type: NodeType
    label: str
    ref_id: str  # Reference to actual entity (equipment_id, part_id, etc.)
    properties: Dict[str, Any] = field(default_factory=dict)
    yacht_id: Optional[str] = None


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph"""
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """Represents a path through the graph"""
    nodes: List[str]  # Node IDs in order
    edges: List[str]  # Edge IDs in order
    total_weight: float = 0.0


@dataclass
class RelatedNodesResult:
    """Result from get_related_nodes"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_count: int
    truncated: bool = False


@dataclass
class FaultCascadeResult:
    """Result from get_fault_cascade"""
    root_fault: Optional[GraphNode]
    cascade_nodes: List[GraphNode]
    cascade_edges: List[GraphEdge]
    affected_equipment: List[str]
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    recommended_actions: List[str]


@dataclass
class GraphSearchResult:
    """Complete result from graph search"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: List[GraphPath]
    insights: Dict[str, Any]


# =============================================================================
# GRAPH RAG INTERFACE (Abstract)
# =============================================================================

class GraphRAGInterface(ABC):
    """Abstract interface for GraphRAG operations"""

    @abstractmethod
    async def get_related_nodes(
        self,
        yacht_id: str,
        equipment_id: Optional[str] = None,
        fault_code: Optional[str] = None,
        part_id: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 20
    ) -> RelatedNodesResult:
        """
        Get nodes related to the given entity

        Args:
            yacht_id: Yacht ID for RLS
            equipment_id: Optional equipment ID to start from
            fault_code: Optional fault code to start from
            part_id: Optional part ID to start from
            max_depth: Maximum traversal depth
            limit: Maximum nodes to return

        Returns:
            RelatedNodesResult with nodes and edges
        """
        pass

    @abstractmethod
    async def get_fault_cascade(
        self,
        yacht_id: str,
        equipment_id: str,
        fault_code: str,
        lookback_days: int = 90
    ) -> FaultCascadeResult:
        """
        Analyze fault cascade for predictive insights

        Args:
            yacht_id: Yacht ID for RLS
            equipment_id: Equipment with the fault
            fault_code: Fault code to analyze
            lookback_days: Historical lookback period

        Returns:
            FaultCascadeResult with cascade analysis
        """
        pass

    @abstractmethod
    async def search(
        self,
        yacht_id: str,
        entities: Any,  # EntityExtractionResult
        intent: Any,  # IntentType
        max_depth: int = 3
    ) -> GraphSearchResult:
        """
        Full graph search for query

        Args:
            yacht_id: Yacht ID
            entities: Extracted entities
            intent: Detected intent
            max_depth: Max traversal depth

        Returns:
            GraphSearchResult with nodes, edges, paths, insights
        """
        pass


# =============================================================================
# STUBBED IMPLEMENTATION (Feature-flagged)
# =============================================================================

class StubbedGraphRAG(GraphRAGInterface):
    """
    Stubbed GraphRAG implementation
    Returns empty structured responses when GraphRAG is disabled
    """

    async def get_related_nodes(
        self,
        yacht_id: str,
        equipment_id: Optional[str] = None,
        fault_code: Optional[str] = None,
        part_id: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 20
    ) -> RelatedNodesResult:
        """Return empty result - GraphRAG not enabled"""
        logger.debug(
            f"[STUBBED] get_related_nodes called: "
            f"equipment_id={equipment_id}, fault_code={fault_code}, part_id={part_id}"
        )
        return RelatedNodesResult(
            nodes=[],
            edges=[],
            total_count=0,
            truncated=False
        )

    async def get_fault_cascade(
        self,
        yacht_id: str,
        equipment_id: str,
        fault_code: str,
        lookback_days: int = 90
    ) -> FaultCascadeResult:
        """Return empty result - GraphRAG not enabled"""
        logger.debug(
            f"[STUBBED] get_fault_cascade called: "
            f"equipment_id={equipment_id}, fault_code={fault_code}"
        )
        return FaultCascadeResult(
            root_fault=None,
            cascade_nodes=[],
            cascade_edges=[],
            affected_equipment=[],
            risk_level="unknown",
            recommended_actions=[]
        )

    async def search(
        self,
        yacht_id: str,
        entities: Any,
        intent: Any,
        max_depth: int = 3
    ) -> GraphSearchResult:
        """Return empty result - GraphRAG not enabled"""
        logger.debug(f"[STUBBED] graph search called for yacht {yacht_id}")
        return GraphSearchResult(
            nodes=[],
            edges=[],
            paths=[],
            insights={
                "total_nodes": 0,
                "total_edges": 0,
                "graph_rag_enabled": False,
                "message": "GraphRAG is currently disabled"
            }
        )


# =============================================================================
# LIVE IMPLEMENTATION (For when GraphRAG is enabled)
# =============================================================================

class LiveGraphRAG(GraphRAGInterface):
    """
    Live GraphRAG implementation using Supabase graph tables
    Only used when settings.graph_rag_enabled = True
    """

    def __init__(self):
        # Import here to avoid circular imports
        from utils.supabase_client import get_supabase_client
        self._get_client = lambda: get_supabase_client(use_service_role=True)

    async def get_related_nodes(
        self,
        yacht_id: str,
        equipment_id: Optional[str] = None,
        fault_code: Optional[str] = None,
        part_id: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 20
    ) -> RelatedNodesResult:
        """Get related nodes via graph traversal"""
        client = self._get_client()
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        try:
            # Build starting conditions
            start_nodes = []

            if equipment_id:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "equipment") \
                    .eq("ref_id", equipment_id) \
                    .execute()
                if result.data:
                    start_nodes.extend(result.data)

            if fault_code:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "fault") \
                    .ilike("label", f"%{fault_code}%") \
                    .execute()
                if result.data:
                    start_nodes.extend(result.data)

            if part_id:
                result = client.table("graph_nodes") \
                    .select("*") \
                    .eq("yacht_id", yacht_id) \
                    .eq("node_type", "part") \
                    .eq("ref_id", part_id) \
                    .execute()
                if result.data:
                    start_nodes.extend(result.data)

            if not start_nodes:
                return RelatedNodesResult(nodes=[], edges=[], total_count=0)

            # BFS traversal
            visited: Set[str] = set()
            queue = [(node["id"], 0) for node in start_nodes]

            for node in start_nodes:
                visited.add(node["id"])
                nodes.append(self._dict_to_node(node))

            while queue and len(nodes) < limit:
                node_id, depth = queue.pop(0)

                if depth >= max_depth:
                    continue

                # Get outgoing edges
                edges_result = client.table("graph_edges") \
                    .select("*, to_node:graph_nodes!to_node_id(*)") \
                    .eq("yacht_id", yacht_id) \
                    .eq("from_node_id", node_id) \
                    .limit(10) \
                    .execute()

                for edge_data in (edges_result.data or []):
                    edges.append(self._dict_to_edge(edge_data))

                    to_node = edge_data.get("to_node")
                    if to_node and to_node["id"] not in visited:
                        visited.add(to_node["id"])
                        nodes.append(self._dict_to_node(to_node))
                        queue.append((to_node["id"], depth + 1))

            return RelatedNodesResult(
                nodes=nodes,
                edges=edges,
                total_count=len(nodes),
                truncated=len(nodes) >= limit
            )

        except Exception as e:
            logger.error(f"get_related_nodes failed: {e}")
            return RelatedNodesResult(nodes=[], edges=[], total_count=0)

    async def get_fault_cascade(
        self,
        yacht_id: str,
        equipment_id: str,
        fault_code: str,
        lookback_days: int = 90
    ) -> FaultCascadeResult:
        """Analyze fault cascade pattern"""
        client = self._get_client()

        try:
            # Get fault history for this equipment
            faults_result = client.table("faults") \
                .select("*") \
                .eq("yacht_id", yacht_id) \
                .eq("equipment_id", equipment_id) \
                .order("detected_at", desc=True) \
                .limit(50) \
                .execute()

            faults = faults_result.data or []

            # Analyze patterns
            fault_codes = [f.get("fault_code") for f in faults if f.get("fault_code")]
            unique_codes = set(fault_codes)
            repeat_count = len(fault_codes) - len(unique_codes)

            # Determine risk level
            if repeat_count >= 5:
                risk_level = "critical"
            elif repeat_count >= 3:
                risk_level = "high"
            elif repeat_count >= 1:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Get related equipment (cascade analysis)
            related_result = await self.get_related_nodes(
                yacht_id=yacht_id,
                equipment_id=equipment_id,
                max_depth=2,
                limit=10
            )

            affected_equipment = [
                n.ref_id for n in related_result.nodes
                if n.node_type == NodeType.EQUIPMENT and n.ref_id != equipment_id
            ]

            # Generate recommendations
            recommendations = []
            if risk_level in ["high", "critical"]:
                recommendations.append("Schedule preventive maintenance")
                recommendations.append("Review related equipment for similar issues")
            if repeat_count > 0:
                recommendations.append(f"Investigate recurring fault pattern ({fault_code})")

            return FaultCascadeResult(
                root_fault=None,  # Would be populated with actual fault node
                cascade_nodes=related_result.nodes,
                cascade_edges=related_result.edges,
                affected_equipment=affected_equipment,
                risk_level=risk_level,
                recommended_actions=recommendations
            )

        except Exception as e:
            logger.error(f"get_fault_cascade failed: {e}")
            return FaultCascadeResult(
                root_fault=None,
                cascade_nodes=[],
                cascade_edges=[],
                affected_equipment=[],
                risk_level="unknown",
                recommended_actions=[]
            )

    async def search(
        self,
        yacht_id: str,
        entities: Any,
        intent: Any,
        max_depth: int = 3
    ) -> GraphSearchResult:
        """Full graph search"""
        # Extract entity IDs
        equipment_ids = getattr(entities, 'equipment', [])
        fault_codes = getattr(entities, 'fault_codes', [])
        part_numbers = getattr(entities, 'part_numbers', [])

        all_nodes: List[GraphNode] = []
        all_edges: List[GraphEdge] = []

        # Search from each entity type
        for equipment in equipment_ids[:3]:  # Limit starting points
            result = await self.get_related_nodes(
                yacht_id=yacht_id,
                equipment_id=None,  # We'd need to resolve name to ID
                max_depth=max_depth,
                limit=15
            )
            all_nodes.extend(result.nodes)
            all_edges.extend(result.edges)

        for fault_code in fault_codes[:2]:
            result = await self.get_related_nodes(
                yacht_id=yacht_id,
                fault_code=fault_code,
                max_depth=max_depth,
                limit=15
            )
            all_nodes.extend(result.nodes)
            all_edges.extend(result.edges)

        # Deduplicate
        seen_nodes: Set[str] = set()
        unique_nodes = []
        for node in all_nodes:
            if node.id not in seen_nodes:
                seen_nodes.add(node.id)
                unique_nodes.append(node)

        seen_edges: Set[str] = set()
        unique_edges = []
        for edge in all_edges:
            if edge.id not in seen_edges:
                seen_edges.add(edge.id)
                unique_edges.append(edge)

        # Generate insights
        node_type_counts = {}
        for node in unique_nodes:
            node_type_counts[node.node_type.value] = node_type_counts.get(node.node_type.value, 0) + 1

        insights = {
            "total_nodes": len(unique_nodes),
            "total_edges": len(unique_edges),
            "node_types": node_type_counts,
            "graph_rag_enabled": True
        }

        return GraphSearchResult(
            nodes=unique_nodes,
            edges=unique_edges,
            paths=[],  # Path extraction would be more complex
            insights=insights
        )

    def _dict_to_node(self, data: Dict[str, Any]) -> GraphNode:
        """Convert dict to GraphNode"""
        return GraphNode(
            id=data.get("id", ""),
            node_type=NodeType(data.get("node_type", "equipment")),
            label=data.get("label", ""),
            ref_id=data.get("ref_id", ""),
            properties=data.get("properties", {}),
            yacht_id=data.get("yacht_id")
        )

    def _dict_to_edge(self, data: Dict[str, Any]) -> GraphEdge:
        """Convert dict to GraphEdge"""
        return GraphEdge(
            id=data.get("id", ""),
            from_node_id=data.get("from_node_id", ""),
            to_node_id=data.get("to_node_id", ""),
            edge_type=EdgeType(data.get("edge_type", "RELATED_WO")),
            weight=data.get("weight", 1.0),
            properties=data.get("properties", {})
        )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

_graph_rag_instance: Optional[GraphRAGInterface] = None


def get_graph_rag() -> GraphRAGInterface:
    """
    Get the appropriate GraphRAG implementation based on feature flag

    Returns:
        GraphRAGInterface implementation (stubbed or live)
    """
    global _graph_rag_instance

    if _graph_rag_instance is None:
        if settings.graph_rag_enabled:
            logger.info("GraphRAG ENABLED - using live implementation")
            _graph_rag_instance = LiveGraphRAG()
        else:
            logger.info("GraphRAG DISABLED - using stubbed implementation")
            _graph_rag_instance = StubbedGraphRAG()

    return _graph_rag_instance


def reset_graph_rag():
    """Reset the singleton (useful for testing)"""
    global _graph_rag_instance
    _graph_rag_instance = None


# =============================================================================
# CONVENIENCE FUNCTIONS (Maintain backward compatibility)
# =============================================================================

async def search_graph(
    query: str,
    yacht_id: str,
    entities: Any,
    intent: Any,
    max_depth: int = None
) -> Dict[str, Any]:
    """
    Backward-compatible search_graph function
    Wraps the new interface for existing code

    Args:
        query: Search query (unused in graph search)
        yacht_id: Yacht ID
        entities: Extracted entities
        intent: Detected intent
        max_depth: Maximum depth

    Returns:
        Dictionary with nodes, edges, paths, insights
    """
    if max_depth is None:
        max_depth = settings.graph_max_depth

    graph_rag = get_graph_rag()
    result = await graph_rag.search(yacht_id, entities, intent, max_depth)

    # Convert to dict format for backward compatibility
    return {
        "nodes": [_node_to_dict(n) for n in result.nodes],
        "edges": [_edge_to_dict(e) for e in result.edges],
        "paths": [[n for n in p.nodes] for p in result.paths],
        "insights": result.insights
    }


async def get_related_nodes(
    yacht_id: str,
    equipment_id: Optional[str] = None,
    fault_code: Optional[str] = None,
    part_id: Optional[str] = None,
    max_depth: int = 2,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get related nodes - convenience function

    Returns:
        Dictionary with nodes, edges, total_count
    """
    graph_rag = get_graph_rag()
    result = await graph_rag.get_related_nodes(
        yacht_id=yacht_id,
        equipment_id=equipment_id,
        fault_code=fault_code,
        part_id=part_id,
        max_depth=max_depth,
        limit=limit
    )

    return {
        "nodes": [_node_to_dict(n) for n in result.nodes],
        "edges": [_edge_to_dict(e) for e in result.edges],
        "total_count": result.total_count,
        "truncated": result.truncated
    }


async def get_fault_cascade(
    yacht_id: str,
    equipment_id: str,
    fault_code: str,
    lookback_days: int = 90
) -> Dict[str, Any]:
    """
    Get fault cascade analysis - convenience function

    Returns:
        Dictionary with cascade analysis
    """
    graph_rag = get_graph_rag()
    result = await graph_rag.get_fault_cascade(
        yacht_id=yacht_id,
        equipment_id=equipment_id,
        fault_code=fault_code,
        lookback_days=lookback_days
    )

    return {
        "root_fault": _node_to_dict(result.root_fault) if result.root_fault else None,
        "cascade_nodes": [_node_to_dict(n) for n in result.cascade_nodes],
        "cascade_edges": [_edge_to_dict(e) for e in result.cascade_edges],
        "affected_equipment": result.affected_equipment,
        "risk_level": result.risk_level,
        "recommended_actions": result.recommended_actions
    }


def _node_to_dict(node: GraphNode) -> Dict[str, Any]:
    """Convert GraphNode to dictionary"""
    return {
        "id": node.id,
        "node_type": node.node_type.value,
        "label": node.label,
        "ref_id": node.ref_id,
        "properties": node.properties,
        "yacht_id": node.yacht_id
    }


def _edge_to_dict(edge: GraphEdge) -> Dict[str, Any]:
    """Convert GraphEdge to dictionary"""
    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "edge_type": edge.edge_type.value,
        "weight": edge.weight,
        "properties": edge.properties
    }
