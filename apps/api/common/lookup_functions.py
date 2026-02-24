"""
CelesteOS - Yacht-Scoped Lookup Functions
==========================================

Provides yacht-scoped entity lookup functions for the prefill engine.

All lookups enforce RLS (Row-Level Security) by filtering on yacht_id.

Lookup behavior:
- 0 matches: Returns LookupResult(success=True, count=0, value=None)
- 1 match: Returns LookupResult(success=True, count=1, value=<uuid>)
- 2+ matches: Returns LookupResult(success=True, count=N, options=[{id, name, ...}])

The prefill engine uses this to:
1. Auto-populate UUID fields from entity names
2. Generate dropdown options when ambiguous
3. Warn users about missing or ambiguous entities
"""

from typing import Dict, List, Any, Optional
import logging
from uuid import UUID

from common.field_metadata import LookupResult

logger = logging.getLogger(__name__)


# =============================================================================
# EQUIPMENT LOOKUPS
# =============================================================================

async def lookup_equipment_by_name(
    name: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Lookup equipment by name with yacht_id scoping (RLS enforcement).

    Args:
        name: Equipment name to search for (case-insensitive partial match)
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with:
        - value: UUID if 1 match
        - options: List[Dict] if 2+ matches
        - count: Number of matches

    Example:
        result = await lookup_equipment_by_name("main engine", yacht_id, client)
        if result.count == 1:
            equipment_id = result.value
        elif result.count > 1:
            options = result.options  # Show dropdown to user
    """
    try:
        # Query equipment with yacht_id filter (RLS enforcement)
        # Use ilike for case-insensitive partial matching
        response = supabase_client.table("pms_equipment") \
            .select("id, name, category, location, manufacturer, model") \
            .eq("yacht_id", yacht_id) \
            .ilike("name", f"%{name}%") \
            .execute()

        results = response.data or []
        count = len(results)

        if count == 0:
            logger.info(f"[Lookup] Equipment '{name}' not found for yacht {yacht_id}")
            return LookupResult(success=True, count=0)

        elif count == 1:
            equipment = results[0]
            logger.info(f"[Lookup] Equipment '{name}' resolved to {equipment['id']}")
            return LookupResult(
                success=True,
                count=1,
                value=str(equipment["id"])
            )

        else:
            # Multiple matches - return options for dropdown
            logger.info(f"[Lookup] Equipment '{name}' matched {count} items")
            options = [
                {
                    "id": str(item["id"]),
                    "name": item["name"],
                    "category": item.get("category"),
                    "location": item.get("location"),
                    "manufacturer": item.get("manufacturer"),
                    "model": item.get("model"),
                }
                for item in results
            ]
            return LookupResult(
                success=True,
                count=count,
                options=options
            )

    except Exception as e:
        logger.error(f"[Lookup] Equipment lookup failed: {e}")
        return LookupResult(
            success=False,
            error=f"Equipment lookup failed: {str(e)}"
        )


async def lookup_equipment_by_id(
    equipment_id: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Verify equipment ID exists and belongs to yacht (RLS validation).

    Args:
        equipment_id: Equipment UUID
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with value=equipment_id if found, None otherwise
    """
    try:
        response = supabase_client.table("pms_equipment") \
            .select("id, name") \
            .eq("id", equipment_id) \
            .eq("yacht_id", yacht_id) \
            .execute()

        if response.data and len(response.data) > 0:
            return LookupResult(success=True, count=1, value=equipment_id)
        else:
            return LookupResult(success=True, count=0)

    except Exception as e:
        logger.error(f"[Lookup] Equipment ID validation failed: {e}")
        return LookupResult(success=False, error=str(e))


# =============================================================================
# FAULT LOOKUPS
# =============================================================================

async def lookup_fault_by_symptom(
    symptom: str,
    yacht_id: str,
    supabase_client,
    equipment_id: Optional[str] = None
) -> LookupResult:
    """
    Lookup fault by symptom with yacht_id scoping.

    Args:
        symptom: Symptom description to search for
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance
        equipment_id: Optional equipment filter

    Returns:
        LookupResult with fault UUID or options
    """
    try:
        query = supabase_client.table("pms_faults") \
            .select("id, fault_code, symptom, equipment_id, severity, resolved") \
            .eq("yacht_id", yacht_id) \
            .ilike("symptom", f"%{symptom}%")

        # Filter by equipment if provided
        if equipment_id:
            query = query.eq("equipment_id", equipment_id)

        response = query.execute()
        results = response.data or []
        count = len(results)

        if count == 0:
            return LookupResult(success=True, count=0)

        elif count == 1:
            fault = results[0]
            return LookupResult(success=True, count=1, value=str(fault["id"]))

        else:
            options = [
                {
                    "id": str(item["id"]),
                    "fault_code": item.get("fault_code"),
                    "symptom": item["symptom"],
                    "equipment_id": str(item.get("equipment_id")),
                    "severity": item.get("severity"),
                    "resolved": item.get("resolved"),
                }
                for item in results
            ]
            return LookupResult(success=True, count=count, options=options)

    except Exception as e:
        logger.error(f"[Lookup] Fault lookup failed: {e}")
        return LookupResult(success=False, error=str(e))


async def lookup_fault_by_code(
    fault_code: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Lookup fault by fault code (exact match).

    Args:
        fault_code: Fault code to search for
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with fault UUID or options
    """
    try:
        response = supabase_client.table("pms_faults") \
            .select("id, fault_code, symptom, equipment_id") \
            .eq("yacht_id", yacht_id) \
            .eq("fault_code", fault_code) \
            .execute()

        results = response.data or []
        count = len(results)

        if count == 0:
            return LookupResult(success=True, count=0)
        elif count == 1:
            return LookupResult(success=True, count=1, value=str(results[0]["id"]))
        else:
            options = [
                {
                    "id": str(item["id"]),
                    "fault_code": item["fault_code"],
                    "symptom": item["symptom"],
                    "equipment_id": str(item.get("equipment_id")),
                }
                for item in results
            ]
            return LookupResult(success=True, count=count, options=options)

    except Exception as e:
        logger.error(f"[Lookup] Fault code lookup failed: {e}")
        return LookupResult(success=False, error=str(e))


# =============================================================================
# PARTS LOOKUPS
# =============================================================================

async def lookup_part_by_name(
    name: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Lookup part by name with yacht_id scoping.

    Args:
        name: Part name to search for
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with part UUID or options
    """
    try:
        response = supabase_client.table("pms_parts") \
            .select("id, name, part_number, manufacturer, category, stock_level") \
            .eq("yacht_id", yacht_id) \
            .ilike("name", f"%{name}%") \
            .execute()

        results = response.data or []
        count = len(results)

        if count == 0:
            return LookupResult(success=True, count=0)
        elif count == 1:
            return LookupResult(success=True, count=1, value=str(results[0]["id"]))
        else:
            options = [
                {
                    "id": str(item["id"]),
                    "name": item["name"],
                    "part_number": item.get("part_number"),
                    "manufacturer": item.get("manufacturer"),
                    "category": item.get("category"),
                    "stock_level": item.get("stock_level"),
                }
                for item in results
            ]
            return LookupResult(success=True, count=count, options=options)

    except Exception as e:
        logger.error(f"[Lookup] Part name lookup failed: {e}")
        return LookupResult(success=False, error=str(e))


async def lookup_part_by_number(
    part_number: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Lookup part by part number (exact match).

    Args:
        part_number: Part number to search for
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with part UUID or options
    """
    try:
        response = supabase_client.table("pms_parts") \
            .select("id, name, part_number, manufacturer, stock_level") \
            .eq("yacht_id", yacht_id) \
            .eq("part_number", part_number) \
            .execute()

        results = response.data or []
        count = len(results)

        if count == 0:
            return LookupResult(success=True, count=0)
        elif count == 1:
            return LookupResult(success=True, count=1, value=str(results[0]["id"]))
        else:
            options = [
                {
                    "id": str(item["id"]),
                    "name": item["name"],
                    "part_number": item["part_number"],
                    "manufacturer": item.get("manufacturer"),
                    "stock_level": item.get("stock_level"),
                }
                for item in results
            ]
            return LookupResult(success=True, count=count, options=options)

    except Exception as e:
        logger.error(f"[Lookup] Part number lookup failed: {e}")
        return LookupResult(success=False, error=str(e))


# =============================================================================
# WORK ORDER LOOKUPS
# =============================================================================

async def lookup_work_order_by_number(
    wo_number: str,
    yacht_id: str,
    supabase_client
) -> LookupResult:
    """
    Lookup work order by WO number.

    Args:
        wo_number: Work order number
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance

    Returns:
        LookupResult with work order UUID or options
    """
    try:
        response = supabase_client.table("pms_work_orders") \
            .select("id, wo_number, title, status, priority") \
            .eq("yacht_id", yacht_id) \
            .eq("wo_number", wo_number) \
            .execute()

        results = response.data or []
        count = len(results)

        if count == 0:
            return LookupResult(success=True, count=0)
        elif count == 1:
            return LookupResult(success=True, count=1, value=str(results[0]["id"]))
        else:
            options = [
                {
                    "id": str(item["id"]),
                    "wo_number": item["wo_number"],
                    "title": item["title"],
                    "status": item.get("status"),
                    "priority": item.get("priority"),
                }
                for item in results
            ]
            return LookupResult(success=True, count=count, options=options)

    except Exception as e:
        logger.error(f"[Lookup] Work order lookup failed: {e}")
        return LookupResult(success=False, error=str(e))


# =============================================================================
# LOOKUP ROUTER
# =============================================================================

async def lookup_entity(
    entity_type: str,
    entity_value: str,
    yacht_id: str,
    supabase_client,
    context: Optional[Dict[str, Any]] = None
) -> LookupResult:
    """
    Generic entity lookup router.

    Dispatches to specialized lookup functions based on entity_type.

    Args:
        entity_type: Type of entity (equipment, part, fault, etc.)
        entity_value: Entity value to lookup
        yacht_id: Yacht UUID for RLS filtering
        supabase_client: Supabase client instance
        context: Optional context (e.g., equipment_id for fault lookup)

    Returns:
        LookupResult from specialized lookup function
    """
    entity_type_lower = entity_type.lower()

    # Equipment lookups
    if entity_type_lower in ["equipment", "equipment_name"]:
        return await lookup_equipment_by_name(entity_value, yacht_id, supabase_client)

    # Part lookups
    elif entity_type_lower in ["part", "part_name"]:
        return await lookup_part_by_name(entity_value, yacht_id, supabase_client)
    elif entity_type_lower == "part_number":
        return await lookup_part_by_number(entity_value, yacht_id, supabase_client)

    # Fault lookups
    elif entity_type_lower == "symptom":
        equipment_id = context.get("equipment_id") if context else None
        return await lookup_fault_by_symptom(
            entity_value, yacht_id, supabase_client, equipment_id
        )
    elif entity_type_lower == "fault_code":
        return await lookup_fault_by_code(entity_value, yacht_id, supabase_client)

    # Work order lookups
    elif entity_type_lower in ["work_order", "work_order_id", "wo_number"]:
        return await lookup_work_order_by_number(entity_value, yacht_id, supabase_client)

    else:
        logger.warning(f"[Lookup] Unknown entity type: {entity_type}")
        return LookupResult(
            success=False,
            error=f"Unsupported entity type: {entity_type}"
        )


__all__ = [
    "lookup_equipment_by_name",
    "lookup_equipment_by_id",
    "lookup_fault_by_symptom",
    "lookup_fault_by_code",
    "lookup_part_by_name",
    "lookup_part_by_number",
    "lookup_work_order_by_number",
    "lookup_entity",
]
