"""
Equipment Domain Handlers
=========================

Group 1: READ handlers for equipment-related actions.

Handlers:
- view_equipment: Equipment details with manual files
- view_maintenance_history: Work order history
- view_equipment_parts: Parts associated with equipment
- view_linked_faults: Faults for equipment
- view_equipment_manual: Manual sections with PDF files

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

# Import schema components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    FileReference,
    FileType,
    AvailableAction,
    SignedUrlGenerator,
    get_available_actions_for_entity
)

from .schema_mapping import (
    get_table,
    map_equipment_select,
    map_work_order_select,
    map_parts_select,
    map_faults_select,
    normalize_equipment,
    normalize_work_order,
    normalize_part,
    normalize_fault
)

logger = logging.getLogger(__name__)


class EquipmentHandlers:
    """
    Equipment domain READ handlers.

    All methods return Dict in standardized envelope format.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_equipment(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View equipment details.

        Returns:
        - Equipment data (id, label, manufacturer, model, status, etc.)
        - Associated manual files (if any)
        - Available actions for this equipment
        """
        builder = ResponseBuilder("view_equipment", entity_id, "equipment", yacht_id)

        try:
            # Query equipment using actual schema columns
            result = self.db.table(get_table("equipment")).select(
                map_equipment_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result or not result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            equipment = normalize_equipment(result.data)

            # Add computed fields
            equipment["risk_score"] = await self._get_risk_score(entity_id)

            builder.set_data(equipment)

            # Get associated manual files
            files = await self._get_equipment_files(entity_id, yacht_id)
            if files:
                builder.add_files(files)

            # Add available actions
            actions = self._get_equipment_actions(entity_id)
            builder.add_available_actions(actions)

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_maintenance_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View maintenance/work order history for equipment.

        Returns:
        - List of work orders for this equipment
        - Pagination info
        """
        builder = ResponseBuilder("view_maintenance_history", entity_id, "equipment", yacht_id)

        try:
            # Get pagination params
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Query work orders for this equipment using actual table
            result = self.db.table(get_table("work_orders")).select(
                map_work_order_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            # Normalize each work order
            work_orders = [normalize_work_order(wo) for wo in (result.data or [])]
            total_count = result.count or len(work_orders)

            # Build list data structure
            builder.set_data({
                "equipment_id": entity_id,
                "work_orders": work_orders,
                "summary": {
                    "total": total_count,
                    "open": len([wo for wo in work_orders if wo.get("status") in ("open", "in_progress", "pending")]),
                    "completed": len([wo for wo in work_orders if wo.get("status") in ("completed", "closed")])
                }
            })

            builder.set_pagination(offset, limit, total_count)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="create_work_order",
                label="Create Work Order",
                variant="MUTATE",
                icon="plus",
                requires_signature=True,
                confirmation_message="Create new work order for this equipment?"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_maintenance_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_equipment_parts(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View parts associated with equipment.

        Returns:
        - List of parts used by/for this equipment
        - Stock status for each part
        """
        builder = ResponseBuilder("view_equipment_parts", entity_id, "equipment", yacht_id)

        try:
            # Query parts - pms_parts doesn't have equipment_id
            # Instead search by model_compatibility or get all parts for yacht
            result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("yacht_id", yacht_id).limit(50).execute()

            # Normalize parts
            parts = [normalize_part(p) for p in (result.data or [])]

            # Add stock status to each part (defaults since not in current schema)
            for part in parts:
                part["stock_status"] = self._compute_stock_status(part)
                part["is_low_stock"] = part["stock_status"] in ("LOW_STOCK", "OUT_OF_STOCK")

            # Build response
            builder.set_data({
                "equipment_id": entity_id,
                "parts": parts,
                "summary": {
                    "total": len(parts),
                    "low_stock": len([p for p in parts if p.get("is_low_stock")]),
                    "in_stock": len([p for p in parts if p.get("stock_status") == "IN_STOCK"])
                }
            })

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_inventory_item",
                label="View Part Details",
                variant="READ",
                icon="eye"
            ))
            builder.add_available_action(AvailableAction(
                action_id="create_reorder",
                label="Create Reorder",
                variant="MUTATE",
                icon="cart",
                requires_signature=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment_parts failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_linked_faults(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View faults linked to equipment.

        Returns:
        - List of faults for this equipment
        - Severity breakdown
        """
        builder = ResponseBuilder("view_linked_faults", entity_id, "equipment", yacht_id)

        try:
            # Get pagination params
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Query faults for this equipment using actual table
            result = self.db.table(get_table("faults")).select(
                map_faults_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            # Normalize faults
            faults = [normalize_fault(f) for f in (result.data or [])]
            total_count = result.count or len(faults)

            # Compute days open for each fault
            for fault in faults:
                fault["is_active"] = not fault.get("is_resolved", False)
                if fault["is_active"] and fault.get("created_at"):
                    try:
                        reported = datetime.fromisoformat(fault["created_at"].replace("Z", "+00:00"))
                        fault["days_open"] = (datetime.now(timezone.utc) - reported).days
                    except:
                        fault["days_open"] = 0
                else:
                    fault["days_open"] = 0

            builder.set_data({
                "equipment_id": entity_id,
                "faults": faults,
                "summary": {
                    "total": total_count,
                    "active": len([f for f in faults if f.get("is_active")]),
                    "critical": len([f for f in faults if f.get("severity") == "critical"]),
                    "high": len([f for f in faults if f.get("severity") == "high"])
                }
            })

            builder.set_pagination(offset, limit, total_count)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_fault",
                label="View Fault Details",
                variant="READ",
                icon="alert"
            ))
            builder.add_available_action(AvailableAction(
                action_id="report_fault",
                label="Report New Fault",
                variant="MUTATE",
                icon="alert-circle",
                requires_signature=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_linked_faults failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_equipment_manual(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Find manual sections for equipment.

        Returns:
        - Document chunks mentioning this equipment
        - Signed URLs for PDF files
        """
        builder = ResponseBuilder("view_equipment_manual", entity_id, "equipment", yacht_id)

        try:
            # First get equipment name using actual schema
            eq_result = self.db.table(get_table("equipment")).select(
                "name"
            ).eq("id", entity_id).maybe_single().execute()

            if not eq_result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            label = eq_result.data["name"]

            # Search document chunks for this equipment (no FK join available)
            chunks_result = self.db.table("document_chunks").select(
                "id, document_id, section_title, page_number, content"
            ).eq("yacht_id", yacht_id).ilike(
                "content", f"%{label}%"
            ).limit(10).execute()

            chunks = chunks_result.data or []

            # Get document IDs and fetch document info separately
            doc_ids = list(set(c.get("document_id") for c in chunks if c.get("document_id")))

            # Fetch documents
            docs_map = {}
            if doc_ids:
                docs_result = self.db.table("documents").select(
                    "id, filename, storage_path, content_type"
                ).in_("id", doc_ids).execute()

                for doc in (docs_result.data or []):
                    docs_map[doc["id"]] = doc

            # Generate signed URLs for documents
            files = []
            seen_docs = set()

            for chunk in chunks:
                doc_id = chunk.get("document_id")
                if doc_id and doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    doc = docs_map.get(doc_id, {})

                    # Create signed URL
                    if self.url_generator and doc.get("storage_path"):
                        file_ref = self.url_generator.create_file_reference(
                            bucket="documents",
                            path=doc["storage_path"],
                            filename=doc.get("filename", "document.pdf"),
                            file_id=doc_id,
                            display_name=doc.get("filename"),
                            mime_type=doc.get("content_type", "application/pdf"),
                            expires_in_minutes=30
                        )
                        if file_ref:
                            files.append(file_ref.to_dict())

            builder.set_data({
                "equipment_id": entity_id,
                "equipment_label": label,
                "manual_sections": [
                    {
                        "chunk_id": c["id"],
                        "document_id": c.get("document_id"),
                        "section_title": c.get("section_title"),
                        "page_number": c.get("page_number"),
                        "content_preview": c.get("content", "")[:200] + "..." if c.get("content") else ""
                    }
                    for c in chunks
                ],
                "document_count": len(seen_docs)
            })

            if files:
                builder.add_files(files)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_manual_section",
                label="Open Manual",
                variant="READ",
                icon="book",
                is_primary=True
            ))
            builder.add_available_action(AvailableAction(
                action_id="view_related_docs",
                label="Related Documents",
                variant="READ",
                icon="link"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment_manual failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_risk_score(self, equipment_id: str) -> float:
        """Get risk score from predictive_state table"""
        try:
            result = self.db.table("predictive_state").select(
                "risk_score"
            ).eq("equipment_id", equipment_id).maybe_single().execute()

            if result.data:
                return result.data.get("risk_score", 0.0)
        except Exception:
            pass
        return 0.0

    async def _get_equipment_files(
        self,
        equipment_id: str,
        yacht_id: str
    ) -> List[Dict]:
        """Get files associated with equipment (photos, manuals, etc.)"""
        files = []

        if not self.url_generator:
            return files

        try:
            # Get attachments
            result = self.db.table("attachments").select(
                "id, filename, mime_type, storage_path, category"
            ).eq("entity_type", "equipment").eq("entity_id", equipment_id).execute()

            for att in (result.data or []):
                file_ref = self.url_generator.create_file_reference(
                    bucket="attachments",
                    path=att.get("storage_path", ""),
                    filename=att.get("filename", "file"),
                    file_id=att["id"],
                    mime_type=att.get("mime_type"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())

        except Exception as e:
            logger.warning(f"Failed to get equipment files: {e}")

        return files

    def _compute_stock_status(self, part: Dict) -> str:
        """Compute stock status for a part"""
        qty = part.get("quantity", 0) or 0
        min_qty = part.get("min_quantity", 0) or 0
        max_qty = part.get("max_quantity", float("inf")) or float("inf")

        if qty <= 0:
            return "OUT_OF_STOCK"
        elif qty <= min_qty:
            return "LOW_STOCK"
        elif max_qty and qty >= max_qty:
            return "OVERSTOCKED"
        else:
            return "IN_STOCK"

    def _get_equipment_actions(self, equipment_id: str) -> List[AvailableAction]:
        """Get available actions for equipment entity"""
        return [
            AvailableAction(
                action_id="view_maintenance_history",
                label="Maintenance History",
                variant="READ",
                icon="history"
            ),
            AvailableAction(
                action_id="view_equipment_parts",
                label="View Parts",
                variant="READ",
                icon="package"
            ),
            AvailableAction(
                action_id="view_linked_faults",
                label="View Faults",
                variant="READ",
                icon="alert"
            ),
            AvailableAction(
                action_id="view_equipment_manual",
                label="Open Manual",
                variant="READ",
                icon="book"
            ),
            AvailableAction(
                action_id="run_diagnostic",
                label="Run Diagnostic",
                variant="READ",
                icon="search"
            ),
            AvailableAction(
                action_id="create_work_order",
                label="Create Work Order",
                variant="MUTATE",
                icon="plus",
                requires_signature=True,
                confirmation_message="Create work order for this equipment?"
            ),
            AvailableAction(
                action_id="report_fault",
                label="Report Fault",
                variant="MUTATE",
                icon="alert-circle",
                requires_signature=True
            ),
            AvailableAction(
                action_id="add_equipment_note",
                label="Add Note",
                variant="MUTATE",
                icon="message"
            )
        ]


# =============================================================================
# HANDLER REGISTRATION
# =============================================================================

def get_equipment_handlers(supabase_client) -> Dict[str, callable]:
    """
    Get equipment handler functions for registration with ActionExecutor.

    Returns dict mapping action_id to async handler function.
    """
    handlers = EquipmentHandlers(supabase_client)

    return {
        "view_equipment": handlers.view_equipment,
        "view_maintenance_history": handlers.view_maintenance_history,
        "view_equipment_parts": handlers.view_equipment_parts,
        "view_linked_faults": handlers.view_linked_faults,
        "view_equipment_manual": handlers.view_equipment_manual,
    }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("EQUIPMENT HANDLERS - Response Format Test")
    print("=" * 60)

    # Test ResponseBuilder without database
    builder = ResponseBuilder("view_equipment", "eq-test", "equipment", "yacht-test")
    builder.set_data({
        "id": "eq-test",
        "canonical_label": "Main Engine Generator 1",
        "manufacturer": "Caterpillar",
        "model": "3512B",
        "status": "operational",
        "running_hours": 12450,
        "risk_score": 0.23
    })

    builder.add_file({
        "file_id": "doc-001",
        "filename": "CAT_3512B_Manual.pdf",
        "file_type": "pdf",
        "mime_type": "application/pdf",
        "signed_url": "https://example.supabase.co/storage/...",
        "expires_at": "2026-01-06T19:30:00+00:00"
    })

    handlers = EquipmentHandlers(None)
    for action in handlers._get_equipment_actions("eq-test"):
        builder.add_available_action(action)

    response = builder.build(source="test")

    print("\nExample view_equipment response:")
    print(json.dumps(response, indent=2))
