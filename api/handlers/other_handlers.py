"""
Other Domain Handlers
=====================

Group 6: READ handlers for remaining domains.

Handlers:
- Handover: view_handover, export_handover
- Hours of Rest: view_hours_of_rest, view_compliance_status, export_hours_of_rest
- Purchasing: track_delivery
- Checklists: view_checklist
- Shipyard: view_worklist, export_worklist
- Fleet: view_fleet_summary, open_vessel, export_fleet_summary
- Predictive: request_predictive_insight, view_smart_summary
- Mobile: view_attachments

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    FileReference,
    FileType,
    AvailableAction,
    SignedUrlGenerator
)

logger = logging.getLogger(__name__)


class HandoverHandlers:
    """Handover domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_handover(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View handover report.

        Returns:
        - Handover details with items grouped by category
        - Status and completion
        """
        builder = ResponseBuilder("view_handover", entity_id, "handover", yacht_id)

        try:
            # Query handover with items
            result = self.db.table("handovers").select(
                "id, title, created_at, from_user_id, to_user_id, status, notes, "
                "from_user:from_user_id(name), "
                "to_user:to_user_id(name)"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Handover not found: {entity_id}")
                return builder.build()

            handover = result.data

            # Get handover items
            items_result = self.db.table("handover_items").select(
                "id, category, title, description, priority, status, entity_type, entity_id"
            ).eq("handover_id", entity_id).order("category").execute()

            items = items_result.data or []

            # Group by category
            items_by_category = {}
            for item in items:
                cat = item.get("category", "general")
                if cat not in items_by_category:
                    items_by_category[cat] = []
                items_by_category[cat].append(item)

            # Calculate completion
            total = len(items)
            completed = len([i for i in items if i.get("status") == "completed"])

            builder.set_data({
                "handover_id": entity_id,
                "title": handover.get("title"),
                "from_user": handover.get("from_user", {}).get("name") if handover.get("from_user") else None,
                "to_user": handover.get("to_user", {}).get("name") if handover.get("to_user") else None,
                "status": handover.get("status"),
                "created_at": handover.get("created_at"),
                "notes": handover.get("notes"),
                "items_by_category": items_by_category,
                "progress": {
                    "completed": completed,
                    "total": total,
                    "percent": round((completed / total * 100) if total > 0 else 0, 1)
                }
            })

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="export_handover",
                label="Export PDF",
                variant="READ",
                icon="download"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_handover_item",
                label="Add Item",
                variant="MUTATE",
                icon="plus"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_handover failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def export_handover(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Export handover as PDF.

        Returns:
        - Signed URL for generated PDF file
        """
        builder = ResponseBuilder("export_handover", entity_id, "handover", yacht_id)

        try:
            # Get handover data
            result = self.db.table("handovers").select(
                "id, title, storage_path"
            ).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Handover not found: {entity_id}")
                return builder.build()

            handover = result.data

            # Check for existing export
            if handover.get("storage_path") and self.url_generator:
                file_ref = self.url_generator.create_file_reference(
                    bucket="exports",
                    path=handover["storage_path"],
                    filename=f"{handover.get('title', 'handover')}.pdf",
                    file_id=entity_id,
                    mime_type="application/pdf",
                    expires_in_minutes=60
                )
                if file_ref:
                    builder.add_file(file_ref)
                    builder.set_data({
                        "handover_id": entity_id,
                        "export_status": "ready",
                        "message": "Export ready for download"
                    })
                    return builder.build()

            # Need to generate export
            builder.set_data({
                "handover_id": entity_id,
                "export_status": "generating",
                "message": "Export is being generated. Please wait..."
            })

            return builder.build()

        except Exception as e:
            logger.error(f"export_handover failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


class HoursOfRestHandlers:
    """Hours of Rest domain READ handlers."""

    # MLC 2006 limits
    MIN_REST_24H = 10  # hours
    MIN_REST_7D = 77   # hours
    MAX_WORK_24H = 14  # hours

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_hours_of_rest(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View hours of rest for a crew member.

        Params:
        - date_from: Start date (default: 7 days ago)
        - date_to: End date (default: today)

        Returns:
        - Daily rest records
        - Compliance status
        """
        builder = ResponseBuilder("view_hours_of_rest", entity_id, "crew_member", yacht_id)

        try:
            # Parse date range
            params = params or {}
            today = datetime.now(timezone.utc).date()
            date_to = params.get("date_to", today.isoformat())
            date_from = params.get("date_from", (today - timedelta(days=7)).isoformat())

            # Get crew member name
            crew_result = self.db.table("crew_members").select(
                "name, role"
            ).eq("id", entity_id).single().execute()

            crew_name = crew_result.data.get("name") if crew_result.data else "Unknown"
            crew_role = crew_result.data.get("role") if crew_result.data else None

            # Get rest records
            result = self.db.table("hours_of_rest").select(
                "id, date, rest_hours, work_hours, notes, is_compliant"
            ).eq("crew_member_id", entity_id).gte(
                "date", date_from
            ).lte("date", date_to).order("date", desc=True).execute()

            records = result.data or []

            # Calculate totals and compliance
            total_rest = sum(r.get("rest_hours", 0) for r in records)
            total_work = sum(r.get("work_hours", 0) for r in records)
            non_compliant_days = len([r for r in records if not r.get("is_compliant")])

            builder.set_data({
                "crew_member_id": entity_id,
                "crew_name": crew_name,
                "crew_role": crew_role,
                "date_range": {
                    "from": date_from,
                    "to": date_to
                },
                "records": records,
                "summary": {
                    "total_rest_hours": total_rest,
                    "total_work_hours": total_work,
                    "average_rest_per_day": round(total_rest / len(records), 1) if records else 0,
                    "non_compliant_days": non_compliant_days,
                    "compliance_rate": round(((len(records) - non_compliant_days) / len(records) * 100) if records else 100, 1)
                },
                "mlc_limits": {
                    "min_rest_24h": self.MIN_REST_24H,
                    "min_rest_7d": self.MIN_REST_7D,
                    "max_work_24h": self.MAX_WORK_24H
                }
            })

            builder.add_available_action(AvailableAction(
                action_id="export_hours_of_rest",
                label="Export Report",
                variant="READ",
                icon="download"
            ))
            builder.add_available_action(AvailableAction(
                action_id="log_rest_hours",
                label="Log Hours",
                variant="MUTATE",
                icon="clock"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_hours_of_rest failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_compliance_status(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View MLC compliance status for yacht.

        Returns:
        - All crew compliance summaries
        - Overall compliance rate
        - Alerts for non-compliance
        """
        builder = ResponseBuilder("view_compliance_status", entity_id, "yacht", yacht_id)

        try:
            # Get all crew members
            crew_result = self.db.table("crew_members").select(
                "id, name, role"
            ).eq("yacht_id", yacht_id).eq("is_active", True).execute()

            crew_members = crew_result.data or []

            # Get last 7 days of rest records for all crew
            today = datetime.now(timezone.utc).date()
            week_ago = (today - timedelta(days=7)).isoformat()

            compliance_data = []
            alerts = []

            for crew in crew_members:
                records = self.db.table("hours_of_rest").select(
                    "rest_hours, is_compliant, date"
                ).eq("crew_member_id", crew["id"]).gte(
                    "date", week_ago
                ).execute()

                crew_records = records.data or []
                total_rest = sum(r.get("rest_hours", 0) for r in crew_records)
                non_compliant = len([r for r in crew_records if not r.get("is_compliant")])

                status = "compliant"
                if non_compliant > 0:
                    status = "warning" if non_compliant < 3 else "non_compliant"

                compliance_data.append({
                    "crew_id": crew["id"],
                    "name": crew.get("name"),
                    "role": crew.get("role"),
                    "total_rest_7d": total_rest,
                    "meets_77h_minimum": total_rest >= self.MIN_REST_7D,
                    "non_compliant_days": non_compliant,
                    "status": status
                })

                if status == "non_compliant":
                    alerts.append({
                        "crew_id": crew["id"],
                        "crew_name": crew.get("name"),
                        "message": f"{non_compliant} non-compliant days in last 7 days",
                        "severity": "high"
                    })

            overall_compliant = len([c for c in compliance_data if c["status"] == "compliant"])

            builder.set_data({
                "yacht_id": yacht_id,
                "period": {
                    "from": week_ago,
                    "to": today.isoformat()
                },
                "crew_compliance": compliance_data,
                "alerts": alerts,
                "summary": {
                    "total_crew": len(crew_members),
                    "fully_compliant": overall_compliant,
                    "compliance_rate": round((overall_compliant / len(crew_members) * 100) if crew_members else 100, 1)
                }
            })

            return builder.build()

        except Exception as e:
            logger.error(f"view_compliance_status failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def export_hours_of_rest(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Export hours of rest report.

        Returns:
        - Signed URL for PDF/Excel export
        """
        builder = ResponseBuilder("export_hours_of_rest", entity_id, "crew_member", yacht_id)

        try:
            format_type = (params or {}).get("format", "pdf")

            # Check for existing export in storage
            export_path = f"exports/hours_of_rest/{yacht_id}/{entity_id}"

            builder.set_data({
                "crew_member_id": entity_id,
                "export_status": "generating",
                "format": format_type,
                "message": f"Generating {format_type.upper()} export..."
            })

            return builder.build()

        except Exception as e:
            logger.error(f"export_hours_of_rest failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


class PurchasingHandlers:
    """Purchasing domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def track_delivery(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Track purchase order delivery.

        Returns:
        - PO details with items
        - Delivery status and tracking
        """
        builder = ResponseBuilder("track_delivery", entity_id, "purchase_order", yacht_id)

        try:
            # Query PO with items
            result = self.db.table("purchase_orders").select(
                "id, po_number, supplier, status, created_at, expected_delivery, "
                "tracking_number, shipping_carrier, total_amount, currency, notes"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Purchase order not found: {entity_id}")
                return builder.build()

            po = result.data

            # Get line items
            items_result = self.db.table("purchase_order_items").select(
                "id, part_id, description, quantity, unit_price, status, "
                "parts:part_id(canonical_name)"
            ).eq("purchase_order_id", entity_id).execute()

            items = items_result.data or []

            # Calculate delivery status
            delivery_status = self._compute_delivery_status(po)

            builder.set_data({
                "po_id": entity_id,
                "po_number": po.get("po_number"),
                "supplier": po.get("supplier"),
                "status": po.get("status"),
                "delivery_status": delivery_status,
                "tracking": {
                    "number": po.get("tracking_number"),
                    "carrier": po.get("shipping_carrier"),
                    "expected_delivery": po.get("expected_delivery")
                },
                "items": [
                    {
                        "id": item.get("id"),
                        "description": item.get("description") or (item.get("parts", {}).get("canonical_name") if item.get("parts") else None),
                        "quantity": item.get("quantity"),
                        "unit_price": item.get("unit_price"),
                        "status": item.get("status")
                    }
                    for item in items
                ],
                "totals": {
                    "amount": po.get("total_amount"),
                    "currency": po.get("currency", "USD"),
                    "items_count": len(items)
                }
            })

            # Add actions based on status
            if po.get("status") not in ("delivered", "cancelled"):
                builder.add_available_action(AvailableAction(
                    action_id="mark_delivered",
                    label="Mark Delivered",
                    variant="MUTATE",
                    icon="check",
                    requires_signature=True
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"track_delivery failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    def _compute_delivery_status(self, po: Dict) -> str:
        """Compute delivery status from PO data"""
        status = po.get("status", "")

        if status == "delivered":
            return "DELIVERED"
        elif status == "cancelled":
            return "CANCELLED"
        elif po.get("tracking_number"):
            return "IN_TRANSIT"
        elif status == "ordered":
            return "PROCESSING"
        else:
            return "PENDING"


class ChecklistHandlers:
    """Checklist domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def view_checklist(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View checklist with items.

        Returns:
        - Checklist details
        - Items with completion status
        - Progress summary
        """
        builder = ResponseBuilder("view_checklist", entity_id, "checklist", yacht_id)

        try:
            # Query checklist
            result = self.db.table("checklists").select(
                "id, title, category, description, created_at, due_date, "
                "status, assigned_to, crew:assigned_to(name)"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Checklist not found: {entity_id}")
                return builder.build()

            checklist = result.data

            # Get items
            items_result = self.db.table("checklist_items").select(
                "id, description, is_completed, completed_at, completed_by, "
                "notes, sequence, is_required"
            ).eq("checklist_id", entity_id).order("sequence").execute()

            items = items_result.data or []

            # Calculate progress
            total = len(items)
            completed = len([i for i in items if i.get("is_completed")])
            required_items = [i for i in items if i.get("is_required")]
            required_completed = len([i for i in required_items if i.get("is_completed")])

            builder.set_data({
                "checklist_id": entity_id,
                "title": checklist.get("title"),
                "category": checklist.get("category"),
                "description": checklist.get("description"),
                "status": checklist.get("status"),
                "due_date": checklist.get("due_date"),
                "assigned_to": checklist.get("crew", {}).get("name") if checklist.get("crew") else None,
                "items": items,
                "progress": {
                    "completed": completed,
                    "total": total,
                    "percent": round((completed / total * 100) if total > 0 else 0, 1),
                    "required_completed": required_completed,
                    "required_total": len(required_items),
                    "can_complete": required_completed == len(required_items)
                }
            })

            # Actions
            builder.add_available_action(AvailableAction(
                action_id="toggle_checklist_item",
                label="Toggle Item",
                variant="MUTATE",
                icon="check"
            ))

            if required_completed == len(required_items) and checklist.get("status") != "completed":
                builder.add_available_action(AvailableAction(
                    action_id="complete_checklist",
                    label="Complete Checklist",
                    variant="MUTATE",
                    icon="check-circle",
                    is_primary=True
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_checklist failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


class ShipyardHandlers:
    """Shipyard domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_worklist(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View shipyard worklist/refit project.

        Returns:
        - Project details
        - Work items with status
        - Budget tracking
        """
        builder = ResponseBuilder("view_worklist", entity_id, "shipyard_project", yacht_id)

        try:
            # Query project
            result = self.db.table("shipyard_projects").select(
                "id, name, shipyard_name, start_date, end_date, status, "
                "budget, spent, currency, notes"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Project not found: {entity_id}")
                return builder.build()

            project = result.data

            # Get work items
            items_result = self.db.table("shipyard_work_items").select(
                "id, title, description, status, priority, estimated_cost, "
                "actual_cost, assigned_contractor, start_date, end_date"
            ).eq("project_id", entity_id).order("priority", desc=True).execute()

            items = items_result.data or []

            # Calculate totals
            total_estimated = sum(i.get("estimated_cost", 0) or 0 for i in items)
            total_actual = sum(i.get("actual_cost", 0) or 0 for i in items)
            completed_items = len([i for i in items if i.get("status") == "completed"])

            builder.set_data({
                "project_id": entity_id,
                "name": project.get("name"),
                "shipyard": project.get("shipyard_name"),
                "status": project.get("status"),
                "dates": {
                    "start": project.get("start_date"),
                    "end": project.get("end_date")
                },
                "budget": {
                    "allocated": project.get("budget"),
                    "spent": project.get("spent"),
                    "remaining": (project.get("budget") or 0) - (project.get("spent") or 0),
                    "currency": project.get("currency", "USD")
                },
                "work_items": items,
                "summary": {
                    "total_items": len(items),
                    "completed": completed_items,
                    "estimated_total": total_estimated,
                    "actual_total": total_actual,
                    "variance": total_actual - total_estimated
                }
            })

            builder.add_available_action(AvailableAction(
                action_id="export_worklist",
                label="Export Worklist",
                variant="READ",
                icon="download"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_work_item",
                label="Add Item",
                variant="MUTATE",
                icon="plus"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_worklist failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def export_worklist(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Export shipyard worklist.

        Returns:
        - Signed URL for export file
        """
        builder = ResponseBuilder("export_worklist", entity_id, "shipyard_project", yacht_id)

        try:
            format_type = (params or {}).get("format", "pdf")

            builder.set_data({
                "project_id": entity_id,
                "export_status": "generating",
                "format": format_type,
                "message": f"Generating {format_type.upper()} export..."
            })

            return builder.build()

        except Exception as e:
            logger.error(f"export_worklist failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


class FleetHandlers:
    """Fleet management domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def view_fleet_summary(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View fleet summary (for fleet managers).

        Returns:
        - List of vessels with status
        - Overall fleet metrics
        """
        builder = ResponseBuilder("view_fleet_summary", entity_id, "fleet", yacht_id)

        try:
            # Get vessels in fleet
            result = self.db.table("yachts").select(
                "id, name, type, length, flag, status, home_port, current_location"
            ).eq("fleet_id", entity_id).execute()

            vessels = result.data or []

            # Get summary metrics for each vessel
            vessel_summaries = []
            for vessel in vessels:
                # Get open work orders count
                wo_count = self.db.table("work_orders").select(
                    "id", count="exact"
                ).eq("yacht_id", vessel["id"]).in_(
                    "status", ["open", "in_progress"]
                ).execute()

                # Get active faults count
                fault_count = self.db.table("faults").select(
                    "id", count="exact"
                ).eq("yacht_id", vessel["id"]).eq("is_resolved", False).execute()

                vessel_summaries.append({
                    "vessel_id": vessel["id"],
                    "name": vessel.get("name"),
                    "type": vessel.get("type"),
                    "status": vessel.get("status"),
                    "location": vessel.get("current_location"),
                    "metrics": {
                        "open_work_orders": wo_count.count or 0,
                        "active_faults": fault_count.count or 0
                    }
                })

            # Fleet totals
            total_wo = sum(v["metrics"]["open_work_orders"] for v in vessel_summaries)
            total_faults = sum(v["metrics"]["active_faults"] for v in vessel_summaries)

            builder.set_data({
                "fleet_id": entity_id,
                "vessels": vessel_summaries,
                "fleet_totals": {
                    "vessel_count": len(vessels),
                    "total_open_work_orders": total_wo,
                    "total_active_faults": total_faults
                }
            })

            builder.add_available_action(AvailableAction(
                action_id="export_fleet_summary",
                label="Export Summary",
                variant="READ",
                icon="download"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_fleet_summary failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def open_vessel(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Open/navigate to specific vessel.

        Returns:
        - Vessel details for navigation
        """
        builder = ResponseBuilder("open_vessel", entity_id, "yacht", yacht_id)

        try:
            result = self.db.table("yachts").select(
                "id, name, type, length, flag, status, home_port, current_location, "
                "build_year, builder, hull_number"
            ).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Vessel not found: {entity_id}")
                return builder.build()

            vessel = result.data

            builder.set_data({
                "vessel_id": entity_id,
                "name": vessel.get("name"),
                "details": vessel,
                "navigate_to": f"/vessels/{entity_id}"
            })

            return builder.build()

        except Exception as e:
            logger.error(f"open_vessel failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def export_fleet_summary(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Export fleet summary report.
        """
        builder = ResponseBuilder("export_fleet_summary", entity_id, "fleet", yacht_id)

        try:
            format_type = (params or {}).get("format", "pdf")

            builder.set_data({
                "fleet_id": entity_id,
                "export_status": "generating",
                "format": format_type,
                "message": f"Generating fleet summary {format_type.upper()}..."
            })

            return builder.build()

        except Exception as e:
            logger.error(f"export_fleet_summary failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


class PredictiveHandlers:
    """Predictive/AI insight domain READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def request_predictive_insight(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Request AI-generated predictive insight.

        Returns:
        - Insight data (predictions, recommendations)
        - Confidence scores
        """
        builder = ResponseBuilder("request_predictive_insight", entity_id, "equipment", yacht_id)

        try:
            insight_type = (params or {}).get("insight_type", "failure_prediction")

            # Get equipment info
            equip_result = self.db.table("equipment").select(
                "id, canonical_label, category, last_service_date, run_hours"
            ).eq("id", entity_id).single().execute()

            if not equip_result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            equipment = equip_result.data

            # Get recent sensor data
            sensor_data = []
            try:
                sensor_result = self.db.table("sensor_readings").select(
                    "parameter, value, unit, timestamp"
                ).eq("equipment_id", entity_id).order(
                    "timestamp", desc=True
                ).limit(100).execute()
                sensor_data = sensor_result.data or []
            except Exception:
                pass

            # Get recent faults
            fault_history = []
            try:
                fault_result = self.db.table("faults").select(
                    "fault_code, severity, created_at"
                ).eq("equipment_id", entity_id).order(
                    "created_at", desc=True
                ).limit(20).execute()
                fault_history = fault_result.data or []
            except Exception:
                pass

            # Generate insight (placeholder for actual ML model)
            insight = self._generate_insight(equipment, sensor_data, fault_history, insight_type)

            builder.set_data({
                "equipment_id": entity_id,
                "equipment_name": equipment.get("canonical_label"),
                "insight_type": insight_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                **insight
            })

            return builder.build()

        except Exception as e:
            logger.error(f"request_predictive_insight failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    def _generate_insight(
        self,
        equipment: Dict,
        sensor_data: List,
        fault_history: List,
        insight_type: str
    ) -> Dict:
        """Generate predictive insight (placeholder)"""
        # This would be replaced with actual ML model calls
        run_hours = equipment.get("run_hours", 0) or 0
        fault_count = len(fault_history)

        # Simple heuristic scoring
        risk_score = min(100, (run_hours / 1000) * 10 + fault_count * 5)

        return {
            "prediction": {
                "risk_level": "high" if risk_score > 70 else "medium" if risk_score > 40 else "low",
                "risk_score": round(risk_score, 1),
                "estimated_days_to_service": max(1, int(90 - risk_score)),
                "confidence": 0.75
            },
            "recommendations": [
                "Schedule preventive maintenance" if risk_score > 50 else "Continue normal operation",
                "Review recent sensor trends" if sensor_data else "Install sensors for better monitoring"
            ],
            "factors": {
                "run_hours": run_hours,
                "recent_fault_count": fault_count,
                "sensor_readings_analyzed": len(sensor_data)
            }
        }

    async def view_smart_summary(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View AI-generated smart summary.

        Returns:
        - Aggregated insights across equipment
        - Priority recommendations
        """
        builder = ResponseBuilder("view_smart_summary", entity_id, "yacht", yacht_id)

        try:
            # Get all equipment
            equip_result = self.db.table("equipment").select(
                "id, canonical_label, category, run_hours"
            ).eq("yacht_id", yacht_id).execute()

            equipment_list = equip_result.data or []

            # Get open work orders
            wo_result = self.db.table("work_orders").select(
                "id, title, priority, status"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["open", "in_progress"]
            ).execute()

            work_orders = wo_result.data or []

            # Get active faults
            fault_result = self.db.table("faults").select(
                "id, fault_code, severity, equipment_id"
            ).eq("yacht_id", yacht_id).eq("is_resolved", False).execute()

            faults = fault_result.data or []

            # Generate summary
            high_priority_wo = len([w for w in work_orders if w.get("priority") == "high"])
            critical_faults = len([f for f in faults if f.get("severity") == "critical"])

            builder.set_data({
                "yacht_id": yacht_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "overview": {
                    "equipment_count": len(equipment_list),
                    "open_work_orders": len(work_orders),
                    "active_faults": len(faults)
                },
                "priorities": {
                    "high_priority_work_orders": high_priority_wo,
                    "critical_faults": critical_faults
                },
                "recommendations": self._generate_recommendations(equipment_list, work_orders, faults),
                "health_score": self._calculate_health_score(work_orders, faults)
            })

            return builder.build()

        except Exception as e:
            logger.error(f"view_smart_summary failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    def _generate_recommendations(
        self,
        equipment: List,
        work_orders: List,
        faults: List
    ) -> List[Dict]:
        """Generate priority recommendations"""
        recommendations = []

        critical_faults = [f for f in faults if f.get("severity") == "critical"]
        if critical_faults:
            recommendations.append({
                "priority": "critical",
                "message": f"Address {len(critical_faults)} critical fault(s) immediately",
                "action_id": "view_fault",
                "entity_ids": [f["id"] for f in critical_faults[:3]]
            })

        high_wo = [w for w in work_orders if w.get("priority") == "high"]
        if high_wo:
            recommendations.append({
                "priority": "high",
                "message": f"{len(high_wo)} high-priority work order(s) require attention",
                "action_id": "view_work_order",
                "entity_ids": [w["id"] for w in high_wo[:3]]
            })

        return recommendations

    def _calculate_health_score(self, work_orders: List, faults: List) -> Dict:
        """Calculate overall yacht health score"""
        base_score = 100

        # Deduct for work orders
        base_score -= len(work_orders) * 2
        base_score -= len([w for w in work_orders if w.get("priority") == "high"]) * 5

        # Deduct for faults
        for fault in faults:
            severity = fault.get("severity", "low")
            if severity == "critical":
                base_score -= 15
            elif severity == "high":
                base_score -= 10
            elif severity == "medium":
                base_score -= 5
            else:
                base_score -= 2

        score = max(0, min(100, base_score))

        return {
            "score": score,
            "status": "excellent" if score >= 90 else "good" if score >= 70 else "fair" if score >= 50 else "poor",
            "trend": "stable"  # Would be calculated from historical data
        }


class MobileHandlers:
    """Mobile-specific READ handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_attachments(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View attachments for any entity.

        Params:
        - entity_type: Type of parent entity

        Returns:
        - List of attachments with signed URLs
        """
        builder = ResponseBuilder("view_attachments", entity_id, "attachment", yacht_id)

        try:
            entity_type = (params or {}).get("entity_type", "work_order")

            # Query attachments
            result = self.db.table("attachments").select(
                "id, filename, mime_type, storage_path, category, uploaded_at, "
                "file_size, uploaded_by"
            ).eq("entity_type", entity_type).eq("entity_id", entity_id).order(
                "uploaded_at", desc=True
            ).execute()

            attachments = result.data or []

            # Generate signed URLs
            files = []
            for att in attachments:
                if self.url_generator and att.get("storage_path"):
                    file_ref = self.url_generator.create_file_reference(
                        bucket="attachments",
                        path=att["storage_path"],
                        filename=att.get("filename", "file"),
                        file_id=att["id"],
                        mime_type=att.get("mime_type"),
                        size_bytes=att.get("file_size"),
                        expires_in_minutes=30
                    )
                    if file_ref:
                        file_dict = file_ref.to_dict()
                        file_dict["category"] = att.get("category")
                        file_dict["uploaded_at"] = att.get("uploaded_at")
                        files.append(file_dict)

            builder.set_data({
                "entity_id": entity_id,
                "entity_type": entity_type,
                "attachment_count": len(attachments)
            })

            if files:
                builder.add_files(files)

            builder.add_available_action(AvailableAction(
                action_id="upload_attachment",
                label="Upload File",
                variant="MUTATE",
                icon="upload"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_attachments failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# HANDLER REGISTRATION
# =========================================================================

def get_handover_handlers(supabase_client) -> Dict[str, callable]:
    """Get handover handler functions for registration."""
    handlers = HandoverHandlers(supabase_client)
    return {
        "view_handover": handlers.view_handover,
        "export_handover": handlers.export_handover,
    }


def get_hours_of_rest_handlers(supabase_client) -> Dict[str, callable]:
    """Get hours of rest handler functions for registration."""
    handlers = HoursOfRestHandlers(supabase_client)
    return {
        "view_hours_of_rest": handlers.view_hours_of_rest,
        "view_compliance_status": handlers.view_compliance_status,
        "export_hours_of_rest": handlers.export_hours_of_rest,
    }


def get_purchasing_handlers(supabase_client) -> Dict[str, callable]:
    """Get purchasing handler functions for registration."""
    handlers = PurchasingHandlers(supabase_client)
    return {
        "track_delivery": handlers.track_delivery,
    }


def get_checklist_handlers(supabase_client) -> Dict[str, callable]:
    """Get checklist handler functions for registration."""
    handlers = ChecklistHandlers(supabase_client)
    return {
        "view_checklist": handlers.view_checklist,
    }


def get_shipyard_handlers(supabase_client) -> Dict[str, callable]:
    """Get shipyard handler functions for registration."""
    handlers = ShipyardHandlers(supabase_client)
    return {
        "view_worklist": handlers.view_worklist,
        "export_worklist": handlers.export_worklist,
    }


def get_fleet_handlers(supabase_client) -> Dict[str, callable]:
    """Get fleet handler functions for registration."""
    handlers = FleetHandlers(supabase_client)
    return {
        "view_fleet_summary": handlers.view_fleet_summary,
        "open_vessel": handlers.open_vessel,
        "export_fleet_summary": handlers.export_fleet_summary,
    }


def get_predictive_handlers(supabase_client) -> Dict[str, callable]:
    """Get predictive/AI handler functions for registration."""
    handlers = PredictiveHandlers(supabase_client)
    return {
        "request_predictive_insight": handlers.request_predictive_insight,
        "view_smart_summary": handlers.view_smart_summary,
    }


def get_mobile_handlers(supabase_client) -> Dict[str, callable]:
    """Get mobile handler functions for registration."""
    handlers = MobileHandlers(supabase_client)
    return {
        "view_attachments": handlers.view_attachments,
    }


def get_all_other_handlers(supabase_client) -> Dict[str, callable]:
    """Get all Group 6 handlers combined."""
    handlers = {}
    handlers.update(get_handover_handlers(supabase_client))
    handlers.update(get_hours_of_rest_handlers(supabase_client))
    handlers.update(get_purchasing_handlers(supabase_client))
    handlers.update(get_checklist_handlers(supabase_client))
    handlers.update(get_shipyard_handlers(supabase_client))
    handlers.update(get_fleet_handlers(supabase_client))
    handlers.update(get_predictive_handlers(supabase_client))
    handlers.update(get_mobile_handlers(supabase_client))
    return handlers
