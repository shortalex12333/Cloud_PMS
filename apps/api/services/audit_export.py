"""
CelesteOS API - Audit Evidence Export Service
==============================================

Compliance evidence exporter for SOC2/ISO audit trails.

Functions:
- export_audit_trace: Export full audit trail for yacht/user/time window
- Redaction: payload_hash included, raw payload excluded
- Output: JSONL + CSV summaries + index.json metadata

Usage:
    from services.audit_export import export_audit_trace

    bundle_path = await export_audit_trace(
        db_client=client,
        yacht_id="yacht-001",
        user_id="user-001",  # optional
        start_ts="2026-01-01T00:00:00Z",
        end_ts="2026-01-31T23:59:59Z",
        out_dir="evidence/yacht-001/2026-01",
    )
"""

import os
import json
import csv
import hashlib
import zipfile
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Exporter version for reproducibility
EXPORTER_VERSION = "1.0.0"

# Fields to redact (never include in export)
REDACT_FIELDS = {
    "raw_payload",
    "payload",
    "password",
    "secret",
    "token",
    "api_key",
    "email_body",
    "document_content",
}

# Fields to hash (include as hash instead of raw value)
HASH_FIELDS = {
    "email",
}


def _hash_value(value: str) -> str:
    """Hash a value for redaction."""
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive fields from a dict.

    - REDACT_FIELDS: removed entirely
    - HASH_FIELDS: replaced with hash
    - Nested dicts are processed recursively
    - Fields ending in _hash are preserved (already hashed)
    """
    if not data:
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Always preserve hash fields (already redacted)
        if key_lower.endswith("_hash"):
            result[key] = value
            continue

        # Skip redacted fields
        if key_lower in REDACT_FIELDS or any(r in key_lower for r in REDACT_FIELDS):
            continue

        # Hash sensitive fields
        if key_lower in HASH_FIELDS:
            result[f"{key}_hash"] = _hash_value(str(value)) if value else None
            continue

        # Recursively process nested dicts
        if isinstance(value, dict):
            result[key] = _redact_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def _write_jsonl(filepath: Path, records: List[Dict[str, Any]]):
    """Write records as JSON Lines."""
    with open(filepath, "w") as f:
        for record in records:
            f.write(json.dumps(record, default=str) + "\n")


def _write_csv(filepath: Path, records: List[Dict[str, Any]], columns: List[str]):
    """Write records as CSV with specified columns."""
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


async def fetch_memberships(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch membership transitions from MASTER DB.

    Returns:
        List of membership records with transitions
    """
    try:
        query = db_client.table("memberships").select(
            "id, user_id, yacht_id, status, role_requested, "
            "invited_by, approved_by, notes, created_at, updated_at"
        ).eq("yacht_id", yacht_id)

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        # Redact sensitive fields
        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch memberships: {e}")
        return []


