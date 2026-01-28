# Part Lens v2 — Phased Implementation Plan

**Branch**: `parts/part-lens-v2-backend_472103`
**Base Branch**: `main`
**Author**: Part Lens Worker
**Date**: 2026-01-27
**Status**: PLANNING

---

## Executive Summary

This document outlines the phased backend implementation for Part Lens v2, enabling intent-first inventory management through the Celeste action router. The implementation follows the proven Certificate Lens GOLD pattern and integrates with existing infrastructure.

**Parallel Worker Context**: This work runs alongside 7 other workers. All changes are isolated to the `parts/` branch until PR review.

---

## Phase 0: Branch Setup & Foundation

### 0.1 Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b parts/part-lens-v2-backend_472103
```

### 0.2 Verify Blockers Resolved

| Blocker | Table | Status | Action |
|---------|-------|--------|--------|
| B1 | `pms_inventory_transactions` | DONE | RLS migration created |
| B2 | `pms_parts` | VERIFY | Confirm RLS enabled |
| B3 | `pms_shopping_list_items` | VERIFY | Confirm RLS enabled |

### 0.3 Pre-Flight Checks
```bash
# Verify Docker test environment
cd apps/api && docker compose up -d
pytest tests/test_health.py -v

# Verify DB connection
python -c "from action_router.dispatchers.internal_dispatcher import get_supabase_client; print(get_supabase_client())"
```

---

## Phase 1: Extend ActionDefinition with `field_metadata`

### 1.1 Add FieldClassification Enum

**File**: `apps/api/action_router/registry.py`

```python
# Add after ActionVariant enum (line ~27)

class FieldClassification(str, Enum):
    """Field classification for auto-population."""
    REQUIRED = "REQUIRED"           # Must be provided by user
    OPTIONAL = "OPTIONAL"           # May be provided by user
    BACKEND_AUTO = "BACKEND_AUTO"   # Computed by backend (prefill)
    CONTEXT = "CONTEXT"             # From auth/session context

@dataclass
class FieldMetadata:
    """Metadata for a single field."""
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None  # e.g., "equipment", "part", "query_text"
    lookup_required: bool = False              # Requires yacht-scoped lookup
    description: Optional[str] = None          # Human-readable description
```

### 1.2 Extend ActionDefinition

**File**: `apps/api/action_router/registry.py`

```python
# Update ActionDefinition.__init__ (line ~32)

class ActionDefinition:
    """Definition of a single action."""

    def __init__(
        self,
        action_id: str,
        label: str,
        endpoint: str,
        handler_type: HandlerType,
        method: str = "POST",
        allowed_roles: List[str] = None,
        required_fields: List[str] = None,
        schema_file: str = None,
        domain: str = None,
        variant: ActionVariant = ActionVariant.MUTATE,
        search_keywords: List[str] = None,
        field_metadata: List[FieldMetadata] = None,  # NEW
        prefill_endpoint: str = None,                  # NEW - for two-phase actions
    ):
        # ... existing assignments ...
        self.field_metadata = field_metadata or []
        self.prefill_endpoint = prefill_endpoint
```

### 1.3 Add Field Metadata Helper Functions

**File**: `apps/api/action_router/registry.py`

```python
# Add after search_actions function (line ~850)

def get_prefillable_fields(action_id: str) -> List[Dict[str, Any]]:
    """
    Get fields that can be auto-populated for an action.

    Returns list of field metadata for BACKEND_AUTO and CONTEXT fields.
    """
    action = get_action(action_id)
    return [
        {
            "name": fm.name,
            "classification": fm.classification.value,
            "auto_populate_from": fm.auto_populate_from,
            "lookup_required": fm.lookup_required,
        }
        for fm in action.field_metadata
        if fm.classification in (FieldClassification.BACKEND_AUTO, FieldClassification.CONTEXT)
    ]


def get_required_user_fields(action_id: str) -> List[str]:
    """Get fields that must be provided by the user."""
    action = get_action(action_id)
    return [
        fm.name
        for fm in action.field_metadata
        if fm.classification == FieldClassification.REQUIRED
    ]
