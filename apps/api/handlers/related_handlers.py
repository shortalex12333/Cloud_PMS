"""
Show Related API Handlers (V1 - Work Order Lens P1)
====================================================

V1 Implementation: FK-only retrieval, deterministic ordering, explainable.

Endpoint: GET /v1/related?entity_type=&entity_id=
- FK joins first (parts, manuals, previous_work, attachments)
- pms_entity_links for curated/explicit links
- related_text for explainability (populated by V1 migration)
- No embeddings in V1 (FK-only ordering)

Endpoint: POST /v1/related/add (HOD/captain/manager only)
- Creates pms_entity_links row
- Unique constraint prevents duplicates (409)
- Audit log with signature {}

Ground Truth (TENANT_1 confirmed):
- Tables WITH deleted_at: pms_work_orders, pms_equipment, pms_faults, pms_parts,
  pms_work_order_parts, pms_attachments
- Tables WITHOUT deleted_at: doc_metadata, pms_work_order_notes, pms_entity_links
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Valid link types (enforced in add_related)
VALID_LINK_TYPES = ["related", "reference", "evidence", "manual"]

# Valid entity types
VALID_ENTITY_TYPES = ["work_order", "equipment", "part", "fault", "manual", "attachment", "handover"]


class RelatedHandlers:
    """
    Handlers for Show Related V1 (FK-only retrieval).

    V1 Features:
    - FK-based retrieval (deterministic)
    - related_text for explainability
    - Soft delete filters per ground truth
    - "Who did this last" fields for previous_work
    - No embeddings (seeds future V2)
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # GET /v1/related - View Related Entities
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

        V1: FK-only retrieval with related_text for explainability.

        Returns:
        {
          "status": "success",
          "groups": [...],
          "add_related_enabled": true/false,
          "group_counts": {"parts": 5, ...},
          "missing_signals": [...],
          "metadata": {"limit_per_group": 20, "total_items": 25}
        }
        """
        # Validate entity_type
        if entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}"
            )

        # Validate limit
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")
        if limit > 50:
            raise HTTPException(status_code=400, detail="limit cannot exceed 50")

        try:
            # 1. Verify entity exists (and yacht isolation)
            focused = await self._get_entity_details(yacht_id, entity_type, entity_id)
            if not focused:
                raise HTTPException(
                    status_code=404,
                    detail=f"{entity_type.replace('_', ' ').title()} not found"
                )

            groups = []
            missing_signals = []

            # 2. Route to entity-specific FK retrieval
            if entity_type == "work_order":
                groups, missing_signals = await self._get_work_order_relations(
                    yacht_id, entity_id, focused, limit
                )
            elif entity_type == "equipment":
                groups, missing_signals = await self._get_equipment_relations(
                    yacht_id, entity_id, focused, limit
                )
            elif entity_type == "fault":
                groups, missing_signals = await self._get_fault_relations(
                    yacht_id, entity_id, focused, limit
                )
            else:
                # Generic: just get explicit links
                pass

            # 3. Get explicit links from pms_entity_links
            explicit_group = await self._get_explicit_links(yacht_id, entity_type, entity_id, limit)
            if explicit_group:
                groups.append(explicit_group)

            # 4. Merge explicit links into respective groups (dedupe)
            groups = self._merge_explicit_into_groups(groups)

            # 5. Check if user can add links (HOD/chief/captain/manager)
            add_enabled = await self._is_hod_or_manager(user_id, yacht_id)

            # 6. Build group counts
            group_counts = {g["group_key"]: g["count"] for g in groups if g["count"] > 0}

            # 7. Calculate total items
            total_items = sum(g["count"] for g in groups)

            return {
                "status": "success",
                "groups": groups,
                "add_related_enabled": add_enabled,
                "group_counts": group_counts,
                "missing_signals": missing_signals,
                "metadata": {
                    "limit_per_group": limit,
                    "total_items": total_items
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"get_related failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Work Order Relations (P1 Show Related Primary Use Case)
    # =========================================================================

    async def _get_work_order_relations(
        self,
        yacht_id: str,
        entity_id: str,
        focused: Dict,
        limit: int,
    ) -> tuple[List[Dict], List[str]]:
        """Get all FK-based relations for a work order."""
        groups = []
        missing_signals = []

        # Always add handover omission signal for V1
        missing_signals.append("handover_group_omitted_v1")

        # Group 1: Parts (via pms_work_order_parts)
        parts_group = await self._query_related_parts(yacht_id, entity_id, limit)
        groups.append(parts_group)

        # Group 2: Manuals (via equipment -> doc_metadata)
        equipment_id = focused.get("equipment_id")
        if equipment_id:
            manuals_group = await self._query_related_manuals(yacht_id, equipment_id, limit)
            groups.append(manuals_group)

            # Group 3: Previous Work Orders (same equipment)
            previous_group = await self._query_previous_work(yacht_id, entity_id, equipment_id, limit)
            groups.append(previous_group)
        else:
            missing_signals.append("no_equipment_linked")

        # Group 4: Attachments (via pms_attachments)
        attachments_group = await self._query_related_attachments(yacht_id, entity_id, limit)
        groups.append(attachments_group)

        return groups, missing_signals

    async def _query_related_parts(self, yacht_id: str, work_order_id: str, limit: int) -> Dict:
        """Query 1: Related Parts (FK Join via pms_work_order_parts)."""
        items = []
        try:
            # Use Supabase nested select
            result = self.db.table("pms_work_order_parts").select(
                "created_at, pms_parts(id, name, part_number, related_text)"
            ).eq("work_order_id", work_order_id).eq(
                "yacht_id", yacht_id
            ).is_("deleted_at", "null").order(
                "created_at", desc=True
            ).limit(limit).execute()

            if result.data:
                for row in result.data:
                    part = row.get("pms_parts")
                    if part:
                        items.append({
                            "entity_id": part["id"],
                            "entity_type": "part",
                            "title": part.get("name", "Unknown Part"),
                            "subtitle": f"Part #: {part.get('part_number', 'N/A')}",
                            "related_text": part.get("related_text"),
                            "match_reasons": ["FK:wo_part"],
                            "weight": 100,
                            "open_action": "focus"
                        })

        except Exception as e:
            logger.warning(f"Failed to query related parts: {e}")

        return self._build_group("parts", "Parts", items, limit)

    async def _query_related_manuals(self, yacht_id: str, equipment_id: str, limit: int) -> Dict:
        """Query 2: Related Manuals (via equipment -> doc_metadata)."""
        items = []
        try:
            # doc_metadata has NO deleted_at column
            # Use equipment_ids array containment (GIN index exists)
            result = self.db.rpc("get_equipment_manuals", {
                "p_equipment_id": equipment_id,
                "p_yacht_id": yacht_id,
                "p_limit": limit
            }).execute()

            # Fallback to direct query if RPC doesn't exist
            if not result.data:
                result = self.db.table("doc_metadata").select(
                    "id, filename, updated_at"
                ).contains("equipment_ids", [equipment_id]).eq(
                    "doc_type", "manual"
                ).eq("yacht_id", yacht_id).order(
                    "updated_at", desc=True
                ).limit(limit).execute()

            if result.data:
                for doc in result.data:
                    items.append({
                        "entity_id": doc["id"],
                        "entity_type": "manual",
                        "title": doc.get("filename", "Unknown Manual"),
                        "subtitle": "Equipment manual",
                        "match_reasons": ["FK:equipment"],
                        "weight": 90,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query related manuals: {e}")

        return self._build_group("manuals", "Manuals", items, limit)

    async def _query_previous_work(
        self, yacht_id: str, work_order_id: str, equipment_id: str, limit: int
    ) -> Dict:
        """Query 3: Previous Work Orders (same equipment) with 'who did this last'."""
        items = []
        try:
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, created_at, completed_at,"
                "completed_by, assigned_to, created_by, related_text, last_activity_at"
            ).eq("equipment_id", equipment_id).neq("id", work_order_id).is_(
                "deleted_at", "null"
            ).eq("yacht_id", yacht_id).order(
                "last_activity_at", desc=True, nullsfirst=False
            ).limit(limit).execute()

            if result.data:
                for wo in result.data:
                    # Format subtitle as date
                    created_date = wo.get("created_at", "")[:10] if wo.get("created_at") else ""
                    wo_number = wo.get("wo_number", "")
                    title = wo.get("title", "Untitled")

                    items.append({
                        "entity_id": wo["id"],
                        "entity_type": "work_order",
                        "title": f"{wo_number}: {title}" if wo_number else title,
                        "subtitle": created_date,
                        "related_text": wo.get("related_text"),
                        "completed_by": wo.get("completed_by"),  # "Who did this last"
                        "assigned_to": wo.get("assigned_to"),
                        "created_by": wo.get("created_by"),
                        "status": wo.get("status"),
                        "match_reasons": ["same_equipment"],
                        "weight": 80,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query previous work: {e}")

        return self._build_group("previous_work", "Previous Work Orders", items, limit)

    async def _query_related_attachments(self, yacht_id: str, work_order_id: str, limit: int) -> Dict:
        """Query 5: Related Attachments (via pms_attachments - NOT doc_metadata JSONB)."""
        items = []
        try:
            # pms_attachments HAS deleted_at and description columns
            result = self.db.table("pms_attachments").select(
                "id, filename, description, mime_type, uploaded_at, related_text"
            ).eq("entity_type", "work_order").eq(
                "entity_id", work_order_id
            ).eq("yacht_id", yacht_id).is_(
                "deleted_at", "null"
            ).order("uploaded_at", desc=True).limit(limit).execute()

            if result.data:
                for att in result.data:
                    subtitle = att.get("description") or att.get("mime_type") or "unknown"
                    items.append({
                        "entity_id": att["id"],
                        "entity_type": "attachment",
                        "title": att.get("filename", "Unknown File"),
                        "subtitle": subtitle,
                        "related_text": att.get("related_text"),
                        "match_reasons": ["FK:wo_attachment"],
                        "weight": 100,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query related attachments: {e}")

        return self._build_group("attachments", "Attachments", items, limit)

    # =========================================================================
    # Equipment Relations
    # =========================================================================

    async def _get_equipment_relations(
        self,
        yacht_id: str,
        entity_id: str,
        focused: Dict,
        limit: int,
    ) -> tuple[List[Dict], List[str]]:
        """Get FK-based relations for equipment."""
        groups = []
        missing_signals = []

        # Faults linked to this equipment
        faults_group = await self._query_equipment_faults(yacht_id, entity_id, limit)
        groups.append(faults_group)

        # Work orders on this equipment
        wo_group = await self._query_equipment_work_orders(yacht_id, entity_id, limit)
        groups.append(wo_group)

        return groups, missing_signals

    async def _query_equipment_faults(self, yacht_id: str, equipment_id: str, limit: int) -> Dict:
        """Get faults linked to equipment."""
        items = []
        try:
            result = self.db.table("pms_faults").select(
                "id, title, description, status, related_text"
            ).eq("equipment_id", equipment_id).is_(
                "deleted_at", "null"
            ).eq("yacht_id", yacht_id).order(
                "created_at", desc=True
            ).limit(limit).execute()

            if result.data:
                for fault in result.data:
                    items.append({
                        "entity_id": fault["id"],
                        "entity_type": "fault",
                        "title": fault.get("title", "Untitled Fault"),
                        "subtitle": fault.get("status", ""),
                        "related_text": fault.get("related_text"),
                        "match_reasons": ["FK:equipment_fault"],
                        "weight": 90,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query equipment faults: {e}")

        return self._build_group("faults", "Faults", items, limit)

    async def _query_equipment_work_orders(self, yacht_id: str, equipment_id: str, limit: int) -> Dict:
        """Get work orders on equipment."""
        items = []
        try:
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, created_at, related_text"
            ).eq("equipment_id", equipment_id).is_(
                "deleted_at", "null"
            ).eq("yacht_id", yacht_id).order(
                "created_at", desc=True
            ).limit(limit).execute()

            if result.data:
                for wo in result.data:
                    wo_number = wo.get("wo_number", "")
                    title = wo.get("title", "Untitled")
                    items.append({
                        "entity_id": wo["id"],
                        "entity_type": "work_order",
                        "title": f"{wo_number}: {title}" if wo_number else title,
                        "subtitle": wo.get("status", ""),
                        "related_text": wo.get("related_text"),
                        "match_reasons": ["FK:equipment_wo"],
                        "weight": 80,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query equipment work orders: {e}")

        return self._build_group("work_orders", "Work Orders", items, limit)

    # =========================================================================
    # Fault Relations
    # =========================================================================

    async def _get_fault_relations(
        self,
        yacht_id: str,
        entity_id: str,
        focused: Dict,
        limit: int,
    ) -> tuple[List[Dict], List[str]]:
        """Get FK-based relations for fault."""
        groups = []
        missing_signals = []

        equipment_id = focused.get("equipment_id")
        if equipment_id:
            # Equipment linked to fault
            eq_group = await self._query_fault_equipment(yacht_id, equipment_id, limit)
            groups.append(eq_group)
        else:
            missing_signals.append("no_equipment_linked")

        # Work orders created from fault
        wo_group = await self._query_fault_work_orders(yacht_id, entity_id, limit)
        groups.append(wo_group)

        return groups, missing_signals

    async def _query_fault_equipment(self, yacht_id: str, equipment_id: str, limit: int) -> Dict:
        """Get equipment linked to fault."""
        items = []
        try:
            result = self.db.table("pms_equipment").select(
                "id, name, manufacturer, model, location, related_text"
            ).eq("id", equipment_id).is_(
                "deleted_at", "null"
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            if result.data:
                eq = result.data
                items.append({
                    "entity_id": eq["id"],
                    "entity_type": "equipment",
                    "title": eq.get("name", "Unknown Equipment"),
                    "subtitle": eq.get("location", ""),
                    "related_text": eq.get("related_text"),
                    "match_reasons": ["FK:fault_equipment"],
                    "weight": 100,
                    "open_action": "focus"
                })

        except Exception as e:
            logger.warning(f"Failed to query fault equipment: {e}")

        return self._build_group("equipment", "Equipment", items, limit)

    async def _query_fault_work_orders(self, yacht_id: str, fault_id: str, limit: int) -> Dict:
        """Get work orders created from fault."""
        items = []
        try:
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, created_at, related_text"
            ).eq("fault_id", fault_id).is_(
                "deleted_at", "null"
            ).eq("yacht_id", yacht_id).order(
                "created_at", desc=True
            ).limit(limit).execute()

            if result.data:
                for wo in result.data:
                    wo_number = wo.get("wo_number", "")
                    title = wo.get("title", "Untitled")
                    items.append({
                        "entity_id": wo["id"],
                        "entity_type": "work_order",
                        "title": f"{wo_number}: {title}" if wo_number else title,
                        "subtitle": wo.get("status", ""),
                        "related_text": wo.get("related_text"),
                        "match_reasons": ["FK:fault_wo"],
                        "weight": 90,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query fault work orders: {e}")

        return self._build_group("work_orders", "Work Orders", items, limit)

    # =========================================================================
    # Explicit Links (pms_entity_links)
    # =========================================================================

    async def _get_explicit_links(
        self, yacht_id: str, entity_type: str, entity_id: str, limit: int
    ) -> Optional[Dict]:
        """Query 6: Explicit links from pms_entity_links."""
        items = []
        try:
            # pms_entity_links has NO deleted_at (hard delete only)
            # Get links where this entity is the source
            result = self.db.table("pms_entity_links").select(
                "id, target_entity_type, target_entity_id, link_type, note, created_at"
            ).eq("yacht_id", yacht_id).eq(
                "source_entity_type", entity_type
            ).eq("source_entity_id", entity_id).order(
                "created_at", desc=True
            ).limit(limit).execute()

            if result.data:
                for link in result.data:
                    items.append({
                        "entity_id": link["target_entity_id"],
                        "entity_type": link["target_entity_type"],
                        "title": link.get("note") or "Manually linked",
                        "subtitle": link.get("created_at", "")[:10] if link.get("created_at") else "",
                        "link_id": link["id"],
                        "match_reasons": [f"explicit_link:{link.get('link_type', 'related')}"],
                        "weight": 70,
                        "open_action": "focus"
                    })

        except Exception as e:
            logger.warning(f"Failed to query explicit links: {e}")

        if not items:
            return None

        return self._build_group("explicit_links", "Linked by Crew", items, limit)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _build_group(self, group_key: str, label: str, items: List[Dict], limit: int) -> Dict:
        """Build a standardized group object."""
        return {
            "group_key": group_key,
            "label": label,
            "count": len(items),
            "items": items,
            "limit": limit,
            "has_more": len(items) >= limit
        }

    def _merge_explicit_into_groups(self, groups: List[Dict]) -> List[Dict]:
        """Merge explicit links into respective type groups (dedupe by entity_id)."""
        # Find explicit_links group
        explicit_group = None
        other_groups = []
        for g in groups:
            if g["group_key"] == "explicit_links":
                explicit_group = g
            else:
                other_groups.append(g)

        if not explicit_group:
            return groups

        # Merge explicit items into matching type groups
        for explicit_item in explicit_group["items"]:
            target_type = explicit_item["entity_type"]

            # Find matching group
            for group in other_groups:
                if self._type_matches_group(target_type, group["group_key"]):
                    # Check if already exists (dedupe)
                    existing_ids = {item["entity_id"] for item in group["items"]}
                    if explicit_item["entity_id"] not in existing_ids:
                        group["items"].append(explicit_item)
                        group["count"] = len(group["items"])
                    else:
                        # Merge match_reasons
                        for item in group["items"]:
                            if item["entity_id"] == explicit_item["entity_id"]:
                                item["match_reasons"] = list(set(
                                    item.get("match_reasons", []) +
                                    explicit_item.get("match_reasons", [])
                                ))
                    break

        # Keep explicit_links group for unmatched items
        return other_groups + [explicit_group]

    def _type_matches_group(self, entity_type: str, group_key: str) -> bool:
        """Check if entity_type belongs to group_key."""
        mapping = {
            "part": "parts",
            "manual": "manuals",
            "work_order": "previous_work",
            "attachment": "attachments",
            "equipment": "equipment",
            "fault": "faults",
        }
        return mapping.get(entity_type) == group_key

    async def _get_entity_details(
        self, yacht_id: str, entity_type: str, entity_id: str
    ) -> Optional[Dict]:
        """Get focused entity details for context."""
        try:
            if entity_type == "work_order":
                result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, equipment_id, fault_id, status"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).is_(
                    "deleted_at", "null"
                ).maybe_single().execute()

                if result.data:
                    return {
                        "number": result.data.get("wo_number"),
                        "title": result.data.get("title"),
                        "equipment_id": result.data.get("equipment_id"),
                        "fault_id": result.data.get("fault_id"),
                        "status": result.data.get("status"),
                    }

            elif entity_type == "equipment":
                result = self.db.table("pms_equipment").select(
                    "id, name, manufacturer, model, location, system_type"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).is_(
                    "deleted_at", "null"
                ).maybe_single().execute()

                if result.data:
                    return {
                        "name": result.data.get("name"),
                        "manufacturer": result.data.get("manufacturer"),
                        "model": result.data.get("model"),
                        "location": result.data.get("location"),
                        "system_type": result.data.get("system_type"),
                    }

            elif entity_type == "fault":
                result = self.db.table("pms_faults").select(
                    "id, title, description, status, equipment_id"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).is_(
                    "deleted_at", "null"
                ).maybe_single().execute()

                if result.data:
                    return {
                        "title": result.data.get("title"),
                        "description": result.data.get("description"),
                        "status": result.data.get("status"),
                        "equipment_id": result.data.get("equipment_id"),
                    }

            return None

        except Exception as e:
            logger.warning(f"Failed to get entity details: {e}")
            return None

    async def _is_hod_or_manager(self, user_id: str, yacht_id: str) -> bool:
        """Check if user can add entity links (HOD/chief/captain/manager)."""
        try:
            result = self.db.table("auth_users_roles").select(
                "role"
            ).eq("user_id", user_id).eq("yacht_id", yacht_id).eq(
                "is_active", True
            ).maybe_single().execute()

            if not result.data:
                return False

            role = result.data.get("role", "")
            return role in ["chief_engineer", "chief_officer", "captain", "manager", "hod"]

        except Exception as e:
            logger.warning(f"Failed to check user role: {e}")
            return False

    # =========================================================================
    # POST /v1/related/add - Add Entity Link
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

        Create explicit link between entities.
        HOD/chief/captain/manager only.

        Validations:
        - entity_type in VALID_ENTITY_TYPES
        - link_type in VALID_LINK_TYPES
        - source != target (400)
        - note max 500 chars (400)
        - source exists (404)
        - target exists (404)
        - unique constraint (409)
        """
        # 0. Role check - only HOD/chief/captain/manager can add links
        can_add = await self._is_hod_or_manager(user_id, yacht_id)
        if not can_add:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to create links (HOD/manager required)"
            )

        # 1. Validate entity types
        if source_entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}"
            )
        if target_entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target_entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}"
            )

        # 2. Validate link_type
        if link_type not in VALID_LINK_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid link_type. Must be one of: {', '.join(VALID_LINK_TYPES)}"
            )

        # 3. Prevent self-links
        if source_entity_type == target_entity_type and source_entity_id == target_entity_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot create link to self (source == target)"
            )

        # 4. Validate note length
        if note and len(note) > 500:
            raise HTTPException(
                status_code=400,
                detail="Note cannot exceed 500 characters"
            )

        # 5. Verify source entity exists
        source_exists = await self._entity_exists(yacht_id, source_entity_type, source_entity_id)
        if not source_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Source {source_entity_type.replace('_', ' ')} not found"
            )

        # 6. Verify target entity exists
        target_exists = await self._entity_exists(yacht_id, target_entity_type, target_entity_id)
        if not target_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Target {target_entity_type.replace('_', ' ')} not found"
            )

        # 6.5. Check for duplicate link
        existing = self.db.table("pms_entity_links").select("id").eq(
            "yacht_id", yacht_id
        ).eq(
            "source_entity_type", source_entity_type
        ).eq(
            "source_entity_id", source_entity_id
        ).eq(
            "target_entity_type", target_entity_type
        ).eq(
            "target_entity_id", target_entity_id
        ).limit(1).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=409,
                detail="Link already exists"
            )

        try:
            # 7. Insert link
            link_data = {
                "yacht_id": yacht_id,
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
                "target_entity_type": target_entity_type,
                "target_entity_id": target_entity_id,
                "link_type": link_type,
                "note": note,
                "created_by": user_id,
            }

            result = self.db.table("pms_entity_links").insert(link_data).execute()

            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create link")

            link = result.data[0]

            # 8. Audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_entity_link",
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
                "link_id": link["id"],
                "created_at": link.get("created_at", datetime.now(timezone.utc).isoformat())
            }

        except HTTPException:
            raise
        except Exception as e:
            # Check for unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(
                    status_code=409,
                    detail="Link already exists"
                )
            logger.error(f"add_related failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def _entity_exists(self, yacht_id: str, entity_type: str, entity_id: str) -> bool:
        """Check if entity exists (with soft delete filter where applicable)."""
        try:
            table_map = {
                "work_order": ("pms_work_orders", True),   # has deleted_at
                "equipment": ("pms_equipment", True),      # has deleted_at
                "fault": ("pms_faults", True),             # has deleted_at
                "part": ("pms_parts", True),               # has deleted_at
                "attachment": ("pms_attachments", True),   # has deleted_at
                "manual": ("doc_metadata", False),         # NO deleted_at
                "handover": ("handover_exports", False),   # NO deleted_at
            }

            if entity_type not in table_map:
                return True  # Unknown types pass through

            table, has_deleted_at = table_map[entity_type]

            query = self.db.table(table).select("id").eq(
                "id", entity_id
            ).eq("yacht_id", yacht_id)

            if has_deleted_at:
                query = query.is_("deleted_at", "null")

            result = query.maybe_single().execute()
            return result.data is not None

        except Exception as e:
            logger.warning(f"Failed to check entity existence: {e}")
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
                "signature": {},  # INVARIANT: non-signed action
                "metadata": {"source": "lens", "lens": "work_orders"},
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
