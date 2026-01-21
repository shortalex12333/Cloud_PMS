"""
Decision Audit Service
======================

Phase 11.3: Logs every decision evaluation for explainability and compliance.

Per E021 spec, every decision is logged with:
- execution_id, timestamp
- user_id, yacht_id, session_id
- action, decision (show/hide/disable)
- confidence breakdown
- reasons
- blocked_by (if applicable)
- context snapshot (entities, intents, situation)

Schema: decision_audit_log table
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DecisionAuditEntry:
    """Single decision audit log entry per E021."""
    execution_id: str
    timestamp: str
    user_id: str
    yacht_id: str
    session_id: Optional[str]

    # What was decided
    action: str
    decision: str  # 'show', 'hide', 'disable'

    # Confidence scores
    confidence_total: float
    confidence_intent: float
    confidence_entity: float
    confidence_situation: float

    # Why
    reasons: List[str]
    blocked_by: Optional[str]
    blocked_by_type: Optional[str]

    # Context snapshot
    detected_intents: List[str]
    entities: List[Dict]
    situation: Dict
    environment: str
    user_role: str


class DecisionAuditService:
    """
    Service for logging decision evaluations.

    Logs to decision_audit_log table with full context for:
    - Explainability ("Why was this action shown/hidden?")
    - Analytics (confidence distribution, common blocks)
    - Compliance (audit trail)
    """

    def __init__(self, supabase_client):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Tenant Supabase client for DB access
        """
        self.db = supabase_client

    def log_decisions(
        self,
        execution_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        detected_intents: List[str],
        entities: List[Dict],
        situation: Dict,
        environment: str,
        decisions: List[Dict],
        session_id: Optional[str] = None,
    ) -> int:
        """
        Log all decisions from a single evaluation.

        Args:
            execution_id: UUID for this evaluation batch
            yacht_id: Yacht UUID
            user_id: User UUID
            user_role: User's role (engineer, chief_engineer, etc.)
            detected_intents: List of detected intents
            entities: List of entity dicts
            situation: Situation flags dict
            environment: at_sea, shipyard, port
            decisions: List of ActionDecision dicts
            session_id: Optional session UUID

        Returns:
            Number of decisions logged
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        logged = 0

        # Prepare batch for efficiency
        entries = []

        for decision in decisions:
            # Map allowed/blocked to show/hide/disable
            if decision.get("allowed"):
                decision_type = "show"
            elif decision.get("blocked_by"):
                # Could be disabled (shown but blocked) or hidden
                block_type = decision.get("blocked_by", {}).get("type", "")
                if block_type in ("permission", "state_guard"):
                    decision_type = "disable"
                else:
                    decision_type = "hide"
            else:
                decision_type = "hide"

            entry = {
                "id": str(uuid.uuid4()),
                "execution_id": execution_id,
                "timestamp": timestamp,
                "user_id": user_id,
                "yacht_id": yacht_id,
                "session_id": session_id,

                # Decision details
                "action": decision.get("action"),
                "decision": decision_type,
                "tier": decision.get("tier"),

                # Confidence
                "confidence_total": decision.get("confidence", 0.0),
                "confidence_intent": decision.get("breakdown", {}).get("intent", 0.0),
                "confidence_entity": decision.get("breakdown", {}).get("entity", 0.0),
                "confidence_situation": decision.get("breakdown", {}).get("situation", 0.0),

                # Reasons
                "reasons": decision.get("reasons", []),
                "blocked_by": decision.get("blocked_by", {}).get("detail") if decision.get("blocked_by") else None,
                "blocked_by_type": decision.get("blocked_by", {}).get("type") if decision.get("blocked_by") else None,

                # Context snapshot
                "detected_intents": detected_intents,
                "entities": self._sanitize_entities(entities),
                "situation": situation,
                "environment": environment,
                "user_role": user_role,
            }
            entries.append(entry)

        # Insert batch
        try:
            if entries:
                self.db.table("decision_audit_log").insert(entries).execute()
                logged = len(entries)
                logger.info(f"[DecisionAudit] Logged {logged} decisions for execution {execution_id[:8]}...")
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"[DecisionAudit] Failed to log decisions: {e}")
            logged = 0

        return logged

    def _sanitize_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Sanitize entities for storage (remove large/sensitive fields).
        """
        sanitized = []
        for e in entities:
            sanitized.append({
                "type": e.get("type"),
                "id": e.get("id"),
                "name": e.get("name"),
                "status": e.get("status"),
            })
        return sanitized

    def log_single_decision(
        self,
        yacht_id: str,
        user_id: str,
        action: str,
        decision: str,
        confidence: float,
        reasons: List[str],
        context: Dict,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Log a single decision (for on-demand queries).

        Args:
            yacht_id: Yacht UUID
            user_id: User UUID
            action: Action name
            decision: 'show', 'hide', or 'disable'
            confidence: Total confidence score
            reasons: List of reason strings
            context: Context snapshot dict
            session_id: Optional session UUID

        Returns:
            True if logged successfully
        """
        entry = {
            "id": str(uuid.uuid4()),
            "execution_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "yacht_id": yacht_id,
            "session_id": session_id,
            "action": action,
            "decision": decision,
            "confidence_total": confidence,
            "reasons": reasons,
            "detected_intents": context.get("detected_intents", []),
            "entities": context.get("entities", []),
            "situation": context.get("situation", {}),
            "environment": context.get("environment", "at_sea"),
            "user_role": context.get("user_role", "member"),
        }

        try:
            self.db.table("decision_audit_log").insert(entry).execute()
            return True
        except Exception as e:
            logger.error(f"[DecisionAudit] Failed to log single decision: {e}")
            return False

    def get_recent_decisions(
        self,
        yacht_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Query recent decisions for debugging/analytics.

        Args:
            yacht_id: Yacht UUID
            user_id: Optional user filter
            action: Optional action filter
            limit: Max results

        Returns:
            List of decision audit entries
        """
        try:
            query = self.db.table("decision_audit_log") \
                .select("*") \
                .eq("yacht_id", yacht_id) \
                .order("timestamp", desc=True) \
                .limit(limit)

            if user_id:
                query = query.eq("user_id", user_id)
            if action:
                query = query.eq("action", action)

            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[DecisionAudit] Failed to query decisions: {e}")
            return []


# Global instance cache
_audit_services: Dict[str, DecisionAuditService] = {}


def get_decision_audit_service(supabase_client) -> DecisionAuditService:
    """
    Get or create DecisionAuditService for a client.

    Note: In production, each tenant has its own DB client,
    so we cache services per client ID (memory address).
    """
    client_id = id(supabase_client)
    if client_id not in _audit_services:
        _audit_services[client_id] = DecisionAuditService(supabase_client)
    return _audit_services[client_id]
