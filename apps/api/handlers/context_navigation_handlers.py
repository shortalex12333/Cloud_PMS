"""
Context Navigation Handlers

Business logic for situational continuity endpoints.
Handles navigation context lifecycle, related expansion, and user relations.
"""

from typing import Dict, Any
from uuid import UUID
from datetime import datetime
from supabase import Client
import logging

from context_nav.schemas import (
    NavigationContextCreate,
    NavigationContext,
    RelatedRequest,
    RelatedResponse,
    RelatedGroup,
    RelatedItem,
    AddRelatedRequest,
    AddRelatedResponse,
)
from context_nav.related_expansion import get_related_artifacts

logger = logging.getLogger(__name__)


def create_navigation_context(
    supabase: Client,
    data: NavigationContextCreate
) -> NavigationContext:
    """
    Create a new navigation context when user opens an artifact from search.

    Behavior:
    1. Insert navigation_contexts row
    2. Insert ledger_events row: artefact_opened
    3. Return context (per schema)
    """
    try:
        # Insert navigation context
        context_data = {
            "yacht_id": str(data.yacht_id),
            "created_by_user_id": str(data.user_id),
            "active_anchor_type": data.artefact_type,
            "active_anchor_id": str(data.artefact_id),
            "extracted_entities": {},  # TODO: Extract entities deterministically
            "temporal_bias": "now",
        }

        context_response = supabase.table("navigation_contexts").insert(
            context_data
        ).execute()

        if not context_response.data:
            raise Exception("Failed to create navigation context")

        context_row = context_response.data[0]

        # Insert audit event: artefact_opened (non-blocking - schema may not match)
        try:
            audit_event = {
                "yacht_id": str(data.yacht_id),
                "user_id": str(data.user_id),
                "event_name": "artefact_opened",
                "payload": {
                    "situation_id": context_row["id"],
                    "artefact_type": data.artefact_type,
                    "artefact_id": str(data.artefact_id),
                },
            }
            supabase.table("ledger_events").insert(audit_event).execute()
        except Exception as ledger_err:
            # B003: ledger_events schema may not match - log but don't fail
            logger.warning(f"Failed to write ledger event (B003): {ledger_err}")

        logger.info(f"Created navigation context {context_row['id']} for user {data.user_id}")

        # Return NavigationContext
        return NavigationContext(
            id=UUID(context_row["id"]),
            yacht_id=UUID(context_row["yacht_id"]),
            created_by_user_id=UUID(context_row["created_by_user_id"]),
            created_at=context_row["created_at"],
            ended_at=context_row.get("ended_at"),
            active_anchor_type=context_row["active_anchor_type"],
            active_anchor_id=UUID(context_row["active_anchor_id"]),
            extracted_entities=context_row.get("extracted_entities", {}),
            temporal_bias=context_row.get("temporal_bias", "now"),
        )

    except Exception as e:
        logger.error(f"Failed to create navigation context: {e}")
        raise Exception(f"Failed to create navigation context: {str(e)}")


def update_active_anchor(
    supabase: Client,
    context_id: UUID,
    yacht_id: UUID,
    user_id: UUID,
    new_anchor_type: str,
    new_anchor_id: UUID
) -> NavigationContext:
    """
    Update the active anchor when user navigates to a different artifact.

    Behavior:
    1. Update navigation_contexts.active_anchor_type/id
    2. Insert ledger_events: artefact_opened
    3. Return updated context (per schema)
    """
    try:
        # Update navigation context
        update_data = {
            "active_anchor_type": new_anchor_type,
            "active_anchor_id": str(new_anchor_id),
            "extracted_entities": {},  # TODO: Extract entities deterministically
        }

        context_response = supabase.table("navigation_contexts").update(
            update_data
        ).eq("id", str(context_id)).eq("yacht_id", str(yacht_id)).execute()

        if not context_response.data:
            raise Exception(f"Navigation context {context_id} not found or not authorized")

        context_row = context_response.data[0]

        # Insert audit event: artefact_opened (non-blocking - schema may not match)
        try:
            audit_event = {
                "yacht_id": str(yacht_id),
                "user_id": str(user_id),
                "event_name": "artefact_opened",
                "payload": {
                    "situation_id": str(context_id),
                    "artefact_type": new_anchor_type,
                    "artefact_id": str(new_anchor_id),
                },
            }
            supabase.table("ledger_events").insert(audit_event).execute()
        except Exception as ledger_err:
            # B003: ledger_events schema may not match - log but don't fail
            logger.warning(f"Failed to write ledger event (B003): {ledger_err}")

        logger.info(f"Updated anchor for context {context_id} to {new_anchor_type}:{new_anchor_id}")

        # Return NavigationContext
        return NavigationContext(
            id=UUID(context_row["id"]),
            yacht_id=UUID(context_row["yacht_id"]),
            created_by_user_id=UUID(context_row["created_by_user_id"]),
            created_at=context_row["created_at"],
            ended_at=context_row.get("ended_at"),
            active_anchor_type=context_row["active_anchor_type"],
            active_anchor_id=UUID(context_row["active_anchor_id"]),
            extracted_entities=context_row.get("extracted_entities", {}),
            temporal_bias=context_row.get("temporal_bias", "now"),
        )

    except Exception as e:
        logger.error(f"Failed to update active anchor: {e}")
        raise Exception(f"Failed to update active anchor: {str(e)}")


