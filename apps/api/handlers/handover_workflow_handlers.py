"""
Handover Workflow Handlers
==========================

Implements dual-hash, dual-signature handover workflow:

Stage 1: Draft Review
- validate_draft: Check for errors (empty fields, invalid links)
- finalize_draft: Lock content, generate content_hash

Stage 2: Export
- export_handover: Generate HTML/PDF, store document_hash

Stage 3: Sign-off (Dual Signature)
- sign_outgoing: Outgoing user signs export
- sign_incoming: Incoming user countersigns + acknowledges critical items

Stage 4: Verification
- get_pending: List handovers awaiting signature
- verify_export: Return hashes + signature metadata for verification

Schema:
- handover_items: content_hash, finalized_at, finalized_by, version, is_finalized
- handover_exports: document_hash, signatures (JSONB), previous_export_id, status,
                    outgoing_*, incoming_*, signoff_complete
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HandoverWorkflowHandlers:
    """Handlers for handover workflow: finalize → export → sign → verify"""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # STAGE 1: DRAFT REVIEW & FINALIZATION
    # =========================================================================

    async def validate_draft(
        self,
        yacht_id: str,
        user_id: str,
        section: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Validate handover draft for finalization.

        Checks:
        - Empty summaries
        - Critical items without action_summary
        - Invalid entity links
        - Duplicate items

        Returns validation report with warnings and blocking errors.
        """
        query = self.db.table("handover_items").select("*").eq("yacht_id", yacht_id).is_("deleted_at", None)

        if section:
            query = query.eq("section", section)
        if category:
            query = query.eq("category", category)

        result = query.execute()
        items = result.data or []

        errors = []
        warnings = []

        for item in items:
            item_id = item["id"]
            summary = item.get("summary", "").strip()

            # Blocking: Empty summary
            if not summary:
                errors.append({
                    "item_id": item_id,
                    "type": "empty_summary",
                    "message": "Item has empty summary"
                })

            # Blocking: Critical item without action summary
            if item.get("is_critical") and not item.get("action_summary"):
                errors.append({
                    "item_id": item_id,
                    "type": "missing_action",
                    "message": "Critical item missing action_summary"
                })

            # Warning: No category
            if not item.get("category"):
                warnings.append({
                    "item_id": item_id,
                    "type": "missing_category",
                    "message": "Item has no category"
                })

        return {
            "valid": len(errors) == 0,
            "total_items": len(items),
            "errors": errors,
            "warnings": warnings,
            "blocking_count": len(errors),
            "warning_count": len(warnings)
        }

    async def finalize_draft(
        self,
        yacht_id: str,
        user_id: str,
        section: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Finalize draft: lock content and generate content_hash.

        Steps:
        1. Validate draft (must have 0 blocking errors)
        2. Fetch all items, normalize to JSON
        3. Generate SHA256 content_hash
        4. Update items: is_finalized=true, content_hash, finalized_at, finalized_by
        5. Return content_hash for display

        Status transitions:
        - Items become read-only (except via tracked change requests)
        """
        # Step 1: Validate
        validation = await self.validate_draft(yacht_id, user_id, section, category)
        if not validation["valid"]:
            return {
                "status": "error",
                "error_code": "VALIDATION_FAILED",
                "message": f"Draft has {validation['blocking_count']} blocking errors",
                "validation": validation
            }

        # Step 2: Fetch items
        query = self.db.table("handover_items").select("*").eq("yacht_id", yacht_id).is_("deleted_at", None)
        if section:
            query = query.eq("section", section)
        if category:
            query = query.eq("category", category)

        result = query.order("category", desc=False).order("created_at", desc=False).execute()
        items = result.data or []

        if not items:
            return {
                "status": "error",
                "error_code": "NO_ITEMS",
                "message": "No items to finalize"
            }

        # Step 3: Normalize and hash
        normalized = self._normalize_draft_content(items)
        content_json = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(content_json.encode('utf-8')).hexdigest()

        # Step 4: Update items
        now = datetime.now(timezone.utc).isoformat()
        item_ids = [item["id"] for item in items]

        self.db.table("handover_items").update({
            "is_finalized": True,
            "content_hash": content_hash,
            "finalized_at": now,
            "finalized_by": user_id,
            "version": 1
        }).in_("id", item_ids).execute()

        logger.info(f"Draft finalized: yacht={yacht_id}, items={len(items)}, hash={content_hash[:16]}")

        return {
            "status": "success",
            "content_hash": content_hash,
            "finalized_at": now,
            "finalized_by": user_id,
            "item_count": len(items),
            "message": "Draft finalized and locked"
        }

    def _normalize_draft_content(self, items: List[Dict]) -> Dict:
        """
        Normalize draft items to canonical JSON for hashing.

        Includes: id, summary, category, priority, is_critical, action_summary, entity references
        Excludes: timestamps, user_ids, audit fields
        """
        normalized_items = []
        for item in items:
            normalized_items.append({
                "id": item["id"],
                "summary": item.get("summary", ""),
                "category": item.get("category"),
                "section": item.get("section"),
                "priority": item.get("priority", "normal"),
                "is_critical": item.get("is_critical", False),
                "requires_action": item.get("requires_action", False),
                "action_summary": item.get("action_summary"),
                "entity_type": item.get("entity_type"),
                "entity_id": item.get("entity_id"),
                "risk_tags": item.get("risk_tags", [])
            })

        return {
            "version": 1,
            "items": normalized_items
        }

    # =========================================================================
    # STAGE 2: EXPORT
    # =========================================================================

    async def export_handover(
        self,
        yacht_id: str,
        user_id: str,
        export_type: str = "html",
        section: Optional[str] = None,
        department: Optional[str] = None,
        shift_date: Optional[str] = None
    ) -> Dict:
        """
        Generate handover export with document_hash.

        Prerequisites:
        - Items must be finalized (content_hash present)

        Steps:
        1. Verify items are finalized
        2. Generate export using handover_export_service
        3. Store document_hash (SHA256 of artifact bytes)
        4. Create handover_exports record: status='awaiting_outgoing_signature'
        5. Send notification to ledger for outgoing signer

        Returns export_id, document_hash, content_hash for verification
        """
        # Verify finalization
        query = self.db.table("handover_items").select("content_hash, is_finalized").eq("yacht_id", yacht_id).is_("deleted_at", None)
        if section:
            query = query.eq("section", section)

        result = query.limit(1).execute()
        if not result.data:
            return {
                "status": "error",
                "error_code": "NO_ITEMS",
                "message": "No items found for export"
            }

        item = result.data[0]
        if not item.get("is_finalized"):
            return {
                "status": "error",
                "error_code": "NOT_FINALIZED",
                "message": "Draft must be finalized before export"
            }

        content_hash = item.get("content_hash")

        # Generate export (delegated to export service)
        try:
            from apps.api.services.handover_export_service import HandoverExportService
            export_service = HandoverExportService(self.db)

            export_result = await export_service.generate_export(
                yacht_id=yacht_id,
                user_id=user_id,
                export_type=export_type,
                include_completed=False
            )
        except ImportError as e:
            logger.error(f"Export service import failed: {e}")
            return {
                "status": "error",
                "error_code": "SERVICE_UNAVAILABLE",
                "message": "Export service not available"
            }
        except Exception as e:
            logger.error(f"Export generation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "EXPORT_FAILED",
                "message": f"Failed to generate export: {str(e)}"
            }

        # Calculate document hash from generated HTML
        document_bytes = export_result.html.encode('utf-8')
        document_hash = hashlib.sha256(document_bytes).hexdigest()

        export_id = export_result.export_id

        # Update export record with workflow fields
        try:
            # DEPRECATED: `status` column retired as state-machine driver (PR #642).
            # `review_status` is the SSOT. The write below is kept only because
            # `sign_outgoing` still gates on `status == 'pending_outgoing'` until
            # the twin /submit+/countersign vs /sign/outgoing+/sign/incoming paths
            # are consolidated (task T4). Do not rely on this value in new code.
            self.db.table("handover_exports").update({
                "document_hash": document_hash,
                "content_hash": content_hash,
                "status": "pending_outgoing",
                "department": department,
                "shift_date": shift_date
            }).eq("id", export_id).execute()
        except Exception as e:
            logger.error(f"Failed to update export record: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to update export record"
            }

        # Send notification to ledger
        try:
            await self._notify_ledger_export_ready(
                yacht_id=yacht_id,
                export_id=export_id,
                user_id=user_id,
                notification_type="handover_ready_outgoing"
            )
        except Exception as e:
            # Non-fatal: export succeeded but notification failed
            logger.warning(f"Failed to send notification: {e}")

        logger.info(f"Export created: export_id={export_id}, document_hash={document_hash[:16]}")

        return {
            "status": "success",
            "export_id": export_id,
            "document_hash": document_hash,
            "content_hash": content_hash,
            "export_type": export_type,
            "total_items": export_result.total_items,
            "message": "Export generated, awaiting outgoing signature"
        }

    # =========================================================================
    # STAGE 3: DUAL SIGNATURE
    # =========================================================================

    async def sign_outgoing(
        self,
        export_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        note: Optional[str] = None,
        method: str = "typed"
    ) -> Dict:
        """
        Outgoing user signs the export.

        Prerequisites:
        - Export must exist with status='pending_outgoing'
        - User must have officer+ role (HOD, Captain, Manager)
        - Document_hash must be present

        Steps:
        1. Verify export exists and status is correct
        2. Require step-up re-auth (password/OTP) - handled by caller
        3. Create signature envelope: { document_hash, export_id, user_id, role, timestamp, method }
        4. Store in handover_exports: outgoing_user_id, outgoing_signed_at, outgoing_notes
        5. (Retired in PR #642) The legacy `status` column used to be set to
           'pending_incoming' here. It is no longer written — `review_status`
           plus `outgoing_signed_at` / `incoming_signed_at` drive the state.
        6. Send notification to incoming user

        Returns signature metadata
        """
        # Fetch export
        result = self.db.table("handover_exports").select("*").eq("id", export_id).eq("yacht_id", yacht_id).single().execute()

        if not result.data:
            return {
                "status": "error",
                "error_code": "EXPORT_NOT_FOUND",
                "message": f"Export {export_id} not found"
            }

        export = result.data

        # DEPRECATED: reads legacy `status` column. `review_status` is the SSOT
        # (PR #642). Kept until task T4 consolidates this twin path with
        # /submit + /countersign. New code must not gate on `status`.
        if export["status"] != "pending_outgoing":
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": f"Export status is '{export['status']}', expected 'pending_outgoing'"
            }

        document_hash = export.get("document_hash")
        if not document_hash:
            return {
                "status": "error",
                "error_code": "MISSING_HASH",
                "message": "Export missing document_hash"
            }

        # Create signature envelope
        now = datetime.now(timezone.utc)
        signature_payload = {
            "document_hash": document_hash,
            "export_id": export_id,
            "signer_user_id": user_id,
            "role": user_role,
            "timestamp": now.isoformat(),
            "method": method
        }

        # In MVP: server-side "soft signature" (JWS envelope stored)
        # Phase 2: WebAuthn client-side signature
        signature_envelope = self._create_signature_envelope(signature_payload)

        # Update export record
        signatures = export.get("signatures") or {}
        signatures["outgoing"] = signature_envelope

        # DEPRECATED: `status` column retired as state-machine driver (PR #642).
        # `review_status` is the SSOT. The legacy transition
        # `status: pending_outgoing -> pending_incoming` is no longer written here.
        # The dual sign/{outgoing,incoming} path is scheduled for consolidation with
        # the /submit + /countersign path (see task T4). Until then, sign_outgoing
        # records only the outgoing signature metadata; downstream readers must use
        # `review_status + outgoing_signed_at + incoming_signed_at`.
        self.db.table("handover_exports").update({
            "outgoing_user_id": user_id,
            "outgoing_role": user_role,
            "outgoing_signed_at": now.isoformat(),
            "outgoing_comments": note,
            "signatures": json.dumps(signatures),
        }).eq("id", export_id).execute()

        # Notify incoming user
        await self._notify_ledger_export_ready(
            yacht_id=yacht_id,
            export_id=export_id,
            user_id=user_id,
            notification_type="handover_ready_incoming"
        )

        logger.info(f"Outgoing signature: export={export_id}, user={user_id}, role={user_role}")

        return {
            "status": "success",
            "export_id": export_id,
            "signed_at": now.isoformat(),
            "signed_by": user_id,
            "role": user_role,
            "signature_method": method,
            "message": "Outgoing signature recorded, awaiting incoming signature"
        }

    async def sign_incoming(
        self,
        export_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        acknowledge_critical: bool,
        note: Optional[str] = None,
        method: str = "typed"
    ) -> Dict:
        """
        Incoming crew acknowledges the handover.

        Prerequisites:
        - Export must exist with review_status='complete' (countersigned by HOD) AND
          incoming_signed_at IS NULL (not yet acknowledged).
        - Any authenticated user on the yacht may acknowledge — no role gate.
        - Must acknowledge critical items (checkbox required).

        State machine note:
        `review_status` is the real state machine for handover_exports:
            pending_review -> pending_hod_signature -> complete -> (ack recorded via
            incoming_signed_at; `review_status` stays 'complete').
        The legacy `status` column ('pending_incoming', 'completed') is retained for
        backward compatibility and is kept in sync here, but new code MUST read
        `review_status` and `incoming_signed_at` — not `status`.

        Steps:
        1. Verify review_status='complete' and not already acknowledged
        2. Require acknowledgment of critical items
        3. Create signature envelope
        4. Store incoming_* fields
        5. Set signoff_complete=true, keep review_status='complete' (ack closes loop)
        6. Write ledger_events + pms_audit_log and notify outgoing user / captain / manager

        Returns completion status
        """
        # Fetch export (include the real state-machine columns)
        result = (
            self.db.table("handover_exports")
            .select(
                "id, yacht_id, status, review_status, document_hash, signatures, "
                "incoming_signed_at, outgoing_user_id, exported_by_user_id, department"
            )
            .eq("id", export_id)
            .eq("yacht_id", yacht_id)
            .single()
            .execute()
        )

        if not result.data:
            return {
                "status": "error",
                "error_code": "EXPORT_NOT_FOUND",
                "message": f"Export {export_id} not found"
            }

        export = result.data

        # `review_status` is the real state machine; `status` is legacy (see docstring).
        review_status = export.get("review_status")
        if review_status != "complete":
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": (
                    f"Export review_status is '{review_status}', expected 'complete' "
                    "(handover must be HOD-countersigned before incoming ack)."
                ),
            }

        if export.get("incoming_signed_at") is not None:
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": "Handover has already been acknowledged by incoming crew.",
            }

        if not acknowledge_critical:
            return {
                "status": "error",
                "error_code": "CRITICAL_NOT_ACKNOWLEDGED",
                "message": "Must acknowledge critical items before signing"
            }

        document_hash = export.get("document_hash")

        # Create signature envelope
        now = datetime.now(timezone.utc)
        signature_payload = {
            "document_hash": document_hash,
            "export_id": export_id,
            "signer_user_id": user_id,
            "role": user_role,
            "timestamp": now.isoformat(),
            "method": method,
            "critical_acknowledged": acknowledge_critical
        }

        signature_envelope = self._create_signature_envelope(signature_payload)

        # Update export record. `signatures` may be stored as JSONB (dict) or a JSON
        # string depending on writer — tolerate both.
        raw_sigs = export.get("signatures") or {}
        if isinstance(raw_sigs, str):
            try:
                signatures = json.loads(raw_sigs) if raw_sigs else {}
            except Exception:
                signatures = {}
        else:
            signatures = dict(raw_sigs)
        signatures["incoming"] = signature_envelope

        self.db.table("handover_exports").update({
            "incoming_user_id": user_id,
            "incoming_role": user_role,
            "incoming_signed_at": now.isoformat(),
            "incoming_comments": note,
            "incoming_acknowledged_critical": acknowledge_critical,
            "signatures": json.dumps(signatures),
            "signoff_complete": True,
            # Legacy `status` column kept in sync for backward compat; real state is
            # `review_status` + `incoming_signed_at`.
            "status": "completed"
        }).eq("id", export_id).execute()

        logger.info(f"Incoming signature: export={export_id}, user={user_id}, signoff complete")

        # Ledger + audit + notification cascade.
        # Mirrors the `handover_countersigned` pattern in
        # routes/handover_export_routes.py (_write_handover_event + _get_role_users).
        # TODO(handover): consolidate with _write_handover_event helper once cross-module
        # import is cleaned up (currently duplicated inline to avoid circular deps).
        self._emit_handover_acknowledged_events(
            export_id=export_id,
            yacht_id=yacht_id,
            actor_id=user_id,
            actor_role=user_role,
            acknowledge_critical=acknowledge_critical,
            outgoing_user_id=(
                export.get("outgoing_user_id") or export.get("exported_by_user_id")
            ),
            department=export.get("department"),
            now_iso=now.isoformat(),
        )

        return {
            "status": "success",
            "export_id": export_id,
            "signed_at": now.isoformat(),
            "signed_by": user_id,
            "role": user_role,
            "signoff_complete": True,
            "message": "Handover sign-off complete"
        }

    def _create_signature_envelope(self, payload: Dict) -> Dict:
        """
        Create a JWS-style signature envelope (MVP: server-side soft signature).

        Phase 2: Replace with client-side WebAuthn signatures.
        """
        import hmac

        # MVP: Server signs with HMAC (soft signature)
        payload_json = json.dumps(payload, sort_keys=True)
        # In production: use proper JWS library with key rotation
        sig = hmac.new(b"handover_signing_key_v1", payload_json.encode(), hashlib.sha256).hexdigest()

        return {
            "payload": payload,
            "signature": sig,
            "alg": "HS256",
            "typ": "soft"
        }

    def _emit_handover_acknowledged_events(
        self,
        export_id: str,
        yacht_id: str,
        actor_id: str,
        actor_role: str,
        acknowledge_critical: bool,
        outgoing_user_id: Optional[str],
        department: Optional[str],
        now_iso: str,
    ) -> None:
        """Write pms_audit_log + ledger_events for handover acknowledgement.

        Mirrors the `handover_countersigned` cascade in handover_export_routes.py
        (`_write_handover_event` + `_get_role_users`). Duplicated inline here to avoid
        a circular import between handlers/ and routes/. Every DB write is wrapped in
        try/except so the ack itself never fails due to notification problems.

        Recipients:
          - actor (self-audit row)
          - outgoing_user_id (the person who wrote the handover), if known
          - all captain + manager users on the yacht (rotation closure notification)
        """
        try:
            from routes.handlers.ledger_utils import build_ledger_event
        except Exception as e:  # pragma: no cover — import path is stable in app
            logger.warning("sign_incoming: ledger_utils import failed: %s", e)
            return

        change_summary = "Handover acknowledged by incoming crew"
        metadata = {
            "acknowledged_critical": acknowledge_critical,
            "export_id": export_id,
        }
        new_values = {
            "incoming_user_id": actor_id,
            "incoming_signed_at": now_iso,
            "incoming_acknowledged_critical": acknowledge_critical,
        }

        # Build recipient list. De-dupe while preserving order.
        recipients: List[Dict[str, Any]] = [
            {"user_id": actor_id, "department": department, "role": actor_role}
        ]
        if outgoing_user_id and outgoing_user_id != actor_id:
            recipients.append(
                {"user_id": outgoing_user_id, "department": department, "role": None}
            )

        # Captain + manager cascade (rotation-closure notification)
        try:
            roles_result = (
                self.db.table("auth_users_roles")
                .select("user_id, role, department")
                .eq("yacht_id", yacht_id)
                .in_("role", ["captain", "manager"])
                .eq("is_active", True)
                .execute()
            )
            for r in (roles_result.data or []):
                recipients.append(
                    {
                        "user_id": r["user_id"],
                        "department": r.get("department") or department,
                        "role": r.get("role"),
                    }
                )
        except Exception as e:
            logger.warning("sign_incoming: auth_users_roles lookup failed: %s", e)

        seen_ids = set()
        for rec in recipients:
            uid = rec.get("user_id")
            if not uid or uid in seen_ids:
                continue
            seen_ids.add(uid)

            # 1. pms_audit_log (immutable compliance trail)
            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "handover_export",
                    "entity_id": export_id,
                    "action": "handover_acknowledged",
                    "user_id": uid,
                    "actor_id": actor_id,
                    "signature": {
                        "actor_id": actor_id,
                        "actor_role": actor_role,
                        "timestamp": now_iso,
                    },
                    "old_values": {},
                    "new_values": new_values,
                    "metadata": metadata,
                    "created_at": now_iso,
                }).execute()
            except Exception as e:
                logger.warning(
                    "sign_incoming: pms_audit_log insert failed (export=%s, user=%s): %s",
                    export_id, uid, e,
                )

            # 2. ledger_events (notification bus + proof_hash chain)
            try:
                ledger_event = build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=uid,
                    event_type="handover",
                    entity_type="handover_export",
                    entity_id=export_id,
                    action="handover_acknowledged",
                    user_role=actor_role,
                    change_summary=change_summary,
                    metadata=metadata,
                    department=rec.get("department"),
                    new_state=new_values,
                )
                self.db.table("ledger_events").insert(ledger_event).execute()
            except Exception as e:
                logger.warning(
                    "sign_incoming: ledger_events insert failed (export=%s, user=%s): %s",
                    export_id, uid, e,
                )

    # =========================================================================
    # STAGE 4: VERIFICATION & PENDING
    # =========================================================================

    async def get_pending_handovers(
        self,
        yacht_id: str,
        user_id: str,
        role_filter: Optional[str] = None
    ) -> Dict:
        """
        Get handovers pending signature by this user.

        Filters (reads `review_status` + `incoming_signed_at` — the real state
        machine. PR #642 retired the legacy `status` column as state driver):

        - role_filter='outgoing': awaiting outgoing (user) signature.
              review_status IN ('pending_review', 'pending_hod_signature')
              AND outgoing_signed_at IS NULL
        - role_filter='incoming': HOD-complete, waiting for incoming ack.
              review_status = 'complete' AND incoming_signed_at IS NULL
        - No filter: anything not fully acknowledged (review_status != 'complete'
              OR incoming_signed_at IS NULL).

        Legacy `status` mappings retired here:
            status='pending_outgoing'  -> review_status='pending_review'
                                          AND outgoing_signed_at IS NULL
            status='pending_incoming'  -> review_status='complete'
                                          AND incoming_signed_at IS NULL
            status='completed'         -> review_status='complete'
                                          AND incoming_signed_at IS NOT NULL

        Returns list of exports with metadata.
        """
        query = self.db.table("handover_exports").select("*").eq("yacht_id", yacht_id)

        if role_filter == "outgoing":
            # Awaiting outgoing/user signature — the export was generated but the
            # author has not yet signed. `outgoing_signed_at IS NULL` filters by
            # absence of the outgoing signature; review_status is pre-complete.
            query = (
                query.in_("review_status", ["pending_review", "pending_hod_signature"])
                .is_("outgoing_signed_at", "null")
            )
        elif role_filter == "incoming":
            # HOD-complete handover that the incoming crew has not yet acknowledged.
            query = query.eq("review_status", "complete").is_("incoming_signed_at", "null")
        else:
            # Anything still pending anywhere in the chain.
            query = query.or_(
                "review_status.neq.complete,incoming_signed_at.is.null"
            )

        result = query.order("created_at", desc=True).execute()
        exports = result.data or []

        return {
            "status": "success",
            "pending_count": len(exports),
            "exports": exports
        }

    async def verify_export(
        self,
        export_id: str,
        yacht_id: str
    ) -> Dict:
        """
        Get verification data for an export.

        Returns:
        - content_hash (draft)
        - document_hash (artifact)
        - Outgoing signature metadata
        - Incoming signature metadata
        - Timestamps
        - Signoff status

        Used for QR verification page and PDF footer.
        """
        result = self.db.table("handover_exports").select("*").eq("id", export_id).eq("yacht_id", yacht_id).single().execute()

        if not result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Export not found"
            }

        export = result.data
        signatures = json.loads(export.get("signatures") or "{}")

        return {
            "status": "success",
            "export_id": export_id,
            "content_hash": export.get("content_hash"),
            "document_hash": export.get("document_hash"),
            "signoff_complete": export.get("signoff_complete", False),
            "outgoing": {
                "user_id": export.get("outgoing_user_id"),
                "role": export.get("outgoing_role"),
                "signed_at": export.get("outgoing_signed_at"),
                "signature": signatures.get("outgoing")
            },
            "incoming": {
                "user_id": export.get("incoming_user_id"),
                "role": export.get("incoming_role"),
                "signed_at": export.get("incoming_signed_at"),
                "critical_acknowledged": export.get("incoming_acknowledged_critical"),
                "signature": signatures.get("incoming")
            },
            "timestamps": {
                "exported_at": export.get("exported_at"),
                "completed_at": export.get("incoming_signed_at") if export.get("signoff_complete") else None
            }
        }

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================

    async def _notify_ledger_export_ready(
        self,
        yacht_id: str,
        export_id: str,
        user_id: str,
        notification_type: str
    ):
        """
        Send notification to ledger when export is ready for signing.

        Notification types:
        - handover_ready_outgoing: Export created, needs outgoing signature
        - handover_ready_incoming: Outgoing signed, needs incoming countersignature

        Ledger will route to appropriate user(s).
        """
        notification_data = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "notification_type": notification_type,
            "entity_type": "handover_export",
            "entity_id": export_id,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "export_id": export_id,
                "action_required": "sign"
            }
        }

        # Insert into notifications/ledger table
        self.db.table("notifications").insert(notification_data).execute()

        logger.info(f"Notification sent: type={notification_type}, export={export_id}")