```

### 1.4 Update Exports

**File**: `apps/api/action_router/registry.py`

```python
__all__ = [
    # ... existing exports ...
    "FieldClassification",
    "FieldMetadata",
    "get_prefillable_fields",
    "get_required_user_fields",
]
```

---

## Phase 2: Register Part Lens Actions

### 2.1 Add Part Lens Actions to Registry

**File**: `apps/api/action_router/registry.py`

Add after Certificate Actions section (around line ~607):

```python
    # ========================================================================
    # PARTS/INVENTORY ACTIONS (Part Lens v2)
    # ========================================================================

    "add_to_shopping_list": ActionDefinition(
        action_id="add_to_shopping_list",
        label="Add to Shopping List",
        endpoint="/v1/parts/shopping-list/add",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity_requested"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "shopping", "list", "order", "request", "part", "buy", "purchase", "need"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("part_name", FieldClassification.BACKEND_AUTO, auto_populate_from="part"),
            FieldMetadata("quantity_requested", FieldClassification.BACKEND_AUTO, auto_populate_from="stock_calculation"),
            FieldMetadata("urgency", FieldClassification.OPTIONAL),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
        prefill_endpoint="/v1/parts/shopping-list/prefill",
    ),

    "consume_part": ActionDefinition(
        action_id="consume_part",
        label="Consume Part",
        endpoint="/v1/parts/consume",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity", "work_order_id"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["consume", "use", "part", "install", "fit", "work", "order"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED),
            FieldMetadata("work_order_id", FieldClassification.OPTIONAL, auto_populate_from="work_order", lookup_required=True),
            FieldMetadata("location_id", FieldClassification.BACKEND_AUTO, auto_populate_from="part"),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "adjust_stock_quantity": ActionDefinition(
        action_id="adjust_stock_quantity",
        label="Adjust Stock",
        endpoint="/v1/parts/adjust-stock",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "new_quantity", "reason"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["adjust", "stock", "count", "inventory", "correct", "fix", "quantity", "update"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("current_quantity", FieldClassification.BACKEND_AUTO, auto_populate_from="part"),
            FieldMetadata("new_quantity", FieldClassification.REQUIRED),
            FieldMetadata("reason", FieldClassification.REQUIRED),
            FieldMetadata("location_id", FieldClassification.OPTIONAL),
        ],
        prefill_endpoint="/v1/parts/adjust-stock/prefill",
    ),

    "receive_part": ActionDefinition(
        action_id="receive_part",
        label="Receive Part",
        endpoint="/v1/parts/receive",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity_received"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["receive", "delivery", "arrived", "part", "stock", "in", "add"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity_received", FieldClassification.REQUIRED),
            FieldMetadata("supplier_id", FieldClassification.OPTIONAL, lookup_required=True),
            FieldMetadata("invoice_number", FieldClassification.OPTIONAL),
            FieldMetadata("location_id", FieldClassification.OPTIONAL, auto_populate_from="part"),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "transfer_part": ActionDefinition(
        action_id="transfer_part",
        label="Transfer Part",
        endpoint="/v1/parts/transfer",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity", "from_location_id", "to_location_id"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["transfer", "move", "part", "location", "relocate", "shift"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED),
            FieldMetadata("from_location_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("to_location_id", FieldClassification.REQUIRED, lookup_required=True),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "mark_part_critical": ActionDefinition(
        action_id="mark_part_critical",
        label="Mark as Critical",
        endpoint="/v1/parts/mark-critical",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "is_critical", "reason", "signature"],
        domain="parts",
        variant=ActionVariant.SIGNED,
        search_keywords=["critical", "essential", "important", "part", "safety", "mark", "flag"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("is_critical", FieldClassification.REQUIRED),
            FieldMetadata("reason", FieldClassification.REQUIRED),
            FieldMetadata("signature", FieldClassification.REQUIRED),
        ],
    ),

    "view_part_details": ActionDefinition(
        action_id="view_part_details",
        label="View Part Details",
        endpoint="/v1/parts/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "part_id"],
        domain="parts",
        variant=ActionVariant.READ,
        search_keywords=["view", "part", "details", "info", "stock", "see", "show"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
        ],
    ),

    "view_low_stock": ActionDefinition(
        action_id="view_low_stock",
        label="View Low Stock",
        endpoint="/v1/parts/low-stock",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["bosun", "eto", "chief_engineer", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="parts",
        variant=ActionVariant.READ,
        search_keywords=["low", "stock", "reorder", "minimum", "parts", "alert", "warning"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("threshold_percent", FieldClassification.OPTIONAL),
        ],
    ),
```

### 2.2 Update Action Count in Header Comment

Update line ~60 comment to reflect new action count:
```python
# ACTION REGISTRY - PRODUCTION VERIFIED (38 ACTIONS)  # Was 30
```

---

## Phase 3: Create Part Handlers

### 3.1 Create Handler File

**File**: `apps/api/handlers/part_handlers.py`

```python
"""
Part/Inventory Domain Handlers
==============================

Handlers for part/inventory actions (Part Lens v2).

READ Handlers:
- view_part_details: View part details with stock levels
- view_low_stock: List parts below minimum threshold

MUTATION Handlers:
- add_to_shopping_list: Add part to shopping list
- consume_part: Consume part for work order
- adjust_stock_quantity: Manual stock adjustment
- receive_part: Receive delivered parts
- transfer_part: Transfer between locations
- mark_part_critical: Mark part as critical (SIGNED)

All handlers return standardized ActionResponseEnvelope.
All mutations write to pms_audit_log with signature invariant.
All mutations create pms_inventory_transactions records.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging
import uuid as uuid_lib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
)

logger = logging.getLogger(__name__)


class PartHandlers:
    """Part/Inventory domain handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # READ HANDLERS
    # =========================================================================

    async def view_part_details(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View part details including stock levels and linked equipment.
        """
        builder = ResponseBuilder("view_part_details", entity_id, "part", yacht_id)

        try:
            # Get part with current stock
            result = self.db.table("pms_parts").select(
                "*, pms_part_stock_levels(*)"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            part = result.data
            stock = part.get("pms_part_stock_levels", [{}])[0] if part.get("pms_part_stock_levels") else {}

            # Compute stock status
            on_hand = stock.get("on_hand_qty", 0) or 0
            min_qty = stock.get("min_qty", 0) or 0
            is_low_stock = on_hand <= min_qty and min_qty > 0
            is_out_of_stock = on_hand == 0

            part_data = {
                "id": part.get("id"),
                "name": part.get("name"),
                "part_number": part.get("part_number"),
                "description": part.get("description"),
                "category": part.get("category"),
                "manufacturer": part.get("manufacturer"),
                "is_critical": part.get("is_critical", False),
                "stock": {
                    "on_hand": on_hand,
                    "min_qty": min_qty,
                    "max_qty": stock.get("max_qty"),
                    "location_id": stock.get("location_id"),
                    "is_low_stock": is_low_stock,
                    "is_out_of_stock": is_out_of_stock,
                },
            }

            builder.set_data(part_data)

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="consume_part",
                label="Consume",
                variant="MUTATE",
                icon="minus-circle"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_to_shopping_list",
                label="Add to Shopping",
                variant="MUTATE",
                icon="shopping-cart",
                is_primary=is_low_stock
            ))
            builder.add_available_action(AvailableAction(
                action_id="adjust_stock_quantity",
                label="Adjust Stock",
                variant="MUTATE",
                icon="edit"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_part_details failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_low_stock(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View parts below minimum stock threshold.
        """
        builder = ResponseBuilder("view_low_stock", entity_id, "part", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)

            # Query parts with stock below minimum
            # Using raw SQL-style query for the comparison
            result = self.db.table("pms_parts").select(
                "id, name, part_number, is_critical, pms_part_stock_levels(on_hand_qty, min_qty, location_id)",
                count="exact"
            ).eq("yacht_id", yacht_id).range(offset, offset + limit - 1).execute()

            parts = result.data or []

            # Filter to low stock in Python (Supabase doesn't support cross-table comparisons easily)
            low_stock_parts = []
            for part in parts:
                stock = part.get("pms_part_stock_levels", [{}])[0] if part.get("pms_part_stock_levels") else {}
                on_hand = stock.get("on_hand_qty", 0) or 0
                min_qty = stock.get("min_qty", 0) or 0

                if min_qty > 0 and on_hand <= min_qty:
                    low_stock_parts.append({
                        "id": part.get("id"),
                        "name": part.get("name"),
                        "part_number": part.get("part_number"),
                        "is_critical": part.get("is_critical", False),
                        "on_hand": on_hand,
                        "min_qty": min_qty,
                        "shortage": min_qty - on_hand,
                    })

            # Sort: critical first, then by shortage
            low_stock_parts.sort(key=lambda p: (not p.get("is_critical"), -p.get("shortage", 0)))

            builder.set_data({
                "parts": low_stock_parts,
                "total_low_stock": len(low_stock_parts),
                "critical_count": len([p for p in low_stock_parts if p.get("is_critical")]),
            })

            builder.set_pagination(offset, limit, len(low_stock_parts))

            return builder.build()

        except Exception as e:
            logger.error(f"view_low_stock failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # PREFILL HANDLERS (for two-phase actions)
    # =========================================================================

    async def prefill_add_to_shopping_list(
        self,
        yacht_id: str,
        part_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Compute prefill values for add_to_shopping_list action.

        Auto-calculates: quantity_requested = min_qty - on_hand_qty + safety_buffer
        """
        try:
            # Get part with stock levels
            result = self.db.table("pms_parts").select(
                "id, name, part_number, pms_part_stock_levels(on_hand_qty, min_qty, max_qty)"
            ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

            if not result.data:
                raise ValueError(f"Part not found: {part_id}")

            part = result.data
            stock = part.get("pms_part_stock_levels", [{}])[0] if part.get("pms_part_stock_levels") else {}

            on_hand = stock.get("on_hand_qty", 0) or 0
            min_qty = stock.get("min_qty", 0) or 0
            max_qty = stock.get("max_qty") or (min_qty * 2)  # Default max = 2x min

            # Calculate suggested quantity
            # Target: bring stock to max_qty (or min + 20% buffer if no max)
            if max_qty:
                suggested_qty = max(0, max_qty - on_hand)
            else:
                buffer = int(min_qty * 0.2) or 1
                suggested_qty = max(0, (min_qty + buffer) - on_hand)

            return {
                "status": "success",
                "prefill": {
                    "part_id": part_id,
                    "part_name": part.get("name"),
                    "part_number": part.get("part_number"),
                    "current_stock": on_hand,
                    "min_qty": min_qty,
                    "max_qty": max_qty,
                    "quantity_requested": suggested_qty,
                    "urgency": "high" if on_hand == 0 else ("medium" if on_hand <= min_qty else "low"),
                },
                "field_metadata": {
                    "quantity_requested": {
                        "classification": "BACKEND_AUTO",
                        "suggested_value": suggested_qty,
                        "editable": True,
                    },
                    "urgency": {
                        "classification": "BACKEND_AUTO",
                        "options": ["low", "medium", "high", "critical"],
                        "editable": True,
                    },
                },
            }

        except Exception as e:
            logger.error(f"prefill_add_to_shopping_list failed: {e}", exc_info=True)
            raise

    async def prefill_adjust_stock(
        self,
        yacht_id: str,
        part_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Compute prefill values for adjust_stock_quantity action.
        """
        try:
            result = self.db.table("pms_parts").select(
                "id, name, part_number, pms_part_stock_levels(on_hand_qty, min_qty, location_id)"
            ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

            if not result.data:
                raise ValueError(f"Part not found: {part_id}")

            part = result.data
            stock = part.get("pms_part_stock_levels", [{}])[0] if part.get("pms_part_stock_levels") else {}

            return {
                "status": "success",
                "prefill": {
                    "part_id": part_id,
                    "part_name": part.get("name"),
                    "part_number": part.get("part_number"),
                    "current_quantity": stock.get("on_hand_qty", 0) or 0,
                    "location_id": stock.get("location_id"),
                    "new_quantity": None,  # User must provide
                    "reason": None,        # User must provide
                },
                "field_metadata": {
                    "current_quantity": {
                        "classification": "BACKEND_AUTO",
                        "editable": False,
                    },
                    "new_quantity": {
                        "classification": "REQUIRED",
                        "editable": True,
                    },
                    "reason": {
                        "classification": "REQUIRED",
                        "options": [
                            "physical_count",
                            "damaged",
                            "expired",
                            "found_additional",
                            "correction",
                            "other",
                        ],
                        "editable": True,
                    },
                },
            }

        except Exception as e:
            logger.error(f"prefill_adjust_stock failed: {e}", exc_info=True)
            raise


# =============================================================================
# MUTATION ADAPTERS (for internal_dispatcher integration)
# =============================================================================

def _add_to_shopping_list_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Add part to shopping list with computed quantity."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        quantity = params.get("quantity_requested", 1)
        urgency = params.get("urgency", "medium")
        notes = params.get("notes")

        now = datetime.now(timezone.utc).isoformat()
        item_id = str(uuid_lib.uuid4())

        # Verify part exists and get name
        part_result = db.table("pms_parts").select("id, name").eq(
            "id", part_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not part_result.data:
            raise ValueError(f"Part {part_id} not found or access denied")

        part_name = part_result.data.get("name")

        # Insert shopping list item
        item_data = {
            "id": item_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "part_name": part_name,
            "quantity_requested": quantity,
            "urgency": urgency,
            "status": "requested",
            "notes": notes,
            "requested_by": user_id,
            "requested_at": now,
            "created_at": now,
        }

        result = db.table("pms_shopping_list_items").insert(item_data).execute()

        if not result.data:
            raise Exception("Failed to add to shopping list")

        # Audit log (non-signed)
        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "shopping_item",
                "entity_id": item_id,
                "action": "add_to_shopping_list",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "part_id": part_id,
                    "part_name": part_name,
                    "quantity_requested": quantity,
                    "urgency": urgency,
                },
                "signature": {},  # Non-signed
                "metadata": {"source": "part_lens"},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for add_to_shopping_list: {e}")

        return {
            "status": "success",
            "shopping_item_id": item_id,
            "part_id": part_id,
            "part_name": part_name,
            "quantity_requested": quantity,
            "message": f"Added {part_name} to shopping list",
        }

    return _fn


def _consume_part_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Consume part and record transaction."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        quantity = params["quantity"]
        work_order_id = params.get("work_order_id")
        notes = params.get("notes")

        now = datetime.now(timezone.utc).isoformat()

        # Get current stock
        stock_result = db.table("pms_part_stock_levels").select(
            "id, on_hand_qty, location_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result.data:
            raise ValueError(f"No stock record for part {part_id}")

        stock = stock_result.data
        current_qty = stock.get("on_hand_qty", 0) or 0

        if quantity > current_qty:
            raise ValueError(f"Insufficient stock: requested {quantity}, available {current_qty}")

        new_qty = current_qty - quantity

        # Update stock level
        db.table("pms_part_stock_levels").update({
            "on_hand_qty": new_qty,
            "updated_at": now,
        }).eq("id", stock["id"]).execute()

        # Create inventory transaction
        txn_id = str(uuid_lib.uuid4())
        db.table("pms_inventory_transactions").insert({
            "id": txn_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "transaction_type": "consumed",
            "quantity": -quantity,  # Negative for consumption
            "work_order_id": work_order_id,
            "location_id": stock.get("location_id"),
            "performed_by": user_id,
            "notes": notes,
            "created_at": now,
        }).execute()

        # Audit log
        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "part",
                "entity_id": part_id,
                "action": "consume_part",
                "user_id": user_id,
                "old_values": {"on_hand_qty": current_qty},
                "new_values": {"on_hand_qty": new_qty, "consumed": quantity},
                "signature": {},
                "metadata": {"source": "part_lens", "work_order_id": work_order_id},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for consume_part: {e}")

        # Check if low stock notification needed
        min_result = db.table("pms_part_stock_levels").select(
            "min_qty"
        ).eq("id", stock["id"]).maybe_single().execute()

        min_qty = (min_result.data or {}).get("min_qty", 0) or 0
        is_now_low = new_qty <= min_qty and min_qty > 0

        return {
            "status": "success",
            "transaction_id": txn_id,
            "part_id": part_id,
            "quantity_consumed": quantity,
            "new_stock_level": new_qty,
            "is_low_stock": is_now_low,
            "message": f"Consumed {quantity} units",
        }

    return _fn


def _adjust_stock_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Adjust stock quantity with reason."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        new_quantity = params["new_quantity"]
        reason = params["reason"]

        now = datetime.now(timezone.utc).isoformat()

        # Get current stock
        stock_result = db.table("pms_part_stock_levels").select(
            "id, on_hand_qty, location_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result.data:
            raise ValueError(f"No stock record for part {part_id}")

        stock = stock_result.data
        old_qty = stock.get("on_hand_qty", 0) or 0
        adjustment = new_quantity - old_qty

        # Update stock
        db.table("pms_part_stock_levels").update({
            "on_hand_qty": new_quantity,
            "updated_at": now,
        }).eq("id", stock["id"]).execute()

        # Create inventory transaction
        txn_id = str(uuid_lib.uuid4())
        db.table("pms_inventory_transactions").insert({
            "id": txn_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "transaction_type": "adjusted",
            "quantity": adjustment,
            "location_id": stock.get("location_id"),
            "performed_by": user_id,
            "notes": f"{reason}: {old_qty} -> {new_quantity}",
            "created_at": now,
        }).execute()

        # Audit log
        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "part",
                "entity_id": part_id,
                "action": "adjust_stock_quantity",
                "user_id": user_id,
                "old_values": {"on_hand_qty": old_qty},
                "new_values": {"on_hand_qty": new_quantity, "reason": reason},
                "signature": {},
                "metadata": {"source": "part_lens", "adjustment": adjustment},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for adjust_stock_quantity: {e}")

        return {
            "status": "success",
            "transaction_id": txn_id,
            "part_id": part_id,
            "old_quantity": old_qty,
            "new_quantity": new_quantity,
            "adjustment": adjustment,
            "reason": reason,
            "message": f"Stock adjusted from {old_qty} to {new_quantity}",
        }

    return _fn


def _receive_part_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Receive parts into inventory."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        quantity = params["quantity_received"]
        supplier_id = params.get("supplier_id")
        invoice_number = params.get("invoice_number")
        location_id = params.get("location_id")
        notes = params.get("notes")

        now = datetime.now(timezone.utc).isoformat()

        # Get or create stock record
        stock_result = db.table("pms_part_stock_levels").select(
            "id, on_hand_qty, location_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if stock_result.data:
            stock = stock_result.data
            old_qty = stock.get("on_hand_qty", 0) or 0
            new_qty = old_qty + quantity
            final_location = location_id or stock.get("location_id")

            db.table("pms_part_stock_levels").update({
                "on_hand_qty": new_qty,
                "location_id": final_location,
                "updated_at": now,
            }).eq("id", stock["id"]).execute()
        else:
            # Create new stock record
            old_qty = 0
            new_qty = quantity
            final_location = location_id

            db.table("pms_part_stock_levels").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "part_id": part_id,
                "on_hand_qty": new_qty,
                "location_id": final_location,
                "created_at": now,
                "updated_at": now,
            }).execute()

        # Create inventory transaction
        txn_id = str(uuid_lib.uuid4())
        db.table("pms_inventory_transactions").insert({
            "id": txn_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "transaction_type": "received",
            "quantity": quantity,  # Positive for receipt
            "supplier_id": supplier_id,
            "location_id": final_location,
            "performed_by": user_id,
            "notes": f"Invoice: {invoice_number}" if invoice_number else notes,
            "created_at": now,
        }).execute()

        # Audit log
        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "part",
                "entity_id": part_id,
                "action": "receive_part",
                "user_id": user_id,
                "old_values": {"on_hand_qty": old_qty},
                "new_values": {"on_hand_qty": new_qty, "received": quantity},
                "signature": {},
                "metadata": {"source": "part_lens", "supplier_id": supplier_id, "invoice": invoice_number},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for receive_part: {e}")

        return {
            "status": "success",
            "transaction_id": txn_id,
            "part_id": part_id,
            "quantity_received": quantity,
            "new_stock_level": new_qty,
            "location_id": final_location,
            "message": f"Received {quantity} units",
        }

    return _fn


def _transfer_part_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Transfer part between locations."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        quantity = params["quantity"]
        from_location = params["from_location_id"]
        to_location = params["to_location_id"]
        notes = params.get("notes")

        now = datetime.now(timezone.utc).isoformat()

        # Get source stock
        from_stock = db.table("pms_part_stock_levels").select(
            "id, on_hand_qty"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).eq(
            "location_id", from_location
        ).maybe_single().execute()

        if not from_stock.data:
            raise ValueError(f"No stock at source location {from_location}")

        from_qty = from_stock.data.get("on_hand_qty", 0) or 0
        if quantity > from_qty:
            raise ValueError(f"Insufficient stock at source: {from_qty} available")

        # Update source (decrease)
        db.table("pms_part_stock_levels").update({
            "on_hand_qty": from_qty - quantity,
            "updated_at": now,
        }).eq("id", from_stock.data["id"]).execute()

        # Get or create destination stock
        to_stock = db.table("pms_part_stock_levels").select(
            "id, on_hand_qty"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).eq(
            "location_id", to_location
        ).maybe_single().execute()

        if to_stock.data:
            to_qty = to_stock.data.get("on_hand_qty", 0) or 0
            db.table("pms_part_stock_levels").update({
                "on_hand_qty": to_qty + quantity,
                "updated_at": now,
            }).eq("id", to_stock.data["id"]).execute()
        else:
            db.table("pms_part_stock_levels").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "part_id": part_id,
                "on_hand_qty": quantity,
                "location_id": to_location,
                "created_at": now,
                "updated_at": now,
            }).execute()

        # Create OUT transaction
        out_txn_id = str(uuid_lib.uuid4())
        db.table("pms_inventory_transactions").insert({
            "id": out_txn_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "transaction_type": "transferred_out",
            "quantity": -quantity,
            "location_id": from_location,
            "performed_by": user_id,
            "notes": f"Transfer to {to_location}",
            "created_at": now,
        }).execute()

        # Create IN transaction
        in_txn_id = str(uuid_lib.uuid4())
        db.table("pms_inventory_transactions").insert({
            "id": in_txn_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "transaction_type": "transferred_in",
            "quantity": quantity,
            "location_id": to_location,
            "performed_by": user_id,
            "notes": f"Transfer from {from_location}",
            "created_at": now,
        }).execute()

        # Audit log
        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "part",
                "entity_id": part_id,
                "action": "transfer_part",
                "user_id": user_id,
                "old_values": {"from_location": from_location, "from_qty": from_qty},
                "new_values": {"to_location": to_location, "quantity": quantity},
                "signature": {},
                "metadata": {"source": "part_lens"},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for transfer_part: {e}")

        return {
            "status": "success",
            "out_transaction_id": out_txn_id,
            "in_transaction_id": in_txn_id,
            "part_id": part_id,
            "quantity_transferred": quantity,
            "from_location_id": from_location,
            "to_location_id": to_location,
            "message": f"Transferred {quantity} units",
        }

    return _fn


def _mark_part_critical_adapter(handlers: PartHandlers):
    async def _fn(**params):
        """Mark part as critical (SIGNED action)."""
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        part_id = params["part_id"]
        is_critical = params["is_critical"]
        reason = params["reason"]
        signature = params["signature"]

        now = datetime.now(timezone.utc).isoformat()

        # Validate signature
        if not signature or signature == {}:
            raise ValueError("Signature is required for mark_part_critical (signed action)")

        # Get current state
        part_result = db.table("pms_parts").select(
            "id, name, is_critical"
        ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not part_result.data:
            raise ValueError(f"Part {part_id} not found")

        old_critical = part_result.data.get("is_critical", False)

        # Update part
        db.table("pms_parts").update({
            "is_critical": is_critical,
            "updated_at": now,
        }).eq("id", part_id).execute()

        # SIGNED audit log
        import hashlib
        signature_hash = hashlib.sha256(
            f"{user_id}:{part_id}:{is_critical}:{now}".encode()
        ).hexdigest()

        signature_payload = {
            "user_id": user_id,
            "signature_type": "mark_part_critical",
            "part_id": part_id,
            "is_critical": is_critical,
            "reason": reason,
            "signature_hash": f"sha256:{signature_hash}",
            "signed_at": now,
            **signature,  # Include user-provided signature data
        }

        try:
            db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "part",
                "entity_id": part_id,
                "action": "mark_part_critical",
                "user_id": user_id,
                "old_values": {"is_critical": old_critical},
                "new_values": {"is_critical": is_critical, "reason": reason},
                "signature": signature_payload,  # SIGNED
                "metadata": {"source": "part_lens"},
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for mark_part_critical: {e}")

        return {
            "status": "success",
            "part_id": part_id,
            "is_critical": is_critical,
            "reason": reason,
            "is_signed": True,
            "message": f"Part marked as {'critical' if is_critical else 'non-critical'}",
        }

    return _fn


def get_part_handlers(supabase_client) -> Dict[str, callable]:
    """Get part handler functions for registration."""
    handlers = PartHandlers(supabase_client)

    return {
        # READ handlers
        "view_part_details": handlers.view_part_details,
        "view_low_stock": handlers.view_low_stock,

        # Prefill handlers
        "prefill_add_to_shopping_list": handlers.prefill_add_to_shopping_list,
        "prefill_adjust_stock": handlers.prefill_adjust_stock,

        # MUTATION handlers
        "add_to_shopping_list": _add_to_shopping_list_adapter(handlers),
        "consume_part": _consume_part_adapter(handlers),
        "adjust_stock_quantity": _adjust_stock_adapter(handlers),
        "receive_part": _receive_part_adapter(handlers),
        "transfer_part": _transfer_part_adapter(handlers),
        "mark_part_critical": _mark_part_critical_adapter(handlers),
    }
```

---

## Phase 4: Bridge Handlers in Internal Dispatcher

### 4.1 Add Imports

**File**: `apps/api/action_router/dispatchers/internal_dispatcher.py`

Add after certificate_handlers import (line ~27):

```python
from handlers.part_handlers import get_part_handlers as _get_part_handlers
```

### 4.2 Add Lazy Initialization

Add after certificate lazy init pattern:

```python
_part_handlers = None

def _get_part_handlers_instance():
    """Get lazy-initialized Part handlers."""
    global _part_handlers
    if _part_handlers is None:
        _part_handlers = _get_part_handlers(get_supabase_client())
    return _part_handlers
```

### 4.3 Add Wrapper Functions

Add after certificate wrappers section (around line ~300):

```python
# ============================================================================
# PART/INVENTORY WRAPPERS (bridge to part handlers)
# ============================================================================

async def _part_add_to_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("add_to_shopping_list")
    if not fn:
        raise ValueError("add_to_shopping_list handler not registered")
    return await fn(**params)


async def _part_consume(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("consume_part")
    if not fn:
        raise ValueError("consume_part handler not registered")
    return await fn(**params)


async def _part_adjust_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("adjust_stock_quantity")
    if not fn:
        raise ValueError("adjust_stock_quantity handler not registered")
    return await fn(**params)


async def _part_receive(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("receive_part")
    if not fn:
        raise ValueError("receive_part handler not registered")
    return await fn(**params)


async def _part_transfer(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("transfer_part")
    if not fn:
        raise ValueError("transfer_part handler not registered")
    return await fn(**params)


async def _part_mark_critical(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("mark_part_critical")
    if not fn:
        raise ValueError("mark_part_critical handler not registered")
    return await fn(**params)


async def _part_view_details(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("view_part_details")
    if not fn:
        raise ValueError("view_part_details handler not registered")
    return await fn(
        entity_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _part_view_low_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_part_handlers_instance()
    fn = handlers.get("view_low_stock")
    if not fn:
        raise ValueError("view_low_stock handler not registered")
    return await fn(
        entity_id=params.get("entity_id") or params["yacht_id"],
        yacht_id=params["yacht_id"],
        params=params
    )
```

### 4.4 Register in INTERNAL_HANDLERS

Add to the `INTERNAL_HANDLERS` dict (around line ~2374):

```python
    # =========================================================================
    # Part/Inventory Handlers (Part Lens v2)
    # =========================================================================
    "add_to_shopping_list": _part_add_to_shopping_list,
    "consume_part": _part_consume,
    "adjust_stock_quantity": _part_adjust_stock,
    "receive_part": _part_receive,
    "transfer_part": _part_transfer,
    "mark_part_critical": _part_mark_critical,
    "view_part_details": _part_view_details,
    "view_low_stock": _part_view_low_stock,
```

---

## Phase 5: Add Prefill Routes

### 5.1 Add Prefill Endpoints

**File**: `apps/api/routes/p0_actions_routes.py`

Add after existing prefill patterns:

```python
@router.post("/v1/parts/shopping-list/prefill")
async def prefill_add_to_shopping_list(
    request: Request,
    yacht_id: str = Body(...),
    part_id: str = Body(...),
):
    """
    Prefill values for add_to_shopping_list action.

    Returns computed quantity_requested based on stock levels.
    """
    from handlers.part_handlers import get_part_handlers
    from action_router.dispatchers.internal_dispatcher import get_supabase_client

    handlers = get_part_handlers(get_supabase_client())
    prefill_fn = handlers.get("prefill_add_to_shopping_list")

    return await prefill_fn(
        yacht_id=yacht_id,
        part_id=part_id,
    )


@router.post("/v1/parts/adjust-stock/prefill")
async def prefill_adjust_stock(
    request: Request,
    yacht_id: str = Body(...),
    part_id: str = Body(...),
):
    """
    Prefill values for adjust_stock_quantity action.

    Returns current quantity for user reference.
    """
    from handlers.part_handlers import get_part_handlers
    from action_router.dispatchers.internal_dispatcher import get_supabase_client

    handlers = get_part_handlers(get_supabase_client())
    prefill_fn = handlers.get("prefill_adjust_stock")

    return await prefill_fn(
        yacht_id=yacht_id,
        part_id=part_id,
    )
```

---

## Phase 6: Docker Tests

### 6.1 Create Test File

**File**: `apps/api/tests/test_part_lens_v2.py`

```python
"""
Part Lens v2 Tests
==================

Tests for Part Lens v2 actions following the acceptance test spec.
"""

import pytest
import uuid
from datetime import datetime, timezone

# Test fixtures assume Docker test environment with seeded data


class TestPartLensRegistry:
    """Test Part Lens actions are properly registered."""

    def test_part_actions_registered(self):
        """Verify all Part Lens actions exist in registry."""
        from action_router.registry import ACTION_REGISTRY

        expected_actions = [
            "add_to_shopping_list",
            "consume_part",
            "adjust_stock_quantity",
            "receive_part",
            "transfer_part",
            "mark_part_critical",
            "view_part_details",
            "view_low_stock",
        ]

        for action_id in expected_actions:
            assert action_id in ACTION_REGISTRY, f"Missing action: {action_id}"

    def test_part_actions_have_domain(self):
        """Verify all Part Lens actions have domain='parts'."""
        from action_router.registry import ACTION_REGISTRY

        part_actions = [
            "add_to_shopping_list",
            "consume_part",
            "adjust_stock_quantity",
            "receive_part",
            "transfer_part",
            "mark_part_critical",
            "view_part_details",
            "view_low_stock",
        ]

        for action_id in part_actions:
            action = ACTION_REGISTRY[action_id]
            assert action.domain == "parts", f"{action_id} should have domain='parts'"

    def test_part_actions_have_search_keywords(self):
        """Verify Part Lens actions have search keywords for discoverability."""
        from action_router.registry import ACTION_REGISTRY

        part_actions = [
            "add_to_shopping_list",
            "consume_part",
            "adjust_stock_quantity",
        ]

        for action_id in part_actions:
            action = ACTION_REGISTRY[action_id]
            assert len(action.search_keywords) > 0, f"{action_id} missing search_keywords"

    def test_mark_critical_is_signed(self):
        """Verify mark_part_critical is a SIGNED action."""
        from action_router.registry import ACTION_REGISTRY, ActionVariant

        action = ACTION_REGISTRY["mark_part_critical"]
        assert action.variant == ActionVariant.SIGNED


class TestPartLensSearchActions:
    """Test action search for Part Lens."""

    def test_search_adjust_stock(self):
        """Search 'adjust stock' should return adjust_stock_quantity."""
        from action_router.registry import search_actions

        results = search_actions(query="adjust stock", domain="parts")
        action_ids = [r["action_id"] for r in results]

        assert "adjust_stock_quantity" in action_ids

    def test_search_shopping(self):
        """Search 'shopping' should return add_to_shopping_list."""
        from action_router.registry import search_actions

        results = search_actions(query="shopping list", domain="parts")
        action_ids = [r["action_id"] for r in results]

        assert "add_to_shopping_list" in action_ids

    def test_search_low_stock(self):
        """Search 'low stock' should return view_low_stock."""
        from action_router.registry import search_actions

        results = search_actions(query="low stock", domain="parts")
        action_ids = [r["action_id"] for r in results]

        assert "view_low_stock" in action_ids


class TestPartLensFieldMetadata:
    """Test field metadata for auto-population."""

    def test_add_to_shopping_has_field_metadata(self):
        """Verify add_to_shopping_list has field_metadata."""
        from action_router.registry import ACTION_REGISTRY

        action = ACTION_REGISTRY["add_to_shopping_list"]
        assert len(action.field_metadata) > 0

    def test_quantity_requested_is_backend_auto(self):
        """Verify quantity_requested is BACKEND_AUTO."""
        from action_router.registry import ACTION_REGISTRY, FieldClassification

        action = ACTION_REGISTRY["add_to_shopping_list"]
        qty_field = next(
            (f for f in action.field_metadata if f.name == "quantity_requested"),
            None
        )

        assert qty_field is not None
        assert qty_field.classification == FieldClassification.BACKEND_AUTO

    def test_part_id_requires_lookup(self):
        """Verify part_id requires yacht-scoped lookup."""
        from action_router.registry import ACTION_REGISTRY

        action = ACTION_REGISTRY["consume_part"]
        part_field = next(
            (f for f in action.field_metadata if f.name == "part_id"),
            None
        )

        assert part_field is not None
        assert part_field.lookup_required is True


# Integration tests (require Docker environment)

@pytest.mark.integration
class TestPartLensHandlers:
    """Integration tests for Part Lens handlers."""

    @pytest.fixture
    def test_yacht_id(self):
        return "test-yacht-001"

    @pytest.fixture
    def test_user_id(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def test_part_id(self):
        return str(uuid.uuid4())

    async def test_consume_insufficient_stock(self, test_yacht_id, test_user_id, test_part_id):
        """Consuming more than available should return 400."""
        from action_router.dispatchers.internal_dispatcher import dispatch

        with pytest.raises(ValueError, match="Insufficient stock"):
            await dispatch("consume_part", {
                "yacht_id": test_yacht_id,
                "user_id": test_user_id,
                "part_id": test_part_id,
                "quantity": 9999,  # More than available
            })

    async def test_mark_critical_requires_signature(self, test_yacht_id, test_user_id, test_part_id):
        """mark_part_critical without signature should return 400."""
        from action_router.dispatchers.internal_dispatcher import dispatch

        with pytest.raises(ValueError, match="Signature is required"):
            await dispatch("mark_part_critical", {
                "yacht_id": test_yacht_id,
                "user_id": test_user_id,
                "part_id": test_part_id,
                "is_critical": True,
                "reason": "Safety critical",
                "signature": {},  # Empty signature should fail
            })
```

### 6.2 Run Tests

```bash
cd apps/api
docker compose up -d
pytest tests/test_part_lens_v2.py -v

# Expected: All registry tests pass
# Integration tests may need seeded data
```

---

## Phase 7: PR and Review

### 7.1 Commit Strategy

```bash
# Commit 1: Registry extension
git add apps/api/action_router/registry.py
git commit -m "feat(parts): extend ActionDefinition with field_metadata

Add FieldClassification enum and FieldMetadata dataclass.
Support auto-population hints for prepare/prefill phase.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Commit 2: Part handlers
git add apps/api/handlers/part_handlers.py
git commit -m "feat(parts): add Part Lens v2 handlers

Implement 8 actions: add_to_shopping_list, consume_part,
adjust_stock_quantity, receive_part, transfer_part,
mark_part_critical (SIGNED), view_part_details, view_low_stock.

All mutations write audit log with signature invariant.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Commit 3: Dispatcher integration
git add apps/api/action_router/dispatchers/internal_dispatcher.py
git commit -m "feat(parts): wire Part Lens handlers to dispatcher

Add bridge functions for Part Lens v2 actions.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Commit 4: Tests
git add apps/api/tests/test_part_lens_v2.py
git commit -m "test(parts): add Part Lens v2 test suite

Registry tests, search tests, field metadata tests.
Integration tests for handler validation.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### 7.2 Create PR

```bash
git push -u origin parts/part-lens-v2-backend_472103

gh pr create \
  --title "feat(parts): Part Lens v2 Backend Implementation" \
  --body "$(cat <<'EOF'
## Summary
- Extends ActionDefinition with `field_metadata` for auto-population
- Adds 8 Part Lens actions to registry with search keywords
- Implements part_handlers.py with prefill/execute pattern
- All mutations write to pms_audit_log (signature invariant)
- All mutations create pms_inventory_transactions

## Actions Added
| Action | Variant | Domain |
|--------|---------|--------|
| add_to_shopping_list | MUTATE | parts |
| consume_part | MUTATE | parts |
| adjust_stock_quantity | MUTATE | parts |
| receive_part | MUTATE | parts |
| transfer_part | MUTATE | parts |
| mark_part_critical | SIGNED | parts |
| view_part_details | READ | parts |
| view_low_stock | READ | parts |

## Test Plan
- [ ] Registry tests pass
- [ ] Search tests pass
- [ ] Field metadata tests pass
- [ ] Docker integration tests pass
- [ ] Manual test: "adjust stock" returns action button

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Checklist

### Phase 0: Foundation
- [ ] Branch created from main
- [ ] RLS migration verified
- [ ] Docker test environment running

### Phase 1: Registry Extension
- [ ] FieldClassification enum added
- [ ] FieldMetadata dataclass added
- [ ] ActionDefinition extended
- [ ] Helper functions added
- [ ] Exports updated

### Phase 2: Action Registration
- [ ] 8 Part Lens actions added to registry
- [ ] All actions have domain="parts"
- [ ] All actions have search_keywords
- [ ] field_metadata populated
- [ ] SIGNED action has signature required_field

### Phase 3: Handlers
- [ ] part_handlers.py created
- [ ] READ handlers implemented
- [ ] MUTATE handlers implemented
- [ ] SIGNED handler implemented
- [ ] Prefill handlers implemented
- [ ] All mutations write audit log
- [ ] All mutations create inventory transactions

### Phase 4: Dispatcher
- [ ] Import added
- [ ] Lazy init added
- [ ] Wrapper functions added
- [ ] INTERNAL_HANDLERS updated

### Phase 5: Routes
- [ ] Prefill endpoints added

### Phase 6: Tests
- [ ] Test file created
- [ ] Registry tests pass
- [ ] Search tests pass
- [ ] Field metadata tests pass
- [ ] Integration tests pass

### Phase 7: PR
- [ ] Commits organized
- [ ] PR created with summary
- [ ] CI passing

---

## Dependencies on Other Workers

| Worker | Dependency | Status |
|--------|------------|--------|
| Fault Lens | None | Independent |
| Equipment Lens | None | Independent |
| Certificate Lens | Pattern reference | Complete |
| Frontend | Action list API | Ready after this PR |

---

## Rollback Plan

If issues arise:

```bash
# Revert to main
git checkout main

# Remove Part Lens actions from registry
# Remove part_handlers.py
# Remove dispatcher wrappers
```

The implementation is modular and can be rolled back per-phase if needed.