def get_related(
    supabase: Client,
    data: RelatedRequest
) -> RelatedResponse:
    """
    Get related artifacts using deterministic FK/JOIN queries + user relations.

    Behavior:
    - Validate tenant + user auth (done by route middleware)
    - For each domain: run FK/JOIN query only (no vector/LLM)
    - Union user_added_relations scoped by tenant
    - Order deterministic (created_at DESC)
    - Limit 20 items per domain
    - If domain fails: omit domain silently (do not error)
    - Return groups in FIXED domain order

    CRITICAL: NO audit event for viewing related (not in spec)
    """
    try:
        # Get related artifacts using deterministic queries
        groups_data = get_related_artifacts(
            supabase=supabase,
            anchor_type=data.anchor_type,
            anchor_id=data.anchor_id,
            yacht_id=data.tenant_id,
            allowed_domains=data.allowed_domains
        )

        # Convert to RelatedGroup objects
        groups = [
            RelatedGroup(
                domain=group["domain"],
                items=[
                    RelatedItem(
                        artefact_type=item["artefact_type"],
                        artefact_id=UUID(item["artefact_id"]),
                        title=item["title"],
                        subtitle=item.get("subtitle"),
                        metadata=item.get("metadata")
                    )
                    for item in group["items"]
                ]
            )
            for group in groups_data
        ]

        logger.info(f"Fetched {len(groups)} related groups for {data.anchor_type}:{data.anchor_id}")

        return RelatedResponse(
            situation_id=data.situation_id,
            anchor_type=data.anchor_type,
            anchor_id=data.anchor_id,
            groups=groups
        )

    except Exception as e:
        logger.error(f"Failed to get related artifacts: {e}")
        raise Exception(f"Failed to get related artifacts: {str(e)}")


def add_user_relation(
    supabase: Client,
    data: AddRelatedRequest
) -> AddRelatedResponse:
    """
    Add an explicit user relation between two artifacts.

    Behavior:
    1. Insert user_added_relations (immediate active, source=user)
    2. Attribute created_by_user_id
    3. Insert ledger_events: relation_added
    4. Return created relation (per schema)
    """
    try:
        # Insert user relation
        relation_data = {
            "yacht_id": str(data.yacht_id),
            "created_by_user_id": str(data.user_id),
            "from_artefact_type": data.from_artefact_type,
            "from_artefact_id": str(data.from_artefact_id),
            "to_artefact_type": data.to_artefact_type,
            "to_artefact_id": str(data.to_artefact_id),
            "source": "user",
        }

        relation_response = supabase.table("user_added_relations").insert(
            relation_data
        ).execute()

        if not relation_response.data:
            raise Exception("Failed to create user relation")

        relation_row = relation_response.data[0]

        # Insert audit event: relation_added (non-blocking - schema may not match)
        try:
            audit_event = {
                "yacht_id": str(data.yacht_id),
                "user_id": str(data.user_id),
                "event_name": "relation_added",
                "payload": {
                    "relation_id": relation_row["id"],
                    "from_artefact_type": data.from_artefact_type,
                    "from_artefact_id": str(data.from_artefact_id),
                    "to_artefact_type": data.to_artefact_type,
                    "to_artefact_id": str(data.to_artefact_id),
                },
            }
            supabase.table("ledger_events").insert(audit_event).execute()
        except Exception as ledger_err:
            # B003: ledger_events schema may not match - log but don't fail
            logger.warning(f"Failed to write ledger event (B003): {ledger_err}")

        logger.info(f"Created user relation {relation_row['id']}: {data.from_artefact_type}:{data.from_artefact_id} → {data.to_artefact_type}:{data.to_artefact_id}")

        # Return AddRelatedResponse
        return AddRelatedResponse(
            relation_id=UUID(relation_row["id"]),
            created_at=relation_row["created_at"]
        )

    except Exception as e:
        logger.error(f"Failed to add user relation: {e}")
        # Check if it's a duplicate relation error
        if "unique_user_relation" in str(e).lower():
            raise Exception("Relation already exists")
        raise Exception(f"Failed to add user relation: {str(e)}")


def end_navigation_context(
    supabase: Client,
    context_id: UUID,
    yacht_id: UUID,
    user_id: UUID
) -> Dict[str, str]:
    """
    End the navigation context when user returns to search bar home.

    Behavior:
    1. Set navigation_contexts.ended_at = now()
    2. Insert ledger_events: situation_ended
    3. Return success
    """
    try:
        # Update navigation context
        update_data = {
            "ended_at": datetime.utcnow().isoformat()
        }

        context_response = supabase.table("navigation_contexts").update(
            update_data
        ).eq("id", str(context_id)).eq("yacht_id", str(yacht_id)).execute()

        if not context_response.data:
            raise Exception(f"Navigation context {context_id} not found or not authorized")

        # Insert audit event: situation_ended (non-blocking - schema may not match)
        try:
            audit_event = {
                "yacht_id": str(yacht_id),
                "user_id": str(user_id),
                "event_name": "situation_ended",
                "payload": {
                    "situation_id": str(context_id),
                },
            }
            supabase.table("ledger_events").insert(audit_event).execute()
        except Exception as ledger_err:
            # B003: ledger_events schema may not match - log but don't fail
            logger.warning(f"Failed to write ledger event (B003): {ledger_err}")

        logger.info(f"Ended navigation context {context_id}")

        return {"status": "success", "message": "Navigation context ended"}

    except Exception as e:
        logger.error(f"Failed to end navigation context: {e}")
        raise Exception(f"Failed to end navigation context: {str(e)}")
