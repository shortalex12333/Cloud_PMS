"""
Part Lens - Microaction Logic
==============================

Context-aware action suggestions for Part Lens entities.

Entity Types Handled:
- part: Core part records
- inventory_stock: Stock level records
- shopping_list_item: Procurement requests

Action Filtering Logic:
1. Stock-based filtering:
   - on_hand = 0 → hide consume_part, transfer_part, write_off_part
   - on_hand <= min_level → boost add_to_shopping_list priority

2. Role-based filtering:
   - SIGNED actions (adjust_stock_quantity, write_off_part) → Captain/Manager only
   - MUTATE actions (receive, consume, transfer) → Chief Engineer+
   - READ actions → All roles

3. Intent-based prioritization:
   - If query_intent matches action_id → priority = 5 (highest)
   - Primary actions (based on state) → priority = 3
   - Secondary actions → priority = 1

Owner: Part Lens team
"""

from typing import List, Dict, Any, Optional
import logging

from ..base_microaction import (
    BaseLensMicroactions,
    ActionSuggestion,
    ActionVariant,
    MicroactionExecutionError
)

logger = logging.getLogger(__name__)


class PartLensMicroactions(BaseLensMicroactions):
    """Part Lens microaction logic."""

    lens_name = "part_lens"
    entity_types = ["part", "inventory_stock", "shopping_list_item"]

    def __init__(self, db_client):
        """
        Initialize Part Lens microactions.

        Args:
            db_client: Supabase client or async postgres client
        """
        self.db = db_client

    async def get_suggestions(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """
        Get context-valid actions for a part entity.

        Args:
            entity_type: "part", "inventory_stock", or "shopping_list_item"
            entity_id: UUID of the entity
            entity_data: Full entity data from search result
            user_role: User's role ("crew", "chief_engineer", "captain", etc.)
            yacht_id: Tenant isolation UUID
            query_intent: Optional intent (e.g., "receive_part")

        Returns:
            List of ActionSuggestion objects, filtered and prioritized
        """
        try:
            # Get all part actions for user role
            from apps.api.action_router.registry import get_actions_for_domain
            all_actions = get_actions_for_domain("parts", user_role)

            # Fetch current stock state
            part_id = entity_id if entity_type == "part" else entity_data.get("part_id")
            stock_info = await self._get_stock_info(part_id, yacht_id)

            # Get part details
            part_details = await self._get_part_details(part_id, yacht_id)

            # Build suggestions
            suggestions = []

            for action in all_actions:
                action_id = action.action_id

                # Stock-based filtering
                is_out_of_stock = stock_info["on_hand"] == 0
                if is_out_of_stock and action_id in ["consume_part", "transfer_part", "write_off_part"]:
                    continue  # Can't consume/transfer/write-off if no stock

                # Calculate priority
                priority = self._calculate_priority(
                    action_id=action_id,
                    query_intent=query_intent,
                    is_out_of_stock=is_out_of_stock,
                    is_low_stock=stock_info["on_hand"] <= part_details.get("min_level", 0),
                    is_critical=part_details.get("is_critical", False)
                )

                # Get prefill data
                prefill_data = await self._get_prefill_data(
                    action_id=action_id,
                    part_id=part_id,
                    part_details=part_details,
                    stock_info=stock_info,
                    yacht_id=yacht_id
                )

                # Determine if confirmation required
                requires_confirmation = action_id in [
                    "write_off_part",
                    "adjust_stock_quantity",
                    "transfer_part"
                ]

                # Build suggestion
                suggestions.append(ActionSuggestion(
                    action_id=action_id,
                    label=action.label,
                    variant=ActionVariant(action.variant.value),
                    entity_id=entity_id,
                    entity_type=entity_type,
                    prefill_data=prefill_data,
                    priority=priority,
                    requires_confirmation=requires_confirmation
                ))

            # Sort by priority (descending)
            suggestions.sort(key=lambda s: s.priority, reverse=True)

            return suggestions

        except Exception as e:
            logger.error(
                f"Part Lens: Failed to get suggestions for {entity_type} ({entity_id}): {str(e)}"
            )
            raise MicroactionExecutionError(
                lens_name=self.lens_name,
                entity_type=entity_type,
                entity_id=entity_id,
                error=e
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_stock_info(self, part_id: str, yacht_id: str) -> Dict[str, Any]:
        """
        Fetch current stock information for a part.

        Args:
            part_id: Part UUID
            yacht_id: Tenant isolation UUID

        Returns:
            Dict with on_hand, allocated, available, storage_location
        """
        try:
            result = self.db.table("pms_part_stock").select(
                "on_hand, location"
            ).eq("yacht_id", yacht_id).eq("part_id", part_id).maybe_single().execute()

            if result.data:
                return {
                    "on_hand": result.data.get("on_hand", 0) or 0,
                    "allocated": 0,  # Calculate if needed
                    "available": result.data.get("on_hand", 0) or 0,
                    "storage_location": result.data.get("location"),
                }
            else:
                return {
                    "on_hand": 0,
                    "allocated": 0,
                    "available": 0,
                    "storage_location": None,
                }
        except Exception as e:
            logger.warning(f"Failed to fetch stock info for part {part_id}: {str(e)}")
            return {
                "on_hand": 0,
                "allocated": 0,
                "available": 0,
                "storage_location": None,
            }

    async def _get_part_details(self, part_id: str, yacht_id: str) -> Dict[str, Any]:
        """
        Fetch part details.

        Args:
            part_id: Part UUID
            yacht_id: Tenant isolation UUID

        Returns:
            Dict with part_number, name, manufacturer, category, is_critical, min_level
        """
        try:
            result = self.db.table("pms_parts").select(
                "id, part_number, name, manufacturer, category, subcategory, "
                "is_critical, min_level, reorder_multiple"
            ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

            if result.data:
                return result.data
            else:
                return {}
        except Exception as e:
            logger.warning(f"Failed to fetch part details for {part_id}: {str(e)}")
            return {}

    def _calculate_priority(
        self,
        action_id: str,
        query_intent: Optional[str],
        is_out_of_stock: bool,
        is_low_stock: bool,
        is_critical: bool
    ) -> int:
        """
        Calculate action priority based on context.

        Priority Levels:
        - 5: Intent match (user explicitly asked for this action)
        - 4: Critical part primary action
        - 3: Primary action based on state
        - 2: Secondary relevant action
        - 1: Standard action

        Args:
            action_id: Action identifier
            query_intent: Detected intent from query
            is_out_of_stock: Stock is 0
            is_low_stock: Stock <= min_level
            is_critical: Part is marked critical

        Returns:
            Priority integer (1-5)
        """
        # Intent match: highest priority
        if query_intent and action_id == query_intent:
            return 5

        # Critical part special handling
        if is_critical:
            if action_id == "add_to_shopping_list" and (is_out_of_stock or is_low_stock):
                return 4
            elif action_id == "receive_part":
                return 4

        # Out of stock: prioritize receiving
        if is_out_of_stock:
            if action_id == "add_to_shopping_list":
                return 3
            elif action_id == "receive_part":
                return 3
            elif action_id == "view_part_details":
                return 2

        # Low stock: prioritize ordering
        elif is_low_stock:
            if action_id == "add_to_shopping_list":
                return 3
            elif action_id == "receive_part":
                return 2
            elif action_id in ["consume_part", "transfer_part"]:
                return 1  # Lower priority for consuming low stock

        # Normal stock: standard priorities
        else:
            if action_id in ["receive_part", "consume_part"]:
                return 2  # Common actions
            elif action_id == "view_part_details":
                return 2

        # Default priority
        return 1

    async def _get_prefill_data(
        self,
        action_id: str,
        part_id: str,
        part_details: Dict[str, Any],
        stock_info: Dict[str, Any],
        yacht_id: str
    ) -> Dict[str, Any]:
        """
        Get prefill data for an action.

        Migrated from part_routes.py lines 315-375.

        Args:
            action_id: Action identifier
            part_id: Part UUID
            part_details: Part details dict
            stock_info: Stock info dict
            yacht_id: Tenant isolation UUID

        Returns:
            Dict of prefill data for the action form
        """
        # Common fields
        base_prefill = {
            "part_id": part_id,
            "part_name": part_details.get("name"),
            "part_number": part_details.get("part_number"),
        }

        # Action-specific prefill
        if action_id == "receive_part":
            return {
                **base_prefill,
                "location": stock_info.get("storage_location"),
                "current_stock": stock_info["on_hand"],
            }

        elif action_id == "consume_part":
            return {
                **base_prefill,
                "available_qty": stock_info["available"],
                "max_quantity": stock_info["available"],
                "location": stock_info.get("storage_location"),
            }

        elif action_id == "transfer_part":
            return {
                **base_prefill,
                "from_location_id": stock_info.get("storage_location"),
                "available_qty": stock_info["available"],
            }

        elif action_id == "write_off_part":
            return {
                **base_prefill,
                "available_qty": stock_info["on_hand"],
                "max_quantity": stock_info["on_hand"],
                "location": stock_info.get("storage_location"),
            }

        elif action_id == "adjust_stock_quantity":
            return {
                **base_prefill,
                "current_quantity": stock_info["on_hand"],
                "location": stock_info.get("storage_location"),
            }

        elif action_id == "add_to_shopping_list":
            # Compute suggested order quantity
            on_hand = stock_info["on_hand"]
            min_level = part_details.get("min_level", 0) or 0
            reorder_multiple = part_details.get("reorder_multiple", 1) or 1

            suggested_qty = self._compute_suggested_order_qty(on_hand, min_level, reorder_multiple)
            urgency = self._compute_urgency(on_hand, min_level)

            return {
                **base_prefill,
                "quantity_requested": suggested_qty,
                "urgency": urgency,
                "current_stock": on_hand,
                "min_level": min_level,
            }

        elif action_id in ("generate_part_labels", "request_label_output"):
            return {
                "part_ids": [part_id]
            }

        elif action_id == "view_part_details":
            return {
                "part_id": part_id
            }

        else:
            # Generic prefill
            return base_prefill

    def _compute_suggested_order_qty(
        self,
        on_hand: int,
        min_level: int,
        reorder_multiple: int
    ) -> int:
        """
        Compute suggested order quantity.

        From part_routes.py:
        suggested_qty = round_up(max(min_level - on_hand, 1), reorder_multiple)

        Args:
            on_hand: Current stock
            min_level: Minimum stock level
            reorder_multiple: Reorder in multiples of this

        Returns:
            Suggested order quantity
        """
        if min_level <= 0:
            return reorder_multiple  # Default to one reorder unit

        shortage = max(min_level - on_hand, 1)

        # Round up to nearest reorder_multiple
        if reorder_multiple > 1:
            suggested_qty = ((shortage + reorder_multiple - 1) // reorder_multiple) * reorder_multiple
        else:
            suggested_qty = shortage

        return suggested_qty

    def _compute_urgency(self, on_hand: int, min_level: int) -> str:
        """
        Compute urgency level based on stock.

        Args:
            on_hand: Current stock
            min_level: Minimum stock level

        Returns:
            "critical", "high", "medium", or "low"
        """
        if on_hand == 0:
            return "critical"
        elif min_level > 0 and on_hand <= min_level * 0.3:
            return "high"
        elif min_level > 0 and on_hand <= min_level * 0.6:
            return "medium"
        else:
            return "low"