async def fetch_role_changes(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch role change events from security_events.
    """
    try:
        query = db_client.table("security_events").select("*").eq(
            "yacht_id", yacht_id
        ).in_(
            "event_type", [
                "admin_change_role_attempt",
                "admin_change_role_success",
                "admin_change_role_denied_self",
                "admin_change_role_error",
            ]
        )

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch role changes: {e}")
        return []


async def fetch_admin_actions(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch admin action events (invites, approvals, revokes, freezes).
    """
    try:
        admin_event_types = [
            "admin_invite_attempt",
            "admin_invite_success",
            "admin_invite_error",
            "admin_approve_attempt",
            "admin_approve_success",
            "admin_approve_denied_2person",
            "admin_approve_error",
            "admin_revoke_attempt",
            "admin_revoke_success",
            "admin_revoke_error",
            "admin_freeze_attempt",
            "admin_freeze_success",
            "admin_unfreeze_success",
            "admin_freeze_error",
        ]

        query = db_client.table("security_events").select("*").eq(
            "yacht_id", yacht_id
        ).in_("event_type", admin_event_types)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch admin actions: {e}")
        return []


async def fetch_router_audits(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch action router audit entries from pms_audit_log.
    """
    try:
        query = db_client.table("pms_audit_log").select(
            "id, request_id, idempotency_key, user_id, yacht_id, "
            "action_name, outcome, entity_type, entity_id, "
            "payload_hash, created_at"
        ).eq("yacht_id", yacht_id)

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch router audits: {e}")
        return []


async def fetch_storage_signing_events(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch storage signing (signed URL) events.
    """
    try:
        query = db_client.table("pms_audit_log").select(
            "id, request_id, user_id, yacht_id, action_name, "
            "outcome, entity_id, created_at"
        ).eq("yacht_id", yacht_id).in_(
            "action_name", [
                "get_secure_download_url",
                "get_secure_upload_url",
                "delete_document",
            ]
        )

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch storage signing events: {e}")
        return []


async def fetch_incident_events(
    db_client,
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch incident mode toggle events (global, not yacht-scoped).
    """
    try:
        query = db_client.table("security_events").select("*").in_(
            "event_type", [
                "incident_mode_enable_attempt",
                "incident_mode_enabled",
                "incident_mode_disable_attempt",
                "incident_mode_disabled",
            ]
        )

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch incident events: {e}")
        return []


async def fetch_cache_invalidations(
    db_client,
    yacht_id: str,
    user_id: Optional[str],
    start_ts: str,
    end_ts: str,
) -> List[Dict[str, Any]]:
    """
    Fetch cache invalidation events.
    """
    try:
        query = db_client.table("security_events").select("*").in_(
            "event_type", [
                "cache_cleared_user",
                "cache_cleared_yacht",
            ]
        )

        if yacht_id:
            query = query.eq("yacht_id", yacht_id)
        if user_id:
            query = query.eq("user_id", user_id)

        query = query.gte("created_at", start_ts).lte("created_at", end_ts)

        result = query.execute()
        records = result.data or []

        return [_redact_dict(r) for r in records]

    except Exception as e:
        logger.error(f"[AuditExport] Failed to fetch cache invalidations: {e}")
        return []


def _generate_summary(
    memberships: List[Dict],
    role_changes: List[Dict],
    admin_actions: List[Dict],
    router_audits: List[Dict],
    storage_events: List[Dict],
    incident_events: List[Dict],
    cache_events: List[Dict],
) -> List[Dict[str, Any]]:
    """Generate summary statistics."""
    return [
        {
            "category": "memberships",
            "total_records": len(memberships),
            "active_count": sum(1 for m in memberships if m.get("status") == "ACTIVE"),
            "revoked_count": sum(1 for m in memberships if m.get("status") == "REVOKED"),
        },
        {
            "category": "role_changes",
            "total_records": len(role_changes),
            "successful": sum(1 for r in role_changes if "success" in r.get("event_type", "")),
            "denied": sum(1 for r in role_changes if "denied" in r.get("event_type", "")),
        },
        {
            "category": "admin_actions",
            "total_records": len(admin_actions),
            "invites": sum(1 for a in admin_actions if "invite" in a.get("event_type", "")),
            "approvals": sum(1 for a in admin_actions if "approve" in a.get("event_type", "")),
            "revocations": sum(1 for a in admin_actions if "revoke" in a.get("event_type", "")),
            "freezes": sum(1 for a in admin_actions if "freeze" in a.get("event_type", "")),
        },
        {
            "category": "router_audits",
            "total_records": len(router_audits),
            "allowed": sum(1 for r in router_audits if r.get("outcome") == "allowed"),
            "denied": sum(1 for r in router_audits if r.get("outcome") == "denied"),
            "error": sum(1 for r in router_audits if r.get("outcome") == "error"),
        },
        {
            "category": "storage_signing",
            "total_records": len(storage_events),
        },
        {
            "category": "incident_events",
            "total_records": len(incident_events),
            "enabled_count": sum(1 for i in incident_events if "enabled" in i.get("event_type", "")),
            "disabled_count": sum(1 for i in incident_events if "disabled" in i.get("event_type", "")),
        },
        {
            "category": "cache_invalidations",
            "total_records": len(cache_events),
        },
    ]


async def export_audit_trace(
    db_client,
    yacht_id: str,
    start_ts: str,
    end_ts: str,
    out_dir: str,
    user_id: Optional[str] = None,
    git_commit: Optional[str] = None,
    command_args: Optional[str] = None,
) -> str:
    """
    Export complete audit trace for compliance evidence.

    Args:
        db_client: Database client (MASTER or TENANT depending on data)
        yacht_id: Yacht ID to export
        start_ts: Start timestamp (ISO 8601 UTC)
        end_ts: End timestamp (ISO 8601 UTC)
        out_dir: Output directory path
        user_id: Optional user ID filter
        git_commit: Optional git commit hash for reproducibility
        command_args: Optional command-line args for index.json

    Returns:
        Path to the created bundle.zip

    Output structure:
        out_dir/
        ├── index.json
        ├── memberships.jsonl
        ├── role_changes.jsonl
        ├── admin_actions.jsonl
        ├── router_audits.jsonl
        ├── storage_signing.jsonl
        ├── incident_events.jsonl
        ├── cache_invalidations.jsonl
        ├── summary.csv
        ├── README.md
        └── bundle.zip
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    export_timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"[AuditExport] Starting export: yacht={yacht_id}, "
        f"user={user_id or 'all'}, period={start_ts} to {end_ts}"
    )

    # Fetch all data
    memberships = await fetch_memberships(db_client, yacht_id, user_id, start_ts, end_ts)
    role_changes = await fetch_role_changes(db_client, yacht_id, user_id, start_ts, end_ts)
    admin_actions = await fetch_admin_actions(db_client, yacht_id, user_id, start_ts, end_ts)
    router_audits = await fetch_router_audits(db_client, yacht_id, user_id, start_ts, end_ts)
    storage_events = await fetch_storage_signing_events(db_client, yacht_id, user_id, start_ts, end_ts)
    incident_events = await fetch_incident_events(db_client, start_ts, end_ts)
    cache_events = await fetch_cache_invalidations(db_client, yacht_id, user_id, start_ts, end_ts)

    # Generate summary
    summary = _generate_summary(
        memberships, role_changes, admin_actions, router_audits,
        storage_events, incident_events, cache_events,
    )

    # Write JSONL files
    _write_jsonl(out_path / "memberships.jsonl", memberships)
    _write_jsonl(out_path / "role_changes.jsonl", role_changes)
    _write_jsonl(out_path / "admin_actions.jsonl", admin_actions)
    _write_jsonl(out_path / "router_audits.jsonl", router_audits)
    _write_jsonl(out_path / "storage_signing.jsonl", storage_events)
    _write_jsonl(out_path / "incident_events.jsonl", incident_events)
    _write_jsonl(out_path / "cache_invalidations.jsonl", cache_events)

    # Write summary CSV
    _write_csv(
        out_path / "summary.csv",
        summary,
        columns=["category", "total_records", "active_count", "revoked_count",
                 "successful", "denied", "error", "invites", "approvals",
                 "revocations", "freezes", "allowed", "enabled_count", "disabled_count"],
    )

    # Write index.json
    index = {
        "exporter_version": EXPORTER_VERSION,
        "export_timestamp": export_timestamp,
        "git_commit": git_commit,
        "command_args": command_args,
        "parameters": {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
        },
        "files": [
            "memberships.jsonl",
            "role_changes.jsonl",
            "admin_actions.jsonl",
            "router_audits.jsonl",
            "storage_signing.jsonl",
            "incident_events.jsonl",
            "cache_invalidations.jsonl",
            "summary.csv",
            "README.md",
        ],
        "record_counts": {s["category"]: s["total_records"] for s in summary},
        "clock_source": "database",
        "timezone": "UTC",
    }

    with open(out_path / "index.json", "w") as f:
        json.dump(index, f, indent=2)

    # Write README
    readme = f"""# Audit Evidence Bundle

## Export Information
- **Yacht ID**: {yacht_id}
- **User ID**: {user_id or 'All users'}
- **Period**: {start_ts} to {end_ts}
- **Exported**: {export_timestamp}
- **Exporter Version**: {EXPORTER_VERSION}

## Files Included
- `memberships.jsonl` - Membership transitions
- `role_changes.jsonl` - Role change events
- `admin_actions.jsonl` - Admin action audits (invites, approvals, revokes, freezes)
- `router_audits.jsonl` - Action router execution logs
- `storage_signing.jsonl` - Signed URL generation events
- `incident_events.jsonl` - Incident mode toggles
- `cache_invalidations.jsonl` - Cache clear events
- `summary.csv` - Summary statistics
- `index.json` - Export metadata

## Redaction
- Raw payloads are excluded
- Email addresses are hashed
- Sensitive fields (password, secret, token) are removed
- Only payload_hash and safe IDs are included

## Verification
To verify this bundle:
1. Check `index.json` for export parameters
2. Verify record counts match expectations
3. Confirm no raw payloads in JSONL files

## Related Documents
- Evidence Checklist: `docs/compliance/EVIDENCE_CHECKLIST_SOC2_ISO.md`
- Access Review Template: `docs/compliance/QUARTERLY_ACCESS_REVIEW_TEMPLATE.md`
"""

    with open(out_path / "README.md", "w") as f:
        f.write(readme)

    # Create zip bundle
    bundle_path = out_path / "bundle.zip"
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in out_path.iterdir():
            if file.name != "bundle.zip" and file.is_file():
                zf.write(file, file.name)

    logger.info(
        f"[AuditExport] Export complete: {bundle_path}, "
        f"records={sum(s['total_records'] for s in summary)}"
    )

    return str(bundle_path)


# ============================================================================
# Convenience Functions
# ============================================================================

async def generate_access_review_data(
    db_client,
    yacht_id: str,
    start_ts: str,
    end_ts: str,
) -> Dict[str, Any]:
    """
    Generate data for quarterly access review.

    Returns dict with:
    - active_memberships: List of active members
    - privileged_roles: Members with captain/manager/chief_engineer
    - two_person_compliance: Privileged grants with inviter != approver
    - role_changes: Role changes in period
    - revocations: Revocations in period
    """
    memberships = await fetch_memberships(db_client, yacht_id, None, start_ts, end_ts)
    role_changes = await fetch_role_changes(db_client, yacht_id, None, start_ts, end_ts)
    admin_actions = await fetch_admin_actions(db_client, yacht_id, None, start_ts, end_ts)

    active = [m for m in memberships if m.get("status") == "ACTIVE"]
    privileged = [
        m for m in active
        if m.get("role_requested") in ("captain", "manager", "chief_engineer")
    ]

    # Check 2-person compliance
    two_person = []
    for m in privileged:
        inviter = m.get("invited_by")
        approver = m.get("approved_by")
        two_person.append({
            "user_id": m.get("user_id"),
            "role": m.get("role_requested"),
            "invited_by": inviter,
            "approved_by": approver,
            "compliant": inviter != approver if inviter and approver else False,
        })

    revocations = [
        a for a in admin_actions
        if "revoke_success" in a.get("event_type", "")
    ]

    return {
        "yacht_id": yacht_id,
        "period": {"start": start_ts, "end": end_ts},
        "active_memberships": active,
        "privileged_roles": privileged,
        "two_person_compliance": two_person,
        "role_changes": role_changes,
        "revocations": revocations,
        "summary": {
            "total_active": len(active),
            "total_privileged": len(privileged),
            "two_person_violations": sum(1 for t in two_person if not t["compliant"]),
            "role_changes_count": len(role_changes),
            "revocations_count": len(revocations),
        },
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "export_audit_trace",
    "generate_access_review_data",
    "EXPORTER_VERSION",
]
