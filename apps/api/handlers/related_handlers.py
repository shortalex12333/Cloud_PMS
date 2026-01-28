"""
Show Related API Handlers (PR #4)
==================================

Fault Lens v1 - Show Related endpoint for entity relationships.

Endpoint: GET /v1/related?entity_type=&entity_id=
- Build "related query object" from entity facts (no user text)
- Retrieval order: FK joins → pms_entity_links → boosting
- Output: focused_entity, groups[], missing_signals[]

Add Related endpoint: POST /v1/related/add (HOD/captain only)
- Creates pms_entity_links row
- Audit {} (non-signed)
- RLS on yacht_id
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class RelatedHandlers:
    """
    Handlers for Show Related and Add Related APIs.

    Implements Fault Lens v1 binding brief:
    - Show Related: deterministic FK/JOIN + pms_entity_links
    - Add Related: HOD/captain only, creates pms_entity_links
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # SHOW RELATED (READ-ONLY)
    # =========================================================================

    async def get_related(
        self,
        yacht_id: str,
        user_id: str,
        entity_type: str,
        entity_id: str,
        limit: int = 20,
    ) -> Dict:
        """
        GET /v1/related?entity_type=&entity_id=

        Returns related entities for the focused entity.

        Retrieval order:
        1. FK joins (fault↔equipment/wo/notes/attachments)
        2. pms_entity_links (curated)
        3. Deterministic boosting (same equipment/system)

        Output contract:
        - focused_entity: {type, id, title, ...}
        - groups[]: {type, items[], match_reasons[], open_action, add_related_enabled}
        - missing_signals[]: signals not found
        """
        try:
            # 1. Get focused entity details
            focused = await self._get_entity_details(yacht_id, entity_type, entity_id)
            if not focused:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"{entity_type} not found: {entity_id}",
                }

            groups = []
            missing_signals = []

            # 2. Get FK-based relations
            fk_relations = await self._get_fk_relations(
                yacht_id, entity_type, entity_id, focused, limit
            )
            groups.extend(fk_relations)

            # 3. Get curated links from pms_entity_links
            curated_links = await self._get_curated_links(
                yacht_id, entity_type, entity_id, limit
            )
            if curated_links:
                groups.append(curated_links)

            # 4. Apply deterministic boosting
            groups = self._apply_boosting(groups, focused)

            # 5. Identify missing signals
            if entity_type == "fault":
                if not any(g["type"] == "equipment" for g in groups):
                    missing_signals.append({
                        "signal": "equipment",
                        "hint": "No equipment linked to this fault",
                    })
                if not any(g["type"] == "work_order" for g in groups):
                    missing_signals.append({
                        "signal": "work_order",
                        "hint": "No work order created for this fault",
                    })

            return {
                "status": "success",
                "focused_entity": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    **focused,
                },
                "groups": groups,
                "missing_signals": missing_signals,
            }

        except Exception as e:
            logger.error(f"get_related failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def _get_entity_details(
        self, yacht_id: str, entity_type: str, entity_id: str
    ) -> Optional[Dict]:
        """Get details for the focused entity."""
        try:
            if entity_type == "fault":
                result = self.db.table("pms_faults").select(
                    "id, fault_code, title, description, severity, status, equipment_id"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if result.data:
                    return {
                        "code": result.data.get("fault_code"),
                        "title": result.data.get("title"),
                        "severity": result.data.get("severity"),
                        "status": result.data.get("status"),
                        "equipment_id": result.data.get("equipment_id"),
                    }

            elif entity_type == "equipment":
                result = self.db.table("pms_equipment").select(
                    "id, name, equipment_type, location, system, status"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if result.data:
                    return {
                        "name": result.data.get("name"),
                        "type": result.data.get("equipment_type"),
                        "location": result.data.get("location"),
                        "system": result.data.get("system"),
                        "status": result.data.get("status"),
                    }

            elif entity_type == "work_order":
                result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, priority, status, equipment_id, fault_id"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if result.data:
                    return {
                        "wo_number": result.data.get("wo_number"),
                        "title": result.data.get("title"),
                        "priority": result.data.get("priority"),
                        "status": result.data.get("status"),
                        "equipment_id": result.data.get("equipment_id"),
                        "fault_id": result.data.get("fault_id"),
                    }

            return None

        except Exception as e:
            logger.warning(f"Failed to get entity details: {e}")
            return None

    async def _get_fk_relations(
        self,
        yacht_id: str,
        entity_type: str,
        entity_id: str,
        focused: Dict,
        limit: int,
    ) -> List[Dict]:
        """Get FK-based relations for the entity."""
        groups = []

        try:
            if entity_type == "fault":
                # FK: fault → equipment
                if focused.get("equipment_id"):
                    eq_result = self.db.table("pms_equipment").select(
                        "id, name, equipment_type, location, system"
                    ).eq("id", focused["equipment_id"]).eq("yacht_id", yacht_id).maybe_single().execute()

                    if eq_result.data:
                        groups.append({
                            "type": "equipment",
                            "items": [{
                                "id": eq_result.data["id"],
                                "name": eq_result.data.get("name"),
                                "subtitle": eq_result.data.get("location"),
                            }],
                            "match_reasons": ["fault_equipment_fk"],
                            "open_action": "view_equipment_detail",
                            "add_related_enabled": True,
                        })

                # FK: work_orders → fault
                wo_result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, status, priority"
                ).eq("fault_id", entity_id).eq("yacht_id", yacht_id).limit(limit).execute()

                if wo_result.data:
                    groups.append({
                        "type": "work_order",
                        "items": [{
                            "id": wo["id"],
                            "wo_number": wo.get("wo_number"),
                            "title": wo.get("title"),
                            "status": wo.get("status"),
                        } for wo in wo_result.data],
                        "match_reasons": ["fault_work_order_fk"],
                        "open_action": "view_work_order_detail",
                        "add_related_enabled": True,
                    })

                # FK: fault_notes → fault
                notes_result = self.db.table("pms_fault_notes").select(
                    "id, text, author_id, created_at"
                ).eq("entity_id", entity_id).eq("yacht_id", yacht_id).limit(limit).execute()

                if notes_result.data:
                    groups.append({
                        "type": "note",
                        "items": [{
                            "id": note["id"],
                            "text": note.get("text", "")[:100],
                            "created_at": note.get("created_at"),
                        } for note in notes_result.data],
                        "match_reasons": ["fault_notes_fk"],
                        "open_action": None,
                        "add_related_enabled": False,
                    })

                # FK: fault_attachments → fault
                attachments_result = self.db.table("pms_fault_attachments").select(
                    "id, filename, storage_path, caption, created_at"
                ).eq("entity_id", entity_id).eq("yacht_id", yacht_id).limit(limit).execute()

                if attachments_result.data:
                    groups.append({
                        "type": "attachment",
                        "items": [{
                            "id": att["id"],
                            "filename": att.get("filename"),
                            "caption": att.get("caption"),
                            "storage_path": att.get("storage_path"),
                        } for att in attachments_result.data],
                        "match_reasons": ["fault_attachments_fk"],
                        "open_action": None,
                        "add_related_enabled": False,
                    })

            elif entity_type == "equipment":
                # FK: faults → equipment
                faults_result = self.db.table("pms_faults").select(
                    "id, fault_code, title, severity, status"
                ).eq("equipment_id", entity_id).eq("yacht_id", yacht_id).order(
                    "created_at", desc=True
                ).limit(limit).execute()

                if faults_result.data:
                    groups.append({
                        "type": "fault",
                        "items": [{
                            "id": f["id"],
                            "fault_code": f.get("fault_code"),
                            "title": f.get("title"),
                            "severity": f.get("severity"),
                            "status": f.get("status"),
                        } for f in faults_result.data],
                        "match_reasons": ["equipment_faults_fk"],
                        "open_action": "view_fault_detail",
                        "add_related_enabled": True,
                    })

                # FK: work_orders → equipment
                wo_result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, status, priority"
                ).eq("equipment_id", entity_id).eq("yacht_id", yacht_id).order(
                    "created_at", desc=True
                ).limit(limit).execute()

                if wo_result.data:
                    groups.append({
                        "type": "work_order",
                        "items": [{
                            "id": wo["id"],
                            "wo_number": wo.get("wo_number"),
                            "title": wo.get("title"),
                            "status": wo.get("status"),
                        } for wo in wo_result.data],
                        "match_reasons": ["equipment_work_orders_fk"],
                        "open_action": "view_work_order_detail",
                        "add_related_enabled": True,
                    })

            elif entity_type == "work_order":
                # FK: work_order → fault
                if focused.get("fault_id"):
                    fault_result = self.db.table("pms_faults").select(
                        "id, fault_code, title, severity, status"
                    ).eq("id", focused["fault_id"]).eq("yacht_id", yacht_id).maybe_single().execute()

                    if fault_result.data:
                        groups.append({
                            "type": "fault",
                            "items": [{
                                "id": fault_result.data["id"],
                                "fault_code": fault_result.data.get("fault_code"),
                                "title": fault_result.data.get("title"),
                                "severity": fault_result.data.get("severity"),
                            }],
                            "match_reasons": ["work_order_fault_fk"],
                            "open_action": "view_fault_detail",
                            "add_related_enabled": True,
                        })

                # FK: work_order → equipment
                if focused.get("equipment_id"):
                    eq_result = self.db.table("pms_equipment").select(
                        "id, name, equipment_type, location"
                    ).eq("id", focused["equipment_id"]).eq("yacht_id", yacht_id).maybe_single().execute()

                    if eq_result.data:
                        groups.append({
                            "type": "equipment",
                            "items": [{
                                "id": eq_result.data["id"],
                                "name": eq_result.data.get("name"),
                                "subtitle": eq_result.data.get("location"),
                            }],
                            "match_reasons": ["work_order_equipment_fk"],
                            "open_action": "view_equipment_detail",
                            "add_related_enabled": True,
                        })

                # ============================================================
                # P1 Show Related: Additional FK Relations for Work Orders
                # ============================================================

                # FK: work_order → parts (via pms_work_order_parts)
                parts_result = self.db.table("pms_work_order_parts").select(
                    "part_id, pms_parts(id, name, part_number)"
                ).eq("work_order_id", entity_id).eq("yacht_id", yacht_id).limit(limit).execute()

                if parts_result.data:
                    part_items = []
                    for row in parts_result.data:
                        part = row.get("pms_parts")
                        if part:
                            part_items.append({
                                "id": part["id"],
                                "name": part.get("name"),
                                "subtitle": f"Part #: {part.get('part_number', 'N/A')}",
                            })
                    if part_items:
                        groups.append({
                            "type": "part",
                            "items": part_items,
                            "match_reasons": ["work_order_parts_fk"],
                            "open_action": "focus",
                            "add_related_enabled": True,
                        })

                # FK: work_order → manuals (via equipment → documents)
                if focused.get("equipment_id"):
                    manuals_result = self.db.table("pms_documents").select(
                        "id, title, doc_type"
                    ).eq("equipment_id", focused["equipment_id"]).eq(
                        "doc_type", "manual"
                    ).eq("yacht_id", yacht_id).limit(limit).execute()

                    if manuals_result.data:
                        groups.append({
                            "type": "manual",
                            "items": [{
                                "id": doc["id"],
                                "title": doc.get("title"),
                                "subtitle": "Equipment manual",
                            } for doc in manuals_result.data],
                            "match_reasons": ["equipment_manual_fk"],
                            "open_action": "focus",
                            "add_related_enabled": True,
                        })

                # FK: work_order → handovers (via equipment → documents)
                if focused.get("equipment_id"):
                    handovers_result = self.db.table("pms_documents").select(
                        "id, title, doc_type, created_at"
                    ).eq("equipment_id", focused["equipment_id"]).eq(
                        "doc_type", "handover"
                    ).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(limit).execute()

                    if handovers_result.data:
                        groups.append({
                            "type": "handover",
                            "items": [{
                                "id": doc["id"],
                                "title": doc.get("title"),
                                "subtitle": doc.get("created_at", "")[:10],
                            } for doc in handovers_result.data],
                            "match_reasons": ["equipment_handover_fk"],
                            "open_action": "focus",
                            "add_related_enabled": True,
                        })

                # FK: work_order → previous work orders (same equipment)
                if focused.get("equipment_id"):
                    previous_wo_result = self.db.table("pms_work_orders").select(
                        "id, wo_number, title, status, created_at"
                    ).eq("equipment_id", focused["equipment_id"]).neq("id", entity_id).is_(
                        "deleted_at", "null"
                    ).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(limit).execute()

                    if previous_wo_result.data:
                        groups.append({
                            "type": "previous_work",
                            "items": [{
                                "id": wo["id"],
                                "wo_number": wo.get("wo_number"),
                                "title": wo.get("title"),
                                "subtitle": wo.get("created_at", "")[:10],
                                "status": wo.get("status"),
                            } for wo in previous_wo_result.data],
                            "match_reasons": ["same_equipment"],
                            "open_action": "focus",
                            "add_related_enabled": True,
                        })

                # FK: work_order → attachments (via pms_work_order_attachments)
                attachments_result = self.db.table("pms_work_order_attachments").select(
                    "document_id, created_at, pms_documents(id, title, mime_type)"
                ).eq("work_order_id", entity_id).eq("yacht_id", yacht_id).order(
                    "created_at", desc=True
                ).limit(limit).execute()

                if attachments_result.data:
                    attachment_items = []
                    for row in attachments_result.data:
                        doc = row.get("pms_documents")
                        if doc:
                            attachment_items.append({
                                "id": doc["id"],
                                "title": doc.get("title"),
                                "subtitle": doc.get("mime_type", "unknown"),
                            })
                    if attachment_items:
                        groups.append({
                            "type": "attachment",
                            "items": attachment_items,
                            "match_reasons": ["work_order_attachment_fk"],
                            "open_action": "focus",
                            "add_related_enabled": True,
                        })

        except Exception as e:
            logger.warning(f"Failed to get FK relations: {e}")

        return groups

    async def _get_curated_links(
        self,
        yacht_id: str,
        entity_type: str,
        entity_id: str,
        limit: int,
    ) -> Optional[Dict]:
        """Get curated links from pms_entity_links."""
        try:
            # Get links where this entity is the source
            source_links = self.db.table("pms_entity_links").select(
                "id, target_entity_type, target_entity_id, link_type, note, created_at"
            ).eq("yacht_id", yacht_id).eq(
                "source_entity_type", entity_type
            ).eq("source_entity_id", entity_id).limit(limit).execute()

            # Get links where this entity is the target
            target_links = self.db.table("pms_entity_links").select(
                "id, source_entity_type, source_entity_id, link_type, note, created_at"
            ).eq("yacht_id", yacht_id).eq(
                "target_entity_type", entity_type
            ).eq("target_entity_id", entity_id).limit(limit).execute()

            items = []

            # Process source links
            if source_links.data:
                for link in source_links.data:
                    items.append({
                        "link_id": link["id"],
                        "entity_type": link["target_entity_type"],
                        "entity_id": link["target_entity_id"],
                        "link_type": link.get("link_type"),
                        "note": link.get("note"),
                        "direction": "outgoing",
                    })

            # Process target links
            if target_links.data:
                for link in target_links.data:
                    items.append({
                        "link_id": link["id"],
                        "entity_type": link["source_entity_type"],
                        "entity_id": link["source_entity_id"],
                        "link_type": link.get("link_type"),
                        "note": link.get("note"),
                        "direction": "incoming",
                    })

            if items:
                return {
                    "type": "curated_link",
                    "items": items,
                    "match_reasons": ["pms_entity_links"],
                    "open_action": None,
                    "add_related_enabled": True,
                }

            return None

        except Exception as e:
            logger.warning(f"Failed to get curated links: {e}")
            return None

    def _apply_boosting(self, groups: List[Dict], focused: Dict) -> List[Dict]:
        """
        Apply deterministic boosting to groups.

        Boosting factors:
        - Same equipment/system
        - Recent items
        - Same vendor/part_number
        """
        # For now, simple ordering by type priority
        type_priority = {
            "equipment": 1,
            "fault": 2,
            "work_order": 3,
            "note": 4,
            "attachment": 5,
            "curated_link": 6,
        }

        groups.sort(key=lambda g: type_priority.get(g["type"], 99))

        return groups

    # =========================================================================
    # ADD RELATED (HOD/CAPTAIN ONLY)
    # =========================================================================

    async def add_related(
        self,
        yacht_id: str,
        user_id: str,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        link_type: str = "related",
        note: Optional[str] = None,
    ) -> Dict:
        """
        POST /v1/related/add

        Create curated link between entities.
        HOD/captain only (enforced at router level).

        Creates pms_entity_links row with:
        - yacht_id (RLS)
        - source/target entity
        - link_type (related, caused_by, resolved_by, etc.)
        - optional note
        """
        try:
            # Validate source entity exists
            source_exists = await self._entity_exists(yacht_id, source_entity_type, source_entity_id)
            if not source_exists:
                return {
                    "status": "error",
                    "error_code": "SOURCE_NOT_FOUND",
                    "message": f"Source {source_entity_type} not found: {source_entity_id}",
                }

            # Validate target entity exists
            target_exists = await self._entity_exists(yacht_id, target_entity_type, target_entity_id)
            if not target_exists:
                return {
                    "status": "error",
                    "error_code": "TARGET_NOT_FOUND",
                    "message": f"Target {target_entity_type} not found: {target_entity_id}",
                }

            # Create link
            now = datetime.now(timezone.utc).isoformat()
            link_data = {
                "yacht_id": yacht_id,
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
                "target_entity_type": target_entity_type,
                "target_entity_id": target_entity_id,
                "link_type": link_type,
                "note": note,
                "created_by": user_id,
                "created_at": now,
            }

            result = self.db.table("pms_entity_links").insert(link_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create link",
                }

            link = result.data[0]

            # Create audit log (signature = {} for non-signed)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_related",
                entity_type="entity_link",
                entity_id=link["id"],
                user_id=user_id,
                new_values={
                    "source": f"{source_entity_type}:{source_entity_id}",
                    "target": f"{target_entity_type}:{target_entity_id}",
                    "link_type": link_type,
                },
            )

            return {
                "status": "success",
                "action": "add_related",
                "result": {
                    "link_id": link["id"],
                    "source_entity_type": source_entity_type,
                    "source_entity_id": source_entity_id,
                    "target_entity_type": target_entity_type,
                    "target_entity_id": target_entity_id,
                    "link_type": link_type,
                },
                "message": f"✓ Link created: {source_entity_type} → {target_entity_type}",
            }

        except Exception as e:
            # Check for unique constraint violation
            if "unique" in str(e).lower():
                return {
                    "status": "error",
                    "error_code": "DUPLICATE_LINK",
                    "message": "This link already exists",
                }

            logger.error(f"add_related failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def _entity_exists(
        self, yacht_id: str, entity_type: str, entity_id: str
    ) -> bool:
        """Check if an entity exists in the database."""
        try:
            table_map = {
                "fault": "pms_faults",
                "equipment": "pms_equipment",
                "work_order": "pms_work_orders",
            }

            table = table_map.get(entity_type)
            if not table:
                return True  # Unknown types pass through

            result = self.db.table(table).select("id").eq(
                "id", entity_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            return result.data is not None

        except Exception:
            return False

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        new_values: Optional[Dict] = None,
    ) -> Optional[str]:
        """Create audit log entry with signature = {} (non-signed)."""
        try:
            audit_data = {
                "yacht_id": yacht_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "new_values": new_values,
                "signature": {},  # INVARIANT: never None
                "metadata": {"source": "lens", "lens": "faults"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_audit_log").insert(audit_data).execute()

            return result.data[0]["id"] if result.data else None

        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
            return None


# =============================================================================
# HANDLER REGISTRATION
# =============================================================================

def get_related_handlers(supabase_client) -> Dict[str, callable]:
    """Get related handler functions for registration."""
    handlers = RelatedHandlers(supabase_client)

    return {
        "get_related": handlers.get_related,
        "add_related": handlers.add_related,
    }


__all__ = [
    "RelatedHandlers",
    "get_related_handlers",
]
