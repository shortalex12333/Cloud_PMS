"""
Trigger Service
===============

Business rule triggers that detect conditions requiring action.

Triggers Implemented:
- LOW_STOCK: Part quantity below minimum threshold
- OVERDUE_WO: Work orders past due date
- HOR_VIOLATION: Hours of rest compliance violations
- MAINTENANCE_DUE: Equipment maintenance due within 7 days

Based on: ACTION_OFFERING_RULES.md
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class TriggerService:
    """
    Service for checking business rule triggers.

    Each trigger returns a list of items that meet the trigger condition,
    along with severity and suggested actions.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # TRIGGER: LOW_STOCK
    # =========================================================================

    async def check_low_stock(self, yacht_id: str) -> List[Dict]:
        """
        Check for parts with stock level at or below minimum threshold.

        Trigger Condition:
        - quantity_on_hand <= minimum_stock (including 0)

        Returns:
            List of triggered items with part details and suggested actions
        """
        try:
            # Query parts with low or zero stock
            # Note: Using quantity_on_hand and minimum_quantity columns
            result = self.db.table("pms_parts").select(
                "id, name, part_number, category, "
                "quantity_on_hand, minimum_quantity, location"
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return []

            triggered = []
            for part in result.data:
                qty = part.get("quantity_on_hand", 0) or 0
                min_stock = part.get("minimum_quantity", 0) or 0

                if qty <= min_stock:
                    severity = "critical" if qty == 0 else "warning"
                    triggered.append({
                        "trigger_type": "LOW_STOCK",
                        "severity": severity,
                        "entity_type": "part",
                        "entity_id": part["id"],
                        "entity_name": part.get("name", part.get("part_number")),
                        "part_number": part.get("part_number"),
                        "current_value": qty,
                        "threshold_value": min_stock,
                        "message": f"{'Out of stock' if qty == 0 else 'Low stock'}: {part.get('name', 'Unknown')} ({qty}/{min_stock})",
                        "location": part.get("location"),
                        "suggested_actions": ["order_part", "view_part_stock", "create_purchase_request"],
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })

            logger.info(f"LOW_STOCK check: {len(triggered)} items triggered for yacht {yacht_id}")
            return triggered

        except Exception as e:
            logger.error(f"LOW_STOCK check error: {e}")
            return []

    # =========================================================================
    # TRIGGER: OVERDUE_WO
    # =========================================================================

    async def check_overdue_work_orders(self, yacht_id: str) -> List[Dict]:
        """
        Check for work orders that are past their due date.

        Trigger Condition:
        - due_date < NOW()
        - AND status NOT IN ('completed', 'cancelled', 'closed')

        Returns:
            List of overdue work orders with details and suggested actions
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Query work orders with due_date in the past
            result = self.db.table("pms_work_orders").select(
                "id, title, wo_number, status, priority, due_date, "
                "equipment_id, assigned_to"
            ).eq("yacht_id", yacht_id).lt("due_date", now).execute()

            if not result.data:
                return []

            triggered = []
            completed_statuses = {'completed', 'cancelled', 'closed'}

            for wo in result.data:
                status = (wo.get("status") or "").lower()
                if status not in completed_statuses:
                    due_date = wo.get("due_date")
                    if due_date:
                        # Calculate days overdue (handle both timezone-aware and naive datetimes)
                        try:
                            if isinstance(due_date, str):
                                if 'Z' in due_date:
                                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                                elif '+' in due_date or '-' in due_date[-6:]:
                                    due_dt = datetime.fromisoformat(due_date)
                                else:
                                    due_dt = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
                            else:
                                due_dt = due_date

                            if due_dt.tzinfo is None:
                                due_dt = due_dt.replace(tzinfo=timezone.utc)

                            days_overdue = (datetime.now(timezone.utc) - due_dt).days
                        except Exception:
                            days_overdue = 0

                        severity = "critical" if days_overdue > 7 else "warning"
                        priority = wo.get("priority", "medium")
                        if priority in ("urgent", "critical"):
                            severity = "critical"

                        triggered.append({
                            "trigger_type": "OVERDUE_WO",
                            "severity": severity,
                            "entity_type": "work_order",
                            "entity_id": wo["id"],
                            "entity_name": wo.get("title") or wo.get("wo_number"),
                            "wo_number": wo.get("wo_number"),
                            "current_status": wo.get("status"),
                            "priority": priority,
                            "due_date": due_date,
                            "days_overdue": days_overdue,
                            "message": f"Overdue by {days_overdue} day(s): {wo.get('title', wo.get('wo_number', 'Unknown'))}",
                            "assigned_to": wo.get("assigned_to"),
                            "equipment_id": wo.get("equipment_id"),
                            "suggested_actions": ["view_work_order_detail", "start_work_order", "assign_work_order"],
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        })

            logger.info(f"OVERDUE_WO check: {len(triggered)} items triggered for yacht {yacht_id}")
            return triggered

        except Exception as e:
            logger.error(f"OVERDUE_WO check error: {e}")
            return []

    # =========================================================================
    # TRIGGER: HOR_VIOLATION
    # =========================================================================

    async def check_hor_violations(self, yacht_id: str, days_back: int = 7) -> List[Dict]:
        """
        Check for Hours of Rest compliance violations.

        Trigger Conditions:
        - is_daily_compliant = false (MLC 2006: < 10 hours rest per 24-hour period)
        - is_weekly_compliant = false (STCW: < 77 hours rest per 7-day period)

        Returns:
            List of HOR violation records with details
        """
        try:
            # Query non-compliant HOR records from last N days
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date().isoformat()

            result = self.db.table("pms_hours_of_rest").select(
                "id, user_id, record_date, total_rest_hours, weekly_rest_hours, "
                "is_daily_compliant, is_weekly_compliant, is_compliant, "
                "daily_compliance_notes, weekly_compliance_notes, status"
            ).eq("yacht_id", yacht_id).gte("record_date", cutoff_date).execute()

            if not result.data:
                return []

            triggered = []
            for record in result.data:
                violations = []

                if not record.get("is_daily_compliant"):
                    violations.append({
                        "type": "daily",
                        "value": record.get("total_rest_hours", 0),
                        "threshold": 10,
                        "standard": "MLC 2006"
                    })

                if not record.get("is_weekly_compliant"):
                    violations.append({
                        "type": "weekly",
                        "value": record.get("weekly_rest_hours", 0),
                        "threshold": 77,
                        "standard": "STCW"
                    })

                if violations:
                    severity = "critical" if len(violations) > 1 else "warning"
                    violation_types = ", ".join([v["type"] for v in violations])

                    triggered.append({
                        "trigger_type": "HOR_VIOLATION",
                        "severity": severity,
                        "entity_type": "hours_of_rest",
                        "entity_id": record["id"],
                        "user_id": record.get("user_id"),
                        "record_date": record.get("record_date"),
                        "violations": violations,
                        "daily_rest_hours": record.get("total_rest_hours"),
                        "weekly_rest_hours": record.get("weekly_rest_hours"),
                        "message": f"HOR violation ({violation_types}) on {record.get('record_date')}",
                        "daily_notes": record.get("daily_compliance_notes"),
                        "weekly_notes": record.get("weekly_compliance_notes"),
                        "suggested_actions": ["update_hours_of_rest", "view_compliance_status"],
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })

            logger.info(f"HOR_VIOLATION check: {len(triggered)} items triggered for yacht {yacht_id}")
            return triggered

        except Exception as e:
            logger.error(f"HOR_VIOLATION check error: {e}")
            return []

    # =========================================================================
    # TRIGGER: MAINTENANCE_DUE
    # =========================================================================

    async def check_maintenance_due(self, yacht_id: str, days_ahead: int = 7) -> List[Dict]:
        """
        Check for equipment with maintenance due within specified window.

        Note: This trigger checks the attention_flag field since next_service_date
        is not available in the current schema. Equipment with attention_flag=true
        needs attention.

        Returns:
            List of equipment requiring attention
        """
        try:
            # Query equipment with attention flag set
            # Since next_service_date doesn't exist, use attention_flag as proxy
            result = self.db.table("pms_equipment").select(
                "id, name, code, location, attention_flag, attention_reason, "
                "status, installed_date"
            ).eq("yacht_id", yacht_id).eq("attention_flag", True).execute()

            if not result.data:
                return []

            triggered = []
            for equip in result.data:
                # Use attention_flag as trigger indicator
                attention_reason = equip.get("attention_reason", "Requires attention")
                status = equip.get("status", "unknown")

                # Determine severity based on status
                severity = "warning"
                if status in ("faulty", "out_of_service"):
                    severity = "critical"

                triggered.append({
                    "trigger_type": "MAINTENANCE_DUE",
                    "severity": severity,
                    "entity_type": "equipment",
                    "entity_id": equip["id"],
                    "entity_name": equip.get("name"),
                    "equipment_code": equip.get("code"),
                    "equipment_status": status,
                    "attention_reason": attention_reason,
                    "message": f"Requires attention: {equip.get('name', 'Unknown')} - {attention_reason}",
                    "location": equip.get("location"),
                    "suggested_actions": ["create_work_order", "view_equipment_details", "view_equipment_manual"],
                    "detected_at": datetime.now(timezone.utc).isoformat()
                })

            logger.info(f"MAINTENANCE_DUE check: {len(triggered)} items triggered for yacht {yacht_id}")
            return triggered

        except Exception as e:
            logger.error(f"MAINTENANCE_DUE check error: {e}")
            return []

    # =========================================================================
    # COMBINED: Check All Triggers
    # =========================================================================

    async def check_all_triggers(self, yacht_id: str) -> Dict[str, Any]:
        """
        Run all trigger checks and return combined results.

        Returns:
            Dictionary with all trigger results organized by type
        """
        low_stock = await self.check_low_stock(yacht_id)
        overdue_wo = await self.check_overdue_work_orders(yacht_id)
        hor_violations = await self.check_hor_violations(yacht_id)
        maintenance_due = await self.check_maintenance_due(yacht_id)

        # Count by severity
        all_triggers = low_stock + overdue_wo + hor_violations + maintenance_due
        critical_count = sum(1 for t in all_triggers if t.get("severity") == "critical")
        warning_count = sum(1 for t in all_triggers if t.get("severity") == "warning")
        info_count = sum(1 for t in all_triggers if t.get("severity") == "info")

        return {
            "yacht_id": yacht_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_triggers": len(all_triggers),
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count
            },
            "triggers": {
                "low_stock": {
                    "count": len(low_stock),
                    "items": low_stock
                },
                "overdue_work_orders": {
                    "count": len(overdue_wo),
                    "items": overdue_wo
                },
                "hor_violations": {
                    "count": len(hor_violations),
                    "items": hor_violations
                },
                "maintenance_due": {
                    "count": len(maintenance_due),
                    "items": maintenance_due
                }
            }
        }
