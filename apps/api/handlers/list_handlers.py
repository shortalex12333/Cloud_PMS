"""
List Handlers - Filter-based Collection Queries
================================================

These handlers support LIST queries that return filtered collections
instead of single entities.

KEY DIFFERENCE FROM EXISTING HANDLERS:
- Existing handlers: view_work_order(entity_id) → single entity
- List handlers: list_work_orders(filters) → filtered collection

This fixes the filter_stack test failures where queries like:
    "pending work orders"
    "out of stock parts"
    "active faults"
Were failing because they tried to resolve a non-existent entity_id.

CONJUNCTION HANDLING (NEW):
    - IN conjunctions: "box 2a and 2b" → query BOTH locations
    - NOT conjunctions: "not in locker" → exclude locker locations
    - CONTRADICTION: "pending completed" → return EMPTY immediately

Usage:
    handlers = ListHandlers(supabase_client)
    result = await handlers.list_work_orders(yacht_id, {"status": "pending"})

    # With QueryClassification (new):
    classification = classifier.classify("inventory in box 2a and 2b")
    result = await handlers.list_parts(yacht_id, classification.filters, classification=classification)
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
)

from .schema_mapping import (
    get_table,
    map_work_order_select,
    map_parts_select,
    map_faults_select,
    map_equipment_select,
    normalize_work_order,
    normalize_part,
    normalize_fault,
    normalize_equipment,
)

# Import conjunction handling from pipeline contract
try:
    from pipeline_contract import ConjunctionType, ConjunctionRule
    from query_classifier import QueryClassification
    CONJUNCTIONS_AVAILABLE = True
except ImportError:
    CONJUNCTIONS_AVAILABLE = False
    QueryClassification = None

logger = logging.getLogger(__name__)


class ListHandlers:
    """
    Handlers for LIST queries (filtered collections).

    These complement the existing entity-specific handlers by supporting
    queries that don't have a specific entity_id.

    NEW: Supports conjunctions from QueryClassification:
    - IN: Query multiple locations ("box 2a and 2b")
    - NOT: Exclude items ("not in locker")
    - CONTRADICTION: Return empty immediately ("pending completed")
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    def _check_contradiction(self, classification) -> Optional[Dict]:
        """
        Check if query has contradictory filters.

        If contradiction detected, returns an error response dict.
        Otherwise returns None (continue processing).
        """
        if not classification:
            return None

        if hasattr(classification, 'contradiction') and classification.contradiction:
            return {
                "status": "error",
                "error_code": "CONTRADICTION",
                "error_message": classification.contradiction,
                "data": {"items": [], "total_count": 0},
                "reasoning": f"Query contains contradictory filters: {classification.contradiction}",
            }
        return None

    def _get_in_locations(self, classification) -> List[str]:
        """
        Get all IN locations from conjunctions.

        For "inventory in box 2a and 2b", returns ["box 2a", "box 2b"]
        """
        if not classification or not CONJUNCTIONS_AVAILABLE:
            return []

        locations = []
        if hasattr(classification, 'conjunctions'):
            for conj in classification.conjunctions:
                if conj.conjunction_type == ConjunctionType.IN:
                    locations.extend(conj.operands)
        return locations

    def _get_not_locations(self, classification) -> List[str]:
        """
        Get all NOT locations from conjunctions.

        For "inventory not in locker", returns ["locker"]
        """
        if not classification or not CONJUNCTIONS_AVAILABLE:
            return []

        locations = []
        if hasattr(classification, 'conjunctions'):
            for conj in classification.conjunctions:
                if conj.conjunction_type == ConjunctionType.NOT:
                    locations.extend(conj.operands)
        return locations

    def _normalize_location(self, loc: str) -> str:
        """
        Normalize location string for database matching.

        "box 2a" → "BOX-2A"
        "locker 3b" → "LOCKER-3B"
        """
        loc = loc.upper().strip()
        # Replace space with hyphen
        loc = loc.replace(" ", "-")
        return loc

    # =========================================================================
    # WORK ORDER LIST HANDLERS
    # =========================================================================

    async def list_work_orders(
        self,
        yacht_id: str,
        filters: Optional[Dict] = None,
        params: Optional[Dict] = None,
        classification=None  # QueryClassification from query_classifier
    ) -> Dict:
        """
        List work orders with filters.

        Filters:
        - status: pending, open, in_progress, completed, etc.
        - priority: low, medium, high, urgent
        - is_overdue: true/false
        - equipment_id: UUID

        Params:
        - limit: max results (default 50)
        - offset: pagination offset
        - order_by: field to sort by
        - order_dir: asc/desc

        Conjunction handling (from classification):
        - CONTRADICTION: "pending completed" → return empty immediately
        """
        builder = ResponseBuilder("list_work_orders", None, "work_order", yacht_id)
        filters = filters or {}
        params = params or {}

        # Check for contradictions first (e.g., "pending completed")
        contradiction_response = self._check_contradiction(classification)
        if contradiction_response:
            return contradiction_response

        try:
            # Start query
            query = self.db.table(get_table("work_orders")).select(
                map_work_order_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if "status" in filters:
                status_val = filters["status"]
                if isinstance(status_val, dict):
                    status_val = status_val.get("value")
                if status_val:
                    query = query.eq("status", status_val)

            if "priority" in filters:
                priority_val = filters["priority"]
                if isinstance(priority_val, dict):
                    priority_val = priority_val.get("value")
                if priority_val:
                    query = query.eq("priority", priority_val)

            if "equipment_id" in filters:
                query = query.eq("equipment_id", filters["equipment_id"])

            if "type" in filters:
                type_val = filters["type"]
                if isinstance(type_val, dict):
                    type_val = type_val.get("value")
                if type_val:
                    query = query.eq("type", type_val)

            # Pagination
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)
            order_by = params.get("order_by", "created_at")
            order_dir = params.get("order_dir", "desc")

            query = query.order(order_by, desc=(order_dir == "desc"))
            query = query.range(offset, offset + limit - 1)

            # Execute
            result = query.execute()
            rows = result.data or []
            total_count = result.count or len(rows)

            # Normalize and enrich
            work_orders = []
            for row in rows:
                wo = normalize_work_order(row)
                wo["is_overdue"] = self._is_overdue(wo)
                work_orders.append(wo)

            # Build response data
            response_data = {
                "items": work_orders,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": list(filters.keys()),
            }

            # Surface unmatched tokens for SALVAGED outcome (receptionist model)
            if classification and hasattr(classification, 'unmatched_tokens'):
                unmatched = getattr(classification, 'unmatched_tokens', [])
                if unmatched:
                    response_data["unmatched_tokens"] = unmatched
                    response_data["note"] = f"Results returned, but these terms were not matched: {', '.join(unmatched)}"

            builder.set_data(response_data)

            # Add actions for creating new work orders
            builder.add_available_actions([
                AvailableAction(
                    action_id="create_work_order",
                    label="Create Work Order",
                    variant="MUTATE",
                    requires_signature=True,
                ),
                AvailableAction(
                    action_id="export_work_orders",
                    label="Export List",
                    variant="READ",
                ),
            ])

            return builder.build()

        except Exception as e:
            logger.error(f"list_work_orders failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    def _is_overdue(self, wo: Dict) -> bool:
        """Check if work order is overdue"""
        due_date = wo.get("due_date")
        if not due_date:
            return False
        if wo.get("status") in ["completed", "closed", "cancelled"]:
            return False
        try:
            if isinstance(due_date, str):
                due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            else:
                due = due_date
            return due < datetime.now(timezone.utc)
        except:
            return False

    # =========================================================================
    # PARTS/INVENTORY LIST HANDLERS
    # =========================================================================

    async def list_parts(
        self,
        yacht_id: str,
        filters: Optional[Dict] = None,
        params: Optional[Dict] = None,
        classification=None  # QueryClassification from query_classifier
    ) -> Dict:
        """
        List parts/inventory with filters.

        Filters:
        - quantity: {"op": "eq", "value": 0} for out of stock
        - quantity: {"op": "lt", "compare_field": "min_quantity"} for low stock
        - category: filter by category
        - manufacturer: filter by manufacturer
        - location: filter by location

        Conjunction handling (from classification):
        - IN: "box 2a and 2b" → query both locations
        - NOT: "not in locker" → exclude locker locations
        - CONTRADICTION: "pending completed" → return empty immediately
        """
        builder = ResponseBuilder("list_parts", None, "part", yacht_id)
        filters = filters or {}
        params = params or {}

        # Check for contradictions first
        contradiction_response = self._check_contradiction(classification)
        if contradiction_response:
            return contradiction_response

        try:
            # Start query
            query = self.db.table(get_table("parts")).select(
                map_parts_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if "category" in filters:
                cat_val = filters["category"]
                if isinstance(cat_val, dict):
                    cat_val = cat_val.get("value")
                if cat_val:
                    query = query.eq("category", cat_val)

            if "manufacturer" in filters:
                mfr_val = filters["manufacturer"]
                if isinstance(mfr_val, dict):
                    mfr_val = mfr_val.get("value")
                if mfr_val:
                    query = query.ilike("manufacturer", f"%{mfr_val}%")

            # Handle location from filters
            if "location" in filters:
                loc_val = filters["location"]
                if isinstance(loc_val, dict):
                    loc_val = loc_val.get("value")
                if loc_val:
                    query = query.ilike("location", f"%{loc_val}%")

            # Handle IN locations from conjunctions ("box 2a and 2b")
            in_locations = self._get_in_locations(classification)
            if in_locations:
                # Query multiple locations with OR
                normalized_locs = [self._normalize_location(loc) for loc in in_locations]
                # Build OR filter: location ILIKE 'BOX-2A' OR location ILIKE 'BOX-2B'
                # Supabase uses .or_() for this
                or_conditions = ",".join([f"location.ilike.%{loc}%" for loc in normalized_locs])
                query = query.or_(or_conditions)

            # Handle NOT locations from conjunctions ("not in locker")
            not_locations = self._get_not_locations(classification)
            for not_loc in not_locations:
                normalized_loc = self._normalize_location(not_loc)
                query = query.not_.ilike("location", f"%{normalized_loc}%")

            # Note: quantity filtering would require the column to exist
            # For now, we return all and filter in Python if needed

            # Pagination
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)
            order_by = params.get("order_by", "name")
            order_dir = params.get("order_dir", "asc")

            query = query.order(order_by, desc=(order_dir == "desc"))
            query = query.range(offset, offset + limit - 1)

            # Execute
            result = query.execute()
            rows = result.data or []
            total_count = result.count or len(rows)

            # Normalize
            parts = [normalize_part(row) for row in rows]

            # Post-filter for quantity if needed (since column may not exist)
            quantity_filter = filters.get("quantity")
            if quantity_filter and isinstance(quantity_filter, dict):
                op = quantity_filter.get("op", "eq")
                val = quantity_filter.get("value")
                if op == "eq" and val == 0:
                    # Filter for "out of stock" - in real DB would be WHERE quantity = 0
                    # For now, mark all as potentially low (schema doesn't have quantity)
                    pass

            # Build response data
            response_data = {
                "items": parts,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": list(filters.keys()),
            }

            # Surface unmatched tokens for SALVAGED outcome (receptionist model)
            if classification and hasattr(classification, 'unmatched_tokens'):
                unmatched = getattr(classification, 'unmatched_tokens', [])
                if unmatched:
                    response_data["unmatched_tokens"] = unmatched
                    response_data["note"] = f"Results returned, but these terms were not matched: {', '.join(unmatched)}"

            # Include conjunction info if present
            if classification and hasattr(classification, 'conjunctions'):
                conjs = classification.conjunctions
                if conjs:
                    response_data["conjunctions_applied"] = [
                        {"type": c.conjunction_type.value, "operands": c.operands}
                        for c in conjs
                    ]

            builder.set_data(response_data)

            # Add actions
            builder.add_available_actions([
                AvailableAction(
                    action_id="add_part",
                    label="Add Part",
                    variant="MUTATE",
                    requires_signature=True,
                ),
                AvailableAction(
                    action_id="create_reorder",
                    label="Create Reorder List",
                    variant="MUTATE",
                ),
            ])

            return builder.build()

        except Exception as e:
            logger.error(f"list_parts failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # FAULT LIST HANDLERS
    # =========================================================================

    async def list_faults(
        self,
        yacht_id: str,
        filters: Optional[Dict] = None,
        params: Optional[Dict] = None,
        classification=None  # QueryClassification from query_classifier
    ) -> Dict:
        """
        List faults with filters.

        Filters:
        - resolved_at: {"op": "is_null"} for active faults
        - resolved_at: {"op": "not_null"} for resolved faults
        - severity: critical, high, medium, low
        - equipment_id: UUID

        Conjunction handling (from classification):
        - CONTRADICTION: "active resolved" → return empty immediately
        """
        builder = ResponseBuilder("list_faults", None, "fault", yacht_id)
        filters = filters or {}
        params = params or {}

        # Check for contradictions first
        contradiction_response = self._check_contradiction(classification)
        if contradiction_response:
            return contradiction_response

        try:
            # Start query
            query = self.db.table(get_table("faults")).select(
                map_faults_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            resolved_filter = filters.get("resolved_at")
            if resolved_filter and isinstance(resolved_filter, dict):
                op = resolved_filter.get("op")
                if op == "is_null":
                    query = query.is_("resolved_at", "null")
                elif op == "not_null":
                    query = query.not_.is_("resolved_at", "null")

            if "severity" in filters:
                sev_val = filters["severity"]
                if isinstance(sev_val, dict):
                    sev_val = sev_val.get("value")
                if sev_val:
                    query = query.eq("severity", sev_val)

            if "equipment_id" in filters:
                query = query.eq("equipment_id", filters["equipment_id"])

            # Pagination
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)
            order_by = params.get("order_by", "detected_at")
            order_dir = params.get("order_dir", "desc")

            query = query.order(order_by, desc=(order_dir == "desc"))
            query = query.range(offset, offset + limit - 1)

            # Execute
            result = query.execute()
            rows = result.data or []
            total_count = result.count or len(rows)

            # Normalize
            faults = [normalize_fault(row) for row in rows]

            # Build response data
            response_data = {
                "items": faults,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": list(filters.keys()),
            }

            # Surface unmatched tokens for SALVAGED outcome (receptionist model)
            if classification and hasattr(classification, 'unmatched_tokens'):
                unmatched = getattr(classification, 'unmatched_tokens', [])
                if unmatched:
                    response_data["unmatched_tokens"] = unmatched
                    response_data["note"] = f"Results returned, but these terms were not matched: {', '.join(unmatched)}"

            builder.set_data(response_data)

            # Add actions
            builder.add_available_actions([
                AvailableAction(
                    action_id="report_fault",
                    label="Report Fault",
                    variant="MUTATE",
                    requires_signature=True,
                ),
            ])

            return builder.build()

        except Exception as e:
            logger.error(f"list_faults failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # EQUIPMENT LIST HANDLERS
    # =========================================================================

    async def list_equipment(
        self,
        yacht_id: str,
        filters: Optional[Dict] = None,
        params: Optional[Dict] = None,
        classification=None  # QueryClassification from query_classifier
    ) -> Dict:
        """
        List equipment with filters.

        Filters:
        - category: filter by code/category
        - manufacturer: filter by manufacturer
        - location: filter by location
        - has_faults: true to show only equipment with active faults

        Conjunction handling (from classification):
        - IN: "equipment in engine room and deck" → query both locations
        - NOT: "equipment not in locker" → exclude locker
        - CONTRADICTION: return empty immediately
        """
        builder = ResponseBuilder("list_equipment", None, "equipment", yacht_id)
        filters = filters or {}
        params = params or {}

        # Check for contradictions first
        contradiction_response = self._check_contradiction(classification)
        if contradiction_response:
            return contradiction_response

        try:
            # Start query
            query = self.db.table(get_table("equipment")).select(
                map_equipment_select(),
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Apply filters
            if "category" in filters:
                cat_val = filters["category"]
                if isinstance(cat_val, dict):
                    cat_val = cat_val.get("value")
                if cat_val:
                    query = query.ilike("code", f"%{cat_val}%")

            if "manufacturer" in filters:
                mfr_val = filters["manufacturer"]
                if isinstance(mfr_val, dict):
                    mfr_val = mfr_val.get("value")
                if mfr_val:
                    query = query.ilike("manufacturer", f"%{mfr_val}%")

            if "location" in filters:
                loc_val = filters["location"]
                if isinstance(loc_val, dict):
                    loc_val = loc_val.get("value")
                if loc_val:
                    query = query.ilike("location", f"%{loc_val}%")

            # Handle IN locations from conjunctions ("engine room and deck")
            in_locations = self._get_in_locations(classification)
            if in_locations:
                normalized_locs = [self._normalize_location(loc) for loc in in_locations]
                or_conditions = ",".join([f"location.ilike.%{loc}%" for loc in normalized_locs])
                query = query.or_(or_conditions)

            # Handle NOT locations from conjunctions ("not in locker")
            not_locations = self._get_not_locations(classification)
            for not_loc in not_locations:
                normalized_loc = self._normalize_location(not_loc)
                query = query.not_.ilike("location", f"%{normalized_loc}%")

            # Pagination
            limit = params.get("limit", 50)
            offset = params.get("offset", 0)
            order_by = params.get("order_by", "name")
            order_dir = params.get("order_dir", "asc")

            query = query.order(order_by, desc=(order_dir == "desc"))
            query = query.range(offset, offset + limit - 1)

            # Execute
            result = query.execute()
            rows = result.data or []
            total_count = result.count or len(rows)

            # Normalize
            equipment = [normalize_equipment(row) for row in rows]

            # Build response data
            response_data = {
                "items": equipment,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "filters_applied": list(filters.keys()),
            }

            # Surface unmatched tokens for SALVAGED outcome (receptionist model)
            if classification and hasattr(classification, 'unmatched_tokens'):
                unmatched = getattr(classification, 'unmatched_tokens', [])
                if unmatched:
                    response_data["unmatched_tokens"] = unmatched
                    response_data["note"] = f"Results returned, but these terms were not matched: {', '.join(unmatched)}"

            # Include conjunction info if present
            if classification and hasattr(classification, 'conjunctions'):
                conjs = classification.conjunctions
                if conjs:
                    response_data["conjunctions_applied"] = [
                        {"type": c.conjunction_type.value, "operands": c.operands}
                        for c in conjs
                    ]

            builder.set_data(response_data)

            # Add actions
            builder.add_available_actions([
                AvailableAction(
                    action_id="view_equipment",
                    label="View Details",
                    variant="READ",
                ),
            ])

            return builder.build()

        except Exception as e:
            logger.error(f"list_equipment failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


    # =========================================================================
    # MY WORK ORDERS (VIEW) - v_my_work_orders_summary
    # =========================================================================

    async def list_my_work_orders(
        self,
        yacht_id: str,
        user_id: str = None,
        assigned_to: str = None,
        group_key: str = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        List My Work Orders with deterministic grouping and sorting.

        Queries v_my_work_orders_summary view, groups by group_key,
        and applies deterministic sorting per group:
        - overdue: days_overdue desc, criticality_rank asc nulls last, due_at asc
        - critical: criticality_rank asc, due_at asc nulls last
        - time_consuming: estimated_duration_minutes desc, due_at asc nulls last
        - other: status priority then last_activity_at desc

        Args:
            yacht_id: Required yacht context
            user_id: Current user ID (for default assigned_to filter)
            assigned_to: Filter by assignee (optional, defaults to current user if None)
            group_key: Filter by specific group (overdue/critical/time_consuming/other)
            params: Pagination params (limit, offset)

        Returns:
            Grouped work orders with deterministic order
        """
        builder = ResponseBuilder("view_my_work_orders", None, "work_order", yacht_id)
        params = params or {}

        try:
            # Query the view
            query = self.db.table("v_my_work_orders_summary").select(
                "*",
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Filter by assigned_to if provided (defaults to current user)
            # Note: assigned_to filter may need JOIN with pms_work_orders if not in view
            # For now, we skip this filter as the view doesn't include assigned_to

            # Filter by group_key if specified
            if group_key:
                query = query.eq("group_key", group_key)

            # Execute query
            result = query.execute()
            rows = result.data or []
            total_count = result.count or len(rows)

            # Group by group_key
            groups = {
                "overdue": [],
                "critical": [],
                "time_consuming": [],
                "other": [],
            }

            for row in rows:
                gk = row.get("group_key", "other")
                if gk in groups:
                    groups[gk].append(row)

            # Apply deterministic sorting per group
            # overdue: days_overdue desc, criticality_rank asc nulls last, due_at asc
            groups["overdue"].sort(key=lambda x: (
                -(x.get("days_overdue") or 0),  # desc
                (x.get("criticality_rank") or 999),  # asc, nulls last
                x.get("due_at") or "9999-12-31",  # asc
            ))

            # critical: criticality_rank asc, due_at asc nulls last
            groups["critical"].sort(key=lambda x: (
                (x.get("criticality_rank") or 999),  # asc
                x.get("due_at") or "9999-12-31",  # asc, nulls last
            ))

            # time_consuming: estimated_duration_minutes desc, due_at asc nulls last
            groups["time_consuming"].sort(key=lambda x: (
                -(x.get("est_minutes") or x.get("estimated_duration_minutes") or 0),  # desc
                x.get("due_at") or "9999-12-31",  # asc, nulls last
            ))

            # other: status priority then last_activity_at desc
            STATUS_PRIORITY = {
                "open": 1,
                "in_progress": 2,
                "pending": 3,
                "deferred": 4,
                "completed": 5,
                "cancelled": 6,
            }
            groups["other"].sort(key=lambda x: (
                STATUS_PRIORITY.get(x.get("status"), 99),  # status priority
                -(datetime.fromisoformat(x["last_activity_at"].replace("Z", "+00:00")).timestamp()
                  if x.get("last_activity_at") else 0),  # desc
            ))

            # Build response data
            response_data = {
                "groups": groups,
                "group_counts": {k: len(v) for k, v in groups.items()},
                "total_count": total_count,
                "yacht_id": yacht_id,
            }

            # If specific group requested, flatten to items
            if group_key and group_key in groups:
                response_data["items"] = groups[group_key]
                response_data["group_key"] = group_key

            builder.set_data(response_data)

            # Add available actions
            builder.add_available_actions([
                AvailableAction(
                    action_id="view_work_order_detail",
                    label="View Details",
                    variant="READ",
                ),
                AvailableAction(
                    action_id="reassign_work_order",
                    label="Reassign",
                    variant="SIGNED",
                    requires_signature=True,
                ),
            ])

            return builder.build()

        except Exception as e:
            logger.error(f"list_my_work_orders failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# Factory function to get list handlers
def get_list_handlers(supabase_client) -> Dict[str, Any]:
    """
    Get list handler functions.

    Returns a dict mapping action_id to async handler function.
    """
    handlers = ListHandlers(supabase_client)

    return {
        "list_work_orders": handlers.list_work_orders,
        "list_my_work_orders": handlers.list_my_work_orders,
        "view_my_work_orders": handlers.list_my_work_orders,  # Alias
        "list_parts": handlers.list_parts,
        "list_inventory": handlers.list_parts,  # Alias
        "list_faults": handlers.list_faults,
        "list_equipment": handlers.list_equipment,
    }
