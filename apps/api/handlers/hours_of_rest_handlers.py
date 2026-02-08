"""
Hours of Rest Handlers (Crew Lens v3)
======================================

Handlers for Maritime Labour Convention (MLC 2006) & STCW compliance.

READ Handlers:
- get_hours_of_rest: Get daily HoR records for user/date range
- get_monthly_signoff: Get monthly sign-off details
- list_monthly_signoffs: List monthly sign-offs
- list_crew_templates: List schedule templates
- list_crew_warnings: List compliance warnings

MUTATE Handlers:
- upsert_hours_of_rest: Create/update daily HoR record
- create_monthly_signoff: Initiate monthly sign-off workflow
- sign_monthly_signoff: Add crew/HOD/captain signature
- create_crew_template: Create schedule template
- apply_crew_template: Apply template to week
- acknowledge_warning: Crew acknowledges warning
- dismiss_warning: HOD/Captain dismisses warning

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone, timedelta, date
from typing import Dict, Optional, List
import logging
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
)

logger = logging.getLogger(__name__)


class HoursOfRestHandlers:
    """
    Hours of Rest domain handlers (Crew Lens v3).

    Implements ILO MLC 2006 and STCW Convention compliance tracking.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # READ HANDLERS - Daily Hours of Rest
    # =========================================================================

    async def get_hours_of_rest(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest

        Get daily HoR records for user within date range.

        Params:
        - user_id: Target user (defaults to current user)
        - start_date: YYYY-MM-DD (defaults to 7 days ago)
        - end_date: YYYY-MM-DD (defaults to today)

        Returns:
        - Daily HoR records with compliance indicators
        - Weekly compliance summary
        - Active warnings count
        """
        builder = ResponseBuilder("get_hours_of_rest", entity_id, "hours_of_rest", yacht_id)

        try:
            params = params or {}
            user_id = params.get("user_id", entity_id)

            # Date range (default: last 7 days)
            end_date = params.get("end_date", date.today().isoformat())
            start_date = params.get(
                "start_date",
                (date.today() - timedelta(days=7)).isoformat()
            )

            # Fetch HoR records
            result = self.db.table("pms_hours_of_rest").select(
                "id, user_id, record_date, rest_periods, "
                "total_rest_hours, total_work_hours, "
                "is_daily_compliant, is_weekly_compliant, "
                "weekly_rest_hours, compliance_status, "
                "daily_compliance_notes, weekly_compliance_notes, "
                "created_at, updated_at"
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).gte(
                "record_date", start_date
            ).lte("record_date", end_date).order("record_date", desc=False).execute()

            records = result.data or []

            # Calculate summary
            total_records = len(records)
            compliant_days = sum(1 for r in records if r.get("is_daily_compliant"))
            non_compliant_days = total_records - compliant_days

            avg_rest_hours = (
                sum(r.get("total_rest_hours", 0) for r in records) / total_records
                if total_records > 0 else 0
            )

            # Get active warnings count
            warnings_result = self.db.table("pms_crew_hours_warnings").select(
                "id", count="exact"
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
                "status", "active"
            ).execute()

            active_warnings_count = warnings_result.count or 0

            builder.set_data({
                "records": records,
                "summary": {
                    "total_records": total_records,
                    "compliant_days": compliant_days,
                    "non_compliant_days": non_compliant_days,
                    "compliance_rate": round(compliant_days / total_records * 100, 1) if total_records > 0 else 0,
                    "average_rest_hours": round(avg_rest_hours, 1),
                    "active_warnings": active_warnings_count,
                },
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            })

            # Available actions
            builder.add_available_action(AvailableAction(
                action_id="upsert_hours_of_rest",
                label="Log Hours",
                variant="MUTATE",
                icon="clock",
                is_primary=True
            ))

            builder.add_available_action(AvailableAction(
                action_id="list_crew_warnings",
                label="View Warnings",
                variant="READ",
                icon="alert-triangle",
                is_primary=False
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"Error fetching hours of rest: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MUTATE HANDLERS - Daily Hours of Rest
    # =========================================================================

    async def upsert_hours_of_rest(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/upsert

        Create or update daily HoR record.

        Payload:
        - record_date: YYYY-MM-DD (required)
        - rest_periods: Array of {start, end, hours} (required)
        - total_rest_hours: Calculated sum (required)
        - total_work_hours: 24 - total_rest_hours (optional)
        - daily_compliance_notes: Optional notes

        Returns:
        - Upserted HoR record
        - Compliance status
        - Auto-generated warnings (if any violations)
        """
        builder = ResponseBuilder("upsert_hours_of_rest", entity_id, "hours_of_rest", yacht_id)

        try:
            record_date = payload.get("record_date")
            rest_periods = payload.get("rest_periods", [])
            total_rest_hours = payload.get("total_rest_hours")
            daily_compliance_notes = payload.get("daily_compliance_notes")

            if not record_date or not rest_periods:
                builder.set_error("VALIDATION_ERROR", "record_date and rest_periods are required")
                return builder.build()

            # Calculate totals
            if total_rest_hours is None:
                total_rest_hours = sum(p.get("hours", 0) for p in rest_periods)

            total_work_hours = 24 - total_rest_hours

            # Check daily compliance (MLC 2006: 10 hrs minimum)
            is_daily_compliant = total_rest_hours >= 10

            # Check rest period rules (no more than 2 periods, one at least 6 hrs)
            rest_period_count = len(rest_periods)
            longest_rest_period = max((p.get("hours", 0) for p in rest_periods), default=0)

            has_valid_rest_periods = (
                rest_period_count <= 2 and
                longest_rest_period >= 6
            )

            # Upsert record
            upsert_data = {
                "yacht_id": yacht_id,
                "user_id": user_id,
                "record_date": record_date,
                "rest_periods": json.dumps(rest_periods) if isinstance(rest_periods, list) else rest_periods,
                "total_rest_hours": total_rest_hours,
                "total_work_hours": total_work_hours,
                "is_daily_compliant": is_daily_compliant and has_valid_rest_periods,
                "daily_compliance_notes": daily_compliance_notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if record exists
            existing = self.db.table("pms_hours_of_rest").select("id").eq(
                "yacht_id", yacht_id
            ).eq("user_id", user_id).eq("record_date", record_date).maybe_single().execute()

            if existing.data:
                # Update
                result = self.db.table("pms_hours_of_rest").update(upsert_data).eq(
                    "id", existing.data["id"]
                ).execute()
                record = result.data[0] if result.data else None
                action_taken = "updated"
            else:
                # Insert
                upsert_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = self.db.table("pms_hours_of_rest").insert(upsert_data).execute()
                record = result.data[0] if result.data else None
                action_taken = "created"

            # Check for violations and create warnings
            warnings_created = []
            if record and record.get("id"):
                # Call check_hor_violations function
                violation_check = self.db.rpc(
                    "check_hor_violations",
                    {"p_hor_id": record["id"]}
                ).execute()

                if violation_check.data:
                    warnings_created = violation_check.data

            builder.set_data({
                "record": record,
                "action_taken": action_taken,
                "compliance": {
                    "is_daily_compliant": is_daily_compliant and has_valid_rest_periods,
                    "total_rest_hours": total_rest_hours,
                    "meets_mlc_minimum": total_rest_hours >= 10,
                    "has_valid_rest_periods": has_valid_rest_periods,
                    "rest_period_count": rest_period_count,
                    "longest_rest_period": longest_rest_period,
                },
                "warnings_created": warnings_created,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error upserting hours of rest: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # READ HANDLERS - Monthly Sign-offs
    # =========================================================================

    async def list_monthly_signoffs(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/signoffs

        List monthly sign-offs for user or department.

        Params:
        - user_id: Filter by user (optional)
        - department: Filter by department (optional)
        - status: Filter by status (optional)
        - limit: Page size (default: 50)
        - offset: Page offset (default: 0)

        Returns:
        - List of monthly sign-offs
        - Pending sign-offs count
        """
        builder = ResponseBuilder("list_monthly_signoffs", entity_id, "monthly_signoff", yacht_id)

        try:
            params = params or {}
            user_filter = params.get("user_id")
            department_filter = params.get("department")
            status_filter = params.get("status")
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)

            # Build query
            query = self.db.table("pms_hor_monthly_signoffs").select(
                "id, user_id, department, month, status, "
                "crew_signature, crew_signed_at, crew_signed_by, "
                "hod_signature, hod_signed_at, hod_signed_by, "
                "master_signature, master_signed_at, master_signed_by, "
                "total_rest_hours, total_work_hours, violation_count, "
                "compliance_percentage, created_at, updated_at",
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if user_filter:
                query = query.eq("user_id", user_filter)
            if department_filter:
                query = query.eq("department", department_filter)
            if status_filter:
                query = query.eq("status", status_filter)

            # Execute with pagination
            result = query.order("month", desc=True).order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            signoffs = result.data or []
            total_count = result.count or len(signoffs)

            # Count pending signoffs
            pending_count = sum(
                1 for s in signoffs if s.get("status") in ["draft", "crew_signed", "hod_signed"]
            )

            builder.set_data({
                "signoffs": signoffs,
                "pending_count": pending_count,
            })

            builder.set_pagination(offset, limit, total_count)

            # Available actions
            builder.add_available_action(AvailableAction(
                action_id="create_monthly_signoff",
                label="Create Sign-off",
                variant="MUTATE",
                icon="file-signature",
                is_primary=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"Error listing monthly signoffs: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def get_monthly_signoff(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/signoffs/{id}

        Get monthly sign-off details.

        Returns:
        - Sign-off details with all signatures
        - Month summary (total hours, violations, compliance %)
        - Available actions (sign, view records)
        """
        builder = ResponseBuilder("get_monthly_signoff", entity_id, "monthly_signoff", yacht_id)

        try:
            result = self.db.table("pms_hor_monthly_signoffs").select(
                "*, user:user_id(email, name)"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Sign-off not found: {entity_id}")
                return builder.build()

            signoff = result.data

            # Calculate month completeness
            month_complete_check = self.db.rpc(
                "is_month_complete",
                {
                    "p_yacht_id": yacht_id,
                    "p_user_id": signoff["user_id"],
                    "p_month": signoff["month"]
                }
            ).execute()

            is_month_complete = month_complete_check.data if month_complete_check.data is not None else False

            builder.set_data({
                "signoff": signoff,
                "is_month_complete": is_month_complete,
            })

            # Available actions based on status and role
            status = signoff.get("status")

            if status in ["draft", "crew_signed", "hod_signed"]:
                builder.add_available_action(AvailableAction(
                    action_id="sign_monthly_signoff",
                    label="Sign",
                    variant="MUTATE",
                    icon="pen",
                    is_primary=True
                ))

            builder.add_available_action(AvailableAction(
                action_id="get_hours_of_rest",
                label="View Records",
                variant="READ",
                icon="list",
                is_primary=False
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"Error getting monthly signoff: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MUTATE HANDLERS - Monthly Sign-offs
    # =========================================================================

    async def create_monthly_signoff(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/signoffs/create

        Create monthly sign-off (must start as draft).

        Payload:
        - month: YYYY-MM format (required)
        - department: engineering/deck/interior/galley/general (required)

        Returns:
        - Created sign-off record
        - Month summary
        """
        builder = ResponseBuilder("create_monthly_signoff", entity_id, "monthly_signoff", yacht_id)

        try:
            month = payload.get("month")
            department = payload.get("department")

            if not month or not department:
                builder.set_error("VALIDATION_ERROR", "month and department are required")
                return builder.build()

            # Check if sign-off already exists
            existing = self.db.table("pms_hor_monthly_signoffs").select("id").eq(
                "yacht_id", yacht_id
            ).eq("user_id", user_id).eq("month", month).maybe_single().execute()

            if existing.data:
                builder.set_error("DUPLICATE_ERROR", f"Sign-off already exists for {month}")
                return builder.build()

            # Calculate month summary
            summary_result = self.db.rpc(
                "calculate_month_summary",
                {
                    "p_yacht_id": yacht_id,
                    "p_user_id": user_id,
                    "p_month": month
                }
            ).execute()

            summary = summary_result.data[0] if summary_result.data else {}
            total_rest = summary.get("total_rest", 0)
            total_work = summary.get("total_work", 0)
            violations = summary.get("violations", 0)
            compliance_pct = summary.get("compliance_pct", 0)

            # Create sign-off
            insert_data = {
                "yacht_id": yacht_id,
                "user_id": user_id,
                "department": department,
                "month": month,
                "status": "draft",
                "total_rest_hours": total_rest,
                "total_work_hours": total_work,
                "violation_count": violations,
                "compliance_percentage": compliance_pct,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_hor_monthly_signoffs").insert(insert_data).execute()
            signoff = result.data[0] if result.data else None

            builder.set_data({
                "signoff": signoff,
                "summary": summary,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error creating monthly signoff: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def sign_monthly_signoff(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/signoffs/sign

        Add signature to monthly sign-off (crew/HOD/captain).

        Payload:
        - signoff_id: UUID (required)
        - signature_level: crew|hod|master (required)
        - signature_data: {name, timestamp, ip_address} (required)
        - notes: Optional notes/declaration

        Returns:
        - Updated sign-off with new signature
        - Next workflow status
        """
        builder = ResponseBuilder("sign_monthly_signoff", entity_id, "monthly_signoff", yacht_id)

        try:
            signoff_id = payload.get("signoff_id")
            signature_level = payload.get("signature_level")
            signature_data = payload.get("signature_data")
            notes = payload.get("notes")

            if not signoff_id or not signature_level or not signature_data:
                builder.set_error("VALIDATION_ERROR", "signoff_id, signature_level, and signature_data are required")
                return builder.build()

            # Fetch current sign-off
            current = self.db.table("pms_hor_monthly_signoffs").select("*").eq(
                "id", signoff_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            if not current.data:
                builder.set_error("NOT_FOUND", f"Sign-off not found: {signoff_id}")
                return builder.build()

            signoff = current.data

            # Determine update based on signature level
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if signature_level == "crew":
                update_data.update({
                    "crew_signature": json.dumps(signature_data) if isinstance(signature_data, dict) else signature_data,
                    "crew_signed_at": datetime.now(timezone.utc).isoformat(),
                    "crew_signed_by": user_id,
                    "crew_declaration": notes,
                    "status": "crew_signed"
                })
            elif signature_level == "hod":
                update_data.update({
                    "hod_signature": json.dumps(signature_data) if isinstance(signature_data, dict) else signature_data,
                    "hod_signed_at": datetime.now(timezone.utc).isoformat(),
                    "hod_signed_by": user_id,
                    "hod_notes": notes,
                    "status": "hod_signed"
                })
            elif signature_level == "master":
                update_data.update({
                    "master_signature": json.dumps(signature_data) if isinstance(signature_data, dict) else signature_data,
                    "master_signed_at": datetime.now(timezone.utc).isoformat(),
                    "master_signed_by": user_id,
                    "master_notes": notes,
                    "status": "finalized"
                })
            else:
                builder.set_error("VALIDATION_ERROR", f"Invalid signature_level: {signature_level}")
                return builder.build()

            # Update sign-off
            result = self.db.table("pms_hor_monthly_signoffs").update(update_data).eq(
                "id", signoff_id
            ).execute()

            updated_signoff = result.data[0] if result.data else None

            builder.set_data({
                "signoff": updated_signoff,
                "signature_level": signature_level,
                "new_status": update_data.get("status"),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error signing monthly signoff: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # READ HANDLERS - Schedule Templates
    # =========================================================================

    async def list_crew_templates(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/templates

        List schedule templates for user.

        Params:
        - user_id: Target user (defaults to current user)
        - is_active: Filter active only (default: true)

        Returns:
        - List of templates
        - Active template highlighted
        """
        builder = ResponseBuilder("list_crew_templates", entity_id, "crew_template", yacht_id)

        try:
            params = params or {}
            user_filter = params.get("user_id", entity_id)
            active_only = params.get("is_active", True)

            query = self.db.table("pms_crew_normal_hours").select(
                "id, schedule_name, description, schedule_template, "
                "is_active, applies_to, last_applied_at, created_at, updated_at"
            ).eq("yacht_id", yacht_id).eq("user_id", user_filter)

            if active_only:
                query = query.eq("is_active", True)

            result = query.order("is_active", desc=True).order(
                "created_at", desc=True
            ).execute()

            templates = result.data or []

            builder.set_data({
                "templates": templates,
                "active_template": next((t for t in templates if t.get("is_active")), None),
            })

            # Available actions
            builder.add_available_action(AvailableAction(
                action_id="create_crew_template",
                label="New Template",
                variant="MUTATE",
                icon="plus",
                is_primary=True
            ))

            if templates:
                builder.add_available_action(AvailableAction(
                    action_id="apply_crew_template",
                    label="Apply to Week",
                    variant="MUTATE",
                    icon="calendar",
                    is_primary=False
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"Error listing crew templates: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MUTATE HANDLERS - Schedule Templates
    # =========================================================================

    async def create_crew_template(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/templates/create

        Create schedule template.

        Payload:
        - schedule_name: Template name (required)
        - description: Template description (optional)
        - schedule_template: JSONB with 7 days (required)
        - applies_to: normal|port|transit (default: normal)
        - is_active: Activate template (default: true)

        Returns:
        - Created template
        """
        builder = ResponseBuilder("create_crew_template", entity_id, "crew_template", yacht_id)

        try:
            schedule_name = payload.get("schedule_name")
            description = payload.get("description")
            schedule_template = payload.get("schedule_template")
            applies_to = payload.get("applies_to", "normal")
            is_active = payload.get("is_active", True)

            if not schedule_name or not schedule_template:
                builder.set_error("VALIDATION_ERROR", "schedule_name and schedule_template are required")
                return builder.build()

            # If setting as active, deactivate other templates
            if is_active:
                self.db.table("pms_crew_normal_hours").update({
                    "is_active": False
                }).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
                    "applies_to", applies_to
                ).execute()

            # Create template
            insert_data = {
                "yacht_id": yacht_id,
                "user_id": user_id,
                "schedule_name": schedule_name,
                "description": description,
                "schedule_template": json.dumps(schedule_template) if isinstance(schedule_template, dict) else schedule_template,
                "applies_to": applies_to,
                "is_active": is_active,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_crew_normal_hours").insert(insert_data).execute()
            template = result.data[0] if result.data else None

            builder.set_data({
                "template": template,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error creating crew template: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def apply_crew_template(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/templates/apply

        Apply template to week of dates.

        Payload:
        - week_start_date: YYYY-MM-DD (required, Monday)
        - template_id: UUID (optional, uses active template if not provided)

        Returns:
        - Applied dates with success/failure per day
        - Summary of records created
        """
        builder = ResponseBuilder("apply_crew_template", entity_id, "crew_template", yacht_id)

        try:
            week_start_date = payload.get("week_start_date")
            template_id = payload.get("template_id")

            if not week_start_date:
                builder.set_error("VALIDATION_ERROR", "week_start_date is required")
                return builder.build()

            # Call apply_template_to_week function
            rpc_result = self.db.rpc(
                "apply_template_to_week",
                {
                    "p_yacht_id": yacht_id,
                    "p_user_id": user_id,
                    "p_week_start_date": week_start_date,
                    "p_template_id": template_id
                }
            ).execute()

            application_results = rpc_result.data or []

            # Count successes
            created_count = sum(1 for r in application_results if r.get("created"))
            skipped_count = len(application_results) - created_count

            builder.set_data({
                "application_results": application_results,
                "summary": {
                    "total_days": len(application_results),
                    "created": created_count,
                    "skipped": skipped_count,
                },
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error applying crew template: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # READ HANDLERS - Warnings
    # =========================================================================

    async def list_crew_warnings(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/warnings

        List compliance warnings for user.

        Params:
        - user_id: Target user (defaults to current user)
        - status: Filter by status (active|acknowledged|dismissed)
        - warning_type: Filter by type
        - limit: Page size
        - offset: Page offset

        Returns:
        - List of warnings
        - Active warnings count
        - Critical warnings count
        """
        builder = ResponseBuilder("list_crew_warnings", entity_id, "crew_warning", yacht_id)

        try:
            params = params or {}
            user_filter = params.get("user_id", entity_id)
            status_filter = params.get("status")
            warning_type_filter = params.get("warning_type")
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)

            query = self.db.table("pms_crew_hours_warnings").select(
                "id, user_id, warning_type, severity, record_date, "
                "message, violation_data, status, "
                "acknowledged_at, acknowledged_by, crew_reason, "
                "dismissed_at, dismissed_by, dismissed_by_role, "
                "hod_justification, is_dismissed, created_at, updated_at",
                count="exact"
            ).eq("yacht_id", yacht_id).eq("user_id", user_filter)

            if status_filter:
                query = query.eq("status", status_filter)
            if warning_type_filter:
                query = query.eq("warning_type", warning_type_filter)

            result = query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            warnings = result.data or []
            total_count = result.count or len(warnings)

            # Count by status and severity
            active_count = sum(1 for w in warnings if w.get("status") == "active")
            critical_count = sum(1 for w in warnings if w.get("severity") == "critical")

            builder.set_data({
                "warnings": warnings,
                "summary": {
                    "active_count": active_count,
                    "critical_count": critical_count,
                },
            })

            builder.set_pagination(offset, limit, total_count)

            # Available actions
            if active_count > 0:
                builder.add_available_action(AvailableAction(
                    action_id="acknowledge_warning",
                    label="Acknowledge",
                    variant="MUTATE",
                    icon="check",
                    is_primary=True
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"Error listing crew warnings: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MUTATE HANDLERS - Warnings
    # =========================================================================

    async def acknowledge_warning(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/warnings/acknowledge

        Crew acknowledges warning (cannot dismiss).

        Payload:
        - warning_id: UUID (required)
        - crew_reason: Explanation text (optional)

        Returns:
        - Updated warning
        """
        builder = ResponseBuilder("acknowledge_warning", entity_id, "crew_warning", yacht_id)

        try:
            warning_id = payload.get("warning_id")
            crew_reason = payload.get("crew_reason")

            if not warning_id:
                builder.set_error("VALIDATION_ERROR", "warning_id is required")
                return builder.build()

            update_data = {
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged_by": user_id,
                "crew_reason": crew_reason,
                "status": "acknowledged",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_crew_hours_warnings").update(update_data).eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).execute()

            warning = result.data[0] if result.data else None

            if not warning:
                builder.set_error("NOT_FOUND", f"Warning not found or not accessible: {warning_id}")
                return builder.build()

            builder.set_data({
                "warning": warning,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error acknowledging warning: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def dismiss_warning(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/warnings/dismiss

        HOD/Captain dismisses warning (requires justification).

        Payload:
        - warning_id: UUID (required)
        - hod_justification: Explanation (required)
        - dismissed_by_role: hod|captain (required)

        Returns:
        - Updated warning
        """
        builder = ResponseBuilder("dismiss_warning", entity_id, "crew_warning", yacht_id)

        try:
            warning_id = payload.get("warning_id")
            hod_justification = payload.get("hod_justification")
            dismissed_by_role = payload.get("dismissed_by_role")

            if not warning_id or not hod_justification or not dismissed_by_role:
                builder.set_error("VALIDATION_ERROR", "warning_id, hod_justification, and dismissed_by_role are required")
                return builder.build()

            update_data = {
                "is_dismissed": True,
                "dismissed_at": datetime.now(timezone.utc).isoformat(),
                "dismissed_by": user_id,
                "dismissed_by_role": dismissed_by_role,
                "hod_justification": hod_justification,
                "status": "dismissed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_crew_hours_warnings").update(update_data).eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).execute()

            warning = result.data[0] if result.data else None

            if not warning:
                builder.set_error("NOT_FOUND", f"Warning not found: {warning_id}")
                return builder.build()

            builder.set_data({
                "warning": warning,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error dismissing warning: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()
