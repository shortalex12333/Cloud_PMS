"""
Inventory Domain Handlers
=========================

Group 2: READ handlers for inventory/parts actions.

Handlers:
- view_inventory_item: Part details with stock status
- view_stock_levels: Stock levels with history
- view_part_location: Storage location
- view_part_usage: Usage history
- scan_part_barcode: Lookup by barcode
- check_stock_level: Quick stock check (alias)

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
    StockStatus
)

from .schema_mapping import get_table, normalize_part, map_parts_select

logger = logging.getLogger(__name__)


class InventoryHandlers:
    """
    Inventory domain READ handlers.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_inventory_item(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View inventory item/part details.

        Returns:
        - Part data (name, part_number, manufacturer, quantity, etc.)
        - Stock status (IN_STOCK, LOW_STOCK, OUT_OF_STOCK)
        - Available actions
        """
        builder = ResponseBuilder("view_inventory_item", entity_id, "part", yacht_id)

        try:
            # Use actual schema columns
            result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            part = normalize_part(result.data)

            # Add computed fields
            part["stock_status"] = self._compute_stock_status(part)
            part["is_low_stock"] = part["stock_status"] in ("LOW_STOCK", "OUT_OF_STOCK")
            part["reorder_needed"] = part["is_low_stock"]

            # Calculate value
            if part.get("quantity") and part.get("unit_cost"):
                part["total_value"] = part["quantity"] * part["unit_cost"]

            builder.set_data(part)

            # Get part images if any
            files = await self._get_part_files(entity_id)
            if files:
                builder.add_files(files)

            # Add available actions
            builder.add_available_actions(self._get_part_actions(part))

            return builder.build()

        except Exception as e:
            logger.error(f"view_inventory_item failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_stock_levels(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View stock levels with status.

        Returns:
        - Current quantity and status
        - Min/max thresholds
        - Recent transactions (if available)
        """
        builder = ResponseBuilder("view_stock_levels", entity_id, "part", yacht_id)

        try:
            # Get current stock using actual schema
            result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            part = normalize_part(result.data)
            stock_status = self._compute_stock_status(part)

            # Try to get recent transactions
            transactions = []
            try:
                tx_result = self.db.table("stock_transactions").select(
                    "id, transaction_type, quantity, created_at, notes, user_id"
                ).eq("part_id", entity_id).order(
                    "created_at", desc=True
                ).limit(10).execute()
                transactions = tx_result.data or []
            except Exception:
                pass  # Table may not exist

            builder.set_data({
                "part_id": entity_id,
                "part_name": part.get("canonical_name"),
                "current": {
                    "quantity": part.get("quantity", 0),
                    "unit": part.get("unit", "units"),
                    "status": stock_status,
                    "location": part.get("location")
                },
                "thresholds": {
                    "min_quantity": part.get("min_quantity", 0),
                    "max_quantity": part.get("max_quantity"),
                    "reorder_point": part.get("min_quantity", 0)
                },
                "recent_transactions": transactions
            })

            # Actions based on status
            actions = [
                AvailableAction(
                    action_id="edit_inventory_quantity",
                    label="Adjust Quantity",
                    variant="MUTATE",
                    icon="edit",
                    requires_signature=True,
                    confirmation_message="Adjust inventory quantity?"
                )
            ]

            if stock_status in ("LOW_STOCK", "OUT_OF_STOCK"):
                actions.insert(0, AvailableAction(
                    action_id="create_reorder",
                    label="Create Reorder",
                    variant="MUTATE",
                    icon="cart",
                    requires_signature=True,
                    is_primary=True
                ))

            builder.add_available_actions(actions)

            return builder.build()

        except Exception as e:
            logger.error(f"view_stock_levels failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_part_location(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View part storage location.

        Returns:
        - Location details (deck, compartment, bin)
        """
        builder = ResponseBuilder("view_part_location", entity_id, "part", yacht_id)

        try:
            result = self.db.table(get_table("parts")).select(
                "id, name, description, metadata"
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            part = result.data
            # Extract location from metadata if available
            metadata = part.get("metadata") or {}

            builder.set_data({
                "part_id": entity_id,
                "part_name": part.get("name"),
                "location": {
                    "description": metadata.get("location", part.get("description")),
                    "bin_number": metadata.get("bin_number"),
                    "deck": metadata.get("deck"),
                    "compartment": metadata.get("compartment")
                }
            })

            return builder.build()

        except Exception as e:
            logger.error(f"view_part_location failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_part_usage(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View part usage history.

        Returns:
        - List of work orders where part was used
        - Usage statistics
        """
        builder = ResponseBuilder("view_part_usage", entity_id, "part", yacht_id)

        try:
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Get part name
            part_result = self.db.table(get_table("parts")).select(
                "name"
            ).eq("id", entity_id).maybe_single().execute()

            part_name = part_result.data.get("name") if part_result.data else "Unknown"

            # Try to query usage log (table may not exist yet)
            usage_records = []
            total_count = 0
            try:
                result = self.db.table(get_table("work_order_parts")).select(
                    "work_order_id, quantity_used, used_at",
                    count="exact"
                ).eq("part_id", entity_id).order(
                    "used_at", desc=True
                ).range(offset, offset + limit - 1).execute()

                usage_records = result.data or []
                total_count = result.count or len(usage_records)
            except Exception as table_err:
                # Table doesn't exist - return empty usage history
                logger.debug(f"work_order_parts table not available: {table_err}")

            # Calculate total used
            total_used = sum(r.get("quantity_used", 0) for r in usage_records)

            builder.set_data({
                "part_id": entity_id,
                "part_name": part_name,
                "usage_history": [
                    {
                        "work_order_id": r.get("work_order_id"),
                        "work_order_title": None,  # Simplified - no FK join
                        "quantity_used": r.get("quantity_used"),
                        "used_at": r.get("used_at")
                    }
                    for r in usage_records
                ],
                "summary": {
                    "total_records": total_count,
                    "total_quantity_used": total_used
                },
                "message": "Usage tracking not configured" if not usage_records else None
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_part_usage failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def scan_part_barcode(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Lookup part by barcode.

        Params:
        - barcode: The scanned barcode value

        Returns:
        - Part data if found
        """
        builder = ResponseBuilder("scan_part_barcode", entity_id, "part", yacht_id)

        try:
            barcode = (params or {}).get("barcode", entity_id)

            # Search by part_number (barcode column may not exist)
            result = self.db.table(get_table("parts")).select(
                "id, name, part_number, manufacturer, description, category, metadata"
            ).eq("yacht_id", yacht_id).eq(
                "part_number", barcode
            ).maybe_single().execute()

            if not result or not result.data:
                builder.set_error(
                    "NOT_FOUND",
                    f"No part found for barcode: {barcode}",
                    suggestions=["Verify barcode is correct", "Part may not be in inventory"]
                )
                return builder.build()

            # Normalize part data
            part = normalize_part(result.data)
            part["stock_status"] = self._compute_stock_status(part)
            part["scanned_barcode"] = barcode

            builder.set_data(part)

            # Update entity_id to actual part ID
            builder.entity_id = part["id"]

            builder.add_available_actions(self._get_part_actions(part))

            return builder.build()

        except Exception as e:
            logger.error(f"scan_part_barcode failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def check_stock_level(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Quick stock level check (alias for view_stock_levels).
        """
        return await self.view_stock_levels(entity_id, yacht_id, params)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _compute_stock_status(self, part: Dict) -> str:
        """Compute stock status for a part"""
        qty = part.get("quantity", 0) or 0
        min_qty = part.get("min_quantity", 0) or 0
        max_qty = part.get("max_quantity") or float("inf")

        if qty <= 0:
            return "OUT_OF_STOCK"
        elif qty <= min_qty:
            return "LOW_STOCK"
        elif max_qty != float("inf") and qty >= max_qty:
            return "OVERSTOCKED"
        else:
            return "IN_STOCK"

    async def _get_part_files(self, part_id: str) -> List[Dict]:
        """Get files associated with part"""
        files = []

        if not self.url_generator:
            return files

        try:
            result = self.db.table("attachments").select(
                "id, filename, mime_type, storage_path"
            ).eq("entity_type", "part").eq("entity_id", part_id).execute()

            for att in (result.data or []):
                file_ref = self.url_generator.create_file_reference(
                    bucket="attachments",
                    path=att.get("storage_path", ""),
                    filename=att.get("filename", "file"),
                    file_id=att["id"],
                    mime_type=att.get("mime_type"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())

        except Exception as e:
            logger.warning(f"Failed to get part files: {e}")

        return files

    def _get_part_actions(self, part: Dict) -> List[AvailableAction]:
        """Get available actions for part entity"""
        actions = [
            AvailableAction(
                action_id="view_stock_levels",
                label="Stock Levels",
                variant="READ",
                icon="chart"
            ),
            AvailableAction(
                action_id="view_part_location",
                label="View Location",
                variant="READ",
                icon="map-pin"
            ),
            AvailableAction(
                action_id="view_part_usage",
                label="Usage History",
                variant="READ",
                icon="activity"
            ),
            AvailableAction(
                action_id="edit_inventory_quantity",
                label="Adjust Quantity",
                variant="MUTATE",
                icon="edit",
                requires_signature=True,
                confirmation_message="Adjust inventory quantity?"
            ),
            AvailableAction(
                action_id="log_part_usage",
                label="Log Usage",
                variant="MUTATE",
                icon="minus"
            )
        ]

        # Add reorder if low stock
        if part.get("stock_status") in ("LOW_STOCK", "OUT_OF_STOCK"):
            actions.insert(0, AvailableAction(
                action_id="create_reorder",
                label="Create Reorder",
                variant="MUTATE",
                icon="cart",
                requires_signature=True,
                is_primary=True
            ))

        return actions


def get_inventory_handlers(supabase_client) -> Dict[str, callable]:
    """Get inventory handler functions for registration."""
    handlers = InventoryHandlers(supabase_client)

    return {
        "view_inventory_item": handlers.view_inventory_item,
        "view_stock_levels": handlers.view_stock_levels,
        "view_part_location": handlers.view_part_location,
        "view_part_usage": handlers.view_part_usage,
        "scan_part_barcode": handlers.scan_part_barcode,
        "check_stock_level": handlers.check_stock_level,
    }
