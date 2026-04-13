"""
HoR Compliance Endpoints — Enriched Views
==========================================

Three role-gated read endpoints that power the redesigned Hours of Rest UI.
Registered on the same /v1/hours-of-rest prefix as the main router.

GET /v1/hours-of-rest/my-week         — crew: own week view (all roles)
GET /v1/hours-of-rest/department-status — HOD: department grid
GET /v1/hours-of-rest/vessel-compliance — Captain: vessel overview

All responses are enriched beyond the basic dash_crew_hours_compliance data.
Each endpoint hits multiple tables and returns a single composed response.
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/hours-of-rest", tags=["hor-compliance"])

# ---------------------------------------------------------------------------
# Role sets
# ---------------------------------------------------------------------------
_HOD_ROLES = {
    "chief_engineer", "chief_officer", "chief_steward",
    "eto", "purser", "captain", "manager",
}
_CAPTAIN_ROLES = {"captain", "manager"}


def _parse_week_start(week_start_str: Optional[str]) -> date:
    if week_start_str:
        try:
            return date.fromisoformat(week_start_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"error": "INVALID_DATE", "message": "week_start must be YYYY-MM-DD"}
            )
    today = date.today()
    return today - timedelta(days=today.weekday())  # Monday


# ===========================================================================
# GET /v1/hours-of-rest/my-week
# ===========================================================================

@router.get("/my-week")
async def get_my_week(
    week_start: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Crew view: own daily HoR records + enriched compliance for a given week.

    Returns:
    - days[7]: one slot per day (null if not submitted). Each day includes
      a warnings[] array from pms_crew_hours_warnings.
    - compliance: weekly summary renamed from weekly_summary, with
      rolling_24h_rest and rolling_7day_rest computed from pms_hours_of_rest.
    - pending_signoff: current month's sign-off status from
      pms_hor_monthly_signoffs.
    - templates: user's available active templates from pms_crew_normal_hours.
    """
    user_id    = auth["user_id"]
    yacht_id   = auth["yacht_id"]
    department = auth.get("department", "general")
    tenant_key_alias = auth["tenant_key_alias"]

    week_monday = _parse_week_start(week_start)
    week_end    = week_monday + timedelta(days=6)
    today       = date.today()
    current_month = today.strftime("%Y-%m")

    supabase = get_tenant_client(tenant_key_alias)
    if not supabase:
        raise HTTPException(status_code=503, detail={"error": "DB_UNAVAILABLE"})

    try:
        # ------------------------------------------------------------------
        # 1. Daily records for the week
        # ------------------------------------------------------------------
        records_r = supabase.table("pms_hours_of_rest").select(
            "id, record_date, work_periods, rest_periods, total_rest_hours, total_work_hours, "
            "is_daily_compliant, is_weekly_compliant, daily_compliance_notes, "
            "location, voyage_type, updated_at"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).gte(
            "record_date", week_monday.isoformat()
        ).lte("record_date", week_end.isoformat()).order("record_date").execute()

        daily_by_date: Dict[str, dict] = {
            r["record_date"]: r for r in (records_r.data or [])
        }

        # ------------------------------------------------------------------
        # 2. Warnings for the week — keyed by record_date
        # ------------------------------------------------------------------
        warnings_r = supabase.table("pms_crew_hours_warnings").select(
            "record_date, warning_type, severity, message, violation_data, status"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).gte(
            "record_date", week_monday.isoformat()
        ).lte("record_date", week_end.isoformat()).eq("status", "active").execute()

        warnings_by_date: Dict[str, list] = {}
        for w in (warnings_r.data or []):
            d = w["record_date"]
            warnings_by_date.setdefault(d, [])
            vd = w.get("violation_data") or {}
            warnings_by_date[d].append({
                "type":      w.get("warning_type"),
                "severity":  w.get("severity"),
                "shortfall": vd.get("shortfall"),
                "message":   w.get("message"),
            })

        # ------------------------------------------------------------------
        # 3. Build 7-slot days array — always 7 non-null objects
        # ------------------------------------------------------------------
        days: List[dict] = []
        for i in range(7):
            d = week_monday + timedelta(days=i)
            dstr = d.isoformat()
            rec = daily_by_date.get(dstr)
            if rec is None:
                days.append({
                    "record_date":          dstr,
                    "work_periods":         [],
                    "rest_periods":         [],
                    "total_rest_hours":     0,
                    "total_work_hours":     0,
                    "is_daily_compliant":   None,
                    "submitted":            False,
                    "warnings":             [],
                })
            else:
                rec = dict(rec)
                rec["submitted"] = True
                rec["warnings"] = warnings_by_date.get(dstr, [])
                days.append(rec)

        # ------------------------------------------------------------------
        # 4. Weekly compliance summary from dash_crew_hours_compliance
        # ------------------------------------------------------------------
        summary_r = supabase.table("dash_crew_hours_compliance").select(
            "id, total_work_hours, total_rest_hours, days_submitted, days_compliant, "
            "is_weekly_compliant, has_active_warnings, signoff_status, updated_at"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
            "week_start", week_monday.isoformat()
        ).maybe_single().execute()

        # Rolling 24h rest: today's record rest hours
        rolling_24h = None
        today_rec = daily_by_date.get(today.isoformat())
        if today_rec:
            rolling_24h = today_rec.get("total_rest_hours")

        # Rolling 7-day rest: last 7 calendar days ending today
        rolling_start = today - timedelta(days=6)
        rolling_r = supabase.table("pms_hours_of_rest").select(
            "total_rest_hours"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).gte(
            "record_date", rolling_start.isoformat()
        ).lte("record_date", today.isoformat()).execute()
        rolling_data = rolling_r.data or []
        rolling_7day = sum(
            (r.get("total_rest_hours") or 0) for r in rolling_data
        ) if rolling_data else None

        summary_data = summary_r.data if summary_r else None
        compliance = {
            **(summary_data if summary_data else {}),
            "rolling_24h_rest":  rolling_24h,
            "rolling_7day_rest": rolling_7day,
        }

        # ------------------------------------------------------------------
        # 5. Pending sign-off for current month + weekly signoff status
        # ------------------------------------------------------------------
        signoff_r = supabase.table("pms_hor_monthly_signoffs").select(
            "id, month, status"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
            "month", current_month
        ).maybe_single().execute()

        signoff_data = signoff_r.data if signoff_r else None
        if signoff_data:
            pending_signoff = {
                "month":      signoff_data["month"],
                "status":     signoff_data["status"],
                "signoff_id": signoff_data["id"],
            }
        else:
            pending_signoff = {
                "month":      current_month,
                "status":     "not_started",
                "signoff_id": None,
            }

        # Weekly signoff status for the selected week (Phase 7 lock signal)
        weekly_signoff_r = supabase.table("pms_hor_monthly_signoffs").select(
            "id, status, correction_requested, correction_note"
        ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq(
            "period_type", "weekly"
        ).eq("week_start", week_monday.isoformat()).maybe_single().execute()

        weekly_signoff_data = weekly_signoff_r.data if weekly_signoff_r else None
        signoff_status = weekly_signoff_data.get("status") if weekly_signoff_data else None

        # ------------------------------------------------------------------
        # 6. Templates
        # ------------------------------------------------------------------
        tmpl_r = supabase.table("pms_crew_normal_hours").select(
            "id, schedule_name, applies_to, is_active"
        ).eq("yacht_id", yacht_id).eq("is_active", True).execute()
        # Include user's own + yacht-wide (user_id IS NULL handled server-side via RLS)
        templates = [
            {
                "id":         t["id"],
                "name":       t["schedule_name"],
                "applies_to": t.get("applies_to"),
                "is_default": False,  # column not in schema
            }
            for t in (tmpl_r.data or [])
        ]

        return JSONResponse(content={
            "status":         "success",
            "week_start":     week_monday.isoformat(),
            "week_end":       week_end.isoformat(),
            "user_id":        user_id,
            "department":     department,
            "days":           days,
            "compliance":     compliance,
            "pending_signoff": pending_signoff,
            "templates":      templates,
            # Phase 7: weekly sign-off status for lock signal
            # null = no weekly signoff exists yet (editable)
            # "finalized" or "locked" = read-only, TimeSlider hidden
            "signoff_status": signoff_status,
            "correction_requested": weekly_signoff_data.get("correction_requested", False) if weekly_signoff_data else False,
            "correction_note": weekly_signoff_data.get("correction_note") if weekly_signoff_data else None,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_my_week error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


# ===========================================================================
# GET /v1/hours-of-rest/department-status
# ===========================================================================

@router.get("/department-status")
async def get_department_status(
    week_start: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    HOD view: all crew in department — weekly compliance grid.

    Returns:
    - crew[]: one entry per crew member, each with:
      - name (from auth_users_profiles)
      - daily[]: 7 slots {date, work_hours, rest_hours, submitted}
      - weekly summary fields from dash_crew_hours_compliance
    - pending_signoffs: {month, awaiting_hod, signoff_ids[]}
    - compliance.missing_today: names of crew with no record for today
    """
    user_role  = auth.get("role", "crew")
    department = auth.get("department", "")
    yacht_id   = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    if user_role.lower() not in _HOD_ROLES:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": f"Role '{user_role}' cannot access department status. HOD+ required."}
        )

    week_monday  = _parse_week_start(week_start)
    week_end     = week_monday + timedelta(days=6)
    today        = date.today()
    current_month = today.strftime("%Y-%m")

    supabase = get_tenant_client(tenant_key_alias)
    if not supabase:
        raise HTTPException(status_code=503, detail={"error": "DB_UNAVAILABLE"})

    try:
        # ------------------------------------------------------------------
        # 1. All crew in department from auth_users_roles
        # ------------------------------------------------------------------
        roles_q = supabase.table("auth_users_roles").select(
            "user_id"
        ).eq("yacht_id", yacht_id)

        if user_role.lower() not in _CAPTAIN_ROLES and department:
            roles_q = roles_q.eq("department", department)

        roles_r = roles_q.execute()
        crew_user_ids = list({r["user_id"] for r in (roles_r.data or [])})

        if not crew_user_ids:
            return JSONResponse(content={
                "status": "success",
                "week_start": week_monday.isoformat(),
                "department": department,
                "total_crew": 0,
                "submitted_count": 0,
                "compliant_count": 0,
                "crew": [],
                "pending_signoffs": {"month": current_month, "awaiting_hod": 0, "signoff_ids": []},
                "compliance": {"missing_today": []},
            })

        # ------------------------------------------------------------------
        # 2. Names from auth_users_profiles
        # ------------------------------------------------------------------
        profiles_r = supabase.table("auth_users_profiles").select(
            "id, name"
        ).in_("id", crew_user_ids).execute()
        name_by_id = {p["id"]: p.get("name") or "Unknown" for p in (profiles_r.data or [])}

        # ------------------------------------------------------------------
        # 3. dash_crew_hours_compliance for the week — all crew
        # ------------------------------------------------------------------
        compliance_r = supabase.table("dash_crew_hours_compliance").select(
            "user_id, total_work_hours, total_rest_hours, days_submitted, "
            "days_compliant, is_weekly_compliant, has_active_warnings, signoff_status"
        ).eq("yacht_id", yacht_id).eq("week_start", week_monday.isoformat()).in_(
            "user_id", crew_user_ids
        ).execute()
        compliance_by_uid = {r["user_id"]: r for r in (compliance_r.data or [])}

        # ------------------------------------------------------------------
        # 4. Per-day HoR records for all crew for the week (single query)
        # ------------------------------------------------------------------
        hor_r = supabase.table("pms_hours_of_rest").select(
            "user_id, record_date, total_work_hours, total_rest_hours, is_daily_compliant"
        ).eq("yacht_id", yacht_id).in_(
            "user_id", crew_user_ids
        ).gte("record_date", week_monday.isoformat()).lte(
            "record_date", week_end.isoformat()
        ).execute()

        daily_by_uid: Dict[str, Dict[str, dict]] = {}
        for r in (hor_r.data or []):
            uid = r["user_id"]
            daily_by_uid.setdefault(uid, {})
            daily_by_uid[uid][r["record_date"]] = r

        # ------------------------------------------------------------------
        # 5. Build crew array
        # ------------------------------------------------------------------
        crew_rows = []
        submitted_count = 0
        compliant_count = 0
        missing_today_names = []

        today_str = today.isoformat()

        for uid in crew_user_ids:
            comp = compliance_by_uid.get(uid, {})
            uid_daily = daily_by_uid.get(uid, {})

            # 7-slot daily array
            daily_slots = []
            for i in range(7):
                d = week_monday + timedelta(days=i)
                dstr = d.isoformat()
                rec = uid_daily.get(dstr)
                daily_slots.append({
                    "date":       dstr,
                    "work_hours": rec.get("total_work_hours") if rec else None,
                    "rest_hours": rec.get("total_rest_hours") if rec else None,
                    "submitted":  rec is not None,
                    "compliant":  rec.get("is_daily_compliant") if rec else None,
                })

            days_sub = comp.get("days_submitted") or 0
            if days_sub > 0:
                submitted_count += 1
            if comp.get("is_weekly_compliant"):
                compliant_count += 1

            # Missing today
            if today_str not in uid_daily:
                missing_today_names.append(name_by_id.get(uid, uid[:8]))

            crew_rows.append({
                "user_id":        uid,
                "name":           name_by_id.get(uid, "Unknown"),
                "total_work_hours": comp.get("total_work_hours"),
                "total_rest_hours": comp.get("total_rest_hours"),
                "days_submitted": days_sub,
                "days_compliant": comp.get("days_compliant"),
                "is_weekly_compliant": comp.get("is_weekly_compliant", False),
                "has_active_warnings": comp.get("has_active_warnings", False),
                "signoff_status": comp.get("signoff_status", "draft"),
                "daily":          daily_slots,
            })

        # ------------------------------------------------------------------
        # 6. Pending signoffs awaiting HOD counter-sign
        # ------------------------------------------------------------------
        pending_q = supabase.table("pms_hor_monthly_signoffs").select(
            "id, user_id, month, status"
        ).eq("yacht_id", yacht_id).eq("month", current_month).eq("status", "crew_signed")

        if user_role.lower() not in _CAPTAIN_ROLES and department:
            pending_q = pending_q.eq("department", department)

        pending_r = pending_q.execute()
        pending_rows = pending_r.data or []
        pending_signoffs = {
            "month":        current_month,
            "awaiting_hod": len(pending_rows),
            "signoff_ids":  [r["id"] for r in pending_rows],
            "crew_user_ids": [r["user_id"] for r in pending_rows],
            # parallel arrays — index i: signoff_ids[i] belongs to crew_user_ids[i]
        }

        dept_label = department if user_role.lower() not in _CAPTAIN_ROLES else "all"
        return JSONResponse(content={
            "status":          "success",
            "week_start":      week_monday.isoformat(),
            "department":      dept_label,
            "total_crew":      len(crew_user_ids),
            "submitted_count": submitted_count,
            "compliant_count": compliant_count,
            "crew":            crew_rows,
            "pending_signoffs": pending_signoffs,
            "compliance":      {"missing_today": missing_today_names},
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_department_status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


# ===========================================================================
# GET /v1/hours-of-rest/vessel-compliance
# ===========================================================================

@router.get("/vessel-compliance")
async def get_vessel_compliance(
    week_start: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Captain view: vessel-wide compliance grouped by department.

    Returns:
    - departments[]: per-dept totals
    - all_crew[]: every crew member with weekly summary + name
    - analytics: avg_work_hours, compliance_rate, violations_this_quarter
    """
    user_role = auth.get("role", "crew")
    yacht_id  = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    if user_role.lower() not in _CAPTAIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail={"error": "FORBIDDEN", "message": f"Role '{user_role}' cannot access vessel compliance. Captain+ required."}
        )

    week_monday = _parse_week_start(week_start)
    today       = date.today()

    # Quarter boundaries
    quarter_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_month, 1).isoformat()

    supabase = get_tenant_client(tenant_key_alias)
    if not supabase:
        raise HTTPException(status_code=503, detail={"error": "DB_UNAVAILABLE"})

    try:
        # ------------------------------------------------------------------
        # 1. All dash_crew_hours_compliance rows for the week
        # ------------------------------------------------------------------
        rows_r = supabase.table("dash_crew_hours_compliance").select(
            "user_id, department, days_submitted, days_compliant, "
            "total_work_hours, total_rest_hours, is_weekly_compliant, "
            "has_active_warnings, signoff_status"
        ).eq("yacht_id", yacht_id).eq("week_start", week_monday.isoformat()).execute()
        rows = rows_r.data or []

        # ------------------------------------------------------------------
        # 2. Names from auth_users_profiles
        # ------------------------------------------------------------------
        all_uids = list({r["user_id"] for r in rows})
        name_by_id: Dict[str, str] = {}
        if all_uids:
            prof_r = supabase.table("auth_users_profiles").select(
                "id, name"
            ).in_("id", all_uids).execute()
            name_by_id = {p["id"]: p.get("name") or "Unknown" for p in (prof_r.data or [])}

        # ------------------------------------------------------------------
        # 3. Violations — this quarter (legacy) and this week (scoped)
        # ------------------------------------------------------------------
        viol_r = supabase.table("pms_crew_hours_warnings").select(
            "id"
        ).eq("yacht_id", yacht_id).gte("record_date", quarter_start).execute()
        violations_this_quarter = len(viol_r.data or [])

        week_end = week_monday + timedelta(days=6)
        viol_week_r = supabase.table("pms_crew_hours_warnings").select(
            "id"
        ).eq("yacht_id", yacht_id).gte(
            "record_date", week_monday.isoformat()
        ).lte("record_date", week_end.isoformat()).execute()
        violations_this_week = len(viol_week_r.data or [])

        # ------------------------------------------------------------------
        # 4. Build department groups
        # ------------------------------------------------------------------
        dept_map: Dict[str, dict] = {}
        for r in rows:
            dept = r.get("department") or "unassigned"
            if dept not in dept_map:
                dept_map[dept] = {
                    "department":         dept,
                    "total_crew":         0,
                    "submitted_count":    0,
                    "compliant_count":    0,
                    "pending_warnings":   0,
                    "pending_signoff_count": 0,
                }
            g = dept_map[dept]
            g["total_crew"] += 1
            if (r.get("days_submitted") or 0) > 0:
                g["submitted_count"] += 1
            if r.get("is_weekly_compliant"):
                g["compliant_count"] += 1
            if r.get("has_active_warnings"):
                g["pending_warnings"] += 1
            if r.get("signoff_status") in ("draft", "crew_signed"):
                g["pending_signoff_count"] += 1

        # ------------------------------------------------------------------
        # 5. all_crew array
        # ------------------------------------------------------------------
        all_crew = [
            {
                "user_id":          r["user_id"],
                "name":             name_by_id.get(r["user_id"], "Unknown"),
                "department":       r.get("department"),
                "total_work_hours": r.get("total_work_hours"),
                "total_rest_hours": r.get("total_rest_hours"),
                "days_submitted":   r.get("days_submitted"),
                "is_weekly_compliant": r.get("is_weekly_compliant", False),
                "has_active_warnings": r.get("has_active_warnings", False),
                "signoff_status":   r.get("signoff_status", "draft"),
            }
            for r in rows
        ]

        # ------------------------------------------------------------------
        # 6. Analytics
        # ------------------------------------------------------------------
        total_crew      = len(rows)
        total_compliant = sum(1 for r in rows if r.get("is_weekly_compliant"))
        total_work_hrs  = [r.get("total_work_hours") for r in rows if r.get("total_work_hours") is not None]
        # avg_work_hours = average crew member's TOTAL weekly work hours
        avg_work_hours_per_week = round(sum(total_work_hrs) / len(total_work_hrs), 2) if total_work_hrs else None
        avg_work_hours_per_day  = round(avg_work_hours_per_week / 7, 2) if avg_work_hours_per_week is not None else None
        # compliance_pct: 0–100 (not 0–1). 100 = all crew submitted with no violations.
        # A missed submission day OR a violation day = non-compliance.
        total_submitted_days = sum((r.get("days_submitted") or 0) for r in rows)
        total_expected_days  = total_crew * 7
        total_violation_days = sum(
            7 - (r.get("days_compliant") or 0) for r in rows
            if (r.get("days_submitted") or 0) > 0
        )
        non_compliant_days = (total_expected_days - total_submitted_days) + total_violation_days
        compliance_pct = round(
            max(0, (total_expected_days - non_compliant_days) / total_expected_days * 100), 1
        ) if total_expected_days else None

        # ------------------------------------------------------------------
        # 7. Sign chain — per-dept HOD sign status + captain/FM sign for this week
        # ------------------------------------------------------------------
        sign_chain_r = supabase.table("pms_hor_monthly_signoffs").select(
            "id, user_id, department, status, period_type, week_start, "
            "hod_signed_by, hod_signed_at, master_signed_by, master_signed_at, "
            "fleet_manager_signed_by, fleet_manager_signed_at, "
            "correction_requested, correction_note"
        ).eq("yacht_id", yacht_id).eq("period_type", "weekly").eq(
            "week_start", week_monday.isoformat()
        ).execute()

        sign_rows = sign_chain_r.data or []

        # dept → sign status
        dept_sign: Dict[str, dict] = {}
        captain_signed = False
        fleet_reviewed = False
        for s in sign_rows:
            dept = s.get("department", "unassigned")
            status = s.get("status", "draft")
            dept_sign[dept] = {
                "signoff_id":         s.get("id"),
                "status":             status,
                "hod_signed_at":      s.get("hod_signed_at"),
                "correction_requested": s.get("correction_requested", False),
                "correction_note":    s.get("correction_note"),
            }
            if s.get("master_signed_by"):
                captain_signed = True
            if s.get("fleet_manager_signed_by"):
                fleet_reviewed = True

        # Merge sign status into dept_map
        departments_out = []
        for dept, g in dept_map.items():
            sign_info = dept_sign.get(dept, {
                "signoff_id": None,
                "status": "draft",
                "hod_signed_at": None,
                "correction_requested": False,
                "correction_note": None,
            })
            departments_out.append({**g, **sign_info})

        all_hods_signed = all(
            d.get("status") in ("hod_signed", "finalized") and not d.get("correction_requested")
            for d in departments_out
        ) if departments_out else False

        return JSONResponse(content={
            "status":      "success",
            "week_start":  week_monday.isoformat(),
            "vessel_summary": {
                "total_crew":      total_crew,
                "submitted_count": sum(1 for r in rows if (r.get("days_submitted") or 0) > 0),
                "compliant_count": total_compliant,
            },
            "departments": departments_out,
            "all_crew":    all_crew,
            "analytics": {
                "avg_work_hours":           avg_work_hours_per_week,   # kept for backward compat
                "avg_work_hours_per_week":  avg_work_hours_per_week,
                "avg_work_hours_per_day":   avg_work_hours_per_day,
                "compliance_pct":           compliance_pct,            # 0–100, use this
                "compliance_rate":          compliance_pct,            # deprecated alias
                "violations_this_week":     violations_this_week,
                "violations_this_quarter":  violations_this_quarter,   # deprecated
            },
            "sign_chain": {
                "all_hods_signed":       all_hods_signed,
                "captain_signed":        captain_signed,
                "fleet_manager_reviewed": fleet_reviewed,
                "ready_for_captain":     all_hods_signed and not captain_signed,
                "ready_for_fleet_manager": all_hods_signed and captain_signed and not fleet_reviewed,
            },
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_vessel_compliance error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})
