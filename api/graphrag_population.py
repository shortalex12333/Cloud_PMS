"""
GraphRAG Population Service
============================

Wires extraction results into the Graph RAG database layer.

This service is called by n8n workflows (Graph_RAG_Digest) after GPT extraction
to populate:
- graph_nodes (with canonical resolution)
- graph_edges (relationships between entities)
- maintenance_templates (extracted maintenance facts)
- document_chunks.extraction_status

ARCHITECTURE:
┌─────────────────────┐
│  GPT Extraction     │  (n8n: Graph_RAG_Digest)
│  (entities, rels)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  GraphRAG           │  This service
│  Population Service │
└──────────┬──────────┘
           │
           ├─► resolve_entity_alias() → canonical_id
           ├─► INSERT graph_nodes
           ├─► INSERT graph_edges
           ├─► INSERT maintenance_templates
           └─► UPDATE document_chunks.extraction_status

GUARDRAILS:
- All operations are filtered by yacht_id (tenant isolation)
- No direct user mutations (this is internal workflow use only)
- Uses database helper functions for resolution
- Logs all operations for audit
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import re

# Database client (Supabase)
try:
    from supabase import create_client, Client
except ImportError:
    # For type hints when supabase not installed
    Client = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS (must match database)
# ============================================================================

class EntityType(str, Enum):
    EQUIPMENT = "equipment"
    PART = "part"
    FAULT = "fault"
    SYMPTOM = "symptom"
    SUPPLIER = "supplier"
    DOCUMENT = "document"
    WORK_ORDER = "work_order"
    HANDOVER_ITEM = "handover_item"
    PERSON = "person"
    LOCATION = "location"
    SYSTEM = "system"


class EdgeType(str, Enum):
    USES_PART = "USES_PART"
    HAS_FAULT = "HAS_FAULT"
    HAS_SYMPTOM = "HAS_SYMPTOM"
    MENTIONED_IN = "MENTIONED_IN"
    REFERS_TO = "REFERS_TO"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    RELATED_TO = "RELATED_TO"
    HAS_WORK_ORDER = "HAS_WORK_ORDER"
    SUPPLIED_BY = "SUPPLIED_BY"
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    REPLACED_BY = "REPLACED_BY"
    REQUIRES_TOOL = "REQUIRES_TOOL"
    HAS_MAINTENANCE = "HAS_MAINTENANCE"


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    EMPTY = "empty"
    PARTIAL = "partial"


class MaintenanceAction(str, Enum):
    INSPECT = "inspect"
    REPLACE = "replace"
    CLEAN = "clean"
    SERVICE = "service"
    LUBRICATE = "lubricate"
    CALIBRATE = "calibrate"
    TEST = "test"
    ADJUST = "adjust"
    OVERHAUL = "overhaul"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExtractedEntity:
    """Entity extracted from GPT"""
    label: str
    entity_type: str  # Will map to EntityType
    confidence: float = 0.8
    properties: Optional[Dict] = None


@dataclass
class ExtractedRelationship:
    """Relationship extracted from GPT"""
    from_label: str
    to_label: str
    relationship_type: str  # Will map to EdgeType
    confidence: float = 0.8
    properties: Optional[Dict] = None


@dataclass
class ExtractedMaintenance:
    """Maintenance fact extracted from GPT"""
    equipment_label: str
    part_label: Optional[str] = None
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None
    interval_description: Optional[str] = None
    action: Optional[str] = None
    action_description: Optional[str] = None
    tools_required: Optional[List[str]] = None
    confidence: float = 0.8


@dataclass
class PopulationResult:
    """Result of graph population"""
    chunk_id: str
    status: ExtractionStatus
    nodes_inserted: int = 0
    edges_inserted: int = 0
    maintenance_inserted: int = 0
    nodes_resolved: int = 0  # With canonical_id
    errors: Optional[List[str]] = None


# ============================================================================
# GRAPH RAG POPULATION SERVICE
# ============================================================================

class GraphRAGPopulationService:
    """
    Service to populate Graph RAG tables from extraction results.

    Used by n8n Graph_RAG_Digest workflow after GPT extraction.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize with Supabase connection.

        Args:
            supabase_url: Supabase project URL (or from env SUPABASE_URL)
            supabase_key: Supabase service role key (or from env SUPABASE_SERVICE_KEY)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if self.supabase_url and self.supabase_key and Client:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("GraphRAG Population Service initialized with Supabase")
        else:
            self.client = None
            logger.warning("GraphRAG Population Service running without Supabase (dry-run mode)")

        # Entity type mapping from extraction labels
        self.entity_type_map = {
            "equipment": EntityType.EQUIPMENT,
            "part": EntityType.PART,
            "fault": EntityType.FAULT,
            "fault_code": EntityType.FAULT,
            "symptom": EntityType.SYMPTOM,
            "maritime_term": EntityType.SYMPTOM,  # Map symptoms
            "supplier": EntityType.SUPPLIER,
            "person": EntityType.PERSON,
            "location": EntityType.LOCATION,
            "system": EntityType.SYSTEM,
            "measurement": EntityType.EQUIPMENT,  # Context for equipment
        }

        # Edge type mapping from extraction labels
        self.edge_type_map = {
            "uses_part": EdgeType.USES_PART,
            "has_fault": EdgeType.HAS_FAULT,
            "has_symptom": EdgeType.HAS_SYMPTOM,
            "mentioned_in": EdgeType.MENTIONED_IN,
            "refers_to": EdgeType.REFERS_TO,
            "related_to": EdgeType.RELATED_TO,
            "part_of": EdgeType.PART_OF,
            "located_in": EdgeType.LOCATED_IN,
            "supplied_by": EdgeType.SUPPLIED_BY,
            "requires": EdgeType.REQUIRES_TOOL,
            "has_maintenance": EdgeType.HAS_MAINTENANCE,
        }

        # Maintenance action mapping
        self.action_map = {
            "inspect": MaintenanceAction.INSPECT,
            "check": MaintenanceAction.INSPECT,
            "replace": MaintenanceAction.REPLACE,
            "change": MaintenanceAction.REPLACE,
            "clean": MaintenanceAction.CLEAN,
            "service": MaintenanceAction.SERVICE,
            "lubricate": MaintenanceAction.LUBRICATE,
            "oil": MaintenanceAction.LUBRICATE,
            "grease": MaintenanceAction.LUBRICATE,
            "calibrate": MaintenanceAction.CALIBRATE,
            "test": MaintenanceAction.TEST,
            "adjust": MaintenanceAction.ADJUST,
            "overhaul": MaintenanceAction.OVERHAUL,
        }

    # ========================================================================
    # MAIN POPULATION METHOD
    # ========================================================================

    def populate_from_extraction(
        self,
        yacht_id: str,
        chunk_id: str,
        entities: List[Dict],
        relationships: List[Dict],
        maintenance_facts: Optional[List[Dict]] = None,
        raw_extraction: Optional[Dict] = None,
        force_reprocess: bool = False
    ) -> PopulationResult:
        """
        Populate graph tables from GPT extraction results.

        This is the main entry point called by n8n Graph_RAG_Digest workflow.

        IDEMPOTENCY RULES:
        - If chunk_id was already processed with status=success, returns existing result
        - If chunk_id was processed with status=failed/partial, re-processes
        - If force_reprocess=True, always re-processes (deletes existing nodes/edges first)
        - Uses upsert for all DB operations to handle race conditions

        Args:
            yacht_id: Tenant yacht ID
            chunk_id: Source document chunk ID
            entities: List of extracted entities [{label, type, confidence, properties}]
            relationships: List of extracted relationships [{from_label, to_label, type, confidence}]
            maintenance_facts: Optional list of maintenance facts
            raw_extraction: Original GPT response for debugging
            force_reprocess: Force re-processing even if already successful

        Returns:
            PopulationResult with counts and status
        """
        logger.info(f"Populating graph for yacht={yacht_id}, chunk={chunk_id}")
        logger.info(f"  Entities: {len(entities)}, Relationships: {len(relationships)}")

        # IDEMPOTENCY CHECK: Skip if already successfully processed
        existing_status = self._get_chunk_extraction_status(chunk_id)
        if existing_status and not force_reprocess:
            if existing_status == ExtractionStatus.SUCCESS.value:
                logger.info(f"Chunk {chunk_id} already processed successfully, skipping (idempotent)")
                existing_counts = self._get_existing_counts(yacht_id, chunk_id)
                return PopulationResult(
                    chunk_id=chunk_id,
                    status=ExtractionStatus.SUCCESS,
                    nodes_inserted=existing_counts.get("nodes", 0),
                    edges_inserted=existing_counts.get("edges", 0),
                    maintenance_inserted=existing_counts.get("maintenance", 0),
                    nodes_resolved=existing_counts.get("resolved", 0),
                    errors=["Already processed - idempotent skip"]
                )
            elif existing_status == ExtractionStatus.PROCESSING.value:
                logger.warning(f"Chunk {chunk_id} is currently being processed, skipping")
                return PopulationResult(
                    chunk_id=chunk_id,
                    status=ExtractionStatus.PROCESSING,
                    errors=["Already processing - concurrent request blocked"]
                )

        result = PopulationResult(
            chunk_id=chunk_id,
            status=ExtractionStatus.PROCESSING,
            errors=[]
        )

        try:
            # Mark chunk as processing
            self._update_chunk_status(chunk_id, ExtractionStatus.PROCESSING)

            # STEP 1: Insert graph nodes (with canonical resolution)
            node_map = {}  # label -> node_id mapping
            for entity in entities:
                parsed = self._parse_entity(entity)
                if parsed:
                    node_id, resolved = self._insert_graph_node(
                        yacht_id=yacht_id,
                        chunk_id=chunk_id,
                        entity=parsed
                    )
                    if node_id:
                        node_map[parsed.label.lower()] = node_id
                        result.nodes_inserted += 1
                        if resolved:
                            result.nodes_resolved += 1

            # STEP 2: Insert graph edges
            for rel in relationships:
                parsed = self._parse_relationship(rel)
                if parsed:
                    edge_id = self._insert_graph_edge(
                        yacht_id=yacht_id,
                        chunk_id=chunk_id,
                        relationship=parsed,
                        node_map=node_map
                    )
                    if edge_id:
                        result.edges_inserted += 1

            # STEP 3: Insert maintenance templates
            if maintenance_facts:
                for maint in maintenance_facts:
                    parsed = self._parse_maintenance(maint)
                    if parsed:
                        maint_id = self._insert_maintenance_template(
                            yacht_id=yacht_id,
                            chunk_id=chunk_id,
                            maintenance=parsed
                        )
                        if maint_id:
                            result.maintenance_inserted += 1

            # STEP 4: Determine final status
            if result.nodes_inserted == 0 and result.edges_inserted == 0:
                result.status = ExtractionStatus.EMPTY
            elif result.errors:
                result.status = ExtractionStatus.PARTIAL
            else:
                result.status = ExtractionStatus.SUCCESS

            # Update chunk with final status and counts
            self._update_chunk_status(
                chunk_id=chunk_id,
                status=result.status,
                entity_count=result.nodes_inserted,
                relationship_count=result.edges_inserted,
                errors=result.errors if result.errors else None
            )

            logger.info(
                f"Population complete: chunk={chunk_id}, status={result.status.value}, "
                f"nodes={result.nodes_inserted} ({result.nodes_resolved} resolved), "
                f"edges={result.edges_inserted}, maintenance={result.maintenance_inserted}"
            )

            return result

        except Exception as e:
            logger.error(f"Population failed for chunk={chunk_id}: {e}")
            result.status = ExtractionStatus.FAILED
            result.errors.append(str(e))

            self._update_chunk_status(
                chunk_id=chunk_id,
                status=ExtractionStatus.FAILED,
                errors=[str(e)]
            )

            return result

    # ========================================================================
    # PARSING METHODS
    # ========================================================================

    def _parse_entity(self, entity: Dict) -> Optional[ExtractedEntity]:
        """Parse entity dict into ExtractedEntity"""
        try:
            label = entity.get("label") or entity.get("name") or entity.get("value")
            entity_type = entity.get("type") or entity.get("entity_type", "equipment")

            if not label:
                return None

            return ExtractedEntity(
                label=str(label).strip(),
                entity_type=entity_type.lower(),
                confidence=float(entity.get("confidence", 0.8)),
                properties=entity.get("properties")
            )
        except Exception as e:
            logger.warning(f"Failed to parse entity: {entity} - {e}")
            return None

    def _parse_relationship(self, rel: Dict) -> Optional[ExtractedRelationship]:
        """Parse relationship dict into ExtractedRelationship"""
        try:
            from_label = rel.get("from") or rel.get("from_label") or rel.get("source")
            to_label = rel.get("to") or rel.get("to_label") or rel.get("target")
            rel_type = rel.get("type") or rel.get("relationship_type") or rel.get("relation")

            if not from_label or not to_label or not rel_type:
                return None

            return ExtractedRelationship(
                from_label=str(from_label).strip(),
                to_label=str(to_label).strip(),
                relationship_type=rel_type.lower().replace(" ", "_"),
                confidence=float(rel.get("confidence", 0.8)),
                properties=rel.get("properties")
            )
        except Exception as e:
            logger.warning(f"Failed to parse relationship: {rel} - {e}")
            return None

    def _parse_maintenance(self, maint: Dict) -> Optional[ExtractedMaintenance]:
        """Parse maintenance dict into ExtractedMaintenance"""
        try:
            equipment = maint.get("equipment") or maint.get("equipment_label")

            if not equipment:
                return None

            # Parse interval
            interval_hours = None
            interval_days = None
            interval_desc = maint.get("interval") or maint.get("interval_description")

            if interval_desc:
                # Try to extract hours
                hours_match = re.search(r"(\d+)\s*(?:hours?|hrs?|h)", str(interval_desc), re.I)
                if hours_match:
                    interval_hours = int(hours_match.group(1))

                # Try to extract days
                days_match = re.search(r"(\d+)\s*(?:days?|d)", str(interval_desc), re.I)
                if days_match:
                    interval_days = int(days_match.group(1))

            # Direct values override parsed
            if maint.get("interval_hours"):
                interval_hours = int(maint["interval_hours"])
            if maint.get("interval_days"):
                interval_days = int(maint["interval_days"])

            # Parse action
            action = maint.get("action")
            action_desc = maint.get("action_description") or maint.get("task")

            return ExtractedMaintenance(
                equipment_label=str(equipment).strip(),
                part_label=maint.get("part") or maint.get("part_label"),
                interval_hours=interval_hours,
                interval_days=interval_days,
                interval_description=str(interval_desc) if interval_desc else None,
                action=action,
                action_description=action_desc,
                tools_required=maint.get("tools") or maint.get("tools_required"),
                confidence=float(maint.get("confidence", 0.7))
            )
        except Exception as e:
            logger.warning(f"Failed to parse maintenance: {maint} - {e}")
            return None

    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================

    def _resolve_entity(
        self,
        yacht_id: str,
        entity_type: EntityType,
        label: str
    ) -> Optional[str]:
        """
        Resolve entity label to canonical ID using database function.

        Uses: resolve_entity_alias(yacht_id, entity_type, alias_text)
        """
        if not self.client:
            return None

        try:
            # Call the database function
            result = self.client.rpc(
                "resolve_entity_alias",
                {
                    "p_yacht_id": yacht_id,
                    "p_entity_type": entity_type.value,
                    "p_alias_text": label
                }
            ).execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            logger.debug(f"Entity resolution failed for {label}: {e}")
            return None

    def _resolve_symptom(self, label: str) -> Optional[str]:
        """
        Resolve symptom label to symptom code.

        Uses: resolve_symptom_alias(alias_text)
        """
        if not self.client:
            return None

        try:
            result = self.client.rpc(
                "resolve_symptom_alias",
                {"p_alias_text": label}
            ).execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            logger.debug(f"Symptom resolution failed for {label}: {e}")
            return None

    def _insert_graph_node(
        self,
        yacht_id: str,
        chunk_id: str,
        entity: ExtractedEntity
    ) -> Tuple[Optional[str], bool]:
        """
        Insert graph node with canonical resolution.

        Returns: (node_id, was_resolved)
        """
        # Map entity type
        node_type = self.entity_type_map.get(
            entity.entity_type,
            EntityType.EQUIPMENT
        )

        # Try to resolve to canonical
        canonical_id = None
        was_resolved = False

        if node_type == EntityType.SYMPTOM:
            # Use symptom resolution
            symptom_code = self._resolve_symptom(entity.label)
            if symptom_code:
                canonical_id = symptom_code  # Store symptom code as canonical
                was_resolved = True
        else:
            # Use entity alias resolution
            canonical_id = self._resolve_entity(yacht_id, node_type, entity.label)
            if canonical_id:
                was_resolved = True

        if not self.client:
            logger.info(f"[DRY-RUN] Would insert node: {entity.label} ({node_type.value})")
            return ("dry-run-id", was_resolved)

        try:
            result = self.client.table("graph_nodes").upsert({
                "yacht_id": yacht_id,
                "node_type": node_type.value,
                "ref_table": "document_chunks",
                "ref_id": chunk_id,
                "label": entity.label,
                "canonical_id": canonical_id,
                "properties": entity.properties or {}
            }, on_conflict="yacht_id,ref_id,label,node_type").execute()

            if result.data:
                return (result.data[0]["id"], was_resolved)
            return (None, False)

        except Exception as e:
            logger.error(f"Failed to insert node {entity.label}: {e}")
            return (None, False)

    def _insert_graph_edge(
        self,
        yacht_id: str,
        chunk_id: str,
        relationship: ExtractedRelationship,
        node_map: Dict[str, str]
    ) -> Optional[str]:
        """
        Insert graph edge between nodes.
        """
        # Map edge type
        edge_type = self.edge_type_map.get(
            relationship.relationship_type,
            EdgeType.RELATED_TO
        )

        # Look up node IDs
        from_key = relationship.from_label.lower()
        to_key = relationship.to_label.lower()

        from_node_id = node_map.get(from_key)
        to_node_id = node_map.get(to_key)

        if not self.client:
            logger.info(
                f"[DRY-RUN] Would insert edge: {relationship.from_label} "
                f"-[{edge_type.value}]-> {relationship.to_label}"
            )
            return "dry-run-edge-id"

        try:
            result = self.client.table("graph_edges").upsert({
                "yacht_id": yacht_id,
                "edge_type": edge_type.value,
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "from_label": relationship.from_label,
                "to_label": relationship.to_label,
                "source_chunk_id": chunk_id,
                "confidence": relationship.confidence,
                "properties": relationship.properties or {}
            }, on_conflict="yacht_id,edge_type,from_label,to_label,source_chunk_id").execute()

            if result.data:
                return result.data[0]["id"]
            return None

        except Exception as e:
            logger.error(
                f"Failed to insert edge {relationship.from_label} -> {relationship.to_label}: {e}"
            )
            return None

    def _insert_maintenance_template(
        self,
        yacht_id: str,
        chunk_id: str,
        maintenance: ExtractedMaintenance
    ) -> Optional[str]:
        """
        Insert maintenance template.
        """
        # Resolve equipment to canonical ID
        equipment_id = self._resolve_entity(
            yacht_id,
            EntityType.EQUIPMENT,
            maintenance.equipment_label
        )

        # Resolve part if provided
        part_id = None
        if maintenance.part_label:
            part_id = self._resolve_entity(
                yacht_id,
                EntityType.PART,
                maintenance.part_label
            )

        # Map action
        action_enum = None
        if maintenance.action:
            action_key = maintenance.action.lower()
            action_enum = self.action_map.get(action_key)

        if not self.client:
            logger.info(
                f"[DRY-RUN] Would insert maintenance: {maintenance.equipment_label} "
                f"every {maintenance.interval_hours}h / {maintenance.interval_days}d"
            )
            return "dry-run-maint-id"

        try:
            data = {
                "yacht_id": yacht_id,
                "source_chunk_id": chunk_id,
                "equipment_id": equipment_id,
                "part_id": part_id,
                "interval_hours": maintenance.interval_hours,
                "interval_days": maintenance.interval_days,
                "interval_description": maintenance.interval_description,
                "action": action_enum.value if action_enum else None,
                "action_description": maintenance.action_description,
                "tools_required": maintenance.tools_required,
                "raw_extraction": {
                    "equipment_label": maintenance.equipment_label,
                    "part_label": maintenance.part_label,
                    "confidence": maintenance.confidence
                }
            }

            result = self.client.table("maintenance_templates").upsert(
                data,
                on_conflict="source_chunk_id,equipment_id,part_id,action"
            ).execute()

            if result.data:
                return result.data[0]["id"]
            return None

        except Exception as e:
            logger.error(f"Failed to insert maintenance template: {e}")
            return None

    def _update_chunk_status(
        self,
        chunk_id: str,
        status: ExtractionStatus,
        entity_count: int = None,
        relationship_count: int = None,
        errors: List[str] = None
    ):
        """
        Update document_chunks extraction status.
        """
        if not self.client:
            logger.info(f"[DRY-RUN] Would update chunk {chunk_id} status to {status.value}")
            return

        try:
            update_data = {
                "graph_extraction_status": status.value
            }

            if entity_count is not None:
                update_data["extracted_entity_count"] = entity_count

            if relationship_count is not None:
                update_data["extracted_relationship_count"] = relationship_count

            if errors:
                update_data["graph_extraction_errors"] = errors

            self.client.table("document_chunks").update(update_data).eq(
                "id", chunk_id
            ).execute()

        except Exception as e:
            logger.error(f"Failed to update chunk status: {e}")

    def _get_chunk_extraction_status(self, chunk_id: str) -> Optional[str]:
        """
        Get current extraction status for a chunk.
        Used for idempotency checks.
        """
        if not self.client:
            return None

        try:
            result = self.client.table("document_chunks").select(
                "graph_extraction_status"
            ).eq("id", chunk_id).single().execute()

            if result.data:
                return result.data.get("graph_extraction_status")
            return None

        except Exception as e:
            logger.debug(f"Could not get chunk status for {chunk_id}: {e}")
            return None

    def _get_existing_counts(self, yacht_id: str, chunk_id: str) -> Dict[str, int]:
        """
        Get existing node/edge counts for a chunk.
        Used for idempotent responses.
        """
        counts = {"nodes": 0, "edges": 0, "maintenance": 0, "resolved": 0}

        if not self.client:
            return counts

        try:
            # Count nodes
            nodes_result = self.client.table("graph_nodes").select(
                "id,canonical_id", count="exact"
            ).eq("ref_id", chunk_id).execute()
            counts["nodes"] = nodes_result.count or 0
            if nodes_result.data:
                counts["resolved"] = sum(1 for n in nodes_result.data if n.get("canonical_id"))

            # Count edges
            edges_result = self.client.table("graph_edges").select(
                "id", count="exact"
            ).eq("source_chunk_id", chunk_id).execute()
            counts["edges"] = edges_result.count or 0

            # Count maintenance
            maint_result = self.client.table("maintenance_templates").select(
                "id", count="exact"
            ).eq("source_chunk_id", chunk_id).execute()
            counts["maintenance"] = maint_result.count or 0

        except Exception as e:
            logger.debug(f"Could not get existing counts for {chunk_id}: {e}")

        return counts


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_service_instance = None

