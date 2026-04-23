"""
Certificate Domain Handlers
===========================

Handlers for certificate actions (Certificate Lens v2).

READ Handlers:
- list_vessel_certificates: List vessel/flag certificates
- list_crew_certificates: List crew/seafarer certificates
- get_certificate_details: View certificate details
- view_certificate_history: Audit history of changes
- find_expiring_certificates: Certificates expiring within time range

MUTATION Handlers (require confirmation via action_gating):
- create_vessel_certificate: Create new vessel certificate
- create_crew_certificate: Create new crew certificate
- update_certificate: Update certificate details
- link_document_to_certificate: Link document to certificate
- supersede_certificate: Supersede certificate (SIGNED action)
- delete_certificate: Delete certificate (Manager-only)

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging
import json
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
)

from .schema_mapping import (
    get_table,
    map_vessel_certificate_select,
    normalize_vessel_certificate,
    map_crew_certificate_select,
    normalize_crew_certificate,
)

logger = logging.getLogger(__name__)


# Certificate status flow
CERTIFICATE_STATUS_FLOW = {
    "draft": ["active"],
    "active": ["superseded", "expired", "revoked"],
    "superseded": [],       # Terminal state
    "expired": ["active"],  # Can be renewed
    "revoked": [],          # Terminal state
}

# Certificate types for vessel certificates
VESSEL_CERTIFICATE_TYPES = [
    "ISM", "ISPS", "SOLAS", "MLC", "CLASS", "FLAG",
    "SEC", "SRC", "SCC", "LOAD_LINE", "TONNAGE", "MARPOL", "IOPP"
]

# Certificate types for crew certificates
CREW_CERTIFICATE_TYPES = [
    "STCW", "ENG1", "COC", "GMDSS", "BST", "PSC", "AFF", "MEDICAL_CARE"
]


class CertificateHandlers:
    """
    Certificate domain handlers.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    def _ledger_read(self, yacht_id: str, user_id: str, user_role: str,
                     action: str, entity_id: str = None, summary: str = None) -> None:
        """
        Write a view-type ledger event for certificate read operations.
        Fire-and-forget — never raises, never blocks the read response.
        """
        try:
            import hashlib
            now = datetime.now(timezone.utc).isoformat()
            proof_input = f"{yacht_id}{entity_id or ''}{action}{now}"
            proof_hash = hashlib.sha256(proof_input.encode()).hexdigest()
            self.db.table("ledger_events").insert({
                "yacht_id": yacht_id,
                "event_type": "view",
                "entity_type": "certificate",
                "entity_id": entity_id or yacht_id,
                "action": action,
                "user_id": user_id or "00000000-0000-0000-0000-000000000000",
                "user_role": user_role or "unknown",
                "change_summary": summary or action.replace("_", " ").capitalize(),
                "source_context": "microaction",
                "proof_hash": proof_hash,
                "event_timestamp": now,
                "created_at": now,
            }).execute()
        except Exception:
            pass  # Never block a read because of a ledger write failure

    # =========================================================================
    # READ HANDLERS
    # =========================================================================

    async def list_vessel_certificates(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        List all vessel certificates.

        Returns:
        - List of vessel certificates with status indicators
        - Expiry warnings for certificates expiring soon
        """
        builder = ResponseBuilder("list_vessel_certificates", entity_id, "vessel_certificate", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)
            status_filter = params.get("status")
            cert_type_filter = params.get("certificate_type")

            self._ledger_read(yacht_id, params.get("user_id"), params.get("user_role"),
                               "list_vessel_certificates", entity_id or yacht_id,
                               "Viewed vessel certificate list")

            # Refresh expired status before listing (lazy expiry evaluation)
            try:
                self.db.rpc("refresh_certificate_expiry", {"p_yacht_id": yacht_id}).execute()
            except Exception:
                pass

            # Build query
            query = self.db.table(get_table("vessel_certificates")).select(
                map_vessel_certificate_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if status_filter:
                query = query.eq("status", status_filter)
            if cert_type_filter:
                query = query.eq("certificate_type", cert_type_filter)

            # Execute with pagination
            result = query.order("expiry_date").range(offset, offset + limit - 1).execute()

            certificates = result.data or []
            total_count = result.count or len(certificates)

            # Add computed fields
            for cert in certificates:
                cert = normalize_vessel_certificate(cert)
                cert["is_expiring_soon"] = self._is_expiring_soon(cert.get("expiry_date"))
                cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
                cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))

            builder.set_data({
                "certificates": certificates,
                "certificate_types": VESSEL_CERTIFICATE_TYPES,
            })

            builder.set_pagination(offset, limit, total_count)

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="create_vessel_certificate",
                label="New Certificate",
                variant="MUTATE",
                icon="plus",
                is_primary=True
            ))
            builder.add_available_action(AvailableAction(
                action_id="find_expiring_certificates",
                label="Expiring Soon",
                variant="READ",
                icon="alert-triangle"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"list_vessel_certificates failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def list_crew_certificates(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        List all crew certificates.

        Returns:
        - List of crew certificates grouped by person
        - Expiry warnings for certificates expiring soon
        """
        builder = ResponseBuilder("list_crew_certificates", entity_id, "crew_certificate", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)
            person_filter = params.get("person_name")
            cert_type_filter = params.get("certificate_type")

            self._ledger_read(yacht_id, params.get("user_id"), params.get("user_role"),
                               "list_crew_certificates", entity_id or yacht_id,
                               "Viewed crew certificate list")

            # Refresh expired status before listing (lazy expiry evaluation)
            try:
                self.db.rpc("refresh_certificate_expiry", {"p_yacht_id": yacht_id}).execute()
            except Exception:
                pass

            # Build query
            query = self.db.table(get_table("crew_certificates")).select(
                map_crew_certificate_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if person_filter:
                query = query.ilike("person_name", f"%{person_filter}%")
            if cert_type_filter:
                query = query.eq("certificate_type", cert_type_filter)

            # Execute with pagination
            result = query.order("person_name").order("expiry_date").range(offset, offset + limit - 1).execute()

            certificates = result.data or []
            total_count = result.count or len(certificates)

            # Add computed fields
            for cert in certificates:
                cert = normalize_crew_certificate(cert)
                cert["is_expiring_soon"] = self._is_expiring_soon(cert.get("expiry_date"))
                cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
                cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))

            builder.set_data({
                "certificates": certificates,
                "certificate_types": CREW_CERTIFICATE_TYPES,
            })

            builder.set_pagination(offset, limit, total_count)

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="create_crew_certificate",
                label="New Certificate",
                variant="MUTATE",
                icon="plus",
                is_primary=True
            ))
            builder.add_available_action(AvailableAction(
                action_id="find_expiring_certificates",
                label="Expiring Soon",
                variant="READ",
                icon="alert-triangle"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"list_crew_certificates failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def get_certificate_details(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Get certificate details.

        Works for both vessel and crew certificates.
        Determines type from entity_id prefix or params.
        """
        params = params or {}
        cert_domain = params.get("domain", "vessel")  # "vessel" or "crew"

        self._ledger_read(yacht_id, params.get("user_id"), params.get("user_role"),
                           "get_certificate_details", entity_id,
                           f"Viewed {cert_domain} certificate detail")

        if cert_domain == "crew":
            return await self._get_crew_certificate_details(entity_id, yacht_id, params)
        else:
            return await self._get_vessel_certificate_details(entity_id, yacht_id, params)

    async def _get_vessel_certificate_details(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """Get vessel certificate details."""
        builder = ResponseBuilder("get_certificate_details", entity_id, "vessel_certificate", yacht_id)

        try:
            result = self.db.table(get_table("vessel_certificates")).select(
                map_vessel_certificate_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Vessel certificate not found: {entity_id}")
                return builder.build()

            cert = normalize_vessel_certificate(result.data)

            # Add computed fields
            cert["is_expiring_soon"] = self._is_expiring_soon(cert.get("expiry_date"))
            cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
            cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))
            cert["allowed_transitions"] = CERTIFICATE_STATUS_FLOW.get(cert.get("status", "draft"), [])

            builder.set_data(cert)

            # Get linked document
            if cert.get("document_id"):
                files = await self._get_certificate_document(cert["document_id"])
                if files:
                    builder.add_files(files)

            # Add available actions based on status
            builder.add_available_actions(self._get_certificate_actions(cert, "vessel"))

            return builder.build()

        except Exception as e:
            logger.error(f"get_certificate_details (vessel) failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def _get_crew_certificate_details(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """Get crew certificate details."""
        builder = ResponseBuilder("get_certificate_details", entity_id, "crew_certificate", yacht_id)

        try:
            result = self.db.table(get_table("crew_certificates")).select(
                map_crew_certificate_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Crew certificate not found: {entity_id}")
                return builder.build()

            cert = normalize_crew_certificate(result.data)

            # Add computed fields
            cert["is_expiring_soon"] = self._is_expiring_soon(cert.get("expiry_date"))
            cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
            cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))
            cert["allowed_transitions"] = CERTIFICATE_STATUS_FLOW.get(cert.get("status", "draft"), [])

            builder.set_data(cert)

            # Get linked document
            if cert.get("document_id"):
                files = await self._get_certificate_document(cert["document_id"])
                if files:
                    builder.add_files(files)

            # Add available actions based on status
            builder.add_available_actions(self._get_certificate_actions(cert, "crew"))

            return builder.build()

        except Exception as e:
            logger.error(f"get_certificate_details (crew) failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_certificate_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View certificate audit history.

        Returns:
        - List of changes/events for this certificate
        - Who made changes and when
        - Signature payloads for signed actions
        """
        params = params or {}
        cert_domain = params.get("domain", "vessel")
        entity_type = "vessel_certificate" if cert_domain == "vessel" else "crew_certificate"

        self._ledger_read(yacht_id, params.get("user_id"), params.get("user_role"),
                           "view_certificate_history", entity_id,
                           f"Viewed {cert_domain} certificate audit history")

        builder = ResponseBuilder("view_certificate_history", entity_id, entity_type, yacht_id)

        try:
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)

            # Query audit log for this certificate
            history = []
            total_count = 0
            try:
                result = self.db.table(get_table("audit_log")).select(
                    "id, action, old_values, new_values, created_at, user_id, signature",
                    count="exact"
                ).eq("entity_type", entity_type).eq(
                    "entity_id", entity_id
                ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

                entries = result.data or []
                total_count = result.count or len(entries)

                for entry in entries:
                    history.append({
                        "id": entry.get("id"),
                        "action": entry.get("action"),
                        "changes": self._format_changes(entry.get("old_values"), entry.get("new_values")),
                        "user_name": "System",  # Simplified - no FK join
                        "timestamp": entry.get("created_at"),
                        "is_signed": entry.get("signature") != "{}" and entry.get("signature") is not None,
                    })
            except Exception as table_err:
                logger.debug(f"audit_log table not available: {table_err}")

            builder.set_data({
                "certificate_id": entity_id,
                "domain": cert_domain,
                "history": history,
                "message": "Audit log not configured" if not history else None
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_certificate_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def find_expiring_certificates(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Find certificates expiring within a time range.

        Params:
        - days_ahead: Number of days to look ahead (default: 90)
        - domain: "vessel", "crew", or "all" (default: "all")
        """
        builder = ResponseBuilder("find_expiring_certificates", entity_id, "certificate", yacht_id)

        try:
            params = params or {}
            days_ahead = params.get("days_ahead", 90)
            domain = params.get("domain", "all")

            self._ledger_read(yacht_id, params.get("user_id"), params.get("user_role"),
                               "find_expiring_certificates", entity_id or yacht_id,
                               f"Queried expiring certificates ({days_ahead}d, domain={domain})")

            now = datetime.now(timezone.utc)
            cutoff_date = now + timedelta(days=days_ahead)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")

            expiring = []

            # Query vessel certificates
            if domain in ("vessel", "all"):
                try:
                    result = self.db.table(get_table("vessel_certificates")).select(
                        "id, certificate_type, certificate_name, expiry_date, status"
                    ).eq("yacht_id", yacht_id).lt(
                        "expiry_date", cutoff_str
                    ).neq("status", "superseded").neq("status", "revoked").order("expiry_date").execute()

                    for cert in (result.data or []):
                        cert["domain"] = "vessel"
                        cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))
                        cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
                        expiring.append(cert)
                except Exception as e:
                    logger.warning(f"Failed to query vessel certificates: {e}")

            # Query crew certificates
            if domain in ("crew", "all"):
                try:
                    result = self.db.table(get_table("crew_certificates")).select(
                        "id, certificate_type, person_name, expiry_date"
                    ).eq("yacht_id", yacht_id).lt(
                        "expiry_date", cutoff_str
                    ).order("expiry_date").execute()

                    for cert in (result.data or []):
                        cert["domain"] = "crew"
                        cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))
                        cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
                        expiring.append(cert)
                except Exception as e:
                    logger.warning(f"Failed to query crew certificates: {e}")

            # Sort by expiry date (already expired first, then by days)
            expiring.sort(key=lambda c: c.get("expiry_date") or "9999-12-31")

            # Group by urgency
            expired = [c for c in expiring if c.get("is_expired")]
            expiring_30 = [c for c in expiring if not c.get("is_expired") and (c.get("days_until_expiry") or 999) <= 30]
            expiring_90 = [c for c in expiring if not c.get("is_expired") and 30 < (c.get("days_until_expiry") or 999) <= 90]

            builder.set_data({
                "days_ahead": days_ahead,
                "domain": domain,
                "total_expiring": len(expiring),
                "expired": expired,
                "expiring_within_30_days": expiring_30,
                "expiring_within_90_days": expiring_90,
                "all_expiring": expiring,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"find_expiring_certificates failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _is_expiring_soon(self, expiry_date: Optional[str], days: int = 90) -> bool:
        """Check if certificate is expiring within specified days."""
        if not expiry_date:
            return False

        try:
            expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) + timedelta(days=days)
            return expiry <= cutoff
        except Exception:
            return False

    def _is_expired(self, expiry_date: Optional[str]) -> bool:
        """Check if certificate is expired."""
        if not expiry_date:
            return False

        try:
            expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expiry
        except Exception:
            return False

    def _days_until_expiry(self, expiry_date: Optional[str]) -> Optional[int]:
        """Calculate days until certificate expires."""
        if not expiry_date:
            return None

        try:
            expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            delta = expiry - datetime.now(timezone.utc)
            return delta.days
        except Exception:
            return None

    async def _get_certificate_document(self, document_id: str) -> List[Dict]:
        """Get document file linked to certificate."""
        files = []

        if not self.url_generator or not document_id:
            return files

        try:
            # doc_metadata uses: filename (text), content_type (text), storage_path (text)
            result = self.db.table("doc_metadata").select(
                "id, filename, storage_path, content_type"
            ).eq("id", document_id).maybe_single().execute()

            if result.data:
                doc = result.data
                file_ref = self.url_generator.create_file_reference(
                    bucket="documents",
                    path=doc.get("storage_path", ""),
                    filename=doc.get("filename", "document"),
                    file_id=doc["id"],
                    mime_type=doc.get("content_type", "application/pdf"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())
        except Exception as e:
            logger.warning(f"Failed to get certificate document: {e}")

        return files

    def _format_changes(self, old_values: Optional[Dict], new_values: Optional[Dict]) -> List[Dict]:
        """Format change diff for display."""
        if not old_values and not new_values:
            return []

        changes = []
        old = old_values or {}
        new = new_values or {}

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            if old.get(key) != new.get(key):
                changes.append({
                    "field": key,
                    "from": old.get(key),
                    "to": new.get(key)
                })

        return changes

    def _get_certificate_actions(self, cert: Dict, domain: str) -> List[AvailableAction]:
        """Get available actions based on certificate status."""
        status = cert.get("status", "draft")
        allowed_transitions = cert.get("allowed_transitions", [])

        actions = []

        # View history always available
        actions.append(AvailableAction(
            action_id="view_certificate_history",
            label="View History",
            variant="READ",
            icon="history"
        ))

        # Link document (vessel certs only — documents don't apply to crew cert domain)
        if domain == "vessel" and not cert.get("document_id"):
            actions.append(AvailableAction(
                action_id="link_document_to_certificate",
                label="Link Document",
                variant="MUTATE",
                icon="paperclip"
            ))

        # Status-based actions

        if status not in ("superseded", "revoked"):
            # Update action
            actions.append(AvailableAction(
                action_id="update_certificate",
                label="Update",
                variant="MUTATE",
                icon="edit"
            ))

        # Renew (not for terminal states)
        if status not in ("superseded", "revoked"):
            actions.append(AvailableAction(
                action_id="renew_certificate",
                label="Renew",
                variant="MUTATE",
                icon="refresh-cw"
            ))

        # Add note (always available)
        actions.append(AvailableAction(
            action_id="add_certificate_note",
            label="Add Note",
            variant="MUTATE",
            icon="message-square"
        ))

        # Danger zone (not for terminal states)
        if status not in ("superseded", "revoked"):
            actions.append(AvailableAction(
                action_id="suspend_certificate",
                label="Suspend",
                variant="SIGNED",
                icon="pause-circle",
                requires_signature=True,
                confirmation_message="This will suspend this certificate. This action is logged."
            ))
            actions.append(AvailableAction(
                action_id="revoke_certificate",
                label="Revoke",
                variant="SIGNED",
                icon="x-circle",
                requires_signature=True,
                confirmation_message="This will permanently revoke this certificate. This action is logged and cannot be undone."
            ))

        # Archive (always available, soft-delete)
        actions.append(AvailableAction(
            action_id="archive_certificate",
            label="Archive",
            variant="SIGNED",
            icon="archive",
            requires_signature=True,
            confirmation_message="This will archive this certificate record."
        ))

        # Delete action (for draft or manager-only)
        if status == "draft":
            actions.append(AvailableAction(
                action_id="delete_certificate",
                label="Delete",
                variant="MUTATE",
                icon="trash-2",
                confirmation_message="This will permanently delete this certificate record."
            ))

        return actions


def get_certificate_handlers(supabase_client) -> Dict[str, callable]:
    """Get certificate handler functions for registration."""
    handlers = CertificateHandlers(supabase_client)

    _suspend = _change_certificate_status_adapter("suspended")(handlers)
    _revoke = _change_certificate_status_adapter("revoked")(handlers)

    return {
        # READ handlers
        "list_vessel_certificates": handlers.list_vessel_certificates,
        "list_crew_certificates": handlers.list_crew_certificates,
        "get_certificate_details": handlers.get_certificate_details,
        "view_certificate_history": handlers.view_certificate_history,
        "find_expiring_certificates": handlers.find_expiring_certificates,

        # MUTATION handlers
        "create_vessel_certificate": _create_vessel_certificate_adapter(handlers),
        "create_crew_certificate": _create_crew_certificate_adapter(handlers),
        "update_certificate": _update_certificate_adapter(handlers),
        "link_document_to_certificate": _link_document_to_certificate_adapter(handlers),
        "supersede_certificate": _supersede_certificate_adapter(handlers),
        "renew_certificate": _renew_certificate_adapter(handlers),
        "suspend_certificate": _suspend,
        "revoke_certificate": _revoke,
        "archive_certificate": _archive_certificate_adapter(handlers),
        "assign_certificate": _assign_certificate_adapter(handlers),
    }


# =============================================================================
# MUTATION ADAPTERS (thin wrappers that align with Action Router param shape)
# =============================================================================

def _create_vessel_certificate_adapter(handlers: CertificateHandlers):
    async def _fn(**params):
        """
        Create a vessel certificate.

        Expected params (validated upstream by action router/config):
        - yacht_id (str)
        - user_id (str)
        - certificate_type (str)
        - certificate_name (str)
        - issuing_authority (str)
        - certificate_number (str, optional)
        - issue_date (str, optional, ISO date)
        - expiry_date (str, optional, ISO date)
        - last_survey_date (str, optional)
        - next_survey_due (str, optional)
        - document_id (str, optional)
        - properties (dict, optional)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]

        payload = {
            "yacht_id": yacht_id,
            "certificate_type": params["certificate_type"],
            "certificate_name": params["certificate_name"],
            "certificate_number": params.get("certificate_number") or None,
            "issuing_authority": params["issuing_authority"],
            "issue_date": params.get("issue_date") or None,
            "expiry_date": params.get("expiry_date") or None,
            "last_survey_date": params.get("last_survey_date") or None,
            "next_survey_due": params.get("next_survey_due") or None,
            "status": "valid",
            "document_id": params.get("document_id"),
            "properties": params.get("properties") or {},
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Insert certificate (RLS enforces yacht + role via policies)
        ins = db.table(get_table("vessel_certificates")).insert(payload).execute()
        new_id = (ins.data or [{}])[0].get("id")
        if not new_id:
            raise ValueError("Insert did not return id for vessel certificate")

        # Audit log (signature invariant: {})
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "certificate",
            "entity_id": new_id,
            "action": "create_vessel_certificate",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                k: v
                for k, v in payload.items()
                if k
                in (
                    "certificate_type",
                    "certificate_name",
                    "certificate_number",
                    "issuing_authority",
                    "issue_date",
                    "expiry_date",
                )
            },
            "signature": {},
            "metadata": {"source": "certificate_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            # Do not fail the main operation if audit insert throws; log upstream
            pass

        _notify_cert_stakeholders(db, yacht_id, new_id,
            params.get("certificate_name") or "Certificate",
            "created", user_id, "vessel")

        return {
            "status": "success",
            "certificate_id": new_id,
        }

    return _fn


def _link_document_to_certificate_adapter(handlers: CertificateHandlers):
    async def _fn(**params):
        """
        Link a document to a certificate (vessel or crew).

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - certificate_id (str)
        - domain (str) -> "vessel" | "crew" (default vessel)
        - document_id (str)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params["certificate_id"]
        document_id = params["document_id"]

        # Auto-detect domain from the actual cert row (don't trust client)
        domain, table_key, _cert_row = _resolve_cert_domain(db, yacht_id, cert_id)
        _cert_mutation_gate(domain, params.get("role", ""), "link_document_to_certificate")
        table = get_table(table_key)

        # Basic existence checks (defensive against client return shapes)
        try:
            dm = db.table("doc_metadata").select("id").eq("id", document_id).maybe_single().execute()
        except Exception:
            dm = None
        if not getattr(dm, 'data', None):
            raise ValueError("document_id not found")

        res = db.table(table).update({"document_id": document_id}).eq("yacht_id", yacht_id).eq("id", cert_id).execute()
        if (res.data or [{}])[0].get("id") != cert_id:
            raise ValueError("certificate update failed or not permitted by RLS")

        # Audit (non-signed)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "certificate",
            "entity_id": cert_id,
            "action": "link_document",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"document_id": document_id},
            "signature": {},
            "metadata": {"source": "certificate_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "certificate_id": cert_id,
            "document_id": document_id,
        }

    return _fn


def _update_certificate_adapter(handlers: CertificateHandlers):
    async def _fn(**params):
        """
        Update a certificate (vessel or crew).

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - certificate_id (str)
        - domain (str) -> "vessel" | "crew" (default vessel)
        - certificate_name (str, optional)
        - certificate_number (str, optional)
        - issuing_authority (str, optional)
        - issue_date (str, optional, ISO date)
        - expiry_date (str, optional, ISO date)
        - last_survey_date (str, optional) - vessel only
        - next_survey_due (str, optional) - vessel only
        - properties (dict, optional)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params["certificate_id"]

        # Auto-detect domain from the actual cert row
        domain, table_key, old_values = _resolve_cert_domain(db, yacht_id, cert_id)
        _cert_mutation_gate(domain, params.get("role", ""), "update_certificate")
        table = get_table(table_key)

        # Don't allow updates to superseded/revoked certificates
        if old_values.get("status") in ("superseded", "revoked"):
            raise ValueError(f"Cannot update certificate with status '{old_values.get('status')}'")

        # Build update payload (only include fields that are provided)
        update_fields = {}
        audit_fields = {}

        updatable = [
            "certificate_name", "certificate_number", "issuing_authority",
            "issue_date", "expiry_date", "properties"
        ]
        if domain == "vessel":
            updatable.extend(["last_survey_date", "next_survey_due"])

        for field in updatable:
            if field in params and params[field] is not None:
                update_fields[field] = params[field]
                audit_fields[field] = params[field]

        if not update_fields:
            raise ValueError("No fields to update")

        # Date validation: expiry_date must be after issue_date
        issue_date = update_fields.get("issue_date") or old_values.get("issue_date")
        expiry_date = update_fields.get("expiry_date") or old_values.get("expiry_date")
        if issue_date and expiry_date and expiry_date < issue_date:
            raise ValueError("expiry_date must be after issue_date")

        # Update certificate
        res = db.table(table).update(update_fields).eq("yacht_id", yacht_id).eq("id", cert_id).execute()
        if not res.data:
            raise ValueError("Update failed or not permitted by RLS")

        # Audit log (non-signed)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "certificate",
            "entity_id": cert_id,
            "action": "update_certificate",
            "user_id": user_id,
            "old_values": {k: old_values.get(k) for k in audit_fields.keys()},
            "new_values": audit_fields,
            "signature": {},
            "metadata": {"source": "certificate_lens", "domain": domain},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "certificate_id": cert_id,
            "updated_fields": list(update_fields.keys()),
        }

    return _fn


def _create_crew_certificate_adapter(handlers: CertificateHandlers):
    async def _fn(**params):
        """
        Create a crew certificate.

        Expected params (validated upstream by action router/config):
        - yacht_id (str)
        - user_id (str)
        - person_name (str)
        - person_node_id (str, optional) - reference to crew member node
        - certificate_type (str) - STCW, ENG1, COC, GMDSS, etc.
        - certificate_number (str, optional)
        - issuing_authority (str)
        - issue_date (str, optional, ISO date)
        - expiry_date (str, optional, ISO date)
        - document_id (str, optional)
        - properties (dict, optional)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]

        # Validate required fields
        if not params.get("person_name"):
            raise ValueError("person_name is required for crew certificates")
        if not params.get("certificate_type"):
            raise ValueError("certificate_type is required")
        if not params.get("issuing_authority"):
            raise ValueError("issuing_authority is required")

        payload = {
            "yacht_id": yacht_id,
            "person_name": params["person_name"],
            "person_node_id": params.get("person_node_id"),
            "certificate_type": params["certificate_type"],
            "certificate_number": params.get("certificate_number"),
            "issuing_authority": params["issuing_authority"],
            "issue_date": params.get("issue_date"),
            "expiry_date": params.get("expiry_date"),
            "document_id": params.get("document_id"),
            "properties": params.get("properties") or {},
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Insert certificate (RLS enforces yacht + role via policies)
        ins = db.table(get_table("crew_certificates")).insert(payload).execute()
        new_id = (ins.data or [{}])[0].get("id")
        if not new_id:
            raise ValueError("Insert did not return id for crew certificate")

        # Audit log (signature invariant: {})
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "certificate",
            "entity_id": new_id,
            "action": "create_crew_certificate",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                k: v
                for k, v in payload.items()
                if k in (
                    "person_name",
                    "certificate_type",
                    "certificate_number",
                    "issuing_authority",
                    "issue_date",
                    "expiry_date",
                )
            },
            "signature": {},
            "metadata": {"source": "certificate_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        _notify_cert_stakeholders(db, yacht_id, new_id,
            params.get("person_name") or "Certificate",
            "created", user_id, "crew")

        return {
            "status": "success",
            "certificate_id": new_id,
            "person_name": params["person_name"],
        }

    return _fn


def _supersede_certificate_adapter(handlers: CertificateHandlers):
    async def _fn(**params):
        """
        Supersede a certificate (SIGNED action).

        This is a compliance-critical action that:
        1. Marks the old certificate as 'superseded' (terminal state)
        2. Optionally creates a new 'valid' certificate
        3. Records a SIGNED audit entry with signature payload

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - certificate_id (str) - the certificate being superseded
        - domain (str) -> "vessel" | "crew" (default vessel)
        - reason (str) - reason for supersession (required)
        - signature (dict) - signature payload (REQUIRED for signed actions)
        - new_certificate (dict, optional) - if provided, creates replacement certificate
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params["certificate_id"]
        domain = (params.get("domain") or "vessel").lower()
        reason = params.get("reason")
        signature = params.get("signature")

        # Parse signature if it's a JSON string
        if isinstance(signature, str):
            try:
                signature = json.loads(signature)
            except json.JSONDecodeError:
                raise ValueError("signature must be valid JSON")

        # Validate required fields
        if not reason:
            raise ValueError("reason is required for supersede action")
        if not signature or signature == {}:
            raise ValueError("signature payload is required for supersede action (signed action)")

        table = get_table("vessel_certificates" if domain == "vessel" else "crew_certificates")

        # Get current certificate
        current = db.table(table).select("*").eq("yacht_id", yacht_id).eq("id", cert_id).maybe_single().execute()
        if not current.data:
            raise ValueError(f"Certificate not found or access denied: {cert_id}")

        old_cert = current.data

        # Cannot supersede already terminal certificates
        if old_cert.get("status") in ("superseded", "revoked"):
            raise ValueError(f"Cannot supersede certificate with status '{old_cert.get('status')}' (terminal state)")

        # Mark old certificate as superseded
        supersede_update = {
            "status": "superseded",
            "properties": {
                **(old_cert.get("properties") or {}),
                "superseded_at": datetime.now(timezone.utc).isoformat(),
                "superseded_by": user_id,
                "supersede_reason": reason,
            }
        }

        res = db.table(table).update(supersede_update).eq("yacht_id", yacht_id).eq("id", cert_id).execute()
        if not res.data:
            raise ValueError("Supersede update failed or not permitted by RLS")

        # Create new certificate if provided
        new_cert_id = None
        if params.get("new_certificate"):
            new_cert_data = params["new_certificate"]
            new_payload = {
                "yacht_id": yacht_id,
                "certificate_type": new_cert_data.get("certificate_type") or old_cert.get("certificate_type"),
                "issuing_authority": new_cert_data.get("issuing_authority") or old_cert.get("issuing_authority"),
                "status": "valid",
                "properties": {
                    **(new_cert_data.get("properties") or {}),
                    "supersedes": cert_id,
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Domain-specific fields
            if domain == "vessel":
                new_payload["certificate_name"] = new_cert_data.get("certificate_name") or old_cert.get("certificate_name")
                new_payload["certificate_number"] = new_cert_data.get("certificate_number")
                new_payload["issue_date"] = new_cert_data.get("issue_date")
                new_payload["expiry_date"] = new_cert_data.get("expiry_date")
                new_payload["last_survey_date"] = new_cert_data.get("last_survey_date")
                new_payload["next_survey_due"] = new_cert_data.get("next_survey_due")
            else:
                new_payload["person_name"] = new_cert_data.get("person_name") or old_cert.get("person_name")
                new_payload["person_node_id"] = new_cert_data.get("person_node_id") or old_cert.get("person_node_id")
                new_payload["certificate_number"] = new_cert_data.get("certificate_number")
                new_payload["issue_date"] = new_cert_data.get("issue_date")
                new_payload["expiry_date"] = new_cert_data.get("expiry_date")

            ins = db.table(table).insert(new_payload).execute()
            new_cert_id = (ins.data or [{}])[0].get("id")

        # SIGNED audit log entry (signature is NOT empty)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "certificate",
            "entity_id": cert_id,
            "action": "supersede_certificate",
            "user_id": user_id,
            "old_values": {
                "status": old_cert.get("status"),
                "certificate_type": old_cert.get("certificate_type"),
            },
            "new_values": {
                "status": "superseded",
                "reason": reason,
                "new_certificate_id": new_cert_id,
            },
            "signature": signature,  # SIGNED - non-empty payload
            "metadata": {
                "source": "certificate_lens",
                "domain": domain,
                "is_signed_action": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "superseded_certificate_id": cert_id,
            "new_certificate_id": new_cert_id,
            "reason": reason,
            "is_signed": True,
        }

    return _fn


def _resolve_cert_domain(db, yacht_id: str, cert_id: str) -> tuple:
    """
    Auto-detect which table a certificate belongs to.
    Returns (domain, table_key, row_data) or raises ValueError if not found.

    Uses .execute() with limit(1) instead of maybe_single() because
    maybe_single() returns None (not a response object) when no row matches
    in this supabase client version, causing AttributeError on .data access.
    """
    for domain, table_key in [("vessel", "vessel_certificates"), ("crew", "crew_certificates")]:
        result = db.table(get_table(table_key)).select("*").eq("yacht_id", yacht_id).eq("id", cert_id).limit(1).execute()
        rows = getattr(result, "data", None) or []
        if rows:
            return domain, table_key, rows[0]
    raise ValueError(f"Certificate {cert_id} not found or access denied")


# ── Domain-based role narrowing ──────────────────────────────────────────
# The registry allows the full 8-HOD union so the action appears in the
# dropdown for any HOD. This gate narrows at handler level: engineering
# roles can only mutate vessel certs, interior roles can only mutate crew
# certs. Captain + manager pass unconditionally.

_VESSEL_CERT_ROLES = frozenset({"engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"})
_CREW_CERT_ROLES = frozenset({"chief_engineer", "chief_officer", "purser", "chief_steward", "captain", "manager"})


def _cert_mutation_gate(domain: str, user_role: str, action: str) -> None:
    """Raise ValueError if user_role cannot mutate a cert in this domain."""
    if user_role in ("captain", "manager"):
        return  # always allowed
    if domain == "vessel" and user_role not in _VESSEL_CERT_ROLES:
        raise ValueError(f"Role '{user_role}' cannot modify vessel certificates")
    if domain == "crew" and user_role not in _CREW_CERT_ROLES:
        raise ValueError(f"Role '{user_role}' cannot modify crew certificates")


def _renew_certificate_adapter(handlers: "CertificateHandlers"):
    async def _fn(**params):
        """
        Renew a certificate: mark old as superseded, create new with updated dates.

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - certificate_id (str) — the certificate being renewed
        - new_issue_date (str, ISO date)
        - new_expiry_date (str, ISO date)
        - new_certificate_number (str, optional)
        - new_issuing_authority (str, optional)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params["certificate_id"]
        new_issue_date = params.get("new_issue_date")
        new_expiry_date = params.get("new_expiry_date")

        if not new_issue_date or not new_expiry_date:
            raise ValueError("new_issue_date and new_expiry_date are required")
        if new_expiry_date <= new_issue_date:
            raise ValueError("new_expiry_date must be after new_issue_date")

        domain, table_key, old_cert = _resolve_cert_domain(db, yacht_id, cert_id)
        _cert_mutation_gate(domain, params.get("role", ""), "renew_certificate")
        table = get_table(table_key)

        if old_cert.get("status") in ("superseded", "revoked"):
            raise ValueError(f"Cannot renew a certificate with status '{old_cert.get('status')}'")

        now = datetime.now(timezone.utc).isoformat()

        # Build new cert payload — copy all non-date fields from old cert
        exclude = {"id", "created_at", "updated_at", "status", "deleted_at", "deleted_by",
                   "issue_date", "expiry_date", "certificate_number", "issuing_authority",
                   "last_survey_date", "next_survey_due", "is_seed", "source_id",
                   "imported_at", "import_session_id"}
        new_payload = {k: v for k, v in old_cert.items() if k not in exclude and v is not None}
        new_payload.update({
            "yacht_id": yacht_id,
            "status": "valid",
            "issue_date": new_issue_date,
            "expiry_date": new_expiry_date,
            "certificate_number": params.get("new_certificate_number") or f"{old_cert.get('certificate_number', 'CERT')}-R{now[:10].replace('-', '')}",
            "issuing_authority": params.get("new_issuing_authority") or old_cert.get("issuing_authority"),
            "source": "manual",
            "is_seed": False,
            "created_at": now,
            "properties": {
                **(old_cert.get("properties") or {}),
                "renews": cert_id,
                "renewed_at": now,
            },
        })
        if domain == "vessel":
            new_payload["last_survey_date"] = params.get("new_last_survey_date")
            new_payload["next_survey_due"] = params.get("new_next_survey_due")

        ins = db.table(table).insert(new_payload).execute()
        new_id = (ins.data or [{}])[0].get("id")
        if not new_id:
            raise ValueError("Renewal insert did not return id")

        # Mark old cert as superseded
        db.table(table).update({
            "status": "superseded",
            "properties": {
                **(old_cert.get("properties") or {}),
                "superseded_at": now,
                "superseded_by_renewal": new_id,
            },
        }).eq("yacht_id", yacht_id).eq("id", cert_id).execute()

        # Audit log
        try:
            db.table("pms_audit_log").insert({
                "yacht_id": yacht_id,
                "entity_type": "certificate",
                "entity_id": cert_id,
                "action": "renew_certificate",
                "user_id": user_id,
                "old_values": {"status": old_cert.get("status"), "expiry_date": old_cert.get("expiry_date")},
                "new_values": {"status": "superseded", "renewed_by": new_id, "new_expiry_date": new_expiry_date},
                "signature": {},
                "metadata": {"source": "certificate_lens", "domain": domain, "new_certificate_id": new_id},
                "created_at": now,
            }).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "renewed_certificate_id": new_id,
            "superseded_certificate_id": cert_id,
            "new_expiry_date": new_expiry_date,
        }

    return _fn


def _change_certificate_status_adapter(new_status: str):
    """
    Factory that returns a handler for suspend/revoke — both are status-change operations.
    new_status: 'suspended' | 'revoked'
    """
    def _make(handlers: "CertificateHandlers"):
        async def _fn(**params):
            db = handlers.db
            yacht_id = params["yacht_id"]
            user_id = params["user_id"]
            # entity_id is the canonical key from the action router for archive/suspend/revoke
            cert_id = params.get("entity_id") or params.get("certificate_id")
            reason = params.get("reason", "")
            signature = params.get("signature", {})

            if not cert_id:
                raise ValueError("entity_id (certificate id) is required")

            domain, table_key, old_cert = _resolve_cert_domain(db, yacht_id, cert_id)
            _cert_mutation_gate(domain, params.get("role", ""), f"{new_status}_certificate")
            table = get_table(table_key)

            current_status = old_cert.get("status")
            if current_status in ("superseded", "revoked"):
                raise ValueError(f"Cannot change status of a certificate in terminal state '{current_status}'")
            if current_status == new_status:
                raise ValueError(f"Certificate is already '{new_status}'")

            now = datetime.now(timezone.utc).isoformat()
            db.table(table).update({
                "status": new_status,
                "properties": {
                    **(old_cert.get("properties") or {}),
                    f"{new_status}_at": now,
                    f"{new_status}_by": user_id,
                    f"{new_status}_reason": reason,
                },
            }).eq("yacht_id", yacht_id).eq("id", cert_id).execute()

            try:
                db.table("pms_audit_log").insert({
                    "yacht_id": yacht_id,
                    "entity_type": "certificate",
                    "entity_id": cert_id,
                    "action": f"{new_status}_certificate",
                    "user_id": user_id,
                    "old_values": {"status": current_status},
                    "new_values": {"status": new_status, "reason": reason},
                    "signature": signature if signature else {},
                    "metadata": {"source": "certificate_lens", "domain": domain, "is_signed_action": bool(signature)},
                    "created_at": now,
                }).execute()
            except Exception:
                pass

            _notify_cert_stakeholders(db, yacht_id, cert_id,
                old_cert.get("certificate_name") or old_cert.get("person_name") or "Certificate",
                new_status, user_id, domain)

            return {
                "status": "success",
                "certificate_id": cert_id,
                "new_status": new_status,
                "reason": reason,
            }

        return _fn
    return _make


def _archive_certificate_adapter(handlers: "CertificateHandlers"):
    async def _fn(**params):
        """
        Archive a certificate (soft-delete). Works for both vessel and crew.

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - entity_id (str) — the certificate UUID
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params.get("entity_id") or params.get("certificate_id")
        signature = params.get("signature", {})

        if not cert_id:
            raise ValueError("entity_id (certificate id) is required")

        domain, table_key, old_cert = _resolve_cert_domain(db, yacht_id, cert_id)
        _cert_mutation_gate(domain, params.get("role", ""), "archive_certificate")
        table = get_table(table_key)

        now = datetime.now(timezone.utc).isoformat()
        db.table(table).update({
            "deleted_at": now,
            "deleted_by": user_id,
        }).eq("yacht_id", yacht_id).eq("id", cert_id).execute()

        try:
            db.table("pms_audit_log").insert({
                "yacht_id": yacht_id,
                "entity_type": "certificate",
                "entity_id": cert_id,
                "action": "archive_certificate",
                "user_id": user_id,
                "old_values": {"deleted_at": None},
                "new_values": {"deleted_at": now},
                "signature": signature if signature else {},
                "metadata": {"source": "certificate_lens", "domain": domain},
                "created_at": now,
            }).execute()
        except Exception:
            pass

        _notify_cert_stakeholders(db, yacht_id, cert_id,
            old_cert.get("certificate_name") or old_cert.get("person_name") or "Certificate",
            "archived", user_id, domain)

        return {
            "status": "success",
            "certificate_id": cert_id,
            "deleted_at": now,
        }

    return _fn


def _assign_certificate_adapter(handlers: "CertificateHandlers"):
    async def _fn(**params):
        """
        Assign a responsible officer to a certificate.

        Stores assignment in `properties.assigned_to` on the cert row
        (uses the existing jsonb column — no schema change). Writes an
        audit log row and emits a ledger event via the safety-net path.

        Expected params:
        - yacht_id (str)
        - user_id (str)            — actor (who is making the assignment)
        - certificate_id (str)     — which cert to assign
        - assigned_to (str)        — user UUID being assigned
        - assigned_to_name (str, optional) — display name for audit trail
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        cert_id = params.get("certificate_id")
        assigned_to = params.get("assigned_to")
        assigned_to_name = params.get("assigned_to_name")

        if not cert_id:
            raise ValueError("certificate_id is required")
        if not assigned_to:
            raise ValueError("assigned_to is required")

        # Find the cert (vessel or crew) — reuses domain resolver
        domain, table_key, old_cert = _resolve_cert_domain(db, yacht_id, cert_id)
        _cert_mutation_gate(domain, params.get("role", ""), "assign_certificate")
        table = get_table(table_key)

        now = datetime.now(timezone.utc).isoformat()
        old_assignment = (old_cert.get("properties") or {}).get("assigned_to")
        new_properties = {
            **(old_cert.get("properties") or {}),
            "assigned_to": assigned_to,
            "assigned_to_name": assigned_to_name,
            "assigned_at": now,
            "assigned_by": user_id,
        }

        res = db.table(table).update({"properties": new_properties}).eq(
            "yacht_id", yacht_id
        ).eq("id", cert_id).execute()
        if not res.data:
            raise ValueError("Assignment update failed or not permitted by RLS")

        try:
            db.table("pms_audit_log").insert({
                "yacht_id": yacht_id,
                "entity_type": "certificate",
                "entity_id": cert_id,
                "action": "assign_certificate",
                "user_id": user_id,
                "old_values": {"assigned_to": old_assignment},
                "new_values": {
                    "assigned_to": assigned_to,
                    "assigned_to_name": assigned_to_name,
                },
                "signature": {},
                "metadata": {"source": "certificate_lens", "domain": domain},
                "created_at": now,
            }).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "certificate_id": cert_id,
            "assigned_to": assigned_to,
            "assigned_to_name": assigned_to_name,
        }

    return _fn


# =============================================================================
# NOTIFICATION HELPERS
# =============================================================================

def _body_for_event(event_type: str, cert_name: str, cert_domain: str) -> str:
    """Return human-readable notification body for a certificate event."""
    bodies = {
        "created": f"A new {cert_domain} certificate '{cert_name}' has been added.",
        "suspended": f"Certificate '{cert_name}' has been suspended. Review required.",
        "revoked": f"Certificate '{cert_name}' has been revoked. Immediate attention required.",
        "archived": f"Certificate '{cert_name}' has been archived.",
        "expired": f"Certificate '{cert_name}' has expired. Renewal action required.",
    }
    return bodies.get(event_type, f"Certificate '{cert_name}': {event_type}.")


def _get_cert_notification_recipients(db, yacht_id: str, cert_domain: str) -> list:
    """Return deduplicated user_ids who should be notified about a certificate event."""
    try:
        roles = ["captain", "manager"]
        if cert_domain == "vessel":
            roles.extend(["chief_engineer", "chief_officer"])
        elif cert_domain == "crew":
            roles.extend(["chief_officer", "purser", "chief_steward", "chief_engineer"])
        result = db.table("auth_users_roles").select(
            "user_id"
        ).eq("yacht_id", yacht_id).in_("role", roles).execute()
        seen: set = set()
        ids = []
        for row in (result.data or []):
            uid = row["user_id"]
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
        return ids
    except Exception:
        return []


def _notify_cert_stakeholders(db, yacht_id: str, cert_id: str, cert_name: str,
                              event_type: str, actor_user_id: str, cert_domain: str) -> int:
    """Insert notification rows into pms_notifications. Fire-and-forget."""
    try:
        recipients = _get_cert_notification_recipients(db, yacht_id, cert_domain)
        notifs = []
        for uid in recipients:
            if uid == actor_user_id:
                continue
            notifs.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "user_id": uid,
                "notification_type": f"certificate_{event_type}",
                "title": f"Certificate {event_type.title()}: {cert_name}",
                "body": _body_for_event(event_type, cert_name, cert_domain),
                "priority": "high" if event_type in ("expired", "revoked", "suspended") else "normal",
                "entity_type": "certificate",
                "entity_id": cert_id,
                "triggered_by": actor_user_id,
                "idempotency_key": f"cert_{event_type}:{cert_id}:{uid}",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        if notifs:
            db.table("pms_notifications").upsert(
                notifs, on_conflict="yacht_id,user_id,idempotency_key"
            ).execute()
        return len(notifs)
    except Exception:
        return 0
