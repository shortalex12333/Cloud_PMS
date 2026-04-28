"""
Entity Lens read-handlers — extracted from entity_routes.py (Phase C thinning).

Each method corresponds to a GET /v1/entity/{type}/{id} route.
The route layer (entity_routes.py) parses HTTP context and delegates here;
all DB queries and business logic live in this file.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from action_router.entity_actions import get_available_actions
from integrations.supabase import get_supabase_client
from lib.entity_helpers import _sign_url, _get_attachments, _nav, ATTACHMENT_BUCKET
from lib.user_resolver import resolve_users, resolve_yacht_name, resolve_equipment_batch

logger = logging.getLogger(__name__)


class EntityLensHandlers:
    def __init__(self, supabase):
        self.db = supabase

    # ── Certificate ────────────────────────────────────────────────────────────

    async def get_certificate_entity(self, certificate_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        domain = None
        data = None

        vessel_r = supabase.table("pms_vessel_certificates").select("*") \
            .eq("id", certificate_id).eq("yacht_id", yacht_id).limit(1).execute()
        vessel_rows = getattr(vessel_r, "data", None) or []
        if vessel_rows:
            domain = "vessel"
            data = vessel_rows[0]
        else:
            crew_r = supabase.table("pms_crew_certificates").select("*") \
                .eq("id", certificate_id).eq("yacht_id", yacht_id).limit(1).execute()
            crew_rows = getattr(crew_r, "data", None) or []
            if crew_rows:
                domain = "crew"
                data = crew_rows[0]

        if not data:
            raise HTTPException(status_code=404, detail="Certificate not found")

        properties = data.get("properties") or {}
        if isinstance(properties, str):
            try:
                properties = json.loads(properties) if properties else {}
            except Exception:
                properties = {}

        attachments = _get_attachments(supabase, "certificate", certificate_id, yacht_id)
        doc_id = data.get("document_id")
        if doc_id:
            try:
                doc_r = supabase.table("doc_metadata").select(
                    "id, filename, mime_type, file_size, storage_path, storage_bucket"
                ).eq("id", doc_id).limit(1).execute()
                doc_rows = getattr(doc_r, "data", None) or []
                if doc_rows:
                    dm = doc_rows[0]
                    bucket = dm.get("storage_bucket") or "pms-certificate-documents"
                    url = _sign_url(supabase, bucket, dm.get("storage_path"))
                    if url:
                        attachments.append({
                            "id": dm.get("id") or doc_id,
                            "filename": dm.get("filename") or "Certificate Document",
                            "url": url,
                            "mime_type": dm.get("mime_type") or "application/octet-stream",
                            "size_bytes": dm.get("file_size") or 0,
                        })
            except Exception as e:
                logger.warning(f"Failed to resolve document_id {doc_id} for cert {certificate_id}: {e}")

        cert_notes = []
        try:
            notes_r = supabase.table("pms_notes").select(
                "id, text, note_type, created_by, created_at"
            ).eq("certificate_id", certificate_id).eq("yacht_id", yacht_id).order("created_at", desc=True).execute()
            cert_notes = notes_r.data or []
        except Exception:
            cert_notes = []

        cert_audit = []
        try:
            audit_r = supabase.table("pms_audit_log").select(
                "id, action, user_id, old_values, new_values, created_at"
            ).eq("entity_type", "certificate").eq("entity_id", certificate_id).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(50).execute()
            cert_audit = audit_r.data or []
        except Exception:
            cert_audit = []

        nav = [n for n in [
            _nav("document", doc_id, "Document"),
        ] if n]

        cert_table = f"pms_{'vessel' if domain == 'vessel' else 'crew'}_certificates"
        prior_periods = []
        renews_id = properties.get("renews")
        depth = 0
        while renews_id and depth < 10:
            try:
                prior_rows = (
                    supabase.table(cert_table)
                    .select("id, certificate_name, person_name, status, issue_date, expiry_date, certificate_number, properties, created_by, deleted_by")
                    .eq("id", renews_id).eq("yacht_id", yacht_id).limit(1).execute()
                )
                prior_data = (getattr(prior_rows, "data", None) or [])
                if not prior_data:
                    break
                p = prior_data[0]
                p_props = p.get("properties") or {}
                if isinstance(p_props, str):
                    try:
                        p_props = json.loads(p_props) if p_props else {}
                    except Exception:
                        p_props = {}
                prior_periods.append({
                    "id": p.get("id"),
                    "label": p.get("certificate_name") or p.get("person_name") or "Certificate",
                    "year": str(p.get("issue_date") or "")[:4] or "—",
                    "status": p.get("status"),
                    "summary": f"{p.get('issue_date', '?')} → {p.get('expiry_date', '?')}",
                    "certificate_number": p.get("certificate_number"),
                    "actor_id": p.get("created_by"),
                })
                renews_id = p_props.get("renews")
                depth += 1
            except Exception:
                break

        superseded_by = None
        try:
            fwd = (
                supabase.table(cert_table)
                .select("id, certificate_name, person_name, certificate_number, status")
                .filter("properties->>renews", "eq", certificate_id)
                .eq("yacht_id", yacht_id)
                .is_("deleted_at", None)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            fwd_data = getattr(fwd, "data", None) or []
            if fwd_data:
                f = fwd_data[0]
                superseded_by = {
                    "id": f.get("id"),
                    "label": f.get("certificate_name") or f.get("person_name") or "Certificate",
                    "certificate_number": f.get("certificate_number"),
                    "status": f.get("status"),
                }
        except Exception as _se:
            logger.warning("Failed to resolve superseded_by for cert %s: %s", certificate_id, _se)

        equipment_ids_raw = properties.get("equipment_ids") or []
        if not isinstance(equipment_ids_raw, list):
            equipment_ids_raw = []
        related_equipment = resolve_equipment_batch(supabase, yacht_id, equipment_ids_raw)

        if domain == "vessel":
            for _eq in related_equipment[:3]:
                _eq_n = _nav("equipment", _eq.get("id"), _eq.get("name") or "Equipment")
                if _eq_n:
                    nav.append(_eq_n)

        yacht_name = resolve_yacht_name(supabase, yacht_id)

        _DELETE_ACTIONS = {
            "archive_certificate",
            "delete_certificate",
            "revoke_certificate",
            "suspend_certificate",
        }
        user_ids_to_resolve: set = set()
        for e in cert_audit:
            if e.get("user_id"):
                user_ids_to_resolve.add(e["user_id"])
        for n in cert_notes:
            if n.get("created_by"):
                user_ids_to_resolve.add(n["created_by"])
        for p in prior_periods:
            if p.get("actor_id"):
                user_ids_to_resolve.add(p["actor_id"])
        if data.get("created_by"):
            user_ids_to_resolve.add(data["created_by"])
        if data.get("deleted_by"):
            user_ids_to_resolve.add(data["deleted_by"])

        user_map = resolve_users(supabase, yacht_id, user_ids_to_resolve)

        for e in cert_audit:
            uid = e.get("user_id")
            u = user_map.get(uid) or {}
            e["actor_name"] = u.get("name")
            e["actor_role"] = u.get("role")
            e["deleted"] = (e.get("action") or "") in _DELETE_ACTIONS

        for n in cert_notes:
            uid = n.get("created_by")
            u = user_map.get(uid) or {}
            n["author_name"] = u.get("name")
            n["author_role"] = u.get("role")

        for p in prior_periods:
            uid = p.get("actor_id")
            u = user_map.get(uid) or {}
            p["actor_name"] = u.get("name")
            p["actor_role"] = u.get("role")

        created_by_id = data.get("created_by")
        deleted_by_id = data.get("deleted_by")
        created_by_meta = user_map.get(created_by_id) if created_by_id else None
        deleted_by_meta = user_map.get(deleted_by_id) if deleted_by_id else None

        _entity_response = {
            "id": data.get("id"),
            "name": data.get("certificate_name") or data.get("person_name") or data.get("certificate_type"),
            "certificate_type": data.get("certificate_type"),
            "certificate_number": data.get("certificate_number"),
            "issuing_authority": data.get("issuing_authority"),
            "issue_date": data.get("issue_date"),
            "expiry_date": data.get("expiry_date"),
            "last_survey_date": data.get("last_survey_date"),
            "next_survey_due": data.get("next_survey_due"),
            "status": data.get("status", "valid"),
            "holder_name": data.get("person_name"),
            "vessel_name": yacht_name,
            "yacht_name": yacht_name,
            "document_id": doc_id,
            "domain": domain,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "created_by_name": (created_by_meta or {}).get("name"),
            "created_by_role": (created_by_meta or {}).get("role"),
            "deleted_at": data.get("deleted_at"),
            "deleted_by_name": (deleted_by_meta or {}).get("name"),
            "deleted_by_role": (deleted_by_meta or {}).get("role"),
            "properties": properties,
            "attachments": attachments,
            "notes": cert_notes,
            "audit_trail": cert_audit,
            "prior_periods": prior_periods,
            "superseded_by": superseded_by,
            "related_equipment": related_equipment,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "certificate", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Document ───────────────────────────────────────────────────────────────

    async def get_document_entity(self, document_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        r = supabase.table("doc_metadata").select("*") \
            .eq("id", document_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Document not found")

        data = r.data

        bucket = data.get("storage_bucket") or "documents"
        signed_url = _sign_url(supabase, bucket, data.get("storage_path"))

        user_ids_needed: list[str] = []
        if data.get("uploaded_by"):
            user_ids_needed.append(data["uploaded_by"])
        if data.get("deleted_by"):
            user_ids_needed.append(data["deleted_by"])

        equipment_ids = data.get("equipment_ids") or []

        audit_rows: list[dict] = []
        try:
            audit_r = (
                supabase.table("pms_audit_log")
                .select("id, action, user_id, actor_id, created_at, metadata")
                .eq("entity_type", "document")
                .eq("entity_id", document_id)
                .eq("yacht_id", yacht_id)
                .order("created_at", desc=True)
                .limit(200)
                .execute()
            )
            audit_rows = audit_r.data or []
        except Exception as exc:
            logger.warning("get_document_entity(%s): audit fetch failed: %s", document_id, exc)

        for row in audit_rows:
            for key in ("user_id", "actor_id"):
                uid = row.get(key)
                if uid:
                    user_ids_needed.append(uid)

        resolved_users = resolve_users(supabase, yacht_id, user_ids_needed)
        yacht_name = resolve_yacht_name(supabase, yacht_id)
        related_equipment = resolve_equipment_batch(supabase, yacht_id, equipment_ids)

        def _user_name(uid: Optional[str]) -> Optional[str]:
            if not uid:
                return None
            return (resolved_users.get(uid) or {}).get("name")

        def _user_role(uid: Optional[str]) -> Optional[str]:
            if not uid:
                return None
            return (resolved_users.get(uid) or {}).get("role")

        uploaded_by_uid = data.get("uploaded_by")
        deleted_by_uid = data.get("deleted_by")

        audit_trail = [
            {
                "id": row.get("id"),
                "action": (row.get("action") or "").replace("_", " "),
                "actor": _user_name(row.get("user_id") or row.get("actor_id")),
                "actor_role": _user_role(row.get("user_id") or row.get("actor_id")),
                "timestamp": row.get("created_at"),
                "deleted": bool((row.get("metadata") or {}).get("deleted")) if isinstance(row.get("metadata"), dict) else False,
            }
            for row in audit_rows
        ]

        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
        ] if n]

        _entity_response = {
            "id": data.get("id"),
            "filename": data.get("filename"),
            "title": data.get("title") or data.get("filename"),
            "description": data.get("description"),
            "mime_type": data.get("content_type"),
            "url": signed_url,
            "classification": data.get("classification"),
            "doc_type": data.get("doc_type"),
            "document_type": data.get("document_type"),
            "system_type": data.get("system_type"),
            "oem": data.get("oem"),
            "model": data.get("model"),
            "size_bytes": data.get("size_bytes"),
            "tags": data.get("tags") or [],
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "yacht_id": data.get("yacht_id"),
            "yacht_name": yacht_name,
            "uploaded_by": uploaded_by_uid,
            "uploaded_by_name": _user_name(uploaded_by_uid),
            "uploaded_by_role": _user_role(uploaded_by_uid),
            "deleted_by": deleted_by_uid,
            "deleted_by_name": _user_name(deleted_by_uid),
            "deleted_by_role": _user_role(deleted_by_uid),
            "equipment_ids": equipment_ids,
            "related_equipment": related_equipment,
            "related_entities": nav,
            "attachments": [],
            "audit_trail": audit_trail,
        }
        _entity_response["available_actions"] = get_available_actions(
            "document", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Hours of Rest ──────────────────────────────────────────────────────────

    async def get_hours_of_rest_entity(self, record_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        r = supabase.table("pms_hours_of_rest").select("*") \
            .eq("id", record_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Hours of rest record not found")

        data = r.data
        rest_periods = data.get("rest_periods") or []
        if isinstance(rest_periods, str):
            rest_periods = json.loads(rest_periods) if rest_periods else []

        is_daily = data.get("is_daily_compliant")
        if is_daily is True:
            status = "compliant"
        elif is_daily is False:
            status = "non_compliant"
        else:
            status = "unknown"

        _entity_response = {
            "id": data.get("id"),
            "crew_member_id": data.get("user_id"),
            "crew_name": None,
            "date": data.get("record_date"),
            "total_rest_hours": data.get("total_rest_hours"),
            "total_work_hours": data.get("total_work_hours"),
            "is_compliant": data.get("is_daily_compliant"),
            "status": status,
            "weekly_rest_hours": data.get("weekly_rest_hours"),
            "daily_compliance_notes": data.get("daily_compliance_notes"),
            "weekly_compliance_notes": data.get("weekly_compliance_notes"),
            "rest_periods": [
                {
                    "id": p.get("id", f"period-{i}"),
                    "start_time": (
                        p.get("start_time") or
                        (f"{data.get('record_date')}T{p['start']}:00" if p.get("start") and data.get("record_date") else p.get("start"))
                    ),
                    "end_time": (
                        p.get("end_time") or
                        (f"{data.get('record_date')}T{p['end']}:00" if p.get("end") and data.get("record_date") else p.get("end"))
                    ),
                    "duration_hours": p.get("duration_hours") or p.get("hours"),
                }
                for i, p in enumerate(rest_periods)
                if isinstance(p, dict)
            ],
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "attachments": [],
            "related_entities": [n for n in [
                _nav("crew", data.get("user_id"), "Crew Member"),
            ] if n],
        }
        _entity_response["available_actions"] = get_available_actions(
            "hours_of_rest", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Hours of Rest Monthly Sign-Off ─────────────────────────────────────────

    async def get_hor_signoff_entity(self, signoff_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        r = supabase.table("pms_hor_monthly_signoffs").select("*") \
            .eq("id", signoff_id).eq("yacht_id", yacht_id).limit(1).execute()

        if not r.data or len(r.data) == 0:
            raise HTTPException(status_code=404, detail="Sign-off record not found")

        data = r.data[0]

        user_name = None
        user_id_val = data.get("user_id")
        if user_id_val:
            try:
                user_result = supabase.table("auth_users_profiles").select(
                    "name, email"
                ).eq("id", user_id_val).eq("yacht_id", yacht_id).limit(1).execute()
                if user_result.data and len(user_result.data) > 0:
                    u = user_result.data[0]
                    user_name = u.get("name") or u.get("email")
            except Exception:
                pass

        status = data.get("status", "draft")
        title = f"HoR Sign-Off — {data.get('month', '')}"
        if user_name:
            title = f"{user_name} — {data.get('month', '')}"

        _entity_response = {
            "id": data.get("id"),
            "title": title,
            "crew_name": user_name,
            "user_id": data.get("user_id"),
            "department": data.get("department"),
            "month": data.get("month"),
            "status": status,
            "total_rest_hours": data.get("total_rest_hours"),
            "total_work_hours": data.get("total_work_hours"),
            "violation_count": data.get("violation_count"),
            "compliance_percentage": data.get("compliance_percentage"),
            "crew_signature": data.get("crew_signature"),
            "crew_signed_at": data.get("crew_signed_at"),
            "crew_signed_by": data.get("crew_signed_by"),
            "hod_signature": data.get("hod_signature"),
            "hod_signed_at": data.get("hod_signed_at"),
            "hod_signed_by": data.get("hod_signed_by"),
            "master_signature": data.get("master_signature"),
            "master_signed_at": data.get("master_signed_at"),
            "master_signed_by": data.get("master_signed_by"),
            "notes": data.get("notes"),
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "attachments": [],
            "related_entities": [n for n in [
                _nav("crew", data.get("user_id"), "Crew Member"),
            ] if n],
        }
        _entity_response["available_actions"] = get_available_actions(
            "hours_of_rest_signoff", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Shopping List Item ─────────────────────────────────────────────────────

    async def get_shopping_list_entity(self, item_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        r = supabase.table("pms_shopping_list_items").select("*") \
            .eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        data = r.data

        raw_history: list[dict] = []
        try:
            hist_r = supabase.table("pms_shopping_list_state_history").select(
                "id, previous_state, new_state, transition_reason, transition_notes, changed_by, changed_at"
            ).eq("shopping_list_item_id", item_id).eq("yacht_id", yacht_id) \
             .order("changed_at", desc=False).execute()
            raw_history = hist_r.data or []
        except Exception as e:
            logger.warning(f"[entity.shopping_list] state_history fetch failed for {item_id}: {e}")

        requester_id = data.get("requested_by") or data.get("created_by")
        approver_id = data.get("approved_by")
        rejected_id = data.get("rejected_by")
        promoted_id = data.get("promoted_by")
        updated_id = data.get("updated_by")
        history_actor_ids = {h.get("changed_by") for h in raw_history if h.get("changed_by")}
        lookup_ids = list({
            uid for uid in (
                {requester_id, approver_id, rejected_id, promoted_id, updated_id}
                | history_actor_ids
            ) if uid
        })
        profile_map: dict[str, str] = {}
        if lookup_ids:
            try:
                profiles = supabase.table("auth_users_profiles").select("id, name").in_("id", lookup_ids).execute()
                profile_map = {p["id"]: p.get("name") for p in (profiles.data or []) if p.get("id")}
            except Exception as e:
                logger.warning(f"[entity.shopping_list] profile lookup failed: {e}")

        requester_name = profile_map.get(requester_id) if requester_id else None
        approver_name = profile_map.get(approver_id) if approver_id else None
        rejected_by_name = profile_map.get(rejected_id) if rejected_id else None
        promoted_by_name = profile_map.get(promoted_id) if promoted_id else None
        updated_by_name = profile_map.get(updated_id) if updated_id else None

        def _event_label(row: dict) -> str:
            prev = row.get("previous_state")
            new = row.get("new_state")
            reason = row.get("transition_reason")
            if prev and new:
                label = f"{prev} → {new}"
            elif new:
                label = f"Status: {new}"
            else:
                label = reason or "State change"
            return label if not reason or label == reason else f"{label} — {reason}"

        audit_history = [
            {
                "id": h.get("id"),
                "action": _event_label(h),
                "actor": profile_map.get(h.get("changed_by")) if h.get("changed_by") else None,
                "timestamp": h.get("changed_at"),
                "previous_state": h.get("previous_state"),
                "new_state": h.get("new_state"),
                "transition_notes": h.get("transition_notes"),
            }
            for h in raw_history
        ]

        item = {
            "id": data.get("id"),
            "part_name": data.get("part_name"),
            "part_number": data.get("part_number"),
            "manufacturer": data.get("manufacturer"),
            "unit": data.get("unit"),
            "quantity_requested": data.get("quantity_requested"),
            "quantity_approved": data.get("quantity_approved"),
            "quantity_ordered": data.get("quantity_ordered"),
            "quantity_received": data.get("quantity_received"),
            "quantity_installed": data.get("quantity_installed"),
            "estimated_unit_price": data.get("estimated_unit_price"),
            "preferred_supplier": data.get("preferred_supplier"),
            "urgency": data.get("urgency"),
            "status": data.get("status"),
            "source_type": data.get("source_type"),
            "source_notes": data.get("source_notes"),
            "required_by_date": data.get("required_by_date"),
            "is_candidate_part": data.get("is_candidate_part", False),
            "approval_notes": data.get("approval_notes"),
            "approved_at": data.get("approved_at"),
            "rejection_reason": data.get("rejection_reason"),
            "rejection_notes": data.get("rejection_notes"),
            "rejected_at": data.get("rejected_at"),
            "rejected_by_name": rejected_by_name,
            "order_id": data.get("order_id"),
            "order_line_number": data.get("order_line_number"),
            "fulfilled_at": data.get("fulfilled_at"),
            "installed_at": data.get("installed_at"),
            "installed_to_equipment_id": data.get("installed_to_equipment_id"),
            "candidate_promoted_to_part_id": data.get("candidate_promoted_to_part_id"),
            "promoted_at": data.get("promoted_at"),
            "promoted_by_name": promoted_by_name,
            "updated_at": data.get("updated_at"),
            "updated_by_name": updated_by_name,
            "source_work_order_id": data.get("source_work_order_id"),
            "source_receiving_id": data.get("source_receiving_id"),
        }

        nav = [n for n in [
            _nav("part", data.get("part_id"), "Linked Part"),
            _nav("work_order", data.get("source_work_order_id"), "Source Work Order"),
            _nav("receiving", data.get("source_receiving_id"), "Source Receiving"),
            _nav("purchase_order", data.get("order_id"), "Linked Purchase Order"),
            _nav("equipment", data.get("installed_to_equipment_id"), "Installed to Equipment"),
            _nav("part", data.get("candidate_promoted_to_part_id"), "Promoted Part"),
        ] if n]

        _entity_response = {
            "id": data.get("id"),
            "title": data.get("part_name") or "Shopping List Item",
            "status": data.get("status", "candidate"),
            "urgency": data.get("urgency"),
            "priority": data.get("urgency"),
            "requester_id": requester_id,
            "requester_name": requester_name,
            "created_by": requester_name,
            "approver_name": approver_name,
            "rejected_by_name": rejected_by_name,
            "promoted_by_name": promoted_by_name,
            "updated_by_name": updated_by_name,
            "approved_at": data.get("approved_at"),
            "approval_notes": data.get("approval_notes"),
            "rejected_at": data.get("rejected_at"),
            "rejection_reason": data.get("rejection_reason"),
            "rejection_notes": data.get("rejection_notes"),
            "fulfilled_at": data.get("fulfilled_at"),
            "installed_at": data.get("installed_at"),
            "promoted_at": data.get("promoted_at"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "source_type": data.get("source_type"),
            "source_notes": data.get("source_notes"),
            "description": data.get("source_notes"),
            "quantity_requested": data.get("quantity_requested"),
            "quantity_approved": data.get("quantity_approved"),
            "quantity_ordered": data.get("quantity_ordered"),
            "quantity_received": data.get("quantity_received"),
            "quantity_installed": data.get("quantity_installed"),
            "estimated_unit_price": data.get("estimated_unit_price"),
            "preferred_supplier": data.get("preferred_supplier"),
            "unit": data.get("unit"),
            "required_by_date": data.get("required_by_date"),
            "is_candidate_part": data.get("is_candidate_part", False),
            "items": [item],
            "notes": [],
            "yacht_id": data.get("yacht_id"),
            "attachments": _get_attachments(supabase, "shopping_list", item_id, yacht_id),
            "related_entities": nav,
            "audit_history": audit_history,
        }
        _entity_response["available_actions"] = get_available_actions(
            "shopping_list", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Warranty Claim ─────────────────────────────────────────────────────────

    async def get_warranty_entity(self, warranty_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        _supabase_err = None
        r = None
        for _attempt in range(3):
            try:
                r = supabase.table("v_warranty_enriched").select("*") \
                    .eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()
                _supabase_err = None
                break
            except Exception as _e:
                _supabase_err = _e
                if _attempt < 2:
                    time.sleep(0.8)
        if _supabase_err is not None:
            raise _supabase_err

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Warranty not found")

        data = r.data

        try:
            import hashlib as _hl
            _view_now = datetime.now(timezone.utc).isoformat()
            _proof = _hl.sha256(f"{yacht_id}{warranty_id}view_warranty_claim{_view_now}".encode()).hexdigest()
            get_supabase_client().table("ledger_events").insert({
                "yacht_id": yacht_id,
                "event_type": "view",
                "entity_type": "warranty",
                "entity_id": warranty_id,
                "action": "view_warranty_claim",
                "user_id": auth.get("user_id") or auth.get("sub") or "00000000-0000-0000-0000-000000000000",
                "user_role": auth.get("role") or "unknown",
                "change_summary": f"Viewed warranty claim",
                "source_context": "microaction",
                "proof_hash": _proof,
                "event_timestamp": _view_now,
                "created_at": _view_now,
            }).execute()
        except Exception:
            pass

        title = data.get("title") or data.get("claim_number") or (data.get("id", "")[:8])

        attachments = _get_attachments(supabase, "warranty", warranty_id, yacht_id)
        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
            _nav("fault", data.get("fault_id"), "Fault"),
            _nav("work_order", data.get("work_order_id"), "Work Order"),
        ] if n]

        try:
            notes_r = supabase.table("pms_notes").select(
                "id, text, note_type, created_by, created_by_role, created_at"
            ).eq("warranty_id", warranty_id).eq("yacht_id", yacht_id).order("created_at", desc=True).execute()
            warranty_notes = notes_r.data or []
        except Exception:
            warranty_notes = []

        try:
            audit_r = supabase.table("pms_audit_log").select(
                "id, action, user_id, new_values, created_at"
            ).eq("entity_type", "warranty").eq("entity_id", warranty_id).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(50).execute()
            warranty_audit = audit_r.data or []
        except Exception:
            warranty_audit = []

        _entity_response = {
            "id": data.get("id"),
            "title": title,
            "claim_number": data.get("claim_number"),
            "equipment_id": data.get("equipment_id"),
            "fault_id": data.get("fault_id"),
            "work_order_id": data.get("work_order_id"),
            "vendor_name": data.get("vendor_name"),
            "manufacturer": data.get("manufacturer"),
            "part_number": data.get("part_number"),
            "serial_number": data.get("serial_number"),
            "purchase_date": data.get("purchase_date"),
            "expiry_date": data.get("warranty_expiry"),
            "status": data.get("status"),
            "claimed_amount": data.get("claimed_amount"),
            "approved_amount": data.get("approved_amount"),
            "currency": data.get("currency"),
            "description": data.get("description"),
            "claim_type": data.get("claim_type"),
            "created_at": data.get("created_at"),
            "yacht_id": data.get("yacht_id"),
            "equipment_name": data.get("equipment_name"),
            "equipment_code": data.get("equipment_code"),
            "days_until_expiry": data.get("days_until_expiry"),
            "status_label": data.get("status_label"),
            "workflow_stage": data.get("workflow_stage"),
            "drafted_at": data.get("drafted_at"),
            "submitted_at": data.get("submitted_at"),
            "approved_at": data.get("approved_at"),
            "rejected_by": data.get("rejected_by"),
            "rejected_at": data.get("rejected_at"),
            "rejection_reason": data.get("rejection_reason"),
            "email_draft": data.get("email_draft"),
            "metadata": data.get("metadata"),
            "attachments": attachments,
            "notes": warranty_notes,
            "audit_trail": warranty_audit,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "warranty", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Purchase Order ─────────────────────────────────────────────────────────

    async def get_purchase_order_entity(self, po_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        r = supabase.table("pms_purchase_orders").select("*") \
            .eq("id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        data = r.data

        items_r = supabase.table("pms_purchase_order_items").select("*") \
            .eq("purchase_order_id", po_id).execute()
        raw_items = items_r.data or []

        items = [
            {
                "id": item.get("id"),
                "part_id": item.get("part_id"),
                "name": item.get("name") or item.get("part_name") or item.get("description"),
                "description": item.get("description"),
                "quantity_ordered": item.get("quantity_ordered"),
                "quantity": item.get("quantity_ordered"),
                "quantity_received": item.get("quantity_received", 0),
                "unit_price": item.get("unit_price"),
                "currency": item.get("currency") or data.get("currency", "USD"),
                "line_status": item.get("line_status", "accepted"),
                "denied_at": item.get("denied_at"),
                "denial_reason": item.get("denial_reason"),
                "shopping_list_item_id": item.get("shopping_list_item_id"),
            }
            for item in raw_items
        ]

        computed_total = sum(
            (float(it.get("unit_price") or 0) * float(it.get("quantity_ordered") or 0))
            for it in raw_items
        ) or None

        supplier_id = data.get("supplier_id")
        supplier_name: Optional[str] = None
        supplier_block: Optional[Dict[str, Any]] = None
        if supplier_id:
            try:
                sup_r = supabase.table("pms_suppliers").select(
                    "id, name, contact_name, email, phone, preferred, address"
                ).eq("id", supplier_id).maybe_single().execute()
                if sup_r and sup_r.data:
                    supplier_name = sup_r.data.get("name")
                    supplier_block = {
                        "id":           sup_r.data.get("id"),
                        "name":         sup_r.data.get("name"),
                        "contact_name": sup_r.data.get("contact_name"),
                        "email":        sup_r.data.get("email"),
                        "phone":        sup_r.data.get("phone"),
                        "preferred":    sup_r.data.get("preferred") or False,
                        "address":      sup_r.data.get("address") or None,
                    }
            except Exception as e:
                logger.warning(f"Supplier resolve failed for po={po_id}: {e}")

        actor_ids = [
            uid for uid in (
                data.get("ordered_by"),
                data.get("approved_by"),
                data.get("received_by"),
                data.get("deleted_by"),
            ) if uid
        ]
        actor_map = resolve_users(supabase, yacht_id, actor_ids) if actor_ids else {}

        def _actor(uid: Optional[str]) -> Dict[str, Optional[str]]:
            entry = actor_map.get(uid) if uid else None
            if not entry:
                return {"id": uid, "name": None, "role": None}
            return {"id": uid, "name": entry.get("name"), "role": entry.get("role")}

        ordered_by_actor  = _actor(data.get("ordered_by"))
        approved_by_actor = _actor(data.get("approved_by"))
        received_by_actor = _actor(data.get("received_by"))
        deleted_by_actor  = _actor(data.get("deleted_by"))

        part_ids = sorted({it.get("part_id") for it in raw_items if it.get("part_id")})
        related_parts: List[Dict[str, Any]] = []
        if part_ids:
            try:
                parts_r = supabase.table("pms_parts").select(
                    "id, part_number, name, manufacturer, description"
                ).in_("id", part_ids).eq("yacht_id", yacht_id).execute()
                related_parts = [
                    {
                        "id":           p.get("id"),
                        "part_number":  p.get("part_number"),
                        "name":         p.get("name"),
                        "manufacturer": p.get("manufacturer"),
                        "description": (p.get("description") or "")[:120],
                    }
                    for p in (parts_r.data or [])
                ]
            except Exception as e:
                logger.warning(f"Related parts resolve failed for po={po_id}: {e}")

        meta = data.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        notes_text = meta.get("notes")
        deletion_reason = meta.get("deletion_reason")

        attachments = _get_attachments(supabase, "purchase_order", po_id, yacht_id)

        nav = []
        if data.get("source_shopping_list_id"):
            nav.append(_nav("shopping_list", data["source_shopping_list_id"], "Source Shopping List"))
        for it in raw_items[:5]:
            n = _nav("part", it.get("part_id"), it.get("description") or it.get("name") or "Part")
            if n:
                nav.append(n)
        try:
            recv_r = supabase.table("pms_receiving").select(
                "id, po_number, received_date, status"
            ).eq("po_id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").limit(5).execute()
            for _recv in (recv_r.data or []):
                _recv_po_num = _recv.get("po_number") or data.get("po_number")
                _label = f"Receiving · {_recv_po_num}" if _recv_po_num else "Receiving"
                _n = _nav("receiving", _recv.get("id"), _label)
                if _n:
                    nav.append(_n)
        except Exception as _re:
            logger.warning(f"get_purchase_order_entity: receiving backwards compat failed po={po_id}: {_re}")

        _entity_response = {
            "id": data.get("id"),
            "po_number": data.get("po_number"),
            "status": data.get("status"),
            "supplier_name": supplier_name,
            "supplier_id": supplier_id,
            "supplier": supplier_block,
            "order_date": data.get("ordered_at") or data.get("created_at"),
            "ordered_at": data.get("ordered_at"),
            "received_at": data.get("received_at"),
            "approved_at": data.get("approved_at"),
            "expected_delivery": data.get("expected_delivery") or data.get("expected_delivery_date"),
            "tracking_number": data.get("tracking_number"),
            "carrier": data.get("carrier"),
            "expected_delivery_start": data.get("expected_delivery_start"),
            "expected_delivery_end": data.get("expected_delivery_end"),
            "source_shopping_list_id": data.get("source_shopping_list_id"),
            "total_amount": data.get("total_amount") or computed_total,
            "item_count": len(raw_items),
            "currency": data.get("currency", "USD"),
            "notes": notes_text,
            "description": notes_text,
            "approval_notes": data.get("approval_notes"),
            "receiving_notes": data.get("receiving_notes"),
            "ordered_by": data.get("ordered_by"),
            "approved_by": data.get("approved_by") or (meta.get("approved_by") if isinstance(meta, dict) else None),
            "received_by": data.get("received_by"),
            "ordered_by_actor":  ordered_by_actor,
            "approved_by_actor": approved_by_actor,
            "received_by_actor": received_by_actor,
            "items": items,
            "line_items": items,
            "related_parts": related_parts,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "deleted_at": data.get("deleted_at"),
            "deleted_by_actor": deleted_by_actor if data.get("deleted_at") else None,
            "deletion_reason": deletion_reason,
            "yacht_id": data.get("yacht_id"),
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "purchase_order", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Fault ──────────────────────────────────────────────────────────────────

    async def get_fault_entity(self, fault_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        response = supabase.table('pms_faults').select('*').eq('id', fault_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Fault not found")

        data = response.data

        attachments = _get_attachments(supabase, "fault", fault_id, yacht_id)

        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
        ] if n]
        try:
            wo_r = supabase.table("pms_work_orders").select("id, title").eq(
                "fault_id", fault_id
            ).eq("yacht_id", yacht_id).limit(5).execute()
            for wo in (wo_r.data or []):
                n = _nav("work_order", wo.get("id"), wo.get("title") or "Work Order")
                if n:
                    nav.append(n)
        except Exception:
            pass

        fault_metadata = data.get('metadata', {}) or {}
        _entity_response = {
            "id": data.get('id'),
            "title": data.get('title') or data.get('fault_code', 'Unknown Fault'),
            "description": data.get('description', ''),
            "severity": data.get('severity', 'medium'),
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),
            "reported_at": data.get('reported_at') or data.get('detected_at'),
            "reporter": data.get('reporter') or data.get('reported_by', 'System'),
            "status": data.get('status'),
            "has_work_order": data.get('has_work_order', False),
            "ai_diagnosis": data.get('ai_diagnosis'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "attachments": attachments,
            "related_entities": nav,
            "notes": fault_metadata.get("notes", []),
        }
        _entity_response["available_actions"] = get_available_actions(
            "fault", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Work Order ─────────────────────────────────────────────────────────────

    async def _is_user_hod(self, user_id: str, yacht_id: str) -> bool:
        """Check if user has Head of Department (HOD) role."""
        try:
            result = self.db.table('auth_users_roles').select('role').eq(
                'user_id', user_id
            ).eq(
                'yacht_id', yacht_id
            ).eq(
                'is_active', True
            ).in_(
                'role', ['chief_engineer', 'chief_officer', 'captain', 'purser']
            ).maybe_single().execute()
            return bool(result.data)
        except Exception as e:
            logger.warning(f"Failed to check HOD status for user {user_id}: {e}")
            return False

    async def get_work_order_entity(self, work_order_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db
        user_id = auth['user_id']

        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection unavailable")

        response = supabase.table('pms_work_orders').select('*').eq('id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()
        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Work order not found")

        data = response.data
        wo_id = data.get('id') or data.get('work_order_id')

        notes_response = supabase.table('pms_work_order_notes').select(
            'id, note_text, note_type, created_by, created_at'
        ).eq('work_order_id', wo_id).order('created_at', desc=True).execute()
        _raw_notes = notes_response.data if notes_response.data else []

        # Enrich notes: resolve created_by UUID → name + role for display
        _note_user_ids = list({n.get('created_by') for n in _raw_notes if n.get('created_by')})
        _profile_map: dict = {}
        _role_map: dict = {}
        if _note_user_ids:
            try:
                _prof_r = supabase.table('auth_users_profiles').select('id, name, email').in_(
                    'id', _note_user_ids
                ).execute()
                for _p in (_prof_r.data or []):
                    _profile_map[_p['id']] = _p.get('name') or _p.get('email')
            except Exception as _e:
                logger.warning(f"get_work_order_entity: notes profile lookup failed: {_e}")
            try:
                _role_r = supabase.table('auth_users_roles').select('user_id, role').in_(
                    'user_id', _note_user_ids
                ).eq('yacht_id', yacht_id).eq('is_active', True).execute()
                for _r in (_role_r.data or []):
                    _role_map[_r['user_id']] = _r.get('role')
            except Exception as _e:
                logger.warning(f"get_work_order_entity: notes role lookup failed: {_e}")
        notes = []
        for _n in _raw_notes:
            _uid = _n.get('created_by')
            notes.append({**_n, 'author_name': _profile_map.get(_uid) if _uid else None,
                          'author_role': _role_map.get(_uid) if _uid else None})

        parts_response = supabase.table('pms_work_order_parts').select(
            'id, part_id, quantity, notes, created_at, pms_parts(id, name, part_number, location)'
        ).eq('work_order_id', wo_id).execute()
        # Flatten pms_parts join so frontend reads name/part_number at top level
        parts = []
        for _row in (parts_response.data or []):
            _nested = _row.get('pms_parts') or {}
            parts.append({
                'id': _row.get('id'), 'part_id': _row.get('part_id'),
                'quantity': _row.get('quantity'), 'notes': _row.get('notes'),
                'created_at': _row.get('created_at'), 'name': _nested.get('name'),
                'part_number': _nested.get('part_number'), 'location': _nested.get('location'),
            })

        try:
            checklist_response = supabase.table('pms_work_order_checklist').select(
                'id, title, description, is_completed, completed_by, completed_at, '
                'sequence, item_type, actual_value, is_required'
            ).eq('work_order_id', wo_id).order('sequence').execute()
            checklist = checklist_response.data if checklist_response.data else []
        except Exception:
            checklist = []

        audit_response = supabase.table('pms_audit_log').select(
            'id, action, old_values, new_values, user_id, created_at'
        ).eq('entity_type', 'work_order').eq('entity_id', wo_id).eq('yacht_id', yacht_id).order('created_at', desc=True).limit(50).execute()
        _read_prefixes = ('view_', 'list_', 'get_', 'read_')
        audit_history = [
            a for a in (audit_response.data or [])
            if not any((a.get('action') or '').startswith(p) for p in _read_prefixes)
        ]
        _audit_user_ids = list({a['user_id'] for a in audit_history if a.get('user_id')})
        if _audit_user_ids:
            _audit_actor_map = resolve_users(supabase, yacht_id, _audit_user_ids)
            for _a in audit_history:
                _uid = _a.get('user_id')
                if _uid and _uid in _audit_actor_map:
                    _a['actor'] = _audit_actor_map[_uid]

        is_hod = await self._is_user_hod(user_id, yacht_id)

        attachments = _get_attachments(supabase, "work_order", wo_id, yacht_id)
        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
            _nav("fault", data.get("fault_id"), "Fault"),
        ] if n]

        # Linked documents — uploaded via /v1/documents/upload + /v1/documents/link
        linked_docs = []
        try:
            links_resp = supabase.table('email_attachment_object_links').select(
                'id, document_id, link_reason, created_at'
            ).eq('object_type', 'work_order').eq('object_id', wo_id).eq(
                'yacht_id', yacht_id
            ).eq('is_active', True).execute()
            for link in (links_resp.data or []):
                doc_id = link['document_id']
                # doc_metadata first (documents uploaded via /v1/documents/upload)
                dm = supabase.table('doc_metadata').select(
                    'id, title, doc_type, description, created_at'
                ).eq('id', doc_id).eq('yacht_id', yacht_id).maybe_single().execute()
                doc = dm.data if dm and dm.data else None
                if not doc:
                    # fallback: doc_yacht_library (email-sourced documents)
                    lib = supabase.table('doc_yacht_library').select(
                        'id, document_name, document_type, created_at'
                    ).eq('id', doc_id).maybe_single().execute()
                    raw = lib.data if lib and lib.data else {}
                    doc = {'title': raw.get('document_name'), 'doc_type': raw.get('document_type'), 'created_at': raw.get('created_at')}
                linked_docs.append({
                    'id': link['id'],
                    'document_id': doc_id,
                    'name': doc.get('title') or 'Document',
                    'code': doc.get('doc_type'),
                    'meta': link.get('link_reason'),
                    'date': (doc.get('created_at') or link.get('created_at') or '')[:10],
                })
        except Exception as _doc_err:
            logger.warning(f"get_work_order_entity: linked docs failed: {_doc_err}")

        # Fault enrichment — resolve fault_id → full fault card data for Faults tab
        faults_data = []
        _fault_id = data.get('fault_id')
        if _fault_id:
            try:
                _fault_r = supabase.table('pms_faults').select(
                    'id, title, fault_code, status, severity'
                ).eq('id', _fault_id).eq('yacht_id', yacht_id).maybe_single().execute()
                if _fault_r and _fault_r.data:
                    faults_data = [_fault_r.data]
            except Exception as _fe:
                logger.warning(f"get_work_order_entity: fault enrichment failed: {_fe}")

        _entity_response = {
            "id": wo_id,
            "yacht_id": data.get('yacht_id'),
            "wo_number": data.get('wo_number'),
            "title": data.get('title', 'Untitled Work Order'),
            "description": data.get('description', ''),
            "status": data.get('status', 'pending'),
            "priority": data.get('priority', 'medium'),
            "type": data.get('type') or data.get('work_order_type'),
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),
            "assigned_to": data.get('assigned_to'),
            "assigned_to_name": data.get('assigned_to_name'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "due_date": data.get('due_date'),
            "frequency": data.get('frequency'),
            "completed_at": data.get('completed_at'),
            "completed_by": data.get('completed_by'),
            "fault_id": data.get('fault_id'),
            "faults": faults_data,
            "notes": notes,
            "parts": parts,
            "checklist": checklist,
            "audit_history": audit_history,
            "notes_count": len(notes),
            "parts_count": len(parts),
            "checklist_count": len(checklist),
            "checklist_completed": len([c for c in checklist if c.get('is_completed')]),
            "attachments": attachments,
            "documents": linked_docs,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "work_order", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Equipment ──────────────────────────────────────────────────────────────

    async def get_equipment_entity(self, equipment_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        response = supabase.table('pms_equipment').select('*').eq('id', equipment_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Equipment not found")

        data = response.data
        metadata = data.get('metadata') or {}

        attachments = _get_attachments(supabase, "equipment", equipment_id, yacht_id)

        try:
            notes_r = supabase.table('pms_notes').select(
                'id, text, note_type, created_by, created_at'
            ).eq('equipment_id', equipment_id).eq('yacht_id', yacht_id).order('created_at', desc=True).execute()
            equipment_notes = notes_r.data or []
        except Exception:
            equipment_notes = []

        nav = []
        try:
            wo_r = supabase.table("pms_work_orders").select("id, title").eq(
                "equipment_id", equipment_id
            ).eq("yacht_id", yacht_id).limit(3).execute()
            for wo in (wo_r.data or []):
                n = _nav("work_order", wo.get("id"), wo.get("title") or "Work Order")
                if n:
                    nav.append(n)
        except Exception:
            pass
        try:
            f_r = supabase.table("pms_faults").select("id, title").eq(
                "equipment_id", equipment_id
            ).eq("yacht_id", yacht_id).limit(3).execute()
            for f in (f_r.data or []):
                n = _nav("fault", f.get("id"), f.get("title") or "Fault")
                if n:
                    nav.append(n)
        except Exception:
            pass

        parent_equipment = None
        parent_id = data.get("parent_id")
        if parent_id:
            try:
                pe_r = supabase.table("pms_equipment").select(
                    "id, name, code, system_type"
                ).eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if pe_r and pe_r.data:
                    parent_equipment = pe_r.data
            except Exception:
                pass

        linked_parts = []
        try:
            bom_r = supabase.table("pms_equipment_parts_bom").select(
                "part_id, quantity_required, notes, pms_parts(id, name, part_number, quantity_on_hand, location)"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).limit(50).execute()
            for row in (bom_r.data or []):
                part = row.get("pms_parts")
                if part:
                    linked_parts.append({
                        **part,
                        "quantity_required": row.get("quantity_required"),
                        "bom_notes": row.get("notes"),
                    })
        except Exception:
            pass

        _entity_response = {
            "id": data.get('id'),
            "name": data.get('name', 'Unknown Equipment'),
            "code": data.get('code'),
            "system_type": data.get('system_type'),
            "equipment_type": data.get('system_type') or metadata.get('category', 'General'),
            "manufacturer": data.get('manufacturer'),
            "model": data.get('model'),
            "serial_number": data.get('serial_number'),
            "location": data.get('location', 'Unknown'),
            "status": metadata.get('status', 'operational'),
            "criticality": data.get('criticality'),
            "running_hours": data.get('running_hours'),
            "installation_date": data.get('installed_date'),
            "last_maintenance": metadata.get('last_maintenance'),
            "next_maintenance": metadata.get('next_maintenance'),
            "description": data.get('description'),
            "attention_flag": data.get('attention_flag'),
            "attention_reason": data.get('attention_reason'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "attachments": attachments,
            "related_entities": nav,
            "notes": equipment_notes,
            "parent_equipment": parent_equipment,
            "linked_parts": linked_parts,
        }
        _entity_response["available_actions"] = get_available_actions(
            "equipment", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Part ───────────────────────────────────────────────────────────────────

    async def get_part_entity(self, part_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        response = supabase.table('pms_parts').select('*').eq('id', part_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Part not found")

        data = response.data
        metadata = data.get('metadata') or {}

        image_bucket = data.get('image_bucket') or 'pms-work-order-photos'
        image_url = _sign_url(supabase, image_bucket, data.get('image_storage_path'))

        attachments = _get_attachments(supabase, "part", part_id, yacht_id)

        try:
            notes_r = supabase.table('pms_notes').select(
                'id, text, note_type, created_by, created_at'
            ).eq('part_id', part_id).eq('yacht_id', yacht_id).order('created_at', desc=True).execute()
            part_notes = notes_r.data or []
        except Exception:
            part_notes = []

        # Related WOs — surface work orders that use this part (backwards compat)
        related_wo_nav = []
        try:
            wo_part_r = supabase.table('pms_work_order_parts').select(
                'work_order_id, pms_work_orders(id, title, wo_number, yacht_id)'
            ).eq('part_id', part_id).limit(5).execute()
            for _row in (wo_part_r.data or []):
                _wo = _row.get('pms_work_orders')
                if _wo and _wo.get('yacht_id') == yacht_id:
                    _label = _wo.get('title') or f"WO {_wo.get('wo_number') or ''}".strip()
                    _n = _nav("work_order", _wo.get("id"), _label or "Work Order")
                    if _n:
                        related_wo_nav.append(_n)
        except Exception as _we:
            logger.warning(f"get_part_entity: related WOs lookup failed: {_we}")

        # Shopping list items that reference this part (backwards compat)
        # Use shopping_list_id (list header), not item id — item id 404s on the V2 doc page.
        related_sl_nav = []
        try:
            sl_r = supabase.table("pms_shopping_list_items").select(
                "shopping_list_id, part_name, part_number, status"
            ).eq("part_id", part_id).eq("yacht_id", yacht_id).limit(5).execute()
            _seen_sl: set = set()
            for _sl in (sl_r.data or []):
                _sl_id = _sl.get("shopping_list_id")
                if _sl_id and _sl_id not in _seen_sl:
                    _seen_sl.add(_sl_id)
                    _label = _sl.get("part_name") or _sl.get("part_number") or "Shopping List"
                    _n = _nav("shopping_list", _sl_id, _label)
                    if _n:
                        related_sl_nav.append(_n)
        except Exception as _se:
            logger.warning(f"get_part_entity: related shopping lists lookup failed: {_se}")

        # PO items that reference this part (backwards compat)
        related_po_nav = []
        try:
            poi_r = supabase.table("pms_purchase_order_items").select(
                "purchase_order_id, pms_purchase_orders(id, po_number, status, yacht_id)"
            ).eq("part_id", part_id).eq("yacht_id", yacht_id).limit(5).execute()
            _seen_po_ids: set = set()
            for _row in (poi_r.data or []):
                _po = _row.get("pms_purchase_orders") or {}
                _po_id_val = _po.get("id")
                if _po_id_val and _po.get("yacht_id") == yacht_id and _po_id_val not in _seen_po_ids:
                    _seen_po_ids.add(_po_id_val)
                    _po_num = _po.get("po_number")
                    _label = f"PO {_po_num}" if _po_num else "Purchase Order"
                    _n = _nav("purchase_order", _po_id_val, _label)
                    if _n:
                        related_po_nav.append(_n)
        except Exception as _pe:
            logger.warning(f"get_part_entity: related POs lookup failed: {_pe}")

        _entity_response = {
            "id": data.get('id'),
            "name": data.get('name') or 'Unknown Part',
            "part_number": data.get('part_number', ''),
            "stock_quantity": data.get('quantity_on_hand', 0),
            "min_stock_level": data.get('minimum_quantity') or data.get('min_level', 0),
            "location": data.get('location', 'Unknown'),
            "unit_cost": metadata.get('unit_cost'),
            "supplier": metadata.get('supplier'),
            "category": data.get('category'),
            "unit": data.get('unit'),
            "manufacturer": data.get('manufacturer'),
            "description": data.get('description'),
            "last_counted_at": data.get('last_counted_at'),
            "last_counted_by": data.get('last_counted_by'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "image_url": image_url,
            "attachments": attachments,
            "related_entities": related_wo_nav + related_sl_nav + related_po_nav,
            "notes": part_notes,
        }
        _entity_response["available_actions"] = get_available_actions(
            "part", _entity_response, auth.get("role", "crew")
        )
        return _entity_response

    # ── Receiving ──────────────────────────────────────────────────────────────

    async def get_receiving_entity(self, receiving_id: str, yacht_id: str, auth: dict) -> dict:
        supabase = self.db

        response = supabase.table('pms_receiving') \
            .select('*') \
            .eq('id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .maybe_single() \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receiving not found")

        data = response.data

        items_response = supabase.table('pms_receiving_items') \
            .select('id, description, quantity_expected, quantity_received, quantity_accepted, quantity_rejected, disposition, unit_price, currency, part_id') \
            .eq('receiving_id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .execute()
        raw_items = items_response.data or []

        attachments = _get_attachments(supabase, "receiving", receiving_id, yacht_id)

        invoice_images = [
            a for a in attachments
            if (a.get("mime_type") or "").startswith("image/")
        ]

        received_by_id = data.get('received_by')
        received_by_name = None
        if received_by_id:
            try:
                u_r = supabase.table('auth_users_profiles').select('name, email').eq(
                    'id', received_by_id
                ).maybe_single().execute()
                if u_r and u_r.data:
                    received_by_name = u_r.data.get('name') or u_r.data.get('email')
            except Exception as e:
                logger.warning(f"received_by lookup failed for {received_by_id}: {e}")

        yacht_name = None
        try:
            y_r = supabase.table('yacht_registry').select('name').eq(
                'id', yacht_id
            ).maybe_single().execute()
            if y_r and y_r.data:
                yacht_name = y_r.data.get('name')
        except Exception as e:
            logger.warning(f"yacht_name lookup failed for {yacht_id}: {e}")

        nav = []
        for it in raw_items[:5]:
            n = _nav("part", it.get("part_id"), it.get("description") or "Part")
            if n:
                nav.append(n)

        po_num = data.get("po_number")
        po_id = data.get("po_id")
        supplier_email = None
        linked_po_items = []

        if po_id:
            try:
                po_r = supabase.table("pms_purchase_orders").select(
                    "id, po_number, supplier_id, pms_suppliers(email)"
                ).eq("id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if po_r and po_r.data:
                    po_data = po_r.data
                    po_num = po_num or po_data.get("po_number")
                    sup = po_data.get("pms_suppliers") or {}
                    supplier_email = sup.get("email")
                    nav_label = f"PO {po_num}" if po_num else "Purchase Order"
                    n = _nav("purchase_order", po_id, nav_label)
                    if n:
                        nav.append(n)
                    try:
                        po_items_r = supabase.table("pms_purchase_order_items").select(
                            "id, part_id, description, quantity_ordered, quantity_received, unit_price"
                        ).eq("purchase_order_id", po_id).eq("yacht_id", yacht_id).execute()
                        linked_po_items = po_items_r.data or []
                    except Exception as e:
                        logger.warning(f"linked_po_items fetch failed for po {po_id}: {e}")
            except Exception as e:
                logger.warning(f"PO FK lookup failed for receiving {receiving_id}: {e}")
        elif po_num:
            try:
                po_r = supabase.table("pms_purchase_orders").select("id").eq(
                    "po_number", po_num
                ).eq("yacht_id", yacht_id).maybe_single().execute()
                if po_r and po_r.data:
                    po_id = po_r.data["id"]
                    n = _nav("purchase_order", po_id, f"PO {po_num}")
                    if n:
                        nav.append(n)
            except Exception:
                pass

        audit_history = []
        try:
            lh_r = supabase.table('ledger_events').select(
                'id, action, change_summary, user_id, user_role, created_at'
            ).eq('entity_type', 'receiving').eq('entity_id', receiving_id).eq(
                'yacht_id', yacht_id
            ).neq('event_category', 'read').order('created_at', desc=True).limit(50).execute()
            audit_history = lh_r.data or []
        except Exception as e:
            logger.warning(f"audit_history lookup failed for receiving/{receiving_id}: {e}")

        _entity_response = {
            "id": data.get('id'),
            "vendor_name": data.get('vendor_name'),
            "vendor_reference": data.get('vendor_reference'),
            "po_number": po_num,
            "po_id": po_id,
            "supplier_email": supplier_email,
            "received_date": data.get('received_date'),
            "status": data.get('status', 'awaiting'),
            "shipment_number": data.get('shipment_number', 1),
            "total_shipments": data.get('total_shipments', 1),
            "total": data.get('total'),
            "currency": data.get('currency'),
            "notes": data.get('notes'),
            "received_by": received_by_name,
            "yacht_name": yacht_name,
            "items": raw_items,
            "total_items": len(raw_items),
            "linked_po_items": linked_po_items,
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "invoice_images": invoice_images,
            "attachments": attachments,
            "related_entities": nav,
            "audit_history": audit_history,
        }
        _entity_response["available_actions"] = get_available_actions(
            "receiving", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
