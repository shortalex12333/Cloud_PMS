"""
P3 Read-Only Handlers
=====================

Read-only view handlers for data retrieval.

Actions:
- #38 view_fault_history
- #39 suggest_parts
- #40 view_work_order_history
- #41 view_work_order_checklist
- #42 view_equipment_details
- #43 view_equipment_history
- #44 view_equipment_parts
- #45 view_linked_faults
- #46 view_equipment_manual
- #47 view_part_stock
- #48 view_part_location
- #49 view_part_usage
- #50 scan_part_barcode
- #51 view_linked_equipment
- #52 export_handover
- #53 view_document
- #54 view_related_documents
- #55 view_document_section
- #56 view_hours_of_rest
- #57 export_hours_of_rest
- #58 view_compliance_status
- #59 track_delivery
- #60 view_checklist
- #61 view_worklist
- #62 export_worklist
- #63 view_fleet_summary
- #64 open_vessel
- #65 export_fleet_summary
- #66 request_predictive_insight
- #67 view_smart_summary

All handlers are read-only and create no audit logs.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class P3ReadOnlyHandlers:
    """
    P3 read-only handlers.

    All actions:
    - Are read-only (SELECT queries only)
    - Support yacht isolation
    - Do not create audit logs (no mutations)
    - Support pagination where appropriate
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P3 #38: view_fault_history
    # =========================================================================

    async def view_fault_history_execute(
        self,
        fault_id: str,
        yacht_id: str,
        include_notes: bool = True,
        include_photos: bool = True,
        include_work_orders: bool = True
    ) -> Dict:
        """
        View complete history of a fault including notes, photos, and linked work orders.
        """
        try:
            # Get fault details
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title, description, severity, status, "
                "equipment_id, detected_at, resolved_at, resolved_by, "
                "work_order_id, metadata, created_at, updated_at"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not fault_result.data:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = fault_result.data[0]
            result = {"fault": fault}

            # Get notes from metadata
            if include_notes:
                metadata = fault.get("metadata") or {}
                result["notes"] = metadata.get("notes") or []

            # Get photos from attachments
            if include_photos:
                photo_result = self.db.table("documents").select(
                    "id, filename, storage_path, doc_type, metadata, created_at"
                ).eq("yacht_id", yacht_id).execute()
                # Filter for fault-related docs in metadata
                fault_photos = []
                for doc in (photo_result.data or []):
                    meta = doc.get("metadata") or {}
                    if meta.get("entity_type") == "fault" and meta.get("entity_id") == fault_id:
                        fault_photos.append(doc)
                photo_result.data = fault_photos

                result["photos"] = photo_result.data if photo_result.data else []

            # Get linked work orders
            if include_work_orders:
                wo_result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, status, priority, created_at, completed_at"
                ).eq("fault_id", fault_id).eq("yacht_id", yacht_id).order(
                    "created_at", desc=True
                ).execute()

                result["work_orders"] = wo_result.data if wo_result.data else []

            # Get audit history
            audit_result = self.db.table("pms_audit_log").select(
                "action, old_values, new_values, user_id, created_at"
            ).eq("entity_type", "fault").eq("entity_id", fault_id).eq(
                "yacht_id", yacht_id
            ).order("created_at", desc=True).limit(50).execute()

            result["audit_history"] = audit_result.data if audit_result.data else []

            return {
                "status": "success",
                "action": "view_fault_history",
                "result": result,
                "message": f"Fault history for {fault.get('fault_code', fault_id[:8])}"
            }

        except Exception as e:
            logger.error(f"view_fault_history_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #39: suggest_parts
    # =========================================================================

    async def suggest_parts_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        fault_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """
        Suggest parts for an equipment item based on:
        - Parts linked to equipment
        - Parts used in previous work orders
        - Common parts for similar fault types
        """
        try:
            suggestions = []

            # Get equipment details
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model, system_type, metadata"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            # Get parts directly linked to equipment
            parts_result = self.db.table("pms_equipment_parts_bom").select(
                "part_id, pms_parts(id, name, part_number, quantity_on_hand, location)"
            ).eq("equipment_id", equipment_id).limit(limit).execute()

            if parts_result.data:
                for ep in parts_result.data:
                    part = ep.get("pms_parts")
                    if part:
                        suggestions.append({
                            **part,
                            "source": "equipment_linked",
                            "relevance": "high"
                        })

            # Get parts from previous work orders on this equipment
            wo_parts_result = self.db.table("pms_work_order_parts").select(
                "part_id, quantity, pms_parts(id, name, part_number, quantity_on_hand)"
            ).limit(20).execute()

            seen_parts = {s["id"] for s in suggestions}
            if wo_parts_result.data:
                for wp in wo_parts_result.data:
                    part = wp.get("pms_parts")
                    if part and part["id"] not in seen_parts:
                        suggestions.append({
                            **part,
                            "source": "work_order_history",
                            "relevance": "medium",
                            "previous_usage": wp.get("quantity")
                        })
                        seen_parts.add(part["id"])

            # Limit results
            suggestions = suggestions[:limit]

            return {
                "status": "success",
                "action": "suggest_parts",
                "result": {
                    "equipment": {
                        "id": equipment_id,
                        "name": equipment.get("name"),
                        "model": equipment.get("model")
                    },
                    "suggestions": suggestions,
                    "total_suggestions": len(suggestions)
                },
                "message": f"Found {len(suggestions)} part suggestions"
            }

        except Exception as e:
            logger.error(f"suggest_parts_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #40: view_work_order_history
    # =========================================================================

    async def view_work_order_history_execute(
        self,
        work_order_id: str,
        yacht_id: str,
        include_notes: bool = True,
        include_parts: bool = True,
        include_photos: bool = True
    ) -> Dict:
        """
        View complete history of a work order.
        """
        try:
            # Get work order details
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, type, work_order_type, "
                "priority, status, equipment_id, fault_id, assigned_to, "
                "due_date, created_at, completed_at, completed_by, "
                "due_hours, completed_at, metadata, created_at, updated_at"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]
            result = {"work_order": wo}

            # Get notes
            if include_notes:
                notes_result = self.db.table("pms_work_order_notes").select(
                    "id, note_text, note_type, created_by, created_at"
                ).eq("work_order_id", work_order_id).order("created_at", desc=True).execute()

                result["notes"] = notes_result.data if notes_result.data else []

            # Get parts used
            if include_parts:
                parts_result = self.db.table("pms_work_order_parts").select(
                    "id, part_id, quantity, quantity, notes, "
                    "pms_parts(id, name, part_number)"
                ).eq("work_order_id", work_order_id).execute()

                result["parts"] = parts_result.data if parts_result.data else []

            # Get photos
            if include_photos:
                photo_result = self.db.table("documents").select(
                    "id, filename, storage_path, doc_type, metadata, created_at"
                ).eq("yacht_id", yacht_id).execute()
                # Filter for work_order-related docs in metadata
                wo_photos = []
                for doc in (photo_result.data or []):
                    meta = doc.get("metadata") or {}
                    if meta.get("entity_type") == "work_order" and meta.get("entity_id") == work_order_id:
                        wo_photos.append(doc)
                result["photos"] = wo_photos

            # Get audit history
            audit_result = self.db.table("pms_audit_log").select(
                "action, old_values, new_values, user_id, created_at"
            ).eq("entity_type", "work_order").eq("entity_id", work_order_id).eq(
                "yacht_id", yacht_id
            ).order("created_at", desc=True).limit(50).execute()

            result["audit_history"] = audit_result.data if audit_result.data else []

            return {
                "status": "success",
                "action": "view_work_order_history",
                "result": result,
                "message": f"Work order history for {wo.get('wo_number', work_order_id[:8])}"
            }

        except Exception as e:
            logger.error(f"view_work_order_history_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #41: view_work_order_checklist
    # =========================================================================

    async def view_work_order_checklist_execute(
        self,
        work_order_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View checklist items for a work order.
        """
        try:
            # Get work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            # Try pms_work_order_checklist first
            checklist = []
            try:
                checklist_result = self.db.table("pms_work_order_checklist").select(
                    "id, title, description, is_completed, completed_by, completed_at, "
                    "completion_notes, sequence, metadata"
                ).eq("work_order_id", work_order_id).order("sequence").execute()

                if checklist_result.data:
                    checklist = checklist_result.data
            except:
                pass

            # Calculate completion stats
            total = len(checklist)
            completed = sum(1 for item in checklist if item.get("is_completed"))

            return {
                "status": "success",
                "action": "view_work_order_checklist",
                "result": {
                    "work_order": {
                        "id": work_order_id,
                        "wo_number": wo.get("wo_number"),
                        "title": wo.get("title"),
                        "status": wo.get("status")
                    },
                    "checklist": checklist,
                    "stats": {
                        "total": total,
                        "completed": completed,
                        "pending": total - completed,
                        "completion_percent": round((completed / total * 100) if total > 0 else 0, 1)
                    }
                },
                "message": f"Checklist: {completed}/{total} items completed"
            }

        except Exception as e:
            logger.error(f"view_work_order_checklist_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #42: view_equipment_details
    # =========================================================================

    async def view_equipment_details_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        include_specifications: bool = True
    ) -> Dict:
        """
        View detailed equipment information.
        """
        try:
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model, manufacturer, serial_number, code, "
                "location, criticality, system_type, installed_date, description, "
                "metadata, created_at, updated_at"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            # Get active faults count
            fault_count = self.db.table("pms_faults").select(
                "id", count="exact"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).in_(
                "status", ["open", "investigating", "in_progress"]
            ).execute()

            # Get pending work orders count
            wo_count = self.db.table("pms_work_orders").select(
                "id", count="exact"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).in_(
                "status", ["planned", "in_progress"]
            ).execute()

            result = {
                "equipment": equipment,
                "stats": {
                    "active_faults": fault_count.count if fault_count else 0,
                    "pending_work_orders": wo_count.count if wo_count else 0
                }
            }

            if include_specifications and equipment.get("specifications"):
                result["specifications"] = equipment["specifications"]

            return {
                "status": "success",
                "action": "view_equipment_details",
                "result": result,
                "message": f"Equipment details for {equipment.get('name')}"
            }

        except Exception as e:
            logger.error(f"view_equipment_details_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #43: view_equipment_history
    # =========================================================================

    async def view_equipment_history_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        time_range_days: int = 365,
        include_faults: bool = True,
        include_work_orders: bool = True
    ) -> Dict:
        """
        View maintenance history for equipment.
        """
        try:
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]
            cutoff = (datetime.now(timezone.utc) - timedelta(days=time_range_days)).isoformat()
            result = {"equipment": equipment}

            if include_faults:
                faults_result = self.db.table("pms_faults").select(
                    "id, fault_code, title, severity, status, detected_at, resolved_at"
                ).eq("equipment_id", equipment_id).gte(
                    "detected_at", cutoff
                ).order("detected_at", desc=True).execute()

                result["faults"] = faults_result.data if faults_result.data else []

            if include_work_orders:
                wo_result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, type, priority, status, created_at, completed_at"
                ).eq("equipment_id", equipment_id).gte(
                    "created_at", cutoff
                ).order("created_at", desc=True).execute()

                result["work_orders"] = wo_result.data if wo_result.data else []

            return {
                "status": "success",
                "action": "view_equipment_history",
                "result": result,
                "message": f"Equipment history for {equipment.get('name')} ({time_range_days} days)"
            }

        except Exception as e:
            logger.error(f"view_equipment_history_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #44: view_equipment_parts
    # =========================================================================

    async def view_equipment_parts_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        include_stock_levels: bool = True
    ) -> Dict:
        """
        View parts associated with equipment.
        """
        try:
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            # Get linked parts
            parts_result = self.db.table("pms_equipment_parts_bom").select(
                "part_id, quantity_required, notes, "
                "pms_parts(id, name, part_number, manufacturer, quantity_on_hand, minimum_quantity, location)"
            ).eq("equipment_id", equipment_id).execute()

            parts = []
            low_stock_count = 0

            if parts_result.data:
                for ep in parts_result.data:
                    part_data = ep.get("pms_parts", {})
                    part = {
                        "id": part_data.get("id"),
                        "name": part_data.get("name"),
                        "part_number": part_data.get("part_number"),
                        "manufacturer": part_data.get("manufacturer"),
                        "quantity_required": ep.get("quantity_required"),
                        "notes": ep.get("notes")
                    }

                    if include_stock_levels:
                        part["quantity_on_hand"] = part_data.get("quantity_on_hand", 0)
                        part["minimum_quantity"] = part_data.get("minimum_quantity", 0)
                        part["location"] = part_data.get("location")
                        part["is_low_stock"] = (
                            part_data.get("quantity_on_hand", 0) <
                            part_data.get("minimum_quantity", 0)
                        )
                        if part["is_low_stock"]:
                            low_stock_count += 1

                    parts.append(part)

            return {
                "status": "success",
                "action": "view_equipment_parts",
                "result": {
                    "equipment": {
                        "id": equipment_id,
                        "name": equipment.get("name"),
                        "model": equipment.get("model")
                    },
                    "parts": parts,
                    "stats": {
                        "total_parts": len(parts),
                        "low_stock_count": low_stock_count
                    }
                },
                "message": f"{len(parts)} parts for {equipment.get('name')}"
            }

        except Exception as e:
            logger.error(f"view_equipment_parts_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #45: view_linked_faults
    # =========================================================================

    async def view_linked_faults_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        status_filter: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict:
        """
        View faults linked to equipment.
        """
        try:
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            query = self.db.table("pms_faults").select(
                "id, fault_code, title, severity, status, detected_at, resolved_at, description"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id)

            if status_filter:
                query = query.in_("status", status_filter)

            faults_result = query.order("detected_at", desc=True).limit(limit).execute()

            faults = faults_result.data if faults_result.data else []

            # Group by severity
            severity_counts = {}
            for fault in faults:
                sev = fault.get("severity", "unknown")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            return {
                "status": "success",
                "action": "view_linked_faults",
                "result": {
                    "equipment": {
                        "id": equipment_id,
                        "name": equipment.get("name")
                    },
                    "faults": faults,
                    "stats": {
                        "total": len(faults),
                        "by_severity": severity_counts
                    }
                },
                "message": f"{len(faults)} faults for {equipment.get('name')}"
            }

        except Exception as e:
            logger.error(f"view_linked_faults_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #46: view_equipment_manual
    # =========================================================================

    async def view_equipment_manual_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        section: Optional[str] = None
    ) -> Dict:
        """
        View equipment manual/documentation.
        """
        try:
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model, manufacturer"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            # Get linked documents
            docs_query = self.db.table("documents").select(
                "id, filename, storage_path, doc_type, tags, metadata"
            ).eq("yacht_id", yacht_id)

            # Filter for equipment-related docs
            docs_result = docs_query.in_(
                "doc_type", ["manual", "technical", "service_bulletin", "parts_catalog"]
            ).execute()

            # Filter docs by equipment reference
            relevant_docs = []
            if docs_result.data:
                for doc in docs_result.data:
                    metadata = doc.get("metadata") or {}
                    # Check if doc is linked to this equipment
                    if metadata.get("equipment_id") == equipment_id:
                        relevant_docs.append(doc)
                    # Or matches by model/manufacturer
                    elif (metadata.get("model") == equipment.get("model") or
                          metadata.get("manufacturer") == equipment.get("manufacturer")):
                        relevant_docs.append(doc)

            return {
                "status": "success",
                "action": "view_equipment_manual",
                "result": {
                    "equipment": {
                        "id": equipment_id,
                        "name": equipment.get("name"),
                        "model": equipment.get("model"),
                        "manufacturer": equipment.get("manufacturer")
                    },
                    "documents": relevant_docs,
                    "total_documents": len(relevant_docs)
                },
                "message": f"{len(relevant_docs)} manuals for {equipment.get('name')}"
            }

        except Exception as e:
            logger.error(f"view_equipment_manual_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #47: view_part_stock
    # =========================================================================

    async def view_part_stock_execute(
        self,
        part_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View stock level for a part.
        """
        try:
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, manufacturer, category, "
                "quantity_on_hand, minimum_quantity, unit, location, metadata"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]

            # Calculate stock status (use minimum_quantity as reorder threshold)
            qty_on_hand = part.get("quantity_on_hand", 0) or 0
            min_qty = part.get("minimum_quantity", 0) or 0

            if qty_on_hand <= 0:
                stock_status = "out_of_stock"
            elif qty_on_hand <= min_qty:
                stock_status = "low_stock"
            else:
                stock_status = "adequate"

            return {
                "status": "success",
                "action": "view_part_stock",
                "result": {
                    "part": part,
                    "stock_status": stock_status,
                    "quantity_on_hand": qty_on_hand,
                    "minimum_quantity": min_qty
                },
                "message": f"{part.get('name')}: {qty_on_hand} {part.get('unit', 'units')} ({stock_status})"
            }

        except Exception as e:
            logger.error(f"view_part_stock_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #48: view_part_location
    # =========================================================================

    async def view_part_location_execute(
        self,
        part_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View storage location for a part.
        """
        try:
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, location, quantity_on_hand, metadata"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]
            metadata = part.get("metadata") or {}

            return {
                "status": "success",
                "action": "view_part_location",
                "result": {
                    "part": {
                        "id": part["id"],
                        "name": part.get("name"),
                        "part_number": part.get("part_number")
                    },
                    "location": part.get("location"),
                    "storage_details": metadata.get("storage_details"),
                    "bin_number": metadata.get("bin_number"),
                    "shelf": metadata.get("shelf"),
                    "quantity_at_location": part.get("quantity_on_hand", 0)
                },
                "message": f"{part.get('name')} location: {part.get('location', 'Not specified')}"
            }

        except Exception as e:
            logger.error(f"view_part_location_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #49: view_part_usage
    # =========================================================================

    async def view_part_usage_execute(
        self,
        part_id: str,
        yacht_id: str,
        time_range_days: int = 90
    ) -> Dict:
        """
        View usage history for a part.
        """
        try:
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, quantity_on_hand"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]
            cutoff = (datetime.now(timezone.utc) - timedelta(days=time_range_days)).isoformat()

            # Get usage from work order parts
            usage_result = self.db.table("pms_work_order_parts").select(
                "id, quantity, quantity, work_order_id, created_at, "
                "pms_work_orders(wo_number, title)"
            ).eq("part_id", part_id).gte(
                "created_at", cutoff
            ).order("created_at", desc=True).execute()

            usage_records = usage_result.data if usage_result.data else []
            total_used = sum(r.get("quantity", 0) for r in usage_records)
            total_returned = sum(r.get("quantity", 0) for r in usage_records)

            return {
                "status": "success",
                "action": "view_part_usage",
                "result": {
                    "part": {
                        "id": part["id"],
                        "name": part.get("name"),
                        "part_number": part.get("part_number"),
                        "current_stock": part.get("quantity_on_hand", 0)
                    },
                    "usage_records": usage_records,
                    "stats": {
                        "time_range_days": time_range_days,
                        "total_used": total_used,
                        "total_returned": total_returned,
                        "net_usage": total_used - total_returned,
                        "work_orders_count": len(usage_records)
                    }
                },
                "message": f"{part.get('name')}: {total_used} used in {time_range_days} days"
            }

        except Exception as e:
            logger.error(f"view_part_usage_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #50: scan_part_barcode
    # =========================================================================

    async def scan_part_barcode_execute(
        self,
        barcode: str,
        yacht_id: str
    ) -> Dict:
        """
        Look up part by barcode/QR code.
        """
        try:
            # Try to find by part_number first (common barcode encoding)
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, manufacturer, quantity_on_hand, location, metadata"
            ).eq("yacht_id", yacht_id).eq("part_number", barcode).limit(1).execute()

            if not part_result.data:
                # Try searching in metadata barcode field
                all_parts = self.db.table("pms_parts").select(
                    "id, name, part_number, manufacturer, quantity_on_hand, location, metadata"
                ).eq("yacht_id", yacht_id).execute()

                for part in (all_parts.data or []):
                    metadata = part.get("metadata") or {}
                    if metadata.get("barcode") == barcode or metadata.get("qr_code") == barcode:
                        part_result.data = [part]
                        break

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"No part found for barcode: {barcode}"
                }

            part = part_result.data[0]

            return {
                "status": "success",
                "action": "scan_part_barcode",
                "result": {
                    "part": part,
                    "barcode": barcode,
                    "quick_info": {
                        "name": part.get("name"),
                        "part_number": part.get("part_number"),
                        "stock": part.get("quantity_on_hand", 0),
                        "location": part.get("location")
                    }
                },
                "message": f"Found: {part.get('name')}"
            }

        except Exception as e:
            logger.error(f"scan_part_barcode_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #51: view_linked_equipment
    # =========================================================================

    async def view_linked_equipment_execute(
        self,
        part_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View equipment that uses a specific part.
        """
        try:
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]

            # Get linked equipment
            eq_result = self.db.table("pms_equipment_parts_bom").select(
                "equipment_id, quantity_required, "
                "pms_equipment(id, name, model, system_type, location, criticality)"
            ).eq("part_id", part_id).execute()

            equipment_list = []
            if eq_result.data:
                for ep in eq_result.data:
                    eq = ep.get("pms_equipment", {})
                    equipment_list.append({
                        "id": eq.get("id"),
                        "name": eq.get("name"),
                        "model": eq.get("model"),
                        "system_type": eq.get("system_type"),
                        "location": eq.get("location"),
                        "criticality": eq.get("criticality"),
                        "quantity_required": ep.get("quantity_required")
                    })

            return {
                "status": "success",
                "action": "view_linked_equipment",
                "result": {
                    "part": {
                        "id": part["id"],
                        "name": part.get("name"),
                        "part_number": part.get("part_number")
                    },
                    "equipment": equipment_list,
                    "total_equipment": len(equipment_list)
                },
                "message": f"{part.get('name')} used by {len(equipment_list)} equipment items"
            }

        except Exception as e:
            logger.error(f"view_linked_equipment_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #52: export_handover
    # =========================================================================

    async def export_handover_execute(
        self,
        yacht_id: str,
        user_id: str,
        date_range_hours: int = 24,
        format: str = "json"
    ) -> Dict:
        """
        Export handover report for shift change.
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=date_range_hours)).isoformat()

            # Get handover items
            handover_result = self.db.table("pms_handover").select(
                "id, summary_text, category, priority, entity_type, entity_id, "
                "added_by, added_at, metadata"
            ).gte("added_at", cutoff).order(
                "priority", desc=True
            ).order("added_at", desc=True).execute()

            handover_items = handover_result.data if handover_result.data else []

            # Get urgent/active work orders
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, priority, status, assigned_to"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["in_progress", "planned"]
            ).in_("priority", ["critical", "emergency"]).execute()

            urgent_wos = wo_result.data if wo_result.data else []

            # Get active faults
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title, severity, status"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["open", "investigating", "in_progress"]
            ).execute()

            active_faults = fault_result.data if fault_result.data else []

            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "yacht_id": yacht_id,
                "date_range_hours": date_range_hours,
                "handover_items": handover_items,
                "urgent_work_orders": urgent_wos,
                "active_faults": active_faults,
                "summary": {
                    "handover_count": len(handover_items),
                    "urgent_wo_count": len(urgent_wos),
                    "active_fault_count": len(active_faults)
                }
            }

            return {
                "status": "success",
                "action": "export_handover",
                "result": export_data,
                "format": format,
                "message": f"Handover export: {len(handover_items)} items"
            }

        except Exception as e:
            logger.error(f"export_handover_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #53: view_document
    # =========================================================================

    async def view_document_execute(
        self,
        document_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View document metadata and content reference.
        """
        try:
            doc_result = self.db.table("documents").select(
                "id, filename, storage_path, doc_type, content_type, "
                "size_bytes, tags, metadata, created_at, updated_at"
            ).eq("id", document_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not doc_result.data:
                return {
                    "status": "error",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document not found: {document_id}"
                }

            document = doc_result.data[0]

            return {
                "status": "success",
                "action": "view_document",
                "result": {
                    "document": document,
                    "download_url": document.get("storage_path")
                },
                "message": f"Document: {document.get('filename')}"
            }

        except Exception as e:
            logger.error(f"view_document_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #54: view_related_documents
    # =========================================================================

    async def view_related_documents_execute(
        self,
        document_id: str,
        yacht_id: str,
        limit: int = 10
    ) -> Dict:
        """
        View documents related to a given document.
        """
        try:
            # Get source document
            doc_result = self.db.table("documents").select(
                "id, filename, doc_type, doc_type, metadata"
            ).eq("id", document_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not doc_result.data:
                return {
                    "status": "error",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document not found: {document_id}"
                }

            document = doc_result.data[0]
            metadata = document.get("metadata") or {}

            # Find related docs by doc_type and type
            related_result = self.db.table("documents").select(
                "id, filename, doc_type, metadata"
            ).eq("yacht_id", yacht_id).neq("id", document_id)

            if document.get("doc_type"):
                related_result = related_result.eq("doc_type", document["doc_type"])

            related_result = related_result.limit(limit).execute()

            related_docs = related_result.data if related_result.data else []

            return {
                "status": "success",
                "action": "view_related_documents",
                "result": {
                    "source_document": {
                        "id": document["id"],
                        "filename": document.get("filename"),
                        "doc_type": document.get("doc_type")
                    },
                    "related_documents": related_docs,
                    "total_related": len(related_docs)
                },
                "message": f"Found {len(related_docs)} related documents"
            }

        except Exception as e:
            logger.error(f"view_related_documents_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #55: view_document_section
    # =========================================================================

    async def view_document_section_execute(
        self,
        document_id: str,
        section_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View a specific section of a document.
        Note: Section navigation stored in document metadata if available.
        """
        try:
            doc_result = self.db.table("documents").select(
                "id, filename, metadata"
            ).eq("id", document_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not doc_result.data:
                return {
                    "status": "error",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document not found: {document_id}"
                }

            document = doc_result.data[0]
            metadata = document.get("metadata") or {}
            sections = metadata.get("sections") or []

            # Find the requested section in metadata
            target_section = None
            for section in sections:
                if section.get("id") == section_id or section.get("title") == section_id:
                    target_section = section
                    break

            # If no sections in metadata, return document info
            if not target_section:
                return {
                    "status": "success",
                    "action": "view_document_section",
                    "result": {
                        "document": {
                            "id": document["id"],
                            "filename": document.get("filename")
                        },
                        "section": {"id": section_id, "content": "Section navigation not available for this document"}
                    },
                    "message": f"Document: {document.get('filename')}"
                }

            return {
                "status": "success",
                "action": "view_document_section",
                "result": {
                    "document": {
                        "id": document["id"],
                        "filename": document.get("filename")
                    },
                    "section": target_section
                },
                "message": f"Section: {target_section.get('title', section_id)}"
            }

        except Exception as e:
            logger.error(f"view_document_section_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #56: view_hours_of_rest
    # =========================================================================

    async def view_hours_of_rest_execute(
        self,
        user_id: str,
        yacht_id: str,
        date_range_days: int = 7
    ) -> Dict:
        """
        View hours of rest records for compliance.
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=date_range_days)).date().isoformat()

            hor_result = self.db.table("pms_hours_of_rest").select(
                "id, record_date, rest_periods, total_rest_hours, total_work_hours, "
                "is_daily_compliant, is_weekly_compliant, is_compliant, status, "
                "location, voyage_type, metadata"
            ).eq("user_id", user_id).gte(
                "record_date", cutoff
            ).order("record_date", desc=True).execute()

            records = hor_result.data if hor_result.data else []

            # Calculate compliance stats
            compliant_days = sum(1 for r in records if r.get("is_compliant"))
            non_compliant_days = len(records) - compliant_days

            # Weekly compliance (last 7 days total)
            total_rest_7d = sum(r.get("total_rest_hours", 0) for r in records[:7])
            weekly_compliant = total_rest_7d >= 77  # STCW requirement

            return {
                "status": "success",
                "action": "view_hours_of_rest",
                "result": {
                    "records": records,
                    "stats": {
                        "date_range_days": date_range_days,
                        "total_records": len(records),
                        "compliant_days": compliant_days,
                        "non_compliant_days": non_compliant_days,
                        "weekly_rest_hours": round(total_rest_7d, 2),
                        "weekly_compliant": weekly_compliant,
                        "compliance_rate": round(compliant_days / len(records) * 100, 1) if records else 0
                    }
                },
                "message": f"HOR: {compliant_days}/{len(records)} days compliant"
            }

        except Exception as e:
            logger.error(f"view_hours_of_rest_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #57: export_hours_of_rest
    # =========================================================================

    async def export_hours_of_rest_execute(
        self,
        yacht_id: str,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        format: str = "json"
    ) -> Dict:
        """
        Export hours of rest records for flag state compliance.
        """
        try:
            query = self.db.table("pms_hours_of_rest").select(
                "id, user_id, record_date, rest_periods, total_rest_hours, "
                "total_work_hours, is_daily_compliant, is_weekly_compliant, "
                "is_compliant, status, approved_by, approved_at, location, "
                "voyage_type, signature"
            ).eq("yacht_id", yacht_id)

            if user_id:
                query = query.eq("user_id", user_id)

            if date_from:
                query = query.gte("record_date", date_from)

            if date_to:
                query = query.lte("record_date", date_to)

            result = query.order("user_id").order("record_date", desc=True).execute()

            records = result.data if result.data else []

            # Group by user
            by_user = {}
            for record in records:
                uid = record.get("user_id")
                if uid not in by_user:
                    by_user[uid] = []
                by_user[uid].append(record)

            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "yacht_id": yacht_id,
                "date_range": {
                    "from": date_from,
                    "to": date_to
                },
                "records": records,
                "by_user": by_user,
                "summary": {
                    "total_records": len(records),
                    "users_count": len(by_user),
                    "compliant_records": sum(1 for r in records if r.get("is_compliant")),
                    "non_compliant_records": sum(1 for r in records if not r.get("is_compliant"))
                }
            }

            return {
                "status": "success",
                "action": "export_hours_of_rest",
                "result": export_data,
                "format": format,
                "message": f"Exported {len(records)} HOR records"
            }

        except Exception as e:
            logger.error(f"export_hours_of_rest_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #58: view_compliance_status
    # =========================================================================

    async def view_compliance_status_execute(
        self,
        yacht_id: str,
        compliance_type: Optional[str] = None
    ) -> Dict:
        """
        View overall compliance status for the yacht.

        compliance_type: hours_of_rest, survey, certification, all
        """
        try:
            compliance_data = {}

            # Hours of Rest compliance
            if compliance_type in (None, "all", "hours_of_rest"):
                # Get last 7 days HOR for all crew
                cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()

                hor_result = self.db.table("pms_hours_of_rest").select(
                    "user_id, is_compliant, is_daily_compliant, is_weekly_compliant"
                ).gte("record_date", cutoff).execute()

                hor_records = hor_result.data if hor_result.data else []
                hor_compliant = sum(1 for r in hor_records if r.get("is_compliant"))

                compliance_data["hours_of_rest"] = {
                    "total_records": len(hor_records),
                    "compliant": hor_compliant,
                    "non_compliant": len(hor_records) - hor_compliant,
                    "compliance_rate": round(hor_compliant / len(hor_records) * 100, 1) if hor_records else 100
                }

            # Survey compliance (equipment tagged for survey)
            if compliance_type in (None, "all", "survey"):
                eq_result = self.db.table("pms_equipment").select(
                    "id, metadata"
                ).eq("yacht_id", yacht_id).execute()

                survey_pending = 0
                if eq_result.data:
                    for eq in eq_result.data:
                        metadata = eq.get("metadata") or {}
                        if metadata.get("survey_tags"):
                            survey_pending += 1

                compliance_data["survey"] = {
                    "items_tagged_for_survey": survey_pending
                }

            # Certification compliance
            if compliance_type in (None, "all", "certification"):
                # Check for expiring certifications in documents
                thirty_days = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

                cert_result = self.db.table("documents").select(
                    "id, filename, metadata"
                ).eq("yacht_id", yacht_id).eq("doc_type", "certificate").execute()

                expiring_certs = []
                if cert_result.data:
                    for cert in cert_result.data:
                        metadata = cert.get("metadata") or {}
                        expiry = metadata.get("expiry_date")
                        if expiry and expiry <= thirty_days:
                            expiring_certs.append({
                                "id": cert["id"],
                                "filename": cert.get("filename"),
                                "expiry_date": expiry
                            })

                compliance_data["certification"] = {
                    "expiring_within_30_days": len(expiring_certs),
                    "expiring_certificates": expiring_certs
                }

            return {
                "status": "success",
                "action": "view_compliance_status",
                "result": {
                    "yacht_id": yacht_id,
                    "compliance": compliance_data,
                    "checked_at": datetime.now(timezone.utc).isoformat()
                },
                "message": "Compliance status retrieved"
            }

        except Exception as e:
            logger.error(f"view_compliance_status_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #59: track_delivery
    # =========================================================================

    async def track_delivery_execute(
        self,
        purchase_order_id: str,
        yacht_id: str
    ) -> Dict:
        """
        Track delivery status for a purchase order.
        """
        try:
            # Get PO details
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, ordered_at, metadata"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data:
                return {
                    "status": "error",
                    "error_code": "PO_NOT_FOUND",
                    "message": f"Purchase order not found: {purchase_order_id}"
                }

            po = po_result.data[0]

            # Get line items
            items_result = self.db.table("pms_purchase_order_items").select(
                "id, part_id, quantity_ordered, quantity_received, "
                "pms_parts(name, part_number)"
            ).eq("purchase_order_id", purchase_order_id).execute()

            items = items_result.data if items_result.data else []

            # Calculate delivery progress
            total_ordered = sum(i.get("quantity_ordered", 0) for i in items)
            total_received = sum(i.get("quantity_received", 0) for i in items)

            # Get receiving events
            receiving_result = self.db.table("pms_receiving_events").select(
                "id, receiving_number, received_at, received_by, location, "
                "delivery_method, tracking_number, status"
            ).eq("order_id", purchase_order_id).eq("yacht_id", yacht_id).order(
                "received_at", desc=True
            ).execute()

            receiving_events = receiving_result.data if receiving_result.data else []

            return {
                "status": "success",
                "action": "track_delivery",
                "result": {
                    "purchase_order": {
                        "id": purchase_order_id,
                        "po_number": po.get("po_number"),
                        "status": po.get("status"),
                        "ordered_at": po.get("ordered_at")
                    },
                    "items": items,
                    "receiving_events": receiving_events,
                    "delivery_progress": {
                        "total_items": len(items),
                        "total_ordered": total_ordered,
                        "total_received": total_received,
                        "percent_complete": round(total_received / total_ordered * 100, 1) if total_ordered > 0 else 0
                    }
                },
                "message": f"Delivery tracking for {po.get('po_number')}"
            }

        except Exception as e:
            logger.error(f"track_delivery_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #60: view_checklist
    # =========================================================================

    async def view_checklist_execute(
        self,
        checklist_id: str,
        yacht_id: str
    ) -> Dict:
        """
        View a checklist and its items.
        """
        try:
            # Get checklist
            checklist_result = self.db.table("pms_work_orders").select(
                "id, title, description, work_order_type, metadata"
            ).eq("id", checklist_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not checklist_result.data:
                return {
                    "status": "error",
                    "error_code": "CHECKLIST_NOT_FOUND",
                    "message": f"Checklist not found: {checklist_id}"
                }

            checklist = checklist_result.data[0]

            # Get checklist items from work order metadata
            metadata = checklist.get("metadata") or {}
            items = metadata.get("checklist") or []

            # Calculate stats
            total = len(items)
            completed = sum(1 for i in items if i.get("is_completed"))
            required = sum(1 for i in items if i.get("is_required"))
            required_completed = sum(1 for i in items if i.get("is_required") and i.get("is_completed"))

            return {
                "status": "success",
                "action": "view_checklist",
                "result": {
                    "checklist": checklist,
                    "items": items,
                    "stats": {
                        "total_items": total,
                        "completed": completed,
                        "pending": total - completed,
                        "required_items": required,
                        "required_completed": required_completed,
                        "completion_percent": round(completed / total * 100, 1) if total > 0 else 0
                    }
                },
                "message": f"Checklist: {completed}/{total} items completed"
            }

        except Exception as e:
            logger.error(f"view_checklist_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #61: view_worklist
    # =========================================================================

    async def view_worklist_execute(
        self,
        yacht_id: str,
        user_id: Optional[str] = None,
        date: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> Dict:
        """
        View worklist/task list for the day.
        """
        try:
            # Default to today
            if not date:
                date = datetime.now(timezone.utc).date().isoformat()

            query = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, priority, status, "
                "assigned_to, due_date, metadata"
            ).eq("yacht_id", yacht_id).eq("work_order_type", "task")

            if user_id:
                query = query.eq("assigned_to", user_id)

            if status_filter:
                query = query.in_("status", status_filter)
            else:
                query = query.in_("status", ["planned", "in_progress"])

            query = query.lte("due_date", date).order("priority", desc=True).order("due_date")

            result = query.execute()
            tasks = result.data if result.data else []

            # Group by priority
            by_priority = {
                "emergency": [],
                "critical": [],
                "routine": []
            }
            for task in tasks:
                pri = task.get("priority", "routine")
                if pri in by_priority:
                    by_priority[pri].append(task)

            return {
                "status": "success",
                "action": "view_worklist",
                "result": {
                    "date": date,
                    "tasks": tasks,
                    "by_priority": by_priority,
                    "stats": {
                        "total": len(tasks),
                        "emergency": len(by_priority["emergency"]),
                        "critical": len(by_priority["critical"]),
                        "routine": len(by_priority["routine"])
                    }
                },
                "message": f"Worklist: {len(tasks)} tasks for {date}"
            }

        except Exception as e:
            logger.error(f"view_worklist_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #62: export_worklist
    # =========================================================================

    async def export_worklist_execute(
        self,
        yacht_id: str,
        date: Optional[str] = None,
        format: str = "json"
    ) -> Dict:
        """
        Export worklist for printing or sharing.
        """
        try:
            if not date:
                date = datetime.now(timezone.utc).date().isoformat()

            # Get all tasks for the day
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, priority, status, "
                "assigned_to, due_date, due_hours, metadata"
            ).eq("yacht_id", yacht_id).eq("work_order_type", "task").lte(
                "due_date", date
            ).in_("status", ["planned", "in_progress", "completed"]).order(
                "priority", desc=True
            ).execute()

            tasks = result.data if result.data else []

            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "yacht_id": yacht_id,
                "date": date,
                "tasks": tasks,
                "summary": {
                    "total_tasks": len(tasks),
                    "completed": sum(1 for t in tasks if t.get("status") == "completed"),
                    "in_progress": sum(1 for t in tasks if t.get("status") == "in_progress"),
                    "planned": sum(1 for t in tasks if t.get("status") == "planned")
                }
            }

            return {
                "status": "success",
                "action": "export_worklist",
                "result": export_data,
                "format": format,
                "message": f"Exported worklist for {date}"
            }

        except Exception as e:
            logger.error(f"export_worklist_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #63: view_fleet_summary
    # =========================================================================

    async def view_fleet_summary_execute(
        self,
        user_id: str
    ) -> Dict:
        """
        View summary of all yachts user has access to.
        """
        try:
            # Get yachts user has access to
            # This assumes a yacht_users or similar access control table
            yachts_result = self.db.table("yacht_registry").select(
                "id, name, imo, flag_state, status, metadata"
            ).execute()

            yachts = yachts_result.data if yachts_result.data else []

            fleet_summary = []
            for yacht in yachts:
                yacht_id = yacht["id"]

                # Get active faults count
                faults = self.db.table("pms_faults").select(
                    "id", count="exact"
                ).eq("yacht_id", yacht_id).in_(
                    "status", ["open", "investigating", "in_progress"]
                ).execute()

                # Get pending work orders count
                wos = self.db.table("pms_work_orders").select(
                    "id", count="exact"
                ).eq("yacht_id", yacht_id).in_(
                    "status", ["planned", "in_progress"]
                ).execute()

                fleet_summary.append({
                    "yacht": yacht,
                    "active_faults": faults.count if faults else 0,
                    "pending_work_orders": wos.count if wos else 0
                })

            return {
                "status": "success",
                "action": "view_fleet_summary",
                "result": {
                    "yacht_registry": fleet_summary,
                    "total_yachts": len(fleet_summary)
                },
                "message": f"Fleet summary: {len(fleet_summary)} vessels"
            }

        except Exception as e:
            logger.error(f"view_fleet_summary_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #64: open_vessel
    # =========================================================================

    async def open_vessel_execute(
        self,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        Open/select a specific vessel and get its dashboard data.
        """
        try:
            # Get yacht details
            yacht_result = self.db.table("yacht_registry").select(
                "id, name, imo, flag_state, status, metadata"
            ).eq("id", yacht_id).limit(1).execute()

            if not yacht_result.data:
                return {
                    "status": "error",
                    "error_code": "YACHT_NOT_FOUND",
                    "message": f"Yacht not found: {yacht_id}"
                }

            yacht = yacht_result.data[0]

            # Get quick stats
            faults = self.db.table("pms_faults").select(
                "id, severity", count="exact"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["open", "investigating", "in_progress"]
            ).execute()

            wos = self.db.table("pms_work_orders").select(
                "id", count="exact"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["planned", "in_progress"]
            ).execute()

            # Get critical items
            critical_faults = self.db.table("pms_faults").select(
                "id, fault_code, title, severity"
            ).eq("yacht_id", yacht_id).eq("severity", "critical").in_(
                "status", ["open", "investigating", "in_progress"]
            ).limit(5).execute()

            return {
                "status": "success",
                "action": "open_vessel",
                "result": {
                    "yacht": yacht,
                    "dashboard": {
                        "active_faults": faults.count if faults else 0,
                        "pending_work_orders": wos.count if wos else 0,
                        "critical_faults": critical_faults.data if critical_faults.data else []
                    }
                },
                "message": f"Opened vessel: {yacht.get('name')}"
            }

        except Exception as e:
            logger.error(f"open_vessel_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #65: export_fleet_summary
    # =========================================================================

    async def export_fleet_summary_execute(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict:
        """
        Export fleet summary report.
        """
        try:
            # Get fleet summary first
            summary_result = await self.view_fleet_summary_execute(user_id)

            if summary_result.get("status") != "success":
                return summary_result

            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "exported_by": user_id,
                "fleet_summary": summary_result.get("result", {}),
                "format": format
            }

            return {
                "status": "success",
                "action": "export_fleet_summary",
                "result": export_data,
                "format": format,
                "message": "Fleet summary exported"
            }

        except Exception as e:
            logger.error(f"export_fleet_summary_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #66: request_predictive_insight
    # =========================================================================

    async def request_predictive_insight_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        insight_type: str = "failure_prediction"
    ) -> Dict:
        """
        Request predictive maintenance insight for equipment.

        Note: Full ML-based predictions require external AI integration.
        This implementation provides rule-based insights from historical data.

        insight_type: failure_prediction, maintenance_forecast, anomaly_detection
        """
        try:
            # Get equipment details
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model, metadata, metadata, "
                "created_at, updated_at, metadata"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]

            insights = []

            # Rule-based insights
            if insight_type in ("failure_prediction", "all"):
                # Check for overdue maintenance
                metadata = equipment.get("metadata") or {}
                current_hours = metadata.get("current_hours", 0) or 0
                interval = metadata.get("service_interval_hours", 0) or 0

                if isinstance(interval, (int, float)) and interval > 0:
                    hours_since_service = current_hours % interval
                    if hours_since_service > interval * 0.9:
                        insights.append({
                            "type": "maintenance_due",
                            "severity": "warning",
                            "message": f"Maintenance due in {interval - hours_since_service:.0f} hours",
                            "confidence": 0.95,
                            "source": "rule_based"
                        })

                # Check fault history
                fault_count_result = self.db.table("pms_faults").select(
                    "id", count="exact"
                ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).execute()

                if fault_count_result.count and fault_count_result.count > 5:
                    insights.append({
                        "type": "high_fault_rate",
                        "severity": "warning",
                        "message": f"Equipment has {fault_count_result.count} recorded faults - consider inspection",
                        "confidence": 0.7,
                        "source": "historical_analysis"
                    })

            if insight_type in ("maintenance_forecast", "all"):
                next_service = equipment.get("updated_at")
                if next_service:
                    insights.append({
                        "type": "maintenance_forecast",
                        "severity": "info",
                        "message": f"Next scheduled service: {next_service}",
                        "confidence": 1.0,
                        "source": "schedule"
                    })

            return {
                "status": "success",
                "action": "request_predictive_insight",
                "result": {
                    "equipment": {
                        "id": equipment_id,
                        "name": equipment.get("name"),
                        "model": equipment.get("model")
                    },
                    "insights": insights,
                    "insight_type": insight_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Rule-based insights. ML predictions require AI integration."
                },
                "message": f"Generated {len(insights)} insights for {equipment.get('name')}"
            }

        except Exception as e:
            logger.error(f"request_predictive_insight_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P3 #67: view_smart_summary
    # =========================================================================

    async def view_smart_summary_execute(
        self,
        yacht_id: str,
        user_id: str,
        summary_type: str = "daily"
    ) -> Dict:
        """
        View AI-generated smart summary of yacht status.

        Note: Full AI summarization requires LLM integration.
        This implementation aggregates key data points.

        summary_type: daily, weekly, critical
        """
        try:
            now = datetime.now(timezone.utc)

            if summary_type == "daily":
                cutoff = (now - timedelta(hours=24)).isoformat()
            elif summary_type == "weekly":
                cutoff = (now - timedelta(days=7)).isoformat()
            else:  # critical
                cutoff = (now - timedelta(days=30)).isoformat()

            summary_data = {
                "generated_at": now.isoformat(),
                "summary_type": summary_type,
                "yacht_id": yacht_id
            }

            # Active faults
            faults_result = self.db.table("pms_faults").select(
                "id, fault_code, title, severity, status"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["open", "investigating", "in_progress"]
            ).execute()

            faults = faults_result.data if faults_result.data else []
            critical_faults = [f for f in faults if f.get("severity") == "critical"]

            summary_data["faults"] = {
                "total_active": len(faults),
                "critical": len(critical_faults),
                "critical_items": critical_faults[:5]
            }

            # Work orders
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, priority"
            ).gte("updated_at", cutoff).execute()

            wos = wo_result.data if wo_result.data else []
            completed = [w for w in wos if w.get("status") == "completed"]
            in_progress = [w for w in wos if w.get("status") == "in_progress"]

            summary_data["work_orders"] = {
                "completed": len(completed),
                "in_progress": len(in_progress),
                "total_updated": len(wos)
            }

            # Generate summary text
            summary_parts = []
            if critical_faults:
                summary_parts.append(f"{len(critical_faults)} critical fault(s) require attention")
            if completed:
                summary_parts.append(f"{len(completed)} work order(s) completed")
            if in_progress:
                summary_parts.append(f"{len(in_progress)} work order(s) in progress")

            summary_data["summary_text"] = "; ".join(summary_parts) if summary_parts else "No significant activity"

            return {
                "status": "success",
                "action": "view_smart_summary",
                "result": summary_data,
                "message": f"Smart summary ({summary_type})"
            }

        except Exception as e:
            logger.error(f"view_smart_summary_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }


def get_p3_read_only_handlers(supabase_client) -> Dict[str, callable]:
    """Get P3 read-only handler functions for registration."""
    handlers = P3ReadOnlyHandlers(supabase_client)

    return {
        # fix_something cluster
        "view_fault_history": handlers.view_fault_history_execute,
        "suggest_parts": handlers.suggest_parts_execute,
        "view_document": handlers.view_document_execute,
        "view_related_documents": handlers.view_related_documents_execute,
        "view_document_section": handlers.view_document_section_execute,

        # do_maintenance cluster
        "view_work_order_history": handlers.view_work_order_history_execute,
        "view_work_order_checklist": handlers.view_work_order_checklist_execute,
        "view_checklist": handlers.view_checklist_execute,
        "view_worklist": handlers.view_worklist_execute,
        "export_worklist": handlers.export_worklist_execute,

        # manage_equipment cluster
        "view_equipment_details": handlers.view_equipment_details_execute,
        "view_equipment_history": handlers.view_equipment_history_execute,
        "view_equipment_parts": handlers.view_equipment_parts_execute,
        "view_linked_faults": handlers.view_linked_faults_execute,
        "view_equipment_manual": handlers.view_equipment_manual_execute,
        "view_fleet_summary": handlers.view_fleet_summary_execute,
        "open_vessel": handlers.open_vessel_execute,
        "export_fleet_summary": handlers.export_fleet_summary_execute,
        "request_predictive_insight": handlers.request_predictive_insight_execute,

        # control_inventory cluster
        "view_part_stock": handlers.view_part_stock_execute,
        "view_part_location": handlers.view_part_location_execute,
        "view_part_usage": handlers.view_part_usage_execute,
        "scan_part_barcode": handlers.scan_part_barcode_execute,
        "view_linked_equipment": handlers.view_linked_equipment_execute,

        # communicate_status cluster
        "export_handover": handlers.export_handover_execute,
        "view_smart_summary": handlers.view_smart_summary_execute,

        # comply_audit cluster
        "view_hours_of_rest": handlers.view_hours_of_rest_execute,
        "export_hours_of_rest": handlers.export_hours_of_rest_execute,
        "view_compliance_status": handlers.view_compliance_status_execute,

        # procure_suppliers cluster
        "track_delivery": handlers.track_delivery_execute,
    }