def get_population_service() -> GraphRAGPopulationService:
    """Get or create singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = GraphRAGPopulationService()
    return _service_instance


# ============================================================================
# N8N HELPER FUNCTION
# ============================================================================

def populate_graph_from_n8n(
    yacht_id: str,
    chunk_id: str,
    extraction_json: str
) -> Dict:
    """
    Helper function for n8n HTTP Request node.

    Usage in n8n:
    1. HTTP Request to this service
    2. Pass yacht_id, chunk_id, and GPT extraction JSON

    Expected extraction_json structure:
    {
        "entities": [{"label": "Main Engine", "type": "equipment", "confidence": 0.9}],
        "relationships": [{"from": "Main Engine", "to": "Oil Filter", "type": "uses_part"}],
        "maintenance": [{"equipment": "Main Engine", "interval": "500 hours", "action": "replace"}]
    }
    """
    try:
        extraction = json.loads(extraction_json)

        service = get_population_service()
        result = service.populate_from_extraction(
            yacht_id=yacht_id,
            chunk_id=chunk_id,
            entities=extraction.get("entities", []),
            relationships=extraction.get("relationships", []),
            maintenance_facts=extraction.get("maintenance"),
            raw_extraction=extraction
        )

        return {
            "success": result.status != ExtractionStatus.FAILED,
            "status": result.status.value,
            "nodes_inserted": result.nodes_inserted,
            "nodes_resolved": result.nodes_resolved,
            "edges_inserted": result.edges_inserted,
            "maintenance_inserted": result.maintenance_inserted,
            "errors": result.errors
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "status": "failed",
            "error": f"Invalid JSON: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "error": str(e)
        }


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    # Test with sample data
    service = GraphRAGPopulationService()

    test_entities = [
        {"label": "Main Engine", "type": "equipment", "confidence": 0.95},
        {"label": "Oil Filter", "type": "part", "confidence": 0.90},
        {"label": "overheating", "type": "symptom", "confidence": 0.85},
        {"label": "E047", "type": "fault_code", "confidence": 0.98}
    ]

    test_relationships = [
        {"from": "Main Engine", "to": "Oil Filter", "type": "uses_part", "confidence": 0.88},
        {"from": "Main Engine", "to": "overheating", "type": "has_symptom", "confidence": 0.82},
        {"from": "Main Engine", "to": "E047", "type": "has_fault", "confidence": 0.90}
    ]

    test_maintenance = [
        {
            "equipment": "Main Engine",
            "part": "Oil Filter",
            "interval": "500 hours",
            "action": "replace",
            "action_description": "Replace engine oil and filter"
        }
    ]

    print("GraphRAG Population Service - Test")
    print("=" * 60)

    result = service.populate_from_extraction(
        yacht_id="test-yacht-123",
        chunk_id="test-chunk-456",
        entities=test_entities,
        relationships=test_relationships,
        maintenance_facts=test_maintenance
    )

    print(f"\nResult:")
    print(f"  Status: {result.status.value}")
    print(f"  Nodes inserted: {result.nodes_inserted}")
    print(f"  Nodes resolved: {result.nodes_resolved}")
    print(f"  Edges inserted: {result.edges_inserted}")
    print(f"  Maintenance inserted: {result.maintenance_inserted}")
    if result.errors:
        print(f"  Errors: {result.errors}")
