"""
Context Navigation - Deterministic Related Expansion

CRITICAL CONSTRAINTS:
- NO vector search, NO embeddings, NO LLMs
- FK/JOIN queries ONLY
- Empty results are VALID (silence is valid)
- Partial domain failures are OMITTED silently
- Fixed domain ordering (never dynamic)
- Always filter by tenant (yacht_id)
"""

from typing import List, Dict, Any, Optional
from supabase import Client
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Fixed domain ordering (from spec: 33_DOMAIN_GROUPING_ORDER.md)
DOMAIN_ORDER = [
    "inventory",      # Parts/equipment/tools
    "work_orders",    # Work order tasks
    "faults",         # Equipment failures
    "shopping",       # Shopping items/lists
    "documents",      # Technical docs/manuals
    "manuals",        # Manual sections
    "emails",         # Email messages
    "certificates",   # Equipment certificates
    "history",        # Historical handover entries
]


def get_related_for_equipment(
    supabase: Client,
    anchor_id: UUID,
    yacht_id: UUID,
    allowed_domains: List[str],
    limit: int = 20
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get related artifacts for an equipment anchor.

    FK paths:
    - faults: faults.equipment_id = anchor_id
    - work_orders: work_orders.equipment_id = anchor_id
    - parts: (no direct FK - omit)
    """
    results = {}

    # Domain: faults
    if "faults" in allowed_domains:
        try:
            response = supabase.table("faults").select(
                "id, title, severity, detected_at, resolved_at"
            ).eq("yacht_id", str(yacht_id)).eq("equipment_id", str(anchor_id)).order(
                "detected_at", desc=True
            ).limit(limit).execute()

            results["faults"] = [{
                "artefact_type": "fault",
                "artefact_id": str(row["id"]),
                "title": row["title"],
                "subtitle": f"{row['severity']} - {'Resolved' if row['resolved_at'] else 'Active'}",
                "metadata": {"severity": row["severity"], "resolved_at": row["resolved_at"]}
            } for row in response.data] if response.data else []
        except Exception as e:
            logger.warning(f"Failed to fetch faults for equipment {anchor_id}: {e}")
            # Omit domain silently

    # Domain: work_orders
    if "work_orders" in allowed_domains:
        try:
            response = supabase.table("work_orders").select(
                "id, number, title, status, priority, created_at"
            ).eq("yacht_id", str(yacht_id)).eq("equipment_id", str(anchor_id)).order(
                "created_at", desc=True
            ).limit(limit).execute()

            results["work_orders"] = [{
                "artefact_type": "work_order",
                "artefact_id": str(row["id"]),
                "title": f"{row['number']}: {row['title']}",
                "subtitle": f"{row['status']} - {row['priority']}",
                "metadata": {"status": row["status"], "priority": row["priority"]}
            } for row in response.data] if response.data else []
        except Exception as e:
            logger.warning(f"Failed to fetch work_orders for equipment {anchor_id}: {e}")
            # Omit domain silently

    return results


def get_related_for_fault(
    supabase: Client,
    anchor_id: UUID,
    yacht_id: UUID,
    allowed_domains: List[str],
    limit: int = 20
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get related artifacts for a fault anchor.

    FK paths:
    - work_orders: work_orders.fault_id = anchor_id
    - inventory: faults.equipment_id → equipment (single item, not list)
    """
    results = {}

    # Domain: work_orders
    if "work_orders" in allowed_domains:
        try:
            response = supabase.table("work_orders").select(
                "id, number, title, status, priority, created_at"
            ).eq("yacht_id", str(yacht_id)).eq("fault_id", str(anchor_id)).order(
                "created_at", desc=True
            ).limit(limit).execute()

            results["work_orders"] = [{
                "artefact_type": "work_order",
                "artefact_id": str(row["id"]),
                "title": f"{row['number']}: {row['title']}",
                "subtitle": f"{row['status']} - {row['priority']}",
                "metadata": {"status": row["status"], "priority": row["priority"]}
            } for row in response.data] if response.data else []
        except Exception as e:
            logger.warning(f"Failed to fetch work_orders for fault {anchor_id}: {e}")

    # Domain: inventory (via fault.equipment_id)
    if "inventory" in allowed_domains:
        try:
            # Get fault's equipment_id
            fault_response = supabase.table("faults").select("equipment_id").eq(
                "id", str(anchor_id)
            ).eq("yacht_id", str(yacht_id)).maybe_single().execute()

            if fault_response.data and fault_response.data.get("equipment_id"):
                equipment_id = fault_response.data["equipment_id"]
                equip_response = supabase.table("equipment").select(
                    "id, name, model, location, status"
                ).eq("id", equipment_id).eq("yacht_id", str(yacht_id)).maybe_single().execute()

                if equip_response.data:
                    results["inventory"] = [{
                        "artefact_type": "inventory_item",
                        "artefact_id": str(equip_response.data["id"]),
                        "title": equip_response.data["name"],
                        "subtitle": f"{equip_response.data.get('model', '')} - {equip_response.data.get('location', '')}",
                        "metadata": {"status": equip_response.data.get("status")}
                    }]
        except Exception as e:
            logger.warning(f"Failed to fetch equipment for fault {anchor_id}: {e}")

    return results


def get_related_for_work_order(
    supabase: Client,
    anchor_id: UUID,
    yacht_id: UUID,
    allowed_domains: List[str],
    limit: int = 20
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get related artifacts for a work_order anchor.

    FK paths:
    - inventory: work_orders.equipment_id → equipment (single item)
    - faults: work_orders.fault_id → faults (single item)
    """
    results = {}

    # Get work_order to access its FKs
    try:
        wo_response = supabase.table("work_orders").select(
            "equipment_id, fault_id"
        ).eq("id", str(anchor_id)).eq("yacht_id", str(yacht_id)).maybe_single().execute()

        if not wo_response.data:
            return results

        wo_data = wo_response.data

        # Domain: inventory (via work_order.equipment_id)
        if "inventory" in allowed_domains and wo_data.get("equipment_id"):
            try:
                equip_response = supabase.table("equipment").select(
                    "id, name, model, location, status"
                ).eq("id", wo_data["equipment_id"]).eq("yacht_id", str(yacht_id)).maybe_single().execute()

                if equip_response.data:
                    results["inventory"] = [{
                        "artefact_type": "inventory_item",
                        "artefact_id": str(equip_response.data["id"]),
                        "title": equip_response.data["name"],
                        "subtitle": f"{equip_response.data.get('model', '')} - {equip_response.data.get('location', '')}",
                        "metadata": {"status": equip_response.data.get("status")}
                    }]
            except Exception as e:
                logger.warning(f"Failed to fetch equipment for work_order {anchor_id}: {e}")

        # Domain: faults (via work_order.fault_id)
        if "faults" in allowed_domains and wo_data.get("fault_id"):
            try:
                fault_response = supabase.table("faults").select(
                    "id, title, severity, detected_at, resolved_at"
                ).eq("id", wo_data["fault_id"]).eq("yacht_id", str(yacht_id)).maybe_single().execute()

                if fault_response.data:
                    row = fault_response.data
                    results["faults"] = [{
                        "artefact_type": "fault",
                        "artefact_id": str(row["id"]),
                        "title": row["title"],
                        "subtitle": f"{row['severity']} - {'Resolved' if row.get('resolved_at') else 'Active'}",
                        "metadata": {"severity": row["severity"], "resolved_at": row.get("resolved_at")}
                    }]
            except Exception as e:
                logger.warning(f"Failed to fetch fault for work_order {anchor_id}: {e}")

    except Exception as e:
        logger.warning(f"Failed to fetch work_order {anchor_id}: {e}")

    return results


def get_user_added_relations(
    supabase: Client,
    anchor_type: str,
    anchor_id: UUID,
    yacht_id: UUID,
    allowed_domains: List[str],
    limit: int = 20
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get user-added relations for the anchor.

    Bidirectional lookup:
    - from_artefact matches anchor
    - to_artefact matches anchor (reverse direction)
    """
    results_by_domain = {}

    try:
        # Query bidirectional relations
        forward_relations = supabase.table("user_added_relations").select(
            "to_artefact_type, to_artefact_id, created_at"
        ).eq("yacht_id", str(yacht_id)).eq("from_artefact_type", anchor_type).eq(
            "from_artefact_id", str(anchor_id)
        ).order("created_at", desc=True).limit(limit).execute()

        reverse_relations = supabase.table("user_added_relations").select(
            "from_artefact_type, from_artefact_id, created_at"
        ).eq("yacht_id", str(yacht_id)).eq("to_artefact_type", anchor_type).eq(
            "to_artefact_id", str(anchor_id)
        ).order("created_at", desc=True).limit(limit).execute()

        # Collect all related artifact IDs
        related_artifacts = []

        if forward_relations.data:
            for rel in forward_relations.data:
                related_artifacts.append({
                    "type": rel["to_artefact_type"],
                    "id": rel["to_artefact_id"],
                    "created_at": rel["created_at"]
                })

        if reverse_relations.data:
            for rel in reverse_relations.data:
                related_artifacts.append({
                    "type": rel["from_artefact_type"],
                    "id": rel["from_artefact_id"],
                    "created_at": rel["created_at"]
                })

        # Fetch actual artifact data and group by domain
        # This is simplified - in production, you'd batch fetch by type
        for artifact in related_artifacts:
            domain = _map_artefact_type_to_domain(artifact["type"])
            if domain not in allowed_domains:
                continue

            # Fetch artifact details based on type
            artifact_data = _fetch_artifact_details(supabase, artifact["type"], artifact["id"], yacht_id)
            if artifact_data:
                if domain not in results_by_domain:
                    results_by_domain[domain] = []
                results_by_domain[domain].append(artifact_data)

    except Exception as e:
        logger.warning(f"Failed to fetch user_added_relations for {anchor_type}:{anchor_id}: {e}")

    return results_by_domain


def _map_artefact_type_to_domain(artefact_type: str) -> str:
    """Map artefact type to domain grouping."""
    mapping = {
        "inventory_item": "inventory",
        "work_order": "work_orders",
        "fault": "faults",
        "shopping_item": "shopping",
        "shopping_list": "shopping",
        "document": "documents",
        "manual_section": "manuals",
        "email_message": "emails",
        "certificate": "certificates",
    }
    return mapping.get(artefact_type, "documents")


def _fetch_artifact_details(
    supabase: Client,
    artefact_type: str,
    artefact_id: str,
    yacht_id: UUID
) -> Optional[Dict[str, Any]]:
    """Fetch artifact details for user-added relation."""
    try:
        if artefact_type == "inventory_item":
            response = supabase.table("equipment").select("id, name, model, location").eq(
                "id", artefact_id
            ).eq("yacht_id", str(yacht_id)).maybe_single().execute()
            if response.data:
                return {
                    "artefact_type": "inventory_item",
                    "artefact_id": artefact_id,
                    "title": response.data["name"],
                    "subtitle": f"{response.data.get('model', '')} - {response.data.get('location', '')}",
                    "metadata": {}
                }

        elif artefact_type == "fault":
            response = supabase.table("faults").select("id, title, severity").eq(
                "id", artefact_id
            ).eq("yacht_id", str(yacht_id)).maybe_single().execute()
            if response.data:
                return {
                    "artefact_type": "fault",
                    "artefact_id": artefact_id,
                    "title": response.data["title"],
                    "subtitle": response.data["severity"],
                    "metadata": {}
                }

        elif artefact_type == "work_order":
            response = supabase.table("work_orders").select("id, number, title, status").eq(
                "id", artefact_id
            ).eq("yacht_id", str(yacht_id)).maybe_single().execute()
            if response.data:
                return {
                    "artefact_type": "work_order",
                    "artefact_id": artefact_id,
                    "title": f"{response.data['number']}: {response.data['title']}",
                    "subtitle": response.data["status"],
                    "metadata": {}
                }

        # Add other types as needed

    except Exception as e:
        logger.warning(f"Failed to fetch {artefact_type} {artefact_id}: {e}")

    return None


def get_related_artifacts(
    supabase: Client,
    anchor_type: str,
    anchor_id: UUID,
    yacht_id: UUID,
    allowed_domains: List[str]
) -> List[Dict[str, Any]]:
    """
    Get related artifacts using deterministic FK/JOIN queries + user relations.

    Returns groups in FIXED domain order.
    Omits domains silently if:
    - No FK path exists
    - Query fails
    - Permission denied
    """
    # Get FK-based relations
    fk_results = {}

    if anchor_type == "inventory_item":
        fk_results = get_related_for_equipment(supabase, anchor_id, yacht_id, allowed_domains)
    elif anchor_type == "fault":
        fk_results = get_related_for_fault(supabase, anchor_id, yacht_id, allowed_domains)
    elif anchor_type == "work_order":
        fk_results = get_related_for_work_order(supabase, anchor_id, yacht_id, allowed_domains)
    # Add other anchor types as needed (document, manual_section, etc.)

    # Get user-added relations
    user_results = get_user_added_relations(supabase, anchor_type, anchor_id, yacht_id, allowed_domains)

    # Merge results (FK + user-added)
    all_results = {}
    for domain in allowed_domains:
        items = []

        # Add FK-based items
        if domain in fk_results:
            items.extend(fk_results[domain])

        # Add user-added items
        if domain in user_results:
            items.extend(user_results[domain])

        # Deduplicate by artefact_id
        seen_ids = set()
        unique_items = []
        for item in items:
            if item["artefact_id"] not in seen_ids:
                seen_ids.add(item["artefact_id"])
                unique_items.append(item)

        if unique_items:
            all_results[domain] = unique_items[:20]  # Limit to 20 per domain

    # Return groups in FIXED domain order
    groups = []
    for domain in DOMAIN_ORDER:
        if domain in all_results:
            groups.append({
                "domain": domain,
                "items": all_results[domain]
            })

    return groups
