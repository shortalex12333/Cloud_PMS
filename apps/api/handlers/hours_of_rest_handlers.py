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
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Write Audit Log
# =============================================================================

def _write_hor_audit_log(db, entry: Dict):
    """
    Write entry to pms_audit_log for HOR actions.

    INVARIANT: signature is NEVER NULL - {} for non-signed, full payload for signed.
    """
    try:
        audit_payload = {
            "yacht_id": entry["yacht_id"],
            "entity_type": entry.get("entity_type", "hours_of_rest"),
            "entity_id": entry["entity_id"],
            "action": entry["action"],
            "user_id": entry["user_id"],
            "old_values": entry.get("old_values"),
            "new_values": entry.get("new_values"),
            "signature": entry.get("signature", {}),  # Default to {} if not provided
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("pms_audit_log").insert(audit_payload).execute()
    except Exception as e:
        logger.error(f"Failed to write HOR audit log: {e}")


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
                "weekly_rest_hours, "
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
        - work_periods: Array of {start, end} — crew's working hours (required)
          Backend derives rest_periods as the 24h complement and stores both.
        - daily_compliance_notes: Optional notes

        Returns:
        - Upserted HoR record
        - Compliance status
        - Auto-generated warnings (if any violations)
        """
        builder = ResponseBuilder("upsert_hours_of_rest", entity_id, "hours_of_rest", yacht_id)

        try:
            record_date  = payload.get("record_date")
            work_periods = payload.get("work_periods", [])
            daily_compliance_notes = payload.get("daily_compliance_notes")

            if not record_date:
                builder.set_error("VALIDATION_ERROR", "record_date is required")
                return builder.build()

            # Phase 7 lock: reject if weekly OR monthly signoff is finalized or locked
            try:
                from datetime import date as date_type
                rd = date_type.fromisoformat(str(record_date))
                week_mon = (rd - timedelta(days=rd.weekday())).isoformat()
                month_str = str(record_date)[:7]  # YYYY-MM

                # Check weekly lock
                lock_check_result = self.db.table("pms_hor_monthly_signoffs").select(
                    "status"
                ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
                    "period_type", "weekly"
                ).eq("week_start", week_mon).execute()

                if any(r.get("status") in ("finalized", "locked")
                       for r in (lock_check_result.data or [])):
                    builder.set_error(
                        "LOCKED",
                        f"Week of {week_mon} is finalized and cannot be modified. Contact your HOD to raise a correction."
                    )
                    return builder.build()

                # Check monthly lock
                monthly_lock_result = self.db.table("pms_hor_monthly_signoffs").select(
                    "status"
                ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
                    "period_type", "monthly"
                ).eq("month", month_str).execute()

                if any(r.get("status") in ("finalized", "locked", "captain_signed")
                       for r in (monthly_lock_result.data or [])):
                    builder.set_error(
                        "LOCKED",
                        f"Month {month_str} is finalized and cannot be modified. Contact your captain to raise a correction."
                    )
                    return builder.build()

            except Exception as lock_err:
                logger.warning(f"Lock check failed (FATAL — blocking upsert): {lock_err}")
                builder.set_error("DATABASE_ERROR", f"Lock check failed: {lock_err}")
                return builder.build()

            # Validate: each work_period must have start and end
            for p in work_periods:
                if not p.get("start") or not p.get("end"):
                    builder.set_error("VALIDATION_ERROR",
                        "Each work_period must have start and end (HH:MM format)")
                    return builder.build()

            # Validate: no overlapping work periods
            sorted_work = sorted(work_periods, key=lambda p: p.get("start", ""))
            for i in range(len(sorted_work) - 1):
                a, b = sorted_work[i], sorted_work[i + 1]
                if a.get("end", "") > b.get("start", ""):
                    builder.set_error("VALIDATION_ERROR", "Work periods must not overlap")
                    return builder.build()

            def _period_hours(p: dict) -> float:
                if "hours" in p:
                    return float(p["hours"])
                try:
                    sh, sm = map(int, str(p["start"]).split(":"))
                    eh, em = map(int, str(p["end"]).split(":"))
                    start_mins = sh * 60 + sm
                    end_mins   = eh * 60 + em
                    if end_mins <= start_mins:  # overnight
                        end_mins += 24 * 60
                    return round((end_mins - start_mins) / 60, 2)
                except Exception:
                    return 0.0

            # Inject hours into work_periods
            work_periods = [dict(p, hours=_period_hours(p)) for p in sorted_work]

            # Derive rest_periods as 24h complement of work_periods
            def _complement(periods: list) -> list:
                """Return gaps between 00:00 and 24:00 not covered by periods."""
                if not periods:
                    return [{"start": "00:00", "end": "24:00", "hours": 24.0}]
                rest = []
                prev_end = "00:00"
                for wp in periods:
                    wp_start = wp.get("start", "")
                    if wp_start > prev_end:
                        gap = {"start": prev_end, "end": wp_start}
                        rest.append(dict(gap, hours=_period_hours(gap)))
                    prev_end = wp.get("end", "")
                if prev_end < "24:00":
                    gap = {"start": prev_end, "end": "24:00"}
                    rest.append(dict(gap, hours=_period_hours(gap)))
                return rest

            rest_periods = _complement(work_periods)

            total_work_hours = sum(p["hours"] for p in work_periods)
            total_rest_hours = 24 - total_work_hours

            # MLC 2006 compliance checks
            is_daily_compliant = total_rest_hours >= 10
            rest_period_count = len(rest_periods)
            longest_rest_period = max((_period_hours(p) for p in rest_periods), default=0.0)

            has_valid_rest_periods = (
                rest_period_count <= 2 and
                longest_rest_period >= 6
            )

            # Upsert record
            upsert_data = {
                "yacht_id": yacht_id,
                "user_id": user_id,
                "record_date": record_date,
                "work_periods": work_periods,
                "rest_periods": rest_periods,
                "total_rest_hours": total_rest_hours,
                "total_work_hours": total_work_hours,
                "is_daily_compliant": is_daily_compliant and has_valid_rest_periods,
                "daily_compliance_notes": daily_compliance_notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if record exists (handle RLS/406 errors gracefully)
            record_exists = False
            existing_id = None

            try:
                existing = self.db.table("pms_hours_of_rest").select("id").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", user_id).eq("record_date", record_date).limit(1).execute()

                if existing and existing.data:
                    record_exists = True
                    existing_id = existing.data[0]["id"]
            except Exception as check_err:
                # 406/RLS errors mean no existing record or no permission
                # Safe to attempt INSERT (will fail with 403 if not allowed)
                logger.debug(f"Existence check failed (likely no record): {check_err}")
                record_exists = False

            if record_exists and existing_id:
                # Update existing record — separate SELECT after UPDATE
                # (SyncQueryRequestBuilder doesn't support .select() after .update())
                self.db.table("pms_hours_of_rest").update(upsert_data).eq(
                    "id", existing_id
                ).execute()
                result = self.db.table("pms_hours_of_rest").select("*").eq(
                    "id", existing_id
                ).execute()
                record = result.data[0] if result.data else None
                action_taken = "updated"
            else:
                # Insert new record — separate SELECT after INSERT
                # (SyncQueryRequestBuilder doesn't support .select() after .insert())
                upsert_data["created_at"] = datetime.now(timezone.utc).isoformat()
                self.db.table("pms_hours_of_rest").insert(upsert_data).execute()
                result = self.db.table("pms_hours_of_rest").select("*").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", user_id).eq("record_date", record_date).execute()
                record = result.data[0] if result.data else None
                action_taken = "created"

            # Write audit log + ledger event
            if record and record.get("id"):
                _write_hor_audit_log(self.db, {
                    "yacht_id": yacht_id,
                    "entity_type": "hours_of_rest",
                    "entity_id": str(record["id"]),
                    "action": f"upsert_hours_of_rest:{action_taken}",
                    "user_id": user_id,
                    "new_values": {"record_date": record_date, "total_rest_hours": total_rest_hours},
                    "signature": payload.get("signature", {}),  # {} for non-signed
                })

                # Insert into ledger_events so the ledger panel reflects HoR submissions
                is_violation = not (is_daily_compliant and has_valid_rest_periods)
                try:
                    ledger_event = build_ledger_event(
                        yacht_id=yacht_id,
                        user_id=user_id,
                        event_type="create" if action_taken == "created" else "update",
                        entity_type="hours_of_rest",
                        entity_id=str(record["id"]),
                        action="upsert_hours_of_rest",
                        change_summary=(
                            f"HoR submitted for {record_date}: "
                            f"{total_rest_hours:.1f}h rest, "
                            f"{'VIOLATION' if is_violation else 'compliant'}"
                        ),
                        metadata={
                            "record_date": record_date,
                            "total_rest_hours": total_rest_hours,
                            "total_work_hours": total_work_hours,
                            "is_daily_compliant": not is_violation,
                            "violation": is_violation,
                        },
                        event_category="write",
                    )
                    self.db.table("ledger_events").insert(ledger_event).execute()
                except Exception as ledger_err:
                    logger.warning(f"Ledger insert failed (non-fatal): {ledger_err}")

            # Check for violations and create warnings
            warnings_created = []
            if record and record.get("id"):
                # Dedup: delete any pre-existing non-daily warnings for this 7-day window
                # before calling check_hor_violations, so weekly violations don't accumulate
                # one row per day-submission (7 duplicates per week).
                try:
                    week_end_str = (rd + timedelta(days=6 - rd.weekday())).isoformat()
                    self.db.table("pms_crew_hours_warnings").delete().eq(
                        "yacht_id", yacht_id
                    ).eq("user_id", user_id).neq(
                        "warning_type", "DAILY_REST"
                    ).gte("record_date", week_mon).lte(
                        "record_date", week_end_str
                    ).execute()
                except Exception as dedup_err:
                    logger.warning(f"Weekly warning dedup failed (non-fatal): {dedup_err}")

                # Call check_hor_violations function
                violation_check = self.db.rpc(
                    "check_hor_violations",
                    {"p_hor_id": record["id"]}
                ).execute()

                if violation_check.data:
                    warnings_created = violation_check.data

                # S7: if violation, notify the crew member's HOD
                is_violation = not (is_daily_compliant and has_valid_rest_periods)
                if is_violation:
                    try:
                        # Find HOD for this user's department.
                        # Use list-mode (not .maybe_single()) to handle users with multiple dept rows.
                        crew_role_rows = self.db.table("auth_users_roles").select(
                            "department"
                        ).eq("yacht_id", yacht_id).eq("user_id", user_id).limit(1).execute()
                        dept = (crew_role_rows.data[0] if crew_role_rows.data else {}).get("department")

                        # Notify HOD roles + captain/manager (they hold final responsibility)
                        HOD_ROLES = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"]
                        if dept:
                            hod_result = self.db.table("auth_users_roles").select(
                                "user_id"
                            ).eq("yacht_id", yacht_id).eq("department", dept).in_(
                                "role", HOD_ROLES
                            ).execute()
                            # Fallback: no HOD in crew's dept — notify all HOD users on vessel
                            if not (hod_result.data or []):
                                hod_result = self.db.table("auth_users_roles").select(
                                    "user_id"
                                ).eq("yacht_id", yacht_id).in_(
                                    "role", HOD_ROLES
                                ).execute()
                        else:
                            hod_result = self.db.table("auth_users_roles").select(
                                "user_id"
                            ).eq("yacht_id", yacht_id).in_(
                                "role", HOD_ROLES
                            ).execute()

                        # Notify all resolved HOD users — runs regardless of dept path
                        # Use list-mode (not .maybe_single()) — throws APIError(204) on 0 rows
                        crew_profile_rows = self.db.table("auth_users_profiles").select(
                            "name"
                        ).eq("yacht_id", yacht_id).eq("id", user_id).limit(1).execute()
                        crew_name = (crew_profile_rows.data[0] if crew_profile_rows.data else {}).get("name") or "Crew member"

                        # Deduplicate by user_id — auth_users_roles has one row per role,
                        # so the same user can appear multiple times if they hold multiple roles.
                        seen_hod_ids: set = set()
                        notifications = []
                        for hod in (hod_result.data or []):
                            hod_uid = hod["user_id"]
                            if hod_uid in seen_hod_ids:
                                continue
                            seen_hod_ids.add(hod_uid)
                            notifications.append({
                                "yacht_id": yacht_id,
                                "user_id": hod_uid,
                                "notification_type": "violation_alert",
                                "title": f"HoR Violation — {crew_name}",
                                "body": (
                                    # Period-structure violation: total rest is sufficient but split wrong
                                    f"{crew_name} logged {total_rest_hours:.1f}h rest on {record_date} "
                                    f"split across {rest_period_count} periods — MLC 2006 A2.3 requires "
                                    f"≤2 rest periods, longest ≥6h"
                                    if total_rest_hours >= 10 and not has_valid_rest_periods
                                    # Total-rest violation: not enough hours
                                    else f"{crew_name} logged only {total_rest_hours:.1f}h rest on {record_date} (MLC minimum: 10h)"
                                ),
                                "entity_type": "hours_of_rest",
                                "entity_id": record["id"],
                                "idempotency_key": f"violation:{record['id']}:{hod_uid}",
                                "metadata": {
                                    "crew_user_id": user_id,
                                    "record_date": record_date,
                                    "total_rest_hours": total_rest_hours,
                                    "violation": True,
                                },
                                "is_read": False,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            })
                        if notifications:
                            self.db.table("pms_notifications").upsert(
                                notifications,
                                on_conflict="yacht_id,user_id,idempotency_key"
                            ).execute()
                    except Exception as notif_err:
                        logger.warning(f"Failed to send violation notification (non-fatal): {notif_err}")

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
            period_type_filter = params.get("period_type")
            week_start_filter = params.get("week_start")
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)

            # Build query. NOTE: no cross-schema join to auth.users here —
            # PostgREST cannot resolve auth.users from the public schema,
            # which causes a DATABASE_ERROR instead of a clean success response.
            # User display names are raw UUIDs here; the frontend resolves them.
            query = self.db.table("pms_hor_monthly_signoffs").select(
                "id, user_id, department, month, status, "
                "period_type, week_start, "
                "correction_requested, correction_note, correction_requested_by, "
                "crew_signature, crew_signed_at, crew_signed_by, "
                "hod_signature, hod_signed_at, hod_signed_by, "
                "master_signature, master_signed_at, master_signed_by, "
                "fleet_manager_signed_by, fleet_manager_signed_at, "
                "total_rest_hours, total_work_hours, violation_count, "
                "created_at, updated_at",
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if user_filter:
                query = query.eq("user_id", user_filter)
            if department_filter:
                query = query.eq("department", department_filter)
            if status_filter:
                query = query.eq("status", status_filter)
            if period_type_filter:
                query = query.eq("period_type", period_type_filter)
            if week_start_filter:
                query = query.eq("week_start", week_start_filter)

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

            # Available actions — fleet manager (role=manager) is read-only for HoR
            caller_role = params.get("_caller_role", "")
            if caller_role != "manager":
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
            # NOTE: no cross-schema join to auth.users — PostgREST cannot resolve
            # auth.users from the public schema and throws, which masks the NOT_FOUND path.
            result = self.db.table("pms_hor_monthly_signoffs").select(
                "*"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).limit(1).execute()

            signoff = result.data[0] if result.data else None
            if not signoff:
                builder.set_error("NOT_FOUND", f"Sign-off not found: {entity_id}")
                return builder.build()

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
            period_type = payload.get("period_type", "monthly")
            week_start = payload.get("week_start")
            target_user_id = payload.get("target_user_id") or user_id

            if period_type == "weekly" and not week_start:
                builder.set_error("VALIDATION_ERROR", "week_start is required for weekly sign-offs (YYYY-MM-DD Monday)")
                return builder.build()

            # Auto-derive month from week_start for weekly signoffs
            if period_type == "weekly" and not month and week_start:
                month = week_start[:7]  # YYYY-MM from YYYY-MM-DD

            if not month or not department:
                builder.set_error("VALIDATION_ERROR", "month and department are required")
                return builder.build()

            # Check if sign-off already exists for target user
            # NOTE: .maybe_single() throws APIError(204) in supabase-py 2.12.0 when 0 rows found.
            # Use .execute() list mode instead and check len(data).
            existing_result = self.db.table("pms_hor_monthly_signoffs").select("id").eq(
                "yacht_id", yacht_id
            ).eq("user_id", target_user_id).eq("month", month).execute()

            if existing_result.data:
                builder.set_error("DUPLICATE_ERROR", f"Sign-off already exists for {month}", status_code=409)
                return builder.build()

            # Calculate month summary via RPC (may not exist in DB — graceful fallback)
            try:
                summary_result = self.db.rpc(
                    "calculate_month_summary",
                    {
                        "p_yacht_id": yacht_id,
                        "p_user_id": user_id,
                        "p_month": month
                    }
                ).execute()
            except Exception as rpc_err:
                logger.warning(f"calculate_month_summary RPC failed: {rpc_err}")
                summary_result = None

            # RPC returns a single dict (not a list) — use .data directly
            raw = summary_result.data if (summary_result is not None and hasattr(summary_result, 'data') and summary_result.data) else {}
            summary = raw[0] if isinstance(raw, list) else raw if isinstance(raw, dict) else {}
            total_rest = summary.get("total_rest", 0)
            total_work = summary.get("total_work", 0)
            violations = summary.get("violations", 0)
            compliance_pct = summary.get("compliance_pct", 0)

            # Create sign-off (for target_user_id when HOD is creating for crew)
            insert_data = {
                "yacht_id": yacht_id,
                "user_id": target_user_id,
                "department": department,
                "month": month,
                "status": "draft",
                "total_rest_hours": total_rest,
                "total_work_hours": total_work,
                "violation_count": violations,
                "period_type": period_type,
                "week_start": week_start,
                # compliance_percentage removed — column doesn't exist in DB schema
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Separate SELECT after INSERT (SyncQueryRequestBuilder doesn't support .select() after .insert())
            self.db.table("pms_hor_monthly_signoffs").insert(insert_data).execute()
            result = self.db.table("pms_hor_monthly_signoffs").select("*").eq(
                "yacht_id", yacht_id
            ).eq("user_id", target_user_id).eq("month", month).eq("department", department).execute()
            signoff = result.data[0] if (result is not None and result.data) else None

            # Fix BUG-HOR-2: response entity_id must be the new signoff UUID, not the caller's user_id
            if signoff and signoff.get("id"):
                builder.entity_id = str(signoff["id"])

            # Write audit log
            if signoff and signoff.get("id"):
                _write_hor_audit_log(self.db, {
                    "yacht_id": yacht_id,
                    "entity_type": "monthly_signoff",
                    "entity_id": str(signoff["id"]),
                    "action": "create_monthly_signoff",
                    "user_id": user_id,
                    "new_values": {"month": month, "department": department, "status": "draft"},
                    "signature": {},  # Not a signed action
                })

                # Resolve creator's role for ledger (same pattern as sign handler)
                try:
                    _create_role_r = self.db.table("auth_users_roles").select("role").eq(
                        "user_id", user_id
                    ).eq("yacht_id", yacht_id).limit(1).execute()
                    _create_role = _create_role_r.data[0]["role"] if _create_role_r.data else None
                except Exception:
                    _create_role = None

                # Write ledger event for signoff creation
                try:
                    self.db.table("ledger_events").insert(build_ledger_event(
                        yacht_id=yacht_id,
                        user_id=user_id,
                        event_type="create",
                        entity_type="hours_of_rest_signoff",
                        entity_id=str(signoff["id"]),
                        action="create_monthly_signoff",
                        user_role=_create_role,
                        change_summary=f"HoR signoff period opened for {month}, department {department}",
                        metadata={
                            "month": month,
                            "department": department,
                            "period_type": period_type,
                            "target_user_id": target_user_id,
                        },
                        event_category="write",
                    )).execute()
                except Exception as le:
                    logger.warning(f"Ledger insert failed on signoff creation (non-fatal): {le}")

                # Notify crew member (target_user_id) that their signoff period is now open —
                # only when HOD creates it on their behalf (skip self-creation to avoid noise)
                if target_user_id != user_id:
                    try:
                        self.db.table("pms_notifications").upsert({
                            "yacht_id": yacht_id,
                            "user_id": target_user_id,
                            "notification_type": "hor_signoff_opened",
                            "title": "HoR Sign-Off Period Open",
                            "body": f"Your {month} hours of rest sign-off is now open for your signature.",
                            "entity_type": "pms_hor_monthly_signoffs",
                            "entity_id": str(signoff["id"]),
                            "idempotency_key": f"hor_signoff_opened:{signoff['id']}:{target_user_id}",
                            "triggered_by": user_id,
                            "is_read": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }, on_conflict="idempotency_key").execute()
                    except Exception as notif_err:
                        logger.warning(f"Failed to notify crew of signoff opening (non-fatal): {notif_err}")

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
            # NOTE: .maybe_single() throws APIError(204) in supabase-py 2.12.0 when 0 rows found.
            # Use .execute() list mode and check data explicitly for NOT_FOUND.
            current_result = self.db.table("pms_hor_monthly_signoffs").select("*").eq(
                "id", signoff_id
            ).eq("yacht_id", yacht_id).execute()

            if not current_result.data:
                builder.set_error("NOT_FOUND", f"Sign-off not found: {signoff_id}")
                return builder.build()

            signoff = current_result.data[0]

            # Resolve signer's role for ledger (user_role was NULL — BUG-HOR-LEDGER-1)
            try:
                role_row = self.db.table("auth_users_roles").select("role").eq(
                    "user_id", user_id
                ).eq("yacht_id", yacht_id).limit(1).execute()
                signer_role = role_row.data[0]["role"] if role_row.data else None
            except Exception:
                signer_role = None

            # Role enforcement: only appropriate roles can countersign at each level.
            # Crew can always sign their own records (signature_level == "crew").
            # HOD and master levels require verified role from auth_users_roles.
            _HOD_ROLES_SIGN    = {"chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"}
            _MASTER_ROLES_SIGN = {"captain", "manager"}

            if signature_level in ("hod", "master"):
                # Use list-mode — .maybe_single() throws APIError(204) on 0 rows in supabase-py 2.12.x.
                # A user may also hold multiple roles; take the first.
                role_rows = self.db.table("auth_users_roles").select("role").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", user_id).limit(1).execute()
                caller_role = (role_rows.data[0] if role_rows.data else {}).get("role")

                if signature_level == "hod" and caller_role not in _HOD_ROLES_SIGN:
                    builder.set_error(
                        "FORBIDDEN",
                        f"Role '{caller_role}' cannot countersign as HOD. Requires: chief_engineer, chief_officer, chief_steward, eto, purser, captain, or manager."
                    )
                    return builder.build()

                if signature_level == "master" and caller_role not in _MASTER_ROLES_SIGN:
                    builder.set_error(
                        "FORBIDDEN",
                        f"Role '{caller_role}' cannot give master signature. Requires: captain or manager."
                    )
                    return builder.build()

            # Enforce sequential signing workflow: crew → [hod if dept has a HOD] → master
            current_status = signoff.get("status", "draft")
            signoff_dept   = signoff.get("department", "")

            # Hard stop: finalized records are immutable — no further signatures at any level.
            # MLC 2006 requires the signed record to be preserved exactly as certified by master.
            if current_status == "finalized":
                builder.set_error(
                    "VALIDATION_ERROR",
                    "This sign-off has been finalized by the Master and is now immutable. "
                    "No further signatures can be added. Raise a correction request if changes are needed."
                )
                return builder.build()

            # BUG-HOR-7 fix: crew may only sign their own signoff
            if signature_level == "crew":
                signoff_owner_id = signoff.get("user_id")
                if signoff_owner_id and signoff_owner_id != user_id:
                    builder.set_error(
                        "FORBIDDEN",
                        "Crew can only sign their own monthly sign-off. Cross-user signing is not permitted."
                    )
                    return builder.build()
                # BUG-HOR-6 fix: crew sign only valid from draft state — prevents status regression
                if current_status != "draft":
                    builder.set_error(
                        "VALIDATION_ERROR",
                        f"Crew signature is only valid on a draft sign-off. Current status: {current_status}. "
                        "Once a sign-off progresses past draft it cannot be re-signed at crew level."
                    )
                    return builder.build()

            if signature_level == "hod" and current_status != "crew_signed":
                builder.set_error(
                    "VALIDATION_ERROR",
                    f"HOD can only sign after crew. Current status: {current_status}"
                )
                return builder.build()

            elif signature_level == "master":
                if current_status == "hod_signed":
                    # Normal path. Block same-person signing — MLC requires independent HOD + master.
                    hod_signed_by = signoff.get("hod_signed_by")
                    if hod_signed_by and hod_signed_by == user_id:
                        builder.set_error(
                            "FORBIDDEN",
                            "Master cannot finalise a signoff they counter-signed as HOD. MLC 2006 requires independent verification at each level."
                        )
                        return builder.build()

                elif current_status == "crew_signed":
                    # HOD step not yet completed — only permitted if no designated HOD
                    # exists for this department (pure dept roles, not captain/manager).
                    _DEPT_HOD_ROLES = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser"]
                    dept_hod_q = self.db.table("auth_users_roles").select("user_id").eq(
                        "yacht_id", yacht_id
                    ).in_("role", _DEPT_HOD_ROLES)
                    if signoff_dept:
                        dept_hod_q = dept_hod_q.eq("department", signoff_dept)
                    dept_hod_result = dept_hod_q.limit(1).execute()

                    if dept_hod_result.data:
                        # A designated HOD exists — they must sign before master.
                        builder.set_error(
                            "VALIDATION_ERROR",
                            f"Master can only sign after HOD. Department '{signoff_dept}' has a designated HOD who must countersign first. Current status: {current_status}"
                        )
                        return builder.build()
                    else:
                        # No dept HOD — captain may bypass. Notify vessel-wide HOD-role users.
                        try:
                            vessel_hods = self.db.table("auth_users_roles").select("user_id").eq(
                                "yacht_id", yacht_id
                            ).in_("role", _DEPT_HOD_ROLES).execute()
                            _seen_hod: set = set()
                            bypass_notifs = []
                            for r in (vessel_hods.data or []):
                                uid = r["user_id"]
                                if uid in _seen_hod:
                                    continue
                                _seen_hod.add(uid)
                                bypass_notifs.append({
                                    "yacht_id":           yacht_id,
                                    "user_id":            uid,
                                    "notification_type":  "hor_hod_step_bypassed",
                                    "title":              "HoR HOD Step Bypassed",
                                    "body":               f"No HOD found for department '{signoff_dept}'. Master signed directly. Please review.",
                                    "entity_type":        "pms_hor_monthly_signoffs",
                                    "entity_id":          signoff_id,
                                    "idempotency_key":    f"hor_hod_bypass_{signoff_id}",
                                })
                            if bypass_notifs:
                                self.db.table("pms_notifications").upsert(
                                    bypass_notifs, on_conflict="yacht_id,user_id,idempotency_key"
                                ).execute()
                        except Exception as bypass_notif_err:
                            logger.warning(f"Failed to send HOD-bypass notification (non-fatal): {bypass_notif_err}")
                else:
                    builder.set_error(
                        "VALIDATION_ERROR",
                        f"Master can only sign from hod_signed (or crew_signed when no dept HOD exists). Current status: {current_status}"
                    )
                    return builder.build()

            # Determine update based on signature level
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if signature_level == "crew":
                update_data.update({
                    "crew_signature": signature_data,
                    "crew_signed_at": datetime.now(timezone.utc).isoformat(),
                    "crew_signed_by": user_id,
                    "crew_declaration": notes,
                    "status": "crew_signed"
                })
            elif signature_level == "hod":
                update_data.update({
                    "hod_signature": signature_data,
                    "hod_signed_at": datetime.now(timezone.utc).isoformat(),
                    "hod_signed_by": user_id,
                    "hod_notes": notes,
                    "status": "hod_signed"
                })
            elif signature_level == "master":
                update_data.update({
                    "master_signature": signature_data,
                    "master_signed_at": datetime.now(timezone.utc).isoformat(),
                    "master_signed_by": user_id,
                    "master_notes": notes,
                    "status": "finalized"
                })
            else:
                builder.set_error("VALIDATION_ERROR", f"Invalid signature_level: {signature_level}")
                return builder.build()

            # Update sign-off (SyncFilterRequestBuilder does not support .select() after .update())
            self.db.table("pms_hor_monthly_signoffs").update(update_data).eq(
                "id", signoff_id
            ).execute()
            result = self.db.table("pms_hor_monthly_signoffs").select("*").eq(
                "id", signoff_id
            ).execute()
            updated_signoff = result.data[0] if result.data else None

            # Write audit log with signature
            if updated_signoff:
                _write_hor_audit_log(self.db, {
                    "yacht_id": yacht_id,
                    "entity_type": "monthly_signoff",
                    "entity_id": signoff_id,
                    "action": f"sign_monthly_signoff:{signature_level}",
                    "user_id": user_id,
                    "old_values": {"status": signoff.get("status")},
                    "new_values": {"status": update_data.get("status"), "signature_level": signature_level},
                    "signature": signature_data,  # Actual signature data for signed action
                })

                # Write ledger event for HOD/Captain visibility
                level_labels = {"crew": "hor_crew_signed", "hod": "hor_hod_signed", "master": "hor_master_signed"}
                ledger_action = level_labels.get(signature_level, f"hor_{signature_level}_signed")
                signer_name = signature_data.get("name", "Unknown") if isinstance(signature_data, dict) else "Unknown"
                try:
                    self.db.table("ledger_events").insert(build_ledger_event(
                        yacht_id=yacht_id,
                        user_id=user_id,
                        event_type="approval",
                        entity_type="hours_of_rest_signoff",
                        entity_id=signoff_id,
                        action=ledger_action,
                        user_role=signer_role,
                        department=signoff.get("department"),
                        change_summary=f"{signer_name} signed {signoff.get('month', '')} HoR as {signature_level}",
                        metadata={"signature_level": signature_level, "month": signoff.get("month"), "new_status": update_data.get("status")},
                    )).execute()
                except Exception as le:
                    logger.warning(f"Failed to write ledger event for HoR sign: {le}")

                # Dispatch notification to next party in the sign chain.
                # Non-fatal: a notification failure must never block the sign from completing.
                try:
                    signoff_dept  = signoff.get("department", "")
                    signoff_owner = signoff.get("user_id", "")

                    if signature_level == "crew":
                        # Notify HOD(s) in this department that crew has signed.
                        hod_q = self.db.table("auth_users_roles").select("user_id").eq(
                            "yacht_id", yacht_id
                        ).in_("role", list(_HOD_ROLES_SIGN))
                        if signoff_dept:
                            hod_q = hod_q.eq("department", signoff_dept)
                        hod_result = hod_q.execute()
                        _seen: set = set()
                        notifications = [
                            {
                                "yacht_id": yacht_id,
                                "user_id": row["user_id"],
                                "notification_type": "hor_awaiting_countersign",
                                "title": "HoR Awaiting Counter-Signature",
                                "body": "A crew member has signed their hours of rest — awaiting your counter-signature.",
                                "idempotency_key": f"hor_crew_signed_{signoff_id}_{row['user_id']}",
                            }
                            for row in (hod_result.data or [])
                            if row["user_id"] not in _seen and not _seen.add(row["user_id"])
                        ]
                        if notifications:
                            self.db.table("pms_notifications").upsert(
                                notifications, on_conflict="yacht_id,user_id,idempotency_key"
                            ).execute()

                    elif signature_level == "hod":
                        # Notify captain(s) that HOD has countersigned.
                        cap_result = self.db.table("auth_users_roles").select("user_id").eq(
                            "yacht_id", yacht_id
                        ).in_("role", list(_MASTER_ROLES_SIGN)).execute()
                        _seen2: set = set()
                        notifications = [
                            {
                                "yacht_id": yacht_id,
                                "user_id": row["user_id"],
                                "notification_type": "hor_awaiting_master_sign",
                                "title": "HoR Awaiting Master Signature",
                                "body": "HOD has counter-signed crew hours of rest — awaiting your final signature.",
                                "idempotency_key": f"hor_hod_signed_{signoff_id}_{row['user_id']}",
                            }
                            for row in (cap_result.data or [])
                            if row["user_id"] not in _seen2 and not _seen2.add(row["user_id"])
                        ]
                        if notifications:
                            self.db.table("pms_notifications").upsert(
                                notifications, on_conflict="yacht_id,user_id,idempotency_key"
                            ).execute()

                    elif signature_level == "master":
                        # Notify the crew member that their month is finalized.
                        if signoff_owner:
                            self.db.table("pms_notifications").upsert(
                                [{
                                    "yacht_id": yacht_id,
                                    "user_id": signoff_owner,
                                    "notification_type": "hor_month_finalized",
                                    "title": "Monthly HoR Record Finalized",
                                    "body": "Your monthly hours of rest record has been signed and finalized by the Master.",
                                    "idempotency_key": f"hor_master_signed_{signoff_id}",
                                }],
                                on_conflict="yacht_id,user_id,idempotency_key"
                            ).execute()

                except Exception as notif_err:
                    logger.warning(f"Failed to dispatch sign-chain notification (non-fatal): {notif_err}")

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
                "is_active, applies_to, created_at, updated_at"
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
                "schedule_template": schedule_template,
                "applies_to": applies_to,
                "is_active": is_active,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Separate SELECT after INSERT (SyncQueryRequestBuilder doesn't support .select() after .insert())
            self.db.table("pms_crew_normal_hours").insert(insert_data).execute()
            result = self.db.table("pms_crew_normal_hours").select("*").eq(
                "yacht_id", yacht_id
            ).eq("user_id", user_id).eq("schedule_name", schedule_name).execute()
            template = result.data[0] if result.data else None

            # Write audit log
            if template and template.get("id"):
                _write_hor_audit_log(self.db, {
                    "yacht_id": yacht_id,
                    "entity_type": "crew_template",
                    "entity_id": str(template["id"]),
                    "action": "create_crew_template",
                    "user_id": user_id,
                    "new_values": {"schedule_name": schedule_name, "applies_to": applies_to},
                    "signature": {},  # Not a signed action
                })

                # Write ledger event for template creation
                try:
                    self.db.table("ledger_events").insert(build_ledger_event(
                        yacht_id=yacht_id,
                        user_id=user_id,
                        event_type="create",
                        entity_type="crew_template",
                        entity_id=str(template["id"]),
                        action="create_crew_template",
                        change_summary=f"Schedule template '{schedule_name}' created",
                        metadata={"schedule_name": schedule_name, "applies_to": applies_to},
                        event_category="write",
                    )).execute()
                except Exception as le:
                    logger.warning(f"Ledger insert failed on template creation (non-fatal): {le}")

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

            # Write audit log
            _write_hor_audit_log(self.db, {
                "yacht_id": yacht_id,
                "entity_type": "crew_template",
                "entity_id": template_id or "active_template",
                "action": "apply_crew_template",
                "user_id": user_id,
                "new_values": {"week_start_date": week_start_date, "created": created_count, "skipped": skipped_count},
                "signature": {},  # Not a signed action
            })

            # Write ledger event for template application
            try:
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="update",
                    entity_type="crew_template",
                    entity_id=template_id or "active_template",
                    action="apply_crew_template",
                    change_summary=f"Template applied to week of {week_start_date}: {created_count} records created, {skipped_count} skipped",
                    metadata={"week_start_date": week_start_date, "created": created_count, "skipped": skipped_count},
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on template application (non-fatal): {le}")

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
            error_msg = str(e)
            # No active template or week conflict → client-side fixable → 400
            if "template" in error_msg.lower() or "not found" in error_msg.lower():
                builder.set_error("NOT_FOUND", f"No active template found: {error_msg}")
            else:
                builder.set_error("DATABASE_ERROR", f"Error applying template: {error_msg}")
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

            # Verify warning exists and belongs to this crew member before updating
            existing = self.db.table("pms_crew_hours_warnings").select("id").eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).limit(1).execute()

            if not existing.data:
                builder.set_error("NOT_FOUND", f"Warning not found or not accessible: {warning_id}")
                return builder.build()

            update_data = {
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged_by": user_id,
                "crew_reason": crew_reason,
                "status": "acknowledged",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.db.table("pms_crew_hours_warnings").update(update_data).eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).execute()
            result = self.db.table("pms_crew_hours_warnings").select("*").eq(
                "id", warning_id
            ).limit(1).execute()
            warning = result.data[0] if result.data else None

            # Write audit log
            _write_hor_audit_log(self.db, {
                "yacht_id": yacht_id,
                "entity_type": "crew_warning",
                "entity_id": warning_id,
                "action": "acknowledge_warning",
                "user_id": user_id,
                "new_values": {"status": "acknowledged", "crew_reason": crew_reason},
                "signature": {},  # Not a signed action
            })

            # Write ledger event — crew acknowledgement is legally significant
            try:
                # Resolve caller role for ledger (avoids NULL user_role — BUG-HOR-LEDGER-1 pattern)
                try:
                    _ack_role_r = self.db.table("auth_users_roles").select("role").eq(
                        "user_id", user_id
                    ).eq("yacht_id", yacht_id).limit(1).execute()
                    _ack_role = _ack_role_r.data[0]["role"] if _ack_role_r.data else None
                except Exception:
                    _ack_role = None
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="status_change",
                    entity_type="crew_warning",
                    entity_id=warning_id,
                    action="acknowledge_warning",
                    user_role=_ack_role,
                    change_summary=f"Crew acknowledged compliance warning: {crew_reason or 'no reason given'}",
                    metadata={"status": "acknowledged", "crew_reason": crew_reason, "warning_id": warning_id},
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on warning acknowledgement (non-fatal): {le}")

            # Notify HOD that crew has acknowledged their violation (compliance chain visibility)
            try:
                ack_dept_r = self.db.table("auth_users_roles").select("department").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", user_id).limit(1).execute()
                ack_dept = (ack_dept_r.data[0] if ack_dept_r.data else {}).get("department")

                ack_name_r = self.db.table("auth_users_profiles").select("name").eq(
                    "yacht_id", yacht_id
                ).eq("id", user_id).limit(1).execute()
                ack_crew_name = (ack_name_r.data[0] if ack_name_r.data else {}).get("name") or "Crew member"

                hod_q = self.db.table("auth_users_roles").select("user_id").eq(
                    "yacht_id", yacht_id
                ).in_("role", ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"])
                if ack_dept:
                    hod_q = hod_q.eq("department", ack_dept)
                hod_r = hod_q.execute()

                seen_ack: set = set()
                ack_notifs = []
                for row in (hod_r.data or []):
                    hid = row["user_id"]
                    if hid in seen_ack or hid == user_id:
                        continue
                    seen_ack.add(hid)
                    ack_notifs.append({
                        "yacht_id": yacht_id,
                        "user_id": hid,
                        "notification_type": "hor_warning_acknowledged",
                        "title": f"HoR Warning Acknowledged — {ack_crew_name}",
                        "body": f"{ack_crew_name} has acknowledged their compliance warning: {crew_reason or 'No reason given'}",
                        "entity_type": "crew_warning",
                        "entity_id": warning_id,
                        "idempotency_key": f"hor_ack:{warning_id}:{hid}",
                        "triggered_by": user_id,
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                if ack_notifs:
                    self.db.table("pms_notifications").upsert(
                        ack_notifs, on_conflict="yacht_id,user_id,idempotency_key"
                    ).execute()
            except Exception as notif_err:
                logger.warning(f"Failed to notify HOD of warning acknowledgement (non-fatal): {notif_err}")

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

            # Verify warning exists before updating
            existing = self.db.table("pms_crew_hours_warnings").select("id").eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).limit(1).execute()

            if not existing.data:
                builder.set_error("NOT_FOUND", f"Warning not found: {warning_id}")
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

            # .execute() on update returns the updated rows — use that directly.
            # A separate select().maybe_single() throws APIError(204) in supabase-py 2.x
            # because the dismissed row may not be visible through the active-records view.
            update_result = self.db.table("pms_crew_hours_warnings").update(update_data).eq(
                "id", warning_id
            ).eq("yacht_id", yacht_id).execute()
            warning = update_result.data[0] if (update_result and update_result.data) else None

            # Write audit log with justification
            _write_hor_audit_log(self.db, {
                "yacht_id": yacht_id,
                "entity_type": "crew_warning",
                "entity_id": warning_id,
                "action": "dismiss_warning",
                "user_id": user_id,
                "new_values": {
                    "status": "dismissed",
                    "dismissed_by_role": dismissed_by_role,
                    "hod_justification": hod_justification
                },
                "signature": {},  # Not a SIGNED action, but justification is recorded
            })

            # Write ledger event — HOD/Captain justification for dismissal is legally significant
            try:
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="status_change",
                    entity_type="crew_warning",
                    entity_id=warning_id,
                    action="dismiss_warning",
                    user_role=dismissed_by_role,  # already resolved from payload + DB earlier
                    change_summary=f"{dismissed_by_role.upper()} dismissed compliance warning: {hod_justification}",
                    metadata={
                        "status": "dismissed",
                        "dismissed_by_role": dismissed_by_role,
                        "hod_justification": hod_justification,
                        "warning_id": warning_id,
                    },
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on warning dismissal (non-fatal): {le}")

            # Notify crew member their warning has been dismissed
            try:
                crew_uid = (warning or {}).get("user_id")
                if crew_uid and crew_uid != user_id:
                    self.db.table("pms_notifications").upsert({
                        "yacht_id": yacht_id,
                        "user_id": crew_uid,
                        "notification_type": "hor_warning_dismissed",
                        "title": "HoR Warning Dismissed",
                        "body": (
                            f"Your compliance warning has been reviewed and dismissed "
                            f"by {dismissed_by_role}: {hod_justification}"
                        ),
                        "entity_type": "crew_warning",
                        "entity_id": warning_id,
                        "idempotency_key": f"hor_dismiss:{warning_id}:{crew_uid}",
                        "triggered_by": user_id,
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }, on_conflict="idempotency_key").execute()
            except Exception as notif_err:
                logger.warning(f"Failed to notify crew of warning dismissal (non-fatal): {notif_err}")

            builder.set_data({
                "warning": warning,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error dismissing warning: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MLC 2006 PHASE 1 — Undo, Corrections, Notifications
    # =========================================================================

    async def undo_hours_of_rest(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/undo

        Crew undoes their own submitted day record.

        MLC requirement: original is NEVER deleted. Undo creates a
        pms_hor_corrections row with the original snapshot, then resets the
        pms_hours_of_rest row to unsubmitted state.

        Blocked if HOD has already signed the week containing this record.

        Payload:
        - record_id: UUID of pms_hours_of_rest row (required)
        """
        builder = ResponseBuilder("undo_hours_of_rest", entity_id, "hours_of_rest", yacht_id)

        try:
            record_id = payload.get("record_id")
            if not record_id:
                builder.set_error("VALIDATION_ERROR", "record_id is required")
                return builder.build()

            # Fetch the record to undo
            result = self.db.table("pms_hours_of_rest").select("*").eq(
                "id", record_id
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).limit(1).execute()

            if not result.data:
                builder.set_error("NOT_FOUND", "Record not found or not owned by you")
                return builder.build()

            record = result.data[0]
            record_date = record.get("record_date")

            # Block undo if HOD has signed the week containing this record
            # Determine the Monday of the week containing record_date
            from datetime import date as date_type
            rd = date_type.fromisoformat(str(record_date))
            week_monday = (rd - timedelta(days=rd.weekday())).isoformat()
            week_sunday = (rd - timedelta(days=rd.weekday()) + timedelta(days=6)).isoformat()

            hod_sign_check = self.db.table("pms_hor_monthly_signoffs").select("id, status").eq(
                "yacht_id", yacht_id
            ).eq("user_id", user_id).eq("period_type", "weekly").eq(
                "week_start", week_monday
            ).limit(1).execute()

            if hod_sign_check.data and hod_sign_check.data[0].get("status") in ("hod_signed", "finalized"):
                builder.set_error(
                    "LOCKED",
                    "Cannot undo: HOD has already signed this week. Request a correction through your HOD."
                )
                return builder.build()

            # Snapshot original data into pms_hor_corrections
            correction_insert = {
                "yacht_id": yacht_id,
                "original_record_id": record_id,
                "corrected_record_id": None,  # undo = no replacement record
                "corrected_by": user_id,
                "reason": "crew_undo",
                "note": None,
                "original_rest_periods": record.get("rest_periods", []),
                "corrected_rest_periods": None,
                "requested_by_user_id": None,
                "correction_chain": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.table("pms_hor_corrections").insert(correction_insert).execute()

            # Reset the HoR record to unsubmitted state
            reset_data = {
                "work_periods": [],
                "rest_periods": [],
                "total_rest_hours": 0,
                "total_work_hours": 0,
                "is_daily_compliant": False,
                "is_correction": False,
                "daily_compliance_notes": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.table("pms_hours_of_rest").update(reset_data).eq("id", record_id).execute()

            # Ledger event
            try:
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="update",
                    entity_type="hours_of_rest",
                    entity_id=record_id,
                    action="crew_undo",
                    change_summary=f"Crew undid HoR submission for {record_date} — original preserved in pms_hor_corrections",
                    metadata={"record_date": record_date, "original_total_rest_hours": record.get("total_rest_hours")},
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on undo (non-fatal): {le}")

            # Write audit log (ledger_events above; audit_log for immutable trail)
            _write_hor_audit_log(self.db, {
                "yacht_id": yacht_id,
                "entity_type": "hours_of_rest",
                "entity_id": record_id,
                "action": "undo_hours_of_rest",
                "user_id": user_id,
                "old_values": {
                    "record_date": record_date,
                    "total_rest_hours": record.get("total_rest_hours"),
                    "work_periods": record.get("work_periods"),
                },
                "new_values": {"work_periods": [], "rest_periods": [], "total_rest_hours": 0},
                "signature": {},
            })

            # Notify HOD that crew has undone their submission (weekly tally changed)
            try:
                undo_dept_r = self.db.table("auth_users_roles").select("department").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", user_id).limit(1).execute()
                undo_dept = (undo_dept_r.data[0] if undo_dept_r.data else {}).get("department")

                undo_name_r = self.db.table("auth_users_profiles").select("name").eq(
                    "yacht_id", yacht_id
                ).eq("id", user_id).limit(1).execute()
                undo_crew_name = (undo_name_r.data[0] if undo_name_r.data else {}).get("name") or "Crew member"

                hod_q = self.db.table("auth_users_roles").select("user_id").eq(
                    "yacht_id", yacht_id
                ).in_("role", ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"])
                if undo_dept:
                    hod_q = hod_q.eq("department", undo_dept)
                hod_r = hod_q.execute()

                seen_undo: set = set()
                undo_notifs = []
                for row in (hod_r.data or []):
                    hid = row["user_id"]
                    if hid in seen_undo or hid == user_id:
                        continue
                    seen_undo.add(hid)
                    undo_notifs.append({
                        "yacht_id": yacht_id,
                        "user_id": hid,
                        "notification_type": "hor_record_undone",
                        "title": f"HoR Record Undone — {undo_crew_name}",
                        "body": f"{undo_crew_name} has undone their hours of rest submission for {record_date}.",
                        "entity_type": "hours_of_rest",
                        "entity_id": record_id,
                        "idempotency_key": f"hor_undo:{record_id}:{hid}",
                        "triggered_by": user_id,
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                if undo_notifs:
                    self.db.table("pms_notifications").upsert(
                        undo_notifs, on_conflict="yacht_id,user_id,idempotency_key"
                    ).execute()
            except Exception as notif_err:
                logger.warning(f"Failed to notify HOD of HoR undo (non-fatal): {notif_err}")

            builder.set_data({
                "record_id": record_id,
                "record_date": record_date,
                "undone": True,
                "original_preserved": True,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error undoing hours of rest: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def create_hor_correction(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/corrections

        Create a correction for an existing HoR record.

        Crew: corrects their own time (full rest_periods replacement, reason required).
        HOD/Captain: adds a note only (corrected_rest_periods=None, cannot edit crew time).

        MLC requirement: original row is NEVER modified. A new pms_hours_of_rest
        row is created (is_correction=TRUE) and pms_hor_corrections links both.

        Payload:
        - original_record_id: UUID (required)
        - reason: str (required — legal field)
        - note: str (optional)
        - corrected_rest_periods: Array of {start, end} (required for crew, null for HOD note-only)
        - requested_by_user_id: UUID (optional — set when correction was kicked back by HOD/Captain)
        - correction_chain: list of {user_id, role, requested_at} (optional)
        """
        builder = ResponseBuilder("create_hor_correction", entity_id, "hours_of_rest", yacht_id)

        try:
            original_record_id = payload.get("original_record_id")
            reason = payload.get("reason", "").strip()
            note = payload.get("note")
            corrected_rest_periods = payload.get("corrected_rest_periods")
            requested_by_user_id = payload.get("requested_by_user_id")
            correction_chain = payload.get("correction_chain", [])

            if not original_record_id:
                builder.set_error("VALIDATION_ERROR", "original_record_id is required")
                return builder.build()
            if not reason:
                builder.set_error("VALIDATION_ERROR", "reason is required (MLC legal field)")
                return builder.build()

            # Fetch original record
            orig_result = self.db.table("pms_hours_of_rest").select("*").eq(
                "id", original_record_id
            ).eq("yacht_id", yacht_id).limit(1).execute()

            if not orig_result.data:
                builder.set_error("NOT_FOUND", "Original record not found")
                return builder.build()

            original = orig_result.data[0]
            original_owner_id = original.get("user_id")
            record_date = original.get("record_date")

            corrected_record_id = None
            corrected_record = None

            # If corrected_rest_periods provided — create new HoR row (crew correction only)
            if corrected_rest_periods is not None:
                # Only the record owner (crew) may change rest_periods
                if user_id != original_owner_id:
                    builder.set_error(
                        "FORBIDDEN",
                        "Only the crew member who submitted this record can change rest periods. "
                        "HOD/Captain may add a note only."
                    )
                    return builder.build()

                # Compute new totals (handle overnight periods crossing midnight)
                def _period_hours(p: dict) -> float:
                    if "hours" in p:
                        return float(p["hours"])
                    try:
                        sh, sm = map(int, str(p["start"]).split(":"))
                        eh, em = map(int, str(p["end"]).split(":"))
                        start_mins = sh * 60 + sm
                        end_mins   = eh * 60 + em
                        if end_mins <= start_mins:
                            end_mins += 24 * 60
                        return round((end_mins - start_mins) / 60, 2)
                    except Exception:
                        return 0.0

                # Inject hours into corrected periods for DB trigger
                corrected_rest_periods = [
                    dict(p, hours=_period_hours(p)) for p in corrected_rest_periods
                ]
                total_rest_hours = sum(p["hours"] for p in corrected_rest_periods)
                total_work_hours = 24 - total_rest_hours
                is_daily_compliant = total_rest_hours >= 10
                longest = max((_period_hours(p) for p in corrected_rest_periods), default=0.0)
                has_valid_periods = len(corrected_rest_periods) <= 2 and longest >= 6

                # Insert corrected HoR row
                new_row = {
                    "yacht_id": yacht_id,
                    "user_id": original_owner_id,
                    "record_date": record_date,
                    "rest_periods": corrected_rest_periods,
                    "total_rest_hours": total_rest_hours,
                    "total_work_hours": total_work_hours,
                    "is_daily_compliant": is_daily_compliant and has_valid_periods,
                    "is_correction": True,
                    "correction_of_id": original_record_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                self.db.table("pms_hours_of_rest").insert(new_row).execute()

                fetch = self.db.table("pms_hours_of_rest").select("*").eq(
                    "yacht_id", yacht_id
                ).eq("user_id", original_owner_id).eq("record_date", record_date).eq(
                    "is_correction", True
                ).order("created_at", desc=True).limit(1).execute()
                corrected_record = fetch.data[0] if fetch.data else None
                corrected_record_id = corrected_record.get("id") if corrected_record else None

                # Clear correction_requested on the weekly signoff (crew has addressed it)
                from datetime import date as date_type
                rd = date_type.fromisoformat(str(record_date))
                week_monday = (rd - timedelta(days=rd.weekday())).isoformat()
                self.db.table("pms_hor_monthly_signoffs").update({
                    "correction_requested": False,
                    "correction_requested_at": None,
                    "correction_note": None,
                    "correction_requested_by": None,
                    # Revert HOD sign status to draft so HOD must re-sign
                    "status": "draft",
                    "hod_signature": None,
                    "hod_signed_at": None,
                    "hod_signed_by": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("yacht_id", yacht_id).eq("user_id", original_owner_id).eq(
                    "period_type", "weekly"
                ).eq("week_start", week_monday).execute()

            # Insert into pms_hor_corrections
            correction_row = {
                "yacht_id": yacht_id,
                "original_record_id": original_record_id,
                "corrected_record_id": corrected_record_id,
                "corrected_by": user_id,
                "reason": reason,
                "note": note,
                "original_rest_periods": original.get("rest_periods", []),
                "corrected_rest_periods": corrected_rest_periods,
                "requested_by_user_id": requested_by_user_id,
                "correction_chain": correction_chain,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.table("pms_hor_corrections").insert(correction_row).execute()

            # Ledger event
            try:
                change_desc = (
                    f"Correction by {user_id} for {record_date}: {reason}"
                    if corrected_rest_periods else
                    f"Note added by {user_id} for {record_date}: {reason}"
                )
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="update",
                    entity_type="hours_of_rest",
                    entity_id=original_record_id,
                    action="create_hor_correction",
                    change_summary=change_desc,
                    metadata={
                        "original_record_id": original_record_id,
                        "corrected_record_id": corrected_record_id,
                        "reason": reason,
                        "is_time_change": corrected_rest_periods is not None,
                    },
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on correction (non-fatal): {le}")

            # Write audit log (ledger_events above; audit_log for immutable trail)
            _write_hor_audit_log(self.db, {
                "yacht_id": yacht_id,
                "entity_type": "hours_of_rest",
                "entity_id": original_record_id,
                "action": "create_hor_correction",
                "user_id": user_id,
                "old_values": {
                    "rest_periods": original.get("rest_periods", []),
                    "total_rest_hours": original.get("total_rest_hours"),
                },
                "new_values": {
                    "corrected_record_id": corrected_record_id,
                    "reason": reason,
                    "is_time_change": corrected_rest_periods is not None,
                },
                "signature": {},
            })

            # Notify original record owner when HOD/Captain adds a note to their record
            # (note-only = corrected_rest_periods is None and corrector is not the owner)
            try:
                if original_owner_id and original_owner_id != user_id and corrected_rest_periods is None:
                    corrector_name_r = self.db.table("auth_users_profiles").select("name").eq(
                        "yacht_id", yacht_id
                    ).eq("id", user_id).limit(1).execute()
                    corrector_name = (corrector_name_r.data[0] if corrector_name_r.data else {}).get("name") or "HOD"
                    self.db.table("pms_notifications").upsert({
                        "yacht_id": yacht_id,
                        "user_id": original_owner_id,
                        "notification_type": "hor_correction_note_added",
                        "title": "Note Added to Your HoR Record",
                        "body": (
                            f"{corrector_name} has added a note to your hours of rest "
                            f"for {record_date}: {reason}"
                        ),
                        "entity_type": "hours_of_rest",
                        "entity_id": original_record_id,
                        "idempotency_key": f"hor_note:{original_record_id}:{user_id}",
                        "triggered_by": user_id,
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }, on_conflict="idempotency_key").execute()
            except Exception as notif_err:
                logger.warning(f"Failed to notify crew of correction note (non-fatal): {notif_err}")

            builder.set_data({
                "original_record_id": original_record_id,
                "corrected_record_id": corrected_record_id,
                "corrected_record": corrected_record,
                "is_time_change": corrected_rest_periods is not None,
                "reason": reason,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error creating HoR correction: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def request_hor_correction(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/request-correction

        HOD or Captain kicks back a signed week/signoff record, requesting
        correction from the next party down the chain.

        HOD → Crew: sets correction_requested=TRUE on weekly signoff + notifies crew.
        Captain → HOD: sets correction_requested=TRUE on captain-signed signoff + notifies HOD.

        Payload:
        - signoff_id: UUID of pms_hor_monthly_signoffs (required)
        - target_user_id: UUID of who should receive the correction request (required)
        - correction_note: str (required — what needs correcting)
        - role: 'hod' | 'captain' (role of the requester, required)
        """
        builder = ResponseBuilder("request_hor_correction", entity_id, "monthly_signoff", yacht_id)

        try:
            signoff_id = payload.get("signoff_id")
            target_user_id = payload.get("target_user_id")
            correction_note = payload.get("correction_note", "").strip()
            requester_role = payload.get("role")

            if not signoff_id or not target_user_id or not correction_note:
                builder.set_error(
                    "VALIDATION_ERROR",
                    "signoff_id, target_user_id, and correction_note are required"
                )
                return builder.build()

            # Fetch signoff
            signoff_result = self.db.table("pms_hor_monthly_signoffs").select("*").eq(
                "id", signoff_id
            ).eq("yacht_id", yacht_id).limit(1).execute()

            if not signoff_result.data:
                builder.set_error("NOT_FOUND", "Sign-off not found")
                return builder.build()

            signoff = signoff_result.data[0]
            current_status = signoff.get("status")

            # Auth: HOD can only request correction on hod_signed records
            #       Captain can only request on captain_signed / hod_signed records
            allowed_statuses = {
                "hod": ["hod_signed"],
                "captain": ["hod_signed", "finalized"],
            }
            if requester_role not in allowed_statuses:
                builder.set_error("VALIDATION_ERROR", f"Invalid role: {requester_role}")
                return builder.build()

            if current_status not in allowed_statuses[requester_role]:
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot request correction from {current_status} state as {requester_role}"
                )
                return builder.build()

            # Set correction_requested on signoff
            self.db.table("pms_hor_monthly_signoffs").update({
                "correction_requested": True,
                "correction_requested_at": datetime.now(timezone.utc).isoformat(),
                "correction_note": correction_note,
                "correction_requested_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", signoff_id).execute()

            # Notify the target user
            notification_type = "correction_notice"
            role_label = "HOD" if requester_role == "hod" else "Captain"

            self.db.table("pms_notifications").upsert({
                "yacht_id": yacht_id,
                "user_id": target_user_id,
                "title": "HoR Correction Requested",
                "notification_type": notification_type,
                "entity_type": "hours_of_rest",
                "entity_id": signoff_id,
                "body": f"{role_label} has requested a correction: {correction_note}",
                "metadata": {
                    "signoff_id": signoff_id,
                    "requested_by": user_id,
                    "requester_role": requester_role,
                    "correction_note": correction_note,
                    "signoff_period_type": signoff.get("period_type", "monthly"),
                    "week_start": signoff.get("week_start"),
                    "month": signoff.get("month"),
                },
                "idempotency_key": f"correction_notice:{signoff_id}:{target_user_id}",
                "triggered_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="idempotency_key").execute()

            # Ledger event
            try:
                self.db.table("ledger_events").insert(build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id,
                    event_type="update",
                    entity_type="pms_hor_monthly_signoffs",
                    entity_id=signoff_id,
                    action="request_hor_correction",
                    change_summary=f"{role_label} requested correction from user {target_user_id}: {correction_note}",
                    metadata={
                        "signoff_id": signoff_id,
                        "target_user_id": target_user_id,
                        "requester_role": requester_role,
                        "correction_note": correction_note,
                    },
                    event_category="write",
                )).execute()
            except Exception as le:
                logger.warning(f"Ledger insert failed on correction request (non-fatal): {le}")

            builder.set_data({
                "signoff_id": signoff_id,
                "correction_requested": True,
                "target_user_id": target_user_id,
                "notification_sent": True,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error requesting HoR correction: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def get_unread_notifications(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/notifications/unread

        Returns unread notifications for the current user on this vessel.
        Frontend polls this on page load and after any action.

        Params:
        - limit: int (default 50)
        """
        builder = ResponseBuilder("get_unread_notifications", entity_id, "notification", yacht_id)

        try:
            params = params or {}
            limit = int(params.get("limit", 50))

            result = self.db.table("pms_notifications").select("*").eq(
                "yacht_id", yacht_id
            ).eq("user_id", user_id).eq(
                "is_read", False
            ).order("created_at", desc=True).limit(limit).execute()

            notifications = result.data or []

            builder.set_data({
                "notifications": notifications,
                "unread_count": len(notifications),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def mark_notifications_read(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        POST /v1/hours-of-rest/notifications/mark-read

        Mark one or all unread notifications as read.

        Payload:
        - notification_ids: list of UUIDs (optional — if omitted, marks ALL as read)
        """
        builder = ResponseBuilder("mark_notifications_read", entity_id, "notification", yacht_id)

        try:
            notification_ids = payload.get("notification_ids")
            now = datetime.now(timezone.utc).isoformat()

            query = self.db.table("pms_notifications").update({
                "is_read": True,
                "read_at": now,
            }).eq("yacht_id", yacht_id).eq("user_id", user_id)

            if notification_ids:
                query = query.in_("id", notification_ids)

            query.execute()

            builder.set_data({"marked_read": True})
            return builder.build()

        except Exception as e:
            logger.error(f"Error marking notifications read: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()

    async def get_hor_sign_chain(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        GET /v1/hours-of-rest/sign-chain

        Returns per-vessel or per-week sign chain status for fleet manager view (S6).

        Params:
        - week_start: YYYY-MM-DD (Monday of week, required)
        - target_yacht_id: UUID (optional — for fleet manager viewing another vessel)

        Returns for the week:
        - crew_submitted: count
        - hod_signed: bool per department
        - captain_signed: bool
        - fleet_manager_reviewed: bool
        - correction_requests: list of outstanding correction_requested=TRUE records
        """
        builder = ResponseBuilder("get_hor_sign_chain", entity_id, "sign_chain", yacht_id)

        try:
            params = params or {}
            week_start = params.get("week_start")
            if not week_start:
                builder.set_error("VALIDATION_ERROR", "week_start is required (YYYY-MM-DD Monday)")
                return builder.build()

            target_yacht = params.get("target_yacht_id") or yacht_id

            # All weekly signoffs for this vessel + week
            signoffs_result = self.db.table("pms_hor_monthly_signoffs").select(
                "id, user_id, department, status, period_type, week_start, "
                "hod_signed_by, hod_signed_at, master_signed_by, master_signed_at, "
                "fleet_manager_signed_by, fleet_manager_signed_at, "
                "correction_requested, correction_note, correction_requested_by"
            ).eq("yacht_id", target_yacht).eq("period_type", "weekly").eq(
                "week_start", week_start
            ).execute()

            signoffs = signoffs_result.data or []

            # Count crew submissions for this week
            from datetime import date as date_type
            ws = date_type.fromisoformat(str(week_start))
            week_end = (ws + timedelta(days=6)).isoformat()

            submitted_result = self.db.table("pms_hours_of_rest").select(
                "user_id", count="exact"
            ).eq("yacht_id", target_yacht).gte(
                "record_date", week_start
            ).lte("record_date", week_end).execute()

            crew_submitted_count = submitted_result.count or 0

            # Build department sign status
            dept_status = {}
            captain_signed = False
            fleet_reviewed = False
            outstanding_corrections = []

            for s in signoffs:
                dept = s.get("department", "unknown")
                status = s.get("status", "draft")

                if dept not in dept_status:
                    dept_status[dept] = {
                        "status": status,
                        "hod_signed_at": s.get("hod_signed_at"),
                        "hod_signed_by": s.get("hod_signed_by"),
                        "correction_requested": s.get("correction_requested", False),
                        "correction_note": s.get("correction_note"),
                    }

                if status in ("finalized",) and s.get("master_signed_by"):
                    captain_signed = True

                if s.get("fleet_manager_signed_by"):
                    fleet_reviewed = True

                if s.get("correction_requested"):
                    outstanding_corrections.append({
                        "signoff_id": s.get("id"),
                        "department": dept,
                        "user_id": s.get("user_id"),
                        "correction_note": s.get("correction_note"),
                        "requested_by": s.get("correction_requested_by"),
                    })

            all_hods_signed = all(
                d.get("status") in ("hod_signed", "finalized") and not d.get("correction_requested")
                for d in dept_status.values()
            ) if dept_status else False

            builder.set_data({
                "week_start": week_start,
                "yacht_id": target_yacht,
                "crew_submitted_count": crew_submitted_count,
                "department_status": dept_status,
                "all_hods_signed": all_hods_signed,
                "captain_signed": captain_signed,
                "fleet_manager_reviewed": fleet_reviewed,
                "outstanding_corrections": outstanding_corrections,
                "ready_for_captain": all_hods_signed and not captain_signed,
                "ready_for_fleet_manager": all_hods_signed and captain_signed and not fleet_reviewed,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"Error fetching HoR sign chain: {e}")
            builder.set_error("DATABASE_ERROR", str(e))
            return builder.build()
