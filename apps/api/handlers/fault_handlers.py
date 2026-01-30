"""
Fault/Diagnostic Domain Handlers
================================

Group 4: READ handlers for fault and diagnostic actions.

Handlers:
- view_fault: Fault details with equipment
- diagnose_fault: Diagnosis analysis with remedies
- run_diagnostic: Equipment diagnostic with sensors
- view_fault_history: Fault history for equipment
- suggest_parts: Parts needed for repair

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
    Severity
)

from .schema_mapping import (
    get_table, map_faults_select, normalize_fault,
    map_equipment_select, normalize_equipment
)

logger = logging.getLogger(__name__)


class FaultHandlers:
    """
    Fault/diagnostic domain READ handlers.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_fault(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View fault details.

        Returns:
        - Fault data with equipment reference
        - Severity and status
        - Related work orders
        """
        builder = ResponseBuilder("view_fault", entity_id, "fault", yacht_id)

        try:
            # Query using actual table (pms_faults)
            result = self.db.table(get_table("faults")).select(
                map_faults_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Fault not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            fault = normalize_fault(result.data)

            # Add computed fields
            fault["is_active"] = not fault.get("is_resolved", False)
            fault["days_open"] = self._days_open(fault)

            # Get related work orders
            wo_count = await self._get_related_work_orders_count(entity_id)
            fault["related_work_orders_count"] = wo_count

            builder.set_data(fault)

            # Get attached files (photos of fault)
            files = await self._get_fault_files(entity_id)
            if files:
                builder.add_files(files)

            # Add actions
            builder.add_available_actions(self._get_fault_actions(fault))

            return builder.build()

        except Exception as e:
            logger.error(f"view_fault failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def diagnose_fault(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Run fault diagnosis analysis.

        Returns:
        - Fault details
        - Diagnostic findings from knowledge graph
        - Suggested remedies from maintenance templates
        """
        builder = ResponseBuilder("diagnose_fault", entity_id, "fault", yacht_id)

        try:
            # Get fault details
            fault_result = self.db.table(get_table("faults")).select(
                map_faults_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not fault_result.data:
                builder.set_error("NOT_FOUND", f"Fault not found: {entity_id}")
                return builder.build()

            fault = normalize_fault(fault_result.data)
            fault_code = fault.get("fault_code")

            # Get diagnostic info from graph edges
            diagnosis = []
            try:
                diag_result = self.db.table("graph_edges").select(
                    "target_node:target_id(id, label, properties)"
                ).eq("source_id", entity_id).eq("edge_type", "DIAGNOSED_BY").execute()

                for d in (diag_result.data or []):
                    if d.get("target_node"):
                        diagnosis.append({
                            "id": d["target_node"].get("id"),
                            "finding": d["target_node"].get("label"),
                            "details": d["target_node"].get("properties", {})
                        })
            except Exception:
                pass

            # Get suggested remedies from maintenance templates
            remedies = []
            if fault_code:
                try:
                    remedy_result = self.db.table("maintenance_templates").select(
                        "id, action, interval_hours, procedure, parts_needed, estimated_time"
                    ).eq("fault_code", fault_code).execute()

                    remedies = remedy_result.data or []
                except Exception:
                    pass

            # Get historical occurrences
            history_count = 0
            try:
                history_result = self.db.table(get_table("faults")).select(
                    "id", count="exact"
                ).eq("yacht_id", yacht_id).eq(
                    "fault_code", fault_code
                ).execute()
                history_count = history_result.count or 0
            except Exception:
                pass

            builder.set_data({
                "fault": fault,
                "diagnosis": {
                    "findings": diagnosis,
                    "finding_count": len(diagnosis)
                },
                "remedies": {
                    "suggested_actions": remedies,
                    "remedy_count": len(remedies)
                },
                "history": {
                    "previous_occurrences": history_count,
                    "fault_code": fault_code
                }
            })

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="suggest_parts",
                label="Suggest Parts",
                variant="READ",
                icon="package"
            ))
            builder.add_available_action(AvailableAction(
                action_id="create_work_order",
                label="Create Work Order",
                variant="MUTATE",
                icon="plus",
                requires_signature=True,
                is_primary=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"diagnose_fault failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def run_diagnostic(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Run diagnostic on equipment.

        entity_id is equipment_id for this handler.

        Returns:
        - Latest sensor readings
        - Predictive state (risk score, anomalies)
        - Active faults
        """
        builder = ResponseBuilder("run_diagnostic", entity_id, "equipment", yacht_id)

        try:
            # Get equipment info
            eq_result = self.db.table(get_table("equipment")).select(
                map_equipment_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not eq_result or not eq_result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            equipment = normalize_equipment(eq_result.data)

            # Get latest sensor readings
            sensors = []
            try:
                sensor_result = self.db.table("sensor_readings").select(
                    "sensor_type, value, unit, timestamp, is_anomaly"
                ).eq("equipment_id", entity_id).order(
                    "timestamp", desc=True
                ).limit(10).execute()
                sensors = sensor_result.data or []
            except Exception:
                pass

            # Get predictive state
            predictive = {}
            try:
                pred_result = self.db.table("predictive_state").select(
                    "risk_score, confidence, anomalies, next_maintenance_due, "
                    "failure_probability, trend"
                ).eq("equipment_id", entity_id).maybe_single().execute()
                predictive = pred_result.data or {}
            except Exception:
                pass

            # Get active faults (pms_faults uses resolved_at to indicate if still active)
            active_faults = []
            try:
                fault_result = self.db.table(get_table("faults")).select(
                    "id, fault_code, severity, detected_at"
                ).eq("equipment_id", entity_id).is_(
                    "resolved_at", "null"
                ).execute()
                active_faults = fault_result.data or []
            except Exception:
                pass

            # Determine overall health status
            health_status = self._compute_health_status(predictive, active_faults)

            builder.set_data({
                "equipment": equipment,
                "sensor_readings": sensors,
                "predictive_state": {
                    "risk_score": predictive.get("risk_score", 0),
                    "confidence": predictive.get("confidence", 0),
                    "failure_probability": predictive.get("failure_probability", 0),
                    "trend": predictive.get("trend", "stable"),
                    "anomalies": predictive.get("anomalies", []),
                    "next_maintenance_due": predictive.get("next_maintenance_due")
                },
                "active_faults": active_faults,
                "health_status": health_status,
                "ran_at": datetime.now(timezone.utc).isoformat()
            })

            # Add actions based on health
            actions = [
                AvailableAction(
                    action_id="view_fault_history",
                    label="Fault History",
                    variant="READ",
                    icon="history"
                )
            ]

            if health_status in ("WARNING", "CRITICAL"):
                actions.insert(0, AvailableAction(
                    action_id="report_fault",
                    label="Report Fault",
                    variant="MUTATE",
                    icon="alert-circle",
                    requires_signature=True,
                    is_primary=True
                ))

            builder.add_available_actions(actions)

            return builder.build()

        except Exception as e:
            logger.error(f"run_diagnostic failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_fault_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View fault history for equipment.

        entity_id can be fault_id or equipment_id.

        Returns:
        - List of faults
        - Severity breakdown
        """
        builder = ResponseBuilder("view_fault_history", entity_id, "fault", yacht_id)

        try:
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Query faults - entity_id could be fault or equipment
            result = self.db.table(get_table("faults")).select(
                "id, fault_code, title, description, severity, detected_at, resolved_at",
                count="exact"
            ).eq("yacht_id", yacht_id).or_(
                f"id.eq.{entity_id},equipment_id.eq.{entity_id}"
            ).order("detected_at", desc=True).range(offset, offset + limit - 1).execute()

            faults = result.data or []
            total_count = result.count or len(faults)

            # Add computed fields
            for fault in faults:
                fault["is_active"] = fault.get("resolved_at") is None
                fault["days_open"] = self._days_open(fault)

            # Compute summary
            summary = {
                "total": total_count,
                "active": len([f for f in faults if f.get("is_active")]),
                "by_severity": {
                    "critical": len([f for f in faults if f.get("severity") == "critical"]),
                    "high": len([f for f in faults if f.get("severity") == "high"]),
                    "medium": len([f for f in faults if f.get("severity") == "medium"]),
                    "low": len([f for f in faults if f.get("severity") == "low"]),
                }
            }

            builder.set_data({
                "entity_id": entity_id,
                "faults": faults,
                "summary": summary
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_fault_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def suggest_parts(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Suggest parts needed for fault repair.

        Returns:
        - List of suggested parts from maintenance templates
        - Current inventory status for each part
        """
        builder = ResponseBuilder("suggest_parts", entity_id, "fault", yacht_id)

        try:
            # Get fault details
            fault_result = self.db.table(get_table("faults")).select(
                "id, fault_code, equipment_id"
            ).eq("id", entity_id).maybe_single().execute()

            if not fault_result.data:
                builder.set_error("NOT_FOUND", f"Fault not found: {entity_id}")
                return builder.build()

            fault = fault_result.data
            fault_code = fault.get("fault_code")

            # Get suggested parts from maintenance templates
            part_names = []
            if fault_code:
                try:
                    template_result = self.db.table("maintenance_templates").select(
                        "parts_needed"
                    ).eq("fault_code", fault_code).execute()

                    for t in (template_result.data or []):
                        if t.get("parts_needed"):
                            if isinstance(t["parts_needed"], list):
                                part_names.extend(t["parts_needed"])
                            elif isinstance(t["parts_needed"], str):
                                part_names.append(t["parts_needed"])
                except Exception:
                    pass

            # Get inventory status for suggested parts
            suggested_parts = []
            if part_names:
                try:
                    parts_result = self.db.table(get_table("parts")).select(
                        "id, name, part_number, description, category"
                    ).eq("yacht_id", yacht_id).in_("name", part_names).execute()

                    for part in (parts_result.data or []):
                        # Note: quantity not in current schema, default to available
                        part["canonical_name"] = part.get("name")
                        part["stock_status"] = "UNKNOWN"
                        part["is_available"] = True  # Default to available
                        suggested_parts.append(part)
                except Exception:
                    pass

            builder.set_data({
                "fault_id": entity_id,
                "fault_code": fault_code,
                "suggested_parts": suggested_parts,
                "summary": {
                    "total_suggested": len(suggested_parts),
                    "available": len([p for p in suggested_parts if p.get("is_available")]),
                    "unavailable": len([p for p in suggested_parts if not p.get("is_available")])
                }
            })

            # Add actions
            unavailable = [p for p in suggested_parts if not p.get("is_available")]
            if unavailable:
                builder.add_available_action(AvailableAction(
                    action_id="create_reorder",
                    label="Order Missing Parts",
                    variant="MUTATE",
                    icon="cart",
                    requires_signature=True,
                    is_primary=True
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"suggest_parts failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _days_open(self, fault: Dict) -> int:
        """Calculate days fault has been open"""
        detected_at = fault.get("detected_at")
        if not detected_at:
            return 0

        try:
            detected = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))

            if fault.get("resolved_at"):
                end = datetime.fromisoformat(fault["resolved_at"].replace("Z", "+00:00"))
            else:
                end = datetime.now(timezone.utc)

            return (end - detected).days
        except Exception:
            return 0

    async def _get_related_work_orders_count(self, fault_id: str) -> int:
        """Get count of work orders related to fault"""
        try:
            result = self.db.table("work_orders").select(
                "id", count="exact"
            ).eq("fault_id", fault_id).execute()
            return result.count or 0
        except Exception:
            return 0

    def _get_bucket_for_attachment(self, entity_type: str, category: str, mime_type: str) -> str:
        """
        Determine storage bucket based on entity type and attachment category.

        CRITICAL: Table name is pms_attachments (NOT attachments).
        DO NOT change to table("attachments"). Linter guard enforced.

        Bucket strategy until pms_attachments.bucket column added:
        - fault + photo/image → pms-discrepancy-photos
        - work_order + photo/image → pms-work-order-photos
        - equipment + photo/image → pms-work-order-photos (shared)
        - manual/document/pdf → documents
        - Default → attachments
        """
        category = (category or "").lower()
        mime_type = (mime_type or "").lower()

        # Photo/image categories - route by entity type
        if category in ("photo", "image") or mime_type.startswith("image/"):
            if entity_type == "fault":
                return "pms-discrepancy-photos"
            elif entity_type in ("work_order", "equipment"):
                return "pms-work-order-photos"

        # Manuals and documents
        if category in ("manual", "document", "pdf") or mime_type == "application/pdf":
            return "documents"

        # Default: generic attachments bucket
        return "attachments"

    async def _get_fault_files(self, fault_id: str) -> List[Dict]:
        """Get files attached to fault"""
        files = []

        if not self.url_generator:
            return files

        try:
            # CRITICAL: Use pms_attachments (NOT attachments) - see soft delete migration
            result = self.db.table("pms_attachments").select(
                "id, filename, mime_type, storage_path, category"
            ).eq("entity_type", "fault").eq("entity_id", fault_id).is_(
                "deleted_at", "null"  # Soft delete filter required
            ).execute()

            for att in (result.data or []):
                # Determine bucket based on entity type and category
                bucket = self._get_bucket_for_attachment(
                    entity_type="fault",
                    category=att.get("category"),
                    mime_type=att.get("mime_type")
                )

                file_ref = self.url_generator.create_file_reference(
                    bucket=bucket,
                    path=att.get("storage_path", ""),
                    filename=att.get("filename", "file"),
                    file_id=att["id"],
                    mime_type=att.get("mime_type"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())

        except Exception as e:
            logger.warning(f"Failed to get fault files: {e}")

        return files

    def _compute_stock_status(self, part: Dict) -> str:
        """Compute stock status for a part"""
        qty = part.get("quantity", 0) or 0
        min_qty = part.get("min_quantity", 0) or 0

        if qty <= 0:
            return "OUT_OF_STOCK"
        elif qty <= min_qty:
            return "LOW_STOCK"
        else:
            return "IN_STOCK"

    def _compute_health_status(self, predictive: Dict, active_faults: List) -> str:
        """Compute overall equipment health status"""
        risk_score = predictive.get("risk_score", 0)
        critical_faults = len([f for f in active_faults if f.get("severity") == "critical"])
        high_faults = len([f for f in active_faults if f.get("severity") == "high"])

        if critical_faults > 0 or risk_score > 0.8:
            return "CRITICAL"
        elif high_faults > 0 or risk_score > 0.6:
            return "WARNING"
        elif len(active_faults) > 0 or risk_score > 0.4:
            return "ATTENTION"
        else:
            return "HEALTHY"

    def _get_fault_actions(self, fault: Dict) -> List[AvailableAction]:
        """Get available actions for fault entity"""
        actions = [
            AvailableAction(
                action_id="diagnose_fault",
                label="Diagnose",
                variant="READ",
                icon="stethoscope"
            ),
            AvailableAction(
                action_id="suggest_parts",
                label="Suggest Parts",
                variant="READ",
                icon="package"
            ),
            AvailableAction(
                action_id="view_fault_history",
                label="History",
                variant="READ",
                icon="history"
            )
        ]

        if fault.get("is_active"):
            actions.extend([
                AvailableAction(
                    action_id="create_work_order",
                    label="Create Work Order",
                    variant="MUTATE",
                    icon="plus",
                    requires_signature=True,
                    is_primary=True
                ),
                AvailableAction(
                    action_id="add_fault_note",
                    label="Add Note",
                    variant="MUTATE",
                    icon="message"
                ),
                AvailableAction(
                    action_id="add_fault_photo",
                    label="Add Photo",
                    variant="MUTATE",
                    icon="camera"
                )
            ])

        return actions


def get_fault_handlers(supabase_client) -> Dict[str, callable]:
    """Get fault handler functions for registration."""
    handlers = FaultHandlers(supabase_client)

    return {
        "view_fault": handlers.view_fault,
        "diagnose_fault": handlers.diagnose_fault,
        "run_diagnostic": handlers.run_diagnostic,
        "view_fault_history": handlers.view_fault_history,
        "suggest_parts": handlers.suggest_parts,
    }
